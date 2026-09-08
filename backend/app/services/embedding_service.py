from __future__ import annotations

from functools import lru_cache
from typing import List, Literal

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("bayyinah.embeddings")

settings = get_settings()

EmbedBackend = Literal["flag_embedding", "sentence_transformers", "hash_fallback"]


class EmbeddingService:
    """Wraps BAAI/bge-m3 via FlagEmbedding (preferred) or sentence-transformers.

    Loading strategy (in order):
      1. FlagEmbedding  — fastest, supports fp16, purpose-built for BGE-M3.
      2. sentence-transformers — standard fallback (requires >=3.0.0).
      3. _hash_embed — deterministic hash-based pseudo-embeddings used ONLY when
         both real model backends fail. These produce ZERO semantic similarity and
         make retrieval completely random. This fallback is intentionally loud in
         logs so it cannot be silently missed.

    Loaded lazily and cached as a singleton to avoid reloading the model on every
    request.
    """

    def __init__(self, model_name: str, device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._is_flag = False
        self._backend: EmbedBackend = "hash_fallback"

    def warm_up(self) -> None:
        """Eagerly load the embedding model at startup so the first request
        never pays the cold-start penalty. Safe to call multiple times."""
        self._load()

    def _load(self):
        if self._model is None:
            logger.info(
                "loading_embedding_model",
                extra={"extra_fields": {"model": self.model_name, "device": self.device}},
            )
            # --- Attempt 1: FlagEmbedding (BGEM3FlagModel) ---
            try:
                from FlagEmbedding import BGEM3FlagModel

                self._model = BGEM3FlagModel(
                    self.model_name, use_fp16=self.device != "cpu"
                )
                self._is_flag = True
                self._backend = "flag_embedding"
                logger.info(
                    "embedding_backend_loaded",
                    extra={"extra_fields": {"backend": "FlagEmbedding", "model": self.model_name}},
                )
                return self._model
            except Exception as e:
                logger.warning(
                    "flag_embedding_load_failed",
                    extra={"extra_fields": {"error": str(e), "trying_next": "sentence_transformers"}},
                )

            # --- Attempt 2: sentence-transformers (requires >=3.0.0) ---
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name, device=self.device)
                self._is_flag = False
                self._backend = "sentence_transformers"
                logger.info(
                    "embedding_backend_loaded",
                    extra={"extra_fields": {"backend": "sentence_transformers", "model": self.model_name}},
                )
                return self._model
            except Exception as e:
                logger.error(
                    "sentence_transformers_load_failed",
                    extra={"extra_fields": {"error": str(e), "using_fallback": "hash_embed"}},
                )

            # --- Attempt 3: hash-based fallback (SEMANTIC RETRIEVAL DISABLED) ---
            logger.critical(
                "EMBEDDING_FALLBACK_HASH_ACTIVE — All real embedding backends failed. "
                "Vector search is NOW RANDOM. Retrieval quality is 0%. "
                "Fix dependencies before going to production.",
                extra={"extra_fields": {"model": self.model_name}},
            )
            self._model = None
            self._is_flag = False
            self._backend = "hash_fallback"

        return self._model

    @property
    def backend(self) -> EmbedBackend:
        """Return which embedding backend is active. Load model if not yet loaded."""
        self._load()
        return self._backend

    @property
    def is_semantic(self) -> bool:
        """True if a real ML model is powering embeddings (not hash fallback)."""
        return self.backend in ("flag_embedding", "sentence_transformers")

    def embed_query(self, text: str) -> List[float]:
        model = self._load()
        if self._is_flag:
            output = model.encode(
                [text],
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )
            return output["dense_vecs"][0].tolist()
        else:
            if model is not None:
                vec = model.encode(text)
                return vec.tolist()
            # hash-based fallback — no semantic signal
            return self._hash_embed(text, settings.EMBEDDING_DIM)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        model = self._load()
        if self._is_flag:
            output = model.encode(
                texts,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )
            return [vec.tolist() for vec in output["dense_vecs"]]
        else:
            if model is not None:
                vecs = model.encode(texts)
                return [v.tolist() for v in vecs]
            return [self._hash_embed(t, settings.EMBEDDING_DIM) for t in texts]

    def _hash_embed(self, text: str, dim: int | None = None) -> List[float]:
        import hashlib
        import random

        if dim is None:
            dim = settings.EMBEDDING_DIM

        h = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(h, "big")
        rnd = random.Random(seed)
        return [rnd.random() for _ in range(dim)]


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(
        model_name=settings.EMBEDDING_MODEL, device=settings.EMBEDDING_DEVICE
    )
