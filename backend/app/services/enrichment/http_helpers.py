"""HTTP helpers — throttle + retry with backoff for external API calls."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate-limit helper
# ---------------------------------------------------------------------------
_last_request_time: float = 0.0
_RATE_LIMIT_SECONDS = 1.0


async def _throttle() -> None:
    """Wait if needed to enforce 1 request/second to external APIs."""
    global _last_request_time
    now = asyncio.get_event_loop().time()
    elapsed = now - _last_request_time
    if elapsed < _RATE_LIMIT_SECONDS:
        await asyncio.sleep(_RATE_LIMIT_SECONDS - elapsed)
    _last_request_time = asyncio.get_event_loop().time()


# ---------------------------------------------------------------------------
# Retry with backoff
# ---------------------------------------------------------------------------
_TRANSIENT_STATUS_CODES = {500, 502, 503, 504}
_RETRY_DELAYS: dict[int, float] = {
    500: 2.0,
    502: 2.0,
    503: 2.0,
    504: 5.0,
}
_CONNECTION_RETRY_DELAY = 3.0


async def _retry_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    params: dict | None = None,
    data: dict | None = None,
    json_body: dict | None = None,
    headers: dict | None = None,
    timeout: float = 15.0,
) -> tuple[httpx.Response, int]:
    """Execute an HTTP request with a single retry on transient failures.

    Returns (response, retry_count).
    On permanent errors (400, 404) returns immediately with no retry.
    """
    retry_count = 0
    kwargs: dict[str, Any] = {}
    if params:
        kwargs["params"] = params
    if data:
        kwargs["data"] = data
    if json_body:
        kwargs["json"] = json_body
    if headers:
        kwargs["headers"] = headers

    try:
        if method == "GET":
            resp = await client.get(url, **kwargs)
        else:
            resp = await client.post(url, **kwargs)
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
        # Connection error — retry once
        logger.warning("Connection error for %s, retrying in %.1fs: %s", url, _CONNECTION_RETRY_DELAY, exc)
        await asyncio.sleep(_CONNECTION_RETRY_DELAY)
        retry_count = 1
        if method == "GET":
            resp = await client.get(url, **kwargs)
        else:
            resp = await client.post(url, **kwargs)
        return resp, retry_count

    if resp.status_code in _TRANSIENT_STATUS_CODES:
        delay = _RETRY_DELAYS.get(resp.status_code, 2.0)
        logger.warning(
            "Transient %d for %s, retrying in %.1fs",
            resp.status_code,
            url,
            delay,
        )
        await asyncio.sleep(delay)
        retry_count = 1
        if method == "GET":
            resp = await client.get(url, **kwargs)
        else:
            resp = await client.post(url, **kwargs)

    return resp, retry_count
