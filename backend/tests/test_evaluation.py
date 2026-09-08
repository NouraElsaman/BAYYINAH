"""
test_evaluation.py
==================
Comprehensive unit tests for the BAYYINAH evaluation framework.

Covers:
- Perfect retrieval
- Failed retrieval (no hits)
- Partial retrieval
- MRR calculation (single and multi-query)
- Latency aggregation (complete, missing keys, empty)
- Routing statistics (local, web, mixed, empty)
- Citation statistics (count, duplicates, coverage, missing rate)
- Report generation (dataclass fields, metadata)
- JSON serialisation (valid JSON, round-trip)
- Full Evaluator.evaluate() end-to-end with all metric groups
- pretty_print() output format
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from app.evaluation.metrics import (
    aggregate_latencies,
    answer_relevancy,
    citation_statistics,
    context_precision,
    context_recall,
    faithfulness_score,
    generation_metrics,
    hit_at_k,
    mean_reciprocal_rank,
    recall_at_k,
    reciprocal_rank,
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
from app.evaluation.evaluator import Evaluator


# ===========================================================================
# Helpers
# ===========================================================================

def _make_citation(chunk_id: str, text: str = "نص المادة", score: float = 0.9) -> MagicMock:
    """Create a simple Citation-like mock object."""
    c = MagicMock()
    c.chunk_id = chunk_id
    c.doc_id = chunk_id.split("_")[0]
    c.text = text
    c.score = score
    return c


def _make_pred(
    retrieved_ids: List[str],
    relevant_ids: List[str],
    answer: str = "الجواب",
    question: str = "السؤال",
    citations: Optional[List] = None,
    latency: Optional[Dict] = None,
    routing: Optional[Dict] = None,
) -> Dict[str, Any]:
    return {
        "question": question,
        "retrieved_ids": retrieved_ids,
        "expected_doc_ids": relevant_ids,
        "answer": answer,
        "citations": citations or [],
        "latency": latency or {},
        "routing": routing or {},
    }


def _make_bm(relevant_ids: List[str], question: str = "السؤال") -> Dict[str, Any]:
    return {"question": question, "relevant_ids": relevant_ids}


# ===========================================================================
# Retrieval metrics — hit_at_k
# ===========================================================================

class TestHitAtK:
    def test_perfect_hit_at_1(self):
        assert hit_at_k(["doc_1", "doc_2", "doc_3"], ["doc_1"], 1) == 1.0

    def test_miss_at_1_hit_at_5(self):
        retrieved = ["doc_2", "doc_3", "doc_1", "doc_4", "doc_5"]
        assert hit_at_k(retrieved, ["doc_1"], 1) == 0.0
        assert hit_at_k(retrieved, ["doc_1"], 5) == 1.0

    def test_no_relevant_ids_returns_zero(self):
        assert hit_at_k(["doc_1"], [], 5) == 0.0

    def test_empty_retrieved_returns_zero(self):
        assert hit_at_k([], ["doc_1"], 5) == 0.0

    def test_k_zero_returns_zero(self):
        assert hit_at_k(["doc_1"], ["doc_1"], 0) == 0.0

    def test_multiple_relevant_ids_partial_hit(self):
        retrieved = ["doc_1", "doc_2", "doc_3"]
        assert hit_at_k(retrieved, ["doc_1", "doc_99"], 1) == 1.0

    def test_failed_retrieval_no_match(self):
        assert hit_at_k(["doc_X", "doc_Y"], ["doc_1"], 5) == 0.0


# ===========================================================================
# Retrieval metrics — recall_at_k
# ===========================================================================

class TestRecallAtK:
    def test_perfect_recall(self):
        assert recall_at_k(["doc_1", "doc_2"], ["doc_1", "doc_2"], 10) == 1.0

    def test_partial_recall(self):
        result = recall_at_k(["doc_1", "doc_2", "doc_3"], ["doc_1", "doc_99"], 3)
        assert result == 0.5

    def test_zero_recall(self):
        assert recall_at_k(["doc_X"], ["doc_1"], 10) == 0.0

    def test_empty_relevant_ids(self):
        assert recall_at_k(["doc_1"], [], 10) == 0.0

    def test_k_limits_scope(self):
        # doc_3 is relevant but not in top-2
        result = recall_at_k(["doc_1", "doc_2", "doc_3"], ["doc_3"], 2)
        assert result == 0.0


# ===========================================================================
# Retrieval metrics — MRR
# ===========================================================================

class TestMRR:
    def test_first_result_relevant(self):
        assert reciprocal_rank(["doc_1", "doc_2"], ["doc_1"]) == 1.0

    def test_second_result_relevant(self):
        rr = reciprocal_rank(["doc_2", "doc_1"], ["doc_1"])
        assert abs(rr - 0.5) < 1e-6

    def test_no_relevant(self):
        assert reciprocal_rank(["doc_X"], ["doc_1"]) == 0.0

    def test_mrr_single_query_perfect(self):
        results = [{"retrieved_ids": ["doc_1"], "relevant_ids": ["doc_1"]}]
        assert mean_reciprocal_rank(results) == 1.0

    def test_mrr_single_query_miss(self):
        results = [{"retrieved_ids": ["doc_X"], "relevant_ids": ["doc_1"]}]
        assert mean_reciprocal_rank(results) == 0.0

    def test_mrr_multiple_queries(self):
        results = [
            {"retrieved_ids": ["doc_1"], "relevant_ids": ["doc_1"]},  # RR=1.0
            {"retrieved_ids": ["doc_X", "doc_1"], "relevant_ids": ["doc_1"]},  # RR=0.5
        ]
        mrr = mean_reciprocal_rank(results)
        assert abs(mrr - 0.75) < 1e-4

    def test_mrr_empty_returns_zero(self):
        assert mean_reciprocal_rank([]) == 0.0

    def test_retrieval_metrics_for_dataset_perfect(self):
        bm = [
            {"retrieved_ids": ["d1", "d2", "d3"], "relevant_ids": ["d1"]},
        ]
        m = retrieval_metrics_for_dataset(bm)
        assert m["hit_at_1"] == 1.0
        assert m["hit_at_5"] == 1.0
        assert m["recall_at_10"] == 1.0
        assert m["mrr"] == 1.0

    def test_retrieval_metrics_for_dataset_failed(self):
        bm = [
            {"retrieved_ids": ["dX", "dY"], "relevant_ids": ["d1"]},
        ]
        m = retrieval_metrics_for_dataset(bm)
        assert m["hit_at_1"] == 0.0
        assert m["hit_at_5"] == 0.0
        assert m["recall_at_10"] == 0.0
        assert m["mrr"] == 0.0

    def test_retrieval_metrics_for_dataset_partial(self):
        bm = [
            {"retrieved_ids": ["dX", "d1"], "relevant_ids": ["d1"]},  # hit@5 yes, hit@1 no
        ]
        m = retrieval_metrics_for_dataset(bm)
        assert m["hit_at_1"] == 0.0
        assert m["hit_at_5"] == 1.0

    def test_retrieval_metrics_for_dataset_empty(self):
        m = retrieval_metrics_for_dataset([])
        assert m == {"hit_at_1": 0.0, "hit_at_5": 0.0, "recall_at_10": 0.0, "mrr": 0.0}


# ===========================================================================
# Generation metrics
# ===========================================================================

class TestGenerationMetrics:
    def test_faithfulness_perfect_overlap(self):
        score = faithfulness_score("answer word", ["answer word context"])
        assert score == 1.0

    def test_faithfulness_no_overlap(self):
        score = faithfulness_score("hello world", ["completely different"])
        assert score == 0.0

    def test_faithfulness_empty_answer(self):
        assert faithfulness_score("", ["some context"]) == 0.0

    def test_faithfulness_empty_citations(self):
        assert faithfulness_score("answer", []) == 0.0

    def test_answer_relevancy_full(self):
        score = answer_relevancy("what is the law", "what is the law")
        assert score == 1.0

    def test_answer_relevancy_partial(self):
        score = answer_relevancy("law article", "what is the law")
        # question tokens: {what, is, the, law} — overlap: {law} → 0.25
        assert score == 0.25

    def test_answer_relevancy_empty(self):
        assert answer_relevancy("", "question") == 0.0

    def test_context_precision_all_relevant(self):
        assert context_precision(["d1", "d2"], ["d1", "d2"]) == 1.0

    def test_context_precision_none_relevant(self):
        assert context_precision(["dX", "dY"], ["d1"]) == 0.0

    def test_context_precision_empty_retrieved(self):
        assert context_precision([], ["d1"]) == 0.0

    def test_context_recall_all_found(self):
        assert context_recall(["d1", "d2", "d3"], ["d1", "d2"]) == 1.0

    def test_context_recall_none_found(self):
        assert context_recall(["dX"], ["d1", "d2"]) == 0.0

    def test_context_recall_empty_relevant(self):
        assert context_recall(["d1"], []) == 0.0

    def test_generation_metrics_bundle(self):
        m = generation_metrics(
            answer="law article",
            question="what is the law",
            citation_texts=["law article text"],
            retrieved_ids=["d1"],
            relevant_ids=["d1"],
        )
        assert set(m.keys()) == {"faithfulness", "answer_relevancy", "context_precision", "context_recall"}
        assert m["context_precision"] == 1.0
        assert m["context_recall"] == 1.0


# ===========================================================================
# Latency metrics
# ===========================================================================

class TestLatencyAggregation:
    def test_basic_average(self):
        timings = [
            {"retrieval_ms": 100.0, "generation_ms": 500.0, "total_ms": 650.0},
            {"retrieval_ms": 200.0, "generation_ms": 600.0, "total_ms": 850.0},
        ]
        r = aggregate_latencies(timings)
        assert r["avg_retrieval_ms"] == 150.0
        assert r["avg_generation_ms"] == 550.0
        assert r["avg_total_ms"] == 750.0
        assert r["num_runs"] == 2

    def test_missing_keys_ignored(self):
        timings = [
            {"retrieval_ms": 100.0},
            {"total_ms": 500.0},
        ]
        r = aggregate_latencies(timings)
        assert r["avg_retrieval_ms"] == 100.0
        assert r["avg_total_ms"] == 500.0
        assert r["avg_web_search_ms"] == 0.0  # never provided

    def test_empty_timings(self):
        r = aggregate_latencies([])
        assert r["avg_total_ms"] == 0.0
        assert r["num_runs"] == 0

    def test_percentiles(self):
        timings = [{"total_ms": float(v)} for v in [100, 200, 300, 400, 500]]
        r = aggregate_latencies(timings)
        # Floor-index: idx = max(0, int(5 * 50 / 100) - 1) = 1 → sorted[1] = 200.0
        assert r["p50_total_ms"] == 200.0
        assert r["p95_total_ms"] <= 500.0
        assert r["p95_total_ms"] > 0.0

    def test_web_search_latency(self):
        timings = [
            {"web_search_ms": 80.0, "total_ms": 900.0},
            {"web_search_ms": 120.0, "total_ms": 1100.0},
        ]
        r = aggregate_latencies(timings)
        assert r["avg_web_search_ms"] == 100.0


# ===========================================================================
# Routing statistics
# ===========================================================================

class TestRoutingStatistics:
    def test_all_local(self):
        events = [
            {"retrieval_source": "local", "retrieval_confidence": 0.8,
             "context_tokens": 300, "num_citations": 3},
            {"retrieval_source": "local", "retrieval_confidence": 0.6,
             "context_tokens": 200, "num_citations": 2},
        ]
        r = routing_statistics(events)
        assert r["num_local"] == 2
        assert r["num_web"] == 0
        assert r["web_fallback_pct"] == 0.0
        assert r["avg_confidence"] == pytest.approx(0.7, abs=1e-3)

    def test_all_web(self):
        events = [{"retrieval_source": "web", "retrieval_confidence": 0.1,
                   "context_tokens": 100, "num_citations": 1}]
        r = routing_statistics(events)
        assert r["num_web"] == 1
        assert r["num_local"] == 0
        assert r["web_fallback_pct"] == 100.0

    def test_mixed_routing(self):
        events = [
            {"retrieval_source": "local", "retrieval_confidence": 0.9,
             "context_tokens": 400, "num_citations": 5},
            {"retrieval_source": "web", "retrieval_confidence": 0.2,
             "context_tokens": 100, "num_citations": 1},
        ]
        r = routing_statistics(events)
        assert r["num_local"] == 1
        assert r["num_web"] == 1
        assert r["web_fallback_pct"] == 50.0
        assert r["total"] == 2

    def test_empty_events(self):
        r = routing_statistics([])
        assert r["total"] == 0
        assert r["web_fallback_pct"] == 0.0

    def test_missing_optional_keys(self):
        # Events without optional keys should not crash
        r = routing_statistics([{"retrieval_source": "local"}])
        assert r["avg_confidence"] == 0.0
        assert r["avg_context_tokens"] == 0.0


# ===========================================================================
# Citation statistics
# ===========================================================================

class TestCitationStatistics:
    def test_no_duplicates(self):
        preds = [
            {
                "citations": [_make_citation("c1"), _make_citation("c2")],
                "expected_doc_ids": ["c1", "c2"],
            }
        ]
        r = citation_statistics(preds)
        assert r["avg_citation_count"] == 2.0
        assert r["avg_duplicate_citations"] == 0.0

    def test_with_duplicates(self):
        preds = [
            {
                "citations": [_make_citation("c1"), _make_citation("c1")],
                "expected_doc_ids": [],
            }
        ]
        r = citation_statistics(preds)
        assert r["avg_citation_count"] == 2.0
        assert r["avg_duplicate_citations"] == 1.0

    def test_citation_coverage_full(self):
        preds = [
            {
                "citations": [_make_citation("doc1_chunk1"), _make_citation("doc2_chunk1")],
                "expected_doc_ids": ["doc1_chunk1", "doc2_chunk1"],
            }
        ]
        r = citation_statistics(preds)
        assert r["avg_citation_coverage"] == 1.0
        assert r["avg_missing_citation_rate"] == 0.0

    def test_citation_coverage_zero(self):
        preds = [
            {
                "citations": [_make_citation("doc99_chunk1")],
                "expected_doc_ids": ["doc1", "doc2"],
            }
        ]
        r = citation_statistics(preds)
        assert r["avg_citation_coverage"] == 0.0
        assert r["avg_missing_citation_rate"] == 1.0

    def test_empty_predictions(self):
        r = citation_statistics([])
        assert r["avg_citation_count"] == 0.0
        assert r["avg_duplicate_citations"] == 0.0

    def test_no_expected_doc_ids(self):
        preds = [{"citations": [_make_citation("c1")], "expected_doc_ids": []}]
        r = citation_statistics(preds)
        assert r["avg_citation_count"] == 1.0
        # Coverage / missing rate not computable without expected_doc_ids → 0
        assert r["avg_citation_coverage"] == 0.0

    def test_dict_citations_supported(self):
        """citation_statistics must handle dict-style citations."""
        preds = [
            {
                "citations": [{"chunk_id": "c1", "text": "text1"}, {"chunk_id": "c2", "text": "t2"}],
                "expected_doc_ids": ["c1"],
            }
        ]
        r = citation_statistics(preds)
        assert r["avg_citation_count"] == 2.0


# ===========================================================================
# Report — JSON serialisation
# ===========================================================================

class TestReportSerialisation:
    def test_to_dict_contains_all_keys(self):
        report = EvaluationReport()
        d = report.to_dict()
        assert set(d.keys()) == {"retrieval", "generation", "latency", "routing", "citation", "metadata"}

    def test_to_json_is_valid_json(self):
        report = EvaluationReport(metadata={"run_id": "test-1"})
        raw = report.to_json()
        parsed = json.loads(raw)
        assert parsed["metadata"]["run_id"] == "test-1"

    def test_to_json_round_trip(self):
        report = EvaluationReport(
            retrieval=RetrievalMetrics(hit_at_1=0.75, mrr=0.8),
            generation=GenerationMetrics(faithfulness=0.6),
            latency=LatencyMetrics(avg_total_ms=250.0, num_runs=10),
        )
        parsed = json.loads(report.to_json())
        assert parsed["retrieval"]["hit_at_1"] == 0.75
        assert parsed["generation"]["faithfulness"] == 0.6
        assert parsed["latency"]["avg_total_ms"] == 250.0

    def test_default_report_is_all_zeros(self):
        report = EvaluationReport()
        d = report.to_dict()
        assert d["retrieval"]["hit_at_1"] == 0.0
        assert d["latency"]["num_runs"] == 0


# ===========================================================================
# Report — pretty_print
# ===========================================================================

class TestReportPrettyPrint:
    def test_pretty_print_contains_sections(self):
        report = EvaluationReport(metadata={"run_id": "run-42"})
        text = report.pretty_print()
        assert "RETRIEVAL METRICS" in text
        assert "GENERATION METRICS" in text
        assert "LATENCY METRICS" in text
        assert "ROUTING METRICS" in text
        assert "CITATION METRICS" in text

    def test_pretty_print_contains_metadata(self):
        report = EvaluationReport(metadata={"run_id": "run-42"})
        text = report.pretty_print()
        assert "run-42" in text

    def test_pretty_print_returns_string(self):
        report = EvaluationReport()
        assert isinstance(report.pretty_print(), str)


# ===========================================================================
# Evaluator end-to-end
# ===========================================================================

class TestEvaluatorEndToEnd:
    """Full Evaluator.evaluate() integration test."""

    def _make_dataset(self):
        benchmark = [
            _make_bm(["doc1", "doc2"], "ما هي حقوق العامل؟"),
            _make_bm(["doc3"], "ما هي مدة إشعار إنهاء العقد؟"),
        ]
        predictions = [
            _make_pred(
                retrieved_ids=["doc1", "doc2", "docX"],
                relevant_ids=["doc1", "doc2"],
                answer="للعامل حق في الإجازة",
                question="ما هي حقوق العامل؟",
                citations=[_make_citation("doc1", "للعامل حق في الإجازة"), _make_citation("doc2")],
                latency={"retrieval_ms": 120.0, "generation_ms": 700.0, "total_ms": 850.0},
                routing={"retrieval_source": "local", "retrieval_confidence": 0.8,
                         "context_tokens": 300, "num_citations": 2},
            ),
            _make_pred(
                retrieved_ids=["docX"],
                relevant_ids=["doc3"],
                answer="مدة الإشعار شهر",
                question="ما هي مدة إشعار إنهاء العقد؟",
                citations=[_make_citation("docX")],
                latency={"retrieval_ms": 90.0, "web_search_ms": 80.0,
                         "generation_ms": 600.0, "total_ms": 800.0},
                routing={"retrieval_source": "web", "retrieval_confidence": 0.25,
                         "context_tokens": 150, "num_citations": 1},
            ),
        ]
        return benchmark, predictions

    def test_evaluate_returns_report(self):
        bm, preds = self._make_dataset()
        report = Evaluator().evaluate(bm, preds)
        assert isinstance(report, EvaluationReport)

    def test_evaluate_hit_at_1_partial(self):
        bm, preds = self._make_dataset()
        report = Evaluator().evaluate(bm, preds)
        # First query: doc1 is retrieved first → hit@1=1.0
        # Second query: docX not in relevant → hit@1=0.0
        # Average = 0.5
        assert report.retrieval.hit_at_1 == pytest.approx(0.5, abs=1e-3)

    def test_evaluate_mrr_positive(self):
        bm, preds = self._make_dataset()
        report = Evaluator().evaluate(bm, preds)
        assert report.retrieval.mrr > 0.0

    def test_evaluate_latency_num_runs(self):
        bm, preds = self._make_dataset()
        report = Evaluator().evaluate(bm, preds)
        assert report.latency.num_runs == 2

    def test_evaluate_routing_mixed(self):
        bm, preds = self._make_dataset()
        report = Evaluator().evaluate(bm, preds)
        assert report.routing.num_local == 1
        assert report.routing.num_web == 1
        assert report.routing.web_fallback_pct == 50.0

    def test_evaluate_citation_avg(self):
        bm, preds = self._make_dataset()
        report = Evaluator().evaluate(bm, preds)
        # 2 citations + 1 citation → avg 1.5
        assert report.citation.avg_citation_count == pytest.approx(1.5, abs=1e-3)

    def test_evaluate_metadata_attached(self):
        bm, preds = self._make_dataset()
        report = Evaluator(metadata={"dataset": "labor-bench-v1"}).evaluate(bm, preds)
        assert report.metadata["dataset"] == "labor-bench-v1"

    def test_evaluate_json_serialisable(self):
        bm, preds = self._make_dataset()
        report = Evaluator().evaluate(bm, preds)
        raw = report.to_json()
        parsed = json.loads(raw)
        assert "retrieval" in parsed

    def test_evaluate_empty_benchmark(self):
        report = Evaluator().evaluate([], [])
        assert report.retrieval.hit_at_1 == 0.0
        assert report.latency.num_runs == 0
