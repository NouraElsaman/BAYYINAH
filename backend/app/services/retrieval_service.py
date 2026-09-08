from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.chat import Citation

logger = get_logger("bayyinah.retrieval")
settings = get_settings()


class RetrievalService:
    def __init__(self, url: str, api_key: Optional[str], collection: str):
        self.collection = collection
        self._qdrant_available = False
        try:
            self.client = QdrantClient(url=url, api_key=api_key)
            # Test connection
            self.client.get_collections()
            self._qdrant_available = True
            logger.info("qdrant_connected", extra={"extra_fields": {"url": url}})
        except Exception as e:
            logger.warning(
                "qdrant_connection_failed",
                extra={"extra_fields": {"url": url, "error": str(e), "using_fallback": True}}
            )
            self.client = None
            self._qdrant_available = False

    def _build_filter(self, category: Optional[str], law_type: Optional[str]) -> Optional[qmodels.Filter]:
        """Build a Qdrant filter from domain hints.

        NOTE (2026-06-20 payload audit):
          • law_type is stored as a plain string ('civil', 'family', 'labor', …) → filterable.
          • category is stored as a stringified Python list e.g. "['الاحوال الشخصية']"
            which CANNOT be matched by MatchValue — we intentionally ignore it here.

        NOTE (2026-08-16 Saudi law audit):
          • Corpus contains Saudi law articles (law_name="قانون العمل السعودي",
            law_type="labor" — same type as Egyptian labor law).
          • must_not filter on law_name MatchText("سعودي") permanently excludes them.
          • Benchmark confirmed Saudi article 87 was ranked Top-1 for Egyptian labor
            queries by a lighter reranker — exclusion at retrieval time is safer.
        """
        must: List[qmodels.FieldCondition] = []
        # category is NOT filterable in this corpus (stringified list) — skip it.
        if law_type:
            must.append(
                qmodels.FieldCondition(key="law_type", match=qmodels.MatchValue(value=law_type))
            )

        # Always exclude Saudi law — not relevant to Egyptian legal assistant.
        # Use MatchAny (not MatchText — MatchText requires a full-text index).
        # Exact law_name value confirmed in benchmark: "قانون العمل السعودي".
        must_not: List[qmodels.FieldCondition] = [
            qmodels.FieldCondition(
                key="law_name",
                match=qmodels.MatchAny(any=["قانون العمل السعودي"]),
            )
        ]

        if not must:
            return qmodels.Filter(must_not=must_not)
        return qmodels.Filter(must=must, must_not=must_not)


    @staticmethod
    def _reciprocal_rank_fusion(
        dense_results: List[Citation],
        sparse_results: List[Citation],
        k: int = 60,
    ) -> List[Citation]:
        """Combine dense and sparse search results using Reciprocal Rank Fusion (RRF)."""
        scores: dict[str, float] = {}
        doc_map: dict[str, Citation] = {}

        for rank, c in enumerate(dense_results, 1):
            chunk_id = c.chunk_id
            doc_map[chunk_id] = c
            scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank))

        for rank, c in enumerate(sparse_results, 1):
            chunk_id = c.chunk_id
            if chunk_id not in doc_map:
                doc_map[chunk_id] = c
            scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank))

        fused_citations = []
        for chunk_id, score in scores.items():
            c = doc_map[chunk_id]
            fused_citations.append(
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
        fused_citations.sort(key=lambda c: c.score, reverse=True)
        return fused_citations

    def search(
        self,
        query_vector: List[float],
        query_text: Optional[str] = None,
        category: Optional[str] = None,
        law_type: Optional[str] = None,
        top_k: int = 8,
        score_threshold: float = 0.45,
    ) -> List[Citation]:
        if not self._qdrant_available:
            logger.warning("qdrant_unavailable_using_fallback_citations")
            return self._fallback_citations()
        
        try:
            query_filter = self._build_filter(category, law_type)
            candidate_limit = max(top_k, 20)

            # 1. Search with filter (if any) and strict threshold
            results = self.client.query_points(
                collection_name=self.collection,
                query=query_vector,
                query_filter=query_filter,
                limit=candidate_limit,
                score_threshold=score_threshold,
                using="dense",
                with_payload=True,
            ).points

            # 2. Fallback 1: keep filter but lower score threshold
            if not results and query_filter is not None:
                logger.info("retrieval_fallback_lower_threshold_with_filter", extra={"extra_fields": {"category": category}})
                results = self.client.query_points(
                    collection_name=self.collection,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=candidate_limit,
                    score_threshold=max(score_threshold - 0.20, 0.20),
                    using="dense",
                    with_payload=True,
                ).points

            # 3. Fallback 2: drop filter completely and use relaxed threshold
            if not results:
                logger.info("retrieval_fallback_unfiltered_relaxed", extra={"extra_fields": {"had_filter": query_filter is not None}})
                results = self.client.query_points(
                    collection_name=self.collection,
                    query=query_vector,
                    limit=candidate_limit,
                    score_threshold=max(score_threshold - 0.20, 0.20),
                    using="dense",
                    with_payload=True,
                ).points

            dense_citations = self._to_citations(results)

            if query_text:
                from app.services.bm25_service import get_bm25_service
                bm25_service = get_bm25_service()
                
                sparse_citations = bm25_service.search(
                    query=query_text,
                    law_type=law_type,
                    top_k=candidate_limit,
                )
                
                citations = self._reciprocal_rank_fusion(dense_citations, sparse_citations)
            else:
                citations = dense_citations

            deduplicated = self._deduplicate(citations)
            return deduplicated[:top_k]
        except Exception as e:
            logger.error("qdrant_search_failed", extra={"extra_fields": {"error": str(e)}})
            return self._fallback_citations()

    @staticmethod
    def _to_citations(points: List[Any]) -> List[Citation]:
        citations = []
        for p in points:
            payload: Dict[str, Any] = p.payload or {}
            citations.append(
                Citation(
                    chunk_id=str(payload.get("chunk_id", p.id)),
                    doc_id=str(payload.get("doc_id", "")),
                    law_name=str(payload.get("law_name", "")),
                    law_number=str(payload.get("law_number")) if payload.get("law_number") else None,
                    law_year=str(payload.get("law_year")) if payload.get("law_year") else None,
                    law_type=payload.get("law_type"),
                    category=payload.get("category"),
                    article_number=str(payload.get("article_number")) if payload.get("article_number") else None,
                    text=str(payload.get("text", "")),
                    score=float(p.score),
                )
            )
        return citations

    @staticmethod
    def _deduplicate(citations: List[Citation]) -> List[Citation]:
        """Dedup by (law_name, article_number); keep highest scoring chunk."""
        seen: Dict[tuple, Citation] = {}
        for c in citations:
            key = (c.law_name, c.article_number, c.law_number)
            existing = seen.get(key)
            if existing is None or c.score > existing.score:
                seen[key] = c
        # Preserve descending score order
        return sorted(seen.values(), key=lambda c: c.score, reverse=True)

    @staticmethod
    def _fallback_citations() -> List[Citation]:
        """Return empty list when Qdrant is unavailable.

        Previously returned hardcoded mock articles, but that caused the LLM to
        receive completely wrong domain citations as "legal context" — producing
        confused or incorrect answers for every question.

        Returning [] ensures retrieval_empty=True → the API uses SYSTEM_PROMPT_GENERAL
        which clearly warns the user that the answer is general knowledge only.
        """
        logger.warning("qdrant_unavailable_returning_empty_citations")
        return []


@lru_cache
def get_retrieval_service() -> RetrievalService:
    return RetrievalService(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
        collection=settings.QDRANT_COLLECTION,
    )
