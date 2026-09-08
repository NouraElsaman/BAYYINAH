# Ø¨ÙŠÙ‘Ù†Ø© | BAYYINAH â€” Egyptian Legal AI Assistant

> Arabic-first legal AI that answers Egyptian law questions in Egyptian dialect, grounded in 43,582 Egyptian legal articles.

[![CI](https://github.com/NouraElsaman/BAYYINAH/actions/workflows/ci.yml/badge.svg)](https://github.com/NouraElsaman/BAYYINAH/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Tests](https://img.shields.io/badge/tests-247%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What It Does

BAYYINAH answers Egyptian legal questions ("Ù‡Ù„ ÙŠØ¬ÙˆØ² ÙØµÙ„ Ø§Ù„Ø¹Ø§Ù…Ù„ Ø¨Ø¯ÙˆÙ† Ø³Ø¨Ø¨ØŸ") in Egyptian colloquial dialect, citing the exact law article. It **refuses to answer** when the retrieved corpus does not support the question â€” because hallucination in a legal context is dangerous.

Two products:
- **Legal Assistant** â€” conversational RAG over Egyptian law, multi-turn, streaming
- **Contract Analysis** â€” clause extraction, risk detection, and structured PDF/DOCX analysis

---

## Key Features

- ðŸ—£ï¸ **Egyptian dialect-first** â€” answers in colloquial Arabic, not formal MSA
- ðŸ“š **Grounded generation** â€” every answer cites the specific law article and refuses unsupported claims
- ðŸ” **Hybrid retrieval** â€” dense (BGE-M3) + BM25 + Reciprocal Rank Fusion
- ðŸŽ¯ **Cross-encoder reranking** â€” BAAI/bge-reranker-v2-m3 with adaptive skip for article-reference queries
- ðŸ§  **Multi-turn memory** â€” Redis-backed conversation history
- ðŸ“„ **Contract analysis** â€” PDF/DOCX upload, clause analysis, risk detection
- ðŸ”„ **Streaming responses** â€” real-time SSE token streaming
- ðŸ“Š **Observability** â€” Prometheus metrics + JSON structured logging
- ðŸ›¡ï¸ **Guardrails** â€” faithfulness, citation mismatch, unsafe request detection

---

## Architecture

### Request Flow

```
User question (Egyptian dialect or formal Arabic)
â”‚
â”œâ”€â”€ detect_domain â”€â”€â”€â”€â”€â”€â”€â”€ law_type filter (labor/tenancy/family/criminal/civil)
â”œâ”€â”€ query_expansion â”€â”€â”€â”€â”€â”€â”€ HyDE: generate hypothetical article, embed it
â”œâ”€â”€ retrieve â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ BGE-M3 dense + BM25 sparse â†’ RRF fusion â†’ top-8
â”‚   â””â”€â”€ rerank â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ BAAI/bge-reranker-v2-m3 cross-encoder â†’ top-5
â”‚                           (skip if explicit article reference at top-1)
â”œâ”€â”€ confidence_score â”€â”€â”€â”€â”€â”€â”€ multi-signal confidence check
â”‚   â”œâ”€â”€ [high] â†’ answer_synthesis
â”‚   â””â”€â”€ [low]  â†’ web_search (Tavily) â†’ answer_synthesis
â”œâ”€â”€ cite â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ token-budget citation truncation
â”œâ”€â”€ generate_answer â”€â”€â”€â”€â”€â”€â”€ openai/gpt-oss-120b via Groq + conversation history
â””â”€â”€ verify â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ faithfulness, citation mismatch, safety guardrails
```

### Services

```
frontend (Next.js 14)
â”‚
â”‚  POST /chat           POST /chat/stream        POST /contract-analysis
â”‚  GET  /health         GET  /metrics (Prometheus)
â”‚
backend (FastAPI + LangGraph)
â”‚
â”œâ”€â”€ Legal Assistant Graph (8 nodes)
â”‚   detect_domain â†’ query_expansion â†’ retrieve â†’ web_search?
â”‚   â†’ answer_synthesis â†’ cite â†’ generate_answer â†’ verify
â”‚
â””â”€â”€ Contract Analysis Graph
    extract â†’ chunk â†’ analyze_clauses â†’ detect_risks â†’ summarize
â”‚
â”œâ”€â”€ Qdrant Cloud       (vector store â€” egypt_legal_rag collection, 43,582 vectors)
â”œâ”€â”€ BAAI/bge-m3        (dense embeddings, 1024-dim)
â”œâ”€â”€ BAAI/bge-reranker-v2-m3  (cross-encoder reranker, CPU)
â”œâ”€â”€ Groq               (LLM API â€” openai/gpt-oss-120b)
â””â”€â”€ Redis              (conversation memory, optional)
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

- Frontend â†’ http://localhost:3000
- Backend API â†’ http://localhost:8000/docs
- Qdrant UI â†’ http://localhost:6333/dashboard

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values:

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | âœ… | Groq API key (get at console.groq.com) |
| `QDRANT_URL` | âœ… | Qdrant server URL |
| `QDRANT_API_KEY` | Cloud only | Qdrant JWT token |
| `QDRANT_COLLECTION` | default: `egypt_legal_rag` | Collection name |
| `GROQ_MODEL` | default: `openai/gpt-oss-120b` | Groq model name |
| `SECRET_KEY` | âœ… production | JWT signing secret |
| `CORS_ORIGINS` | âœ… production | Allowed frontend origins (JSON array) |
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

# Option 2: Notebook (Colab/Kaggle â€” downloads corpus from HuggingFace)
# Open bayyinah_ingest.ipynb and follow the instructions
# Set QDRANT_URL / QDRANT_API_KEY as environment secrets before running
```

### JSONL corpus format

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
  "text": "Ù†Øµ Ø§Ù„Ù…Ø§Ø¯Ø© Ø§Ù„ØªØ§Ø³Ø¹Ø© ÙˆØ§Ù„Ø³ØªÙŠÙ†...",
  "context_text": "Ù†Øµ Ø§Ù„Ø³ÙŠØ§Ù‚...",
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
2. In Render dashboard â†’ **New â†’ Blueprint** â†’ select this repo.
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
  "question": "Ù‡Ù„ ÙŠØ¬ÙˆØ² ÙØµÙ„ Ø§Ù„Ø¹Ø§Ù…Ù„ Ø¨Ø¯ÙˆÙ† Ø³Ø¨Ø¨ØŸ",
  "conversation_id": "optional-uuid",
  "stream": false
}
```

Response:
```json
{
  "conversation_id": "uuid",
  "answer": "Ù„Ø£ØŒ Ù…Ø´ ÙŠÙ†ÙØ¹ ØµØ§Ø­Ø¨ Ø§Ù„Ø´ØºÙ„ ÙŠØ·Ø±Ø¯Ùƒ Ù…Ù† ØºÙŠØ± Ø³Ø¨Ø¨ Ù‚Ø§Ù†ÙˆÙ†ÙŠ...",
  "citations": [
    {
      "chunk_id": "labor_12_2003_art69",
      "law_name": "Ù‚Ø§Ù†ÙˆÙ† Ø§Ù„Ø¹Ù…Ù„",
      "law_number": "12",
      "law_year": "2003",
      "article_number": "69",
      "text": "Ù†Øµ Ø§Ù„Ù…Ø§Ø¯Ø©...",
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
- `data: {"type":"token","content":"..."}` â€” streaming tokens
- `data: {"type":"done","final_answer":"...","citations":[...],"is_fallback":false}` â€” completion
- `data: {"type":"error","message":"..."}` â€” guardrail or server error

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
â”œâ”€â”€ backend/
â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”œâ”€â”€ main.py                   FastAPI app + middleware
â”‚   â”‚   â”œâ”€â”€ core/
â”‚   â”‚   â”‚   â”œâ”€â”€ config.py             Pydantic settings (all env vars)
â”‚   â”‚   â”‚   â””â”€â”€ logging.py            JSON structured logging
â”‚   â”‚   â”œâ”€â”€ services/
â”‚   â”‚   â”‚   â”œâ”€â”€ embedding_service.py  BAAI/bge-m3 (singleton)
â”‚   â”‚   â”‚   â”œâ”€â”€ retrieval_service.py  Qdrant + BM25 + RRF
â”‚   â”‚   â”‚   â”œâ”€â”€ reranker_service.py   BGE-reranker-v2-m3 (CPU)
â”‚   â”‚   â”‚   â”œâ”€â”€ bm25_service.py       Arabic BM25 tokenization
â”‚   â”‚   â”‚   â”œâ”€â”€ confidence_scorer.py  Retrieval confidence scoring
â”‚   â”‚   â”‚   â”œâ”€â”€ memory_service.py     Redis conversation memory
â”‚   â”‚   â”‚   â”œâ”€â”€ llm_service.py        Groq async client
â”‚   â”‚   â”‚   â””â”€â”€ web_search_service.py Tavily web search fallback
â”‚   â”‚   â”œâ”€â”€ graphs/
â”‚   â”‚   â”‚   â”œâ”€â”€ legal_assistant/      8-node LangGraph pipeline
â”‚   â”‚   â”‚   â””â”€â”€ contract_analysis/    LangGraph contract pipeline
â”‚   â”‚   â””â”€â”€ api/
â”‚   â”‚       â”œâ”€â”€ chat.py               POST /chat, POST /chat/stream
â”‚   â”‚       â”œâ”€â”€ contract.py           POST /contract-analysis
â”‚   â”‚       â””â”€â”€ system.py             GET /health, GET /metrics
â”‚   â”œâ”€â”€ tests/                        245 unit tests
â”‚   â”œâ”€â”€ requirements.txt
â”‚   â””â”€â”€ Dockerfile
â”œâ”€â”€ frontend/
â”‚   â”œâ”€â”€ src/
â”‚   â”‚   â”œâ”€â”€ app/                      Next.js App Router pages
â”‚   â”‚   â”œâ”€â”€ components/               Chat, contract, citation UI
â”‚   â”‚   â””â”€â”€ lib/                      API client, SSE streaming
â”‚   â”œâ”€â”€ package.json
â”‚   â””â”€â”€ Dockerfile
â”œâ”€â”€ docs/
â”‚   â”œâ”€â”€ PROJECT_EVOLUTION.md          Engineering decisions history
â”‚   â”œâ”€â”€ INTERVIEW_GUIDE.md            Technical explanations
â”‚   â””â”€â”€ DEPLOYMENT.md                 Full deployment guide
â”œâ”€â”€ scripts/
â”‚   â””â”€â”€ ingest.py                     Corpus ingestion CLI
â”œâ”€â”€ bayyinah_ingest.ipynb             GPU-accelerated Colab/Kaggle ingestion
â”œâ”€â”€ docker-compose.yml                Local development orchestration
â”œâ”€â”€ render.yaml                       Render Blueprint deployment
â”œâ”€â”€ .env.example                      Environment variable template
â””â”€â”€ .github/
    â””â”€â”€ workflows/
        â”œâ”€â”€ ci.yml                    Test + build on push/PR
        â””â”€â”€ deploy.yml                Trigger Render deploy on main
```

---

## Further Documentation

| Document | Description |
|----------|-------------|
| [`docs/PROJECT_EVOLUTION.md`](docs/PROJECT_EVOLUTION.md) | Complete engineering history â€” retrieval experiments, reranker optimization, model migration |
| [`docs/INTERVIEW_GUIDE.md`](docs/INTERVIEW_GUIDE.md) | Deep technical Q&A for interviews and Master's discussions |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Full deployment configuration and troubleshooting |

---

## License

MIT License â€” see [LICENSE](LICENSE)
