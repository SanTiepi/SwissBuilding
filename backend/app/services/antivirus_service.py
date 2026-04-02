"""ClamAV antivirus service — scan documents before processing."""

import asyncio
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class AntivirusError(Exception):
    """Raised when antivirus scan fails or detects malware."""

    pass


class ClamAVService:
    """Wrapper around ClamAV daemon for document scanning."""

    def __init__(self, host: str = settings.CLAMAV_HOST, port: int = settings.CLAMAV_PORT):
        """Initialize ClamAV service with daemon connection parameters."""
        self.host = host
        self.port = port
        self.enabled = settings.CLAMAV_ENABLED

    async def scan_file(self, file_path: str | Path) -> dict[str, bool | str]:
        """
        Scan a file using ClamAV daemon.

        Args:
            file_path: Path to file to scan

        Returns:
            dict with "clean" (bool) and "threat" (str if detected)
        """
        if not self.enabled:
            logger.debug("ClamAV disabled, skipping scan for %s", file_path)
            return {"clean": True, "threat": None}

        try:
            result = await self._scan_via_daemon(str(file_path))
            return result
        except Exception as e:
            logger.error("ClamAV scan failed for %s: %s", file_path, e)
            raise AntivirusError(f"Antivirus scan failed: {e}") from e

    async def _scan_via_daemon(self, file_path: str) -> dict[str, bool | str]:
        """Scan file via ClamAV daemon using INSTREAM command."""
        try:
            # Connect to ClamAV daemon
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10.0,
            )

            # Read file in chunks and send to daemon
            file_size = Path(file_path).stat().st_size
            logger.debug("Scanning %s (%d bytes)", file_path, file_size)

            # Send INSTREAM command
            writer.write(b"INSTREAM\n")
            await writer.drain()

            # Send file data in chunks (each chunk prefixed with 4-byte length)
            chunk_size = 4096
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    # Send 4-byte big-endian length followed by chunk
                    length_bytes = len(chunk).to_bytes(4, "big")
                    writer.write(length_bytes + chunk)
                    await writer.drain()

            # Send 0-length chunk to signal end
            writer.write(b"\x00\x00\x00\x00")
            await writer.drain()

            # Read response (e.g., "stream: OK" or "stream: Eicar-Test-File FOUND")
            response = await asyncio.wait_for(reader.readline(), timeout=10.0)
            response_str = response.decode("utf-8", errors="replace").strip()

            writer.close()
            await writer.wait_closed()

            if "FOUND" in response_str:
                # Extract threat name
                threat = response_str.split(": ")[-1].replace(" FOUND", "")
                logger.warning("Malware detected in %s: %s", file_path, threat)
                return {"clean": False, "threat": threat}
            elif "OK" in response_str:
                logger.debug("File %s is clean", file_path)
                return {"clean": True, "threat": None}
            else:
                logger.error("Unexpected ClamAV response: %s", response_str)
                raise AntivirusError(f"Unexpected response: {response_str}")

        except asyncio.TimeoutError as e:
            raise AntivirusError(f"ClamAV daemon timeout: {e}") from e


# Global instance
_clamav_service: ClamAVService | None = None


def get_antivirus_service() -> ClamAVService:
    """Get or create global ClamAV service instance."""
    global _clamav_service
    if _clamav_service is None:
        _clamav_service = ClamAVService()
    return _clamav_service


async def scan_document_file(file_path: str | Path) -> None:
    """
    Scan a document file using ClamAV.

    Raises AntivirusError if malware is detected or scan fails.

    Args:
        file_path: Path to file to scan

    Raises:
        AntivirusError: If malware detected or scan fails
    """
    service = get_antivirus_service()
    result = await service.scan_file(file_path)
    if not result.get("clean"):
        raise AntivirusError(f"File is infected: {result.get('threat', 'unknown')}")
