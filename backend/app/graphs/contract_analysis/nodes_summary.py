from __future__ import annotations

import json

from app.core.logging import get_logger
from app.graphs.contract_analysis.state import ContractAnalysisState
from app.schemas.contract import ContractSummary
from app.services.llm_service import get_llm_service

logger = get_logger("bayyinah.graph.contract.summary")

SUMMARY_SYSTEM_PROMPT = """أنت محلل عقود قانوني متخصص في القانون المصري.
بناءً على نص العقد الكامل، قم بإنشاء:
1. نظرة عامة موجزة بالعربية المصرية المبسطة عن موضوع العقد (3-5 جمل).
2. أطراف العقد (إن وجدت أسماء أو صفات مثل "الطرف الأول"، "المؤجر"، "الشركة").
3. نوع العقد (مثال: عقد إيجار، عقد عمل، عقد بيع، عقد خدمات، إلخ).
4. مدة العقد إن وجدت.

أعد النتيجة بصيغة JSON فقط:
{"overview_ar": "...", "parties": ["..."], "contract_type": "...", "duration": "..."}
"""

RECOMMENDATIONS_SYSTEM_PROMPT = """أنت مستشار قانوني. بناءً على المخاطر والبنود الناقصة المذكورة، قدم قائمة من 3 إلى 6 توصيات
عملية بالعربية المصرية المبسطة لتحسين العقد أو لحماية الطرف الذي يطلب التحليل.
أعد النتيجة بصيغة JSON فقط: {"recommendations": ["...", "..."]}
"""


async def summarize_node(state: ContractAnalysisState) -> ContractAnalysisState:
    if state.get("extraction_failed"):
        summary = ContractSummary(
            overview_ar="تعذر استخراج محتوى الملف. يُرجى التأكد من أن الملف غير تالف وأنه بصيغة PDF أو DOCX صالحة.",
            parties=[],
            contract_type="غير محدد",
            duration=None,
            total_clauses=0,
        )
        return {**state, "summary": summary, "recommendations_ar": []}

    llm = get_llm_service()

    text_excerpt = state["raw_text"][:8000]
    try:
        raw = await llm.generate(SUMMARY_SYSTEM_PROMPT, text_excerpt)
        parsed = _safe_json(raw)
        summary = ContractSummary(
            overview_ar=parsed.get("overview_ar", ""),
            parties=parsed.get("parties", []),
            contract_type=parsed.get("contract_type", "غير محدد"),
            duration=parsed.get("duration"),
            total_clauses=len(state.get("clause_analyses", [])),
        )
    except Exception:
        logger.exception("summary_generation_failed")
        summary = ContractSummary(
            overview_ar="تعذر إنشاء ملخص للعقد.",
            parties=[],
            contract_type="غير محدد",
            duration=None,
            total_clauses=len(state.get("clause_analyses", [])),
        )

    recommendations = await _generate_recommendations(state)

    logger.info("summary_completed")

    return {**state, "summary": summary, "recommendations_ar": recommendations}


async def _generate_recommendations(state: ContractAnalysisState) -> list[str]:
    risks = state.get("risks", [])
    missing = state.get("missing_clauses", [])

    if not risks and not missing:
        return ["لم يتم رصد مخاطر جوهرية أو بنود ناقصة بناءً على التحليل الحالي، ولكن يُنصح دائمًا بمراجعة العقد مع محامٍ قبل التوقيع."]

    llm = get_llm_service()
    risk_summary = "\n".join(f"- {r.clause_type}: {r.risk_reason or 'بدون تفاصيل'}" for r in risks)
    missing_summary = "\n".join(f"- {m.clause_type}: {m.description_ar}" for m in missing)

    user_prompt = f"المخاطر المرصودة:\n{risk_summary}\n\nالبنود الناقصة:\n{missing_summary}"

    try:
        raw = await llm.generate(RECOMMENDATIONS_SYSTEM_PROMPT, user_prompt)
        parsed = _safe_json(raw)
        return parsed.get("recommendations", [])
    except Exception:
        logger.exception("recommendations_generation_failed")
        return ["يُنصح بمراجعة العقد مع محامٍ مرخص قبل التوقيع لمعالجة المخاطر المذكورة أعلاه."]


def _safe_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}
