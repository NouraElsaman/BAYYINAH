import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.graphs.legal_assistant.nodes_query_expansion import query_expansion_node
from app.core.config import get_settings

settings = get_settings()

@pytest.mark.asyncio
@patch("app.graphs.legal_assistant.nodes_query_expansion.get_llm_service")
@patch("app.graphs.legal_assistant.nodes_query_expansion.get_embedding_service")
async def test_query_expansion_node_success(mock_get_embedder, mock_get_llm):
    # Mock LLM response
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value="هذا نص مادة قانونية تجريبية.")
    mock_get_llm.return_value = mock_llm

    # Mock embedder response
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_get_embedder.return_value = mock_embedder

    state = {
        "question": "ما هي عقوبة السرقة؟",
        "warnings": []
    }

    result = await query_expansion_node(state)

    assert result["hyde_document"] == "هذا نص مادة قانونية تجريبية."
    assert result["hyde_vector"] == [0.1, 0.2, 0.3]
    assert result["rewritten_query"] == "ما هي عقوبة السرقة؟"
    mock_llm.generate.assert_called_once()
    mock_embedder.embed_query.assert_called_once_with("هذا نص مادة قانونية تجريبية.")

@pytest.mark.asyncio
@patch("app.graphs.legal_assistant.nodes_query_expansion.get_llm_service")
@patch("app.graphs.legal_assistant.nodes_query_expansion.get_embedding_service")
async def test_query_expansion_disabled(mock_get_embedder, mock_get_llm):
    original_enabled = settings.QUERY_EXPANSION_ENABLED
    settings.QUERY_EXPANSION_ENABLED = False
    try:
        state = {
            "question": "ما هي عقوبة السرقة؟",
            "warnings": []
        }
        result = await query_expansion_node(state)
        assert "hyde_document" not in result
        assert "hyde_vector" not in result
    finally:
        settings.QUERY_EXPANSION_ENABLED = original_enabled
