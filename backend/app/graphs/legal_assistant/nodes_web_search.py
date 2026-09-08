"""
nodes_web_search.py
===================
LangGraph node for executing web search fallback.
Uses WebSearchService, converts normalized SearchResult objects into Citation objects,
and updates the graph state.
"""
from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
from app.graphs.legal_assistant.state import LegalAssistantState
from app.schemas.chat import Citation
from app.services.web_search_service import WebSearchService

logger = get_logger("bayyinah.graph.web_search")


from app.observability import trace_node


@trace_node("web_search")
async def web_search_node(state: LegalAssistantState) -> LegalAssistantState:
    """Executes web search query as fallback, normalizes results into Citations,
    and updates state."""
    settings = get_settings()
    question = state.get("question", "")

    if not settings.WEB_SEARCH_ENABLED:
        logger.info("web_search_disabled_skipping_node")
        return {
            **state,
            "citations": [],
            "web_results": [],
            "retrieval_source": "web",
            "retrieval_empty": True,
        }

    try:
        search_service = WebSearchService()
        search_results = await search_service.search(question)

        citations: list[Citation] = []
        web_results: list[dict] = []

        for idx, r in enumerate(search_results):
            # Normalize into Citation-compatible schema
            citations.append(
                Citation(
                    chunk_id=f"web_{idx}",
                    doc_id=f"web_doc_{idx}",
                    law_name=r.title or "مصدر ويب خارجي",
                    law_number=None,
                    law_year=None,
                    law_type="web",
                    category="web_search",
                    article_number=None,
                    text=r.content,
                    score=r.score,
                )
            )
            # Maintain dict representation in web_results for logging/API
            web_results.append(r.model_dump())

        logger.info(
            "web_search_node_completed",
            extra={
                "extra_fields": {
                    "num_results": len(citations),
                    "query": question,
                }
            },
        )

        return {
            **state,
            "citations": citations,
            "web_results": web_results,
            "retrieval_source": "web",
            "retrieval_empty": len(citations) == 0,
        }

    except Exception as e:
        logger.error(
            "web_search_node_failed_swallowing_exception",
            extra={"extra_fields": {"error": str(e)}},
        )
        return {
            **state,
            "citations": [],
            "web_results": [],
            "retrieval_source": "web",
            "retrieval_empty": True,
        }
