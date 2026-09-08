"""
telemetry.py
============
Telemetry and tracking layer for the BAYYINAH Legal AI backend.
Provides wrappers, timers, metric tracking, and event recording.
"""
from __future__ import annotations

import time
import uuid
import asyncio
from functools import wraps
from contextvars import ContextVar
from typing import Dict, Any, Optional, Callable, TypeVar, Union
from app.core.config import get_settings
from app.observability.logger import get_logger

logger = get_logger("bayyinah.observability.telemetry")

# Context for storing active request telemetry
_telemetry_ctx: ContextVar[Optional[Dict[str, Any]]] = ContextVar("telemetry_ctx", default=None)

def is_enabled() -> bool:
    try:
        settings = get_settings()
        return settings.OBSERVABILITY_ENABLED
    except Exception:
        return True

def init_telemetry(
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Initialize telemetry context for the current request."""
    if not is_enabled():
        return {}
        
    ctx = {
        "request_id": request_id or str(uuid.uuid4()),
        "session_id": session_id or str(uuid.uuid4()),
        "conversation_id": conversation_id or "",
        "retrieval_ms": None,
        "web_search_ms": None,
        "generation_ms": None,
        "verification_ms": None,
        "total_ms": None,
        "retrieval_confidence": None,
        "retrieval_source": "local",
        "num_citations": None,
        "context_tokens": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "estimated_llm_cost": 0.0,
        "fallback_triggered": False,
        "web_fallback_triggered": False,
        "unsafe_detection": False,
        "metrics": {},
        "events": [],
        "node_timings": {},
        "_start_time": time.perf_counter(),
    }
    _telemetry_ctx.set(ctx)
    return ctx

def get_telemetry_data() -> Optional[Dict[str, Any]]:
    """Retrieve current telemetry context."""
    return _telemetry_ctx.get()

def start_timer() -> float:
    """Start timing and return high-precision reference time."""
    return time.perf_counter()

def stop_timer(start_time: float) -> float:
    """Stop timing and return duration in milliseconds."""
    duration = (time.perf_counter() - start_time) * 1000.0
    return round(duration, 2)

def record_metric(name: str, value: Any) -> None:
    """Record a metric inside active telemetry context."""
    if not is_enabled():
        return
    ctx = _telemetry_ctx.get()
    if ctx is not None:
        ctx["metrics"][name] = value
        # Map specific metrics directly to telemetry properties
        if name in ctx:
            ctx[name] = value
            
        # Keep total tokens updated
        if name in ("prompt_tokens", "completion_tokens"):
            prompt = ctx.get("prompt_tokens") or 0
            completion = ctx.get("completion_tokens") or 0
            ctx["total_tokens"] = prompt + completion
            ctx["estimated_llm_cost"] = estimate_cost(prompt, completion)

def record_event(name: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Record an event with details inside active telemetry context."""
    if not is_enabled():
        return
    ctx = _telemetry_ctx.get()
    if ctx is not None:
        ctx["events"].append({
            "name": name,
            "timestamp": time.time(),
            "details": details or {},
        })

def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate LLM call cost based on token weights in config."""
    try:
        settings = get_settings()
        p = max(0, prompt_tokens)
        c = max(0, completion_tokens)
        cost = (p * settings.TOKEN_COST_INPUT / 1000.0) + (
            c * settings.TOKEN_COST_OUTPUT / 1000.0
        )
        return round(cost, 6)
    except Exception:
        return 0.0

def finalize_telemetry() -> Optional[Dict[str, Any]]:
    """Complete active telemetry context, export metrics and log report."""
    if not is_enabled():
        return None
    ctx = _telemetry_ctx.get()
    if ctx is not None:
        if "_start_time" in ctx:
            ctx["total_ms"] = stop_timer(ctx["_start_time"])
            
        # Auto calculate total tokens and cost
        prompt = ctx.get("prompt_tokens") or 0
        completion = ctx.get("completion_tokens") or 0
        ctx["total_tokens"] = prompt + completion
        ctx["estimated_llm_cost"] = estimate_cost(prompt, completion)
        
        # Export stubs
        _export_to_external_services(ctx)
        
        # Record to Prometheus
        try:
            from app.observability.metrics import record_prometheus_metrics
            record_prometheus_metrics(ctx)
        except Exception as e:
            logger.warning(f"Failed to record Prometheus metrics: {e}")
            
        # Log JSON or Console report
        logger.info("telemetry_request_completed", extra={"extra_fields": {"telemetry": ctx}})
        return ctx
    return None

def _export_to_external_services(ctx: Dict[str, Any]) -> None:
    try:
        settings = get_settings()
        if settings.LANGSMITH_ENABLED:
            logger.info("LangSmith export triggered (stub)")
        if settings.OTEL_ENABLED:
            logger.info("OpenTelemetry export triggered (stub)")
    except Exception as e:
        logger.warning(f"External telemetry export failed: {e}")

# Decorator to trace nodes
F = TypeVar("F", bound=Callable[..., Any])

def trace_node(node_name: str) -> Callable[[F], F]:
    """Decorator to trace latency and collect details from graph nodes."""
    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                if not is_enabled():
                    return await func(*args, **kwargs)
                start = start_timer()
                try:
                    result = await func(*args, **kwargs)
                    duration = stop_timer(start)
                    _record_node_details(node_name, duration, result)
                    return result
                except Exception as e:
                    duration = stop_timer(start)
                    _record_node_details(node_name, duration, None, error=e)
                    raise
            return async_wrapper  # type: ignore
        else:
            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                if not is_enabled():
                    return func(*args, **kwargs)
                start = start_timer()
                try:
                    result = func(*args, **kwargs)
                    duration = stop_timer(start)
                    _record_node_details(node_name, duration, result)
                    return result
                except Exception as e:
                    duration = stop_timer(start)
                    _record_node_details(node_name, duration, None, error=e)
                    raise
            return sync_wrapper  # type: ignore
    return decorator

def _record_node_details(
    node_name: str,
    duration: float,
    state: Any,
    error: Optional[Exception] = None,
) -> None:
    """Helper to write node metrics/events into the active context."""
    if not is_enabled():
        return
    ctx = _telemetry_ctx.get()
    if ctx is None:
        return
        
    ctx["node_timings"][node_name] = duration
    
    # Map node duration to specific telemetry latency fields
    latency_map = {
        "retrieve": "retrieval_ms",
        "web_search": "web_search_ms",
        "generate_answer": "generation_ms",
        "verify": "verification_ms",
    }
    if node_name in latency_map:
        ctx[latency_map[node_name]] = duration
        
    if error:
        record_event(f"node_{node_name}_failed", {"error": str(error)})
        return
        
    # Extract state parameters if state is a dict
    if isinstance(state, dict):
        if "retrieval_confidence" in state:
            record_metric("retrieval_confidence", state["retrieval_confidence"])
        if "retrieval_source" in state:
            record_metric("retrieval_source", state["retrieval_source"])
        if "citations" in state:
            record_metric("num_citations", len(state["citations"]))
        if "context_tokens" in state:
            record_metric("context_tokens", state["context_tokens"])
        if "is_fallback" in state:
            if state["is_fallback"]:
                ctx["fallback_triggered"] = True
        if "is_unsafe" in state:
            if state["is_unsafe"]:
                ctx["unsafe_detection"] = True
        if "web_results" in state:
            if state.get("retrieval_source") == "web" or len(state.get("web_results") or []) > 0:
                ctx["web_fallback_triggered"] = True
