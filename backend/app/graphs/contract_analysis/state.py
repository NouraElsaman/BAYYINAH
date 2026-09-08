from __future__ import annotations

from typing import List, TypedDict

from app.schemas.contract import ClauseAnalysis, ContractSummary, MissingClause, RiskLevel


class ContractAnalysisState(TypedDict, total=False):
    document_id: str
    filename: str
    file_path: str
    request_id: str

    raw_text: str
    extraction_failed: bool

    clauses_raw: List[dict]  # {clause_id, text, order}

    clause_analyses: List[ClauseAnalysis]
    risks: List[ClauseAnalysis]
    missing_clauses: List[MissingClause]

    summary: ContractSummary
    recommendations_ar: List[str]
    overall_risk_level: RiskLevel

    warnings: List[str]
    is_unsafe: bool
