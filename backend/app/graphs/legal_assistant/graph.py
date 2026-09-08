from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.core.config import get_settings
from app.graphs.legal_assistant.nodes_answer_synthesis import answer_synthesis_node
from app.graphs.legal_assistant.nodes_citation import citation_node
from app.graphs.legal_assistant.nodes_domain import detect_domain_node
from app.graphs.legal_assistant.nodes_query_expansion import query_expansion_node
from app.graphs.legal_assistant.nodes_generation import generate_answer_node
from app.graphs.legal_assistant.nodes_retrieval import retrieve_node
from app.graphs.legal_assistant.nodes_web_search import web_search_node
from app.graphs.legal_assistant.nodes_verification import verify_node
from app.graphs.legal_assistant.state import LegalAssistantState


def verify_retrieval_confidence(state: LegalAssistantState) -> str:
    """Routes execution to web search if confidence is below fallback threshold,
    otherwise proceeds straight to answer synthesis."""
    settings = get_settings()
    # Default to 0.0 if not present to safely trigger fallback
    confidence = state.get("retrieval_confidence", 0.0)
    if confidence >= settings.CONFIDENCE_FALLBACK_THRESHOLD:
        return "answer_synthesis"
    return "web_search"


async def wrapped_web_search_node(state: LegalAssistantState) -> LegalAssistantState:
    """Wraps web search node to preserve local citations before search results
    overwrite them, allowing synthesis to merge both lists."""
    local_citations = state.get("citations", [])
    result = await web_search_node(state)
    result["local_citations"] = local_citations
    return result


def build_legal_assistant_graph():
    graph = StateGraph(LegalAssistantState)

    graph.add_node("detect_domain", detect_domain_node)
    graph.add_node("query_expansion", query_expansion_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("web_search", wrapped_web_search_node)  # Wrapped for state preservation
    graph.add_node("answer_synthesis", answer_synthesis_node)  # Answer Synthesis Node (Phase 2 Task 8)
    graph.add_node("cite", citation_node)          # Citation Agent (Phase 2 Task 5)
    graph.add_node("generate_answer", generate_answer_node)
    graph.add_node("verify", verify_node)

    graph.set_entry_point("detect_domain")
    graph.add_edge("detect_domain", "query_expansion")
    graph.add_edge("query_expansion", "retrieve")
    
    # Conditional routing after retrieval based on confidence score
    graph.add_conditional_edges(
        "retrieve",
        verify_retrieval_confidence,
        {
            "answer_synthesis": "answer_synthesis",
            "web_search": "web_search",
        }
    )
    graph.add_edge("web_search", "answer_synthesis")
    graph.add_edge("answer_synthesis", "cite")
    graph.add_edge("cite", "generate_answer")
    graph.add_edge("generate_answer", "verify")
    graph.add_edge("verify", END)

    return graph.compile()


# Singleton compiled graph
legal_assistant_graph = build_legal_assistant_graph()
