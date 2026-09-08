"""
logger.py
=========
Observability logger for the BAYYINAH Legal AI backend.
Supports both JSON and standard console formatting depending on configuration.
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict, Optional
from app.core.config import get_settings
from app.core.logging import request_id_ctx

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        
        # Merge telemetry or extra fields if present
        extra = getattr(record, "extra_fields", None)
        if extra:
            # Avoid serializing dict with non-standard types by casting or ignoring
            payload.update(extra)
            
        return json.dumps(payload, ensure_ascii=False)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    
    # Configure it if it doesn't have handlers
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        
        try:
            settings = get_settings()
            use_json = settings.LOG_JSON
        except Exception:
            use_json = True
            
        if use_json:
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    "[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
                )
            )
        logger.addHandler(handler)
        logger.propagate = False
        
    return logger
