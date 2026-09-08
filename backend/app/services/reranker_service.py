from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.chat import Citation
from app.services.bm25_service import tokenize_arabic

logger = get_logger("bayyinah.reranker")
settings = get_settings()


def _compute_overlap_score(query: str, doc_text: str) -> float:
    """Lightweight fallback scoring based on token overlap."""
    query_tokens = set(tokenize_arabic(query))
    if not query_tokens:
        return 0.0
    doc_tokens = set(tokenize_arabic(doc_text))
    overlap = query_tokens.intersection(doc_tokens)
    return len(overlap) / len(query_tokens)


class RerankerService:
    """Reranker service with a 3-tier fallback strategy:

    Tier 1: BAAI/bge-reranker-v2-m3 CrossEncoder (best ablation: Hit@1=11%, MRR=15.16%).
    Tier 2: Token-overlap based heuristic scoring.
    Tier 3: Graceful pass-through of original rankings.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._backend = "none"

    def warm_up(self) -> None:
        """Eagerly load the reranker model at startup to avoid cold-start latency
        on first rerank() call. Safe to call multiple times."""
        self._load()

    def _load(self):
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import CrossEncoder

            logger.info(
                "loading_reranker_model",
                extra={"extra_fields": {"model": self.model_name, "device": self.device}},
            )
            self._model = CrossEncoder(self.model_name, device=self.device, max_length=512)
            self._backend = "cross_encoder"
            logger.info(
                "reranker_backend_loaded",
                extra={"extra_fields": {"model": self.model_name}},
            )
        except Exception as e:
            logger.warning(
                "cross_encoder_load_failed",
                extra={"extra_fields": {"error": str(e), "using_fallback": "overlap"}},
            )
            self._model = None
            self._backend = "overlap"
        return self._model

    def rerank(self, query: str, citations: List[Citation], top_n: int = 5) -> List[Citation]:
        if not citations or not query:
            return []

        model = self._load()
        scored_citations: List[Citation] = []

        # Tier 1: Try Cross-Encoder Reranking
        if self._backend == "cross_encoder" and model is not None:
            try:
                pairs = [[query, c.text] for c in citations]
                # batch_size=1 measured fastest on CPU (9,098ms vs 12,669ms for
                # batch_size=32 with 8 pairs). CPU has no parallel batch benefit;
                # smaller batch_size reduces memory allocation overhead per pass.
                scores = model.predict(
                    pairs,
                    batch_size=1,
                    show_progress_bar=False,
                )
                for idx, score in enumerate(scores):
                    c = citations[idx]
                    scored_citations.append(
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
                            score=float(score),
                        )
                    )
            except Exception as e:
                logger.error(
                    "reranker_prediction_failed_falling_back",
                    extra={"extra_fields": {"error": str(e)}},
                )
                self._backend = "overlap"

        # Tier 2: Try Token Overlap Fallback
        if self._backend == "overlap" or not scored_citations:
            try:
                for c in citations:
                    score = _compute_overlap_score(query, c.text)
                    scored_citations.append(
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
                            score=score,
                        )
                    )
            except Exception as e:
                logger.error(
                    "reranker_overlap_fallback_failed",
                    extra={"extra_fields": {"error": str(e)}},
                )
                # Tier 3: Return original pass-through order up to top_n
                return citations[:top_n]

        # Sort by score descending and return top_n
        scored_citations.sort(key=lambda c: c.score, reverse=True)
        return scored_citations[:top_n]


@lru_cache
def get_reranker_service() -> RerankerService:
    return RerankerService(
        model_name="BAAI/bge-reranker-v2-m3",
        device=settings.EMBEDDING_DEVICE,
    )
