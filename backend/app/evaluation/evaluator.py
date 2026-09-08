"""
evaluator.py
============
Orchestration class for the BAYYINAH evaluation framework.

The :class:`Evaluator` accepts:

- A **benchmark dataset** — list of queries with expected document IDs.
- A **predictions list**  — pipeline outputs (citations, answers, timings,
  routing metadata) for each query.

It returns a single :class:`~app.evaluation.report.EvaluationReport`
containing all five metric groups.

This class is evaluation-only.  It does NOT import or modify any graph,
retrieval, reranking, generation, or API component.

Example
-------
::

    from app.evaluation.evaluator import Evaluator

    benchmark = [
        {
            "question": "ما هي مدة إشعار إنهاء العقد؟",
            "relevant_ids": ["doc_001", "doc_003"],
        },
    ]

    predictions = [
        {
            "question": "ما هي مدة إشعار إنهاء العقد؟",
            "retrieved_ids": ["doc_001", "doc_002", "doc_003"],
            "answer": "مدة الإشعار شهر واحد.",
            "citations": [...],          # Citation objects or dicts
            "expected_doc_ids": ["doc_001", "doc_003"],
            "latency": {
                "retrieval_ms": 120.0,
                "generation_ms": 800.0,
                "total_ms": 950.0,
            },
            "routing": {
                "retrieval_source": "local",
                "retrieval_confidence": 0.72,
                "context_tokens": 320,
                "num_citations": 3,
            },
        },
    ]

    report = Evaluator(metadata={"run_id": "v1.0"}).evaluate(benchmark, predictions)
    print(report.pretty_print())
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.evaluation.metrics import (
    aggregate_latencies,
    citation_statistics,
    generation_metrics,
    retrieval_metrics_for_dataset,
    routing_statistics,
)
from app.evaluation.report import (
    CitationMetrics,
    EvaluationReport,
    GenerationMetrics,
    LatencyMetrics,
    RetrievalMetrics,
    RoutingMetrics,
)


class Evaluator:
    """Compute a full :class:`~app.evaluation.report.EvaluationReport`.

    Parameters
    ----------
    metadata:
        Optional key-value metadata attached to the report (e.g., run_id,
        model_version, dataset_name).
    """

    def __init__(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.metadata: Dict[str, Any] = metadata or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        benchmark: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]],
    ) -> EvaluationReport:
        """Evaluate *predictions* against the *benchmark* dataset.

        Parameters
        ----------
        benchmark:
            List of dicts, one per query.  Each dict **must** contain:

            ``relevant_ids`` : List[str]
                Ground-truth relevant document / chunk IDs.

            And *may* contain:

            ``question`` : str

        predictions:
            List of dicts, one per query, in the **same order** as
            *benchmark*.  Each dict may contain:

            ``retrieved_ids``   : List[str]   — ordered retrieved IDs.
            ``answer``          : str          — generated answer text.
            ``citations``       : list         — Citation objects or dicts.
            ``expected_doc_ids``: List[str]    — mirrors benchmark relevant_ids.
            ``latency``         : dict         — timing breakdown (ms).
            ``routing``         : dict         — routing metadata.
            ``question``        : str          — query text.

        Returns
        -------
        EvaluationReport
        """
        # ── 1. Retrieval metrics ───────────────────────────────────────
        retrieval_inputs = self._build_retrieval_inputs(benchmark, predictions)
        ret_metrics = retrieval_metrics_for_dataset(retrieval_inputs)

        # ── 2. Generation metrics (averaged across predictions) ────────
        gen_metrics = self._compute_generation_metrics(benchmark, predictions)

        # ── 3. Latency metrics ─────────────────────────────────────────
        timings = [p.get("latency", {}) for p in predictions]
        lat_agg = aggregate_latencies(timings)

        # ── 4. Routing metrics ─────────────────────────────────────────
        routing_events = [p.get("routing", {}) for p in predictions]
        route_stats = routing_statistics(routing_events)

        # ── 5. Citation metrics ────────────────────────────────────────
        cit_stats = citation_statistics(predictions)

        # ── Assemble report ────────────────────────────────────────────
        return EvaluationReport(
            retrieval=RetrievalMetrics(**ret_metrics),
            generation=GenerationMetrics(**gen_metrics),
            latency=LatencyMetrics(**lat_agg),
            routing=RoutingMetrics(**route_stats),
            citation=CitationMetrics(**cit_stats),
            metadata=self.metadata,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_retrieval_inputs(
        benchmark: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Zip benchmark relevant_ids with prediction retrieved_ids."""
        result: List[Dict[str, Any]] = []
        for bm, pred in zip(benchmark, predictions):
            result.append({
                "retrieved_ids": pred.get("retrieved_ids", []),
                "relevant_ids": bm.get("relevant_ids", []),
            })
        return result

    @staticmethod
    def _compute_generation_metrics(
        benchmark: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Average generation metrics across all predictions."""
        faithfulness_vals: List[float] = []
        relevancy_vals: List[float] = []
        precision_vals: List[float] = []
        recall_vals: List[float] = []

        for bm, pred in zip(benchmark, predictions):
            answer = pred.get("answer", "")
            question = pred.get("question", "") or bm.get("question", "")
            citations = pred.get("citations", [])

            # Extract text from Citation objects or dicts
            def _text(c: Any) -> str:
                if hasattr(c, "text"):
                    return c.text
                if isinstance(c, dict):
                    return c.get("text", "")
                return str(c)

            citation_texts = [_text(c) for c in citations]
            retrieved_ids = pred.get("retrieved_ids", [])
            relevant_ids = bm.get("relevant_ids", [])

            m = generation_metrics(
                answer=answer,
                question=question,
                citation_texts=citation_texts,
                retrieved_ids=retrieved_ids,
                relevant_ids=relevant_ids,
            )
            faithfulness_vals.append(m["faithfulness"])
            relevancy_vals.append(m["answer_relevancy"])
            precision_vals.append(m["context_precision"])
            recall_vals.append(m["context_recall"])

        def _avg(vals: List[float]) -> float:
            return round(sum(vals) / len(vals), 4) if vals else 0.0

        return {
            "faithfulness": _avg(faithfulness_vals),
            "answer_relevancy": _avg(relevancy_vals),
            "context_precision": _avg(precision_vals),
            "context_recall": _avg(recall_vals),
        }
