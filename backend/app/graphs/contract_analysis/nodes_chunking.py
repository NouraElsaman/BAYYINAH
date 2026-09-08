from __future__ import annotations

from app.core.logging import get_logger
from app.graphs.contract_analysis.state import ContractAnalysisState
from app.services.contract_chunker import chunk_contract

logger = get_logger("bayyinah.graph.contract.chunking")


def chunk_node(state: ContractAnalysisState) -> ContractAnalysisState:
    if state.get("extraction_failed"):
        return {**state, "clauses_raw": []}

    chunks = chunk_contract(state["raw_text"])

    logger.info("chunking_completed", extra={"extra_fields": {"num_chunks": len(chunks)}})

    return {
        **state,
        "clauses_raw": [{"clause_id": c.clause_id, "text": c.text, "order": c.order} for c in chunks],
    }
