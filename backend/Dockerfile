FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/data/hf_cache

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to the latest version for modern resolver behaviour.
RUN pip install --upgrade pip

# Pre-install the PyTorch CPU build explicitly before the main requirements.
# Without this, pip resolves torch from PyPI (CUDA build, ~2.8 GB) when
# sentence-transformers or FlagEmbedding list 'torch' as a dependency.
# With torch-cpu already present, the subsequent -r requirements.txt install
# sees it as satisfied and does not replace it.
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.13.0+cpu

# Install the rest of the application dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Create data directories and non-root user.
# /data/uploads  - contract file uploads (persistent disk mount in production)
# /data/hf_cache - HuggingFace model cache (persistent disk mount in production)
RUN mkdir -p /data/uploads /data/hf_cache \
    && useradd --system --create-home --uid 1001 bayyinah \
    && chown -R bayyinah:bayyinah /app /data

USER bayyinah

EXPOSE 8000

# Healthcheck: start-period is 120s to allow BGE-M3 + reranker to load from
# local disk cache (~30-60s) or download on first deploy (~5-10 min on fast network).
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 1 worker: BGE-M3 (~9GB disk / ~1.5GB inference RAM) + reranker (~2.3GB disk / ~400MB RAM)
# are loaded per-process. Multiple workers would duplicate this RAM usage and OOM on
# Render Standard (2GB). Timeout 180s covers contract analysis workloads.
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "1", "-b", "0.0.0.0:8000", "--timeout", "180"]