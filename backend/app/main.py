from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import chat, contract, system
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.middleware.request_context import RequestContextMiddleware

settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = get_logger("bayyinah.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application_startup", extra={"extra_fields": {"environment": settings.ENVIRONMENT}})

    # ---------------------------------------------------------------
    # Eager warm-up — load every heavy singleton before serving traffic
    # so the cold-start latency is paid once at boot, NOT on the first
    # user request.
    # ---------------------------------------------------------------
    try:
        from app.services.embedding_service import get_embedding_service
        embedder = get_embedding_service()
        embedder.warm_up()
        logger.info("startup_embedding_model_loaded",
                    extra={"extra_fields": {"backend": embedder.backend}})
    except Exception as exc:
        logger.warning("startup_embedding_warmup_failed", extra={"extra_fields": {"error": str(exc)}})

    try:
        from app.services.reranker_service import get_reranker_service
        reranker = get_reranker_service()
        reranker.warm_up()
        logger.info("startup_reranker_model_loaded",
                    extra={"extra_fields": {"backend": reranker._backend}})
    except Exception as exc:
        logger.warning("startup_reranker_warmup_failed", extra={"extra_fields": {"error": str(exc)}})

    try:
        from app.services.retrieval_service import get_retrieval_service
        get_retrieval_service()
        logger.info("startup_qdrant_client_ready")
    except Exception as exc:
        logger.warning("startup_qdrant_warmup_failed", extra={"extra_fields": {"error": str(exc)}})

    try:
        from app.services.memory_service import get_memory_service
        get_memory_service()
        logger.info("startup_memory_service_ready")
    except Exception as exc:
        logger.warning("startup_memory_warmup_failed", extra={"extra_fields": {"error": str(exc)}})

    try:
        from app.services.llm_service import get_llm_service
        get_llm_service()
        logger.info("startup_llm_service_ready")
    except Exception as exc:
        logger.warning("startup_llm_warmup_failed", extra={"extra_fields": {"error": str(exc)}})

    yield
    logger.info("application_shutdown")



app = FastAPI(
    title="BAYYINAH API",
    description="Egyptian Legal AI Assistant - RAG Chat & Contract Analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "details": exc.errors()},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": "http_error", "detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception")
    return JSONResponse(status_code=500, content={"error": "internal_server_error"})


app.include_router(system.router, prefix="")
app.include_router(chat.router, prefix="")
app.include_router(contract.router, prefix="")
