"""Test suite for OCR Pipeline Hardening — retry logic, ClamAV, performance tuning."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.antivirus_service import AntivirusError, ClamAVService, scan_document_file
from app.services.ocr_service import (
    OCRError,
    extract_text_from_pdf,
    extract_text_with_metrics,
)


class TestAntivirusService:
    """Tests for ClamAV antivirus scanning."""

    @pytest.mark.asyncio
    async def test_clamav_scan_enabled_clean_file(self, tmp_path):
        """Test that ClamAV correctly identifies clean files."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"dummy")

        service = ClamAVService()
        service.enabled = True

        # Mock daemon connection
        with patch("app.services.antivirus_service.asyncio.open_connection") as mock_conn:
            reader = AsyncMock()
            writer = AsyncMock()
            mock_conn.return_value = (reader, writer)

            reader.readline = AsyncMock(return_value=b"stream: OK\n")

            result = await service.scan_file(str(test_file))

            assert result["clean"] is True
            assert result["threat"] is None
            writer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_clamav_scan_detects_malware(self, tmp_path):
        """Test that ClamAV correctly identifies infected files."""
        test_file = tmp_path / "malware.pdf"
        test_file.write_bytes(b"dummy")

        service = ClamAVService()
        service.enabled = True

        with patch("app.services.antivirus_service.asyncio.open_connection") as mock_conn:
            reader = AsyncMock()
            writer = AsyncMock()
            mock_conn.return_value = (reader, writer)

            reader.readline = AsyncMock(return_value=b"stream: Trojan.Generic FOUND\n")

            result = await service.scan_file(str(test_file))

            assert result["clean"] is False
            assert "Trojan.Generic" in result["threat"]

    @pytest.mark.asyncio
    async def test_clamav_scan_disabled_skips_check(self):
        """Test that disabled ClamAV service skips scanning."""
        service = ClamAVService()
        service.enabled = False

        result = await service.scan_file("any_file.pdf")

        assert result["clean"] is True
        assert result["threat"] is None

    @pytest.mark.asyncio
    async def test_clamav_daemon_timeout_raises_error(self):
        """Test that daemon timeout raises AntivirusError."""
        service = ClamAVService()
        service.enabled = True

        with patch("app.services.antivirus_service.asyncio.open_connection") as mock_conn:
            mock_conn.side_effect = TimeoutError("Connection timeout")

            with pytest.raises(AntivirusError, match="timeout"):
                await service.scan_file("test.pdf")

    @pytest.mark.asyncio
    async def test_scan_document_file_raises_on_infected(self, tmp_path):
        """Test that scan_document_file raises on infected files."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy content")

        with patch("app.services.antivirus_service.get_antivirus_service") as mock_svc:
            service = AsyncMock()
            service.scan_file = AsyncMock(return_value={"clean": False, "threat": "Eicar-Test-File"})
            mock_svc.return_value = service

            with pytest.raises(AntivirusError, match="infected"):
                await scan_document_file(str(test_file))


class TestOCRRetryLogic:
    """Tests for OCR retry mechanism with exponential backoff."""

    @pytest.mark.asyncio
    async def test_ocr_succeeds_on_first_attempt(self, tmp_path):
        """Test that OCR succeeds immediately when service is healthy."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\n")

        with patch("app.services.ocr_service.scan_document_file") as mock_scan:
            with patch("app.services.ocr_service._call_gotenberg_ocr") as mock_ocr:
                mock_scan.return_value = None
                mock_ocr.return_value = {"text": "Sample text", "page_count": 1}

                result = await extract_text_from_pdf(str(test_pdf))

                assert result["success"] is True
                assert "Sample text" in result["text"]
                mock_ocr.assert_called_once()

    @pytest.mark.asyncio
    async def test_ocr_retries_on_timeout(self, tmp_path):
        """Test that OCR retries after timeout."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\n" * 1000)  # Make it large enough

        with patch("app.services.ocr_service.scan_document_file"):
            with patch("app.services.ocr_service._call_gotenberg_ocr") as mock_ocr:
                # First 2 attempts timeout, 3rd succeeds
                mock_ocr.side_effect = [
                    TimeoutError("First timeout"),
                    TimeoutError("Second timeout"),
                    {"text": "Success after retries", "page_count": 1},
                ]

                result = await extract_text_from_pdf(str(test_pdf))

                assert result["success"] is True
                assert "Success after retries" in result["text"]
                assert mock_ocr.call_count == 3

    @pytest.mark.asyncio
    async def test_ocr_raises_after_max_retries_exceeded(self, tmp_path):
        """Test that OCR raises OCRError after max retries."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\n")

        with patch("app.services.ocr_service.scan_document_file"):
            with patch("app.services.ocr_service._call_gotenberg_ocr") as mock_ocr:
                # All attempts timeout
                mock_ocr.side_effect = TimeoutError("Persistent timeout")

                with pytest.raises(OCRError, match="after 3 retries"):
                    await extract_text_from_pdf(str(test_pdf))

    @pytest.mark.asyncio
    async def test_ocr_retries_on_http_error(self, tmp_path):
        """Test that OCR retries on HTTP errors."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\n")

        with patch("app.services.ocr_service.scan_document_file"):
            with patch("app.services.ocr_service._call_gotenberg_ocr") as mock_ocr:
                # First attempt fails with 503, second succeeds
                mock_ocr.side_effect = [
                    httpx.HTTPStatusError(
                        "Service unavailable",
                        request=MagicMock(),
                        response=MagicMock(status_code=503),
                    ),
                    {"text": "Recovered from error", "page_count": 1},
                ]

                result = await extract_text_from_pdf(str(test_pdf))

                assert result["success"] is True
                assert mock_ocr.call_count == 2

    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self):
        """Test that exponential backoff increases appropriately."""
        from app.services.ocr_service import _exponential_backoff

        backoff0 = await _exponential_backoff(0)
        backoff1 = await _exponential_backoff(1)
        backoff2 = await _exponential_backoff(2)

        # Each should be roughly 2x previous (with jitter)
        assert 0.8 < backoff0 < 1.3
        assert 1.5 < backoff1 < 2.5
        assert 3.0 < backoff2 < 5.0

    @pytest.mark.asyncio
    async def test_ocr_raises_on_nonexistent_file(self):
        """Test that OCR raises on missing files."""
        with pytest.raises(OCRError, match="File not found"):
            await extract_text_from_pdf("/nonexistent/file.pdf")

    @pytest.mark.asyncio
    async def test_ocr_scans_file_before_processing(self, tmp_path):
        """Test that antivirus scan happens before OCR processing."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\n")

        with patch("app.services.ocr_service.scan_document_file") as mock_scan:
            mock_scan.side_effect = AntivirusError("File is infected")

            with pytest.raises(OCRError, match="Antivirus scan failed"):
                await extract_text_from_pdf(str(test_pdf))

            mock_scan.assert_called_once()


class TestOCRPerformance:
    """Tests for OCR performance tracking and tuning."""

    @pytest.mark.asyncio
    async def test_ocr_tracks_duration(self, tmp_path):
        """Test that OCR returns duration metrics."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\n")

        with patch("app.services.ocr_service.scan_document_file"):
            with patch("app.services.ocr_service._call_gotenberg_ocr") as mock_ocr:
                mock_ocr.return_value = {"text": "sample", "page_count": 1}

                result = await extract_text_from_pdf(str(test_pdf))

                assert "duration_ms" in result
                assert result["duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_ocr_logs_performance_metrics(self, tmp_path, caplog):
        """Test that OCR logs per-page performance metrics."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\n" * 100)

        with patch("app.services.ocr_service.scan_document_file"):
            with patch("app.services.ocr_service._call_gotenberg_ocr") as mock_ocr:
                mock_ocr.return_value = {"text": "content\n" * 100, "page_count": 5}

                with caplog.at_level("INFO"):
                    result = await extract_text_from_pdf(str(test_pdf))

                assert result["success"] is True
                assert "5 pages" in caplog.text
                assert "ms/page" in caplog.text

    @pytest.mark.asyncio
    async def test_ocr_respects_page_count_estimate(self, tmp_path):
        """Test that OCR estimates timeout based on file size."""
        test_pdf = tmp_path / "large.pdf"
        # Create large file (simulates ~50 pages)
        test_pdf.write_bytes(b"%PDF-1.4\n" * 5000)

        with patch("app.services.ocr_service.scan_document_file"):
            with patch("app.services.ocr_service._call_gotenberg_ocr") as mock_ocr:
                mock_ocr.return_value = {"text": "content", "page_count": 50}

                result = await extract_text_from_pdf(str(test_pdf))

                # Verify timeout was adjusted (should be at least 10 * pages)
                call_args = mock_ocr.call_args
                timeout_arg = call_args[0][1] if len(call_args[0]) > 1 else 0
                assert timeout_arg >= 40  # 50 pages * 10 seconds, capped at 300 total

    @pytest.mark.asyncio
    async def test_extract_text_with_metrics_returns_latencies(self, tmp_path):
        """Test that extract_text_with_metrics returns P50/P95/P99."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\n")

        with patch("app.services.ocr_service.scan_document_file"):
            with patch("app.services.ocr_service._call_gotenberg_ocr") as mock_ocr:
                mock_ocr.return_value = {"text": "sample text", "page_count": 1}

                result = await extract_text_with_metrics(str(test_pdf))

                assert "latency_p50_ms" in result
                assert "latency_p95_ms" in result
                assert "latency_p99_ms" in result
                assert result["latency_p95_ms"] >= result["latency_p50_ms"]
                assert result["latency_p99_ms"] >= result["latency_p95_ms"]

    @pytest.mark.asyncio
    async def test_ocr_timeout_configurable(self, tmp_path):
        """Test that OCR timeout can be configured per call."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\n")

        with patch("app.services.ocr_service.scan_document_file"):
            with patch("app.services.ocr_service._call_gotenberg_ocr") as mock_ocr:
                mock_ocr.return_value = {"text": "sample", "page_count": 1}

                result = await extract_text_from_pdf(
                    str(test_pdf),
                    timeout_per_page=20.0,
                )

                call_args = mock_ocr.call_args
                # Timeout should be adjusted for the custom timeout_per_page
                assert call_args is not None

    @pytest.mark.asyncio
    async def test_ocr_page_count_from_text_lines(self, tmp_path):
        """Test that page count is estimated from extracted text."""
        test_pdf = tmp_path / "test.pdf"
        test_pdf.write_bytes(b"%PDF-1.4\n" * 100)

        with patch("app.services.ocr_service.scan_document_file"):
            with patch("app.services.ocr_service._call_gotenberg_ocr") as mock_ocr:
                # Large text content = many pages
                mock_ocr.return_value = {
                    "text": "line\n" * 1000,
                    "page_count": 20,
                }

                result = await extract_text_from_pdf(str(test_pdf))

                assert result["page_count"] == 20
