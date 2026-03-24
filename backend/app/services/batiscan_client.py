"""
BatiscanClient — abstract adapter for Batiscan diagnostic platform communication.

Stub implementation for development; HTTP implementation for production.
Config-driven via BATISCAN_API_URL / BATISCAN_API_KEY env vars.
"""

from abc import ABC, abstractmethod


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


class HttpBatiscanClient(BatiscanClientBase):
    """Real HTTP client for Batiscan API. Configured via settings."""

    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def send_mission_order(self, order_data: dict) -> dict:
        import httpx

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/diagnostic-orders/receive",
                json=order_data,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def check_mission_status(self, external_mission_id: str) -> dict:
        import httpx

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/diagnostic-orders/{external_mission_id}/status",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()


def get_batiscan_client() -> BatiscanClientBase:
    """Factory: returns stub or HTTP client based on config."""
    from app.config import settings

    batiscan_url = getattr(settings, "BATISCAN_API_URL", None)
    if batiscan_url:
        api_key = getattr(settings, "BATISCAN_API_KEY", None)
        return HttpBatiscanClient(batiscan_url, api_key)
    return StubBatiscanClient()
