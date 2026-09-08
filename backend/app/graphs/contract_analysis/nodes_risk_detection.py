from __future__ import annotations

import json

from app.core.logging import get_logger
from app.graphs.contract_analysis.state import ContractAnalysisState
from app.schemas.contract import MissingClause, RiskLevel
from app.services.llm_service import get_llm_service

logger = get_logger("bayyinah.graph.contract.risk")

EXPECTED_CLAUSES = [
    ("مدة العقد", RiskLevel.HIGH),
    ("آلية فسخ العقد / الإنهاء", RiskLevel.HIGH),
    ("الالتزامات المالية وطريقة الدفع", RiskLevel.HIGH),
    ("حل النزاعات / الاختصاص القضائي", RiskLevel.MEDIUM),
    ("التعويضات عن الإخلال بالعقد", RiskLevel.MEDIUM),
    ("السرية", RiskLevel.LOW),
    ("القوة القاهرة", RiskLevel.LOW),
]

MISSING_CLAUSE_SYSTEM_PROMPT = """أنت محلل عقود قانوني. سيتم تزويدك بقائمة أنواع البنود الموجودة في عقد ما.
حدد أي من البنود التالية الأساسية غير موجودة في العقد، واشرح بالعربية المصرية المبسطة لماذا يعتبر غيابها مشكلة.

البنود الأساسية المتوقعة:
{expected}

أعد النتيجة بصيغة JSON فقط: {{"missing": [{{"clause_type": "...", "description_ar": "...", "importance": "low|medium|high|critical"}}]}}
إذا كانت جميع البنود الأساسية موجودة، أعد {{"missing": []}}.
"""


async def detect_risks_node(state: ContractAnalysisState) -> ContractAnalysisState:
    analyses = state.get("clause_analyses", [])

    risks = [a for a in analyses if a.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.MEDIUM)]
    risks = sorted(risks, key=lambda a: _risk_rank(a.risk_level), reverse=True)

    missing_clauses = await _detect_missing_clauses(analyses)

    overall = _compute_overall_risk(risks, missing_clauses)

    logger.info(
        "risk_detection_completed",
        extra={"extra_fields": {"num_risks": len(risks), "num_missing": len(missing_clauses), "overall": overall.value}},
    )

    return {**state, "risks": risks, "missing_clauses": missing_clauses, "overall_risk_level": overall}


def _risk_rank(level: RiskLevel) -> int:
    return {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}[level]


async def _detect_missing_clauses(analyses) -> list[MissingClause]:
    if not analyses:
        return [
            MissingClause(clause_type=name, description_ar=f"العقد لا يحتوي على بند '{name}'.", importance=importance)
            for name, importance in EXPECTED_CLAUSES
        ]

    clause_types = [a.clause_type for a in analyses]
    llm = get_llm_service()

    expected_str = "\n".join(f"- {name}" for name, _ in EXPECTED_CLAUSES)
    system = MISSING_CLAUSE_SYSTEM_PROMPT.format(expected=expected_str)
    user = "أنواع البنود الموجودة في العقد:\n" + "\n".join(f"- {ct}" for ct in clause_types)

    try:
        raw = await llm.generate(system, user)
        parsed = _safe_json(raw)
        missing_items = parsed.get("missing", [])
        result = []
        for item in missing_items:
            try:
                importance = RiskLevel(item.get("importance", "medium"))
            except ValueError:
                importance = RiskLevel.MEDIUM
            result.append(
                MissingClause(
                    clause_type=item.get("clause_type", "غير محدد"),
                    description_ar=item.get("description_ar", ""),
                    importance=importance,
                )
            )
        return result
    except Exception:
        logger.exception("missing_clause_detection_failed")
        return []


def _compute_overall_risk(risks, missing_clauses) -> RiskLevel:
    if any(r.risk_level == RiskLevel.CRITICAL for r in risks):
        return RiskLevel.CRITICAL
    if any(m.importance in (RiskLevel.HIGH, RiskLevel.CRITICAL) for m in missing_clauses):
        return RiskLevel.HIGH
    if any(r.risk_level == RiskLevel.HIGH for r in risks):
        return RiskLevel.HIGH
    if any(r.risk_level == RiskLevel.MEDIUM for r in risks) or missing_clauses:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


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
