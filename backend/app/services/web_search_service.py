"""
web_search_service.py
======================
Async Web Search Service abstraction supporting multiple search providers (e.g. Tavily).
Provides robust retry mechanisms, timeout controls, result capping, url-based deduplication,
and graceful error handling (returns empty results on failures).

This service is independent of the LangGraph state graph.
"""
from __future__ import annotations

import abc
import asyncio
from typing import List, Optional

import httpx
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("bayyinah.services.web_search")

# ---------------------------------------------------------------------------
# Persistent HTTP client — shared across all web search calls.
# Creating AsyncClient per-request wastes TCP handshakes and connection slots.
# ---------------------------------------------------------------------------
_HTTP_CLIENT: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    """Return (or create) the module-level persistent AsyncClient."""
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30,
            ),
            timeout=httpx.Timeout(30.0),
        )
    return _HTTP_CLIENT


class SearchResult(BaseModel):
    """Normalized search result returned by any search provider."""
    title: str = Field(default="")
    url: str = Field(...)
    content: str = Field(default="")
    source: str = Field(default="")
    score: float = Field(default=1.0)


class BaseSearchProvider(abc.ABC):
    """Abstract base class for all web search providers."""
    @abc.abstractmethod
    async def search(
        self,
        query: str,
        max_results: int,
        timeout: float,
    ) -> List[SearchResult]:
        """Perform search query and return normalized search results."""
        pass


class TavilySearchProvider(BaseSearchProvider):
    """Search provider implementation for Tavily API."""
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.endpoint = "https://api.tavily.com/search"

    async def search(
        self,
        query: str,
        max_results: int,
        timeout: float,
    ) -> List[SearchResult]:
        if not self.api_key:
            logger.warning("tavily_api_key_missing_or_empty")
            return []

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }

        client = _get_http_client()
        response = await client.post(
            self.endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict):
            logger.error("tavily_response_malformed_not_dict")
            return []

        results = data.get("results")
        if not isinstance(results, list):
            logger.error("tavily_results_malformed_not_list")
            return []

        normalized: List[SearchResult] = []
        for r in results:
            if not isinstance(r, dict):
                continue
            url = r.get("url")
            if not url:
                continue  # A search result must have a URL

            # Safely extract score
            score_val = r.get("score")
            try:
                score = float(score_val) if score_val is not None else 1.0
            except (ValueError, TypeError):
                score = 1.0

            normalized.append(
                SearchResult(
                    title=str(r.get("title") or ""),
                    url=str(url),
                    content=str(r.get("content") or ""),
                    source="tavily",
                    score=score,
                )
            )

        return normalized



class DummySearchProvider(BaseSearchProvider):
    """Fallback search provider that returns nothing."""
    async def search(
        self,
        query: str,
        max_results: int,
        timeout: float,
    ) -> List[SearchResult]:
        return []


class WebSearchService:
    """Orchestrates web search queries against the active provider with retries,
    timeout handling, url deduplication, and fallback mechanisms."""
    def __init__(self, provider: Optional[BaseSearchProvider] = None):
        self.settings = get_settings()
        if provider:
            self.provider = provider
        else:
            self.provider = self._init_provider()

    def _init_provider(self) -> BaseSearchProvider:
        provider_name = self.settings.WEB_SEARCH_PROVIDER.lower()
        if provider_name == "tavily":
            return TavilySearchProvider(api_key=self.settings.TAVILY_API_KEY)
        else:
            logger.warning(
                "unknown_web_search_provider_configured",
                extra={"extra_fields": {"provider": provider_name}},
            )
            return DummySearchProvider()

    async def search(self, query: str) -> List[SearchResult]:
        if not self.settings.WEB_SEARCH_ENABLED:
            logger.info("web_search_disabled_in_settings")
            return []

        clean_query = query.strip()
        if not clean_query:
            return []

        max_results = self.settings.WEB_SEARCH_MAX_RESULTS
        timeout = self.settings.WEB_SEARCH_TIMEOUT_S
        max_retries = self.settings.WEB_SEARCH_MAX_RETRIES

        attempt = 0
        while attempt <= max_retries:
            try:
                results = await self.provider.search(
                    clean_query,
                    max_results=max_results,
                    timeout=timeout,
                )

                # Deduplicate by URL (preserving order)
                seen_urls = set()
                deduped: List[SearchResult] = []
                for r in results:
                    if r.url not in seen_urls:
                        seen_urls.add(r.url)
                        deduped.append(r)

                return deduped[:max_results]

            except (httpx.HTTPError, asyncio.TimeoutError) as e:
                attempt += 1
                logger.warning(
                    "web_search_attempt_failed",
                    extra={
                        "extra_fields": {
                            "attempt": attempt,
                            "max_retries": max_retries,
                            "error": str(e),
                        }
                    },
                )
                if attempt > max_retries:
                    logger.error(
                        "web_search_all_attempts_failed",
                        extra={"extra_fields": {"query": clean_query, "error": str(e)}},
                    )
                    break
                # Backoff before retrying
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))

            except Exception as e:
                # Catch mapping or other non-recoverable errors
                logger.error(
                    "web_search_unrecoverable_error",
                    extra={"extra_fields": {"query": clean_query, "error": str(e)}},
                )
                break

        return []
