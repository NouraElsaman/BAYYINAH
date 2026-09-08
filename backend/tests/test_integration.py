"""
Integration tests — require no real external services because conftest
patches all external calls.  Mark as 'integration' so CI can optionally
skip them with -m 'not integration' if services are unavailable.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.schemas.chat import LegalDomain


@pytest.fixture
def client():
    # Prometheus registry singleton causes issues in repeated test runs;
    # reset by re-importing fresh.
    import importlib
    import app.api.system as sys_module
    importlib.reload(sys_module)

    from app.main import app
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    with patch("app.api.system.get_retrieval_service") as mock_r:
        mock_r.return_value.client.get_collections.return_value = MagicMock()
        resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "uptime_seconds" in data


@pytest.mark.integration
def test_chat_endpoint_fallback_on_empty_retrieval(client):
    """With no retrieved citations the graph should return a fallback."""
    with patch("app.graphs.legal_assistant.nodes_generation.get_llm_service") as mock_llm, \
         patch("app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service") as mock_ret, \
         patch("app.graphs.legal_assistant.nodes_retrieval.get_embedding_service") as mock_emb:

        mock_emb.return_value.embed_query.return_value = [0.0] * 1024
        mock_ret.return_value.search.return_value = []
        mock_llm.return_value.generate = AsyncMock(return_value="إجابة بناءً على السياق")

        resp = client.post("/chat", json={"question": "هل يجوز فصل العامل بدون سبب؟"})

    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert data["is_fallback"] is True
    assert data["citations"] == []
