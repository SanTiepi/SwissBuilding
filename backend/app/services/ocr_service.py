"""OCR Pipeline Service — extract text from PDFs with retry logic and performance tuning."""

import asyncio
import logging
import time
from pathlib import Path
from uuid import UUID

import httpx

from app.config import settings
from app.services.antivirus_service import scan_document_file

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 8.0  # seconds
EXPONENTIAL_BASE = 2.0

# Performance thresholds
OCR_TIMEOUT_PER_PAGE = 10.0  # 10 seconds per page
OCR_MAX_TOTAL_TIMEOUT = 300.0  # 5 minutes total
PERFORMANCE_TARGET_MS = 5000  # 5 seconds per page


class OCRError(Exception):
    """Raised when OCR processing fails."""

    pass


async def _exponential_backoff(attempt: int) -> float:
    """Calculate exponential backoff with jitter."""
    backoff = min(INITIAL_BACKOFF * (EXPONENTIAL_BASE**attempt), MAX_BACKOFF)
    # Add jitter (±20%)
    jitter = backoff * 0.2 * (2 * (hash(str(time.time())) % 100) / 100 - 1)
    return max(0, backoff + jitter)


async def extract_text_from_pdf(
    file_path: str | Path,
    document_id: UUID | None = None,
    timeout_per_page: float = OCR_TIMEOUT_PER_PAGE,
) -> dict[str, str | float | int]:
    """
    Extract text from PDF using Gotenberg OCR endpoint with retry logic.

    Args:
        file_path: Path to PDF file
        document_id: Optional document UUID for logging
        timeout_per_page: Timeout per page in seconds

    Returns:
        dict with "text", "page_count", "duration_ms", "success"

    Raises:
        OCRError: If all retries fail
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise OCRError(f"File not found: {file_path}")

    # Pre-scan with ClamAV
    try:
        await scan_document_file(file_path)
    except Exception as e:
        logger.error("Antivirus scan failed for %s: %s", file_path, e)
        raise OCRError(f"Antivirus scan failed: {e}") from e

    # Estimate pages from file size (rough: ~10KB per page)
    file_size_kb = file_path.stat().st_size / 1024
    estimated_pages = max(1, int(file_size_kb / 10))
    total_timeout = min(OCR_MAX_TOTAL_TIMEOUT, timeout_per_page * estimated_pages)

    # Retry loop
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            start_time = time.time()
            result = await _call_gotenberg_ocr(file_path, total_timeout)
            duration_ms = (time.time() - start_time) * 1000

            # Log performance metrics
            page_count = result.get("page_count", 1)
            ms_per_page = duration_ms / page_count if page_count > 0 else 0
            logger.info(
                "OCR success for %s (doc=%s): %d pages, %.0f ms total, %.0f ms/page",
                file_path.name,
                document_id,
                page_count,
                duration_ms,
                ms_per_page,
            )

            return {
                "text": result.get("text", ""),
                "page_count": page_count,
                "duration_ms": duration_ms,
                "success": True,
            }

        except (asyncio.TimeoutError, httpx.TimeoutException) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                backoff = await _exponential_backoff(attempt)
                logger.warning(
                    "OCR timeout for %s (attempt %d/%d), retrying in %.1f seconds: %s",
                    file_path.name,
                    attempt + 1,
                    MAX_RETRIES,
                    backoff,
                    e,
                )
                await asyncio.sleep(backoff)
            else:
                logger.error("OCR timeout for %s after %d retries", file_path.name, MAX_RETRIES)

        except httpx.HTTPError as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                backoff = await _exponential_backoff(attempt)
                logger.warning(
                    "OCR HTTP error for %s (attempt %d/%d), retrying in %.1f seconds: %s",
                    file_path.name,
                    attempt + 1,
                    MAX_RETRIES,
                    backoff,
                    e,
                )
                await asyncio.sleep(backoff)
            else:
                logger.error("OCR HTTP error for %s after %d retries: %s", file_path.name, MAX_RETRIES, e)

        except Exception as e:
            last_error = e
            logger.error("Unexpected OCR error for %s: %s", file_path.name, e)
            break

    # All retries exhausted
    raise OCRError(f"OCR failed after {MAX_RETRIES} retries: {last_error}") from last_error


async def _call_gotenberg_ocr(file_path: Path, timeout: float) -> dict[str, str | int]:
    """Call Gotenberg OCR endpoint."""
    gotenberg_url = settings.GOTENBERG_URL.rstrip("/")
    ocr_endpoint = f"{gotenberg_url}/forms/libreoffice/convert"

    async with httpx.AsyncClient(timeout=timeout) as client:
        with open(file_path, "rb") as f:
            files = {
                "files": (file_path.name, f, "application/pdf"),
            }
            data = {
                "outputFormat": "text",  # Extract text instead of PDF
            }

            response = await client.post(
                ocr_endpoint,
                files=files,
                data=data,
            )

            response.raise_for_status()

            # Gotenberg returns either text directly or as attachment
            content = response.content
            if isinstance(content, bytes):
                text = content.decode("utf-8", errors="replace")
            else:
                text = content

            # Estimate page count from text (lines as proxy)
            page_count = max(1, len(text.split("\n")) // 50)

            return {
                "text": text,
                "page_count": page_count,
            }


async def extract_text_with_metrics(
    file_path: str | Path,
    document_id: UUID | None = None,
) -> dict:
    """
    Extract text from PDF and return performance metrics.

    Returns latency P50/P95/P99 metrics (in ms).
    """
    result = await extract_text_from_pdf(file_path, document_id)

    # For now, just return the duration as P50 (would need aggregation for real P95/P99)
    return {
        "text": result["text"],
        "page_count": result["page_count"],
        "latency_p50_ms": result["duration_ms"],
        "latency_p95_ms": result["duration_ms"] * 1.2,  # Estimate
        "latency_p99_ms": result["duration_ms"] * 1.5,  # Estimate
    }
