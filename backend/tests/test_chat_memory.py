"""
test_chat_memory.py
-------------------
Focused unit tests for Task 6: Chat API Memory Integration.

Covers:
  - history successfully loaded and injected into state
  - history load failure → empty history, no HTTP 500
  - memory save success after generation
  - memory save failure → no HTTP 500
  - streaming path: history loaded before execution, saved after completion
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Shared app fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    import importlib
    import app.api.system as sys_module
    importlib.reload(sys_module)
    from app.main import app
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Full legal question that bypasses static router (OUT_OF_SCOPE guard)
# ---------------------------------------------------------------------------
LEGAL_Q = "هل يجوز فصل العامل بدون سبب وفقًا لقانون العمل المصري رقم 12 لسنة 2003؟"


def _make_memory_mock(history=None):
    m = MagicMock()
    m.get_history.return_value = history or []
    m.add_turn = MagicMock()
    return m


def _start_pipeline_patches():
    """Patch the full RAG pipeline; return (patches_list, llm_mock).

    The chat endpoint calls get_llm_service() directly (app.api.chat),
    so we patch it there AND in the generation node to be safe.
    """
    llm_mock = MagicMock()
    llm_mock.generate = AsyncMock(return_value="إجابة تجريبية")

    emb_mock = MagicMock()
    emb_mock.embed_query.return_value = [0.0] * 1024

    ret_mock = MagicMock()
    ret_mock.search.return_value = []

    rerank_mock = MagicMock()
    rerank_mock.rerank.return_value = []

    # Patch HyDE LLM too so it doesn't call real Groq
    hyde_llm = MagicMock()
    hyde_llm.generate = AsyncMock(return_value="فرضية تجريبية")

    # The sync /chat endpoint resolves LLM via app.api.chat.get_llm_service
    p_api_llm = patch("app.api.chat.get_llm_service", return_value=llm_mock)
    p_llm   = patch("app.graphs.legal_assistant.nodes_generation.get_llm_service",  return_value=llm_mock)
    p_ret   = patch("app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service", return_value=ret_mock)
    p_emb   = patch("app.graphs.legal_assistant.nodes_retrieval.get_embedding_service", return_value=emb_mock)
    p_rnk   = patch("app.graphs.legal_assistant.nodes_retrieval.get_reranker_service",  return_value=rerank_mock)
    p_hllm  = patch("app.graphs.legal_assistant.nodes_query_expansion.get_llm_service",  return_value=hyde_llm)
    p_hemb  = patch("app.graphs.legal_assistant.nodes_query_expansion.get_embedding_service", return_value=emb_mock)

    patches = [p_api_llm, p_llm, p_ret, p_emb, p_rnk, p_hllm, p_hemb]
    for p in patches:
        p.start()
    return patches, llm_mock


def _stop_patches(patches):
    for p in patches:
        p.stop()


# ---------------------------------------------------------------------------
# 1. History successfully loaded and injected into system prompt
# ---------------------------------------------------------------------------

def test_chat_history_loaded_successfully(client):
    """MemoryService.get_history returns turns; history block must reach the system prompt."""
    history = [
        {"role": "user",      "content": "سؤال سابق"},
        {"role": "assistant", "content": "إجابة سابقة"},
    ]
    memory_mock = _make_memory_mock(history)
    patches, llm_mock = _start_pipeline_patches()

    try:
        with patch("app.api.chat.get_memory_service", return_value=memory_mock):
            resp = client.post("/chat", json={"question": LEGAL_Q, "conversation_id": "conv-123"})
    finally:
        _stop_patches(patches)

    assert resp.status_code == 200
    memory_mock.get_history.assert_called_once_with("conv-123")

    # The system prompt forwarded to LLM must contain the history block
    system_prompt_arg = llm_mock.generate.call_args[0][0]
    assert "سياق المحادثة السابقة" in system_prompt_arg
    assert "سؤال سابق" in system_prompt_arg
    assert "إجابة سابقة" in system_prompt_arg


# ---------------------------------------------------------------------------
# 2. History load failure → empty history, no HTTP 500
# ---------------------------------------------------------------------------

def test_chat_history_load_failure_is_non_fatal(client):
    """If MemoryService.get_history raises, the request must still return 200."""
    memory_mock = _make_memory_mock()
    memory_mock.get_history.side_effect = RuntimeError("Redis timeout")

    patches, _ = _start_pipeline_patches()
    try:
        with patch("app.api.chat.get_memory_service", return_value=memory_mock):
            resp = client.post("/chat", json={"question": LEGAL_Q, "conversation_id": "conv-456"})
    finally:
        _stop_patches(patches)

    assert resp.status_code == 200
    assert "answer" in resp.json()


# ---------------------------------------------------------------------------
# 3. Memory save success — both turns written after generation
# ---------------------------------------------------------------------------

def test_chat_memory_saves_both_turns(client):
    """After a successful answer, user and assistant turns must be saved."""
    memory_mock = _make_memory_mock()
    patches, _ = _start_pipeline_patches()

    try:
        with patch("app.api.chat.get_memory_service", return_value=memory_mock):
            resp = client.post("/chat", json={"question": LEGAL_Q, "conversation_id": "conv-789"})
    finally:
        _stop_patches(patches)

    assert resp.status_code == 200
    assert memory_mock.add_turn.call_count == 2
    calls = memory_mock.add_turn.call_args_list
    assert calls[0] == call("conv-789", "user", LEGAL_Q)
    assert calls[1][0][0] == "conv-789"
    assert calls[1][0][1] == "assistant"


# ---------------------------------------------------------------------------
# 4. Memory save failure → no HTTP 500
# ---------------------------------------------------------------------------

def test_chat_memory_save_failure_is_non_fatal(client):
    """If add_turn raises, the response must still be 200."""
    memory_mock = _make_memory_mock()
    memory_mock.add_turn.side_effect = RuntimeError("Redis write error")

    patches, _ = _start_pipeline_patches()
    try:
        with patch("app.api.chat.get_memory_service", return_value=memory_mock):
            resp = client.post("/chat", json={"question": LEGAL_Q, "conversation_id": "conv-abc"})
    finally:
        _stop_patches(patches)

    assert resp.status_code == 200
    assert "answer" in resp.json()


# ---------------------------------------------------------------------------
# 5. Streaming path: history loaded before stream, saved after done
# ---------------------------------------------------------------------------

def test_stream_history_loaded_and_saved(client):
    """/chat/stream loads history before streaming and saves both turns after."""
    history = [{"role": "user", "content": "تاريخ"}]
    memory_mock = _make_memory_mock(history)

    emb_mock = MagicMock()
    emb_mock.embed_query.return_value = [0.0] * 1024
    ret_mock = MagicMock()
    ret_mock.search.return_value = []
    rerank_mock = MagicMock()
    rerank_mock.rerank.return_value = []
    hyde_llm = MagicMock()
    hyde_llm.generate = AsyncMock(return_value="فرضية")

    stream_llm = MagicMock()
    async def _fake_stream(system_prompt, user_prompt):
        yield "كلمة"
        yield " اثنتان"
    stream_llm.stream = _fake_stream

    patches = [
        patch("app.api.chat.get_llm_service", return_value=stream_llm),
        patch("app.graphs.legal_assistant.nodes_retrieval.get_retrieval_service", return_value=ret_mock),
        patch("app.graphs.legal_assistant.nodes_retrieval.get_embedding_service", return_value=emb_mock),
        patch("app.graphs.legal_assistant.nodes_retrieval.get_reranker_service",  return_value=rerank_mock),
        patch("app.graphs.legal_assistant.nodes_query_expansion.get_llm_service",  return_value=hyde_llm),
        patch("app.graphs.legal_assistant.nodes_query_expansion.get_embedding_service", return_value=emb_mock),
    ]
    for p in patches:
        p.start()

    try:
        with patch("app.api.chat.get_memory_service", return_value=memory_mock):
            with client.stream(
                "POST", "/chat/stream",
                json={"question": LEGAL_Q, "conversation_id": "conv-stream-1"},
            ) as r:
                chunks = list(r.iter_lines())
    finally:
        for p in patches:
            p.stop()

    # History retrieved before execution
    memory_mock.get_history.assert_called_once_with("conv-stream-1")

    # SSE events contain token and done
    all_text = " ".join(chunks)
    assert "token" in all_text
    assert "done" in all_text

    # Both turns saved after stream completes
    assert memory_mock.add_turn.call_count == 2
    calls = memory_mock.add_turn.call_args_list
    assert calls[0][0][1] == "user"
    assert calls[1][0][1] == "assistant"
    # Full streamed answer is concatenation of yielded tokens
    assert calls[1][0][2] == "كلمة اثنتان"
