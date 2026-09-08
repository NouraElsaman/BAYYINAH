"""
memory_service.py
-----------------
Redis-backed conversation memory for multi-turn legal AI chat.

Storage layout in Redis:
  Key:   memory:{conversation_id}
  Type:  Redis List (newest turn at head via LPUSH)
  Value: JSON-encoded turn dicts: {role, content, ts}
  TTL:   MEMORY_TTL_SECONDS (default 86400 = 24h)

Fallback:
  When Redis is unavailable, an in-process dict is used.
  Fallback state is per-worker and does NOT survive restarts.
  Degraded mode is logged once at WARNING level.
"""
from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from functools import lru_cache
from typing import Dict, List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("bayyinah.memory")
settings = get_settings()

# ---------------------------------------------------------------------------
# Type alias
# ---------------------------------------------------------------------------
Turn = Dict[str, str]  # {role: "user"|"assistant", content: str, ts: str}


# ---------------------------------------------------------------------------
# MemoryService
# ---------------------------------------------------------------------------

class MemoryService:
    """Thread-safe conversation history store backed by Redis.

    Falls back to an in-process dict if Redis is unavailable.
    All public methods are synchronous; callers can wrap with
    ``asyncio.to_thread`` when called from async context.
    """

    def __init__(self, redis_url: str, ttl: int, max_turns: int) -> None:
        self._ttl = ttl
        self._max_turns = max_turns
        self._redis: Optional[object] = None      # redis.Redis instance
        self._available = False
        self._degraded_logged = False
        self._lock = threading.Lock()

        # In-process fallback: {conversation_id: [turn, ...]}
        self._local: Dict[str, List[Turn]] = defaultdict(list)

        self._connect(redis_url)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _connect(self, redis_url: str) -> None:
        try:
            import redis  # type: ignore[import]

            client = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            client.ping()
            self._redis = client
            self._available = True
            logger.info("memory_redis_connected", extra={"extra_fields": {"url": redis_url}})
        except Exception as exc:
            logger.warning(
                "memory_redis_unavailable_using_local_fallback",
                extra={"extra_fields": {"error": str(exc)}},
            )
            self._available = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_turn(self, conversation_id: str, role: str, content: str) -> None:
        """Append a turn to the conversation history.

        Args:
            conversation_id: Unique conversation identifier.
            role:            "user" or "assistant".
            content:         Raw text of the turn.
        """
        turn: Turn = {
            "role": role,
            "content": content,
            "ts": str(int(time.time())),
        }
        if self._available and self._redis is not None:
            try:
                key = self._key(conversation_id)
                self._redis.lpush(key, json.dumps(turn, ensure_ascii=False))
                # Keep only the newest max_turns entries
                self._redis.ltrim(key, 0, self._max_turns * 2 - 1)
                self._redis.expire(key, self._ttl)
                return
            except Exception as exc:
                self._log_degraded(exc)

        # Fallback
        with self._lock:
            turns = self._local[conversation_id]
            turns.insert(0, turn)
            self._local[conversation_id] = turns[: self._max_turns * 2]

    def get_history(
        self, conversation_id: str, max_turns: Optional[int] = None
    ) -> List[Turn]:
        """Return the last *max_turns* turns in chronological order.

        Args:
            conversation_id: Unique conversation identifier.
            max_turns:       How many turns to return (defaults to
                             ``MEMORY_MAX_TURNS`` setting).

        Returns:
            List of turn dicts sorted oldest-first, e.g.:
            [{"role": "user", "content": "…", "ts": "…"}, …]
        """
        limit = max_turns if max_turns is not None else self._max_turns

        if self._available and self._redis is not None:
            try:
                key = self._key(conversation_id)
                raw = self._redis.lrange(key, 0, limit * 2 - 1)
                turns = [json.loads(r) for r in raw]
                # lrange returns newest-first; reverse to chronological
                return list(reversed(turns))[-limit:]
            except Exception as exc:
                self._log_degraded(exc)

        # Fallback
        with self._lock:
            turns = list(self._local.get(conversation_id, []))
        # local list is also newest-first
        return list(reversed(turns))[-limit:]

    def clear_history(self, conversation_id: str) -> None:
        """Delete all history for a conversation.

        Non-fatal: errors are logged and swallowed.
        """
        if self._available and self._redis is not None:
            try:
                self._redis.delete(self._key(conversation_id))
                return
            except Exception as exc:
                self._log_degraded(exc)

        with self._lock:
            self._local.pop(conversation_id, None)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _key(conversation_id: str) -> str:
        return f"memory:{conversation_id}"

    def _log_degraded(self, exc: Exception) -> None:
        if not self._degraded_logged:
            logger.warning(
                "memory_redis_error_falling_back_to_local",
                extra={"extra_fields": {"error": str(exc)}},
            )
            self._degraded_logged = True
        self._available = False


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_memory_service() -> MemoryService:
    """Return the process-wide MemoryService singleton."""
    return MemoryService(
        redis_url=settings.REDIS_URL,
        ttl=settings.MEMORY_TTL_SECONDS,
        max_turns=settings.MEMORY_MAX_TURNS,
    )
