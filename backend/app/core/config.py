from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "BAYYINAH"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = Field(default="INFO")

    # CORS
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Qdrant
    QDRANT_URL: str = Field(default="http://localhost:6333")
    QDRANT_API_KEY: str | None = Field(default=None)
    QDRANT_COLLECTION: str = Field(default="egypt_legal_rag")

    # Embeddings
    EMBEDDING_MODEL: str = Field(default="BAAI/bge-m3")
    EMBEDDING_DEVICE: str = Field(default="cpu")
    EMBEDDING_DIM: int = Field(default=1024)

    # Groq
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="openai/gpt-oss-120b")  # llama-3.3-70b-versatile decommissioned 2026-08-16
    GROQ_TEMPERATURE: float = Field(default=0.1)
    GROQ_MAX_TOKENS: int = Field(default=2048)

    # OpenAI (Fallback)
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")

    # Retrieval
    RETRIEVAL_TOP_K: int = Field(default=8)
    RETRIEVAL_SCORE_THRESHOLD: float = Field(default=0.30)  # Lowered from 0.45: Arabic BGE-M3 scores are lower; 0.45 was filtering out relevant chunks
    RERANK_TOP_N: int = Field(default=5)
    # Relevance guard: if top reranker score < threshold → treat as retrieval_empty.
    # Measured cross-encoder scores: labor-relevant=0.96-0.99, family-relevant=0.36,
    # corpus-miss=0.77. Single global threshold unsafe — family law scores ~0.36
    # (cross-encoder miscalibrated per-domain). Conservative 0.30 only blocks
    # completely stumped results. Corpus-miss handled by prompt-based guard.
    # Set to 0 to disable entirely.
    RERANK_RELEVANCE_THRESHOLD: float = Field(default=0.30)



    # Guardrails
    HALLUCINATION_MIN_OVERLAP: float = Field(default=0.10)  # Lowered from 0.30: Arabic LLM outputs paraphrase legal text; 30% lexical overlap was unachievable for accurate grounded answers
    MAX_QUESTION_LENGTH: int = Field(default=1000)
    MAX_FILE_SIZE_MB: int = Field(default=15)

    # Redis (chat history / cache)
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Conversational Memory
    MEMORY_MAX_TURNS: int = Field(default=5)
    MEMORY_TTL_SECONDS: int = Field(default=86400)  # 24 hours

    # Query Expansion (HyDE)
    QUERY_EXPANSION_ENABLED: bool = Field(default=True)
    QUERY_EXPANSION_TIMEOUT_S: float = Field(default=3.0)

    # Retrieval Confidence Scorer weights (must sum to 1.0)
    CONFIDENCE_WEIGHT_DENSE: float = Field(default=0.4)
    CONFIDENCE_WEIGHT_RECALL: float = Field(default=0.3)
    CONFIDENCE_WEIGHT_DOMAIN: float = Field(default=0.2)
    CONFIDENCE_WEIGHT_RERANKER: float = Field(default=0.1)
    # Normalisation cap: number of docs considered "full recall coverage"
    CONFIDENCE_RECALL_CAP: int = Field(default=5)
    # Bonus applied when the query domain matches the retrieved documents' domain
    CONFIDENCE_DOMAIN_BONUS: float = Field(default=1.0)
    # Minimum retrieval confidence required to proceed with generation.
    # Requests that score below this threshold are treated as insufficient
    # retrieval and receive the FALLBACK_NO_CONTEXT response.
    CONFIDENCE_FALLBACK_THRESHOLD: float = Field(default=0.35)

    # Citation Agent
    # Maximum total whitespace-split tokens allowed across all citation texts
    CITATION_MAX_TOKENS: int = Field(default=3000)
    # Maximum whitespace-split tokens allowed per individual citation text
    CITATION_MAX_TEXT_TOKENS: int = Field(default=400)

    # Web Search Configuration
    WEB_SEARCH_ENABLED: bool = Field(default=False)
    WEB_SEARCH_PROVIDER: str = Field(default="tavily")
    WEB_SEARCH_TIMEOUT_S: float = Field(default=8.0)
    WEB_SEARCH_MAX_RESULTS: int = Field(default=5)
    WEB_SEARCH_MAX_RETRIES: int = Field(default=2)
    TAVILY_API_KEY: str | None = Field(default=None)

    # JWT / Auth
    SECRET_KEY: str = Field(default="change-me-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24)

    # File storage
    UPLOAD_DIR: str = Field(default="/data/uploads")

    # Observability
    OBSERVABILITY_ENABLED: bool = Field(default=True)
    LOG_JSON: bool = Field(default=True)
    LANGSMITH_ENABLED: bool = Field(default=False)
    LANGSMITH_API_KEY: str | None = Field(default=None)
    OTEL_ENABLED: bool = Field(default=False)
    TOKEN_COST_INPUT: float = Field(default=0.0015)  # Cost per 1000 prompt tokens
    TOKEN_COST_OUTPUT: float = Field(default=0.002)  # Cost per 1000 completion tokens



@lru_cache
def get_settings() -> Settings:
    return Settings()