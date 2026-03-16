"""File processing pipeline: virus scanning (ClamAV) + OCR (OCRmyPDF) for uploaded documents.

Integrates into the document upload flow to ensure every file is:
1. Scanned for viruses before storage
2. OCR-processed (PDFs only) to make scanned documents searchable

Both features can be disabled via settings for dev/test environments.
"""

import asyncio
import struct
import tempfile
from pathlib import Path

from app.config import settings


async def scan_file_clamav(file_bytes: bytes) -> tuple[bool, str]:
    """Scan file bytes with ClamAV via clamd TCP protocol (INSTREAM command).

    Returns:
        (is_clean, message) — True if file is clean or scanning is disabled.

    Raises:
        ConnectionError: If ClamAV is unreachable.
    """
    if not settings.CLAMAV_ENABLED:
        return True, "scanning_disabled"

    try:
        reader, writer = await asyncio.open_connection(settings.CLAMAV_HOST, settings.CLAMAV_PORT)
    except OSError as exc:
        raise ConnectionError(f"Cannot connect to ClamAV at {settings.CLAMAV_HOST}:{settings.CLAMAV_PORT}") from exc

    try:
        # Send INSTREAM command (null-terminated)
        writer.write(b"zINSTREAM\0")
        await writer.drain()

        # Send file data in chunks (max 2MB each)
        chunk_size = 2 * 1024 * 1024
        offset = 0
        while offset < len(file_bytes):
            chunk = file_bytes[offset : offset + chunk_size]
            # Each chunk is prefixed with its size as a 4-byte big-endian unsigned int
            writer.write(struct.pack("!I", len(chunk)))
            writer.write(chunk)
            await writer.drain()
            offset += chunk_size

        # End of stream: zero-length chunk
        writer.write(struct.pack("!I", 0))
        await writer.drain()

        # Read response
        response = await reader.read(4096)
        response_text = response.decode("utf-8", errors="replace").strip()
    finally:
        writer.close()
        await writer.wait_closed()

    # ClamAV response format: "stream: OK" or "stream: <virus_name> FOUND"
    if response_text.endswith("OK"):
        return True, "clean"

    return False, response_text


async def ocr_pdf(input_path: str, output_path: str) -> bool:
    """Run OCRmyPDF on a PDF to make it searchable.

    Uses --skip-text to avoid re-processing pages that already contain text.

    Returns:
        True if OCR was applied successfully, False otherwise.
    """
    if not settings.OCRMYPDF_ENABLED:
        return False

    try:
        process = await asyncio.create_subprocess_exec(
            "ocrmypdf",
            "--skip-text",
            "--language",
            settings.OCRMYPDF_LANGUAGE,
            "--output-type",
            "pdf",
            "--quiet",
            input_path,
            output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode == 0:
            return True

        # Return code 6 means "no text was added" (already has text) — not an error
        if process.returncode == 6:
            return False

        # Log but don't fail the upload for OCR issues
        stderr_text = stderr.decode("utf-8", errors="replace").strip()
        import structlog

        logger = structlog.get_logger()
        logger.warning(
            "ocrmypdf_failed",
            returncode=process.returncode,
            stderr=stderr_text[:500],
        )
        return False

    except FileNotFoundError:
        # ocrmypdf binary not installed — skip silently
        import structlog

        structlog.get_logger().warning("ocrmypdf_not_installed")
        return False


async def process_uploaded_file(
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> tuple[bytes, dict]:
    """Full processing pipeline for uploaded files.

    Steps:
        1. Virus scan via ClamAV (rejects infected files)
        2. OCR via OCRmyPDF (PDFs only, makes scanned pages searchable)

    Returns:
        (processed_bytes, processing_metadata)

    Raises:
        ValueError: If file is rejected by virus scan.
    """
    metadata: dict = {}

    # Step 1: Virus scan
    is_clean, scan_msg = await scan_file_clamav(file_bytes)
    metadata["virus_scan"] = {"clean": is_clean, "message": scan_msg}
    if not is_clean:
        raise ValueError(f"File rejected by virus scan: {scan_msg}")

    # Step 2: OCR if PDF
    is_pdf = content_type == "application/pdf" or filename.lower().endswith(".pdf")
    if is_pdf:
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = str(Path(tmpdir) / "input.pdf")
            output_path = str(Path(tmpdir) / "output.pdf")

            with open(input_path, "wb") as f:
                f.write(file_bytes)

            ocr_applied = await ocr_pdf(input_path, output_path)
            metadata["ocr"] = {
                "applied": ocr_applied,
                "language": settings.OCRMYPDF_LANGUAGE,
            }

            if ocr_applied and Path(output_path).exists():
                with open(output_path, "rb") as f:
                    file_bytes = f.read()
    else:
        metadata["ocr"] = {"applied": False, "language": None}

    return file_bytes, metadata
