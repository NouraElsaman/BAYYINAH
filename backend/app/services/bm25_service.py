from __future__ import annotations

import re
import threading
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from rank_bm25 import BM25Okapi

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.chat import Citation
from app.services.retrieval_service import get_retrieval_service

logger = get_logger("bayyinah.bm25")
settings = get_settings()

# ---------------------------------------------------------------------------
# Module-level compiled patterns (avoids per-call recompilation in tokenizer)
# ---------------------------------------------------------------------------
_RE_DIACRITICS = re.compile(r"[\u064B-\u0652]")
_RE_PUNCTUATION = re.compile(r"[^\w\s]")


def normalize_arabic_text(text: str) -> str:
    """Normalize Arabic text for keyword matching (BM25/Tokenization)."""
    if not text:
        return ""
    # Remove diacritics (harakat) — precompiled pattern
    text = _RE_DIACRITICS.sub("", text)
    # Remove tatweel (kashida)
    text = text.replace("\u0640", "")
    # Normalize alef variants to bare alef
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    # Normalize teh marbuta to heh
    text = text.replace("ة", "ه")
    # Normalize alef maksura to yeh
    text = text.replace("ى", "ي")
    # Lowercase (for any mixed English/numbers)
    text = text.lower()
    return text


def tokenize_arabic(text: str) -> List[str]:
    """Tokenize normalized Arabic text by removing punctuation and splitting by whitespace."""
    normalized = normalize_arabic_text(text)
    # Remove punctuation — precompiled pattern
    cleaned = _RE_PUNCTUATION.sub(" ", normalized)
    # Split and remove empty tokens
    tokens = [tok for tok in cleaned.split() if tok.strip()]
    return tokens


class BM25Service:
    def __init__(self, qdrant_url: str, qdrant_api_key: Optional[str], collection: str):
        self.qdrant_url = qdrant_url
        self.qdrant_api_key = qdrant_api_key
        self.collection = collection
        
        self.client: Optional[QdrantClient] = None
        self._qdrant_connected = False
        
        # Thread safety lock for lazy loading
        self._lock = threading.RLock()
        
        # In-memory indexes and citations caches by law_type (None key represents the global index)
        self._indexes: Dict[Optional[str], BM25Okapi] = {}
        self._citations: Dict[Optional[str], List[Citation]] = {}

    def _connect(self) -> None:
        if self._qdrant_connected:
            return
        with self._lock:
            if self._qdrant_connected:
                return
            try:
                self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
                self.client.get_collections()
                self._qdrant_connected = True
                logger.info("bm25_qdrant_connected")
            except Exception as e:
                logger.error("bm25_qdrant_connection_failed", extra={"extra_fields": {"error": str(e)}})
                self.client = None
                self._qdrant_connected = False

    def _load_domain_corpus(self, law_type: Optional[str]) -> Tuple[BM25Okapi, List[Citation]]:
        """Fetch all documents for the given law_type from Qdrant and build a BM25 index."""
        self._connect()
        if not self._qdrant_connected or not self.client:
            logger.warning("bm25_load_failed_qdrant_unavailable_using_fallback")
            # Fall back to empty index and empty citations
            empty_bm25 = BM25Okapi([["تجربة"]])
            return empty_bm25, []

        logger.info("bm25_loading_domain_corpus_start", extra={"extra_fields": {"law_type": law_type}})
        
        must_conditions = []
        if law_type:
            must_conditions.append(
                qmodels.FieldCondition(key="law_type", match=qmodels.MatchValue(value=law_type))
            )
            
        scroll_filter = qmodels.Filter(must=must_conditions) if must_conditions else None
        
        citations: List[Citation] = []
        next_page = None
        limit = 500
        
        t0 = threading.Event() # dummy
        import time
        start_time = time.perf_counter()

        while True:
            try:
                result = self.client.scroll(
                    collection_name=self.collection,
                    scroll_filter=scroll_filter,
                    limit=limit,
                    with_payload=True,
                    with_vectors=False,
                    offset=next_page,
                )
                points, next_page = result
                if not points:
                    break
                
                for p in points:
                    pay = p.payload or {}
                    citations.append(
                        Citation(
                            chunk_id=str(pay.get("chunk_id", p.id)),
                            doc_id=str(pay.get("doc_id", "")),
                            law_name=str(pay.get("law_name", "")),
                            law_number=str(pay.get("law_number")) if pay.get("law_number") else None,
                            law_year=str(pay.get("law_year")) if pay.get("law_year") else None,
                            law_type=pay.get("law_type"),
                            category=pay.get("category"),
                            article_number=str(pay.get("article_number")) if pay.get("article_number") else None,
                            text=str(pay.get("text", "")),
                            score=0.0,
                        )
                    )
                
                if not next_page:
                    break
            except Exception as e:
                logger.error("bm25_scroll_error", extra={"extra_fields": {"error": str(e)}})
                break

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "bm25_domain_corpus_loaded",
            extra={"extra_fields": {
                "law_type": law_type,
                "count": len(citations),
                "duration_ms": round(duration_ms, 2)
            }}
        )

        if not citations:
            empty_bm25 = BM25Okapi([["تجربة"]])
            return empty_bm25, []

        # Tokenize corpus for BM25
        tokenized_corpus = [tokenize_arabic(c.text) for c in citations]
        bm25 = BM25Okapi(tokenized_corpus)
        
        return bm25, citations

    def get_index(self, law_type: Optional[str]) -> Tuple[BM25Okapi, List[Citation]]:
        """Retrieve or build the BM25 index for the specified law_type."""
        if law_type in self._indexes:
            return self._indexes[law_type], self._citations[law_type]

        with self._lock:
            # Double-check locking pattern
            if law_type in self._indexes:
                return self._indexes[law_type], self._citations[law_type]

            bm25, citations = self._load_domain_corpus(law_type)
            self._indexes[law_type] = bm25
            self._citations[law_type] = citations
            return bm25, citations

    def search(self, query: str, law_type: Optional[str] = None, top_k: int = 20) -> List[Citation]:
        """Perform sparse BM25 query matching over the cached domain or whole corpus."""
        if not query:
            return []

        try:
            bm25, citations = self.get_index(law_type)
            if not citations:
                return []

            tokenized_query = tokenize_arabic(query)
            if not tokenized_query:
                return []

            # Calculate BM25 scores
            doc_scores = bm25.get_scores(tokenized_query)
            
            # Pair scores with original citations
            scored_citations = []
            for idx, score in enumerate(doc_scores):
                if score > 0.0:  # Only return documents with some query term overlap
                    cit = citations[idx]
                    # Create copy with updated score
                    scored_cit = Citation(
                        chunk_id=cit.chunk_id,
                        doc_id=cit.doc_id,
                        law_name=cit.law_name,
                        law_number=cit.law_number,
                        law_year=cit.law_year,
                        law_type=cit.law_type,
                        category=cit.category,
                        article_number=cit.article_number,
                        text=cit.text,
                        score=float(score),
                    )
                    scored_citations.append(scored_cit)

            # Sort by score descending and return top K
            scored_citations.sort(key=lambda c: c.score, reverse=True)
            return scored_citations[:top_k]
        except Exception as e:
            logger.error("bm25_search_failed", extra={"extra_fields": {"error": str(e)}})
            return []


@lru_cache
def get_bm25_service() -> BM25Service:
    return BM25Service(
        qdrant_url=settings.QDRANT_URL,
        qdrant_api_key=settings.QDRANT_API_KEY,
        collection=settings.QDRANT_COLLECTION,
    )
