from __future__ import annotations

from app.core.logging import get_logger
from app.graphs.contract_analysis.state import ContractAnalysisState
from app.services.extraction_service import extract_text

logger = get_logger("bayyinah.graph.contract.extraction")


def extract_node(state: ContractAnalysisState) -> ContractAnalysisState:
    warnings = list(state.get("warnings", []))
    try:
        text = extract_text(state["file_path"], state["filename"])
        if not text.strip():
            logger.warning("extraction_empty")
            return {**state, "raw_text": "", "extraction_failed": True, "warnings": warnings + ["empty_document"]}

        logger.info("extraction_completed", extra={"extra_fields": {"chars": len(text)}})
        return {**state, "raw_text": text, "extraction_failed": False, "warnings": warnings}
    except Exception as exc:
        logger.exception("extraction_failed")
        return {
            **state,
            "raw_text": "",
            "extraction_failed": True,
            "warnings": warnings + [f"extraction_error: {exc}"],
        }
