from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class LegalDomain(str, Enum):
    LABOR = "labor_law"
    TENANCY = "tenancy_law"
    FAMILY = "family_law"
    CIVIL = "civil_law"
    CRIMINAL = "criminal_law"
    COMMERCIAL = "commercial_law"
    ADMINISTRATIVE = "administrative_law"
    UNKNOWN = "unknown"


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    conversation_id: Optional[str] = Field(default=None)
    stream: bool = Field(default=False)

    @field_validator("question")
    @classmethod
    def strip_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question cannot be empty")
        return v


class Citation(BaseModel):
    chunk_id: str
    doc_id: str
    law_name: str
    law_number: Optional[str] = None
    law_year: Optional[str] = None
    law_type: Optional[str] = None
    category: Optional[str] = None
    article_number: Optional[str] = None
    text: str
    score: float


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    domain: LegalDomain
    faithfulness_score: Optional[float] = None
    is_fallback: bool = False
    is_unsafe: bool = False
    warnings: List[str] = Field(default_factory=list)
    request_id: Optional[str] = None
