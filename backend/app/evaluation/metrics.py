"""
metrics.py
==========
Pure metric functions for the BAYYINAH evaluation framework.

All functions are stateless, side-effect-free, and do NOT import any
production graph, LLM, or IO module.  They operate exclusively on plain
Python data types (lists, dicts, floats).

Retrieval metrics
-----------------
hit_at_k            — Hit@k (1 if any relevant doc appears in top-k)
recall_at_k         — Recall@k (fraction of relevant docs found in top-k)
mean_reciprocal_rank— MRR across a set of queries

Generation metrics
------------------
faithfulness_score  — Lexical overlap of answer tokens with context tokens
answer_relevancy    — Lexical overlap of answer tokens with question tokens
context_precision   — Fraction of retrieved docs that are relevant
context_recall      — Fraction of expected docs that were retrieved

Latency metrics
---------------
aggregate_latencies — Aggregate timing measurements across multiple runs

Routing metrics
---------------
routing_statistics  — Counts, percentages, and averages over routing events

Citation metrics
----------------
citation_statistics — Count, duplicates, coverage, and missing-rate
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Internal text helpers (no external dependencies)
# ---------------------------------------------------------------------------

_ARABIC_DIGIT_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def _normalize(text: str) -> str:
    text = text.translate(_ARABIC_DIGIT_MAP)
    text = re.sub(r"[\u064B-\u0652]", "", text)  # strip Arabic diacritics
    return text.lower()


def _tokenize(text: str) -> set[str]:
    """Return a set of normalised, non-trivial tokens from *text*."""
    text = _normalize(text)
    tokens = re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", text)
    return {t for t in tokens if len(t) > 1}


# ===========================================================================
# Retrieval metrics
# ===========================================================================

def hit_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Return 1.0 if any relevant document ID appears in the top-*k* retrieved
    IDs, else 0.0.

    Parameters
    ----------
    retrieved_ids:
        Ranked list of retrieved document/chunk IDs (best first).
    relevant_ids:
        Ground-truth relevant IDs for this query.
    k:
        Cut-off rank.

    Returns
    -------
    float
        1.0 or 0.0.
    """
    if not relevant_ids or k <= 0:
        return 0.0
    top_k = set(retrieved_ids[:k])
    return 1.0 if top_k & set(relevant_ids) else 0.0


def recall_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Return the fraction of *relevant_ids* found in the top-*k* retrieved IDs.

    Parameters
    ----------
    retrieved_ids:
        Ranked list of retrieved document/chunk IDs.
    relevant_ids:
        Ground-truth relevant IDs.
    k:
        Cut-off rank.

    Returns
    -------
    float
        Value in [0.0, 1.0].  Returns 0.0 when *relevant_ids* is empty.
    """
    if not relevant_ids or k <= 0:
        return 0.0
    top_k = set(retrieved_ids[:k])
    found = sum(1 for rid in relevant_ids if rid in top_k)
    return round(found / len(relevant_ids), 4)


def reciprocal_rank(retrieved_ids: List[str], relevant_ids: List[str]) -> float:
    """Return the reciprocal rank of the **first** relevant document.

    Returns
    -------
    float
        1/rank of first hit, or 0.0 if none found.
    """
    relevant_set = set(relevant_ids)
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_set:
            return round(1.0 / rank, 6)
    return 0.0


def mean_reciprocal_rank(
    results: List[Dict[str, Any]],
) -> float:
    """Compute Mean Reciprocal Rank across multiple queries.

    Parameters
    ----------
    results:
        List of dicts, each with keys:

        ``retrieved_ids`` : List[str]
            Ordered list of retrieved document IDs.
        ``relevant_ids``  : List[str]
            Ground-truth relevant document IDs.

    Returns
    -------
    float
        MRR in [0.0, 1.0].  Returns 0.0 for an empty list.
    """
    if not results:
        return 0.0
    rr_sum = sum(
        reciprocal_rank(r["retrieved_ids"], r["relevant_ids"]) for r in results
    )
    return round(rr_sum / len(results), 6)


def retrieval_metrics_for_dataset(
    benchmark: List[Dict[str, Any]],
) -> Dict[str, float]:
    """Compute Hit@1, Hit@5, Recall@10, and MRR over a benchmark dataset.

    Parameters
    ----------
    benchmark:
        List of dicts, each with:

        ``retrieved_ids`` : List[str]
        ``relevant_ids``  : List[str]

    Returns
    -------
    dict
        Keys: ``hit_at_1``, ``hit_at_5``, ``recall_at_10``, ``mrr``.
    """
    if not benchmark:
        return {"hit_at_1": 0.0, "hit_at_5": 0.0, "recall_at_10": 0.0, "mrr": 0.0}

    n = len(benchmark)
    hit1 = sum(hit_at_k(r["retrieved_ids"], r["relevant_ids"], 1) for r in benchmark) / n
    hit5 = sum(hit_at_k(r["retrieved_ids"], r["relevant_ids"], 5) for r in benchmark) / n
    rec10 = sum(recall_at_k(r["retrieved_ids"], r["relevant_ids"], 10) for r in benchmark) / n
    mrr = mean_reciprocal_rank(benchmark)

    return {
        "hit_at_1": round(hit1, 4),
        "hit_at_5": round(hit5, 4),
        "recall_at_10": round(rec10, 4),
        "mrr": mrr,
    }


# ===========================================================================
# Generation metrics
# ===========================================================================

def faithfulness_score(answer: str, citation_texts: List[str]) -> float:
    """Lexical token-overlap faithfulness: fraction of answer tokens found
    in the retrieved context.

    This reuses the same lexical-overlap approach already used in
    ``nodes_verification._compute_faithfulness`` so the two are consistent.
    The implementation lives here as a standalone pure function to avoid
    duplicating verification *logic* (the production code owns its own copy;
    this one is evaluation-only and does not touch state).
    """
    if not answer or not citation_texts:
        return 0.0
    answer_tokens = _tokenize(answer)
    if not answer_tokens:
        return 0.0
    context_tokens: set[str] = set()
    for t in citation_texts:
        context_tokens |= _tokenize(t)
    if not context_tokens:
        return 0.0
    return round(len(answer_tokens & context_tokens) / len(answer_tokens), 4)


def answer_relevancy(answer: str, question: str) -> float:
    """Lexical overlap between answer tokens and question tokens.

    A high value means the answer directly addresses the question vocabulary.
    """
    if not answer or not question:
        return 0.0
    q_tokens = _tokenize(question)
    a_tokens = _tokenize(answer)
    if not q_tokens or not a_tokens:
        return 0.0
    overlap = q_tokens & a_tokens
    return round(len(overlap) / len(q_tokens), 4)


def context_precision(
    retrieved_ids: List[str], relevant_ids: List[str]
) -> float:
    """Fraction of retrieved documents that are actually relevant.

    Context Precision = |retrieved ∩ relevant| / |retrieved|
    """
    if not retrieved_ids:
        return 0.0
    relevant_set = set(relevant_ids)
    hits = sum(1 for rid in retrieved_ids if rid in relevant_set)
    return round(hits / len(retrieved_ids), 4)


def context_recall(
    retrieved_ids: List[str], relevant_ids: List[str]
) -> float:
    """Fraction of relevant documents that were retrieved.

    Context Recall = |retrieved ∩ relevant| / |relevant|
    """
    if not relevant_ids:
        return 0.0
    retrieved_set = set(retrieved_ids)
    hits = sum(1 for rid in relevant_ids if rid in retrieved_set)
    return round(hits / len(relevant_ids), 4)


def generation_metrics(
    *,
    answer: str,
    question: str,
    citation_texts: List[str],
    retrieved_ids: List[str],
    relevant_ids: List[str],
) -> Dict[str, float]:
    """Return all four generation quality metrics in one call."""
    return {
        "faithfulness": faithfulness_score(answer, citation_texts),
        "answer_relevancy": answer_relevancy(answer, question),
        "context_precision": context_precision(retrieved_ids, relevant_ids),
        "context_recall": context_recall(retrieved_ids, relevant_ids),
    }


# ===========================================================================
# Latency metrics
# ===========================================================================

def aggregate_latencies(
    timings: List[Dict[str, Optional[float]]],
) -> Dict[str, float]:
    """Aggregate per-run latency dicts into averages.

    Parameters
    ----------
    timings:
        List of dicts. Each dict may contain any subset of:

        ``retrieval_ms``  : float
        ``web_search_ms`` : float
        ``generation_ms`` : float
        ``total_ms``      : float

    Returns
    -------
    dict
        Keys: ``avg_retrieval_ms``, ``avg_web_search_ms``,
        ``avg_generation_ms``, ``avg_total_ms``, ``p50_total_ms``,
        ``p95_total_ms``, ``num_runs``.
        Values are rounded to 2 decimal places.  Missing keys in
        individual runs are ignored (treated as no data for that run).
    """
    keys = ("retrieval_ms", "web_search_ms", "generation_ms", "total_ms")
    buckets: Dict[str, List[float]] = {k: [] for k in keys}

    for t in timings:
        for k in keys:
            v = t.get(k)
            if v is not None:
                buckets[k].append(float(v))

    def _avg(vals: List[float]) -> float:
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    def _percentile(vals: List[float], p: int) -> float:
        if not vals:
            return 0.0
        sorted_vals = sorted(vals)
        idx = max(0, int(len(sorted_vals) * p / 100) - 1)
        return round(sorted_vals[idx], 2)

    return {
        "avg_retrieval_ms": _avg(buckets["retrieval_ms"]),
        "avg_web_search_ms": _avg(buckets["web_search_ms"]),
        "avg_generation_ms": _avg(buckets["generation_ms"]),
        "avg_total_ms": _avg(buckets["total_ms"]),
        "p50_total_ms": _percentile(buckets["total_ms"], 50),
        "p95_total_ms": _percentile(buckets["total_ms"], 95),
        "num_runs": len(timings),
    }


# ===========================================================================
# Routing metrics
# ===========================================================================

def routing_statistics(
    routing_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute aggregate routing behaviour statistics.

    Parameters
    ----------
    routing_events:
        List of dicts, one per pipeline invocation.  Each dict may contain:

        ``retrieval_source``    : str   — ``"local"`` or ``"web"``
        ``retrieval_confidence``: float
        ``context_tokens``      : int
        ``num_citations``       : int

    Returns
    -------
    dict
        ``num_local``, ``num_web``, ``total``, ``web_fallback_pct``,
        ``avg_confidence``, ``avg_context_tokens``, ``avg_citations``.
    """
    if not routing_events:
        return {
            "num_local": 0,
            "num_web": 0,
            "total": 0,
            "web_fallback_pct": 0.0,
            "avg_confidence": 0.0,
            "avg_context_tokens": 0.0,
            "avg_citations": 0.0,
        }

    total = len(routing_events)
    num_web = sum(1 for e in routing_events if e.get("retrieval_source") == "web")
    num_local = total - num_web

    confidences = [
        float(e["retrieval_confidence"])
        for e in routing_events
        if e.get("retrieval_confidence") is not None
    ]
    tokens = [
        float(e["context_tokens"])
        for e in routing_events
        if e.get("context_tokens") is not None
    ]
    citations = [
        float(e["num_citations"])
        for e in routing_events
        if e.get("num_citations") is not None
    ]

    def _avg(vals: List[float]) -> float:
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    return {
        "num_local": num_local,
        "num_web": num_web,
        "total": total,
        "web_fallback_pct": round(num_web / total * 100, 2),
        "avg_confidence": _avg(confidences),
        "avg_context_tokens": _avg(tokens),
        "avg_citations": _avg(citations),
    }


# ===========================================================================
# Citation metrics
# ===========================================================================

def citation_statistics(
    predictions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute citation quality metrics over a list of predictions.

    Parameters
    ----------
    predictions:
        List of dicts, one per answer.  Each dict may contain:

        ``citations``       : List — citation objects or dicts with a
                              ``chunk_id`` field.
        ``expected_doc_ids``: List[str] — ground-truth relevant IDs
                              (optional; required for coverage/missing-rate).

    Returns
    -------
    dict
        ``avg_citation_count``, ``avg_duplicate_citations``,
        ``avg_citation_coverage``, ``avg_missing_citation_rate``.
    """
    if not predictions:
        return {
            "avg_citation_count": 0.0,
            "avg_duplicate_citations": 0.0,
            "avg_citation_coverage": 0.0,
            "avg_missing_citation_rate": 0.0,
        }

    counts: List[float] = []
    dups: List[float] = []
    coverages: List[float] = []
    missing_rates: List[float] = []

    for pred in predictions:
        raw_cits = pred.get("citations", [])

        # Extract chunk_id or doc_id from citation objects or dicts
        def _get_id(c: Any) -> str:
            if hasattr(c, "chunk_id"):
                return c.chunk_id
            if isinstance(c, dict):
                return c.get("chunk_id") or c.get("doc_id") or ""
            return str(c)

        cit_ids = [_get_id(c) for c in raw_cits]
        unique_ids = set(cit_ids)

        counts.append(float(len(cit_ids)))
        dups.append(float(len(cit_ids) - len(unique_ids)))

        expected = pred.get("expected_doc_ids", [])
        if expected:
            expected_set = set(expected)
            # Doc IDs embedded in chunk_id (chunk_id often starts with doc_id)
            retrieved_doc_ids = set(
                _get_id(c).split("_")[0] if "_" in _get_id(c) else _get_id(c)
                for c in raw_cits
            ) | unique_ids
            covered = sum(1 for eid in expected_set if eid in retrieved_doc_ids or
                          any(eid in cid for cid in cit_ids))
            coverage = covered / len(expected_set)
            missing = 1.0 - coverage
            coverages.append(round(coverage, 4))
            missing_rates.append(round(missing, 4))

    def _avg(vals: List[float]) -> float:
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    return {
        "avg_citation_count": _avg(counts),
        "avg_duplicate_citations": _avg(dups),
        "avg_citation_coverage": _avg(coverages),
        "avg_missing_citation_rate": _avg(missing_rates),
    }
