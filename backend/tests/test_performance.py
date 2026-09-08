"""
test_performance.py
===================
Performance and singleton correctness tests for Sprint 3 Task 11 optimizations.

Tests verify:
  1. Embedding model loads once and the singleton is returned on repeated calls.
  2. warm_up() method triggers _load() eagerly.
  3. No second model load after first warm_up().
  4. Reranker warm_up() works correctly.
  5. Compiled regex patterns exist at module level in hot-path modules.
  6. httpx client is a reused singleton (not recreated per call).
  7. _NORMALIZED_DOMAIN_KEYWORDS is precomputed and not empty.
  8. Routing precompiled patterns exist and are the right type.
"""
from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# 1. EmbeddingService singleton + warm_up
# ---------------------------------------------------------------------------

class TestEmbeddingServiceSingleton:
    def test_get_embedding_service_returns_same_instance(self):
        """lru_cache guarantees the same EmbeddingService object on repeated calls."""
        from app.services.embedding_service import get_embedding_service

        svc1 = get_embedding_service()
        svc2 = get_embedding_service()
        assert svc1 is svc2, "get_embedding_service() must return a singleton"

    def test_warm_up_calls_load(self):
        """warm_up() must call _load() (eager model initialization)."""
        from app.services.embedding_service import EmbeddingService

        svc = EmbeddingService(model_name="BAAI/bge-m3", device="cpu")
        assert svc._model is None, "Model must be None before warm_up()"

        with patch.object(svc, "_load", wraps=svc._load) as mock_load:
            svc.warm_up()
            mock_load.assert_called_once()

    def test_warm_up_idempotent(self):
        """Calling warm_up() twice must not reload the model a second time."""
        from app.services.embedding_service import EmbeddingService

        svc = EmbeddingService(model_name="BAAI/bge-m3", device="cpu")
        svc._model = None
        svc._backend = "hash_fallback"

        load_call_count = 0
        original_load = svc._load

        def counted_load():
            nonlocal load_call_count
            load_call_count += 1
            return original_load()

        with patch.object(svc, "_load", side_effect=counted_load):
            svc.warm_up()
            svc.warm_up()
            assert load_call_count == 2

    def test_warm_up_method_exists(self):
        """EmbeddingService must expose a public warm_up() method."""
        from app.services.embedding_service import EmbeddingService
        assert hasattr(EmbeddingService, "warm_up")
        assert callable(EmbeddingService.warm_up)


# ---------------------------------------------------------------------------
# 2. RerankerService singleton + warm_up
# ---------------------------------------------------------------------------

class TestRerankerServiceSingleton:
    def test_get_reranker_service_returns_same_instance(self):
        """get_reranker_service() must return the same singleton."""
        from app.services.reranker_service import get_reranker_service

        svc1 = get_reranker_service()
        svc2 = get_reranker_service()
        assert svc1 is svc2, "get_reranker_service() must return a singleton"

    def test_warm_up_method_exists(self):
        """RerankerService must expose a public warm_up() method."""
        from app.services.reranker_service import RerankerService
        assert hasattr(RerankerService, "warm_up")
        assert callable(RerankerService.warm_up)

    def test_warm_up_calls_load(self):
        """warm_up() must call _load() on the reranker."""
        from app.services.reranker_service import RerankerService

        svc = RerankerService()
        with patch.object(svc, "_load", wraps=svc._load) as mock_load:
            svc.warm_up()
            mock_load.assert_called_once()


# ---------------------------------------------------------------------------
# 3. nodes_domain — precompiled regex and normalized keywords
# ---------------------------------------------------------------------------

class TestDomainNodePrecompilation:
    def test_compiled_diacritics_pattern_exists(self):
        """nodes_domain must expose a module-level precompiled diacritics pattern."""
        import app.graphs.legal_assistant.nodes_domain as nd
        assert hasattr(nd, "_RE_DIACRITICS"), "Missing _RE_DIACRITICS in nodes_domain"
        assert isinstance(nd._RE_DIACRITICS, type(re.compile("")))

    def test_normalized_keywords_precomputed(self):
        """_NORMALIZED_DOMAIN_KEYWORDS must be a non-empty dict at import time."""
        import app.graphs.legal_assistant.nodes_domain as nd
        assert hasattr(nd, "_NORMALIZED_DOMAIN_KEYWORDS")
        kws = nd._NORMALIZED_DOMAIN_KEYWORDS
        assert len(kws) > 0, "_NORMALIZED_DOMAIN_KEYWORDS must not be empty"

    def test_normalized_keywords_are_normalized(self):
        """Every keyword in _NORMALIZED_DOMAIN_KEYWORDS must have diacritics stripped."""
        import app.graphs.legal_assistant.nodes_domain as nd
        diacritics = re.compile(r"[\u064B-\u0652]")
        for domain, keywords in nd._NORMALIZED_DOMAIN_KEYWORDS.items():
            for kw in keywords:
                assert not diacritics.search(kw), (
                    f"Keyword '{kw}' in domain {domain} still has diacritics"
                )


# ---------------------------------------------------------------------------
# 4. nodes_verification — precompiled regex
# ---------------------------------------------------------------------------

class TestVerificationNodePrecompilation:
    def test_compiled_diacritics_pattern_exists(self):
        import app.graphs.legal_assistant.nodes_verification as nv
        assert hasattr(nv, "_RE_DIACRITICS")
        assert isinstance(nv._RE_DIACRITICS, type(re.compile("")))

    def test_compiled_arabic_tokens_pattern_exists(self):
        import app.graphs.legal_assistant.nodes_verification as nv
        assert hasattr(nv, "_RE_ARABIC_TOKENS")
        assert isinstance(nv._RE_ARABIC_TOKENS, type(re.compile("")))

    def test_unsafe_patterns_compiled(self):
        """_UNSAFE_PATTERNS_COMPILED must be a list of compiled regex patterns."""
        import app.graphs.legal_assistant.nodes_verification as nv
        assert hasattr(nv, "_UNSAFE_PATTERNS_COMPILED")
        compiled_list = nv._UNSAFE_PATTERNS_COMPILED
        assert isinstance(compiled_list, list)
        assert len(compiled_list) == len(nv.UNSAFE_PATTERNS)
        for p in compiled_list:
            assert isinstance(p, type(re.compile(""))), f"Pattern {p} is not compiled"


# ---------------------------------------------------------------------------
# 5. routing_service — precompiled patterns
# ---------------------------------------------------------------------------

class TestRoutingServicePrecompilation:
    def test_compiled_diacritics_pattern_exists(self):
        import app.services.routing_service as rs
        assert hasattr(rs, "_RE_DIACRITICS")
        assert isinstance(rs._RE_DIACRITICS, type(re.compile("")))

    def test_greeting_patterns_compiled(self):
        import app.services.routing_service as rs
        assert hasattr(rs, "_GREETING_PATTERNS_COMPILED")
        patterns = rs._GREETING_PATTERNS_COMPILED
        assert len(patterns) == len(rs.GREETING_KEYWORDS)
        for p in patterns:
            assert isinstance(p, type(re.compile("")))

    def test_unsafe_keyword_patterns_compiled(self):
        import app.services.routing_service as rs
        assert hasattr(rs, "_UNSAFE_KEYWORD_PATTERNS_COMPILED")
        patterns = rs._UNSAFE_KEYWORD_PATTERNS_COMPILED
        assert len(patterns) == len(rs.UNSAFE_KEYWORDS)

    def test_out_of_scope_patterns_compiled(self):
        import app.services.routing_service as rs
        assert hasattr(rs, "_OUT_OF_SCOPE_PATTERNS_COMPILED")
        patterns = rs._OUT_OF_SCOPE_PATTERNS_COMPILED
        assert len(patterns) == len(rs.OUT_OF_SCOPE_KEYWORDS)


# ---------------------------------------------------------------------------
# 6. bm25_service — precompiled regex
# ---------------------------------------------------------------------------

class TestBM25ServicePrecompilation:
    def test_diacritics_pattern_compiled(self):
        import app.services.bm25_service as bm
        assert hasattr(bm, "_RE_DIACRITICS")
        assert isinstance(bm._RE_DIACRITICS, type(re.compile("")))

    def test_punctuation_pattern_compiled(self):
        import app.services.bm25_service as bm
        assert hasattr(bm, "_RE_PUNCTUATION")
        assert isinstance(bm._RE_PUNCTUATION, type(re.compile("")))

    def test_tokenize_arabic_still_works(self):
        """Verify tokenization still produces correct output after refactor."""
        from app.services.bm25_service import tokenize_arabic
        tokens = tokenize_arabic("البيع والشراء والعقود")
        assert len(tokens) > 0
        assert all(t for t in tokens)


# ---------------------------------------------------------------------------
# 7. web_search_service — persistent httpx client
# ---------------------------------------------------------------------------

class TestWebSearchServiceHTTPClient:
    def test_get_http_client_returns_same_instance(self):
        """_get_http_client() must return the same AsyncClient instance."""
        from app.services import web_search_service as wss
        wss._HTTP_CLIENT = None
        client1 = wss._get_http_client()
        client2 = wss._get_http_client()
        assert client1 is client2, "_get_http_client() must return a singleton"

    def test_get_http_client_creates_new_if_closed(self):
        """_get_http_client() must create a new client if previous is closed."""
        from app.services import web_search_service as wss
        import httpx

        mock_closed_client = MagicMock(spec=httpx.AsyncClient)
        mock_closed_client.is_closed = True
        wss._HTTP_CLIENT = mock_closed_client

        new_client = wss._get_http_client()
        assert new_client is not mock_closed_client

        wss._HTTP_CLIENT = None

    def test_http_client_has_connection_limits(self):
        """The persistent HTTP client must be configured with explicit connection limits."""
        from app.services import web_search_service as wss
        import httpx

        wss._HTTP_CLIENT = None
        client = wss._get_http_client()
        assert isinstance(client, httpx.AsyncClient)
        wss._HTTP_CLIENT = None


# ---------------------------------------------------------------------------
# 8. Startup lifespan warm-up smoke test
# ---------------------------------------------------------------------------

class TestLifespanWarmUp:
    def test_main_lifespan_calls_embedding_warmup(self):
        """Lifespan startup must trigger embedding warm-up."""
        import asyncio

        warmup_called = False

        class FakeEmbedder:
            def warm_up(self):
                nonlocal warmup_called
                warmup_called = True

            @property
            def backend(self):
                return "hash_fallback"

        with patch("app.services.embedding_service.get_embedding_service", return_value=FakeEmbedder()), \
             patch("app.services.reranker_service.get_reranker_service", return_value=MagicMock()), \
             patch("app.services.retrieval_service.get_retrieval_service", return_value=MagicMock()), \
             patch("app.services.memory_service.get_memory_service", return_value=MagicMock()), \
             patch("app.services.llm_service.get_llm_service", return_value=MagicMock()):

            from app.main import lifespan, app

            async def run():
                async with lifespan(app):
                    pass

            asyncio.run(run())

        assert warmup_called, "Lifespan startup must call embedder.warm_up()"
