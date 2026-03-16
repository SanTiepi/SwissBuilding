"""Tests for the Completeness Engine service and API endpoint."""

import uuid
from datetime import date

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.services.completeness_engine import evaluate_completeness

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_building(db_session, admin_user, *, construction_year=1965, **kwargs):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        **kwargs,
    )
    db_session.add(building)
    return building


def _make_diagnostic(db_session, building, *, status="completed", context="AvT", **kwargs):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="full",
        diagnostic_context=context,
        status=status,
        date_inspection=date(2024, 1, 15),
        **kwargs,
    )
    db_session.add(diag)
    return diag


def _make_sample(db_session, diag, *, pollutant_type="asbestos", concentration=5.0, unit="percent_weight", **kwargs):
    defaults = {
        "risk_level": "high",
        "threshold_exceeded": True,
        "cfst_work_category": "medium",
        "waste_disposal_type": "type_e",
    }
    defaults.update(kwargs)
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        concentration=concentration,
        unit=unit,
        **defaults,
    )
    db_session.add(sample)
    return sample


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCompletenessEngine:
    """Completeness engine service tests."""

    async def test_empty_building_low_score(self, db_session, admin_user):
        """Building with no diagnostics/samples/docs has low score."""
        building = _make_building(db_session, admin_user)
        await db_session.commit()

        result = await evaluate_completeness(db_session, building.id, "avt")
        assert result.overall_score < 0.3
        assert not result.ready_to_proceed
        assert len(result.missing_items) > 0
        assert result.workflow_stage == "avt"

    async def test_complete_avt_high_score(self, db_session, admin_user):
        """Building with full AvT data gets high completeness score."""
        building = _make_building(db_session, admin_user, construction_year=1965)
        diag = _make_diagnostic(db_session, building, status="validated", context="AvT")

        # Create samples for all 5 pollutants
        for pollutant in ("asbestos", "pcb", "lead", "hap", "radon"):
            _make_sample(
                db_session,
                diag,
                pollutant_type=pollutant,
                concentration=10.0,
                unit="mg_per_kg",
            )

        # Add documents
        db_session.add(
            Document(
                id=uuid.uuid4(),
                building_id=building.id,
                file_path="/reports/diag.pdf",
                file_name="diagnostic_report.pdf",
                document_type="diagnostic_report",
            )
        )
        db_session.add(
            Document(
                id=uuid.uuid4(),
                building_id=building.id,
                file_path="/reports/lab.pdf",
                file_name="lab_analysis.pdf",
                document_type="lab_report",
            )
        )

        # Add floor plan
        db_session.add(
            TechnicalPlan(
                id=uuid.uuid4(),
                building_id=building.id,
                plan_type="floor_plan",
                title="RDC",
                file_path="/plans/rdc.pdf",
                file_name="rdc.pdf",
            )
        )

        await db_session.commit()

        result = await evaluate_completeness(db_session, building.id, "avt")
        assert result.overall_score > 0.7
        assert result.workflow_stage == "avt"

    async def test_pre_1990_requires_asbestos(self, db_session, admin_user):
        """Pre-1990 building must have asbestos samples."""
        building = _make_building(db_session, admin_user, construction_year=1975)
        diag = _make_diagnostic(db_session, building)
        # Only lead sample, no asbestos
        _make_sample(db_session, diag, pollutant_type="lead", concentration=100.0, unit="mg_per_kg")
        await db_session.commit()

        result = await evaluate_completeness(db_session, building.id, "avt")
        asbestos_check = next(c for c in result.checks if c.id == "has_asbestos_samples")
        assert asbestos_check.status == "missing"

    async def test_post_1990_asbestos_not_applicable(self, db_session, admin_user):
        """Post-1990 building marks asbestos samples as not applicable."""
        building = _make_building(db_session, admin_user, construction_year=1995)
        diag = _make_diagnostic(db_session, building)
        _make_sample(db_session, diag, pollutant_type="lead", concentration=100.0, unit="mg_per_kg")
        await db_session.commit()

        result = await evaluate_completeness(db_session, building.id, "avt")
        asbestos_check = next(c for c in result.checks if c.id == "has_asbestos_samples")
        assert asbestos_check.status == "not_applicable"

    async def test_missing_documents_reduces_score(self, db_session, admin_user):
        """Missing documents reduces completeness score."""
        building = _make_building(db_session, admin_user)
        diag = _make_diagnostic(db_session, building)
        _make_sample(db_session, diag, pollutant_type="asbestos")
        await db_session.commit()

        result = await evaluate_completeness(db_session, building.id, "avt")
        report_check = next(c for c in result.checks if c.id == "has_report")
        assert report_check.status == "missing"
        plans_check = next(c for c in result.checks if c.id == "has_plans")
        assert plans_check.status == "missing"

    async def test_pcb_applicability_range(self, db_session, admin_user):
        """PCB samples only required for buildings 1955-1975."""
        # Building outside PCB range
        building = _make_building(db_session, admin_user, construction_year=1980)
        _make_diagnostic(db_session, building)
        await db_session.commit()

        result = await evaluate_completeness(db_session, building.id, "avt")
        pcb_check = next(c for c in result.checks if c.id == "has_pcb_samples")
        assert pcb_check.status == "not_applicable"

    async def test_critical_actions_block_readiness(self, db_session, admin_user):
        """Open critical actions prevent readiness."""
        building = _make_building(db_session, admin_user)
        diag = _make_diagnostic(db_session, building)
        _make_sample(db_session, diag, pollutant_type="asbestos")

        db_session.add(
            ActionItem(
                id=uuid.uuid4(),
                building_id=building.id,
                source_type="risk",
                action_type="notify_suva",
                title="Notify SUVA",
                priority="critical",
                status="open",
            )
        )
        await db_session.commit()

        result = await evaluate_completeness(db_session, building.id, "avt")
        action_check = next(c for c in result.checks if c.id == "no_critical_actions")
        assert action_check.status == "missing"

    async def test_building_not_found(self, db_session):
        """Non-existent building returns zero score."""
        fake_id = uuid.uuid4()
        result = await evaluate_completeness(db_session, fake_id, "avt")
        assert result.overall_score == 0.0
        assert "Building not found" in result.missing_items

    async def test_samples_missing_lab_results(self, db_session, admin_user):
        """Samples without concentration/unit are flagged."""
        building = _make_building(db_session, admin_user)
        diag = _make_diagnostic(db_session, building)
        _make_sample(db_session, diag, pollutant_type="asbestos", concentration=None, unit=None)
        await db_session.commit()

        result = await evaluate_completeness(db_session, building.id, "avt")
        lab_check = next(c for c in result.checks if c.id == "has_lab_results")
        assert lab_check.status == "partial"

    async def test_lead_cutoff_year(self, db_session, admin_user):
        """Lead samples not required for post-2006 buildings."""
        building = _make_building(db_session, admin_user, construction_year=2010)
        _make_diagnostic(db_session, building)
        await db_session.commit()

        result = await evaluate_completeness(db_session, building.id, "avt")
        lead_check = next(c for c in result.checks if c.id == "has_lead_samples")
        assert lead_check.status == "not_applicable"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCompletenessAPI:
    """Completeness API endpoint tests."""

    async def test_api_returns_valid_response(self, client, auth_headers, sample_building):
        """GET /buildings/{id}/completeness returns valid CompletenessResult."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/completeness?stage=avt",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "building_id" in body
        assert "overall_score" in body
        assert "checks" in body
        assert "missing_items" in body
        assert "ready_to_proceed" in body
        assert "evaluated_at" in body
        assert body["workflow_stage"] == "avt"
        assert isinstance(body["overall_score"], float)
        assert isinstance(body["checks"], list)

    async def test_api_404_for_unknown_building(self, client, auth_headers):
        """Returns 404 for non-existent building."""
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/buildings/{fake_id}/completeness?stage=avt",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_api_invalid_stage(self, client, auth_headers, sample_building):
        """Returns 422 for invalid stage parameter."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/completeness?stage=invalid",
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_api_default_stage(self, client, auth_headers, sample_building):
        """Default stage is avt when not specified."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/completeness",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["workflow_stage"] == "avt"

    async def test_api_checks_have_expected_fields(self, client, auth_headers, sample_building):
        """Each check has id, category, label_key, status, weight."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/completeness?stage=avt",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        for check in resp.json()["checks"]:
            assert "id" in check
            assert "category" in check
            assert "label_key" in check
            assert "status" in check
            assert "weight" in check
            assert check["status"] in ("complete", "missing", "partial", "not_applicable")
