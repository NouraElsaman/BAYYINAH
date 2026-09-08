from __future__ import annotations

from typing import List, Optional, TypedDict

from app.schemas.chat import Citation, LegalDomain


class LegalAssistantState(TypedDict, total=False):
    question: str
    conversation_id: str
    request_id: str

    domain: LegalDomain
    category_filter: Optional[str]
    law_type_filter: Optional[str]

    citations: List[Citation]
    retrieval_empty: bool

    prompt: str
    raw_answer: str

    faithfulness_score: float
    citation_valid: bool
    is_unsafe: bool

    final_answer: str
    is_fallback: bool
    warnings: List[str]

    # Sprint 3 memory and query expansion additions
    history: List[dict]
    hyde_vector: List[float]
    hyde_document: str          # The HyDE-generated hypothetical document text (for diagnostics)
    rewritten_query: str
    alt_queries: List[str]

    # Sprint 3 Phase 2 — retrieval confidence score
    retrieval_confidence: float

    # Sprint 3 Phase 2 — citation agent output
    context_tokens: int

    # Sprint 3 Phase 2 — web search additions
    web_results: List[dict]
    retrieval_source: str
