"""
test_retrieval_node.py
======================
Unit tests for retrieve_node.

Sprint 3 Phase 2 additions:
  - confidence stored in returned state
  - empty retrieval returns confidence == 0.0
  - reranker output is unchanged by confidence scoring
  - existing retrieval behaviour remains identical
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import get_settings
from app.graphs.legal_assistant.nodes_retrieval import retrieve_node
from app.schemas.chat import Citation

_settings = get_settings()


# ---------------------------------------------------------------------------
# Fixture helper
# ---------------------------------------------------------------------------

def make_citation(text: str, score: float = 0.8) -> Citation:
    return Citation(
        chunk_id="c1",
        doc_id="d1",
        law_name="قانون العمل",
        law_number="12",
        law_year="2003",
        law_type="labor",
        category="labor_law",
        article_number="10",
        text=text,
        score=score,
    )


def _base_patches():
    """Return the three standard service patches."""
    return (
        patch("app.graphs.legal_assistant.nodes_retrieval.get_embedding_service"),
        patch("app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service"),
        patch("app.graphs.legal_assistant.nodes_retrieval.get_reranker_service"),
    )


# ===========================================================================
# Existing behaviour — HyDE vector path (unchanged)
# ===========================================================================

@patch("app.graphs.legal_assistant.nodes_retrieval.get_embedding_service")
@patch("app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service")
@patch("app.graphs.legal_assistant.nodes_retrieval.get_reranker_service")
def test_retrieve_node_uses_hyde_vector(mock_get_reranker, mock_get_retriever, mock_get_embedder):
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.9, 0.8, 0.7]  # original query embedding
    mock_get_embedder.return_value = mock_embedder

    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [make_citation("سياق تجريبي")]
    mock_get_retriever.return_value = mock_retriever

    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = [make_citation("سياق تجريبي reranked")]
    mock_get_reranker.return_value = mock_reranker

    state = {
        "question": "سؤال تجريبي؟",
        "hyde_vector": [0.1, 0.2, 0.3],
        "category_filter": None,
        "law_type_filter": None,
        "warnings": [],
    }

    result = retrieve_node(state)

    assert result["citations"] == [make_citation("سياق تجريبي reranked")]
    assert result["retrieval_empty"] is False

    # Dual-vector: embed_query IS called for original query (new behaviour)
    mock_embedder.embed_query.assert_called_once_with("سؤال تجريبي؟")

    # Dual-vector: retriever.search called TWICE — once with HyDE vector, once with original
    assert mock_retriever.search.call_count == 2

    # First call uses HyDE vector with BM25 text
    first_call_kwargs = mock_retriever.search.call_args_list[0].kwargs
    assert first_call_kwargs["query_vector"] == [0.1, 0.2, 0.3]
    assert first_call_kwargs["query_text"] == "سؤال تجريبي؟"
    assert first_call_kwargs["score_threshold"] == _settings.RETRIEVAL_SCORE_THRESHOLD

    # Second call uses original embedding vector, no BM25 text to avoid double-counting
    second_call_kwargs = mock_retriever.search.call_args_list[1].kwargs
    assert second_call_kwargs["query_vector"] == [0.9, 0.8, 0.7]
    assert second_call_kwargs["query_text"] is None
    assert second_call_kwargs["score_threshold"] == _settings.RETRIEVAL_SCORE_THRESHOLD



# ===========================================================================
# Existing behaviour — fallback embedding path (unchanged)
# ===========================================================================

@patch("app.graphs.legal_assistant.nodes_retrieval.get_embedding_service")
@patch("app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service")
@patch("app.graphs.legal_assistant.nodes_retrieval.get_reranker_service")
def test_retrieve_node_falls_back_without_hyde_vector(mock_get_reranker, mock_get_retriever, mock_get_embedder):
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.9, 0.8, 0.7]
    mock_get_embedder.return_value = mock_embedder

    mock_retriever = MagicMock()
    mock_retriever.search.return_value = []
    mock_get_retriever.return_value = mock_retriever

    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = []
    mock_get_reranker.return_value = mock_reranker

    state = {
        "question": "سؤال تجريبي بدون هايد؟",
        "category_filter": None,
        "law_type_filter": None,
        "warnings": [],
    }

    result = retrieve_node(state)

    assert result["citations"] == []
    assert result["retrieval_empty"] is True

    mock_embedder.embed_query.assert_called_once_with("سؤال تجريبي بدون هايد؟")
    mock_retriever.search.assert_called_once_with(
        query_vector=[0.9, 0.8, 0.7],
        query_text="سؤال تجريبي بدون هايد؟",
        category=None,
        law_type=None,
        top_k=8,  # updated: was 20, now 8 to reduce reranker input (67% latency saving)
        score_threshold=_settings.RETRIEVAL_SCORE_THRESHOLD,
    )


# ===========================================================================
# Phase 2: confidence stored in returned state
# ===========================================================================

@patch("app.graphs.legal_assistant.nodes_retrieval.get_embedding_service")
@patch("app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service")
@patch("app.graphs.legal_assistant.nodes_retrieval.get_reranker_service")
def test_retrieval_confidence_stored_in_state(mock_get_reranker, mock_get_retriever, mock_get_embedder):
    """retrieve_node must always write 'retrieval_confidence' into the returned state."""
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.5] * 10
    mock_get_embedder.return_value = mock_embedder

    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [make_citation("نص قانوني", score=0.75)]
    mock_get_retriever.return_value = mock_retriever

    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = [make_citation("نص قانوني reranked", score=0.75)]
    mock_get_reranker.return_value = mock_reranker

    state = {
        "question": "ما هو قانون العمل؟",
        "category_filter": None,
        "law_type_filter": None,
    }

    result = retrieve_node(state)

    assert "retrieval_confidence" in result, "retrieval_confidence must be present in returned state"
    confidence = result["retrieval_confidence"]
    assert isinstance(confidence, float), "retrieval_confidence must be a float"
    assert 0.0 <= confidence <= 1.0, f"confidence out of range: {confidence}"
    # With score=0.75 and 1 doc retrieved, confidence must be > 0
    assert confidence > 0.0


# ===========================================================================
# Phase 2: empty retrieval returns confidence == 0.0
# ===========================================================================

@patch("app.graphs.legal_assistant.nodes_retrieval.get_embedding_service")
@patch("app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service")
@patch("app.graphs.legal_assistant.nodes_retrieval.get_reranker_service")
def test_empty_retrieval_returns_zero_confidence(mock_get_reranker, mock_get_retriever, mock_get_embedder):
    """When no documents are retrieved, retrieval_confidence must be 0.0."""
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.5] * 10
    mock_get_embedder.return_value = mock_embedder

    mock_retriever = MagicMock()
    mock_retriever.search.return_value = []
    mock_get_retriever.return_value = mock_retriever

    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = []
    mock_get_reranker.return_value = mock_reranker

    state = {
        "question": "سؤال لا توجد له نتائج؟",
        "category_filter": None,
        "law_type_filter": None,
    }

    result = retrieve_node(state)

    assert result["retrieval_empty"] is True
    assert result["retrieval_confidence"] == 0.0


# ===========================================================================
# Phase 2: reranker output is unchanged by confidence scoring
# ===========================================================================

@patch("app.graphs.legal_assistant.nodes_retrieval.get_embedding_service")
@patch("app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service")
@patch("app.graphs.legal_assistant.nodes_retrieval.get_reranker_service")
def test_reranker_output_unchanged_by_confidence(mock_get_reranker, mock_get_retriever, mock_get_embedder):
    """Adding confidence scoring must not mutate the reranked citations list."""
    c1 = make_citation("أول نتيجة", score=0.9)
    c2 = make_citation("ثاني نتيجة", score=0.7)

    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1] * 5
    mock_get_embedder.return_value = mock_embedder

    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [c1, c2]
    mock_get_retriever.return_value = mock_retriever

    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = [c1, c2]
    mock_get_reranker.return_value = mock_reranker

    state = {
        "question": "سؤال قانوني؟",
        "category_filter": None,
        "law_type_filter": None,
    }

    result = retrieve_node(state)

    # Citations must be exactly what the reranker returned
    assert result["citations"] == [c1, c2]
    assert len(result["citations"]) == 2
    assert result["citations"][0].score == 0.9
    assert result["citations"][1].score == 0.7
    # Confidence added without touching citations
    assert "retrieval_confidence" in result


# ===========================================================================
# Phase 2: domain_match=True (law_type_filter set) raises confidence
# ===========================================================================

@patch("app.graphs.legal_assistant.nodes_retrieval.get_embedding_service")
@patch("app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service")
@patch("app.graphs.legal_assistant.nodes_retrieval.get_reranker_service")
def test_domain_match_increases_confidence(mock_get_reranker, mock_get_retriever, mock_get_embedder):
    """When law_type_filter is set (domain match), confidence must be higher than without it."""
    c = make_citation("نص", score=0.6)

    for svc in (mock_get_embedder, mock_get_retriever, mock_get_reranker):
        svc.return_value = MagicMock()
    mock_get_embedder.return_value.embed_query.return_value = [0.1] * 5
    mock_get_retriever.return_value.search.return_value = [c]
    mock_get_reranker.return_value.rerank.return_value = [c]

    state_no_domain = {
        "question": "سؤال؟",
        "category_filter": None,
        "law_type_filter": None,
    }
    state_with_domain = {
        "question": "سؤال؟",
        "category_filter": None,
        "law_type_filter": "labor",   # truthy → domain_match=True
    }

    result_no = retrieve_node(state_no_domain)
    result_yes = retrieve_node(state_with_domain)

    assert result_yes["retrieval_confidence"] > result_no["retrieval_confidence"]
