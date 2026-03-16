"""Tests for file processing pipeline (ClamAV virus scan + OCRmyPDF).

All external services (ClamAV, ocrmypdf) are mocked — no Docker required.
"""

import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.file_processing_service import (
    ocr_pdf,
    process_uploaded_file,
    scan_file_clamav,
)

# ---------------------------------------------------------------------------
# ClamAV scan tests
# ---------------------------------------------------------------------------


class TestScanFileClamav:
    """Tests for scan_file_clamav."""

    @pytest.mark.asyncio
    async def test_scanning_disabled_returns_clean(self):
        """When CLAMAV_ENABLED is False, scan returns clean without connecting."""
        with patch("app.services.file_processing_service.settings") as mock_settings:
            mock_settings.CLAMAV_ENABLED = False
            is_clean, message = await scan_file_clamav(b"test content")
            assert is_clean is True
            assert message == "scanning_disabled"

    @pytest.mark.asyncio
    async def test_clean_file_detected(self):
        """ClamAV returns OK for a clean file."""
        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(return_value=b"stream: OK")

        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        with (
            patch("app.services.file_processing_service.settings") as mock_settings,
            patch(
                "app.services.file_processing_service.asyncio.open_connection",
                return_value=(mock_reader, mock_writer),
            ),
        ):
            mock_settings.CLAMAV_ENABLED = True
            mock_settings.CLAMAV_HOST = "localhost"
            mock_settings.CLAMAV_PORT = 3310

            is_clean, message = await scan_file_clamav(b"clean file data")
            assert is_clean is True
            assert message == "clean"

    @pytest.mark.asyncio
    async def test_infected_file_detected(self):
        """ClamAV returns FOUND for an infected file."""
        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(return_value=b"stream: Eicar-Signature FOUND")

        mock_writer = MagicMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        with (
            patch("app.services.file_processing_service.settings") as mock_settings,
            patch(
                "app.services.file_processing_service.asyncio.open_connection",
                return_value=(mock_reader, mock_writer),
            ),
        ):
            mock_settings.CLAMAV_ENABLED = True
            mock_settings.CLAMAV_HOST = "localhost"
            mock_settings.CLAMAV_PORT = 3310

            is_clean, message = await scan_file_clamav(b"infected data")
            assert is_clean is False
            assert "FOUND" in message

    @pytest.mark.asyncio
    async def test_connection_error_raises(self):
        """ConnectionError raised when ClamAV is unreachable."""
        with (
            patch("app.services.file_processing_service.settings") as mock_settings,
            patch(
                "app.services.file_processing_service.asyncio.open_connection",
                side_effect=OSError("Connection refused"),
            ),
        ):
            mock_settings.CLAMAV_ENABLED = True
            mock_settings.CLAMAV_HOST = "localhost"
            mock_settings.CLAMAV_PORT = 3310

            with pytest.raises(ConnectionError, match="Cannot connect to ClamAV"):
                await scan_file_clamav(b"test")

    @pytest.mark.asyncio
    async def test_instream_protocol_sends_chunks(self):
        """Verify the INSTREAM protocol sends correct chunk format."""
        test_data = b"A" * 100

        mock_reader = AsyncMock()
        mock_reader.read = AsyncMock(return_value=b"stream: OK")

        written_data = []
        mock_writer = MagicMock()
        mock_writer.write = MagicMock(side_effect=lambda d: written_data.append(d))
        mock_writer.drain = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        with (
            patch("app.services.file_processing_service.settings") as mock_settings,
            patch(
                "app.services.file_processing_service.asyncio.open_connection",
                return_value=(mock_reader, mock_writer),
            ),
        ):
            mock_settings.CLAMAV_ENABLED = True
            mock_settings.CLAMAV_HOST = "localhost"
            mock_settings.CLAMAV_PORT = 3310

            await scan_file_clamav(test_data)

        # First write: zINSTREAM\0
        assert written_data[0] == b"zINSTREAM\0"
        # Second write: chunk size (4 bytes big-endian)
        assert written_data[1] == struct.pack("!I", 100)
        # Third write: chunk data
        assert written_data[2] == test_data
        # Fourth write: zero-length terminator
        assert written_data[3] == struct.pack("!I", 0)


# ---------------------------------------------------------------------------
# OCR tests
# ---------------------------------------------------------------------------


class TestOcrPdf:
    """Tests for ocr_pdf."""

    @pytest.mark.asyncio
    async def test_ocr_disabled_returns_false(self):
        """When OCRMYPDF_ENABLED is False, OCR is skipped."""
        with patch("app.services.file_processing_service.settings") as mock_settings:
            mock_settings.OCRMYPDF_ENABLED = False
            result = await ocr_pdf("/tmp/in.pdf", "/tmp/out.pdf")
            assert result is False

    @pytest.mark.asyncio
    async def test_ocr_success(self):
        """OCR returns True when ocrmypdf succeeds (returncode=0)."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch("app.services.file_processing_service.settings") as mock_settings,
            patch(
                "app.services.file_processing_service.asyncio.create_subprocess_exec",
                return_value=mock_process,
            ),
        ):
            mock_settings.OCRMYPDF_ENABLED = True
            mock_settings.OCRMYPDF_LANGUAGE = "fra+deu+ita+eng"

            result = await ocr_pdf("/tmp/in.pdf", "/tmp/out.pdf")
            assert result is True

    @pytest.mark.asyncio
    async def test_ocr_already_has_text(self):
        """OCR returns False when returncode=6 (no text added)."""
        mock_process = AsyncMock()
        mock_process.returncode = 6
        mock_process.communicate = AsyncMock(return_value=(b"", b""))

        with (
            patch("app.services.file_processing_service.settings") as mock_settings,
            patch(
                "app.services.file_processing_service.asyncio.create_subprocess_exec",
                return_value=mock_process,
            ),
        ):
            mock_settings.OCRMYPDF_ENABLED = True
            mock_settings.OCRMYPDF_LANGUAGE = "fra+deu+ita+eng"

            result = await ocr_pdf("/tmp/in.pdf", "/tmp/out.pdf")
            assert result is False

    @pytest.mark.asyncio
    async def test_ocr_binary_not_found(self):
        """When ocrmypdf binary is missing, returns False gracefully."""
        with (
            patch("app.services.file_processing_service.settings") as mock_settings,
            patch(
                "app.services.file_processing_service.asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError("ocrmypdf not found"),
            ),
        ):
            mock_settings.OCRMYPDF_ENABLED = True
            mock_settings.OCRMYPDF_LANGUAGE = "fra+deu+ita+eng"

            result = await ocr_pdf("/tmp/in.pdf", "/tmp/out.pdf")
            assert result is False


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------


class TestProcessUploadedFile:
    """Tests for process_uploaded_file."""

    @pytest.mark.asyncio
    async def test_pipeline_with_both_disabled(self):
        """Both ClamAV and OCR disabled — file passes through unchanged."""
        original = b"test content"

        with patch("app.services.file_processing_service.settings") as mock_settings:
            mock_settings.CLAMAV_ENABLED = False
            mock_settings.OCRMYPDF_ENABLED = False
            mock_settings.OCRMYPDF_LANGUAGE = "fra+deu+ita+eng"

            result_bytes, metadata = await process_uploaded_file(
                file_bytes=original,
                filename="test.pdf",
                content_type="application/pdf",
            )

        assert result_bytes == original
        assert metadata["virus_scan"]["clean"] is True
        assert metadata["virus_scan"]["message"] == "scanning_disabled"
        assert metadata["ocr"]["applied"] is False

    @pytest.mark.asyncio
    async def test_pipeline_virus_detected_raises(self):
        """Infected file raises ValueError with scan message."""
        with (
            patch(
                "app.services.file_processing_service.scan_file_clamav",
                return_value=(False, "stream: Eicar-Signature FOUND"),
            ),
            pytest.raises(ValueError, match="File rejected by virus scan"),
        ):
            await process_uploaded_file(
                file_bytes=b"infected",
                filename="bad.exe",
                content_type="application/octet-stream",
            )

    @pytest.mark.asyncio
    async def test_pipeline_non_pdf_skips_ocr(self):
        """Non-PDF files skip OCR entirely."""
        with patch("app.services.file_processing_service.settings") as mock_settings:
            mock_settings.CLAMAV_ENABLED = False
            mock_settings.OCRMYPDF_ENABLED = True
            mock_settings.OCRMYPDF_LANGUAGE = "fra+deu+ita+eng"

            _, metadata = await process_uploaded_file(
                file_bytes=b"image data",
                filename="photo.jpg",
                content_type="image/jpeg",
            )

        assert metadata["ocr"]["applied"] is False
        assert metadata["ocr"]["language"] is None

    @pytest.mark.asyncio
    async def test_pipeline_metadata_structure(self):
        """Verify metadata contains expected keys."""
        with patch("app.services.file_processing_service.settings") as mock_settings:
            mock_settings.CLAMAV_ENABLED = False
            mock_settings.OCRMYPDF_ENABLED = False
            mock_settings.OCRMYPDF_LANGUAGE = "fra+deu+ita+eng"

            _, metadata = await process_uploaded_file(
                file_bytes=b"content",
                filename="report.pdf",
                content_type="application/pdf",
            )

        assert "virus_scan" in metadata
        assert "clean" in metadata["virus_scan"]
        assert "message" in metadata["virus_scan"]
        assert "ocr" in metadata
        assert "applied" in metadata["ocr"]
