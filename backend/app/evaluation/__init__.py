"""
evaluation
==========
End-to-End Evaluation & Benchmarking framework for the BAYYINAH Legal AI backend.

Sub-modules
-----------
metrics   — Pure functions for retrieval, generation, latency, routing,
            and citation metrics.
evaluator — Orchestration class that accepts benchmark data + predictions
            and produces an EvaluationReport.
report    — EvaluationReport dataclass with JSON export and console table.

This package is evaluation-only.  It does NOT import or modify any graph,
retrieval, reranking, generation, or API component.
"""
