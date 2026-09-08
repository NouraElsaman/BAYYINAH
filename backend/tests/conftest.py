"""
conftest.py — shared fixtures for backend tests.
Patches are non-autouse so they don't break tests that don't need mocking.
The autouse fixtures that were causing module-not-found errors are replaced
with per-test opt-in patches or lazy-import guards.
"""
import sys
from unittest.mock import MagicMock, AsyncMock

# ── Stub out heavy/unavailable packages before any app code is imported ──────

# groq
groq_mock = MagicMock()
groq_mock.AsyncGroq = MagicMock()
sys.modules.setdefault("groq", groq_mock)

# FlagEmbedding
fe_mock = MagicMock()
sys.modules.setdefault("FlagEmbedding", fe_mock)

# qdrant_client  (already installed, but guard in case CI removes it)
try:
    import qdrant_client  # noqa: F401
except ImportError:
    sys.modules.setdefault("qdrant_client", MagicMock())
    sys.modules.setdefault("qdrant_client.http", MagicMock())
    sys.modules.setdefault("qdrant_client.http.models", MagicMock())

# prometheus_client
pc_mock = MagicMock()
pc_mock.Counter = MagicMock(return_value=MagicMock(labels=MagicMock(return_value=MagicMock())))
pc_mock.Histogram = MagicMock(return_value=MagicMock(time=MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=None), __exit__=MagicMock(return_value=False)))))
pc_mock.generate_latest = MagicMock(return_value=b"")
pc_mock.CONTENT_TYPE_LATEST = "text/plain"
sys.modules.setdefault("prometheus_client", pc_mock)
