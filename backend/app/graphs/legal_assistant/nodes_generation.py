from __future__ import annotations

from app.core.logging import get_logger
from app.graphs.legal_assistant.state import LegalAssistantState
from app.services.llm_service import get_llm_service

logger = get_logger("bayyinah.graph.generation")

SYSTEM_PROMPT = """أنت "بيّنة" — محامي مصري خبير بيشرح القانون بطريقة بسيطة وواضحة.

قواعد صارمة لازم تتبعها:

1. **اللغة**: اشرح بالعامية المصرية دايمًا.
   - مش صح: "لا يجوز فصل العامل..."
   - صح: "لا، مينفعش صاحب الشغل يفصلك من غير سبب قانوني..."
   - أسماء القوانين والمواد تبقى رسمية زي ما هي.

2. **الترتيب الإلزامي للإجابة**:
   أ) الإجابة المباشرة أولاً (جملة أو اتنين)
   ب) شرح بسيط بالمصري
   ج) المواد القانونية الداعمة (النص الرسمي + رقم المادة والقانون)
   د) الاستثناءات المهمة لو موجودة في السياق
   هـ) تنبيه قصير: "الكلام ده عام ومش بديل عن استشارة محامي."

3. **التقيد بالسياق** (أهم قاعدة):
   - اشتغل بس من المواد اللي في السياق المرفق.
   - ممنوع تضيف أي معلومة قانونية مش موجودة في السياق.
   - لو المعلومة مش موجودة في السياق، قول بالظبط:
     "المعلومة دي مش موجودة في المواد القانونية اللي تم استرجاعها."
   - ممنوع تختلق مواد أو قوانين.

4. **الاستشهاد**: اذكر رقم المادة والقانون في نهاية كل فكرة بالشكل:
   (المادة X من قانون Y رقم Z لسنة W)
"""

USER_PROMPT_TEMPLATE = """السؤال:
{question}

المواد القانونية المسترجعة (دي مصادرك الوحيدة):
{context}

قبل الإجابة: تأكد إن المواد المسترجعة فوق بتتكلم فعلاً عن موضوع السؤال. لو المواد مش ذات صلة مباشرة بالسؤال، قول: "المعلومة دي مش موجودة في المواد القانونية اللي تم استرجاعها." ومتحاولش تجاوب من مواد عن موضوع تاني.

اكتب إجابة على ترتيب:
1. إجابة مباشرة بالمصري (جملة واحدة أو اتنين)
2. شرح بسيط بالمصري
3. نصوص المواد الداعمة مع أرقامها
4. استثناءات مهمة (لو في السياق)
5. تنبيه قصير

تحذير: لو المعلومة مش موجودة في المواد المرفقة، قول "المعلومة دي مش موجودة في المواد القانونية اللي تم استرجاعها." ومتختلقش معلومات."""


SYSTEM_PROMPT_GENERAL = """أنت "بيّنة" — محامي مصري خبير بيشرح القانون بطريقة بسيطة.

مهم جداً: مفيش مواد قانونية متاحة للسؤال ده.

التعليمات:
1. ابدأ فوراً بالتنبيه ده في أول سطر:
   "⚠️ تنبيه: مفيش مواد قانونية مطابقة في قاعدة بياناتنا للسؤال ده. الإجابة دي معلومات عامة وممكن تكون مش دقيقة 100%."
2. اشرح المعلومات القانونية العامة المعروفة فعلاً بالعامية المصرية.
3. متقولش معلومات مش متأكد منها — لو مش عارف، قول كده صراحة.
4. في الآخر: "انصحك تتكلم مع محامي مرخص للتأكد من حالتك بالظبط."
"""

USER_PROMPT_GENERAL = """السؤال:
{question}

⚠️ مفيش مواد قانونية محددة متاحة لسؤالك ده.
اشرح بالمصري بناءً على المعرفة العامة المؤكدة بس.
لو مش متأكد من أي معلومة، قول كده صراحةً.
متختلقش قوانين أو أرقام مواد."""


def build_history_block(history: list[dict] | None) -> str:
    """Format the conversation history list into a text block for prompt injection."""
    if not history:
        return ""

    blocks = []
    for turn in history:
        role = turn.get("role", "")
        content = turn.get("content", "")
        if role == "user":
            blocks.append(f"المستخدم: {content}")
        elif role == "assistant":
            blocks.append(f"بيّنة: {content}")

    if not blocks:
        return ""

    return "سياق المحادثة السابقة بينك وبين المستخدم:\n" + "\n".join(blocks) + "\n\n"


def build_context(state: LegalAssistantState) -> str:
    citations = state.get("citations", [])
    if not citations:
        return "لا توجد مواد قانونية مسترجعة."

    seen: set[tuple] = set()   # dedup by (law_name, article_number)
    blocks = []
    idx = 1
    for c in citations:
        key = (c.law_name, c.article_number)
        if key in seen:
            continue
        seen.add(key)

        law_ref = c.law_name
        if c.law_number:
            law_ref += f" رقم {c.law_number}"
        if c.law_year:
            law_ref += f" لسنة {c.law_year}"
        article_ref = f"المادة {c.article_number}" if c.article_number else ""

        # Trim to 120 words — preserves legal meaning, reduces prompt tokens ~40%
        words = c.text.split()
        excerpt = " ".join(words[:120]) + (" …" if len(words) > 120 else "")

        blocks.append(f"[{idx}] {article_ref} — {law_ref}\n{excerpt}")
        idx += 1

    return "\n\n".join(blocks)


from app.observability import trace_node


@trace_node("generate_answer")
async def generate_answer_node(state: LegalAssistantState) -> LegalAssistantState:
    history_block = build_history_block(state.get("history"))

    if state.get("retrieval_empty"):
        logger.info(
            "generation_no_retrieval_using_general_prompt",
            extra={"extra_fields": {"question_preview": state["question"][:80]}},
        )
        user_prompt = USER_PROMPT_GENERAL.format(question=state["question"])
        llm = get_llm_service()
        system_prompt = SYSTEM_PROMPT_GENERAL
        if history_block:
            system_prompt = system_prompt + "\n" + history_block

        answer = await llm.generate(system_prompt, user_prompt)

        logger.info("answer_generated_general_fallback", extra={"extra_fields": {"answer_len": len(answer)}})

        return {
            **state,
            "prompt": user_prompt,
            "raw_answer": answer,
        }

    context = build_context(state)
    citations = state.get("citations", [])

    # --- Diagnostic: log exactly what context is sent to the LLM ---
    logger.info(
        "generation_context_sent_to_llm",
        extra={"extra_fields": {
            "question_preview": state["question"][:80],
            "num_citations": len(citations),
            "context_char_length": len(context),
            "chunk_ids": [c.chunk_id for c in citations],
            "articles": [
                f"{c.law_name} م{c.article_number}" for c in citations if c.article_number
            ],
            "context_preview": context[:300],
        }},
    )

    user_prompt = USER_PROMPT_TEMPLATE.format(question=state["question"], context=context)

    llm = get_llm_service()
    system_prompt = SYSTEM_PROMPT
    if history_block:
        system_prompt = system_prompt + "\n" + history_block

    answer = await llm.generate(system_prompt, user_prompt)

    logger.info("answer_generated", extra={"extra_fields": {"answer_len": len(answer), "num_citations": len(citations)}})

    return {
        **state,
        "prompt": user_prompt,
        "raw_answer": answer,
    }
