"""Tests for enhanced building dossier generation (v2).

Covers HTML template sections, completeness/risk integration,
Gotenberg PDF mock, and preview endpoint.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.dossier_service import generate_building_dossier, html_to_pdf

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def sample_diagnostic(db_session, sample_building):
    """Create a diagnostic with samples for the sample building."""
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        diagnostic_type="full",
        diagnostic_context="AvT",
        status="completed",
        laboratory="LabTest SA",
        laboratory_report_number="LR-2024-001",
        date_inspection=datetime(2024, 6, 15, tzinfo=UTC).date(),
        created_at=datetime.now(UTC),
    )
    db_session.add(diag)
    await db_session.flush()

    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        location_floor="1er etage",
        location_room="Cuisine",
        location_detail="Joint de fenetre",
        material_category="joint",
        pollutant_type="asbestos",
        concentration=2.5,
        unit="percent_weight",
        threshold_exceeded=True,
        risk_level="high",
        cfst_work_category="medium",
        waste_disposal_type="type_e",
    )
    s2 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-002",
        location_floor="RDC",
        location_room="Salon",
        material_category="peinture",
        pollutant_type="lead",
        concentration=1200.0,
        unit="mg_per_kg",
        threshold_exceeded=False,
        risk_level="low",
    )
    db_session.add_all([s1, s2])
    await db_session.commit()
    await db_session.refresh(diag)
    return diag


# ---------------------------------------------------------------------------
# HTML template tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDossierHtmlSections:
    """Verify that the HTML template contains all expected sections."""

    async def test_html_contains_cover_page(self, client, auth_headers, sample_building):
        """Cover page with building address, EGID, and stage label."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        html = resp.text
        assert "DOSSIER BATIMENT" in html
        assert "Rue Test 1" in html
        assert "Lausanne" in html
        assert "avant travaux" in html.lower() or "AvT" in html

    async def test_html_contains_building_identity_section(self, client, auth_headers, sample_building):
        """Section 1 should show building identity details."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        html = resp.text
        assert "Identite du batiment" in html
        assert "1965" in html  # construction year
        assert "residential" in html
        assert "VD" in html

    async def test_html_contains_completeness_section(self, client, auth_headers, sample_building):
        """Section 2 should show completeness assessment."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        html = resp.text
        assert "completude" in html.lower() or "Completude" in html

    async def test_html_contains_risk_section(self, client, auth_headers, sample_building):
        """Section 3 should show risk summary."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        html = resp.text
        assert "risques" in html.lower()
        assert "Amiante" in html or "Aucune evaluation" in html

    async def test_html_contains_diagnostic_section(self, client, auth_headers, sample_building, sample_diagnostic):
        """Section 4 should show diagnostic details and sample table."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        html = resp.text
        assert "Details des diagnostics" in html
        assert "S-001" in html
        assert "asbestos" in html
        assert "LabTest SA" in html

    async def test_html_contains_compliance_section(self, client, auth_headers, sample_building):
        """Section 5 should show compliance requirements."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        html = resp.text
        assert "reglementaires" in html.lower()
        assert "DGE-DIRNA" in html  # VD authority

    async def test_html_contains_actions_section(self, client, auth_headers, sample_building):
        """Section 6 should show actions (or empty message)."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        html = resp.text
        assert "Actions recommandees" in html

    async def test_html_contains_documents_section(self, client, auth_headers, sample_building):
        """Section 7 should show document inventory (or empty message)."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        html = resp.text
        assert "Inventaire des documents" in html

    async def test_html_contains_footer(self, client, auth_headers, sample_building):
        """Footer should contain disclaimer and generation info."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        html = resp.text
        assert "SwissBuildingOS" in html
        assert "garantie de conformite legale" in html.lower() or "conformite" in html.lower()

    async def test_html_contains_swiss_thresholds(self, client, auth_headers, sample_building):
        """Compliance section should include Swiss regulatory thresholds."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        html = resp.text
        assert "OTConst" in html or "ORRChim" in html


# ---------------------------------------------------------------------------
# Building without diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDossierWithoutDiagnostics:
    """Dossier generation for a building without any diagnostics."""

    async def test_generates_valid_html_without_diagnostics(self, client, auth_headers, sample_building):
        """Building with no diagnostics should still produce a valid dossier."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        html = resp.text
        assert "<!DOCTYPE html>" in html
        assert "DOSSIER BATIMENT" in html
        assert "Aucun diagnostic" in html

    async def test_completeness_shown_without_diagnostics(self, client, auth_headers, sample_building):
        """Completeness section should appear even without diagnostics."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        html = resp.text
        assert "completude" in html.lower() or "Completude" in html


# ---------------------------------------------------------------------------
# Completeness and risk data inclusion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDossierDataInclusion:
    """Verify completeness and risk data are included in the dossier."""

    async def test_completeness_data_included(self, db_session, sample_building, admin_user):
        """Generate dossier and check completeness data is used."""
        result = await generate_building_dossier(db_session, sample_building.id, admin_user.id, stage="avt")
        html = result["html"]
        # Completeness section should be present
        assert "completude" in html.lower() or "Completude" in html

    async def test_risk_data_included_when_present(self, db_session, sample_building, admin_user):
        """When no risk scores exist, the dossier should show a fallback."""
        result = await generate_building_dossier(db_session, sample_building.id, admin_user.id)
        html = result["html"]
        # Either shows risk data or the "no evaluation" message
        assert "risques" in html.lower()

    async def test_stage_avt_label(self, db_session, sample_building, admin_user):
        """AvT stage should show the correct label."""
        result = await generate_building_dossier(db_session, sample_building.id, admin_user.id, stage="avt")
        assert "avant travaux" in result["html"].lower()

    async def test_stage_apt_label(self, db_session, sample_building, admin_user):
        """ApT stage should show the correct label."""
        result = await generate_building_dossier(db_session, sample_building.id, admin_user.id, stage="apt")
        assert "apres travaux" in result["html"].lower()


# ---------------------------------------------------------------------------
# Gotenberg PDF mock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGotenbergIntegration:
    """Test Gotenberg HTML-to-PDF conversion (mocked)."""

    async def test_gotenberg_call_returns_pdf_bytes(self):
        """Mock Gotenberg call should return PDF bytes."""
        fake_pdf = b"%PDF-1.4 fake pdf content"

        mock_response = AsyncMock()
        mock_response.content = fake_pdf
        mock_response.raise_for_status = lambda: None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.dossier_service.httpx.AsyncClient", return_value=mock_client):
            result = await html_to_pdf("<html><body>Test</body></html>")

        assert result == fake_pdf
        mock_client.post.assert_called_once()

        # Verify the call used the correct endpoint
        call_args = mock_client.post.call_args
        assert "/forms/chromium/convert/html" in call_args[0][0]

    async def test_dossier_returns_pdf_when_gotenberg_available(self, db_session, sample_building, admin_user):
        """When Gotenberg returns PDF, the result should contain pdf_bytes."""
        fake_pdf = b"%PDF-1.4 fake pdf"

        with patch("app.services.dossier_service.html_to_pdf", new_callable=AsyncMock) as mock_pdf:
            mock_pdf.return_value = fake_pdf
            result = await generate_building_dossier(db_session, sample_building.id, admin_user.id)

        assert result["pdf_bytes"] == fake_pdf
        assert result["html"]  # HTML should always be present
        assert result["export_job_id"]

    async def test_dossier_returns_none_pdf_when_gotenberg_fails(self, db_session, sample_building, admin_user):
        """When Gotenberg fails, pdf_bytes should be None (graceful fallback)."""
        with patch("app.services.dossier_service.html_to_pdf", new_callable=AsyncMock) as mock_pdf:
            mock_pdf.side_effect = Exception("Connection refused")
            result = await generate_building_dossier(db_session, sample_building.id, admin_user.id)

        assert result["pdf_bytes"] is None
        assert result["html"]  # HTML always available


# ---------------------------------------------------------------------------
# Preview endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPreviewEndpoint:
    """Test the preview endpoint."""

    async def test_preview_returns_html(self, client, auth_headers, sample_building):
        """Preview endpoint should return HTML content type."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    async def test_preview_with_stage_parameter(self, client, auth_headers, sample_building):
        """Preview should accept a stage query parameter."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview?stage=apt",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "apres travaux" in resp.text.lower()

    async def test_preview_not_found(self, client, auth_headers):
        """Preview for non-existent building returns 404."""
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/buildings/{fake_id}/dossier/preview",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_generate_with_stage_parameter(self, client, auth_headers, sample_building):
        """Generate endpoint should accept a stage query parameter."""
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/dossier?stage=avt",
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_generate_invalid_stage(self, client, auth_headers, sample_building):
        """Invalid stage parameter should return 422."""
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/dossier?stage=invalid",
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Sample data in dossier
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDossierWithSamples:
    """Verify sample/diagnostic data appears correctly in dossier."""

    async def test_sample_data_in_html(self, client, auth_headers, sample_building, sample_diagnostic):
        """Sample concentrations and details should appear in the HTML."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        html = resp.text
        assert "S-001" in html
        assert "S-002" in html
        assert "Cuisine" in html
        assert "2.5" in html
        assert "asbestos" in html
        assert "lead" in html

    async def test_threshold_exceeded_highlighted(self, client, auth_headers, sample_building, sample_diagnostic):
        """Exceeded thresholds should be marked as OUI."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        html = resp.text
        assert "OUI" in html  # asbestos sample exceeds threshold
        assert "exceeded-yes" in html

    async def test_cfst_category_shown(self, client, auth_headers, sample_building, sample_diagnostic):
        """CFST work category should be visible for positive asbestos samples."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/dossier/preview",
            headers=auth_headers,
        )
        html = resp.text
        assert "medium" in html  # cfst_work_category
