"""Tests for building dossier generation API endpoints."""

import uuid

import pytest

from app.api.dossier import router as dossier_router
from app.main import app

# Register the router for tests (not yet in router.py)
app.include_router(dossier_router, prefix="/api/v1")


@pytest.mark.asyncio
class TestDossierAPI:
    """Building dossier generation API tests."""

    async def test_generate_dossier_admin(self, client, auth_headers, sample_building):
        """Admin can generate a building dossier."""
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/dossier",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "html" in body
        assert "export_job_id" in body
        assert body["format"] == "html"

    async def test_generate_dossier_owner(self, client, owner_headers, sample_building):
        """Owner can generate a dossier (has buildings:read permission)."""
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/dossier",
            headers=owner_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["format"] == "html"
        assert "SwissBuildingOS" in body["html"]

    async def test_dossier_building_not_found(self, client, auth_headers):
        """Returns 404 when building does not exist."""
        fake_id = uuid.uuid4()
        resp = await client.post(
            f"/api/v1/buildings/{fake_id}/dossier",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_preview_dossier(self, client, auth_headers, sample_building):
        """Preview returns HTML content."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "Rue Test 1" in resp.text

    async def test_dossier_html_contains_building_info(self, client, auth_headers, sample_building):
        """Dossier HTML includes building address and metadata."""
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/dossier",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        html = resp.json()["html"]
        assert "Rue Test 1" in html
        assert "Lausanne" in html
        assert "1000" in html
