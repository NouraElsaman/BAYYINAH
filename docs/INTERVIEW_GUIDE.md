# BAYYINAH — Interview Guide
**For project presentations, technical interviews, and Master's programme discussions**

---

## Level 1 — 30-Second Elevator Pitch

> "BAYYINAH is an Arabic-first legal AI assistant that answers Egyptian law questions in Egyptian dialect. It uses Retrieval-Augmented Generation — it searches a corpus of 43,000 Egyptian legal articles, retrieves the most relevant ones, and generates a grounded answer that cites the exact law article. It refuses to answer questions it cannot support with retrieved evidence, which is critical for a legal domain where hallucination is dangerous."

---

## Level 2 — 2-Minute Overview

**The problem:** Egyptian citizens and lawyers need quick, reliable access to legal information, but legal databases are formal, complex, and require expertise to navigate. Generic LLMs hallucinate legal details and cite non-existent articles.

**The users:** Egyptian Arabic speakers asking labor law questions ("هو ينفع يطردني من الشغل بدون سبب؟"), tenancy disputes, personal status questions, and more.

**The solution:** BAYYINAH uses a 4-stage pipeline:

1. **Hybrid retrieval** — searches 43,582 Egyptian legal articles using both semantic embeddings (BGE-M3) and keyword search (BM25), fused with Reciprocal Rank Fusion.

2. **Cross-encoder reranking** — a BGE reranker jointly scores each retrieved article against the query for precision. This is the expensive step that runs on CPU, so it was carefully tuned.

3. **Grounded generation** — `openai/gpt-oss-120b` via Groq generates an answer in Egyptian colloquial Arabic, citing only the retrieved articles. It refuses to answer if evidence is insufficient.

4. **Verification** — faithfulness checking, citation validation, confidence scoring, and guardrails run before the response is returned.

**The stack:** FastAPI + LangGraph backend, Next.js 14 frontend, Qdrant Cloud vector database, deployed on Render.

---

## Level 3 — Deep Technical Questions

---

### 1. Why RAG instead of fine-tuning?

**Short answer:** Fine-tuning would memorize the corpus at training time. RAG retrieves at inference time, enabling up-to-date information and source attribution.

**Deep answer:** Fine-tuning an LLM on Egyptian legal text would:
- Require significant GPU time and cost
- Produce a model that cannot attribute its answers to specific articles
- Become stale as new laws are passed — requiring re-training
- Likely hallucinate article numbers and legal details not well-represented in training data

RAG instead keeps the LLM as a general reasoning engine and uses a vector database as the knowledge store. New laws are added by running the ingestion pipeline — no model retraining needed. Every answer is grounded in retrieved evidence with explicit citations. The LLM's job is to *synthesize* retrieved text, not to *memorize* legal facts.

---

### 2. Why LangGraph?

**Short answer:** The retrieval pipeline has conditional branching — different paths for different query types, confidence levels, and fallback conditions. LangGraph models this cleanly as a directed graph.

**Deep answer:** The legal assistant graph has 8 nodes:
```
detect_domain → query_expansion → retrieve → [answer_synthesis|web_search] → cite → generate_answer → verify → END
```
There are two conditional branches: (1) domain routing before retrieval, and (2) confidence-gated web search fallback after retrieval. LangGraph's `add_conditional_edges` makes these branches explicit, testable, and observable. LangChain alone (without LangGraph) would require manual state management and control flow.

---

### 3. Why Qdrant?

**Short answer:** Qdrant supports hybrid search (dense + sparse vectors in one query), has excellent Python client support, offers a free cloud tier, and supports metadata filtering that is essential for domain routing.

**Deep answer:** The retrieval uses two query types simultaneously: dense vector similarity (from BGE-M3) and BM25 sparse vectors. Qdrant supports this natively. Its `Filter` API (MatchValue, MatchAny, must_not conditions) enables the law_type domain filtering and Saudi law exclusion filter at query time. Alternatives like Pinecone support dense-only; Elasticsearch supports BM25 but requires more infrastructure setup.

---

### 4. Why hybrid retrieval?

**Short answer:** Dense embeddings capture semantic meaning; BM25 captures exact keyword matches. Legal text benefits from both.

**Deep answer:** Consider the query "ما هي المادة 69 من قانون العمل؟" (What does article 69 of the labor law say?). A dense embedding model encodes this as a semantic concept of "article 69 labor law" — but there are thousands of articles, and the embedding of the query and the embedding of the specific article may not be the closest pair in 1024-dimensional space. BM25 would directly surface documents containing the tokens "مادة 69" and "قانون العمل" with high TF-IDF scores. Fusing both with RRF surfaces the correct article from both directions, increasing recall.

---

### 5. What is BM25?

**Short answer:** BM25 is a ranking function that scores documents based on the frequency of query terms in the document, adjusted for document length and term frequency saturation.

**Deep answer:** BM25 (Best Match 25) extends TF-IDF with two improvements:
1. **Term saturation:** TF contribution levels off for high-frequency terms (prevents spam amplification)
2. **Length normalization:** Longer documents are penalized to avoid ranking bias toward verbose articles

Formula: `BM25(q,d) = sum over terms t: IDF(t) * (tf(t,d) * (k1+1)) / (tf(t,d) + k1 * (1 - b + b * |d|/avgdl))`

For Arabic legal text, BM25 is particularly useful for exact article numbering and specific legal terminology.

---

### 6. What are embeddings?

**Short answer:** Embeddings are dense numerical vectors that represent text in a high-dimensional semantic space, where semantically similar texts are close together.

**Deep answer:** BGE-M3 (from BAAI) encodes text into 1024-dimensional vectors. The model was trained on multilingual data including Arabic, using contrastive learning — similar texts are pushed together in vector space, dissimilar texts are pushed apart. At query time, the query is encoded into a vector, and Qdrant finds the nearest stored vectors using approximate nearest neighbor search. BGE-M3 specifically supports dense, sparse, and multi-vector retrieval from a single model — we use dense vectors for semantic search.

---

### 7. What is cosine similarity?

**Short answer:** Cosine similarity measures the angle between two vectors. A score of 1.0 means identical direction (maximum relevance), 0 means perpendicular (no relationship), -1 means opposite.

**Deep answer:** `cosine_similarity(a, b) = (a · b) / (||a|| * ||b||)`

Unlike Euclidean distance, cosine similarity is magnitude-independent — it measures the *direction* of vectors, not their length. For text embeddings this is correct behavior: a longer document with the same semantic content should have the same similarity as a shorter one.

**Important gotcha in this project:** After RRF fusion, citation scores become RRF weights (~0.016), NOT cosine similarity scores (~0.30-1.0). The retrieval confidence scorer had a bug where it misinterpreted post-RRF weights as cosine similarity, collapsing confidence to near-zero for all hybrid queries. The fix: capture the raw cosine similarity score *before* RRF fusion.

---

### 8. What is RRF?

**Short answer:** Reciprocal Rank Fusion combines multiple ranked lists into a single ranking by summing the reciprocal of each document's rank position across lists.

**Deep answer:** `RRF_score(doc) = sum(1 / (k + rank_in_list_i(doc)))` where k=60 (a smoothing constant).

**Why rank-based, not score-based:** BM25 scores and cosine similarity scores are on completely different scales. BM25 scores are document-collection-relative (can range from 0 to ~20). Cosine similarity is bounded [-1, 1]. You cannot meaningfully add them or find a weighting that works across all query types. RRF sidesteps this by only using rank positions.

**Practical effect:** A document ranked 1st in both lists gets `1/(60+1) + 1/(60+1) ≈ 0.033`. A document ranked 1st in one and 10th in the other gets `1/61 + 1/70 ≈ 0.030`. The combined ranking is robust to each individual list's idiosyncrasies.

---

### 9. Why use a reranker?

**Short answer:** Bi-encoder retrieval (embedding model) encodes query and document independently — fast but less precise. A reranker processes query+document pairs together, with full cross-attention, giving much higher relevance precision.

**Deep answer:** When BGE-M3 encodes "هل يجوز فصل العامل بدون سبب؟" as a vector, that vector represents the general semantic space of "labor termination questions." Every article about termination will be somewhat close to it. The reranker, by contrast, takes the full query text and full article text together and computes a relevance score that can distinguish "termination for cause" from "termination procedures" from "termination compensation." This is the precision/recall tradeoff: retrieval maximizes recall (get many relevant candidates), reranking maximizes precision (select the best).

---

### 10. What is a cross-encoder?

**Short answer:** A cross-encoder takes both query and document as a single concatenated input and outputs a relevance score. It uses full attention between query and document tokens.

**Deep answer:** In contrast to bi-encoders (used for embedding-based retrieval), cross-encoders like BAAI/bge-reranker-v2-m3 process `[CLS] query [SEP] document [SEP]` jointly. Every query token can attend to every document token and vice versa. This means the model can detect subtle mismatches — like a document that uses similar words but in a different legal context. The cost is speed: a cross-encoder cannot pre-compute document embeddings offline; it must process every query-document pair at inference time.

---

### 11. Why was BGE-v2-m3 chosen as the reranker?

**Short answer:** It was the only model that maintained quality on Egyptian dialect queries without quality regressions.

**Deep answer:** Four models were benchmarked:
- `ms-marco-MiniLM-L-6-v2`: English-only, completely fails on Arabic
- `mMiniLMv2-L12-H384-mMarcov2`: Multilingual but weak on Egyptian colloquial; missed key labor law distinctions
- `bge-reranker-base`: Better multilingual coverage but quality regressions on dialect queries like "هو ينفع يطردني من الشغل؟"
- `bge-reranker-v2-m3`: Best across all test categories including Egyptian dialect, formal Arabic, specific article references, and cross-domain queries

---

### 12. Why was candidate count kept at 8?

**Short answer:** Benchmarking showed correct documents appearing as deep as raw rank 7/8. Reducing below 8 caused measurable quality regressions.

**Deep answer:** A candidate reduction study benchmarked top_k from 3 to 20. At top_k=5, there were cases where the correct article was ranked 6th or 7th by the initial retrieval and would have been excluded from reranking. After reranking, it would have been the correct top-1. At top_k=8, no such regressions were observed in the benchmark. The internal implementation fetches 20 candidates from Qdrant for recall but passes only the top-8 by RRF score to the reranker — this is the compute savings while preserving quality.

---

### 13. Why was batch_size=1 faster on CPU?

**Short answer:** CPUs have no parallel batch execution benefit. Larger batches add memory allocation overhead without any compute parallelism gain.

**Deep answer:** GPU architectures have thousands of CUDA cores that can process matrix multiplications across a batch in parallel. A batch_size=32 on GPU processes 32 pairs simultaneously. On CPU, matrix operations are sequential — batch_size=32 processes 32 pairs one after another, with additional overhead for memory allocation and matrix reshaping per batch. Measured: batch_size=1 took ~9,098ms; batch_size=32 took ~12,669ms for 8 pairs on the same CPU. The smaller batch_size won because it minimizes per-step overhead without losing any compute parallelism (there is none on CPU).

---

### 14. What failed during optimization?

**Short answer:** Multiple reranker skip heuristics, candidate reduction below 8, lightweight reranker models, and Qwen3.6 as the generation model all failed benchmarking.

**Deep answer:**

*Reranker skip heuristics:* We hoped to find a rule like "if the top RRF score is high, skip the reranker." Benchmarks showed no reliable signal:
- RRF score margin had no clean separation between queries where reranking changed vs. did not change the top-1
- Absolute RRF scores are dataset-relative and cannot be thresholded globally
- Query length and dialect were unreliable proxy signals

*Candidate reduction:* Reducing to top_k=5 caused quality regressions when correct documents appeared at raw rank 6-8.

*Lighter reranker:* `bge-reranker-base` had quality regressions on Egyptian dialect queries specifically — the harder class of queries.

*Qwen3.6 generation:* Despite scoring 30/30 on deterministic checks (vs. 24/30 for gpt-oss-120b), Qwen exposed raw `<think>` chain-of-thought blocks to users. The actual answer was buried after a multi-paragraph internal reasoning trace. This is disqualifying for a production legal AI.

---

### 15. How did you evaluate retrieval quality?

**Short answer:** Golden test set benchmarking — manually curated query/expected-article pairs measured using Hit@1, Hit@3, Hit@5, and MRR metrics.

**Deep answer:** A golden test set of 12–20 queries was created, each with a known correct article. Metrics:
- **Hit@k:** Was the correct article in the top-k returned results?
- **MRR (Mean Reciprocal Rank):** Average of 1/rank for the correct article across queries. Punishes placing the correct answer at rank 3 more than rank 2.

Multiple pipeline configurations were benchmarked:
- Dense-only vs. hybrid
- Different reranker models
- Different top_k values
- With/without domain filtering

The adaptive reranking benchmark showed reranking materially improved 3/20 end-to-end answers — enough to keep it.

---

### 16. How did you evaluate answer quality?

**Short answer:** Deterministic check scoring + LLM-as-judge comparison + manual review of borderline cases.

**Deep answer:** The end-to-end A/B benchmark used:
- **Deterministic checks per response:** Did it answer? Egyptian dialect? Correct citation? Disclaimer present? No hallucination? Corpus-miss handled?
- **LLM-as-judge:** For ambiguous cases where both pipeline versions produced different answers, a third-model judge compared quality
- **Manual review:** Final decisions on borderline queries were made by human inspection

---

### 17. What were the hardest Arabic/NLP problems?

1. **Egyptian dialect retrieval:** Corpus is in formal Modern Standard Arabic (MSA). Queries arrive in Egyptian colloquial. BGE-M3 handles this reasonably well but the gap is real — "بيطردني" (Egyptian for "he fires me") vs. "إنهاء عقد العمل" (MSA for "employment termination"). HyDE partially addresses this by generating an MSA hypothetical document from the dialect query.

2. **Arabic tokenization for BM25:** Arabic has complex morphology — prefixes, suffixes, clitics. Standard tokenization would split "العمل" (the work) differently from "عمل" (work), missing BM25 matches. Custom Arabic tokenization was needed.

3. **Cross-domain false positives:** Labor law vocabulary overlaps significantly with civil law and commercial law vocabulary. Domain routing based on keywords was not always clean — queries about "employment contracts" could match both labor and commercial law.

4. **RRF score misinterpretation:** Post-RRF scores look like numbers (0.016) but are not comparable to cosine similarity (0.30-1.0). Any system component that treats RRF scores as similarity scores produces incorrect behavior.

---

### 18. How did Egyptian dialect affect retrieval?

**Impact:** Egyptian dialect queries like "هو ينفع يطردني من الشغل بدون سبب مش عارف أعمل إيه؟" use different vocabulary than the formal legal corpus ("إنهاء عقد العمل لغير سبب مشروع").

**Mitigations applied:**
1. **BGE-M3 multilingual training:** The embedding model was trained on extensive Arabic including Egyptian dialect
2. **HyDE query expansion:** Generates a formal Arabic hypothetical article from the dialect query, bridging the vocabulary gap
3. **Reranker cross-attention:** The cross-encoder can detect semantic relevance across register differences
4. **BM25 hybrid:** Even if the dense embedding misses, BM25 may surface documents containing related terminology

---

### 19. How did you reduce hallucination risk?

**Layered approach:**
1. **Grounded system prompt:** The SYSTEM_PROMPT explicitly instructs the model to answer *only* from provided citations. If the answer is not in the citations, refuse.
2. **Retrieval confidence gating:** If retrieval confidence < 0.35, route to fallback instead of generating from low-quality context.
3. **Citation-only context:** Only the retrieved article texts are passed to the model as context — no general legal knowledge injected.
4. **Faithfulness check:** Post-generation, verify ≥10% token overlap between the answer and the source citations.
5. **Citation mismatch check:** Verify that article numbers mentioned in the answer exist in the retrieved set.
6. **Explicit refusal training:** The prompt instructs: "إذا المعلومة مش موجودة في المواد، قول صراحة إنك مش لاقيها."

---

### 20. How are citations handled?

**Flow:**
1. The reranker outputs top-5 citations with scores
2. `nodes_citation.py` applies a token budget (max 3,000 tokens total, max 400 per citation) to fit within the LLM context window
3. Each citation's full article text is included in the generation prompt
4. The generated answer references specific law names and article numbers
5. The API response includes structured citation objects with `law_name`, `law_number`, `law_year`, `article_number`, `text`, and `score`
6. The frontend renders citation cards showing the exact legal text

---

### 21. What happened with Saudi law contamination?

**Problem:** The Hugging Face corpus contained Saudi Arabian labor law articles alongside Egyptian ones, all tagged with `law_type="labor"`. Because they used similar labor law vocabulary, they were surfacing in Egyptian labor law queries.

**First fix attempt (failed):** Used Qdrant's `MatchText` operator on `law_name` to exclude articles where law_name contains "سعودي". This failed because `MatchText` requires a full-text payload index on the field, which did not exist for `law_name`.

**Correct fix (implemented):** Used `MatchAny(any=["قانون العمل السعودي"])` — an exact string match against the literal law_name value. `MatchAny` works on unindexed keyword fields. The exact value "قانون العمل السعودي" was confirmed by querying the Qdrant payload directly.

**Lesson:** Qdrant filtering operators have specific index requirements. `MatchText` requires full-text index, `MatchValue`/`MatchAny` work on plain string fields. Always verify operator compatibility with actual payload structure.

---

### 22. Why was the generation model migrated?

**Short answer:** Groq sunset `llama-3.3-70b-versatile` with a 100K tokens/day cap. 3 of 5 test queries failed with 429 errors on the same day.

**Technical context:** The model was formally decommissioned on 2026-08-16. Groq reduced the daily token limit from effectively unlimited to 100K tokens/day — equivalent to ~50–70 full legal questions per day. This is not viable for a production service.

**Migration process:**
1. Enumerated all available Groq models via `client.models.list()`
2. Shortlisted Arabic-capable models: `openai/gpt-oss-120b` and `qwen/qwen3.6-27b`
3. Benchmarked both against 5 representative queries using production prompts
4. Selected `openai/gpt-oss-120b`
5. Updated 4 configuration files (config.py, .env, .env.example, render.yaml)
6. Re-ran full test suite: 245/245 passing

---

### 23. Why was openai/gpt-oss-120b selected?

**Three decisive factors:**

1. **Latency:** 1,707ms average vs. 7,282ms for Qwen — 4.3× faster. For a legal Q&A service, 7s average latency would be user-hostile.

2. **No `<think>` block leakage:** Qwen 3.6-27b uses chain-of-thought reasoning, exposing `<think>...</think>` blocks with internal reasoning traces in the response. These were delivered to end users in testing. For a legal AI, showing users "Here's me thinking step by step..." before a legal answer damages credibility and trust.

3. **Reliability at scale:** 5/5 queries answered vs. 2/5 for the deprecated model. No 429 errors, no timeouts.

**On the deterministic score discrepancy:** Qwen scored 30/30 vs. gpt-oss-120b's 24/30. The 6-point gap is explained by two false negatives: gpt-oss-120b correctly refused to generate an answer for out-of-corpus queries with a short "المعلومة دي مش موجودة" response. The benchmark's length check penalized this correct refusal behavior. In real use, refusing to hallucinate is better behavior than scoring higher on a metric that doesn't capture refusal quality.

---

### 24. What would you improve with more time/resources?

**Technical improvements:**

1. **GPU deployment for the reranker:** The biggest remaining latency bottleneck. A T4 GPU would reduce reranker time from 3–9s to <100ms. Currently too expensive for the Render starter/standard plan.

2. **Semantic faithfulness checking:** The current faithfulness check is lexical (token overlap ≥10%). It fails for paraphrased answers that are genuinely grounded. Replace with BGE-M3 cosine similarity between the answer and citations.

3. **Payload indexing on `law_name`:** Would allow efficient MatchText filtering for more nuanced Saudi law exclusion and enable searching within specific law families.

4. **Automated re-ingestion pipeline:** New Egyptian legislation triggers an automatic re-ingestion workflow rather than a manual CLI run.

5. **Multi-turn evaluation:** Current evaluation is single-turn. Multi-turn conversations with context accumulation need dedicated evaluation.

**Research directions:**

6. **Arabic legal NLP benchmark:** There is no standardized Egyptian legal QA benchmark. Creating one would enable reproducible evaluation.

7. **Reranker fine-tuning on Egyptian legal pairs:** BGE-reranker-v2-m3 is a general multilingual model. Fine-tuning on Egyptian legal query/article pairs could improve precision without changing the architecture.

---

## Challenges I Personally Faced and How I Solved Them

### Challenge 1 — Embedding Dimension Mismatch on Fallback
**Problem:** An early version of the embedding service used a 384-dimension fallback model when BGE-M3 (1024-dim) was unavailable. Qdrant rejects points with the wrong vector dimension, causing crashes.
**Investigation:** Traced the exception to the fallback code path in `embedding_service.py`.
**Solution:** Replaced the 384-dim fallback with a deterministic hash-based 1024-dim vector. The fallback produces a stable embedding that matches the collection dimension, even if its quality is poor.
**Status:** IMPLEMENTED.

### Challenge 2 — RRF Scores Breaking the Confidence Scorer
**Problem:** After adding hybrid retrieval with RRF fusion, the retrieval confidence scorer was returning near-zero for all queries. The system was triggering web search fallback for every request, even for high-quality retrievals.
**Investigation:** The confidence scorer used `Citation.score` as the "top-1 dense similarity score." After RRF fusion, `Citation.score` is the RRF weight (~0.016), not the cosine similarity (~0.50-0.90).
**Solution:** In the dual-vector search path, capture `max(c.score for c in pre_rrf_citations)` *before* calling `_rrf_merge()`, and pass that pre-fusion score to the confidence scorer.
**Status:** IMPLEMENTED.

### Challenge 3 — Saudi Law Contamination via Wrong Qdrant Filter
**Problem:** Egyptian labor law queries were retrieving Saudi labor law articles. Initial filtering attempt using `MatchText` on `law_name` silently failed and had no effect.
**Investigation:** Read Qdrant documentation. `MatchText` requires a full-text payload index on the field, which was not created during ingestion. The filter was silently ignored.
**Solution:** Used `MatchAny(any=["قانون العمل السعودي"])` with the exact string value confirmed by direct payload inspection. `MatchAny` works on unindexed string fields.
**Lesson:** Always test filters with a direct Qdrant query before assuming they work.

### Challenge 4 — Reranker batch_size Making Things Slower
**Problem:** Initially assumed larger batch_size would be faster (GPU intuition). Set batch_size=32. Measured latency was 12,669ms.
**Investigation:** Profiled batch_size 1, 4, 8, 16, 32 with 8 candidate pairs on CPU.
**Finding:** batch_size=1 (9,098ms) was fastest because CPU has no parallel execution benefit. Larger batches just add memory overhead.
**Status:** IMPLEMENTED — batch_size=1 hardcoded with an explanatory comment.

### Challenge 5 — Generation Model Decommissioning in Production
**Problem:** Groq decommissioned `llama-3.3-70b-versatile` during active development. Discovered via 429 errors and 56-second timeouts during a benchmark session.
**Investigation:** Listed available models via Groq API. Benchmarked the two best Arabic candidates against production prompts.
**Solution:** Migrated to `openai/gpt-oss-120b` (4 config file changes, 0 code changes). Re-ran 245 unit tests — all passing.
**Lesson:** Never hardcode a specific hosted model name in config defaults without a documented rotation plan. Monitor provider deprecation notices.

### Challenge 6 — HyDE Causing Semantic Drift
**Problem:** After adding HyDE, retrieval sometimes returned less relevant results than before. The hypothetical document was drifting into a different semantic space.
**Investigation:** Logged both the HyDE hypothetical document and the original query retrieval results side-by-side. Confirmed that for some queries, the hypothetical document described a different scenario than the user actually asked.
**Solution:** Dual-vector search — run both HyDE vector and original query vector, then RRF-merge. The original query vector acts as an anchor, preventing HyDE drift from dominating.
**Status:** IMPLEMENTED.

---

## Quick Reference — Architecture in One Sentence

> BAYYINAH is a 9-node LangGraph pipeline that takes an Egyptian Arabic legal question, routes it by domain, optionally expands it via HyDE, retrieves from 43,582 articles using hybrid dense+BM25 search fused with RRF, cross-encoder reranks the top-8 candidates, scores retrieval confidence, and generates a grounded Egyptian-dialect answer using openai/gpt-oss-120b via Groq — refusing to answer when evidence is insufficient.
