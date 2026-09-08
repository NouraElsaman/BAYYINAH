"""
metrics.py
==========
Prometheus or other telemetry metric reporting stubs/helpers.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram
from app.observability.logger import get_logger

logger = get_logger("bayyinah.observability.metrics")

# Prometheus Metrics
RETRIEVAL_LATENCY_METRIC = Histogram("bayyinah_retrieval_latency_ms", "Retrieval latency in milliseconds")
WEB_SEARCH_LATENCY_METRIC = Histogram("bayyinah_web_search_latency_ms", "Web search latency in milliseconds")
GENERATION_LATENCY_METRIC = Histogram("bayyinah_generation_latency_ms", "Generation latency in milliseconds")
VERIFICATION_LATENCY_METRIC = Histogram("bayyinah_verification_latency_ms", "Verification latency in milliseconds")
TOTAL_LATENCY_METRIC = Histogram("bayyinah_total_latency_ms", "Total pipeline latency in milliseconds")
LLM_COST_METRIC = Counter("bayyinah_llm_cost_usd_total", "Estimated LLM cost in USD")
TOKEN_USAGE_METRIC = Counter("bayyinah_token_usage_total", "Total token usage", ["type"])

def record_prometheus_metrics(telemetry_data: Dict[str, Any]) -> None:
    """Safely updates Prometheus client metrics with telemetry values."""
    try:
        if telemetry_data.get("retrieval_ms") is not None:
            RETRIEVAL_LATENCY_METRIC.observe(telemetry_data["retrieval_ms"])
        if telemetry_data.get("web_search_ms") is not None:
            WEB_SEARCH_LATENCY_METRIC.observe(telemetry_data["web_search_ms"])
        if telemetry_data.get("generation_ms") is not None:
            GENERATION_LATENCY_METRIC.observe(telemetry_data["generation_ms"])
        if telemetry_data.get("verification_ms") is not None:
            VERIFICATION_LATENCY_METRIC.observe(telemetry_data["verification_ms"])
        if telemetry_data.get("total_ms") is not None:
            TOTAL_LATENCY_METRIC.observe(telemetry_data["total_ms"])
        if telemetry_data.get("estimated_llm_cost") is not None:
            LLM_COST_METRIC.inc(telemetry_data["estimated_llm_cost"])
            
        # Record tokens
        if telemetry_data.get("prompt_tokens") is not None:
            TOKEN_USAGE_METRIC.labels(type="prompt").inc(telemetry_data["prompt_tokens"])
        if telemetry_data.get("completion_tokens") is not None:
            TOKEN_USAGE_METRIC.labels(type="completion").inc(telemetry_data["completion_tokens"])
    except Exception as e:
        logger.warning(f"Error recording Prometheus metrics: {e}")
