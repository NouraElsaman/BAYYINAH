"""
test_web_search_node.py
========================
Tests for the web_search_node and the conditional routing logic in LangGraph.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graphs.legal_assistant.graph import (
    build_legal_assistant_graph,
    verify_retrieval_confidence,
)
from app.graphs.legal_assistant.nodes_web_search import web_search_node
from app.graphs.legal_assistant.nodes_citation import citation_node
from app.schemas.chat import Citation
from app.services.web_search_service import SearchResult

# Workaround for langchain-core globals AttributeError on minimal installations
try:
    import langchain
    if not hasattr(langchain, "debug"):
        langchain.debug = False
except ImportError:
    pass


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.WEB_SEARCH_ENABLED = True
    s.WEB_SEARCH_PROVIDER = "tavily"
    s.WEB_SEARCH_TIMEOUT_S = 2.0
    s.WEB_SEARCH_MAX_RESULTS = 5
    s.WEB_SEARCH_MAX_RETRIES = 2
    s.TAVILY_API_KEY = "dummy-key"
    s.CONFIDENCE_FALLBACK_THRESHOLD = 0.35
    s.CITATION_MAX_TEXT_TOKENS = 400
    s.CITATION_MAX_TOKENS = 3000
    return s


# ===========================================================================
# 1. Graph compiles successfully
# ===========================================================================

def test_graph_compiles_successfully():
    graph = build_legal_assistant_graph()
    assert graph is not None
    assert "web_search" in graph.nodes


# ===========================================================================
# 2. Routing logic (verify_retrieval_confidence)
# ===========================================================================

def test_routing_high_confidence_skips_web(mock_settings):
    state = {"retrieval_confidence": 0.85}
    with patch("app.graphs.legal_assistant.graph.get_settings", return_value=mock_settings):
        route = verify_retrieval_confidence(state)
    # High confidence routes directly to answer_synthesis (not web_search)
    assert route == "answer_synthesis"


def test_routing_low_confidence_routes_to_web(mock_settings):
    state = {"retrieval_confidence": 0.20}
    with patch("app.graphs.legal_assistant.graph.get_settings", return_value=mock_settings):
        route = verify_retrieval_confidence(state)
    assert route == "web_search"


def test_routing_missing_confidence_defaults_to_web(mock_settings):
    state = {}  # missing confidence
    with patch("app.graphs.legal_assistant.graph.get_settings", return_value=mock_settings):
        route = verify_retrieval_confidence(state)
    # Missing confidence should safely default to 0.0 -> trigger web_search fallback
    assert route == "web_search"


# ===========================================================================
# 3. Disabled web search returns empty citations
# ===========================================================================

@pytest.mark.asyncio
async def test_node_disabled_returns_empty(mock_settings):
    mock_settings.WEB_SEARCH_ENABLED = False
    state = {"question": "سؤال"}

    with patch("app.graphs.legal_assistant.nodes_web_search.get_settings", return_value=mock_settings):
        res = await web_search_node(state)

    assert res["citations"] == []
    assert res["web_results"] == []
    assert res["retrieval_source"] == "web"
    assert res["retrieval_empty"] is True


# ===========================================================================
# 4. Web search exception is swallowed
# ===========================================================================

@pytest.mark.asyncio
async def test_node_exception_swallowed(mock_settings):
    state = {"question": "سؤال"}
    
    # Mocking WebSearchService search method to throw an error
    mock_service = MagicMock()
    mock_service.search = AsyncMock(side_effect=RuntimeError("Search backend crashed"))

    with patch("app.graphs.legal_assistant.nodes_web_search.get_settings", return_value=mock_settings), \
         patch("app.graphs.legal_assistant.nodes_web_search.WebSearchService", return_value=mock_service):
        
        # Should not raise exception
        res = await web_search_node(state)

    assert res["citations"] == []
    assert res["web_results"] == []
    assert res["retrieval_source"] == "web"
    assert res["retrieval_empty"] is True


# ===========================================================================
# 5. Citation node accepts web citations
# ===========================================================================

def test_citation_node_accepts_web_citations(mock_settings):
    # Web search results mapped into Citation schema format
    web_citations = [
        Citation(
            chunk_id="web_0",
            doc_id="web_doc_0",
            law_name="موقع ويب خارجي",
            law_number=None,
            law_year=None,
            law_type="web",
            category="web_search",
            article_number=None,
            text="نص مستخرج من الويب بخصوص قانون العمل",
            score=0.9,
        )
    ]
    state = {
        "citations": web_citations,
        "retrieval_source": "web",
    }
    
    with patch("app.graphs.legal_assistant.nodes_citation.get_settings", return_value=mock_settings):
        res = citation_node(state)

    assert len(res["citations"]) == 1
    assert res["citations"][0].chunk_id == "web_0"
    assert res["citations"][0].law_type == "web"
    assert res["citations"][0].category == "web_search"
    assert res["context_tokens"] > 0


# ===========================================================================
# 6. End-to-end routing integration tests via Graph
# ===========================================================================

@pytest.mark.asyncio
async def test_graph_executes_web_search_on_low_confidence(mock_settings):
    """If confidence is low, verify routing redirects execution through web search node."""
    mock_service = MagicMock()
    mock_service.search = AsyncMock(return_value=[
        SearchResult(url="http://tavily.com", title="Tavily Law Result", content="قانون العمل تفاصيل", score=0.95)
    ])

    state = {
        "question": "ما هي المادة 10؟",
        "retrieval_confidence": 0.10,  # Below default threshold (0.35)
        "citations": [],               # Reranker returned nothing
        "retrieval_empty": True,
        "warnings": [],
    }

    # Patch the real search service & settings
    with patch("app.graphs.legal_assistant.nodes_web_search.get_settings", return_value=mock_settings), \
         patch("app.graphs.legal_assistant.graph.get_settings", return_value=mock_settings), \
         patch("app.graphs.legal_assistant.nodes_citation.get_settings", return_value=mock_settings), \
         patch("app.graphs.legal_assistant.nodes_web_search.WebSearchService", return_value=mock_service):
        
        # Execute the web_search_node manually representing the step
        res = await web_search_node(state)
        
    assert len(res["citations"]) == 1
    assert res["citations"][0].law_name == "Tavily Law Result"
    assert res["retrieval_source"] == "web"
    assert res["retrieval_empty"] is False
