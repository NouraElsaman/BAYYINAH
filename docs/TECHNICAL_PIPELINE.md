# BAYYINAH â€” Technical Pipeline Reference

Complete end-to-end documentation of the BAYYINAH RAG pipeline, from raw legal data to final user response.

> **Ground truth:** Every claim in this document is traceable to specific source files in the repository. File references are provided for all non-obvious details.

---

## 1. High-Level Architecture

```
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘                   DATA INGESTION PATH                    â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘                                                          â•‘
â•‘  HuggingFace corpus                                      â•‘
â•‘  (dataflare/egypt-legal-corpus)                          â•‘
â•‘         â”‚                                                â•‘
â•‘         â–¼                                                â•‘
â•‘  JSONL format per article                                â•‘
â•‘  (chunk_id, doc_id, law_name, law_number, law_year,      â•‘
â•‘   law_type, category, article_number, text, ...)         â•‘
â•‘         â”‚                                                â•‘
â•‘         â–¼                                                â•‘
â•‘  scripts/ingest.py  â”€â”€orâ”€â”€  bayyinah_ingest.ipynb        â•‘
â•‘         â”‚                                                â•‘
â•‘         â–¼                                                â•‘
â•‘  BGE-M3 embed_batch()  â†’  1024-dim dense vectors         â•‘
â•‘         â”‚                                                â•‘
â•‘         â–¼                                                â•‘
â•‘  qdrant_client.upsert()                                  â•‘
â•‘  Collection: egypt_legal_rag  (43,582 vectors)           â•‘
â•‘  Named vector: "dense"  â”‚  Distance: COSINE              â•‘
â•‘  Payload indexes: category, law_type, law_name, law_year â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘                 QUERY / INFERENCE PATH                   â•‘
â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£
â•‘                                                          â•‘
â•‘  User: "Ù…Ø§ Ø­Ù‚ÙˆÙ‚ÙŠ Ù„Ùˆ Ø·Ø±Ø¯ÙˆÙ†ÙŠ Ù…Ù† Ø§Ù„Ø´ØºÙ„ØŸ"                   â•‘
â•‘         â”‚                                                â•‘
â•‘         â–¼  POST /chat  (FastAPI)                         â•‘
â•‘  LegalAssistantState  â†  ChatRequest validation          â•‘
â•‘         â”‚                                                â•‘
â•‘  Node 1: detect_domain â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•‘
â•‘    keyword scoring â†’ LegalDomain.LABOR                   â•‘
â•‘    law_type_filter = "labor"                             â•‘
â•‘         â”‚                                                â•‘
â•‘  Node 2: query_expansion (HyDE) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•‘
â•‘    domain == LABOR (known) â†’ SKIP HyDE                   â•‘
â•‘    [HyDE only runs for UNKNOWN domain queries]           â•‘
â•‘         â”‚                                                â•‘
â•‘  Node 3: retrieve â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•‘
â•‘    embed(question) â†’ 1024-dim vector                     â•‘
â•‘    Qdrant dense search  +  BM25 search                   â•‘
â•‘    â†’ 20 candidates each                                  â•‘
â•‘    â†’ RRF fusion â†’ top-8 by RRF score                     â•‘
â•‘    â†’ Saudi law must_not filter (always applied)          â•‘
â•‘    â†’ law_type filter (if domain detected)                â•‘
â•‘    â†’ reranker skip check (article-ref rule)              â•‘
â•‘    â†’ BGE-reranker-v2-m3 cross-encoder â†’ top-5            â•‘
â•‘    â†’ relevance guard (score threshold)                   â•‘
â•‘    â†’ retrieval_confidence scoring                        â•‘
â•‘         â”‚                                                â•‘
â•‘  Conditional edge: confidence â‰¥ 0.35?                   â•‘
â•‘    YES â†’ Node 4: answer_synthesis                        â•‘
â•‘    NO  â†’ Node 4b: web_search (Tavily) â†’ answer_synthesis â•‘
â•‘         â”‚                                                â•‘
â•‘  Node 5: cite â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•‘
â•‘    dedup by chunk_id                                     â•‘
â•‘    trim each citation to 400 tokens                      â•‘
â•‘    enforce 3000-token total budget                       â•‘
â•‘         â”‚                                                â•‘
â•‘  Node 6: generate_answer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•‘
â•‘    build_context(): numbered blocks, 120-word excerpts   â•‘
â•‘    build_history_block(): last 5 conversation turns      â•‘
â•‘    SYSTEM_PROMPT (Egyptian dialect, grounding rules)     â•‘
â•‘    USER_PROMPT_TEMPLATE (question + context)             â•‘
â•‘    â†’ openai/gpt-oss-120b via Groq API                    â•‘
â•‘         â”‚                                                â•‘
â•‘  Node 7: verify â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•‘
â•‘    unsafe request regex check                            â•‘
â•‘    faithfulness: token overlap(answer, citations) â‰¥ 10%  â•‘
â•‘    citation_valid: article numbers in answer âŠ† citations  â•‘
â•‘    â†’ final_answer / is_fallback / warnings               â•‘
â•‘         â”‚                                                â•‘
â•‘  ChatResponse: answer, citations, domain,                â•‘
â•‘               faithfulness_score, is_fallback, warnings  â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
```

---

## 2. Data Ingestion: Before the RAG

### 2.1 Data Source

**Source:** HuggingFace dataset `dataflare/egypt-legal-corpus`
**Format at source:** Pre-structured JSON/JSONL â€” no parsing of raw PDFs in this pipeline
**Content:** 43,582 Egyptian legal articles across multiple law types

**Important:** The raw source already provides structured records. BAYYINAH's ingestion pipeline does **not** parse PDFs or raw legislative text â€” it consumes the pre-structured JSONL dataset. PDF/DOCX parsing only occurs in the **contract analysis** pipeline, which is separate from the legal assistant RAG pipeline.

The corpus includes articles from:
- Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ (Labor law)
- Ø§Ù„Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ù…Ø¯Ù†ÙŠ (Civil law)
- Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø£Ø­ÙˆØ§Ù„ Ø§Ù„Ø´Ø®ØµÙŠØ© (Family/personal status law)
- Ø§Ù„Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¬Ù†Ø§Ø¦ÙŠ (Criminal law)
- Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¥ÙŠØ¬Ø§Ø± (Tenancy, subsumed under civil)
- Ø§Ù„Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¯Ø³ØªÙˆØ±ÙŠ (Constitutional law)
- Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ù…Ø±Ø§ÙØ¹Ø§Øª (Procedural/civil procedure law)
- And general/encyclopedia law types

**Known contamination:** The dataset also contains Saudi labor law articles (`law_name="Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ"`). These are NOT relevant to Egyptian queries. They are **excluded at retrieval time** via a permanent `must_not` Qdrant filter â€” not at ingestion time. See Section 6.4 for details.

### 2.2 Ingestion Entry Points

Two ingestion paths exist in the repository:

**Path A â€” CLI script (`scripts/ingest.py`)**
- Reads a local JSONL file
- Uses `EmbeddingService` directly (`embed_batch()`)
- Upserts directly to Qdrant
- Creates collection with payload indexes if it does not exist
- Supports `--recreate` to drop and recreate
- Default batch size: 32

**Path B â€” Colab/Kaggle notebook (`bayyinah_ingest.ipynb`)**
- Downloads corpus from HuggingFace Hub (GPU-accelerated)
- Preferred for initial large-scale ingestion (43K+ vectors)
- Reads credentials from environment variables (not hardcoded â€” see Cell 2)

### 2.3 Input Record Structure (JSONL)

One record per article. Every field is present in the Qdrant payload after ingestion:

```json
{
  "chunk_id": "labor_12_2003_art69",
  "doc_id": "labor_12_2003",
  "law_name": "Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„",
  "law_number": "12",
  "law_year": "2003",
  "law_type": "labor",
  "category": "labor_law",
  "article_number": "69",
  "text": "Ù†Øµ Ø§Ù„Ù…Ø§Ø¯Ø© Ø§Ù„ØªØ§Ø³Ø¹Ø© ÙˆØ§Ù„Ø³ØªÙŠÙ† ...",
  "context_text": "Ù†Øµ Ø§Ù„Ø³ÙŠØ§Ù‚ Ø§Ù„Ù…Ø­ÙŠØ· ...",
  "cross_references": ["labor_12_2003_art68"]
}
```

**Note on law_type values found in corpus (sampled from Qdrant payload audit):**
`civil`, `family`, `labor`, `criminal`, `constitutional`, `procedural`, `encyclopedia`, `other`

**Note on category field:** The `category` field is stored as a **stringified Python list** in the actual Qdrant payload â€” e.g., `"['Ø§Ù„Ø§Ø­ÙˆØ§Ù„ Ø§Ù„Ø´Ø®ØµÙŠØ©']"`. This is a data quality issue from the source dataset. Qdrant's `MatchValue` operator cannot match this format. As a result, **category filtering is not used** in any retrieval query; only `law_type` (stored as a plain string) is used for metadata filtering.

### 2.4 Preprocessing at Ingestion Time

The CLI ingestion script performs **no text preprocessing** before embedding â€” article text is embedded as-is from the JSONL.

All Arabic text normalization exists in the **BM25 service** (`bm25_service.py`) and is applied **at query time**, not at ingestion time:

```python
# normalize_arabic_text() applied to: corpus at BM25 index-build time, and to every query
- Remove diacritics (harakat): [\u064B-\u0652]
- Remove tatweel (kashida): \u0640
- Normalize alef variants: Ø£ Ø¥ Ø¢ â†’ Ø§
- Normalize teh marbuta: Ø© â†’ Ù‡
- Normalize alef maksura: Ù‰ â†’ ÙŠ
- Lowercase (for any Latin/numeric mixed content)
```

**Why normalize for BM25 but not for embeddings?** BGE-M3 was trained on multilingual data including Arabic with full diacritics â€” it handles them natively. BM25 is token-based; without normalization, "Ø¹Ø§Ù…Ù„" and "Ø¹Ø§Ù…Ù„ÙŒ" (diacritized) would not match the same BM25 token.

### 2.5 Chunking Strategy

**Current approach: no chunking â€” one article = one vector**

Each Egyptian legal article is a complete, standalone unit of law. Articles are typically 20â€“500 words. The ingestion script embeds the full `text` field of each article as a single vector. There is no sentence splitting, sliding window, or overlap logic in the ingestion pipeline.

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
| `category` | KEYWORD | (Defined, but not used â€” see Â§2.3 note) |
| `law_type` | KEYWORD | Domain routing filter |
| `law_name` | KEYWORD | Saudi law must_not filter |
| `law_year` | KEYWORD | Potential future date filtering |

### 3.3 Metadata Filtering

`_build_filter()` in `retrieval_service.py` constructs two types of Qdrant conditions per query:

**1. `must` â€” domain filter (optional, only when domain detected):**
```python
FieldCondition(key="law_type", match=MatchValue(value="labor"))
```

**2. `must_not` â€” Saudi law exclusion (permanent, every query):**
```python
FieldCondition(key="law_name", match=MatchAny(any=["Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ"]))
```

**Historical note â€” broken `MatchText` attempt:**
An earlier implementation used `MatchText("Ø³Ø¹ÙˆØ¯ÙŠ")` to exclude Saudi articles by substring match. This silently failed because `MatchText` requires a **full-text payload index** on the field, which does not exist for `law_name` (it only has a KEYWORD index). The filter produced no error but had zero effect.

**Correct fix:** `MatchAny` with the exact string value `"Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ"`. This operator works on KEYWORD-indexed fields, matching the complete stored value. The exact string was confirmed by direct Qdrant payload inspection.

### 3.4 Three-Fallback Retrieval Strategy

`retrieval_service.search()` implements a progressive fallback to prevent empty retrieval:

```
Attempt 1: Filtered dense search (law_type filter + score_threshold=0.30)
     â†“ empty?
Attempt 2: Filtered dense search with relaxed threshold (threshold - 0.20)
     â†“ empty?
Attempt 3: Unfiltered dense search with relaxed threshold
```

This ensures the pipeline never returns empty results from Qdrant due to an overly strict domain filter or score threshold.

### 3.5 BM25 In-Memory Index

The BM25 service (`bm25_service.py`) builds an **in-memory BM25Okapi index** by scrolling ALL Qdrant documents at startup for the requested `law_type`. This is not a separate search engine â€” it is a RAM-resident BM25 index constructed from the same corpus stored in Qdrant.

**Lazy loading with thread-safe locking:** The BM25 index for each `law_type` is built on first use, then cached. Scroll batch size: 500 records per request. The index for the full `labor` corpus (~4,000 articles) is built in ~2-5 seconds on first query, then served from RAM.

**Important implication:** The BM25 service needs enough RAM to hold the tokenized corpus in memory alongside the embedding model and reranker.

---

## 4. Query Processing â€” LangGraph Flow

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
     â†“
query_expansion
     â†“
retrieve
     â†“ (conditional)
   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚ confidence >= 0.35? â”‚
   â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
     YES  â”‚    NO
          â†“    â†“
answer_synthesis â† web_search
          â†“
         cite
          â†“
   generate_answer
          â†“
        verify
          â†“
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

## 5. Node 1 â€” Domain Detection (`detect_domain_node`)

**File:** `backend/app/graphs/legal_assistant/nodes_domain.py`

### Mechanism

Pure keyword-based scoring. No LLM call. No embedding.

1. Normalize the query with Arabic normalization (diacritics, alef variants, teh marbuta, alef maksura)
2. For each legal domain, count how many of its keywords appear in the normalized query
3. Select the domain with the highest keyword count
4. If all counts are zero â†’ `LegalDomain.UNKNOWN`

### Domain keyword lexicon (representative samples)

| Domain | Sample Arabic keywords |
|--------|----------------------|
| LABOR | Ø¹Ø§Ù…Ù„ØŒ ÙØµÙ„ØŒ Ø£Ø¬Ø±ØŒ Ø¥Ø¬Ø§Ø²Ø©ØŒ Ø¹Ù‚Ø¯ Ø¹Ù…Ù„ØŒ ØªØ£Ù…ÙŠÙ†Ø§Øª |
| TENANCY | Ø¥ÙŠØ¬Ø§Ø±ØŒ Ù…Ø³ØªØ£Ø¬Ø±ØŒ Ø¥Ø®Ù„Ø§Ø¡ØŒ Ø¹ÙŠÙ† Ù…Ø¤Ø¬Ø±Ø© |
| FAMILY | Ø²ÙˆØ§Ø¬ØŒ Ø·Ù„Ø§Ù‚ØŒ Ø­Ø¶Ø§Ù†Ø©ØŒ Ù†ÙÙ‚Ø©ØŒ Ù…ÙŠØ±Ø§Ø« |
| CRIMINAL | Ø¬Ø±ÙŠÙ…Ø©ØŒ Ø³Ø±Ù‚Ø©ØŒ Ø¹Ù‚ÙˆØ¨Ø©ØŒ Ø¬Ù†Ø­Ø©ØŒ Ø¨Ù„Ø§Øº |
| COMMERCIAL | Ø´Ø±ÙƒØ©ØŒ Ø´ÙŠÙƒØŒ ÙƒÙ…Ø¨ÙŠØ§Ù„Ø©ØŒ Ø¥ÙÙ„Ø§Ø³ |
| ADMINISTRATIVE | Ù‚Ø±Ø§Ø± Ø¥Ø¯Ø§Ø±ÙŠØŒ Ù…Ø¬Ù„Ø³ Ø§Ù„Ø¯ÙˆÙ„Ø©ØŒ ØªØ±Ø®ÙŠØµ |
| CIVIL | Ø¹Ù‚Ø¯ØŒ Ù…Ù„ÙƒÙŠØ©ØŒ Ø¶Ø±Ø±ØŒ Ù…Ø³Ø¤ÙˆÙ„ÙŠØ© |

### Domain â†’ Qdrant filter mapping

```python
DOMAIN_TO_FILTERS = {
    LegalDomain.LABOR:          (None, "labor"),
    LegalDomain.TENANCY:        (None, "civil"),   # tenancy = civil code
    LegalDomain.FAMILY:         (None, "family"),
    LegalDomain.CRIMINAL:       (None, "criminal"),
    LegalDomain.COMMERCIAL:     (None, "civil"),
    LegalDomain.ADMINISTRATIVE: (None, "other"),
    LegalDomain.CIVIL:          (None, "civil"),
    LegalDomain.UNKNOWN:        (None, None),      # no filter â†’ full corpus search
}
```

The first tuple element (category_filter) is always `None` because the category payload field is not filterable (stringified list format).

### Output

Sets `state["domain"]`, `state["law_type_filter"]`, `state["category_filter"]`.

### Limitation

Keyword scoring is fast but crude. A query like "Ù‡Ù„ ÙŠØ¬ÙˆØ² Ù„Ù„Ø´Ø±ÙƒØ© Ø£Ù† ØªÙØµÙ„ Ø§Ù„Ø¹Ø§Ù…Ù„" scores for both COMMERCIAL (`Ø´Ø±ÙƒØ©`) and LABOR (`Ø¹Ø§Ù…Ù„`, `ÙØµÙ„`). In this case, the correct domain (LABOR) wins only because it has more matching keywords. Ambiguous multi-domain queries can be mis-routed.

---

## 6. Node 2 â€” Query Expansion (HyDE)

**File:** `backend/app/graphs/legal_assistant/nodes_query_expansion.py`

### What HyDE is

HyDE (Hypothetical Document Embeddings) generates a hypothetical article text that *would* answer the query, then embeds that hypothetical text instead of (or alongside) the raw query vector. The insight: a hypothetical answer embeds closer to real answer documents than a short colloquial question does.

### Current activation condition

**HyDE only runs for `LegalDomain.UNKNOWN` queries.**

```python
if detected_domain and detected_domain != LegalDomain.UNKNOWN:
    return state  # skip HyDE
```

**Rationale (documented in code):** When a domain is detected, the query already contains specific legal keywords that make the original query vector precise enough. HyDE adds latency (+1â€“3s LLM call) that is only justified for vague, domain-ambiguous queries where the embedding may not retrieve the right domain of documents.

### HyDE generation

```
HYDE_SYSTEM_PROMPT: "ÙƒØªØ§Ø¨Ø© ÙÙ‚Ø±Ø© Ù‚ØµÙŠØ±Ø© ØªØ­Ø§ÙƒÙŠ Ù…Ø§Ø¯Ø© Ù‚Ø§Ù†ÙˆÙ†ÙŠØ©..."
HYDE_USER_PROMPT:   "Ø§Ù„Ø³Ø¤Ø§Ù„: {question}"
â†’ Groq LLM call (max_tokens=300, timeout=2.0s)
â†’ hypothetical Arabic legal article text
â†’ embed_query(hyde_doc) â†’ 1024-dim hyde_vector
```

### Output

Sets `state["hyde_vector"]` and `state["hyde_document"]`.
If timeout or error: adds `"hyde_generation_timeout"` to warnings, no hyde_vector set.

---

## 7. Node 3 â€” Retrieval (`retrieve_node`)

**File:** `backend/app/graphs/legal_assistant/nodes_retrieval.py`

This is the most complex node. It performs the full retrieval, reranking, and confidence scoring pipeline.

### 7.1 Torch CPU Thread Optimization

```python
import torch
torch.set_num_threads(os.cpu_count() or 4)
```
9% embedding speedup measured by using all available CPU cores.

### 7.2 Single-Vector vs. Dual-Vector Path

**Dual-vector path (when `hyde_vector` is set â€” UNKNOWN domain only):**

```
embed(original_query)  â†’ original_vector
hyde_vector (from state)

Qdrant dense search(hyde_vector,   top_k=8, query_text=None)   â†’ hyde_results
Qdrant dense search(original_vector, top_k=8, query_text=None)  â†’ original_results

best_pre_rrf_score = max cosine score across all pre-RRF results  # captured BEFORE RRF!

citations = _rrf_merge(hyde_results, original_results)
```

**Single-vector path (known domain â€” all LABOR, FAMILY, etc. queries):**

```
embed(original_query)  â†’ original_vector

retrieval_service.search(
    query_vector=original_vector,
    query_text=question,          # enables BM25 hybrid
    law_type=law_type_filter,
    top_k=8
) â†’ citations
```

### 7.3 Inside retrieval_service.search()

When called with `query_text` (the single-vector path):

```
1. Qdrant dense search (law_type filter + Saudi must_not)
   â†’ candidate_limit = max(top_k, 20) = 20 from Qdrant
   â†’ score_threshold = 0.30 (configurable)

2. BM25 search (same law_type filter)
   â†’ top 20 results from in-memory BM25Okapi index

3. RRF fusion â†’ merge dense + sparse ranked lists
   score(doc) = Î£ 1/(60 + rank_i)  (k=60)

4. Deduplication by (law_name, article_number, law_number)
   â†’ keep highest-scored duplicate

5. Return top_k=8
```

### 7.4 RRF: The Critical Score Transformation

After RRF fusion, `Citation.score` values become RRF weights:
- **Typical range: ~0.016** (document ranked 1st in both lists gets `2/(60+1) â‰ˆ 0.033`)
- **Not cosine similarity** (range 0.30â€“1.0)
- **Not BM25 scores** (range 0â€“20+)

**This matters for confidence scoring.** In the dual-vector path, the code explicitly captures the raw cosine similarity score before RRF fusion:

```python
all_pre_rrf = hyde_results + original_results
best_pre_rrf_score = max(c.score for c in all_pre_rrf)  # real cosine similarity
citations = _rrf_merge(hyde_results, original_results)   # scores now â‰ˆ 0.016
```

The `best_pre_rrf_score` is then passed to `compute_confidence()` as `top1_dense_score` â€” which expects cosine similarity range [0,1], not RRF weights.

In the single-vector path, scores from Qdrant are already genuine cosine similarity values (RRF is applied internally in `retrieval_service.search()` but the node uses `score_from_citations()` which is appropriate for this path).

### 7.5 Adaptive Reranking â€” Explicit Article Reference Skip

```python
def _should_skip_rerank(citations, question, law_type_filter):
    # Guard 1: need at least 2 candidates to have a meaningful skip
    if len(citations) < 2: return False, "too_few_candidates"

    # Guard 2: query must explicitly name an article number
    m = re.search(r"\bØ§Ù„Ù…Ø§Ø¯Ø©\s+(\d+)", question)
    if m is None: return False, "no_article_ref"

    article_ref = m.group(1)

    # Guard 3: raw top-1 must be that exact article
    top1_art = str(citations[0].article_number or "")
    if top1_art != article_ref: return False, "article_ref_not_top1"

    # Guard 4: domain filter active â†’ top-1 must be in that domain
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

**Why batch_size=1:** Measured fastest on CPU â€” 9,098ms vs 12,669ms for batch_size=32 with 8 pairs. CPU has no parallel batch execution; larger batches add memory allocation overhead without compute benefit.

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

Cross-encoder scores are calibrated: labor-relevant=0.96-0.99, family-relevant=0.36, corpus-miss=0.23-0.77. A global threshold of 0.30 is conservative â€” it only blocks completely stumped results while allowing the more variable family law scores (~0.36) through.

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

If `confidence < 0.35` â†’ route to web_search in the graph conditional edge.

### 7.9 Retrieval Node Output

State after retrieval:
```python
state["citations"]             # List[Citation], top-5 reranked, scored
state["retrieval_empty"]       # bool: True if 0 citations after all filters
state["retrieval_confidence"]  # float in [0,1]
```

---

## 8. Node 4 â€” Answer Synthesis (`answer_synthesis_node`)

**File:** `backend/app/graphs/legal_assistant/nodes_answer_synthesis.py`

This node runs unconditionally (both the high-confidence and web-search paths lead here).

**Primary purpose:** Merge local retrieval citations with Tavily web search results when web search ran.

**If web search did not run:**
- `web_results = []` â†’ no web citations â†’ return state with updated `retrieval_empty` flag

**If web search ran:**
- Local citations take priority (ranked first)
- Web citations appended after, deduped by chunk_id and URL
- Web citations have `law_type="web"`, no `law_number`/`law_year`/`article_number`
- Combined list becomes `state["citations"]`

---

## 9. Node 5 â€” Citation Agent (`citation_node`)

**File:** `backend/app/graphs/legal_assistant/nodes_citation.py`

Performs three operations on the reranked citations before generation:

**Step 1: Deduplication** â€” remove any citations with duplicate `chunk_id`, keeping the first occurrence (highest ranked)

**Step 2: Per-citation text trimming** â€” trim each citation's `text` to at most `CITATION_MAX_TEXT_TOKENS = 400` whitespace tokens. Uses a trailing ` â€¦` marker. Token counting is whitespace-split (no subword tokenizer â€” ~30% margin built into the budget for real tokenizer overhead).

**Step 3: Total budget enforcement** â€” accumulate token counts; stop adding citations once the total would exceed `CITATION_MAX_TOKENS = 3000` tokens. Citations are processed in ranking order, so the most relevant citations always survive.

**Output:** `state["citations"]` (trimmed, budgeted list), `state["context_tokens"]` (total token count)

This is not the same trimming as in `build_context()` in `nodes_generation.py`. Both apply: the citation node applies a 400-token per-citation limit to the `text` field stored in state; `build_context()` additionally trims each article to **120 words** when formatting the final LLM prompt.

---

## 10. Node 6 â€” Generation (`generate_answer_node`)

**File:** `backend/app/graphs/legal_assistant/nodes_generation.py`

### 10.1 Context Building

`build_context()` formats the citations list into a numbered article block:

```
[1] Ø§Ù„Ù…Ø§Ø¯Ø© 69 â€” Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ Ø±Ù‚Ù… 12 Ù„Ø³Ù†Ø© 2003
Ù†Øµ Ø§Ù„Ù…Ø§Ø¯Ø© Ø§Ù„ØªØ§Ø³Ø¹Ø© ÙˆØ§Ù„Ø³ØªÙŠÙ† ... [trimmed to 120 words]

[2] Ø§Ù„Ù…Ø§Ø¯Ø© 70 â€” Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ Ø±Ù‚Ù… 12 Ù„Ø³Ù†Ø© 2003
...
```

- Deduplicates by `(law_name, article_number)` â€” same article from two retrieval paths appears only once
- Trims each citation to **120 words** (whitespace split) with trailing ` â€¦`
- Preserves law reference metadata in the header line

### 10.2 History Block

`build_history_block()` formats the last N conversation turns (fetched from Redis memory by the API layer):

```
Ø³ÙŠØ§Ù‚ Ø§Ù„Ù…Ø­Ø§Ø¯Ø«Ø© Ø§Ù„Ø³Ø§Ø¨Ù‚Ø© Ø¨ÙŠÙ†Ùƒ ÙˆØ¨ÙŠÙ† Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…:
Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…: Ø³Ø¤Ø§Ù„ Ø³Ø§Ø¨Ù‚...
Ø¨ÙŠÙ‘Ù†Ø©: Ø¥Ø¬Ø§Ø¨Ø© Ø³Ø§Ø¨Ù‚Ø©...
```

Prepended to `system_prompt` if history exists.

### 10.3 Prompts

**`SYSTEM_PROMPT` (grounded path â€” when citations exist):**
Egyptian Arabic rules, mandatory answer structure, strict grounding rule: "Ø§Ø´ØªØºÙ„ Ø¨Ø³ Ù…Ù† Ø§Ù„Ù…ÙˆØ§Ø¯ Ø§Ù„Ù„ÙŠ ÙÙŠ Ø§Ù„Ø³ÙŠØ§Ù‚ Ø§Ù„Ù…Ø±ÙÙ‚", citation format rule, explicit hallucination prevention: "Ù„Ùˆ Ø§Ù„Ù…Ø¹Ù„ÙˆÙ…Ø© Ù…Ø´ Ù…ÙˆØ¬ÙˆØ¯Ø© ÙÙŠ Ø§Ù„Ø³ÙŠØ§Ù‚ØŒ Ù‚ÙˆÙ„ Ø¨Ø§Ù„Ø¸Ø¨Ø·..."

**`USER_PROMPT_TEMPLATE` (grounded path):**
```
Ø§Ù„Ø³Ø¤Ø§Ù„: {question}
Ø§Ù„Ù…ÙˆØ§Ø¯ Ø§Ù„Ù‚Ø§Ù†ÙˆÙ†ÙŠØ© Ø§Ù„Ù…Ø³ØªØ±Ø¬Ø¹Ø© (Ø¯ÙŠ Ù…ØµØ§Ø¯Ø±Ùƒ Ø§Ù„ÙˆØ­ÙŠØ¯Ø©):
{context}
Ù‚Ø¨Ù„ Ø§Ù„Ø¥Ø¬Ø§Ø¨Ø©: ØªØ£ÙƒØ¯ Ø¥Ù† Ø§Ù„Ù…ÙˆØ§Ø¯ Ø§Ù„Ù…Ø³ØªØ±Ø¬Ø¹Ø© ÙÙˆÙ‚ Ø¨ØªØªÙƒÙ„Ù… ÙØ¹Ù„Ø§Ù‹ Ø¹Ù† Ù…ÙˆØ¶ÙˆØ¹ Ø§Ù„Ø³Ø¤Ø§Ù„...
```

**`SYSTEM_PROMPT_GENERAL` / `USER_PROMPT_GENERAL` (fallback path â€” when `retrieval_empty=True`):**
Used when no citations were retrieved. Explicitly warns the model: "Ù…ÙÙŠØ´ Ù…ÙˆØ§Ø¯ Ù‚Ø§Ù†ÙˆÙ†ÙŠØ© Ù…ØªØ§Ø­Ø© Ù„Ù„Ø³Ø¤Ø§Ù„ Ø¯Ù‡." Instructs to answer from general legal knowledge but clearly disclaim the lack of specific citations.

### 10.4 LLM API Call

**File:** `backend/app/services/llm_service.py`

- Provider: Groq API (`api.groq.com`)
- Model: `openai/gpt-oss-120b`
- API style: OpenAI-compatible (`groq.AsyncGroq`)
- `temperature=0.1` (low randomness â€” legal answers should be consistent)
- `max_tokens=2048`
- Async call: `await llm.generate(system_prompt, user_prompt)`

### 10.5 Why openai/gpt-oss-120b

Benchmark comparison between candidate Groq models (2026-08-16):

| Model | Reliability | Avg latency | Disqualifier |
|-------|------------|------------|-------------|
| `llama-3.3-70b-versatile` | 2/5 queries | ~12,575ms | Sunset â€” 100K tokens/day cap |
| `openai/gpt-oss-120b` | **5/5** | **1,707ms** | None |
| `qwen/qwen3.6-27b` | 5/5 | 7,282ms | `<think>` block leakage to users |

Qwen's `<think>...</think>` chain-of-thought was delivered to end users in the raw response stream before the actual answer â€” a trust failure for a legal AI platform.

---

## 11. Node 7 â€” Verification (`verify_node`)

**File:** `backend/app/graphs/legal_assistant/nodes_verification.py`

Four checks in order:

### Check 1: Unsafe Request Detection

Regex patterns checked against the normalized question:
```python
r"ÙƒÙŠÙ (Ø£|Ø§Ø¹Ù…Ù„|Ø§ØµÙ†Ø¹)?\s*(Ø£Ù‡Ø±Ø¨|Ø£Ø²ÙˆØ±|Ø£Ø²ÙŠÙ)"
r"ØªÙ‡Ø±Ø¨ Ù…Ù† (Ø§Ù„Ø¶Ø±ÙŠØ¨Ø©|Ø§Ù„Ø¶Ø±Ø§Ø¦Ø¨|Ø§Ù„Ù‚Ø§Ù†ÙˆÙ†)"
r"ØªØ¬Ù†Ø¨ (Ø§Ù„Ù…Ø³Ø¤ÙˆÙ„ÙŠØ©|Ø§Ù„Ø¹Ù‚Ø§Ø¨|Ø§Ù„Ù…Ù„Ø§Ø­Ù‚Ø©)"
r"ÙƒÙŠÙÙŠØ© Ø§Ø±ØªÙƒØ§Ø¨"
```
If matched â†’ `final_answer = FALLBACK_UNSAFE`, `is_fallback = True`, `is_unsafe = True`

### Check 2: Empty Retrieval

If `state["retrieval_empty"] == True` (no citations after all retrieval fallbacks):
â†’ Accept the general-knowledge fallback answer from `SYSTEM_PROMPT_GENERAL`
â†’ `is_fallback = True`, `faithfulness_score = 0.0`

This is not a hard error â€” the answer was already generated using the general knowledge prompt that warned the user.

### Check 3: Low Confidence Warning (advisory only)

If `retrieval_confidence < 0.35` at this stage:
- Add `f"low_retrieval_confidence:{confidence}"` to warnings
- **Do NOT return fallback** â€” the graph router already processed this
- Allow faithfulness check to make the final call

### Check 4: Faithfulness Check

Token overlap between the generated answer and the combined citation text:

```python
faithfulness = |tokens(answer) âˆ© tokens(all_citation_texts)| / |tokens(answer)|
```

Tokenization: regex `[\u0600-\u06FFA-Za-z0-9]+`, minimum token length 2, with Arabic diacritics and Eastern Arabic digit normalization.

If `faithfulness < HALLUCINATION_MIN_OVERLAP (=0.10)`:
â†’ `final_answer = FALLBACK_LOW_FAITHFULNESS`
â†’ `is_fallback = True`

**Important limitation:** This is a lexical check. A correctly grounded answer that *paraphrases* legal text (instead of quoting it word-for-word) may fail the faithfulness check, producing a false fallback. The system prompt explicitly instructs the model to quote article text (`Ù†ØµÙˆØµ Ø§Ù„Ù…ÙˆØ§Ø¯ Ø§Ù„Ø¯Ø§Ø¹Ù…Ø© Ù…Ø¹ Ø£Ø±Ù‚Ø§Ù…Ù‡Ø§`), which reduces but does not eliminate this risk.

### Check 5: Citation Mismatch Detection

Extract article numbers from the generated answer (regex: `(?:Ø§Ù„Ù…Ø§Ø¯Ø©|Ù…Ø§Ø¯Ø©)\s*(\d+)`) and verify that all mentioned article numbers exist in the retrieved citation set.

If not a subset:
- Add `"citation_mismatch"` to warnings
- **Do NOT return fallback** â€” this is a warning only

### Final State

```python
state["final_answer"]        # str â€” the answer or a fallback message
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

The `citations` in the response are the **final citation objects** â€” trimmed text (max 400 tokens each), with all metadata preserved: `chunk_id`, `doc_id`, `law_name`, `law_number`, `law_year`, `law_type`, `category`, `article_number`, `text`, `score`.

---

## 13. Complete Walkthrough â€” Example Query

**Query:** `"Ù…Ø§ Ø­Ù‚ÙˆÙ‚ÙŠ Ù„Ùˆ Ø·Ø±Ø¯ÙˆÙ†ÙŠ Ù…Ù† Ø§Ù„Ø´ØºÙ„ØŸ"`

### Step 1 â€” HTTP Ingress

`POST /chat` body: `{"question": "Ù…Ø§ Ø­Ù‚ÙˆÙ‚ÙŠ Ù„Ùˆ Ø·Ø±Ø¯ÙˆÙ†ÙŠ Ù…Ù† Ø§Ù„Ø´ØºÙ„ØŸ"}`

FastAPI validates `ChatRequest` (length 2-1000, stripped). State initialized:
```python
{
    "question": "Ù…Ø§ Ø­Ù‚ÙˆÙ‚ÙŠ Ù„Ùˆ Ø·Ø±Ø¯ÙˆÙ†ÙŠ Ù…Ù† Ø§Ù„Ø´ØºÙ„ØŸ",
    "conversation_id": "uuid-...",
    "request_id": "uuid-...",
    "warnings": [],
}
```

### Step 2 â€” detect_domain

Normalized query: `"Ù…Ø§ Ø­Ù‚ÙˆÙ‚ÙŠ Ù„Ùˆ Ø·Ø±Ø¯ÙˆÙ†ÙŠ Ù…Ù† Ø§Ù„Ø´ØºÙ„"` (diacritics removed)

Keyword scoring:
- LABOR: matches `["ÙØµÙ„"â†’"Ø·Ø±Ø¯ÙˆÙ†ÙŠ", "Ø´ØºÙ„"]` â†’ score: 2
- Others: score: 0

Best domain: `LegalDomain.LABOR`
`law_type_filter = "labor"`, `category_filter = None`

### Step 3 â€” query_expansion (HyDE)

Domain is LABOR (not UNKNOWN) â†’ **HyDE skipped**
No `hyde_vector` set in state.

### Step 4 â€” retrieve

**Since no hyde_vector â†’ single-vector path:**

```
original_vector = embed("Ù…Ø§ Ø­Ù‚ÙˆÙ‚ÙŠ Ù„Ùˆ Ø·Ø±Ø¯ÙˆÙ†ÙŠ Ù…Ù† Ø§Ù„Ø´ØºÙ„ØŸ")  # 1024-dim float list

retrieval_service.search(
    query_vector=original_vector,
    query_text="Ù…Ø§ Ø­Ù‚ÙˆÙ‚ÙŠ Ù„Ùˆ Ø·Ø±Ø¯ÙˆÙ†ÙŠ Ù…Ù† Ø§Ù„Ø´ØºÙ„ØŸ",
    law_type="labor",
    top_k=8
)
```

Inside `search()`:
1. Qdrant dense search: vector similarity against `egypt_legal_rag`, `law_type=labor`, `must_not law_name=Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ`, `score_threshold=0.30`, `limit=20` â†’ ~15 Egyptian labor law articles
2. BM25 search: `tokenize("Ù…Ø§ Ø­Ù‚ÙˆÙ‚ÙŠ Ù„Ùˆ Ø·Ø±Ø¯ÙˆÙ†ÙŠ Ù…Ù† Ø§Ù„Ø´ØºÙ„")` â†’ ["Ø­Ù‚ÙˆÙ‚", "Ø·Ø±Ø¯", "Ø´ØºÙ„"] â†’ BM25Okapi against labor corpus â†’ 20 scored articles
3. RRF fusion: merge two ranked lists, scores become ~0.016â€“0.033
4. Dedup: by (law_name, article_number, law_number)
5. Return top 8

**Back in retrieve_node:**

Adaptive skip check:
- No "Ø§Ù„Ù…Ø§Ø¯Ø© X" in query â†’ `skip_reason = "no_article_ref"` â†’ **reranker runs**

BGE-reranker-v2-m3:
```python
pairs = [["Ù…Ø§ Ø­Ù‚ÙˆÙ‚ÙŠ Ù„Ùˆ Ø·Ø±Ø¯ÙˆÙ†ÙŠ Ù…Ù† Ø§Ù„Ø´ØºÙ„ØŸ", article_1.text],
         ["Ù…Ø§ Ø­Ù‚ÙˆÙ‚ÙŠ Ù„Ùˆ Ø·Ø±Ø¯ÙˆÙ†ÙŠ Ù…Ù† Ø§Ù„Ø´ØºÙ„ØŸ", article_2.text],
         ...  # 8 pairs
]
scores = model.predict(pairs, batch_size=1)
```

Suppose top reranker scores:
- Ø§Ù„Ù…Ø§Ø¯Ø© 69 Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ (ÙØµÙ„ ØªØ¹Ø³ÙÙŠ): 0.97
- Ø§Ù„Ù…Ø§Ø¯Ø© 71 Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ (ØªØ¹ÙˆÙŠØ¶ Ø§Ù„ÙØµÙ„): 0.94
- Ø§Ù„Ù…Ø§Ø¯Ø© 70 Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ (Ø¥Ø¬Ø±Ø§Ø¡Ø§Øª Ø§Ù„ÙØµÙ„): 0.91
- Ø§Ù„Ù…Ø§Ø¯Ø© 46 Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ (Ø§Ù„ØªØ²Ø§Ù…Ø§Øª ØµØ§Ø­Ø¨ Ø§Ù„Ø¹Ù…Ù„): 0.72
- Ø§Ù„Ù…Ø§Ø¯Ø© 15 Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„: 0.45

Top-5 after reranking. Relevance guard: max score 0.97 > 0.30 â†’ no guard triggered.

Confidence scoring (single-vector path, using Citation.score which is cosine similarity from Qdrant):
```python
confidence = 0.4 * 0.85   # top-1 cosine similarity (estimated)
           + 0.3 * 1.0    # recall: 5 docs / cap 5 = 1.0
           + 0.2 * 1.0    # domain_bonus: law_type_filter set
           + 0.1 * 0.97   # reranker_score
           = 0.34 + 0.30 + 0.20 + 0.097 = 0.937
```

`retrieval_confidence = 0.937` â†’ well above 0.35 â†’ graph routes to `answer_synthesis`

### Step 5 â€” answer_synthesis

No web search ran (confidence was high). `web_results = []` â†’ pass-through. `retrieval_empty = False`.

### Step 6 â€” cite

Input: 5 citations
- Dedup: no duplicates
- Per-citation trim: all citations within 400 tokens
- Total budget: ~400 tokens < 3000 â†’ all 5 kept

`context_tokens â‰ˆ 400`

### Step 7 â€” generate_answer

```python
context = build_context(state)
# Produces:
# [1] Ø§Ù„Ù…Ø§Ø¯Ø© 69 â€” Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ Ø±Ù‚Ù… 12 Ù„Ø³Ù†Ø© 2003
# Ù†Øµ Ø§Ù„Ù…Ø§Ø¯Ø©... [120 words max]
# [2] Ø§Ù„Ù…Ø§Ø¯Ø© 71 â€” Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ Ø±Ù‚Ù… 12 Ù„Ø³Ù†Ø© 2003
# Ù†Øµ Ø§Ù„Ù…Ø§Ø¯Ø©...

user_prompt = USER_PROMPT_TEMPLATE.format(
    question="Ù…Ø§ Ø­Ù‚ÙˆÙ‚ÙŠ Ù„Ùˆ Ø·Ø±Ø¯ÙˆÙ†ÙŠ Ù…Ù† Ø§Ù„Ø´ØºÙ„ØŸ",
    context=context
)
â†’ Groq API: openai/gpt-oss-120b, temp=0.1, max_tokens=2048
â†’ raw_answer: "Ù„Ø£ØŒ Ù…Ø´ ÙŠÙ†ÙØ¹Ø´ ØµØ§Ø­Ø¨ Ø§Ù„Ø´ØºÙ„ ÙŠØ·Ø±Ø¯Ùƒ Ù…Ù† ØºÙŠØ± Ø³Ø¨Ø¨ Ù‚Ø§Ù†ÙˆÙ†ÙŠ..."
```

### Step 8 â€” verify

1. Unsafe check: no unsafe patterns â†’ pass
2. retrieval_empty: False â†’ pass
3. Confidence 0.937: above threshold â†’ advisory only
4. Faithfulness: token overlap(answer, citations) â†’ suppose 0.45 (45%) > 0.10 â†’ **PASS**
5. Citation mismatch: answer mentions "Ø§Ù„Ù…Ø§Ø¯Ø© 69" and "Ø§Ù„Ù…Ø§Ø¯Ø© 71" â†’ both exist in retrieved citations â†’ **citation_valid = True**

### Step 9 â€” Final Response

```json
{
    "conversation_id": "uuid-...",
    "answer": "Ù„Ø£ØŒ Ù…Ø´ ÙŠÙ†ÙØ¹Ø´ ØµØ§Ø­Ø¨ Ø§Ù„Ø´ØºÙ„ ÙŠØ·Ø±Ø¯Ùƒ Ù…Ù† ØºÙŠØ± Ø³Ø¨Ø¨ Ù‚Ø§Ù†ÙˆÙ†ÙŠ...\n\n(Ø§Ù„Ù…Ø§Ø¯Ø© 69 Ù…Ù† Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ Ø±Ù‚Ù… 12 Ù„Ø³Ù†Ø© 2003)",
    "citations": [
        {
            "chunk_id": "labor_12_2003_art69",
            "doc_id": "labor_12_2003",
            "law_name": "Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„",
            "law_number": "12",
            "law_year": "2003",
            "law_type": "labor",
            "article_number": "69",
            "text": "Ù†Øµ Ø§Ù„Ù…Ø§Ø¯Ø©... [trimmed]",
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

The Groq API uses the OpenAI `/v1/chat/completions` protocol, making models like `openai/gpt-oss-120b` accessible through a single interface. No special handling is needed for the model name â€” it is just the model ID as listed in `client.models.list()`.

---

## 15. Embedding Service Details

**File:** `backend/app/services/embedding_service.py`

### Loading strategy (priority order)

1. **FlagEmbedding** (`BGEM3FlagModel`) â€” preferred; purpose-built for BGE-M3; supports fp16 on GPU
2. **sentence-transformers** (`SentenceTransformer`) â€” standard fallback
3. **Hash-based pseudo-embedding** â€” emergency fallback; produces 1024-dim deterministic random vectors from SHA-256 hash; **zero semantic signal; retrieval quality = 0%; logged as CRITICAL**

The hash fallback is **intentionally noisy in logs** so it cannot be silently missed in production.

### embed_query() via FlagEmbedding

```python
output = model.encode(
    [text],
    return_dense=True,
    return_sparse=False,    # BGE-M3 can return sparse + ColBERT vecs too â€” not used here
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
| Saudi law exclusion | `retrieval_service._build_filter()` | Every query | `must_not MatchAny(["Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„ Ø§Ù„Ø³Ø¹ÙˆØ¯ÙŠ"])` |
| Score threshold | `retrieval_service.search()` | Qdrant query | Exclude cosine similarity < 0.30 |
| Three-attempt retrieval | `retrieval_service.search()` | Empty result | Relax threshold, then drop filter |
| Relevance guard | `retrieve_node` | Cross-encoder max score < 0.30 | Treat as corpus miss (`retrieval_empty=True`) |
| HyDE timeout | `query_expansion_node` | LLM call > 2s | Skip HyDE, add warning, continue with original vector |
| Retrieval confidence | `graph.py` conditional edge | confidence < 0.35 | Route to web search fallback |
| Empty retrieval | `answer_synthesis_node`, `verify_node` | 0 citations | Use `SYSTEM_PROMPT_GENERAL`, `is_fallback=True` |
| Low faithfulness | `verify_node` | Token overlap < 10% | Return `FALLBACK_LOW_FAITHFULNESS`, `is_fallback=True` |
| Citation mismatch | `verify_node` | Article# in answer âˆ‰ retrieved | Add `"citation_mismatch"` warning (no fallback) |
| Embedding failure | `embedding_service._load()` | Model fails to load | Hash fallback (CRITICAL log) |
| Reranker failure | `reranker_service.rerank()` | Cross-encoder fails | Token-overlap fallback, then pass-through |
| Qdrant unavailable | `retrieval_service.__init__()` | Connection fails | Return empty citations â†’ fallback answer |
| BM25 unavailable | `bm25_service._connect()` | Connection fails | Return empty BM25 results, dense-only retrieval |

---

## 17. Current Architecture vs. Historical Alternatives

| Component | Current Implementation | Historical/Rejected | Reason for Current Choice |
|-----------|----------------------|-------------------|--------------------------|
| Embedding model | `BAAI/bge-m3` (FlagEmbedding, 1024-dim) | Earlier models (unspecified) | Best multilingual Arabic quality; native BGE support |
| Retrieval | Hybrid: dense (BGE-M3) + BM25 (BM25Okapi) + RRF | Dense-only | BM25 adds recall for exact legal terms and article numbers |
| RRF k value | 60 | N/A | Standard default; produces stable score distribution |
| Saudi law filter | `MatchAny` on exact `law_name` | `MatchText` (failed â€” requires full-text index) | `MatchAny` works on KEYWORD-indexed fields |
| HyDE activation | UNKNOWN domain queries only | All queries | Reduces latency; only adds value when query is domain-ambiguous |
| Reranker model | `BAAI/bge-reranker-v2-m3` | ms-marco-MiniLM, mMiniLMv2, bge-base | Best Arabic/Egyptian dialect quality across test categories |
| Reranker batch_size | 1 | 8, 32 | 9,098ms vs 12,669ms â€” CPU has no parallel batch benefit |
| Reranker candidates (top_k) | 8 | 3, 5 (quality regression), 20 (too slow) | Correct docs appear at rank 7-8; <8 causes regression |
| Adaptive skip rule | Explicit article reference only | RRF margin, absolute score, query length, dialect | Only this rule passed benchmarking safely |
| Generation model | `openai/gpt-oss-120b` via Groq | `llama-3.3-70b-versatile` (sunset), `qwen3.6-27b` (think bleed) | Reliability + latency + no `<think>` leakage |
| Confidence scoring | Multi-signal (dense + recall + domain + reranker) | Post-RRF scores (broken â€” â‰ˆ0.016) | Pre-RRF cosine similarity is the correct input |
| Faithfulness check | Token overlap â‰¥ 10% | â€” | Conservative; works without external model |
| BM25 index storage | In-memory (`BM25Okapi`) | â€” | Fast query latency; corpus fits in RAM |
| Fallback on Qdrant failure | Return `[]` (empty citations) | Return hardcoded mock articles | Mock articles caused wrong domain answers for every question |

---

## 18. Known Gaps in Repository Evidence

1. **Corpus preprocessing history:** The `dataflare/egypt-legal-corpus` dataset is already structured â€” the original PDF/web sources and any pre-processing pipeline that created this dataset exist outside this repository and are not documented here.

2. **Original collection creation parameters for the live Qdrant Cloud cluster:** The `ensure_collection()` function in `scripts/ingest.py` creates the collection with `KEYWORD` payload indexes. However, the actual live cluster may have been created differently (e.g., with different index types) depending on which ingestion path was used. The `law_name` field has a KEYWORD index (confirmed by `MatchAny` working on it), but the presence/absence of other indexes is not verifiable without direct Qdrant Cloud access.

3. **BM25 first-load latency at scale:** The BM25 service scrolls all Qdrant documents for a `law_type` on first use. The actual latency for the full `civil` corpus (~30,000+ articles) is not benchmarked in the repository.

4. **Streaming SSE path:** The streaming response (`POST /chat/stream`) uses Server-Sent Events but the streaming implementation details in `nodes_generation.py` are not traced in this document. The LLM service does support streaming via the Groq client.
