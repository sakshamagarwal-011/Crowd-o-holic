from __future__ import annotations

"""Server-side client for TinyFish Search and Fetch."""

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"


class TinyFishUnavailableError(RuntimeError):
    """Raised when live intelligence has not been configured."""


class TinyFishRequestError(RuntimeError):
    """Raised when TinyFish cannot complete an upstream request."""


def _headers() -> dict[str, str]:
    if not settings.tinyfish_api_key:
        raise TinyFishUnavailableError("TinyFish is not configured on this server.")
    return {"X-API-Key": settings.tinyfish_api_key}


async def search_public_sources(query: str, *, max_results: int | None = None) -> list[dict[str, str]]:
    """Return a deliberately small, display-safe subset of TinyFish results."""
    try:
        async with httpx.AsyncClient(timeout=settings.tinyfish_timeout) as client:
            response = await client.get(SEARCH_URL, params={"query": query}, headers=_headers())
            response.raise_for_status()
    except TinyFishUnavailableError:
        raise
    except httpx.HTTPStatusError as exc:
        log.warning("TinyFish search failed with status %s", exc.response.status_code)
        raise TinyFishRequestError("Live source search is temporarily unavailable.") from exc
    except httpx.HTTPError as exc:
        log.warning("TinyFish search request failed: %s", type(exc).__name__)
        raise TinyFishRequestError("Live source search is temporarily unavailable.") from exc

    payload: dict[str, Any] = response.json()
    limit = min(max_results or settings.tinyfish_max_results, settings.tinyfish_max_results)
    results: list[dict[str, str]] = []
    for item in payload.get("results", [])[:limit]:
        url = item.get("url")
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            continue
        results.append({
            "title": str(item.get("title") or url),
            "url": url,
            "snippet": str(item.get("snippet") or ""),
            "site_name": str(item.get("site_name") or ""),
        })
    return results


async def fetch_public_sources(urls: list[str]) -> list[dict[str, str]]:
    """Fetch clean Markdown from up to three public URLs selected by an operator."""
    safe_urls = [url for url in urls if url.startswith(("https://", "http://"))][:3]
    if not safe_urls:
        return []
    try:
        async with httpx.AsyncClient(timeout=settings.tinyfish_timeout) as client:
            response = await client.post(
                FETCH_URL,
                headers={**_headers(), "Content-Type": "application/json"},
                json={"urls": safe_urls, "format": "markdown", "links": False, "image_links": False},
            )
            response.raise_for_status()
    except TinyFishUnavailableError:
        raise
    except httpx.HTTPStatusError as exc:
        log.warning("TinyFish fetch failed with status %s", exc.response.status_code)
        raise TinyFishRequestError("Live source retrieval is temporarily unavailable.") from exc
    except httpx.HTTPError as exc:
        log.warning("TinyFish fetch request failed: %s", type(exc).__name__)
        raise TinyFishRequestError("Live source retrieval is temporarily unavailable.") from exc

    payload: dict[str, Any] = response.json()
    return [
        {
            "title": str(item.get("title") or item.get("url") or "Untitled source"),
            "url": str(item.get("url") or ""),
            # A bounded response prevents the operations UI becoming a raw dump.
            "text": str(item.get("text") or "")[:12000],
        }
        for item in payload.get("results", [])
        if isinstance(item, dict)
    ]
