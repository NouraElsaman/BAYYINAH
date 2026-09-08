# بيّنة | BAYYINAH — Egyptian Legal AI Assistant

> Arabic-first legal AI that answers Egyptian law questions in Egyptian dialect, grounded in 43,582 Egyptian legal articles.

[![CI](https://github.com/Shahd-Ayman1/DIgitLaw/actions/workflows/ci.yml/badge.svg)](https://github.com/Shahd-Ayman1/DIgitLaw/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Tests](https://img.shields.io/badge/tests-245%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What It Does

BAYYINAH answers Egyptian legal questions ("هل يجوز فصل العامل بدون سبب؟") in Egyptian colloquial dialect, citing the exact law article. It **refuses to answer** when the retrieved corpus does not support the question — because hallucination in a legal context is dangerous.

Two products:
- **Legal Assistant** — conversational RAG over Egyptian law, multi-turn, streaming
- **Contract Analysis** — clause extraction, risk detection, and structured PDF/DOCX analysis

---

## Key Features

- 🗣️ **Egyptian dialect-first** — answers in colloquial Arabic, not formal MSA
- 📚 **Grounded generation** — every answer cites the specific law article and refuses unsupported claims
- 🔍 **Hybrid retrieval** — dense (BGE-M3) + BM25 + Reciprocal Rank Fusion
- 🎯 **Cross-encoder reranking** — BAAI/bge-reranker-v2-m3 with adaptive skip for article-reference queries
- 🧠 **Multi-turn memory** — Redis-backed conversation history
- 📄 **Contract analysis** — PDF/DOCX upload, clause analysis, risk detection
- 🔄 **Streaming responses** — real-time SSE token streaming
- 📊 **Observability** — Prometheus metrics + JSON structured logging
- 🛡️ **Guardrails** — faithfulness, citation mismatch, unsafe request detection

---

## Architecture

### Request Flow

```
User question (Egyptian dialect or formal Arabic)
│
├── detect_domain ──────── law_type filter (labor/tenancy/family/criminal/civil)
├── query_expansion ─────── HyDE: generate hypothetical article, embed it
├── retrieve ────────────── BGE-M3 dense + BM25 sparse → RRF fusion → top-8
│   └── rerank ──────────── BAAI/bge-reranker-v2-m3 cross-encoder → top-5
│                           (skip if explicit article reference at top-1)
├── confidence_score ─────── multi-signal confidence check
│   ├── [high] → answer_synthesis
│   └── [low]  → web_search (Tavily) → answer_synthesis
├── cite ────────────────── token-budget citation truncation
├── generate_answer ─────── openai/gpt-oss-120b via Groq + conversation history
└── verify ──────────────── faithfulness, citation mismatch, safety guardrails
```

### Services

```
frontend (Next.js 14)
│
│  POST /chat           POST /chat/stream        POST /contract-analysis
│  GET  /health         GET  /metrics (Prometheus)
│
backend (FastAPI + LangGraph)
│
├── Legal Assistant Graph (8 nodes)
│   detect_domain → query_expansion → retrieve → web_search?
│   → answer_synthesis → cite → generate_answer → verify
│
└── Contract Analysis Graph
    extract → chunk → analyze_clauses → detect_risks → summarize
│
├── Qdrant Cloud       (vector store — egypt_legal_rag collection, 43,582 vectors)
├── BAAI/bge-m3        (dense embeddings, 1024-dim)
├── BAAI/bge-reranker-v2-m3  (cross-encoder reranker, CPU)
├── Groq               (LLM API — openai/gpt-oss-120b)
└── Redis              (conversation memory, optional)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | `openai/gpt-oss-120b` via Groq |
| Embeddings | `BAAI/bge-m3` (1024-dim dense) |
| Reranker | `BAAI/bge-reranker-v2-m3` |
| Vector DB | Qdrant Cloud |
| Graph Orchestration | LangGraph 0.2 |
| Backend | FastAPI + Uvicorn/Gunicorn |
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Radix UI |
| Observability | Prometheus metrics + JSON structured logs |
| Container | Docker + Docker Compose |
| Deployment | Render (Blueprint) |
| CI/CD | GitHub Actions |

---

## Quick Start (Docker Compose)

```bash
cp .env.example .env
# Fill in: GROQ_API_KEY, QDRANT_URL, QDRANT_API_KEY

docker compose up --build
```

- Frontend → http://localhost:3000
- Backend API → http://localhost:8000/docs
- Qdrant UI → http://localhost:6333/dashboard

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values:

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Groq API key (get at console.groq.com) |
| `QDRANT_URL` | ✅ | Qdrant server URL |
| `QDRANT_API_KEY` | Cloud only | Qdrant JWT token |
| `QDRANT_COLLECTION` | default: `egypt_legal_rag` | Collection name |
| `GROQ_MODEL` | default: `openai/gpt-oss-120b` | Groq model name |
| `SECRET_KEY` | ✅ production | JWT signing secret |
| `CORS_ORIGINS` | ✅ production | Allowed frontend origins (JSON array) |
| `REDIS_URL` | optional | Redis for conversation memory |
| `TAVILY_API_KEY` | optional | Web search fallback (disabled by default) |
| `NEXT_PUBLIC_API_URL` | frontend | Backend base URL |

---

## Backend Development

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate  # Windows
# source .venv/bin/activate                       # Linux/macOS

pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

### Run tests

```bash
cd backend
pytest tests/ -v --ignore=tests/test_integration.py
# 245 tests, 0 failures
```

---

## Frontend Development

```bash
cd frontend
npm install --legacy-peer-deps

NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
# Windows:
# set NEXT_PUBLIC_API_URL=http://localhost:8000 && npm run dev
```

---

## Corpus Ingestion

The legal corpus is not included in this repository (98MB, excluded by `.gitignore`). To ingest:

```bash
# Option 1: CLI (local, requires the JSONL corpus file)
cd backend
python ../scripts/ingest.py \
  --input /path/to/legal_corpus.jsonl \
  --qdrant-url https://YOUR-CLUSTER.cloud.qdrant.io \
  --qdrant-api-key YOUR-JWT \
  --collection egypt_legal_rag \
  --batch-size 32

# Option 2: Notebook (Colab/Kaggle — downloads corpus from HuggingFace)
# Open bayyinah_ingest.ipynb and follow the instructions
# Set QDRANT_URL / QDRANT_API_KEY as environment secrets before running
```

### JSONL corpus format

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
  "text": "نص المادة التاسعة والستين...",
  "context_text": "نص السياق...",
  "cross_references": ["labor_12_2003_art68"]
}
```

**Supported `law_type` values for metadata filtering:**
`labor`, `civil`, `criminal`, `family`, `procedural`, `constitutional`, `other`

---

## Deployment (Render Blueprint)

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the complete deployment guide.

**Quick deploy:**

1. Push this repository to GitHub.
2. In Render dashboard → **New → Blueprint** → select this repo.
3. Render reads `render.yaml` and creates:
   - `digitlaw-backend` (Docker, standard plan)
   - `digitlaw-frontend` (Docker, starter plan)
   - `digitlaw-redis` (managed Redis)
4. Set these secrets in Render dashboard for `digitlaw-backend`:
   - `GROQ_API_KEY`
   - `QDRANT_URL`
   - `QDRANT_API_KEY`
5. Add GitHub Actions secrets for CD:
   - `RENDER_BACKEND_DEPLOY_HOOK`
   - `RENDER_FRONTEND_DEPLOY_HOOK`

---

## API Reference

### `POST /chat`

```json
{
  "question": "هل يجوز فصل العامل بدون سبب؟",
  "conversation_id": "optional-uuid",
  "stream": false
}
```

Response:
```json
{
  "conversation_id": "uuid",
  "answer": "لأ، مش ينفع صاحب الشغل يطردك من غير سبب قانوني...",
  "citations": [
    {
      "chunk_id": "labor_12_2003_art69",
      "law_name": "قانون العمل",
      "law_number": "12",
      "law_year": "2003",
      "article_number": "69",
      "text": "نص المادة...",
      "score": 0.94
    }
  ],
  "domain": "labor",
  "faithfulness_score": 0.71,
  "is_fallback": false,
  "warnings": []
}
```

### `POST /chat/stream`

Same body as `/chat`. Returns `text/event-stream`:
- `data: {"type":"token","content":"..."}` — streaming tokens
- `data: {"type":"done","final_answer":"...","citations":[...],"is_fallback":false}` — completion
- `data: {"type":"error","message":"..."}` — guardrail or server error

### `POST /contract-analysis`

`multipart/form-data` with `file` field (PDF or DOCX, max 15MB). Returns full `ContractAnalysisResponse` with summary, clause analyses, risks, missing clauses, recommendations, and overall risk level.

### `GET /health`

```json
{"status": "ok", "uptime_seconds": 142.3, "environment": "production", "dependencies": {"qdrant": "ok"}}
```

### `GET /metrics`

Prometheus text format metrics including request counts, latency histograms, faithfulness score distribution, and fallback counters.

---

## Guardrails

| Guardrail | Trigger | Action |
|-----------|---------|--------|
| Empty retrieval | No relevant articles found | Fallback response |
| Low confidence | Retrieval confidence < 0.35 | Web search fallback or fallback response |
| Low faithfulness | Token overlap < 10% | Fallback response, log warning |
| Citation mismatch | Article numbers in answer not in retrieved set | Warning flag in response |
| Unsafe request | Regex match on harmful intent | Block and return safe refusal |

---

## Project Structure

```
bayyinah/
├── backend/
│   ├── app/
│   │   ├── main.py                   FastAPI app + middleware
│   │   ├── core/
│   │   │   ├── config.py             Pydantic settings (all env vars)
│   │   │   └── logging.py            JSON structured logging
│   │   ├── services/
│   │   │   ├── embedding_service.py  BAAI/bge-m3 (singleton)
│   │   │   ├── retrieval_service.py  Qdrant + BM25 + RRF
│   │   │   ├── reranker_service.py   BGE-reranker-v2-m3 (CPU)
│   │   │   ├── bm25_service.py       Arabic BM25 tokenization
│   │   │   ├── confidence_scorer.py  Retrieval confidence scoring
│   │   │   ├── memory_service.py     Redis conversation memory
│   │   │   ├── llm_service.py        Groq async client
│   │   │   └── web_search_service.py Tavily web search fallback
│   │   ├── graphs/
│   │   │   ├── legal_assistant/      8-node LangGraph pipeline
│   │   │   └── contract_analysis/    LangGraph contract pipeline
│   │   └── api/
│   │       ├── chat.py               POST /chat, POST /chat/stream
│   │       ├── contract.py           POST /contract-analysis
│   │       └── system.py             GET /health, GET /metrics
│   ├── tests/                        245 unit tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                      Next.js App Router pages
│   │   ├── components/               Chat, contract, citation UI
│   │   └── lib/                      API client, SSE streaming
│   ├── package.json
│   └── Dockerfile
├── docs/
│   ├── PROJECT_EVOLUTION.md          Engineering decisions history
│   ├── INTERVIEW_GUIDE.md            Technical explanations
│   └── DEPLOYMENT.md                 Full deployment guide
├── scripts/
│   └── ingest.py                     Corpus ingestion CLI
├── bayyinah_ingest.ipynb             GPU-accelerated Colab/Kaggle ingestion
├── docker-compose.yml                Local development orchestration
├── render.yaml                       Render Blueprint deployment
├── .env.example                      Environment variable template
└── .github/
    └── workflows/
        ├── ci.yml                    Test + build on push/PR
        └── deploy.yml                Trigger Render deploy on main
```

---

## Further Documentation

| Document | Description |
|----------|-------------|
| [`docs/PROJECT_EVOLUTION.md`](docs/PROJECT_EVOLUTION.md) | Complete engineering history — retrieval experiments, reranker optimization, model migration |
| [`docs/INTERVIEW_GUIDE.md`](docs/INTERVIEW_GUIDE.md) | Deep technical Q&A for interviews and Master's discussions |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Full deployment configuration and troubleshooting |

---

## License

MIT License — see [LICENSE](LICENSE)
