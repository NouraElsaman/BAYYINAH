from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graphs.contract_analysis.nodes_chunking import chunk_node
from app.graphs.contract_analysis.nodes_clause_analysis import analyze_clauses_node
from app.graphs.contract_analysis.nodes_extraction import extract_node
from app.graphs.contract_analysis.nodes_risk_detection import detect_risks_node
from app.graphs.contract_analysis.nodes_summary import summarize_node
from app.graphs.contract_analysis.state import ContractAnalysisState


def build_contract_analysis_graph():
    graph = StateGraph(ContractAnalysisState)

    graph.add_node("extract", extract_node)
    graph.add_node("chunk", chunk_node)
    graph.add_node("analyze_clauses", analyze_clauses_node)
    graph.add_node("detect_risks", detect_risks_node)
    graph.add_node("summarize", summarize_node)

    graph.set_entry_point("extract")
    graph.add_edge("extract", "chunk")
    graph.add_edge("chunk", "analyze_clauses")
    graph.add_edge("analyze_clauses", "detect_risks")
    graph.add_edge("detect_risks", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()


contract_analysis_graph = build_contract_analysis_graph()
