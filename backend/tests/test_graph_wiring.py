"""
test_graph_wiring.py
====================
Smoke tests verifying that the compiled LangGraph executes nodes in the
correct order after Sprint 3 Phase 2 Task 8 (Answer Synthesis Agent wired in).

Expected order (high confidence path):
  detect_domain â†’ query_expansion â†’ retrieve â†’ answer_synthesis â†’ cite â†’ generate_answer â†’ verify

Expected order (low confidence path):
  detect_domain â†’ query_expansion â†’ retrieve â†’ web_search â†’ answer_synthesis â†’ cite â†’ generate_answer â†’ verify
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock, AsyncMock

import pytest

# Workaround for langchain-core globals AttributeError on minimal installations
try:
    import langchain
    if not hasattr(langchain, "debug"):
        langchain.debug = False
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Helper: build a minimal valid state that survives every node mock
# ---------------------------------------------------------------------------

def _base_state():
    return {
        "question": "Ù‡Ù„ ÙŠØ¬ÙˆØ² ÙØµÙ„ Ø§Ù„Ø¹Ø§Ù…Ù„ Ø¨Ø¯ÙˆÙ† Ø³Ø¨Ø¨ ÙˆÙÙ‚Ù‹Ø§ Ù„Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ Ø§Ù„Ù…ØµØ±ÙŠØŸ",
        "conversation_id": "test-conv-1",
        "request_id": "req-001",
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Smoke test: compile succeeds
# ---------------------------------------------------------------------------

def test_graph_compiles_successfully():
    """build_legal_assistant_graph() must compile without raising."""
    from app.graphs.legal_assistant.graph import build_legal_assistant_graph
    graph = build_legal_assistant_graph()
    assert graph is not None


# ---------------------------------------------------------------------------
# Smoke test: high confidence node execution order
# ---------------------------------------------------------------------------

async def test_retrieve_synthesis_cite_generate_order_high_confidence():
    """
    Verify that when retrieval_confidence is high, execution routes:
    retrieve â†’ answer_synthesis â†’ cite â†’ generate_answer
    """
    call_log: list[str] = []

    def _sync_sentinel(name: str):
        def _node(state):
            call_log.append(name)
            return state
        return _node

    async def _async_sentinel(name: str):
        call_log.append(name)
        return {"citations": []}

    async def query_expansion_sentinel(state):
        call_log.append("query_expansion")
        return state

    async def generate_answer_sentinel(state):
        call_log.append("generate_answer")
        return state

    async def web_search_sentinel(state):
        call_log.append("web_search")
        return state

    patches = [
        patch(
            "app.graphs.legal_assistant.nodes_domain.detect_domain_node",
            side_effect=_sync_sentinel("detect_domain"),
        ),
        patch(
            "app.graphs.legal_assistant.nodes_query_expansion.query_expansion_node",
            side_effect=query_expansion_sentinel,
        ),
        patch(
            "app.graphs.legal_assistant.nodes_retrieval.retrieve_node",
            side_effect=_sync_sentinel("retrieve"),
        ),
        patch(
            "app.graphs.legal_assistant.nodes_web_search.web_search_node",
            side_effect=web_search_sentinel,
        ),
        patch(
            "app.graphs.legal_assistant.nodes_answer_synthesis.answer_synthesis_node",
            side_effect=_sync_sentinel("answer_synthesis"),
        ),
        patch(
            "app.graphs.legal_assistant.nodes_citation.citation_node",
            side_effect=_sync_sentinel("cite"),
        ),
        patch(
            "app.graphs.legal_assistant.nodes_generation.generate_answer_node",
            side_effect=generate_answer_sentinel,
        ),
        patch(
            "app.graphs.legal_assistant.nodes_verification.verify_node",
            side_effect=_sync_sentinel("verify"),
        ),
    ]

    for p in patches:
        p.start()

    try:
        from app.graphs.legal_assistant import graph as graph_module
        import importlib
        importlib.reload(graph_module)
        compiled = graph_module.build_legal_assistant_graph()

        # Run with high confidence -> should route straight to synthesis (skipping web)
        state_high = _base_state()
        state_high["retrieval_confidence"] = 0.90
        await compiled.ainvoke(state_high)
    finally:
        for p in patches:
            p.stop()

    # Verify high confidence execution sequence
    assert "retrieve" in call_log
    assert "answer_synthesis" in call_log
    assert "cite" in call_log
    assert "generate_answer" in call_log
    assert "web_search" not in call_log

    retrieve_idx = call_log.index("retrieve")
    synthesis_idx = call_log.index("answer_synthesis")
    cite_idx = call_log.index("cite")
    generate_idx = call_log.index("generate_answer")

    assert retrieve_idx < synthesis_idx
    assert synthesis_idx < cite_idx
    assert cite_idx < generate_idx


# ---------------------------------------------------------------------------
# Smoke test: low confidence node execution order
# ---------------------------------------------------------------------------

async def test_low_confidence_routes_through_web_search():
    """Verify that when retrieval_confidence is low, graph routes:
    retrieve â†’ web_search â†’ answer_synthesis â†’ cite â†’ generate_answer
    """
    call_log: list[str] = []

    def _sync_sentinel(name: str):
        def _node(state):
            call_log.append(name)
            return state
        return _node

    async def query_expansion_sentinel(state):
        call_log.append("query_expansion")
        return state

    async def generate_answer_sentinel(state):
        call_log.append("generate_answer")
        return state

    async def web_search_sentinel(state):
        call_log.append("web_search")
        return state

    patches = [
        patch(
            "app.graphs.legal_assistant.nodes_domain.detect_domain_node",
            side_effect=_sync_sentinel("detect_domain"),
        ),
        patch(
            "app.graphs.legal_assistant.nodes_query_expansion.query_expansion_node",
            side_effect=query_expansion_sentinel,
        ),
        patch(
            "app.graphs.legal_assistant.nodes_retrieval.retrieve_node",
            side_effect=_sync_sentinel("retrieve"),
        ),
        patch(
            "app.graphs.legal_assistant.nodes_web_search.web_search_node",
            side_effect=web_search_sentinel,
        ),
        patch(
            "app.graphs.legal_assistant.nodes_answer_synthesis.answer_synthesis_node",
            side_effect=_sync_sentinel("answer_synthesis"),
        ),
        patch(
            "app.graphs.legal_assistant.nodes_citation.citation_node",
            side_effect=_sync_sentinel("cite"),
        ),
        patch(
            "app.graphs.legal_assistant.nodes_generation.generate_answer_node",
            side_effect=generate_answer_sentinel,
        ),
        patch(
            "app.graphs.legal_assistant.nodes_verification.verify_node",
            side_effect=_sync_sentinel("verify"),
        ),
    ]

    for p in patches:
        p.start()

    try:
        from app.graphs.legal_assistant import graph as graph_module
        import importlib
        importlib.reload(graph_module)
        compiled = graph_module.build_legal_assistant_graph()

        # Run with low confidence -> should route retrieve -> web_search -> answer_synthesis
        state_low = _base_state()
        state_low["retrieval_confidence"] = 0.10
        await compiled.ainvoke(state_low)
    finally:
        for p in patches:
            p.stop()

    # Verify low confidence execution sequence
    assert "retrieve" in call_log
    assert "web_search" in call_log
    assert "answer_synthesis" in call_log
    assert "cite" in call_log
    assert "generate_answer" in call_log

    retrieve_idx = call_log.index("retrieve")
    web_search_idx = call_log.index("web_search")
    synthesis_idx = call_log.index("answer_synthesis")
    cite_idx = call_log.index("cite")
    generate_idx = call_log.index("generate_answer")

    assert retrieve_idx < web_search_idx
    assert web_search_idx < synthesis_idx
    assert synthesis_idx < cite_idx
    assert cite_idx < generate_idx


# ---------------------------------------------------------------------------
# Smoke test: full registered node list
# ---------------------------------------------------------------------------

def test_graph_contains_cite_node():
    """The compiled graph must include the answer_synthesis and other nodes."""
    from app.graphs.legal_assistant.graph import build_legal_assistant_graph
    graph = build_legal_assistant_graph()
    node_names = set(graph.nodes)
    assert "cite" in node_names
    assert "web_search" in node_names
    assert "answer_synthesis" in node_names
    assert "retrieve" in node_names
    assert "generate_answer" in node_names
    assert "verify" in node_names
