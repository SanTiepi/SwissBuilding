"""BatiConnect — Gotenberg client for HTML-to-PDF conversion.

Gotenberg 8 API: POST /forms/chromium/convert/html
Docs: https://gotenberg.dev/docs/routes#html-file-into-pdf-route
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Gotenberg 8 chromium HTML → PDF endpoint
_CONVERT_URL = f"{settings.GOTENBERG_URL}/forms/chromium/convert/html"


async def html_to_pdf(
    html: str,
    *,
    margin_top: str = "1in",
    margin_bottom: str = "1in",
    margin_left: str = "0.75in",
    margin_right: str = "0.75in",
    paper_width: str = "8.27",
    paper_height: str = "11.69",
    timeout: float = 30.0,
) -> bytes:
    """Convert an HTML string to PDF bytes via Gotenberg.

    Args:
        html: Full HTML document string.
        margin_*: Page margins (CSS units or inches).
        paper_width/paper_height: A4 in inches by default.
        timeout: HTTP timeout in seconds.

    Returns:
        Raw PDF bytes.

    Raises:
        httpx.HTTPStatusError: If Gotenberg returns a non-2xx status.
        httpx.ConnectError: If Gotenberg is unreachable.
    """
    files = {"files": ("index.html", html.encode("utf-8"), "text/html")}
    data = {
        "marginTop": margin_top,
        "marginBottom": margin_bottom,
        "marginLeft": margin_left,
        "marginRight": margin_right,
        "paperWidth": paper_width,
        "paperHeight": paper_height,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(_CONVERT_URL, files=files, data=data)
        response.raise_for_status()

    logger.info("Gotenberg PDF generated: %d bytes", len(response.content))
    return response.content
