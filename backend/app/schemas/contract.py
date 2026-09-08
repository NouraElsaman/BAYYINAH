from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClauseAnalysis(BaseModel):
    clause_id: str
    original_text: str
    simple_explanation_ar: str
    clause_type: str
    risk_level: RiskLevel
    risk_reason: Optional[str] = None


class MissingClause(BaseModel):
    clause_type: str
    description_ar: str
    importance: RiskLevel


class ContractSummary(BaseModel):
    overview_ar: str
    parties: List[str] = Field(default_factory=list)
    contract_type: str
    duration: Optional[str] = None
    total_clauses: int


class ContractAnalysisResponse(BaseModel):
    document_id: str
    filename: str
    summary: ContractSummary
    clauses: List[ClauseAnalysis]
    risks: List[ClauseAnalysis]
    missing_clauses: List[MissingClause]
    recommendations_ar: List[str]
    overall_risk_level: RiskLevel
    warnings: List[str] = Field(default_factory=list)
    request_id: Optional[str] = None
