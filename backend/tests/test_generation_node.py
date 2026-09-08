import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.graphs.legal_assistant.nodes_generation import build_history_block, generate_answer_node
from app.schemas.chat import Citation


def test_build_history_block_empty():
    assert build_history_block(None) == ""
    assert build_history_block([]) == ""
    assert build_history_block([{"role": "other", "content": "hello"}]) == ""


def test_build_history_block_single():
    history = [{"role": "user", "content": "أهلاً بك"}]
    expected = "سياق المحادثة السابقة بينك وبين المستخدم:\nالمستخدم: أهلاً بك\n\n"
    assert build_history_block(history) == expected


def test_build_history_block_multi():
    history = [
        {"role": "user", "content": "سؤال ١"},
        {"role": "assistant", "content": "إجابة ١"},
        {"role": "user", "content": "سؤال ٢"}
    ]
    expected = (
        "سياق المحادثة السابقة بينك وبين المستخدم:\n"
        "المستخدم: سؤال ١\n"
        "بيّنة: إجابة ١\n"
        "المستخدم: سؤال ٢\n\n"
    )
    assert build_history_block(history) == expected


@pytest.mark.asyncio
@patch("app.graphs.legal_assistant.nodes_generation.get_llm_service")
async def test_generate_answer_node_with_history(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value="إجابة تجريبية مع سياق")
    mock_get_llm.return_value = mock_llm

    citation = Citation(
        chunk_id="c1", doc_id="d1", law_name="قانون العمل", text="نص المادة", score=0.9
    )

    state = {
        "question": "ما هو سؤالي؟",
        "retrieval_empty": False,
        "citations": [citation],
        "history": [
            {"role": "user", "content": "مرحبا"},
            {"role": "assistant", "content": "أهلا بك"}
        ],
        "warnings": []
    }

    result = await generate_answer_node(state)

    assert result["raw_answer"] == "إجابة تجريبية مع سياق"
    
    # Check mock call
    mock_llm.generate.assert_called_once()
    system_prompt_arg = mock_llm.generate.call_args[0][0]
    user_prompt_arg = mock_llm.generate.call_args[0][1]

    # Verify history block is inside system prompt
    assert "سياق المحادثة السابقة بينك وبين المستخدم:" in system_prompt_arg
    assert "المستخدم: مرحبا" in system_prompt_arg
    assert "بيّنة: أهلا بك" in system_prompt_arg
    assert "نص المادة" in user_prompt_arg
