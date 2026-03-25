"""
BatiscanClient — abstract adapter for Batiscan diagnostic platform communication.

Stub implementation for development; HTTP implementation for production.
Config-driven via BATISCAN_API_URL / BATISCAN_API_KEY env vars.
"""

from abc import ABC, abstractmethod


class BridgeError(Exception):
    """Base exception for bridge communication errors."""


class BridgeAuthError(BridgeError):
    """Authentication failed (401)."""


class BridgeNotFoundError(BridgeError):
    """Resource not found on producer (404)."""


class BridgeValidationError(BridgeError):
    """Producer rejected the request (422)."""


class BatiscanClientBase(ABC):
    """Abstract base for Batiscan communication."""

    @abstractmethod
    async def send_mission_order(self, order_data: dict) -> dict:
        """Send a mission order to Batiscan. Returns response with external_mission_id."""
        ...

    @abstractmethod
    async def check_mission_status(self, external_mission_id: str) -> dict:
        """Check status of a mission in Batiscan."""
        ...

    @abstractmethod
    async def fetch_diagnostic_package(self, dossier_ref: str) -> dict:
        """Fetch diagnostic package from producer. Returns parsed payload or raises."""
        ...


class StubBatiscanClient(BatiscanClientBase):
    """Stub client for development/testing. Simulates Batiscan responses."""

    async def send_mission_order(self, order_data: dict) -> dict:
        import uuid

        return {
            "status": "acknowledged",
            "external_mission_id": f"BAT-{uuid.uuid4().hex[:8].upper()}",
            "message": "Mission order received (stub mode)",
        }

    async def check_mission_status(self, external_mission_id: str) -> dict:
        return {
            "external_mission_id": external_mission_id,
            "status": "in_progress",
            "message": "Mission is being processed (stub mode)",
        }

    async def fetch_diagnostic_package(self, dossier_ref: str) -> dict:
        import uuid
        from datetime import UTC, datetime

        return {
            "source_system": "batiscan",
            "source_mission_id": dossier_ref,
            "object_id": dossier_ref,
            "mission_type": "asbestos_full",
            "schema_version": "v1",
            "building_match_keys": {},
            "report_pdf_url": f"https://cdn.stub.example.com/reports/{dossier_ref}.pdf",
            "publication_snapshot": {
                "pollutants_found": ["asbestos"],
                "fach_urgency": "medium",
                "zones": ["Z1"],
            },
            "annexes": [],
            "payload_hash": uuid.uuid4().hex,
            "published_at": datetime.now(UTC).isoformat(),
            "snapshot_version": 1,
        }


class HttpBatiscanClient(BatiscanClientBase):
    """Real HTTP client for Batiscan API. Configured via settings."""

    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def send_mission_order(self, order_data: dict) -> dict:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/diagnostic-orders/receive",
                json=order_data,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def check_mission_status(self, external_mission_id: str) -> dict:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/diagnostic-orders/{external_mission_id}/status",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def fetch_diagnostic_package(self, dossier_ref: str) -> dict:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{self.base_url}/dossiers/{dossier_ref}/diagnostic-package",
                    headers=self._headers(),
                )
        except httpx.TimeoutException:
            raise BridgeError("Connection to Batiscan timed out") from None
        except httpx.ConnectError:
            raise BridgeError("Cannot connect to Batiscan") from None
        except httpx.HTTPError as e:
            raise BridgeError(f"HTTP error: {e}") from None

        if resp.status_code == 401:
            raise BridgeAuthError("Authentication failed")
        elif resp.status_code == 404:
            raise BridgeNotFoundError(f"Dossier {dossier_ref} not found")
        elif resp.status_code == 422:
            try:
                detail = resp.json().get("detail", "Package not eligible")
            except Exception:
                detail = "Package not eligible"
            raise BridgeValidationError(detail)
        elif resp.status_code != 200:
            raise BridgeError(f"Unexpected status {resp.status_code} from Batiscan")

        try:
            return resp.json()
        except Exception as e:
            raise BridgeError(f"Invalid JSON response from Batiscan: {e}") from None


def get_batiscan_client() -> BatiscanClientBase:
    """Factory: returns stub or HTTP client based on config."""
    from app.config import settings

    if settings.BATISCAN_API_URL:
        return HttpBatiscanClient(settings.BATISCAN_API_URL, settings.BATISCAN_API_KEY)
    return StubBatiscanClient()
