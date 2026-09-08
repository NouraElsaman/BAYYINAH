"""
test_observability.py
=====================
Unit tests for the BAYYINAH Production Observability & Telemetry Layer.
"""
from __future__ import annotations

import json
import logging
import time
import asyncio
from unittest.mock import MagicMock, patch
import pytest

from app.core.config import Settings
from app.observability.telemetry import (
    init_telemetry,
    get_telemetry_data,
    finalize_telemetry,
    start_timer,
    stop_timer,
    record_metric,
    record_event,
    estimate_cost,
    trace_node,
    is_enabled,
)
from app.observability.logger import get_logger, JSONFormatter


def test_is_enabled_default():
    assert is_enabled() is True


def test_timer_accuracy():
    start = start_timer()
    time.sleep(0.01)  # sleep 10ms
    duration = stop_timer(start)
    assert duration >= 9.0  # allow some OS schedule variance
    assert duration <= 100.0


def test_cost_estimation():
    # settings input/output cost: 0.0015 and 0.002 per 1000 tokens
    # 2000 prompt, 1000 completion
    cost = estimate_cost(2000, 1000)
    # (2000 * 0.0015 / 1000) + (1000 * 0.002 / 1000) = 0.003 + 0.002 = 0.005
    assert cost == 0.005
    
    # Degenerate input handling
    assert estimate_cost(-10, 0) == 0.0


def test_init_and_get_telemetry():
    init_telemetry(request_id="req-1", session_id="sess-1", conversation_id="conv-1")
    data = get_telemetry_data()
    assert data is not None
    assert data["request_id"] == "req-1"
    assert data["session_id"] == "sess-1"
    assert data["conversation_id"] == "conv-1"
    assert data["fallback_triggered"] is False
    assert data["unsafe_detection"] is False


def test_metrics_and_token_aggregation():
    init_telemetry()
    record_metric("prompt_tokens", 500)
    record_metric("completion_tokens", 250)
    record_metric("retrieval_confidence", 0.75)
    
    data = get_telemetry_data()
    assert data["prompt_tokens"] == 500
    assert data["completion_tokens"] == 250
    assert data["total_tokens"] == 750
    assert data["retrieval_confidence"] == 0.75
    assert data["estimated_llm_cost"] > 0.0


def test_event_recording():
    init_telemetry()
    record_event("test_event", {"some": "detail"})
    
    data = get_telemetry_data()
    assert len(data["events"]) == 1
    assert data["events"][0]["name"] == "test_event"
    assert data["events"][0]["details"] == {"some": "detail"}


def test_finalize_telemetry():
    init_telemetry()
    time.sleep(0.01)
    report = finalize_telemetry()
    assert report is not None
    assert report["total_ms"] > 0.0


@patch("app.observability.telemetry.is_enabled", return_value=False)
def test_telemetry_disabled(mock_enabled):
    init_telemetry(request_id="req-disabled")
    record_metric("prompt_tokens", 100)
    record_event("some_event")
    
    # Context should be initialized as empty dict if disabled,
    # or no recording should have updated properties.
    data = get_telemetry_data()
    if data:
        assert data.get("prompt_tokens") is None
    assert finalize_telemetry() is None


def test_exception_safety_in_telemetry_functions():
    # None of these should throw even if context is uninitialized or invalid inputs passed
    from contextvars import ContextVar
    from app.observability.telemetry import _telemetry_ctx
    
    _telemetry_ctx.set(None)
    record_metric("test", 123)
    record_event("test_event")
    
    # Cost estimator with string input
    cost = estimate_cost("invalid", 10)  # type: ignore
    assert cost == 0.0


def test_logger_serialization():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test-logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test log message",
        args=(),
        exc_info=None,
    )
    record.extra_fields = {"extra_key": "extra_val"}
    formatted_str = formatter.format(record)
    parsed = json.loads(formatted_str)
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test log message"
    assert parsed["extra_key"] == "extra_val"


def test_sync_trace_node_decorator():
    init_telemetry()
    
    @trace_node("test_sync_node")
    def my_node(state):
        return {**state, "retrieval_confidence": 0.9, "is_fallback": True}
        
    res = my_node({"test": "value"})
    assert res["test"] == "value"
    
    data = get_telemetry_data()
    assert "test_sync_node" in data["node_timings"]
    assert data["retrieval_confidence"] == 0.9
    assert data["fallback_triggered"] is True


@pytest.mark.anyio
async def test_async_trace_node_decorator():
    init_telemetry()
    
    @trace_node("test_async_node")
    async def my_async_node(state):
        await asyncio.sleep(0.01)
        return {**state, "context_tokens": 150}
        
    res = await my_async_node({})
    assert res == {"context_tokens": 150}
    
    data = get_telemetry_data()
    assert "test_async_node" in data["node_timings"]
    assert data["context_tokens"] == 150


def test_missing_metadata_defaults():
    init_telemetry(request_id=None, session_id=None, conversation_id=None)
    data = get_telemetry_data()
    assert data["request_id"] is not None
    assert data["session_id"] is not None
    assert data["conversation_id"] == ""
