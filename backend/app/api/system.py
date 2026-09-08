from __future__ import annotations

import time

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.core.config import get_settings
from app.services.retrieval_service import get_retrieval_service

router = APIRouter(tags=["system"])
settings = get_settings()

START_TIME = time.time()

REQUEST_COUNT = Counter("bayyinah_requests_total", "Total requests", ["endpoint", "status"])
CHAT_LATENCY = Histogram("bayyinah_chat_latency_seconds", "Chat endpoint latency")
CONTRACT_LATENCY = Histogram("bayyinah_contract_latency_seconds", "Contract analysis latency")
FAITHFULNESS_GAUGE = Histogram("bayyinah_faithfulness_score", "Faithfulness score distribution")
FALLBACK_COUNT = Counter("bayyinah_fallback_responses_total", "Number of fallback responses")


@router.get("/health")
async def health():
    qdrant_status = "ok"
    try:
        retriever = get_retrieval_service()
        retriever.client.get_collections()
    except Exception as exc:
        qdrant_status = f"error: {exc}"

    return {
        "status": "ok" if qdrant_status == "ok" else "degraded",
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "qdrant": qdrant_status,
        },
    }


@router.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
