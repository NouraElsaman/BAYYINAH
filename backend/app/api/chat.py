from __future__ import annotations

import csv
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.core.logging import get_logger, request_id_ctx
from app.graphs.legal_assistant.nodes_domain import detect_domain_node
from app.graphs.legal_assistant.nodes_query_expansion import query_expansion_node
from app.graphs.legal_assistant.nodes_generation import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_GENERAL,
    USER_PROMPT_GENERAL,
    USER_PROMPT_TEMPLATE,
    build_context,
    build_history_block,
)
from app.graphs.legal_assistant.nodes_retrieval import retrieve_node
from app.graphs.legal_assistant.nodes_verification import FALLBACK_UNSAFE, _check_unsafe
from app.schemas.chat import ChatRequest, ChatResponse, LegalDomain
from app.services.llm_service import get_llm_service
from app.services.memory_service import get_memory_service
from app.services.routing_service import route_query
from app.api.system import CHAT_LATENCY, FAITHFULNESS_GAUGE, FALLBACK_COUNT, REQUEST_COUNT

router = APIRouter(tags=["chat"])
logger = get_logger("bayyinah.api.chat")

FEEDBACK_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "user_feedback_log.csv")


class FeedbackRequest(BaseModel):
    conversation_id: str
    question: str
    answer: str
    is_correct: bool


def _log_feedback(conversation_id: str, question: str, answer: str, is_correct: bool) -> None:
    """Append a feedback row to the CSV log file."""
    file_exists = os.path.isfile(FEEDBACK_LOG_PATH)
    with open(FEEDBACK_LOG_PATH, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "conversation_id", "question", "answer_preview", "is_correct"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            conversation_id,
            question,
            answer[:200],
            "Yes" if is_correct else "No",
        ])


@router.post("/chat/feedback")
async def chat_feedback(body: FeedbackRequest) -> JSONResponse:
    """Record user feedback (thumbs up/down) for a chat answer."""
    _log_feedback(body.conversation_id, body.question, body.answer, body.is_correct)
    return JSONResponse({"status": "ok", "message": "شكراً على تقييمك!"})


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    conversation_id = body.conversation_id or str(uuid.uuid4())
    request_id = request_id_ctx.get()

    from app.observability import init_telemetry, finalize_telemetry, record_metric
    init_telemetry(request_id=request_id, conversation_id=conversation_id)

    try:
        state = {
            "question": body.question,
            "conversation_id": conversation_id,
            "request_id": request_id,
            "warnings": [],
        }

        with CHAT_LATENCY.time():
            # 1. Unsafe guardrail
            if _check_unsafe(state["question"]):
                record_metric("unsafe_detection", True)
                record_metric("fallback_triggered", True)
                FALLBACK_COUNT.inc()
                REQUEST_COUNT.labels(endpoint="/chat", status="success").inc()
                return ChatResponse(
                    conversation_id=conversation_id,
                    answer=FALLBACK_UNSAFE,
                    citations=[],
                    domain=LegalDomain.UNKNOWN,
                    is_fallback=True,
                    is_unsafe=True,
                    warnings=["unsafe_request_blocked"],
                    request_id=request_id,
                )

            # 2. Static intent routing (greetings, out-of-scope) — no LLM cost
            static_response, detected_intent = await route_query(state["question"])
            if static_response:
                REQUEST_COUNT.labels(endpoint="/chat", status="success").inc()
                logger.info("static_route_triggered", extra={"extra_fields": {"intent": detected_intent}})
                return ChatResponse(
                    conversation_id=conversation_id,
                    answer=static_response,
                    citations=[],
                    domain=LegalDomain.UNKNOWN,
                    is_fallback=False,
                    warnings=[f"static_route:{detected_intent}"],
                    request_id=request_id,
                )

            # Load history
            history = []
            if conversation_id:
                try:
                    memory_service = get_memory_service()
                    history = memory_service.get_history(conversation_id)
                except Exception as e:
                    logger.error("memory_retrieve_failed", extra={"extra_fields": {"error": str(e)}})
                    history = []
            state["history"] = history

            # 3. Domain Detection, Query Expansion & Retrieval
            state = detect_domain_node(state)
            try:
                state = await query_expansion_node(state)
            except Exception as e:
                logger.exception("query_expansion_failed_in_api", extra={"extra_fields": {"error": str(e)}})
            state = retrieve_node(state)

            # 4. Generate Answer (handles both context-based and general-knowledge fallback)
            history_block = build_history_block(history)
            llm = get_llm_service()
            citations = state.get("citations", [])

            # --- Diagnostic log ---
            logger.info(
                "chat_api_retrieval_result",
                extra={"extra_fields": {
                    "question_preview": state["question"][:80],
                    "retrieval_empty": state.get("retrieval_empty"),
                    "num_citations": len(citations),
                    "retrieval_confidence": round(state.get("retrieval_confidence", 0.0), 4),
                    "used_hyde": "hyde_vector" in state and bool(state.get("hyde_vector")),
                    "domain": str(state.get("domain", "")),
                    "law_type_filter": state.get("law_type_filter"),
                    "citation_previews": [
                        {"chunk_id": c.chunk_id, "article": c.article_number, "score": round(c.score, 4)}
                        for c in citations[:5]
                    ],
                }},
            )

            if state.get("retrieval_empty"):
                logger.warning(
                    "chat_api_using_general_fallback_no_citations",
                    extra={"extra_fields": {"question_preview": state["question"][:80]}},
                )
                user_prompt = USER_PROMPT_GENERAL.format(question=state["question"])
                system_prompt = SYSTEM_PROMPT_GENERAL
                if history_block:
                    system_prompt = system_prompt + "\n" + history_block
                answer = await llm.generate(system_prompt, user_prompt)
                FALLBACK_COUNT.inc()
                is_fallback = True
            else:
                context = build_context(state)
                logger.info(
                    "chat_api_generation_with_context",
                    extra={"extra_fields": {
                        "num_citations": len(citations),
                        "context_length": len(context),
                        "chunk_ids": [c.chunk_id for c in citations],
                        "articles": [f"{c.law_name} م{c.article_number}" for c in citations if c.article_number],
                        "context_preview": context[:300],
                    }},
                )
                user_prompt = USER_PROMPT_TEMPLATE.format(question=state["question"], context=context)
                system_prompt = SYSTEM_PROMPT
                if history_block:
                    system_prompt = system_prompt + "\n" + history_block
                answer = await llm.generate(system_prompt, user_prompt)
                is_fallback = False


            # Save history
            if conversation_id:
                try:
                    memory_service = get_memory_service()
                    memory_service.add_turn(conversation_id, "user", state["question"])
                    memory_service.add_turn(conversation_id, "assistant", answer)
                except Exception as e:
                    logger.error("memory_save_failed", extra={"extra_fields": {"error": str(e)}})

        REQUEST_COUNT.labels(endpoint="/chat", status="success").inc()

        record_metric("fallback_triggered", is_fallback)
        record_metric("num_citations", len(state.get("citations", [])))

        return ChatResponse(
            conversation_id=conversation_id,
            answer=answer,
            citations=state.get("citations", []),
            domain=state.get("domain", LegalDomain.UNKNOWN),
            is_fallback=is_fallback,
            is_unsafe=state.get("is_unsafe", False),
            warnings=state.get("warnings", []),
            request_id=request_id,
        )
    finally:
        finalize_telemetry()


@router.post("/chat/stream")
async def chat_stream(request: Request, body: ChatRequest):
    """Streaming variant: intent routing → domain detection → retrieval → LLM stream."""

    request_id = request_id_ctx.get()

    state = {
        "question": body.question,
        "conversation_id": body.conversation_id or str(uuid.uuid4()),
        "request_id": request_id,
        "warnings": [],
    }

    async def event_stream():
        from app.observability import init_telemetry, finalize_telemetry, record_metric
        init_telemetry(request_id=request_id, conversation_id=state["conversation_id"])
        try:
            # 1. Unsafe guardrail
            if _check_unsafe(state["question"]):
                record_metric("unsafe_detection", True)
                record_metric("fallback_triggered", True)
                yield _sse({"type": "error", "message": FALLBACK_UNSAFE})
                return

            # 2. Static intent routing (greetings, out-of-scope)
            static_response, detected_intent = await route_query(state["question"])
            if static_response:
                logger.info("static_route_triggered_stream", extra={"extra_fields": {"intent": detected_intent}})
                yield _sse({"type": "token", "content": static_response})
                yield _sse({
                    "type": "done",
                    "final_answer": static_response,
                    "is_fallback": False,
                    "citations": [],
                    "conversation_id": state["conversation_id"],
                })
                return

            # Load history
            history = []
            conversation_id = state["conversation_id"]
            if conversation_id:
                try:
                    memory_service = get_memory_service()
                    history = memory_service.get_history(conversation_id)
                except Exception as e:
                    logger.error("memory_retrieve_failed_stream", extra={"extra_fields": {"error": str(e)}})
                    history = []
            state["history"] = history

            # 3. Domain Detection, Query Expansion & Retrieval
            current_state = detect_domain_node(state)
            try:
                current_state = await query_expansion_node(current_state)
            except Exception as e:
                logger.exception("query_expansion_failed_in_api_stream", extra={"extra_fields": {"error": str(e)}})
            current_state = retrieve_node(current_state)

            llm = get_llm_service()

            # 4. Choose prompt based on retrieval result
            history_block = build_history_block(history)
            if current_state.get("retrieval_empty"):
                user_prompt = USER_PROMPT_GENERAL.format(question=current_state["question"])
                system_prompt = SYSTEM_PROMPT_GENERAL
                if history_block:
                    system_prompt = system_prompt + "\n" + history_block
                is_fallback = True
            else:
                context = build_context(current_state)
                user_prompt = USER_PROMPT_TEMPLATE.format(
                    question=current_state["question"],
                    context=context,
                )
                system_prompt = SYSTEM_PROMPT
                if history_block:
                    system_prompt = system_prompt + "\n" + history_block
                is_fallback = False

            full_answer = ""

            async for token in llm.stream(system_prompt, user_prompt):
                full_answer += token
                yield _sse({"type": "token", "content": token})

            citations = [c.model_dump() for c in current_state.get("citations", [])]

            record_metric("fallback_triggered", is_fallback)
            record_metric("num_citations", len(citations))

            yield _sse({
                "type": "done",
                "final_answer": full_answer,
                "is_fallback": is_fallback,
                "citations": citations,
                "conversation_id": current_state["conversation_id"],
            })

            # Save history after successful stream
            if conversation_id:
                try:
                    memory_service = get_memory_service()
                    memory_service.add_turn(conversation_id, "user", current_state["question"])
                    memory_service.add_turn(conversation_id, "assistant", full_answer)
                except Exception as e:
                    logger.error("memory_save_failed_stream", extra={"extra_fields": {"error": str(e)}})
        finally:
            finalize_telemetry()

    return StreamingResponse(event_stream(), media_type="text/event-stream")



def _sse(data: dict) -> str:
    import json
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
