from __future__ import annotations

import asyncio
from app.core.config import get_settings
from app.core.logging import get_logger
from app.graphs.legal_assistant.state import LegalAssistantState
from app.services.llm_service import get_llm_service
from app.services.embedding_service import get_embedding_service

logger = get_logger("bayyinah.graph.query_expansion")
settings = get_settings()

HYDE_SYSTEM_PROMPT = """أنت مساعد قانوني ذكي متخصص في القانون المصري.
مهمتك هي كتابة فقرة قصيرة تحاكي مادة قانونية أو تفسيراً قانونياً يجيب عن السؤال المقدم من المستخدم.
الهدف هو استخدام هذه الإجابة التخيلية للبحث عن نصوص مطابقة في قاعدة البيانات.
اكتب الفقرة باللغة العربية الفصحى القانونية بدقة وبدون أي مقدمات أو شروحات إضافية.
"""

HYDE_USER_PROMPT = "السؤال: {question}"

from app.observability import trace_node


@trace_node("query_expansion")
async def query_expansion_node(state: LegalAssistantState) -> LegalAssistantState:
    question = state.get("question", "")
    if not question:
        return state

    if not settings.QUERY_EXPANSION_ENABLED:
        logger.info("query_expansion_disabled")
        return state

    # Skip HyDE when domain was already detected — the question has specific legal
    # keywords so the original query vector is precise enough. HyDE only adds value
    # for vague / domain-unknown questions where retrieval might otherwise miss context.
    from app.schemas.chat import LegalDomain
    detected_domain = state.get("domain")
    if detected_domain and detected_domain != LegalDomain.UNKNOWN:
        logger.info(
            "query_expansion_skipped_domain_detected",
            extra={"extra_fields": {"domain": str(detected_domain)}},
        )
        return state

    llm = get_llm_service()
    embedder = get_embedding_service()
    
    try:
        # HyDE generation
        logger.info("query_expansion_hyde_generation_start")
        # Call LLM with a timeout
        user_prompt = HYDE_USER_PROMPT.format(question=question)
        
        # HyDE only needs a short hypothetical paragraph — cap at 300 tokens
        raw_hyde_doc = await asyncio.wait_for(
            llm.generate(HYDE_SYSTEM_PROMPT, user_prompt, max_tokens=300),
            timeout=min(settings.QUERY_EXPANSION_TIMEOUT_S, 2.0)
        )
        hyde_doc = raw_hyde_doc.strip()
        logger.info("query_expansion_hyde_generation_success", extra={"extra_fields": {"doc_len": len(hyde_doc)}})
        
        # Embed the generated hypothetical document
        hyde_vector = embedder.embed_query(hyde_doc)
        
        return {
            **state,
            "rewritten_query": question, # default rewritten query is the question itself for now
            "hyde_document": hyde_doc,
            "hyde_vector": hyde_vector,
        }
    except asyncio.TimeoutError:
        logger.warning("query_expansion_hyde_timeout", extra={"extra_fields": {"timeout_s": settings.QUERY_EXPANSION_TIMEOUT_S}})
        return {
            **state,
            "warnings": list(state.get("warnings", [])) + ["hyde_generation_timeout"]
        }
    except Exception as e:
        logger.exception("query_expansion_failed", extra={"extra_fields": {"error": str(e)}})
        return {
            **state,
            "warnings": list(state.get("warnings", [])) + [f"hyde_generation_failed: {str(e)}"]
        }
