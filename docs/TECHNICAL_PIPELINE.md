# BAYYINAH — Technical Pipeline Reference

Complete end-to-end documentation of the BAYYINAH RAG pipeline, from raw legal data to final user response.

> **Ground truth:** Every claim in this document is traceable to specific source files in the repository. File references are provided for all non-obvious details.

---

## 1. High-Level Architecture

```
╔══════════════════════════════════════════════════════════╗
║                   DATA INGESTION PATH                    ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  HuggingFace corpus                                      ║
║  (dataflare/egypt-legal-corpus)                          ║
║         │                                                ║
║         ▼                                                ║
║  JSONL format per article                                ║
║  (chunk_id, doc_id, law_name, law_number, law_year,      ║
║   law_type, category, article_number, text, ...)         ║
║         │                                                ║
║         ▼                                                ║
║  scripts/ingest.py  ──or──  bayyinah_ingest.ipynb        ║
║         │                                                ║
║         ▼                                                ║
║  BGE-M3 embed_batch()  →  1024-dim dense vectors         ║
║         │                                                ║
║         ▼                                                ║
║  qdrant_client.upsert()                                  ║
║  Collection: egypt_legal_rag  (43,582 vectors)           ║
║  Named vector: "dense"  │  Distance: COSINE              ║
║  Payload indexes: category, law_type, law_name, law_year ║
╚══════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════╗
║                 QUERY / INFERENCE PATH                   ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  User: "ما حقوقي لو طردوني من الشغل؟"                   ║
║         │                                                ║
║         ▼  POST /chat  (FastAPI)                         ║
║  LegalAssistantState  ←  ChatRequest validation          ║
║         │                                                ║
║  Node 1: detect_domain ─────────────────────────────────║
║    keyword scoring → LegalDomain.LABOR                   ║
║    law_type_filter = "labor"                             ║
║         │                                                ║
║  Node 2: query_expansion (HyDE) ────────────────────────║
║    domain == LABOR (known) → SKIP HyDE                   ║
║    [HyDE only runs for UNKNOWN domain queries]           ║
║         │                                                ║
║  Node 3: retrieve ──────────────────────────────────────║
║    embed(question) → 1024-dim vector                     ║
║    Qdrant dense search  +  BM25 search                   ║
║    → 20 candidates each                                  ║
║    → RRF fusion → top-8 by RRF score                     ║
║    → Saudi law must_not filter (always applied)          ║
║    → law_type filter (if domain detected)                ║
║    → reranker skip check (article-ref rule)              ║
║    → BGE-reranker-v2-m3 cross-encoder → top-5            ║
║    → relevance guard (score threshold)                   ║
║    → retrieval_confidence scoring                        ║
║         │                                                ║
║  Conditional edge: confidence ≥ 0.35?                   ║
║    YES → Node 4: answer_synthesis                        ║
║    NO  → Node 4b: web_search (Tavily) → answer_synthesis ║
║         │                                                ║
║  Node 5: cite ──────────────────────────────────────────║
║    dedup by chunk_id                                     ║
║    trim each citation to 400 tokens                      ║
║    enforce 3000-token total budget                       ║
║         │                                                ║
║  Node 6: generate_answer ───────────────────────────────║
║    build_context(): numbered blocks, 120-word excerpts   ║
║    build_history_block(): last 5 conversation turns      ║
║    SYSTEM_PROMPT (Egyptian dialect, grounding rules)     ║
║    USER_PROMPT_TEMPLATE (question + context)             ║
║    → openai/gpt-oss-120b via Groq API                    ║
║         │                                                ║
║  Node 7: verify ────────────────────────────────────────║
║    unsafe request regex check                            ║
║    faithfulness: token overlap(answer, citations) ≥ 10%  ║
║    citation_valid: article numbers in answer ⊆ citations  ║
║    → final_answer / is_fallback / warnings               ║
║         │                                                ║
║  ChatResponse: answer, citations, domain,                ║
║               faithfulness_score, is_fallback, warnings  ║
╚══════════════════════════════════════════════════════════╝
```

---

## 2. Data Ingestion: Before the RAG

### 2.1 Data Source

**Source:** HuggingFace dataset `dataflare/egypt-legal-corpus`
**Format at source:** Pre-structured JSON/JSONL — no parsing of raw PDFs in this pipeline
**Content:** 43,582 Egyptian legal articles across multiple law types

**Important:** The raw source already provides structured records. BAYYINAH's ingestion pipeline does **not** parse PDFs or raw legislative text — it consumes the pre-structured JSONL dataset. PDF/DOCX parsing only occurs in the **contract analysis** pipeline, which is separate from the legal assistant RAG pipeline.

The corpus includes articles from:
- قانون العمل (Labor law)
- القانون المدني (Civil law)
- قانون الأحوال الشخصية (Family/personal status law)
- القانون الجنائي (Criminal law)
- قانون الإيجار (Tenancy, subsumed under civil)
- القانون الدستوري (Constitutional law)
- قانون المرافعات (Procedural/civil procedure law)
- And general/encyclopedia law types

**Known contamination:** The dataset also contains Saudi labor law articles (`law_name="قانون العمل السعودي"`). These are NOT relevant to Egyptian queries. They are **excluded at retrieval time** via a permanent `must_not` Qdrant filter — not at ingestion time. See Section 6.4 for details.

### 2.2 Ingestion Entry Points

Two ingestion paths exist in the repository:

**Path A — CLI script (`scripts/ingest.py`)**
- Reads a local JSONL file
- Uses `EmbeddingService` directly (`embed_batch()`)
- Upserts directly to Qdrant
- Creates collection with payload indexes if it does not exist
- Supports `--recreate` to drop and recreate
- Default batch size: 32

**Path B — Colab/Kaggle notebook (`bayyinah_ingest.ipynb`)**
- Downloads corpus from HuggingFace Hub (GPU-accelerated)
- Preferred for initial large-scale ingestion (43K+ vectors)
- Reads credentials from environment variables (not hardcoded — see Cell 2)

### 2.3 Input Record Structure (JSONL)

One record per article. Every field is present in the Qdrant payload after ingestion:

```json
{
  "chunk_id": "labor_12_2003_art69",
  "doc_id": "labor_12_2003",
  "law_name": "قانون العمل",
  "law_number": "12",
  "law_year": "2003",
  "law_type": "labor",
  "category": "labor_law",
  "article_number": "69",
  "text": "نص المادة التاسعة والستين ...",
  "context_text": "نص السياق المحيط ...",
  "cross_references": ["labor_12_2003_art68"]
}
```

**Note on law_type values found in corpus (sampled from Qdrant payload audit):**
`civil`, `family`, `labor`, `criminal`, `constitutional`, `procedural`, `encyclopedia`, `other`

**Note on category field:** The `category` field is stored as a **stringified Python list** in the actual Qdrant payload — e.g., `"['الاحوال الشخصية']"`. This is a data quality issue from the source dataset. Qdrant's `MatchValue` operator cannot match this format. As a result, **category filtering is not used** in any retrieval query; only `law_type` (stored as a plain string) is used for metadata filtering.

### 2.4 Preprocessing at Ingestion Time

The CLI ingestion script performs **no text preprocessing** before embedding — article text is embedded as-is from the JSONL.

All Arabic text normalization exists in the **BM25 service** (`bm25_service.py`) and is applied **at query time**, not at ingestion time:

```python
# normalize_arabic_text() applied to: corpus at BM25 index-build time, and to every query
- Remove diacritics (harakat): [\u064B-\u0652]
- Remove tatweel (kashida): \u0640
- Normalize alef variants: أ إ آ → ا
- Normalize teh marbuta: ة → ه
- Normalize alef maksura: ى → ي
- Lowercase (for any Latin/numeric mixed content)
```

**Why normalize for BM25 but not for embeddings?** BGE-M3 was trained on multilingual data including Arabic with full diacritics — it handles them natively. BM25 is token-based; without normalization, "عامل" and "عاملٌ" (diacritized) would not match the same BM25 token.

### 2.5 Chunking Strategy

**Current approach: no chunking — one article = one vector**

Each Egyptian legal article is a complete, standalone unit of law. Articles are typically 20–500 words. The ingestion script embeds the full `text` field of each article as a single vector. There is no sentence splitting, sliding window, or overlap logic in the ingestion pipeline.

**Why one article = one chunk:**
1. Each article has a unique legal meaning that should be retrievable as a whole unit
2. Article boundaries are already the natural "minimum retrievable unit" in Egyptian law
3. Splitting articles would orphan article numbers and law references from their text
4. The `context_text` field provides a broader surrounding context if needed (stored in payload but not embedded separately)

**Long articles:** The `nodes_generation.py` `build_context()` function trims articles to **120 words** when building the LLM prompt, ensuring prompt token budget is respected while preserving the article number/law reference metadata.

---

## 3. Qdrant Vector Database

**File:** `backend/app/services/retrieval_service.py`

### 3.1 Collection Configuration

| Parameter | Value |
|-----------|-------|
| Collection name | `egypt_legal_rag` |
| Vector name | `"dense"` |
| Vector dimension | 1024 |
| Distance metric | COSINE |
| Total vectors | 43,582 |

### 3.2 Payload Indexes

Created at ingestion time by `ensure_collection()` in `scripts/ingest.py`:

| Field | Index type | Used for |
|-------|-----------|---------|
| `category` | KEYWORD | (Defined, but not used — see §2.3 note) |
| `law_type` | KEYWORD | Domain routing filter |
| `law_name` | KEYWORD | Saudi law must_not filter |
| `law_year` | KEYWORD | Potential future date filtering |

### 3.3 Metadata Filtering

`_build_filter()` in `retrieval_service.py` constructs two types of Qdrant conditions per query:

**1. `must` — domain filter (optional, only when domain detected):**
```python
FieldCondition(key="law_type", match=MatchValue(value="labor"))
```

**2. `must_not` — Saudi law exclusion (permanent, every query):**
```python
FieldCondition(key="law_name", match=MatchAny(any=["قانون العمل السعودي"]))
```

**Historical note — broken `MatchText` attempt:**
An earlier implementation used `MatchText("سعودي")` to exclude Saudi articles by substring match. This silently failed because `MatchText` requires a **full-text payload index** on the field, which does not exist for `law_name` (it only has a KEYWORD index). The filter produced no error but had zero effect.

**Correct fix:** `MatchAny` with the exact string value `"قانون العمل السعودي"`. This operator works on KEYWORD-indexed fields, matching the complete stored value. The exact string was confirmed by direct Qdrant payload inspection.

### 3.4 Three-Fallback Retrieval Strategy

`retrieval_service.search()` implements a progressive fallback to prevent empty retrieval:

```
Attempt 1: Filtered dense search (law_type filter + score_threshold=0.30)
     ↓ empty?
Attempt 2: Filtered dense search with relaxed threshold (threshold - 0.20)
     ↓ empty?
Attempt 3: Unfiltered dense search with relaxed threshold
```

This ensures the pipeline never returns empty results from Qdrant due to an overly strict domain filter or score threshold.

### 3.5 BM25 In-Memory Index

The BM25 service (`bm25_service.py`) builds an **in-memory BM25Okapi index** by scrolling ALL Qdrant documents at startup for the requested `law_type`. This is not a separate search engine — it is a RAM-resident BM25 index constructed from the same corpus stored in Qdrant.

**Lazy loading with thread-safe locking:** The BM25 index for each `law_type` is built on first use, then cached. Scroll batch size: 500 records per request. The index for the full `labor` corpus (~4,000 articles) is built in ~2-5 seconds on first query, then served from RAM.

**Important implication:** The BM25 service needs enough RAM to hold the tokenized corpus in memory alongside the embedding model and reranker.

---

## 4. Query Processing — LangGraph Flow

**File:** `backend/app/graphs/legal_assistant/graph.py`

The legal assistant pipeline is a **LangGraph `StateGraph`** with a single shared state object (`LegalAssistantState`) threaded through 8 nodes.

### 4.1 State Object

```python
class LegalAssistantState(TypedDict, total=False):
    # Input
    question: str
    conversation_id: str
    request_id: str

    # Domain detection output
    domain: LegalDomain
    category_filter: Optional[str]   # currently always None (category not filterable)
    law_type_filter: Optional[str]   # e.g., "labor"

    # Retrieval output
    citations: List[Citation]
    retrieval_empty: bool

    # Generation output
    prompt: str
    raw_answer: str

    # Verification output
    faithfulness_score: float
    citation_valid: bool
    is_unsafe: bool

    # Final response
    final_answer: str
    is_fallback: bool
    warnings: List[str]

    # Sprint 3 additions
    history: List[dict]             # Redis conversation history
    hyde_vector: List[float]        # HyDE embedding (if generated)
    hyde_document: str              # HyDE hypothetical text (diagnostics)
    rewritten_query: str
    alt_queries: List[str]
    retrieval_confidence: float     # multi-signal confidence score [0,1]
    context_tokens: int             # total tokens in citation context
    web_results: List[dict]         # Tavily web search results
    retrieval_source: str
```

### 4.2 Graph Topology

```
detect_domain
     ↓
query_expansion
     ↓
retrieve
     ↓ (conditional)
   ┌─────────────────────┐
   │ confidence >= 0.35? │
   └──────┬──────────────┘
     YES  │    NO
          ↓    ↓
answer_synthesis ← web_search
          ↓
         cite
          ↓
   generate_answer
          ↓
        verify
          ↓
         END
```

The conditional routing is implemented in `graph.py` as:
```python
graph.add_conditional_edges(
    "retrieve",
    verify_retrieval_confidence,   # checks state["retrieval_confidence"]
    {
        "answer_synthesis": "answer_synthesis",
        "web_search": "web_search",
    }
)
```

---

## 5. Node 1 — Domain Detection (`detect_domain_node`)

**File:** `backend/app/graphs/legal_assistant/nodes_domain.py`

### Mechanism

Pure keyword-based scoring. No LLM call. No embedding.

1. Normalize the query with Arabic normalization (diacritics, alef variants, teh marbuta, alef maksura)
2. For each legal domain, count how many of its keywords appear in the normalized query
3. Select the domain with the highest keyword count
4. If all counts are zero → `LegalDomain.UNKNOWN`

### Domain keyword lexicon (representative samples)

| Domain | Sample Arabic keywords |
|--------|----------------------|
| LABOR | عامل، فصل، أجر، إجازة، عقد عمل، تأمينات |
| TENANCY | إيجار، مستأجر، إخلاء، عين مؤجرة |
| FAMILY | زواج، طلاق، حضانة، نفقة، ميراث |
| CRIMINAL | جريمة، سرقة، عقوبة، جنحة، بلاغ |
| COMMERCIAL | شركة، شيك، كمبيالة، إفلاس |
| ADMINISTRATIVE | قرار إداري، مجلس الدولة، ترخيص |
| CIVIL | عقد، ملكية، ضرر، مسؤولية |

### Domain → Qdrant filter mapping

```python
DOMAIN_TO_FILTERS = {
    LegalDomain.LABOR:          (None, "labor"),
    LegalDomain.TENANCY:        (None, "civil"),   # tenancy = civil code
    LegalDomain.FAMILY:         (None, "family"),
    LegalDomain.CRIMINAL:       (None, "criminal"),
    LegalDomain.COMMERCIAL:     (None, "civil"),
    LegalDomain.ADMINISTRATIVE: (None, "other"),
    LegalDomain.CIVIL:          (None, "civil"),
    LegalDomain.UNKNOWN:        (None, None),      # no filter → full corpus search
}
```

The first tuple element (category_filter) is always `None` because the category payload field is not filterable (stringified list format).

### Output

Sets `state["domain"]`, `state["law_type_filter"]`, `state["category_filter"]`.

### Limitation

Keyword scoring is fast but crude. A query like "هل يجوز للشركة أن تفصل العامل" scores for both COMMERCIAL (`شركة`) and LABOR (`عامل`, `فصل`). In this case, the correct domain (LABOR) wins only because it has more matching keywords. Ambiguous multi-domain queries can be mis-routed.

---

## 6. Node 2 — Query Expansion (HyDE)

**File:** `backend/app/graphs/legal_assistant/nodes_query_expansion.py`

### What HyDE is

HyDE (Hypothetical Document Embeddings) generates a hypothetical article text that *would* answer the query, then embeds that hypothetical text instead of (or alongside) the raw query vector. The insight: a hypothetical answer embeds closer to real answer documents than a short colloquial question does.

### Current activation condition

**HyDE only runs for `LegalDomain.UNKNOWN` queries.**

```python
if detected_domain and detected_domain != LegalDomain.UNKNOWN:
    return state  # skip HyDE
```

**Rationale (documented in code):** When a domain is detected, the query already contains specific legal keywords that make the original query vector precise enough. HyDE adds latency (+1–3s LLM call) that is only justified for vague, domain-ambiguous queries where the embedding may not retrieve the right domain of documents.

### HyDE generation

```
HYDE_SYSTEM_PROMPT: "كتابة فقرة قصيرة تحاكي مادة قانونية..."
HYDE_USER_PROMPT:   "السؤال: {question}"
→ Groq LLM call (max_tokens=300, timeout=2.0s)
→ hypothetical Arabic legal article text
→ embed_query(hyde_doc) → 1024-dim hyde_vector
```

### Output

Sets `state["hyde_vector"]` and `state["hyde_document"]`.
If timeout or error: adds `"hyde_generation_timeout"` to warnings, no hyde_vector set.

---

## 7. Node 3 — Retrieval (`retrieve_node`)

**File:** `backend/app/graphs/legal_assistant/nodes_retrieval.py`

This is the most complex node. It performs the full retrieval, reranking, and confidence scoring pipeline.

### 7.1 Torch CPU Thread Optimization

```python
import torch
torch.set_num_threads(os.cpu_count() or 4)
```
9% embedding speedup measured by using all available CPU cores.

### 7.2 Single-Vector vs. Dual-Vector Path

**Dual-vector path (when `hyde_vector` is set — UNKNOWN domain only):**

```
embed(original_query)  → original_vector
hyde_vector (from state)

Qdrant dense search(hyde_vector,   top_k=8, query_text=None)   → hyde_results
Qdrant dense search(original_vector, top_k=8, query_text=None)  → original_results

best_pre_rrf_score = max cosine score across all pre-RRF results  # captured BEFORE RRF!

citations = _rrf_merge(hyde_results, original_results)
```

**Single-vector path (known domain — all LABOR, FAMILY, etc. queries):**

```
embed(original_query)  → original_vector

retrieval_service.search(
    query_vector=original_vector,
    query_text=question,          # enables BM25 hybrid
    law_type=law_type_filter,
    top_k=8
) → citations
```

### 7.3 Inside retrieval_service.search()

When called with `query_text` (the single-vector path):

```
1. Qdrant dense search (law_type filter + Saudi must_not)
   → candidate_limit = max(top_k, 20) = 20 from Qdrant
   → score_threshold = 0.30 (configurable)

2. BM25 search (same law_type filter)
   → top 20 results from in-memory BM25Okapi index

3. RRF fusion → merge dense + sparse ranked lists
   score(doc) = Σ 1/(60 + rank_i)  (k=60)

4. Deduplication by (law_name, article_number, law_number)
   → keep highest-scored duplicate

5. Return top_k=8
```

### 7.4 RRF: The Critical Score Transformation

After RRF fusion, `Citation.score` values become RRF weights:
- **Typical range: ~0.016** (document ranked 1st in both lists gets `2/(60+1) ≈ 0.033`)
- **Not cosine similarity** (range 0.30–1.0)
- **Not BM25 scores** (range 0–20+)

**This matters for confidence scoring.** In the dual-vector path, the code explicitly captures the raw cosine similarity score before RRF fusion:

```python
all_pre_rrf = hyde_results + original_results
best_pre_rrf_score = max(c.score for c in all_pre_rrf)  # real cosine similarity
citations = _rrf_merge(hyde_results, original_results)   # scores now ≈ 0.016
```

The `best_pre_rrf_score` is then passed to `compute_confidence()` as `top1_dense_score` — which expects cosine similarity range [0,1], not RRF weights.

In the single-vector path, scores from Qdrant are already genuine cosine similarity values (RRF is applied internally in `retrieval_service.search()` but the node uses `score_from_citations()` which is appropriate for this path).

### 7.5 Adaptive Reranking — Explicit Article Reference Skip

```python
def _should_skip_rerank(citations, question, law_type_filter):
    # Guard 1: need at least 2 candidates to have a meaningful skip
    if len(citations) < 2: return False, "too_few_candidates"

    # Guard 2: query must explicitly name an article number
    m = re.search(r"\bالمادة\s+(\d+)", question)
    if m is None: return False, "no_article_ref"

    article_ref = m.group(1)

    # Guard 3: raw top-1 must be that exact article
    top1_art = str(citations[0].article_number or "")
    if top1_art != article_ref: return False, "article_ref_not_top1"

    # Guard 4: domain filter active → top-1 must be in that domain
    if law_type_filter:
        if citations[0].law_type != law_type_filter: return False, "domain_mismatch"

    # Guard 5: non-zero score margin (tied candidates = ambiguous)
    margin = citations[0].score - citations[1].score
    if margin <= 0: return False, "zero_margin_ambiguous"

    return True, "article_ref_matched_high_confidence"
```

If skip: return `citations[:RERANK_TOP_N]` (no cross-encoder)
If no skip: call `reranker.rerank(question, citations, top_n=5)`

### 7.6 Cross-Encoder Reranking

**File:** `backend/app/services/reranker_service.py`

```python
model = CrossEncoder("BAAI/bge-reranker-v2-m3", device="cpu", max_length=512)

pairs = [[question, c.text] for c in citations]  # 8 pairs
scores = model.predict(pairs, batch_size=1, show_progress_bar=False)
```

**Why batch_size=1:** Measured fastest on CPU — 9,098ms vs 12,669ms for batch_size=32 with 8 pairs. CPU has no parallel batch execution; larger batches add memory allocation overhead without compute benefit.

**3-tier fallback:**
1. `BAAI/bge-reranker-v2-m3` CrossEncoder (primary)
2. Token-overlap heuristic (if cross-encoder fails to load)
3. Pass-through of original RRF order (if overlap scoring also fails)

### 7.7 Relevance Guard (Post-Rerank)

After reranking, a guard checks whether the top reranker score is below a threshold:

```python
# Only applies when cross-encoder actually ran (not article-ref skip)
if max(c.score for c in reranked) < RERANK_RELEVANCE_THRESHOLD (=0.30):
    reranked_citations = []  # treat as corpus miss
```

Cross-encoder scores are calibrated: labor-relevant=0.96-0.99, family-relevant=0.36, corpus-miss=0.23-0.77. A global threshold of 0.30 is conservative — it only blocks completely stumped results while allowing the more variable family law scores (~0.36) through.

### 7.8 Retrieval Confidence Scoring

**File:** `backend/app/services/confidence_scorer.py`

```
confidence = 0.4 * top1_dense_score   (raw cosine similarity, 0-1)
           + 0.3 * recall_coverage     (num_docs / 5, capped at 1.0)
           + 0.2 * domain_bonus        (1.0 if law_type_filter set, else 0.0)
           + 0.1 * reranker_score      (normalized, 0-1)
```

Result: scalar in [0.0, 1.0]
Threshold: `CONFIDENCE_FALLBACK_THRESHOLD = 0.35`

If `confidence < 0.35` → route to web_search in the graph conditional edge.

### 7.9 Retrieval Node Output

State after retrieval:
```python
state["citations"]             # List[Citation], top-5 reranked, scored
state["retrieval_empty"]       # bool: True if 0 citations after all filters
state["retrieval_confidence"]  # float in [0,1]
```

---

## 8. Node 4 — Answer Synthesis (`answer_synthesis_node`)

**File:** `backend/app/graphs/legal_assistant/nodes_answer_synthesis.py`

This node runs unconditionally (both the high-confidence and web-search paths lead here).

**Primary purpose:** Merge local retrieval citations with Tavily web search results when web search ran.

**If web search did not run:**
- `web_results = []` → no web citations → return state with updated `retrieval_empty` flag

**If web search ran:**
- Local citations take priority (ranked first)
- Web citations appended after, deduped by chunk_id and URL
- Web citations have `law_type="web"`, no `law_number`/`law_year`/`article_number`
- Combined list becomes `state["citations"]`

---

## 9. Node 5 — Citation Agent (`citation_node`)

**File:** `backend/app/graphs/legal_assistant/nodes_citation.py`

Performs three operations on the reranked citations before generation:

**Step 1: Deduplication** — remove any citations with duplicate `chunk_id`, keeping the first occurrence (highest ranked)

**Step 2: Per-citation text trimming** — trim each citation's `text` to at most `CITATION_MAX_TEXT_TOKENS = 400` whitespace tokens. Uses a trailing ` …` marker. Token counting is whitespace-split (no subword tokenizer — ~30% margin built into the budget for real tokenizer overhead).

**Step 3: Total budget enforcement** — accumulate token counts; stop adding citations once the total would exceed `CITATION_MAX_TOKENS = 3000` tokens. Citations are processed in ranking order, so the most relevant citations always survive.

**Output:** `state["citations"]` (trimmed, budgeted list), `state["context_tokens"]` (total token count)

This is not the same trimming as in `build_context()` in `nodes_generation.py`. Both apply: the citation node applies a 400-token per-citation limit to the `text` field stored in state; `build_context()` additionally trims each article to **120 words** when formatting the final LLM prompt.

---

## 10. Node 6 — Generation (`generate_answer_node`)

**File:** `backend/app/graphs/legal_assistant/nodes_generation.py`

### 10.1 Context Building

`build_context()` formats the citations list into a numbered article block:

```
[1] المادة 69 — قانون العمل رقم 12 لسنة 2003
نص المادة التاسعة والستين ... [trimmed to 120 words]

[2] المادة 70 — قانون العمل رقم 12 لسنة 2003
...
```

- Deduplicates by `(law_name, article_number)` — same article from two retrieval paths appears only once
- Trims each citation to **120 words** (whitespace split) with trailing ` …`
- Preserves law reference metadata in the header line

### 10.2 History Block

`build_history_block()` formats the last N conversation turns (fetched from Redis memory by the API layer):

```
سياق المحادثة السابقة بينك وبين المستخدم:
المستخدم: سؤال سابق...
بيّنة: إجابة سابقة...
```

Prepended to `system_prompt` if history exists.

### 10.3 Prompts

**`SYSTEM_PROMPT` (grounded path — when citations exist):**
Egyptian Arabic rules, mandatory answer structure, strict grounding rule: "اشتغل بس من المواد اللي في السياق المرفق", citation format rule, explicit hallucination prevention: "لو المعلومة مش موجودة في السياق، قول بالظبط..."

**`USER_PROMPT_TEMPLATE` (grounded path):**
```
السؤال: {question}
المواد القانونية المسترجعة (دي مصادرك الوحيدة):
{context}
قبل الإجابة: تأكد إن المواد المسترجعة فوق بتتكلم فعلاً عن موضوع السؤال...
```

**`SYSTEM_PROMPT_GENERAL` / `USER_PROMPT_GENERAL` (fallback path — when `retrieval_empty=True`):**
Used when no citations were retrieved. Explicitly warns the model: "مفيش مواد قانونية متاحة للسؤال ده." Instructs to answer from general legal knowledge but clearly disclaim the lack of specific citations.

### 10.4 LLM API Call

**File:** `backend/app/services/llm_service.py`

- Provider: Groq API (`api.groq.com`)
- Model: `openai/gpt-oss-120b`
- API style: OpenAI-compatible (`groq.AsyncGroq`)
- `temperature=0.1` (low randomness — legal answers should be consistent)
- `max_tokens=2048`
- Async call: `await llm.generate(system_prompt, user_prompt)`

### 10.5 Why openai/gpt-oss-120b

Benchmark comparison between candidate Groq models (2026-08-16):

| Model | Reliability | Avg latency | Disqualifier |
|-------|------------|------------|-------------|
| `llama-3.3-70b-versatile` | 2/5 queries | ~12,575ms | Sunset — 100K tokens/day cap |
| `openai/gpt-oss-120b` | **5/5** | **1,707ms** | None |
| `qwen/qwen3.6-27b` | 5/5 | 7,282ms | `<think>` block leakage to users |

Qwen's `<think>...</think>` chain-of-thought was delivered to end users in the raw response stream before the actual answer — a trust failure for a legal AI platform.

---

## 11. Node 7 — Verification (`verify_node`)

**File:** `backend/app/graphs/legal_assistant/nodes_verification.py`

Four checks in order:

### Check 1: Unsafe Request Detection

Regex patterns checked against the normalized question:
```python
r"كيف (أ|اعمل|اصنع)?\s*(أهرب|أزور|أزيف)"
r"تهرب من (الضريبة|الضرائب|القانون)"
r"تجنب (المسؤولية|العقاب|الملاحقة)"
r"كيفية ارتكاب"
```
If matched → `final_answer = FALLBACK_UNSAFE`, `is_fallback = True`, `is_unsafe = True`

### Check 2: Empty Retrieval

If `state["retrieval_empty"] == True` (no citations after all retrieval fallbacks):
→ Accept the general-knowledge fallback answer from `SYSTEM_PROMPT_GENERAL`
→ `is_fallback = True`, `faithfulness_score = 0.0`

This is not a hard error — the answer was already generated using the general knowledge prompt that warned the user.

### Check 3: Low Confidence Warning (advisory only)

If `retrieval_confidence < 0.35` at this stage:
- Add `f"low_retrieval_confidence:{confidence}"` to warnings
- **Do NOT return fallback** — the graph router already processed this
- Allow faithfulness check to make the final call

### Check 4: Faithfulness Check

Token overlap between the generated answer and the combined citation text:

```python
faithfulness = |tokens(answer) ∩ tokens(all_citation_texts)| / |tokens(answer)|
```

Tokenization: regex `[\u0600-\u06FFA-Za-z0-9]+`, minimum token length 2, with Arabic diacritics and Eastern Arabic digit normalization.

If `faithfulness < HALLUCINATION_MIN_OVERLAP (=0.10)`:
→ `final_answer = FALLBACK_LOW_FAITHFULNESS`
→ `is_fallback = True`

**Important limitation:** This is a lexical check. A correctly grounded answer that *paraphrases* legal text (instead of quoting it word-for-word) may fail the faithfulness check, producing a false fallback. The system prompt explicitly instructs the model to quote article text (`نصوص المواد الداعمة مع أرقامها`), which reduces but does not eliminate this risk.

### Check 5: Citation Mismatch Detection

Extract article numbers from the generated answer (regex: `(?:المادة|مادة)\s*(\d+)`) and verify that all mentioned article numbers exist in the retrieved citation set.

If not a subset:
- Add `"citation_mismatch"` to warnings
- **Do NOT return fallback** — this is a warning only

### Final State

```python
state["final_answer"]        # str — the answer or a fallback message
state["is_fallback"]         # bool
state["is_unsafe"]           # bool
state["faithfulness_score"]  # float [0,1]
state["citation_valid"]      # bool
state["warnings"]            # List[str]
```

---

## 12. Final Response Assembly

**File:** `backend/app/api/chat.py`

After the graph completes, the API assembles the `ChatResponse`:

```python
ChatResponse(
    conversation_id = conversation_id,   # from request or newly generated UUID
    answer           = state["final_answer"],
    citations        = state["citations"],  # List[Citation] with scores
    domain           = state["domain"],
    faithfulness_score = state.get("faithfulness_score"),
    is_fallback      = state.get("is_fallback", False),
    is_unsafe        = state.get("is_unsafe", False),
    warnings         = state.get("warnings", []),
    request_id       = state.get("request_id"),
)
```

The `citations` in the response are the **final citation objects** — trimmed text (max 400 tokens each), with all metadata preserved: `chunk_id`, `doc_id`, `law_name`, `law_number`, `law_year`, `law_type`, `category`, `article_number`, `text`, `score`.

---

## 13. Complete Walkthrough — Example Query

**Query:** `"ما حقوقي لو طردوني من الشغل؟"`

### Step 1 — HTTP Ingress

`POST /chat` body: `{"question": "ما حقوقي لو طردوني من الشغل؟"}`

FastAPI validates `ChatRequest` (length 2-1000, stripped). State initialized:
```python
{
    "question": "ما حقوقي لو طردوني من الشغل؟",
    "conversation_id": "uuid-...",
    "request_id": "uuid-...",
    "warnings": [],
}
```

### Step 2 — detect_domain

Normalized query: `"ما حقوقي لو طردوني من الشغل"` (diacritics removed)

Keyword scoring:
- LABOR: matches `["فصل"→"طردوني", "شغل"]` → score: 2
- Others: score: 0

Best domain: `LegalDomain.LABOR`
`law_type_filter = "labor"`, `category_filter = None`

### Step 3 — query_expansion (HyDE)

Domain is LABOR (not UNKNOWN) → **HyDE skipped**
No `hyde_vector` set in state.

### Step 4 — retrieve

**Since no hyde_vector → single-vector path:**

```
original_vector = embed("ما حقوقي لو طردوني من الشغل؟")  # 1024-dim float list

retrieval_service.search(
    query_vector=original_vector,
    query_text="ما حقوقي لو طردوني من الشغل؟",
    law_type="labor",
    top_k=8
)
```

Inside `search()`:
1. Qdrant dense search: vector similarity against `egypt_legal_rag`, `law_type=labor`, `must_not law_name=قانون العمل السعودي`, `score_threshold=0.30`, `limit=20` → ~15 Egyptian labor law articles
2. BM25 search: `tokenize("ما حقوقي لو طردوني من الشغل")` → ["حقوق", "طرد", "شغل"] → BM25Okapi against labor corpus → 20 scored articles
3. RRF fusion: merge two ranked lists, scores become ~0.016–0.033
4. Dedup: by (law_name, article_number, law_number)
5. Return top 8

**Back in retrieve_node:**

Adaptive skip check:
- No "المادة X" in query → `skip_reason = "no_article_ref"` → **reranker runs**

BGE-reranker-v2-m3:
```python
pairs = [["ما حقوقي لو طردوني من الشغل؟", article_1.text],
         ["ما حقوقي لو طردوني من الشغل؟", article_2.text],
         ...  # 8 pairs
]
scores = model.predict(pairs, batch_size=1)
```

Suppose top reranker scores:
- المادة 69 قانون العمل (فصل تعسفي): 0.97
- المادة 71 قانون العمل (تعويض الفصل): 0.94
- المادة 70 قانون العمل (إجراءات الفصل): 0.91
- المادة 46 قانون العمل (التزامات صاحب العمل): 0.72
- المادة 15 قانون العمل: 0.45

Top-5 after reranking. Relevance guard: max score 0.97 > 0.30 → no guard triggered.

Confidence scoring (single-vector path, using Citation.score which is cosine similarity from Qdrant):
```python
confidence = 0.4 * 0.85   # top-1 cosine similarity (estimated)
           + 0.3 * 1.0    # recall: 5 docs / cap 5 = 1.0
           + 0.2 * 1.0    # domain_bonus: law_type_filter set
           + 0.1 * 0.97   # reranker_score
           = 0.34 + 0.30 + 0.20 + 0.097 = 0.937
```

`retrieval_confidence = 0.937` → well above 0.35 → graph routes to `answer_synthesis`

### Step 5 — answer_synthesis

No web search ran (confidence was high). `web_results = []` → pass-through. `retrieval_empty = False`.

### Step 6 — cite

Input: 5 citations
- Dedup: no duplicates
- Per-citation trim: all citations within 400 tokens
- Total budget: ~400 tokens < 3000 → all 5 kept

`context_tokens ≈ 400`

### Step 7 — generate_answer

```python
context = build_context(state)
# Produces:
# [1] المادة 69 — قانون العمل رقم 12 لسنة 2003
# نص المادة... [120 words max]
# [2] المادة 71 — قانون العمل رقم 12 لسنة 2003
# نص المادة...

user_prompt = USER_PROMPT_TEMPLATE.format(
    question="ما حقوقي لو طردوني من الشغل؟",
    context=context
)
→ Groq API: openai/gpt-oss-120b, temp=0.1, max_tokens=2048
→ raw_answer: "لأ، مش ينفعش صاحب الشغل يطردك من غير سبب قانوني..."
```

### Step 8 — verify

1. Unsafe check: no unsafe patterns → pass
2. retrieval_empty: False → pass
3. Confidence 0.937: above threshold → advisory only
4. Faithfulness: token overlap(answer, citations) → suppose 0.45 (45%) > 0.10 → **PASS**
5. Citation mismatch: answer mentions "المادة 69" and "المادة 71" → both exist in retrieved citations → **citation_valid = True**

### Step 9 — Final Response

```json
{
    "conversation_id": "uuid-...",
    "answer": "لأ، مش ينفعش صاحب الشغل يطردك من غير سبب قانوني...\n\n(المادة 69 من قانون العمل رقم 12 لسنة 2003)",
    "citations": [
        {
            "chunk_id": "labor_12_2003_art69",
            "doc_id": "labor_12_2003",
            "law_name": "قانون العمل",
            "law_number": "12",
            "law_year": "2003",
            "law_type": "labor",
            "article_number": "69",
            "text": "نص المادة... [trimmed]",
            "score": 0.97
        },
        ...
    ],
    "domain": "labor_law",
    "faithfulness_score": 0.45,
    "is_fallback": false,
    "is_unsafe": false,
    "warnings": []
}
```

---

## 14. LLM Service and API

**File:** `backend/app/services/llm_service.py`

Uses Groq's OpenAI-compatible async client:
```python
client = groq.AsyncGroq(api_key=settings.GROQ_API_KEY)

response = await client.chat.completions.create(
    model=settings.GROQ_MODEL,     # "openai/gpt-oss-120b"
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ],
    temperature=settings.GROQ_TEMPERATURE,    # 0.1
    max_tokens=settings.GROQ_MAX_TOKENS,      # 2048
)
return response.choices[0].message.content
```

The Groq API uses the OpenAI `/v1/chat/completions` protocol, making models like `openai/gpt-oss-120b` accessible through a single interface. No special handling is needed for the model name — it is just the model ID as listed in `client.models.list()`.

---

## 15. Embedding Service Details

**File:** `backend/app/services/embedding_service.py`

### Loading strategy (priority order)

1. **FlagEmbedding** (`BGEM3FlagModel`) — preferred; purpose-built for BGE-M3; supports fp16 on GPU
2. **sentence-transformers** (`SentenceTransformer`) — standard fallback
3. **Hash-based pseudo-embedding** — emergency fallback; produces 1024-dim deterministic random vectors from SHA-256 hash; **zero semantic signal; retrieval quality = 0%; logged as CRITICAL**

The hash fallback is **intentionally noisy in logs** so it cannot be silently missed in production.

### embed_query() via FlagEmbedding

```python
output = model.encode(
    [text],
    return_dense=True,
    return_sparse=False,    # BGE-M3 can return sparse + ColBERT vecs too — not used here
    return_colbert_vecs=False,
)
return output["dense_vecs"][0].tolist()  # List[float], length 1024
```

### Warm-up

`embedding_service.warm_up()` and `reranker_service.warm_up()` are called at FastAPI startup (application lifespan handler) to avoid cold-start latency on the first request.

---

## 16. Safeguard and Failure Handling Summary

| Safeguard | Location | Trigger | Action |
|-----------|----------|---------|--------|
| Unsafe request regex | `verify_node` | Query matches harmful pattern | Block, return `FALLBACK_UNSAFE`, `is_unsafe=True` |
| Domain filter | `detect_domain_node` | Always | Restrict Qdrant to relevant law_type |
| Saudi law exclusion | `retrieval_service._build_filter()` | Every query | `must_not MatchAny(["قانون العمل السعودي"])` |
| Score threshold | `retrieval_service.search()` | Qdrant query | Exclude cosine similarity < 0.30 |
| Three-attempt retrieval | `retrieval_service.search()` | Empty result | Relax threshold, then drop filter |
| Relevance guard | `retrieve_node` | Cross-encoder max score < 0.30 | Treat as corpus miss (`retrieval_empty=True`) |
| HyDE timeout | `query_expansion_node` | LLM call > 2s | Skip HyDE, add warning, continue with original vector |
| Retrieval confidence | `graph.py` conditional edge | confidence < 0.35 | Route to web search fallback |
| Empty retrieval | `answer_synthesis_node`, `verify_node` | 0 citations | Use `SYSTEM_PROMPT_GENERAL`, `is_fallback=True` |
| Low faithfulness | `verify_node` | Token overlap < 10% | Return `FALLBACK_LOW_FAITHFULNESS`, `is_fallback=True` |
| Citation mismatch | `verify_node` | Article# in answer ∉ retrieved | Add `"citation_mismatch"` warning (no fallback) |
| Embedding failure | `embedding_service._load()` | Model fails to load | Hash fallback (CRITICAL log) |
| Reranker failure | `reranker_service.rerank()` | Cross-encoder fails | Token-overlap fallback, then pass-through |
| Qdrant unavailable | `retrieval_service.__init__()` | Connection fails | Return empty citations → fallback answer |
| BM25 unavailable | `bm25_service._connect()` | Connection fails | Return empty BM25 results, dense-only retrieval |

---

## 17. Current Architecture vs. Historical Alternatives

| Component | Current Implementation | Historical/Rejected | Reason for Current Choice |
|-----------|----------------------|-------------------|--------------------------|
| Embedding model | `BAAI/bge-m3` (FlagEmbedding, 1024-dim) | Earlier models (unspecified) | Best multilingual Arabic quality; native BGE support |
| Retrieval | Hybrid: dense (BGE-M3) + BM25 (BM25Okapi) + RRF | Dense-only | BM25 adds recall for exact legal terms and article numbers |
| RRF k value | 60 | N/A | Standard default; produces stable score distribution |
| Saudi law filter | `MatchAny` on exact `law_name` | `MatchText` (failed — requires full-text index) | `MatchAny` works on KEYWORD-indexed fields |
| HyDE activation | UNKNOWN domain queries only | All queries | Reduces latency; only adds value when query is domain-ambiguous |
| Reranker model | `BAAI/bge-reranker-v2-m3` | ms-marco-MiniLM, mMiniLMv2, bge-base | Best Arabic/Egyptian dialect quality across test categories |
| Reranker batch_size | 1 | 8, 32 | 9,098ms vs 12,669ms — CPU has no parallel batch benefit |
| Reranker candidates (top_k) | 8 | 3, 5 (quality regression), 20 (too slow) | Correct docs appear at rank 7-8; <8 causes regression |
| Adaptive skip rule | Explicit article reference only | RRF margin, absolute score, query length, dialect | Only this rule passed benchmarking safely |
| Generation model | `openai/gpt-oss-120b` via Groq | `llama-3.3-70b-versatile` (sunset), `qwen3.6-27b` (think bleed) | Reliability + latency + no `<think>` leakage |
| Confidence scoring | Multi-signal (dense + recall + domain + reranker) | Post-RRF scores (broken — ≈0.016) | Pre-RRF cosine similarity is the correct input |
| Faithfulness check | Token overlap ≥ 10% | — | Conservative; works without external model |
| BM25 index storage | In-memory (`BM25Okapi`) | — | Fast query latency; corpus fits in RAM |
| Fallback on Qdrant failure | Return `[]` (empty citations) | Return hardcoded mock articles | Mock articles caused wrong domain answers for every question |

---

## 18. Known Gaps in Repository Evidence

1. **Corpus preprocessing history:** The `dataflare/egypt-legal-corpus` dataset is already structured — the original PDF/web sources and any pre-processing pipeline that created this dataset exist outside this repository and are not documented here.

2. **Original collection creation parameters for the live Qdrant Cloud cluster:** The `ensure_collection()` function in `scripts/ingest.py` creates the collection with `KEYWORD` payload indexes. However, the actual live cluster may have been created differently (e.g., with different index types) depending on which ingestion path was used. The `law_name` field has a KEYWORD index (confirmed by `MatchAny` working on it), but the presence/absence of other indexes is not verifiable without direct Qdrant Cloud access.

3. **BM25 first-load latency at scale:** The BM25 service scrolls all Qdrant documents for a `law_type` on first use. The actual latency for the full `civil` corpus (~30,000+ articles) is not benchmarked in the repository.

4. **Streaming SSE path:** The streaming response (`POST /chat/stream`) uses Server-Sent Events but the streaming implementation details in `nodes_generation.py` are not traced in this document. The LLM service does support streaming via the Groq client.
