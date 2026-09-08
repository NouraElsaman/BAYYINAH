"""
observability
=============
Observability, logging, and telemetry package for the BAYYINAH Legal AI backend.
"""
from __future__ import annotations

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
)
from app.observability.logger import get_logger

__all__ = [
    "init_telemetry",
    "get_telemetry_data",
    "finalize_telemetry",
    "start_timer",
    "stop_timer",
    "record_metric",
    "record_event",
    "estimate_cost",
    "trace_node",
    "get_logger",
]
