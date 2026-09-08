"""
legal_evaluator.py
------------------
Sprint 2 updated evaluation harness.

Changes vs Sprint 1:
  - Now runs TWO evaluation passes:
      Pass A: Unfiltered (pure dense embedding, no law_type filter)
      Pass B: Filtered (domain-detected law_type filter applied)
  - Reports metrics for both passes and the delta.
  - Uses the fixed law_type values discovered in the Qdrant payload audit.
  - Logs which embedding backend is active (flag/sentence-transformers/hash).
"""

import csv
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add workspace directory to python path
ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings
from app.services.embedding_service import get_embedding_service
from app.services.retrieval_service import get_retrieval_service
from app.services.reranker_service import get_reranker_service

settings = get_settings()

# ─────────────────────────────────────────────────────────────────────────────
# Domain detection — lightweight keyword match to pick law_type filter
# Uses the actual Qdrant law_type values: 'civil', 'family', 'labor', 'criminal'
# ─────────────────────────────────────────────────────────────────────────────

_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "labor": ["عامل", "عمال", "فصل", "أجر", "مرتب", "صاحب العمل", "إجازة",
              "استقالة", "إنهاء الخدمة", "نقابة", "ساعات العمل", "عقد عمل",
              "تأمينات", "معاش", "إضراب", "موظف", "اجر", "مكافاه"],
    "family": ["زواج", "طلاق", "حضانة", "نفقة", "خلع", "ميراث", "وصية",
               "نسب", "زوجة", "زوج", "أولاد", "ولاية", "مهر", "عدة",
               "رؤية الأبناء"],
    "criminal": ["جريمة", "سرقة", "قتل", "ضرب", "نصب", "احتيال", "عقوبة",
                 "سجن", "غرامة", "جنحة", "جناية", "بلاغ", "نيابة"],
    "civil": ["عقد", "تعويض", "ملكية", "بيع", "شراء", "ضرر", "مسؤولية",
              "دين", "التزام", "إيجار", "مستأجر", "مؤجر", "شقة"],
}


def _normalize_arabic(text: str) -> str:
    text = re.sub(r"[\u064B-\u0652]", "", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ة", "ه")
    return text.strip().lower()


def detect_law_type(question: str) -> Optional[str]:
    """Return Qdrant law_type value for the question, or None if unknown."""
    norm = _normalize_arabic(question)
    scores: Dict[str, int] = {k: 0 for k in _DOMAIN_KEYWORDS}
    for domain, kws in _DOMAIN_KEYWORDS.items():
        for kw in kws:
            if _normalize_arabic(kw) in norm:
                scores[domain] += 1
    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] > 0 else None


# ─────────────────────────────────────────────────────────────────────────────
# Metrics helpers
# ─────────────────────────────────────────────────────────────────────────────

def normalize_law_name(name: str) -> str:
    if not name:
        return ""
    name = name.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    name = name.replace("ى", "ي").replace("ة", "ه")
    name = name.replace("_", "").replace(" ", "").replace("-", "")
    return name.strip().lower()


def compute_metrics(results_per_query: List[Optional[int]], total: int) -> Dict[str, float]:
    """Compute Hit@K, Recall@K, MRR, nDCG@5 from a list of match ranks (None = no match)."""
    h1 = h3 = h5 = r5 = r10 = mrr = ndcg = 0.0
    for rank in results_per_query:
        if rank is None:
            continue
        if rank <= 1: h1 += 1
        if rank <= 3: h3 += 1
        if rank <= 5: h5 += 1
        if rank <= 5: r5 += 1
        if rank <= 10: r10 += 1
        mrr += 1.0 / rank
        if rank <= 5:
            ndcg += 1.0 / math.log2(rank + 1)
    return {
        "Hit@1":    round(h1 / total, 4),
        "Hit@3":    round(h3 / total, 4),
        "Hit@5":    round(h5 / total, 4),
        "Recall@5": round(r5 / total, 4),
        "Recall@10":round(r10 / total, 4),
        "MRR":      round(mrr / total, 4),
        "nDCG@5":   round(ndcg / total, 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main evaluation
# ─────────────────────────────────────────────────────────────────────────────

def run_evaluation() -> None:
    embedder = get_embedding_service()
    retriever = get_retrieval_service()
    reranker = get_reranker_service()  # pre-warm: loads model once

    # Report which backend is powering embeddings
    backend = embedder.backend
    is_semantic = embedder.is_semantic
    print(f"\n[Embedding backend] {backend}  |  semantic={is_semantic}")
    if not is_semantic:
        print("[WARNING] Hash-based fallback is active — retrieval quality will be 0%.")
        print("          Install BAAI/bge-m3 before interpreting results.\n")

    csv_path = ROOT / "backend" / "data" / "golden_test_set.csv"
    if not csv_path.exists():
        print(f"Error: Golden Test Set not found at {csv_path}")
        sys.exit(1)

    print(f"Loading test set from {csv_path}...")
    queries = []
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            queries.append(row)

    total = len(queries)
    print(f"Loaded {total} evaluation queries.\n")

    # Pre-warm services (load models once before the evaluation loops)
    print("[Pre-warming] Loading embedding model...")
    embedder.embed_query("تجربة")
    print("[Pre-warming] Loading cross-encoder reranker model...")
    reranker._load()
    print("[Pre-warming] Done.\n")

    # ── Pass A: Unfiltered ──────────────────────────────────────────────────
    print("=" * 60)
    print("PASS A: Unfiltered (dense only, no law_type filter)")
    print("=" * 60)
    ranks_unfiltered: List[Optional[int]] = []
    snapshots_a = []
    t0 = time.time()

    for idx, q in enumerate(queries, 1):
        question = q["question"]
        expected_law = q["expected_law"]
        expected_article = q["expected_article"]
        t_start = time.time()

        try:
            vector = embedder.embed_query(question)
            # Pass A: dense-only (no BM25 to avoid 38k-doc global index build)
            candidates = retriever.search(
                query_vector=vector,
                query_text=None,
                category=None,
                law_type=None,
                top_k=20,
                score_threshold=0.10,
            )
            results = reranker.rerank(question, candidates, top_n=10)
        except Exception as e:
            print(f"  Search error q{idx}: {e}", flush=True)
            results = []

        norm_exp_law = normalize_law_name(expected_law)
        match_rank = None
        snap = []

        for rank_idx, c in enumerate(results, 1):
            norm_ret_law = normalize_law_name(c.law_name)
            is_match = (
                norm_exp_law in norm_ret_law or norm_ret_law in norm_exp_law
            ) and str(c.article_number) == str(expected_article)
            snap.append({"rank": rank_idx, "law": c.law_name, "article": c.article_number,
                         "score": c.score, "is_match": is_match})
            if is_match and match_rank is None:
                match_rank = rank_idx

        ranks_unfiltered.append(match_rank)
        snapshots_a.append({"question": question, "expected_law": expected_law,
                             "expected_article": expected_article, "results": snap})

        q_dur = time.time() - t_start
        elapsed = time.time() - t0
        avg_dur = elapsed / idx
        est_rem = avg_dur * (total - idx)
        est_min, est_sec = int(est_rem // 60), int(est_rem % 60)
        print(f"  [Pass A] {idx}/{total} | Match Rank: {match_rank} | Query Latency: {q_dur:.2f}s | Avg: {avg_dur:.2f}s | Est. Rem: {est_min}m {est_sec}s", flush=True)

    dur_a = time.time() - t0
    metrics_a = compute_metrics(ranks_unfiltered, total)

    # ── Pass B: Domain-filtered ─────────────────────────────────────────────
    print()
    print("=" * 60)
    print("PASS B: Domain-filtered (law_type filter applied)")
    print("=" * 60)
    ranks_filtered: List[Optional[int]] = []
    snapshots_b = []
    t1 = time.time()

    for idx, q in enumerate(queries, 1):
        question = q["question"]
        expected_law = q["expected_law"]
        expected_article = q["expected_article"]
        law_type = detect_law_type(question)
        t_start = time.time()

        try:
            vector = embedder.embed_query(question)
            # Pass B: hybrid search (dense + BM25 with domain filter)
            candidates = retriever.search(
                query_vector=vector,
                query_text=question,
                category=None,
                law_type=law_type,
                top_k=20,
                score_threshold=0.10,
            )
            results = reranker.rerank(question, candidates, top_n=10)
        except Exception as e:
            print(f"  Search error q{idx}: {e}", flush=True)
            results = []

        norm_exp_law = normalize_law_name(expected_law)
        match_rank = None
        snap = []

        for rank_idx, c in enumerate(results, 1):
            norm_ret_law = normalize_law_name(c.law_name)
            is_match = (
                norm_exp_law in norm_ret_law or norm_ret_law in norm_exp_law
            ) and str(c.article_number) == str(expected_article)
            snap.append({"rank": rank_idx, "law": c.law_name, "article": c.article_number,
                         "score": c.score, "law_type_filter": law_type, "is_match": is_match})
            if is_match and match_rank is None:
                match_rank = rank_idx

        ranks_filtered.append(match_rank)
        snapshots_b.append({"question": question, "expected_law": expected_law,
                             "expected_article": expected_article,
                             "law_type_filter": law_type, "results": snap})

        q_dur = time.time() - t_start
        elapsed = time.time() - t1
        avg_dur = elapsed / idx
        est_rem = avg_dur * (total - idx)
        est_min, est_sec = int(est_rem // 60), int(est_rem % 60)
        print(f"  [Pass B] {idx}/{total} | Match Rank: {match_rank} | Query Latency: {q_dur:.2f}s | Avg: {avg_dur:.2f}s | Est. Rem: {est_min}m {est_sec}s", flush=True)

    dur_b = time.time() - t1
    metrics_b = compute_metrics(ranks_filtered, total)

    # ── Final report ────────────────────────────────────────────────────────
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_queries": total,
        "embedding_backend": backend,
        "is_semantic": is_semantic,
        "pass_a_unfiltered": {
            "duration_seconds": round(dur_a, 2),
            "avg_latency_ms": round((dur_a / total) * 1000, 2),
            "metrics": metrics_a,
        },
        "pass_b_filtered": {
            "duration_seconds": round(dur_b, 2),
            "avg_latency_ms": round((dur_b / total) * 1000, 2),
            "metrics": metrics_b,
        },
        "delta": {
            k: round(metrics_b[k] - metrics_a[k], 4) for k in metrics_a
        },
    }

    data_dir = ROOT / "backend" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    with open(data_dir / "evaluation_report_sprint3.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    with open(data_dir / "retrieval_snapshot_sprint3_a.json", "w", encoding="utf-8") as f:
        json.dump(snapshots_a, f, indent=2, ensure_ascii=False)

    with open(data_dir / "retrieval_snapshot_sprint3_b.json", "w", encoding="utf-8") as f:
        json.dump(snapshots_b, f, indent=2, ensure_ascii=False)

    # Print summary
    print()
    print("=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Embedding backend : {backend}  (semantic={is_semantic})")
    print(f"Total queries     : {total}")
    print()
    print(f"{'Metric':<12} {'Pass A (No filter)':>20} {'Pass B (Filtered)':>20} {'Delta':>10}")
    print("-" * 65)
    for k in ["Hit@1", "Hit@3", "Hit@5", "Recall@10", "MRR", "nDCG@5"]:
        a = metrics_a[k]
        b = metrics_b[k]
        d = b - a
        sign = "+" if d >= 0 else ""
        print(f"{k:<12} {a:>20.2%} {b:>20.2%} {sign}{d:>9.2%}")
    print()
    print(f"Reports saved to {data_dir}")


if __name__ == "__main__":
    run_evaluation()
