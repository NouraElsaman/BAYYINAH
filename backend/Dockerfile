FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Point HuggingFace model downloads to /data/hf_cache.
    # On Render this path is on the persistent disk so models survive restarts.
    # On Docker Compose, mount a named volume here for the same effect.
    # If HF_HOME is overridden by the caller (e.g. local dev), that takes precedence.
    HF_HOME=/data/hf_cache

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster installs
RUN pip install --no-cache-dir uv

# Install Python dependencies
COPY requirements.txt .
RUN uv pip install --system --no-cache-dir \
    --index-url https://pypi.org/simple \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

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