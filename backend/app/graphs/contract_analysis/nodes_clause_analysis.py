from __future__ import annotations

import json

from app.core.logging import get_logger
from app.graphs.contract_analysis.state import ContractAnalysisState
from app.schemas.contract import ClauseAnalysis, RiskLevel
from app.services.llm_service import get_llm_service

logger = get_logger("bayyinah.graph.contract.clauses")

SYSTEM_PROMPT = """أنت محلل عقود قانوني متخصص في القانون المصري.
لكل بند من بنود العقد المرسل إليك، قم بالتالي:
1. صنّف نوع البند (مثل: مدة العقد، الالتزامات المالية، الإنهاء، التعويضات، السرية، حل النزاعات، الضمانات، أخرى).
2. اشرح البند بلغة عربية مصرية مبسطة يسهل على غير المتخصصين فهمها.
3. حدد مستوى الخطورة القانونية لهذا البند: low, medium, high, critical.
4. إذا كان هناك خطر، اذكر السبب باختصار بالعربية.

أعد الإجابة بصيغة JSON فقط بدون أي نص إضافي، بالشكل التالي:
{"clause_type": "...", "simple_explanation_ar": "...", "risk_level": "low|medium|high|critical", "risk_reason": "..." }
"""


async def analyze_clauses_node(state: ContractAnalysisState) -> ContractAnalysisState:
    if state.get("extraction_failed") or not state.get("clauses_raw"):
        return {**state, "clause_analyses": []}

    llm = get_llm_service()
    analyses: list[ClauseAnalysis] = []

    for clause in state["clauses_raw"]:
        user_prompt = f"نص البند:\n{clause['text']}"
        try:
            raw = await llm.generate(SYSTEM_PROMPT, user_prompt)
            parsed = _safe_json(raw)
            risk_level = _safe_risk_level(parsed.get("risk_level"))

            analyses.append(
                ClauseAnalysis(
                    clause_id=clause["clause_id"],
                    original_text=clause["text"],
                    simple_explanation_ar=parsed.get("simple_explanation_ar", ""),
                    clause_type=parsed.get("clause_type", "أخرى"),
                    risk_level=risk_level,
                    risk_reason=parsed.get("risk_reason"),
                )
            )
        except Exception:
            logger.exception("clause_analysis_failed", extra={"extra_fields": {"clause_id": clause["clause_id"]}})
            analyses.append(
                ClauseAnalysis(
                    clause_id=clause["clause_id"],
                    original_text=clause["text"],
                    simple_explanation_ar="تعذر تحليل هذا البند تلقائيًا.",
                    clause_type="أخرى",
                    risk_level=RiskLevel.LOW,
                    risk_reason=None,
                )
            )

    logger.info("clause_analysis_completed", extra={"extra_fields": {"num_clauses": len(analyses)}})

    return {**state, "clause_analyses": analyses}


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


def _safe_risk_level(value: str | None) -> RiskLevel:
    try:
        return RiskLevel(value)
    except (ValueError, TypeError):
        return RiskLevel.LOW
