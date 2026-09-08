"""
test_web_search.py
===================
Comprehensive unit tests for the WebSearchService and TavilySearchProvider.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.web_search_service import (
    BaseSearchProvider,
    SearchResult,
    TavilySearchProvider,
    WebSearchService,
)


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.WEB_SEARCH_ENABLED = True
    s.WEB_SEARCH_PROVIDER = "tavily"
    s.WEB_SEARCH_TIMEOUT_S = 2.0
    s.WEB_SEARCH_MAX_RESULTS = 5
    s.WEB_SEARCH_MAX_RETRIES = 2
    s.TAVILY_API_KEY = "dummy-key"
    return s


# ===========================================================================
# 1. Base provider interface & Dummy Provider test
# ===========================================================================

def test_search_result_schema():
    res = SearchResult(
        title="Test Page",
        url="http://example.com",
        content="Description",
        source="tavily",
        score=0.95,
    )
    assert res.title == "Test Page"
    assert res.url == "http://example.com"
    assert res.score == 0.95


# ===========================================================================
# 2. Disabled feature test
# ===========================================================================

@pytest.mark.asyncio
async def test_search_disabled(mock_settings):
    mock_settings.WEB_SEARCH_ENABLED = False
    
    with patch("app.services.web_search_service.get_settings", return_value=mock_settings):
        service = WebSearchService()
        results = await service.search("قانون العمل")
        
    assert results == []


# ===========================================================================
# 3. WebSearchService deduplication & max_results capping
# ===========================================================================

@pytest.mark.asyncio
async def test_deduplication_and_max_results(mock_settings):
    # Setup provider returning duplicate URLs and exceeding max results
    provider = MagicMock(spec=BaseSearchProvider)
    provider.search = AsyncMock(return_value=[
        SearchResult(url="http://site1.com", title="Page 1", score=0.9),
        SearchResult(url="http://site2.com", title="Page 2", score=0.8),
        SearchResult(url="http://site1.com", title="Page 1 Copy", score=0.7),  # Duplicate URL
        SearchResult(url="http://site3.com", title="Page 3", score=0.6),
        SearchResult(url="http://site4.com", title="Page 4", score=0.5),
        SearchResult(url="http://site5.com", title="Page 5", score=0.4),
        SearchResult(url="http://site6.com", title="Page 6", score=0.3),  # Extra result
    ])

    mock_settings.WEB_SEARCH_MAX_RESULTS = 3

    with patch("app.services.web_search_service.get_settings", return_value=mock_settings):
        service = WebSearchService(provider=provider)
        results = await service.search("قانون الإيجار")

    # Should be capped at 3, duplicate should be removed, preserving original order
    assert len(results) == 3
    assert results[0].url == "http://site1.com"
    assert results[1].url == "http://site2.com"
    # http://site1.com (dup) skipped
    assert results[2].url == "http://site3.com"


# ===========================================================================
# 4. Tavily provider - successful response mapping
# ===========================================================================

@pytest.mark.asyncio
async def test_tavily_provider_success():
    provider = TavilySearchProvider(api_key="tvly-xxx")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "title": "قانون العمل المصري",
                "url": "https://egypt.gov/labor",
                "content": "شرح مواد قانون العمل الموحد",
                "score": 0.98,
            }
        ]
    }

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        results = await provider.search("قانون العمل", max_results=5, timeout=5.0)

    mock_post.assert_called_once()
    assert len(results) == 1
    assert results[0].title == "قانون العمل المصري"
    assert results[0].url == "https://egypt.gov/labor"
    assert results[0].score == 0.98
    assert results[0].source == "tavily"


# ===========================================================================
# 5. Malformed provider responses
# ===========================================================================

@pytest.mark.asyncio
async def test_tavily_malformed_response_not_dict():
    provider = TavilySearchProvider(api_key="tvly-xxx")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = ["not", "a", "dict"]  # Malformed

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        results = await provider.search("قانون", max_results=5, timeout=5.0)

    assert results == []


@pytest.mark.asyncio
async def test_tavily_malformed_response_no_results():
    provider = TavilySearchProvider(api_key="tvly-xxx")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}  # Missing 'results'

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        results = await provider.search("قانون", max_results=5, timeout=5.0)

    assert results == []


@pytest.mark.asyncio
async def test_tavily_missing_url_skipped():
    provider = TavilySearchProvider(api_key="tvly-xxx")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"title": "Result with no url"},  # Invalid
            {"title": "Valid result", "url": "https://ok.com", "score": "not-a-float"},  # Valid with unparseable score
        ]
    }

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        results = await provider.search("قانون", max_results=5, timeout=5.0)

    assert len(results) == 1
    assert results[0].url == "https://ok.com"
    assert results[0].score == 1.0  # Default fallback score


# ===========================================================================
# 6. Retry behavior on transient errors
# ===========================================================================

@pytest.mark.asyncio
async def test_service_retries_on_transient_http_error(mock_settings):
    provider = MagicMock(spec=BaseSearchProvider)
    # Fail first, then succeed on retry
    provider.search = AsyncMock(side_effect=[
        httpx.ConnectError("Connection timed out"),
        [SearchResult(url="https:// egypt.gov", title="Succeeded on retry")],
    ])

    with patch("app.services.web_search_service.get_settings", return_value=mock_settings), \
         patch("asyncio.sleep", return_value=None) as mock_sleep:  # Speed up tests
        
        service = WebSearchService(provider=provider)
        results = await service.search("قانون العمل")

    assert len(results) == 1
    assert results[0].title == "Succeeded on retry"
    assert provider.search.call_count == 2
    mock_sleep.assert_called_once_with(0.5)


@pytest.mark.asyncio
async def test_service_stops_retrying_after_limit(mock_settings):
    provider = MagicMock(spec=BaseSearchProvider)
    # Fail persistently
    provider.search = AsyncMock(side_effect=httpx.HTTPStatusError(
        "Internal Server Error",
        request=MagicMock(),
        response=MagicMock(status_code=500),
    ))

    # max_retries = 2 -> total attempts = 3
    with patch("app.services.web_search_service.get_settings", return_value=mock_settings), \
         patch("asyncio.sleep", return_value=None):
        
        service = WebSearchService(provider=provider)
        results = await service.search("قانون")

    assert results == []
    assert provider.search.call_count == 3


# ===========================================================================
# 7. Unrecoverable errors (stops immediately)
# ===========================================================================

@pytest.mark.asyncio
async def test_service_unrecoverable_error_no_retry(mock_settings):
    provider = MagicMock(spec=BaseSearchProvider)
    provider.search = AsyncMock(side_effect=ValueError("Invalid parameter passed"))

    with patch("app.services.web_search_service.get_settings", return_value=mock_settings), \
         patch("asyncio.sleep", return_value=None) as mock_sleep:
        
        service = WebSearchService(provider=provider)
        results = await service.search("قانون")

    assert results == []
    assert provider.search.call_count == 1
    mock_sleep.assert_not_called()
