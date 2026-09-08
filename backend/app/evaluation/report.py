"""
report.py
=========
EvaluationReport dataclass and rendering utilities.

Provides:

- ``EvaluationReport``   — structured container for all metric groups.
- ``to_json()``          — serialize to a JSON string.
- ``to_dict()``          — serialize to a plain dict.
- ``pretty_print()``     — formatted console table (no third-party deps).

This module has NO side-effects.  It does NOT import any graph, LLM, or
IO module.  It is evaluation-only.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Top-level report structure
# ---------------------------------------------------------------------------

@dataclass
class RetrievalMetrics:
    """Hit@1, Hit@5, Recall@10, MRR."""
    hit_at_1: float = 0.0
    hit_at_5: float = 0.0
    recall_at_10: float = 0.0
    mrr: float = 0.0


@dataclass
class GenerationMetrics:
    """Faithfulness, answer relevancy, context precision/recall."""
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0
    context_recall: float = 0.0


@dataclass
class LatencyMetrics:
    """Timing averages and percentiles (all values in milliseconds)."""
    avg_retrieval_ms: float = 0.0
    avg_web_search_ms: float = 0.0
    avg_generation_ms: float = 0.0
    avg_total_ms: float = 0.0
    p50_total_ms: float = 0.0
    p95_total_ms: float = 0.0
    num_runs: int = 0


@dataclass
class RoutingMetrics:
    """Routing behaviour statistics."""
    num_local: int = 0
    num_web: int = 0
    total: int = 0
    web_fallback_pct: float = 0.0
    avg_confidence: float = 0.0
    avg_context_tokens: float = 0.0
    avg_citations: float = 0.0


@dataclass
class CitationMetrics:
    """Citation quality statistics."""
    avg_citation_count: float = 0.0
    avg_duplicate_citations: float = 0.0
    avg_citation_coverage: float = 0.0
    avg_missing_citation_rate: float = 0.0


@dataclass
class EvaluationReport:
    """Complete evaluation report returned by the :class:`~app.evaluation.evaluator.Evaluator`.

    Attributes
    ----------
    retrieval:
        Retrieval quality metrics (Hit@k, Recall@k, MRR).
    generation:
        Generation quality metrics (faithfulness, relevancy, precision, recall).
    latency:
        Latency aggregates in milliseconds.
    routing:
        Routing behaviour statistics.
    citation:
        Citation quality statistics.
    metadata:
        Arbitrary key-value pairs for run identification (e.g., run_id,
        dataset_name, model_version).
    """
    retrieval: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    generation: GenerationMetrics = field(default_factory=GenerationMetrics)
    latency: LatencyMetrics = field(default_factory=LatencyMetrics)
    routing: RoutingMetrics = field(default_factory=RoutingMetrics)
    citation: CitationMetrics = field(default_factory=CitationMetrics)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a fully serialisable plain-dict representation."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Return a JSON string of the report.

        Parameters
        ----------
        indent:
            JSON indentation level (default 2).
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Console rendering
    # ------------------------------------------------------------------

    def pretty_print(self) -> str:  # noqa: PLR0914
        """Return a human-readable console table of the full report.

        Returns a multi-line string; call ``print(report.pretty_print())``
        to display it.
        """
        lines: list[str] = []

        def _hr(width: int = 62) -> str:
            return "─" * width

        def _section(title: str) -> None:
            lines.append("")
            lines.append(f"  {title}")
            lines.append("  " + _hr(58))

        def _row(label: str, value: Any, unit: str = "") -> None:
            unit_str = f" {unit}" if unit else ""
            lines.append(f"  {label:<36}  {value}{unit_str}")

        lines.append("")
        lines.append("=" * 62)
        lines.append("  BAYYINAH LEGAL AI — EVALUATION REPORT")
        if self.metadata:
            for k, v in self.metadata.items():
                lines.append(f"  {k}: {v}")
        lines.append("=" * 62)

        # ── Retrieval ──────────────────────────────────────────────────
        _section("RETRIEVAL METRICS")
        _row("Hit@1", f"{self.retrieval.hit_at_1:.4f}")
        _row("Hit@5", f"{self.retrieval.hit_at_5:.4f}")
        _row("Recall@10", f"{self.retrieval.recall_at_10:.4f}")
        _row("MRR", f"{self.retrieval.mrr:.6f}")

        # ── Generation ─────────────────────────────────────────────────
        _section("GENERATION METRICS")
        _row("Faithfulness", f"{self.generation.faithfulness:.4f}")
        _row("Answer Relevancy", f"{self.generation.answer_relevancy:.4f}")
        _row("Context Precision", f"{self.generation.context_precision:.4f}")
        _row("Context Recall", f"{self.generation.context_recall:.4f}")

        # ── Latency ────────────────────────────────────────────────────
        _section("LATENCY METRICS")
        _row("Avg Retrieval", f"{self.latency.avg_retrieval_ms:.2f}", "ms")
        _row("Avg Web Search", f"{self.latency.avg_web_search_ms:.2f}", "ms")
        _row("Avg Generation", f"{self.latency.avg_generation_ms:.2f}", "ms")
        _row("Avg Total", f"{self.latency.avg_total_ms:.2f}", "ms")
        _row("P50 Total", f"{self.latency.p50_total_ms:.2f}", "ms")
        _row("P95 Total", f"{self.latency.p95_total_ms:.2f}", "ms")
        _row("Runs", str(self.latency.num_runs))

        # ── Routing ────────────────────────────────────────────────────
        _section("ROUTING METRICS")
        _row("Total Requests", str(self.routing.total))
        _row("Local Retrievals", str(self.routing.num_local))
        _row("Web Fallbacks", str(self.routing.num_web))
        _row("Web Fallback %", f"{self.routing.web_fallback_pct:.2f}", "%")
        _row("Avg Retrieval Confidence", f"{self.routing.avg_confidence:.4f}")
        _row("Avg Context Tokens", f"{self.routing.avg_context_tokens:.1f}")
        _row("Avg Citations / Answer", f"{self.routing.avg_citations:.2f}")

        # ── Citation ───────────────────────────────────────────────────
        _section("CITATION METRICS")
        _row("Avg Citation Count", f"{self.citation.avg_citation_count:.2f}")
        _row("Avg Duplicate Citations", f"{self.citation.avg_duplicate_citations:.2f}")
        _row("Avg Citation Coverage", f"{self.citation.avg_citation_coverage:.4f}")
        _row("Avg Missing Citation Rate", f"{self.citation.avg_missing_citation_rate:.4f}")

        lines.append("")
        lines.append("=" * 62)
        lines.append("")
        return "\n".join(lines)
