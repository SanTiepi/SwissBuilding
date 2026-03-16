"""Tests for building quality API endpoint."""

import uuid

import pytest

from app.api.building_quality import router as quality_router
from app.main import app
from app.models.building_risk_score import BuildingRiskScore

# Register the router for tests (not yet in router.py)
app.include_router(quality_router, prefix="/api/v1")


@pytest.mark.asyncio
class TestQualityAPI:
    """Building data quality API tests."""

    async def test_quality_for_building_with_data(self, client, auth_headers, sample_building, db_session):
        """Quality score reflects available data."""
        # Add a risk score to boost the score
        risk = BuildingRiskScore(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            overall_risk_level="medium",
            asbestos_probability=0.6,
        )
        db_session.add(risk)
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/quality",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "overall_score" in body
        assert "sections" in body
        assert "missing" in body
        # Building has address and construction_year, so identity score > 0
        assert body["sections"]["identity"]["score"] > 0

    async def test_quality_for_building_minimal_data(self, client, auth_headers, sample_building):
        """Building with minimal data has low quality score and many missing items."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/quality",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["overall_score"] < 0.5
        assert len(body["missing"]) > 0

    async def test_quality_building_not_found(self, client, auth_headers):
        """Returns 404 for non-existent building."""
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/buildings/{fake_id}/quality",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_quality_response_structure(self, client, auth_headers, sample_building):
        """Quality response has the expected structure."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/quality",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["overall_score"], float)
        assert isinstance(body["sections"], dict)
        assert isinstance(body["missing"], list)

    async def test_quality_sections_contain_expected_keys(self, client, auth_headers, sample_building):
        """Quality sections contain all expected assessment areas."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/quality",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        sections = resp.json()["sections"]
        expected_keys = {
            "identity",
            "diagnostics",
            "zones",
            "materials",
            "interventions",
            "documents",
            "plans",
            "evidence",
        }
        assert expected_keys == set(sections.keys())
        # Each section should have score and details
        for key in expected_keys:
            assert "score" in sections[key]
            assert "details" in sections[key]
