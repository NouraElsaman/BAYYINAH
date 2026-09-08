from __future__ import annotations

import re

from app.core.config import get_settings
from app.core.logging import get_logger
from app.graphs.legal_assistant.state import LegalAssistantState
from app.schemas.chat import Citation
from app.services.confidence_scorer import score_from_citations
from app.services.embedding_service import get_embedding_service
from app.services.retrieval_service import get_retrieval_service
from app.services.reranker_service import get_reranker_service

logger = get_logger("bayyinah.graph.retrieval")
settings = get_settings()


from app.observability import trace_node


def _rrf_merge(list_a, list_b, k: int = 60):
    """Reciprocal Rank Fusion of two citation lists. Keeps the highest-ranked
    from each list and blends their scores without duplicating chunk_ids."""
    scores: dict[str, float] = {}
    doc_map: dict[str, Citation] = {}

    for rank, c in enumerate(list_a, 1):
        cid = c.chunk_id
        doc_map[cid] = c
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)

    for rank, c in enumerate(list_b, 1):
        cid = c.chunk_id
        if cid not in doc_map:
            doc_map[cid] = c
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)

    merged = []
    for cid, c in doc_map.items():
        merged.append(
            Citation(
                chunk_id=c.chunk_id,
                doc_id=c.doc_id,
                law_name=c.law_name,
                law_number=c.law_number,
                law_year=c.law_year,
                law_type=c.law_type,
                category=c.category,
                article_number=c.article_number,
                text=c.text,
                score=scores[cid],
            )
        )
    merged.sort(key=lambda c: c.score, reverse=True)
    return merged


# ---------------------------------------------------------------------------
# Adaptive reranking helpers
# ---------------------------------------------------------------------------

_ARTICLE_REF_RE = re.compile(r"\bالمادة\s+(\d+)")


def _should_skip_rerank(
    citations: list,
    question: str,
    law_type_filter: str | None,
) -> tuple[bool, str]:
    """Conservative reranker skip decision derived from benchmark data.

    Benchmark (adaptive_rerank_bench.py, 2026-08-16):
    - Reranker changes top-1 in 66% of queries (8/12).
    - Score margin (RRF weights ~0.016) has NO clean separation between
      changed / unchanged — cannot be used as a skip threshold.
    - Only safe skip signal: query explicitly references 'المادة X' AND
      raw top-1 IS article X in the confirmed domain with non-zero margin.
    - Corpus-miss never triggers this rule (no article ref in query).

    Returns
    -------
    (should_skip, reason)
    """
    if len(citations) < 2:
        return False, "too_few_candidates"

    # Only skip if query explicitly names a specific article number.
    m = _ARTICLE_REF_RE.search(question)
    if m is None:
        return False, "no_article_ref"

    article_ref = m.group(1).strip()

    # Raw top-1 must be that exact article.
    top1_art = str(citations[0].article_number or "").strip()
    if top1_art != article_ref:
        return False, "article_ref_not_top1"

    # When a domain filter is active, the top-1 must belong to that domain.
    # (Prevents e.g. child-law art.69 matching a labor-law query.)
    if law_type_filter:
        top1_law_type = getattr(citations[0], "law_type", None)
        if top1_law_type != law_type_filter:
            return False, "domain_mismatch"

    # Benchmark: margin == 0 indicates perfectly tied candidates (ambiguous).
    # Never skip when there is no score separation.
    margin = citations[0].score - citations[1].score
    if margin <= 0:
        return False, "zero_margin_ambiguous"

    return True, "article_ref_matched_high_confidence"


@trace_node("retrieve")
def retrieve_node(state: LegalAssistantState) -> LegalAssistantState:
    import torch
    # Ensure all CPU cores used — 9% embed speedup measured.
    import os as _os
    torch.set_num_threads(_os.cpu_count() or 4)

    embedder = get_embedding_service()
    retriever = get_retrieval_service()
    reranker = get_reranker_service()

    question = state["question"]

    # --- Always embed the original query ---
    original_vector = embedder.embed_query(question)

    # --- Dual-vector strategy: use BOTH HyDE + original ---
    # HyDE alone can drift semantically away from the indexed legal vocabulary.
    # By searching with the original query vector as well and RRF-merging results,
    # we ensure relevant chunks are never missed solely due to HyDE drift.
    hyde_vector = state.get("hyde_vector")

    # NOTE: top_k=8 here — retrieval_service internally always fetches
    # candidate_limit=max(top_k, 20)=20 from Qdrant (recall preserved).
    # Only the reranker input shrinks: 8 pairs → ~14,400ms vs 20 pairs → ~43,200ms.
    _RERANKER_CANDIDATES = 8

    if hyde_vector:
        logger.info(
            "retrieval_dual_vector_search",
            extra={"extra_fields": {
                "hyde_doc_preview": (state.get("hyde_document") or "")[:120],
            }},
        )
        # Search with HyDE vector
        hyde_results = retriever.search(
            query_vector=hyde_vector,
            query_text=question,
            category=state.get("category_filter"),
            law_type=state.get("law_type_filter"),
            top_k=_RERANKER_CANDIDATES,
            score_threshold=settings.RETRIEVAL_SCORE_THRESHOLD,
        )
        # Search with original query vector (no BM25 double-count — query_text=None)
        original_results = retriever.search(
            query_vector=original_vector,
            query_text=None,
            category=state.get("category_filter"),
            law_type=state.get("law_type_filter"),
            top_k=_RERANKER_CANDIDATES,
            score_threshold=settings.RETRIEVAL_SCORE_THRESHOLD,
        )
        # Capture the best original similarity score BEFORE RRF destroys it.
        # score_from_citations() uses Citation.score as top1_dense_score; after
        # _rrf_merge those become RRF weights (~0.016) instead of cosine scores
        # (~0.30–1.0), which collapses confidence to near-zero for all dual-vector
        # requests regardless of actual retrieval quality.
        all_pre_rrf = hyde_results + original_results
        best_pre_rrf_score = max((c.score for c in all_pre_rrf), default=0.0)

        # Merge via RRF
        citations = _rrf_merge(hyde_results, original_results)
        logger.info(
            "retrieval_dual_vector_merged",
            extra={"extra_fields": {
                "hyde_count": len(hyde_results),
                "original_count": len(original_results),
                "merged_count": len(citations),
                "best_pre_rrf_score": round(best_pre_rrf_score, 4),
            }},
        )
    else:
        best_pre_rrf_score = None  # single-vector path: scores are real cosine values
        logger.info("retrieval_single_vector_original_query")
        citations = retriever.search(
            query_vector=original_vector,
            query_text=question,
            category=state.get("category_filter"),
            law_type=state.get("law_type_filter"),
            top_k=_RERANKER_CANDIDATES,
            score_threshold=settings.RETRIEVAL_SCORE_THRESHOLD,
        )

    # --- Diagnostic: log every candidate before reranking ---
    logger.info(
        "retrieval_candidates_before_rerank",
        extra={"extra_fields": {
            "num_candidates": len(citations),
            "law_type_filter": state.get("law_type_filter"),
            "score_threshold": settings.RETRIEVAL_SCORE_THRESHOLD,
            "candidates": [
                {
                    "chunk_id": c.chunk_id,
                    "law_name": c.law_name,
                    "article_number": c.article_number,
                    "score": round(c.score, 4),
                    "text_preview": c.text[:80],
                }
                for c in citations[:10]  # log top-10 only
            ],
        }},
    )

    # --- Adaptive reranking: skip when retrieval is clearly confident ---
    # Rule derived from benchmark data (2026-08-16):
    #   ONLY skip when query explicitly names an article AND raw top-1 IS
    #   that article in the confirmed domain with a non-zero score margin.
    #   Score margin alone is NOT a reliable signal (RRF weights have no
    #   clean separation across changed/unchanged queries).
    law_type_filter = state.get("law_type_filter")
    skip_rerank, skip_reason = _should_skip_rerank(
        citations, question, law_type_filter
    )
    top1_score = citations[0].score if citations else 0.0
    top2_score = citations[1].score if len(citations) >= 2 else 0.0
    logger.info(
        "reranker_decision",
        extra={"extra_fields": {
            "event": "reranker_decision",
            "reranker_used": not skip_rerank,
            "reason": skip_reason,
            "candidate_count": len(citations),
            "top1_score": round(top1_score, 5),
            "top2_score": round(top2_score, 5),
            "score_margin": round(top1_score - top2_score, 5),
            "question_preview": question[:80],
        }},
    )

    if skip_rerank:
        # Return top-N by raw RRF score — no cross-encoder overhead.
        reranked_citations = citations[: settings.RERANK_TOP_N]
    else:
        reranked_citations = reranker.rerank(
            query=question,
            citations=citations,
            top_n=settings.RERANK_TOP_N,
        )

    # --- Relevance guard: if top reranker score is below threshold,
    # retrieved articles are likely from a different domain (corpus miss).
    # Treat as empty instead of hallucinating from irrelevant context.
    # Threshold 0.85 measured: relevant queries score 0.96-0.99,
    # corpus-miss queries score 0.23-0.77. ─────────────────────────────
    # IMPORTANT: only apply when backend == "cross_encoder" — overlap-fallback
    # and test-mock scores are cosine-based (0.3-0.9 range) and NOT calibrated
    # against this threshold. MagicMock._backend != "cross_encoder" safely.
    rerank_threshold = settings.RERANK_RELEVANCE_THRESHOLD
    if (reranked_citations
            and rerank_threshold > 0
            and not skip_rerank                                          # guard only valid when CE ran
            and getattr(reranker, "_backend", None) == "cross_encoder"):

        max_rerank_score = max(c.score for c in reranked_citations)
        if max_rerank_score < rerank_threshold:
            logger.info(
                "retrieval_relevance_guard_triggered",
                extra={"extra_fields": {
                    "max_rerank_score": round(max_rerank_score, 4),
                    "threshold": rerank_threshold,
                    "question_preview": question[:80],
                }},
            )
            reranked_citations = []

    # --- Diagnostic: log reranked results ---
    logger.info(
        "retrieval_after_rerank",
        extra={"extra_fields": {
            "num_reranked": len(reranked_citations),
            "reranked": [
                {
                    "chunk_id": c.chunk_id,
                    "law_name": c.law_name,
                    "article_number": c.article_number,
                    "score": round(c.score, 4),
                }
                for c in reranked_citations
            ],
        }},
    )

    # --- Compute retrieval confidence after reranking ---
    # For dual-vector paths, use the best original cosine score (captured before
    # node-level RRF) as top1_dense_score instead of the corrupted RRF weight.
    domain_match = bool(state.get("law_type_filter"))
    if best_pre_rrf_score is not None and reranked_citations:
        from app.services.confidence_scorer import compute_confidence
        retrieval_confidence = compute_confidence(
            top1_dense_score=best_pre_rrf_score,
            num_docs=len(reranked_citations),
            domain_match=domain_match,
            top1_reranker_score=reranked_citations[0].score,  # reranker score is valid
        )
    else:
        retrieval_confidence = score_from_citations(
            reranked_citations, domain_match=domain_match
        )

    logger.info(
        "retrieval_completed",
        extra={"extra_fields": {
            "question_preview": question[:80],
            "num_raw_results": len(citations),
            "num_reranked_results": len(reranked_citations),
            "retrieval_confidence": round(retrieval_confidence, 4),
            "retrieval_empty": len(reranked_citations) == 0,
            "law_type_filter": state.get("law_type_filter"),
            "used_hyde": bool(hyde_vector),
        }},
    )

    return {
        **state,
        "citations": reranked_citations,
        "retrieval_empty": len(reranked_citations) == 0,
        "retrieval_confidence": retrieval_confidence,
    }
