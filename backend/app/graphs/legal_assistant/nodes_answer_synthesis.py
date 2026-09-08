"""
nodes_answer_synthesis.py
=========================
Answer Synthesis node for the BAYYINAH legal assistant graph.
Responsible for merging local retrieval citations with Web Search fallback citations,
deduplicating them, and updating the state with a single unified list.
"""
from __future__ import annotations

from typing import List

from app.core.logging import get_logger
from app.graphs.legal_assistant.state import LegalAssistantState
from app.schemas.chat import Citation

logger = get_logger("bayyinah.graph.answer_synthesis")


from app.observability import trace_node


@trace_node("answer_synthesis")
def answer_synthesis_node(state: LegalAssistantState) -> LegalAssistantState:
    """Merges local citations and web search results, deduplicates by chunk_id
    and URL, and updates state['citations']."""
    # 1. Retrieve local citations
    # If the wrapped web_search_node ran, it saved local citations to "local_citations"
    local_citations = state.get("local_citations")
    if local_citations is None:
        # Fallback if wrapped node didn't run: filter non-web citations from state["citations"]
        local_citations = [
            c for c in state.get("citations", [])
            if getattr(c, "law_type", "") != "web"
        ]

    # 2. Retrieve and normalize web results
    web_results = state.get("web_results", [])
    web_citations: List[Citation] = []

    for idx, r in enumerate(web_results):
        if isinstance(r, dict):
            title = r.get("title") or "مصدر ويب خارجي"
            url = r.get("url") or ""
            content = r.get("content") or ""
            score = r.get("score", 1.0)
        else:
            title = getattr(r, "title", None) or "مصدر ويب خارجي"
            url = getattr(r, "url", None) or ""
            content = getattr(r, "content", None) or ""
            score = getattr(r, "score", 1.0)

        # Build Citation object preserving all standard fields
        web_citations.append(
            Citation(
                chunk_id=f"web_{idx}",
                doc_id=f"web_doc_{idx}",
                law_name=title,
                law_number=None,
                law_year=None,
                law_type="web",
                category="web_search",
                article_number=None,
                text=content,
                score=float(score) if score is not None else 1.0,
            )
        )

    # 3. If no web results exist, return state with updated retrieval_empty flag
    if not web_citations:
        cleaned_state = {
            **state,
            "retrieval_empty": len(local_citations) == 0,
        }
        cleaned_state.pop("local_citations", None)
        return cleaned_state

    # 4. Merge and deduplicate
    seen_chunk_ids = set()
    seen_urls = set()
    merged_citations: List[Citation] = []

    # Keep local citations first (preserving ranking order)
    for c in local_citations:
        if c.chunk_id not in seen_chunk_ids:
            seen_chunk_ids.add(c.chunk_id)
            merged_citations.append(c)

    # Append only new web citations
    for idx, c in enumerate(web_citations):
        url = ""
        if idx < len(web_results):
            r = web_results[idx]
            url = r.get("url", "") if isinstance(r, dict) else getattr(r, "url", "")

        is_dup = False
        if c.chunk_id in seen_chunk_ids:
            is_dup = True
        if url and url in seen_urls:
            is_dup = True

        if not is_dup:
            seen_chunk_ids.add(c.chunk_id)
            if url:
                seen_urls.add(url)
            merged_citations.append(c)

    logger.info(
        "answer_synthesis_node_completed",
        extra={
            "extra_fields": {
                "num_local": len(local_citations),
                "num_web": len(web_citations),
                "num_merged": len(merged_citations),
            }
        },
    )

    new_state = {
        **state,
        "citations": merged_citations,
        "retrieval_empty": len(merged_citations) == 0,
    }
    new_state.pop("local_citations", None)
    return new_state
