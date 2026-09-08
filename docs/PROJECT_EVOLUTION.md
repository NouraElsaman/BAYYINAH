# BAYYINAH — Project Evolution

A chronological record of the major engineering decisions that shaped BAYYINAH from its initial DigitLaw prototype to its current production architecture.

> **Reading guide:** Each milestone follows the structure — **Problem → Investigation → Options Considered → Evidence → Decision → Current Impact**. Entries clearly mark what was IMPLEMENTED vs. TESTED AND REJECTED.

---

## 1. Project Overview (Current State)

BAYYINAH is an Arabic-first Egyptian legal AI assistant. It answers legal questions in Egyptian colloquial dialect, grounded exclusively in a corpus of 43,582 Egyptian legal articles. The system refuses to answer questions not supported by the retrieved corpus, and explicitly attributes every answer to the relevant law articles.

The platform consists of:
- A **FastAPI + LangGraph** backend implementing a multi-node RAG pipeline
- A **Next.js 14** frontend with Arabic RTL layout and streaming SSE
- **BAAI/bge-m3** dense embeddings + BM25 sparse retrieval fused via RRF
- **BAAI/bge-reranker-v2-m3** cross-encoder reranking
- **Qdrant Cloud** as the vector database
- **Groq** as the LLM API provider (model: `openai/gpt-oss-120b`)
- **Render** as the deployment platform

---

## 2. Phase 0 — DigitLaw Origin

**Before:** The project started as "DigitLaw" — a general Egyptian legal information system with a FastAPI backend, basic Qdrant retrieval, and initial Groq generation.

**Architecture at this point:**
- Single-vector dense retrieval only
- No reranking
- No BM25/hybrid search
- No domain routing
- No conversation memory
- Basic generation without grounding guardrails
- Frontend: minimal, no landing page

**What existed:** A working but unoptimized RAG pipeline capable of basic Arabic legal question answering.

---

## 3. Phase 1 — BAYYINAH Rebranding and UI/UX Overhaul

**Problem:** DigitLaw lacked a professional identity, a public-facing landing page, and a polished chat experience suitable for demo or portfolio use.

**Decision:** Rebrand to BAYYINAH (بيّنة — Arabic for "evidence" or "proof"). The word is legally significant in Arabic jurisprudence, directly relevant to a legal AI.

**Work completed during this phase:**
- Design system derived from the official logo (`#0b3c5d` Navy, `#bda054` Gold)
- Full SaaS landing page (9 sections including services, how-it-works, FAQ, testimonials)
- Enhanced chat interface: RTL layout, Cairo font, collapsible sidebar, streaming SSE, Arabic markdown rendering, follow-up suggestions
- Contract analysis workspace: 3-column responsive layout, drag-and-drop upload, risk gauge, clause filtering
- Framer Motion animations for landing page hero
- WCAG accessibility compliance (aria-live, aria-label, role="log")
- Light/Dark mode with CSS custom properties

**Status:** IMPLEMENTED — all frontend work is current production code.

---

## 4. Phase 2 — Hybrid Retrieval Architecture

### Problem
Dense-only retrieval using BGE-M3 embeddings missed lexically specific legal terms. Arabic legal vocabulary uses precise article numbering (e.g., "المادة 69") and exact law names that dense vectors do not reliably surface.

### Investigation
Added BM25 sparse retrieval alongside dense. Tested multiple fusion strategies.

### Decision: Reciprocal Rank Fusion (RRF)
**Why RRF over weighted sum:** RRF is rank-based, not score-based. This matters because BGE-M3 cosine similarity scores and BM25 TF-IDF scores live on completely different scales and cannot be meaningfully combined arithmetically. RRF normalizes them through rank position.

**Formula:** `RRF_score(d) = sum(1 / (k + rank(d)))` where k=60

**Important calibration note:** After RRF fusion, citation scores become RRF weights (~0.016) rather than cosine similarity scores (~0.30-1.0). An early retrieval confidence scorer was broken because it misinterpreted post-RRF weights as cosine similarity scores, collapsing confidence to near-zero for all hybrid queries. The fix: capture the raw cosine similarity score *before* RRF fusion for confidence scoring.

**Status:** IMPLEMENTED — `retrieval_service.py` and `nodes_retrieval.py`

---

## 5. Phase 3 — Domain Routing and HyDE

### Domain Routing
**Problem:** Querying labor law articles for a personal-status question dilutes retrieval precision.

**Solution:** `nodes_domain.py` keyword + weighted scoring detects query domain before retrieval, applying a `law_type` metadata filter to Qdrant.

**Note on category field:** The `category` payload field is stored as a stringified Python list (e.g., `"['الاحوال الشخصية']"`) which is not matchable by Qdrant's `MatchValue` operator. Only `law_type` (stored as a plain string) is used for filtering.

### HyDE (Hypothetical Document Embeddings)
**Problem:** Short Egyptian dialect queries may embed poorly against formal legal Arabic article text.

**Solution:** `nodes_query_expansion.py` — a fast LLM call generates a hypothetical article text that would answer the query, then embeds that instead of the raw query.

**Risk and mitigation:** HyDE hypothetical documents can drift semantically away from the actual legal corpus vocabulary. Mitigation: dual-vector search runs *both* the HyDE vector and the original query vector through Qdrant, then RRF-merges results. This ensures relevant chunks are never missed solely due to HyDE drift.

**Status:** IMPLEMENTED — `nodes_query_expansion.py`, `nodes_retrieval.py`

---

## 6. Phase 4 — Saudi Law Contamination Investigation

### Problem
The Hugging Face corpus (`dataflare/egypt-legal-corpus`) contains Saudi law articles (law_name="قانون العمل السعودي", law_type="labor"). Because they share the same `law_type` as Egyptian labor law, they were surfacing in Egyptian labor law queries.

### Investigation
A benchmark confirmed that a lighter reranker ranked a Saudi labor law article (article 87) as top-1 for Egyptian labor law queries.

### Attempted Fix — FAILED
First attempt used Qdrant's `MatchText` operator on `law_name`. This failed because `MatchText` requires a full-text payload index, which does not exist for this field.

### Corrected Fix — IMPLEMENTED
Use `MatchAny` with the exact string value: `MatchAny(any=["قانون العمل السعودي"])` in a `must_not` filter. The exact `law_name` value was confirmed by querying the Qdrant payload directly.

This filter is **permanently applied to every query** — Saudi articles are excluded at retrieval time regardless of domain or query type.

**Status:** IMPLEMENTED — `retrieval_service.py` `_build_filter()` method

---

## 7. Phase 5 — Reranker Architecture and Optimization

### 7.1 Why Reranking Was Added

Bi-encoder embeddings encode query and document independently, allowing fast vector search but sacrificing cross-attention between query and document. For legal Arabic text, a document about "termination procedures for executive employees" can embed similarly to one about "termination of the employment contract for cause," even though they answer different questions. A cross-encoder reranker processes query+document pairs jointly, computing a relevance score with full attention between both.

### 7.2 Reranker Model Selection

| Model | Arabic Performance | Decision |
|-------|-------------------|---------|
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | English-only, fails on Arabic | REJECTED |
| `cross-encoder/mMiniLMv2-L12-H384-mMarcov2` | Weak on Egyptian dialect | REJECTED |
| `BAAI/bge-reranker-base` | Quality regressions on dialect queries | REJECTED |
| `BAAI/bge-reranker-v2-m3` | Best across all Arabic legal test categories | **SELECTED** |

**Status:** `BAAI/bge-reranker-v2-m3` — ACTIVE

### 7.3 CPU Latency — batch_size=1

**Benchmark result:**
- `batch_size=1`: ~9,098ms
- `batch_size=32`: ~12,669ms

**Why batch_size=1 is faster on CPU:** CPU has no parallel batch execution benefit. Larger batches increase memory allocation overhead without any compute parallelism gain.

**Status:** IMPLEMENTED — `reranker_service.py` line 84: `batch_size=1`

### 7.4 Candidate Count — top_k=8

| Candidates | Quality |
|-----------|---------|
| 20 | Baseline |
| 8 | No regression — selected |
| 5 | Regression — correct docs appear at rank 6-8 |
| 3 | Significant regression |

**Critical finding:** Correct documents appeared at raw rank 7/8 for some queries. Reducing below 8 caused measurable quality regressions.

**Status:** IMPLEMENTED — `nodes_retrieval.py` `_RERANKER_CANDIDATES = 8`

### 7.5 Adaptive Reranking Experiments

**End-to-end A/B benchmark (20 queries):**
- Reranking materially improved answer quality in 3/20 queries (15%)
- No-rerank materially improved in 1/20 queries (5%)
- 16/20 produced equivalent final answers regardless of reranking

The 15% cases where reranking mattered were specifically the hardest Egyptian dialect and domain-ambiguous queries — exactly where quality matters most. Reranking was kept.

**Heuristic skip rules tested — all REJECTED:**

| Rule | Why Rejected |
|------|-------------|
| RRF score margin threshold | No clean separation between changed/unchanged outcomes |
| Absolute RRF score | Dataset-relative; no safe global threshold |
| Top-k law concentration | No reliable correlation with reranker necessity |
| Query length | Short dialect queries are actually hardest |
| Dialect heuristic | Not validated; formal queries can still need reranking |

**One rule validated and IMPLEMENTED — explicit article reference skip:**

IF the query explicitly names "المادة X" AND the raw top-1 IS article X AND domain filter matches AND RRF margin > 0 → skip the cross-encoder.

**Why safe:** When a user asks for article 69 specifically, the correct answer is deterministically article 69. If the embedder already retrieved it at top-1, the cross-encoder cannot improve on this. Multiple guards prevent false positives.

**Status:** IMPLEMENTED — `nodes_retrieval.py` `_should_skip_rerank()`

---

## 8. Phase 6 — Retrieval Confidence Scoring and Web Fallback

### Retrieval Confidence Scorer

A multi-signal confidence score combining:
- Top-1 dense cosine similarity (weight: 0.4)
- Retrieval recall coverage (weight: 0.3)
- Domain match bonus (weight: 0.2)
- Top reranker score (weight: 0.1)

Queries scoring below `CONFIDENCE_FALLBACK_THRESHOLD=0.35` route to web search fallback.

**Note:** Score captured *before* RRF fusion. Post-RRF scores (~0.016) are not usable as confidence signals.

### Web Search Fallback (Tavily)

When confidence < threshold, `nodes_web_search.py` queries Tavily. Results are merged with local citations by `nodes_answer_synthesis.py`. `WEB_SEARCH_ENABLED=False` by default.

**Status:** IMPLEMENTED — `confidence_scorer.py`, `nodes_web_search.py`, `nodes_answer_synthesis.py`

---

## 9. Phase 7 — Generation Model Migration

### Why Migration Was Necessary

`llama-3.3-70b-versatile` was sunset by Groq with a 100K tokens/day hard cap. Live benchmarking on 2026-08-16 confirmed 3 of 5 test queries failed with 429 errors. The model was operationally decommissioned.

### Models Evaluated

| Model | Queries answered | Avg latency | Issue |
|-------|-----------------|------------|-------|
| `llama-3.3-70b-versatile` | 2/5 | 12,575ms | 100K TPD sunset |
| `openai/gpt-oss-120b` | 5/5 | **1,707ms** | None |
| `qwen/qwen3.6-27b` | 5/5 | 7,282ms | `<think>` bleed to users |

### Why openai/gpt-oss-120b Was Selected

1. **Reliability:** 5/5 queries answered vs. 2/5 for the deprecated model
2. **Latency:** 1,707ms average — 4.3× faster than Qwen
3. **No `<think>` leakage:** Qwen exposed raw internal reasoning traces to end users — a trust failure for a legal AI
4. **Zero hallucinations** in benchmark
5. **Correct grounded refusal:** Correctly returned "المعلومة مش موجودة" for out-of-corpus queries

**Migration scope:** Configuration only. No prompts, retrieval, or application code changed.

**Status:** `openai/gpt-oss-120b` via Groq — ACTIVE

---

## 10. Current Architecture Reference

See [README.md](../README.md) for the quick overview and request flow diagram.

See [docs/DEPLOYMENT.md](DEPLOYMENT.md) for deployment configuration.

---

## 11. Key Engineering Decisions Table

| Decision | Alternatives | Evidence | Status |
|----------|-------------|---------|--------|
| BAAI/bge-reranker-v2-m3 | ms-marco-MiniLM, mMiniLMv2, bge-base | Best Arabic quality benchmark | **ACTIVE** |
| batch_size=1 reranker | batch_size=8, 32 | 9,098ms vs 12,669ms on CPU | **ACTIVE** |
| top_k=8 candidates | 3, 5, 20 | Docs appear at rank 7-8 | **ACTIVE** |
| Explicit article-ref skip only | RRF margin, score, law concentration, length, dialect | No reliable signal found except article-ref | **ACTIVE** |
| RRF fusion | Weighted score sum | Incompatible score scales | **ACTIVE** |
| Saudi law must_not filter | MatchText (broken) | MatchAny on exact law_name | **ACTIVE** |
| Dual-vector HyDE+original | HyDE only | HyDE drift risk | **ACTIVE** |
| Pre-RRF cosine score for confidence | Post-RRF weights | Post-RRF ≈ 0.016 — useless | **ACTIVE** |
| openai/gpt-oss-120b | llama-3.3-70b (sunset), qwen3.6 | Benchmark: latency + reliability | **ACTIVE** |
| Candidate prefilter <8 | — | Quality regression | **REJECTED** |
| Lighter reranker models | — | Arabic quality regression | **REJECTED** |
| Additional heuristic skip rules | — | No safe threshold found | **REJECTED** |
| qwen3.6-27b generation | — | `<think>` bleed + 4.3x latency | **REJECTED** |

---

## 12. Remaining Limitations

1. **Cold-start latency:** BGE-M3 + BGE-reranker download on every Render cold start → 5–10 min first request
2. **CPU-only reranking:** 3–9 seconds per query; GPU would reduce to <1s
3. **HyDE latency:** +1–3s per query for query expansion LLM call
4. **Web search disabled by default:** Requires Tavily API key
5. **Lexical faithfulness check:** Token-overlap ≥10% does not understand paraphrase; correct grounded answers that paraphrase legal text may trigger false fallback

---

## 13. Future Improvements

- GPU deployment for reranker (Render GPU instance)
- Semantic faithfulness check using BGE-M3 cosine similarity
- Automated corpus update pipeline for new Egyptian legislation
- Payload index on `law_name` for efficient MatchText filtering
- Retrieval evaluation framework automation
