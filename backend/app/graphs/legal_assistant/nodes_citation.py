"""
nodes_citation.py
=================
Citation Agent node for the BAYYINAH legal assistant graph.

Responsibilities
----------------
1. Accept the reranked citations already present in ``state["citations"]``.
2. Remove duplicate citations (same ``chunk_id``), preserving ranking order.
3. Trim each citation's text to at most ``CITATION_MAX_TEXT_TOKENS`` whitespace
   tokens; the trimmed text is stored on a *copy* of the Citation so that the
   original object is never mutated.
4. Enforce a total context token budget of ``CITATION_MAX_TOKENS`` across all
   selected citations; any citation that would push the total over budget is
   dropped.
5. Preserve all metadata (``article_number``, ``law_name``, ``law_number``,
   ``law_year``, ``law_type``, ``category``, ``score``).
6. Write the result back to ``state["citations"]`` and the total token count
   to ``state["context_tokens"]``.

What this node does NOT do
--------------------------
- It does not retrieve documents.
- It does not call any LLM.
- It does not rerank.
- It does not change the graph structure.
- It does not modify any API endpoint.

Token counting
--------------
We use a simple whitespace-split token approximation deliberately: the node
must work without any tokeniser library.  A real sub-word token count would
be ~30 % higher on average; the configurable budget accounts for this margin.
"""
from __future__ import annotations

from typing import List

from app.core.config import get_settings
from app.core.logging import get_logger
from app.graphs.legal_assistant.state import LegalAssistantState
from app.schemas.chat import Citation

logger = get_logger("bayyinah.graph.citation")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _token_count(text: str) -> int:
    """Return a fast whitespace-split token count for *text*."""
    return len(text.split())


def _trim_text(text: str, max_tokens: int) -> str:
    """Return *text* trimmed to at most *max_tokens* whitespace tokens.

    If the text is already within budget, it is returned unchanged.
    The trimmed result is joined with a single space and a trailing
    ellipsis marker is appended so downstream readers know the text
    was truncated.
    """
    if max_tokens <= 0:
        return ""
    tokens = text.split()
    if len(tokens) <= max_tokens:
        return text
    return " ".join(tokens[:max_tokens]) + " …"


def _dedup_citations(citations: List[Citation]) -> List[Citation]:
    """Remove citations with duplicate ``chunk_id`` values.

    The first occurrence in ranking order is kept; all later duplicates
    for the same ``chunk_id`` are discarded.
    """
    seen: set[str] = set()
    result: List[Citation] = []
    for c in citations:
        if c.chunk_id not in seen:
            seen.add(c.chunk_id)
            result.append(c)
    return result


def _apply_token_budget(
    citations: List[Citation],
    max_text_tokens: int,
    max_total_tokens: int,
) -> tuple[List[Citation], int]:
    """Trim each citation to *max_text_tokens* and enforce *max_total_tokens*.

    Returns
    -------
    (selected, total_tokens)
        ``selected`` is the list of (possibly text-trimmed) Citation copies
        that fit within the total budget.
        ``total_tokens`` is the sum of whitespace tokens across all selected
        citation texts.
    """
    selected: List[Citation] = []
    total: int = 0

    for c in citations:
        # Trim individual text first
        trimmed_text = _trim_text(c.text, max_text_tokens)
        this_tokens = _token_count(trimmed_text)

        # Check whether adding this citation would exceed the total budget
        if total + this_tokens > max_total_tokens:
            break  # citations are ranked; stop as soon as budget is exceeded

        # Create a new Citation with the (possibly trimmed) text; keep all
        # other fields identical so metadata is always preserved.
        selected.append(
            Citation(
                chunk_id=c.chunk_id,
                doc_id=c.doc_id,
                law_name=c.law_name,
                law_number=c.law_number,
                law_year=c.law_year,
                law_type=c.law_type,
                category=c.category,
                article_number=c.article_number,
                text=trimmed_text,
                score=c.score,
            )
        )
        total += this_tokens

    return selected, total


# ---------------------------------------------------------------------------
# Public node
# ---------------------------------------------------------------------------

from app.observability import trace_node


@trace_node("cite")
def citation_node(state: LegalAssistantState) -> LegalAssistantState:
    """Citation Agent: dedup → trim → budget → store.

    Reads
    -----
    state["citations"] : List[Citation]
        Reranked citations from the retrieval node.

    Writes
    ------
    state["citations"] : List[Citation]
        Deduplicated, trimmed, budget-constrained citations.
    state["context_tokens"] : int
        Total whitespace-token count of all selected citation texts.
    """
    settings = get_settings()
    raw: List[Citation] = state.get("citations", [])

    if not raw:
        logger.info(
            "citation_node_empty_input",
            extra={"extra_fields": {"num_input": 0}},
        )
        return {**state, "citations": [], "context_tokens": 0}

    # Step 1: deduplicate, preserving ranking order
    deduped = _dedup_citations(raw)

    # Step 2: trim texts + enforce token budget
    selected, total_tokens = _apply_token_budget(
        deduped,
        max_text_tokens=settings.CITATION_MAX_TEXT_TOKENS,
        max_total_tokens=settings.CITATION_MAX_TOKENS,
    )

    logger.info(
        "citation_node_completed",
        extra={
            "extra_fields": {
                "num_input": len(raw),
                "num_after_dedup": len(deduped),
                "num_selected": len(selected),
                "context_tokens": total_tokens,
            }
        },
    )

    return {
        **state,
        "citations": selected,
        "context_tokens": total_tokens,
    }
