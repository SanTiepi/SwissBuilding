"""Tests for warranty obligations module."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.warranty_obligations_service import (
    get_building_warranty_report,
    get_defect_summary,
    get_obligations_schedule,
    get_portfolio_warranty_overview,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_intervention(
    building_id,
    *,
    status="completed",
    date_end=None,
    contractor_name="Sanacore AG",
    intervention_type="remediation",
):
    return Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type=intervention_type,
        title="Test intervention",
        status=status,
        date_end=date_end,
        contractor_name=contractor_name,
    )


def _make_diagnostic(building_id, *, diagnostic_type="asbestos", date_inspection=None):
    return Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type=diagnostic_type,
        status="completed",
        date_inspection=date_inspection,
    )


def _make_sample(diagnostic_id, *, pollutant_type="asbestos", threshold_exceeded=True):
    return Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number="S-001",
        pollutant_type=pollutant_type,
        threshold_exceeded=threshold_exceeded,
    )


def _make_action(
    building_id,
    *,
    source_type="intervention",
    action_type="remediation",
    priority="high",
    status="open",
    title="Defect found",
):
    return ActionItem(
        id=uuid.uuid4(),
        building_id=building_id,
        source_type=source_type,
        action_type=action_type,
        priority=priority,
        status=status,
        title=title,
    )


# ---------------------------------------------------------------------------
# Service tests — get_building_warranty_report
# ---------------------------------------------------------------------------


class TestGetBuildingWarrantyReport:
    @pytest.mark.asyncio
    async def test_returns_none_for_missing_building(self, db_session):
        result = await get_building_warranty_report(uuid.uuid4(), db_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_warranties_when_no_interventions(self, db_session, sample_building):
        result = await get_building_warranty_report(sample_building.id, db_session)
        assert result is not None
        assert result.warranties == []
        assert result.total_active == 0
        assert result.coverage_score == 1.0

    @pytest.mark.asyncio
    async def test_generates_three_warranties_per_intervention(self, db_session, sample_building):
        intv = _make_intervention(sample_building.id, date_end=date.today() - timedelta(days=30))
        db_session.add(intv)
        await db_session.commit()

        result = await get_building_warranty_report(sample_building.id, db_session)
        assert result is not None
        assert len(result.warranties) == 3
        types = {w.warranty_type for w in result.warranties}
        assert types == {"defect_liability", "material_guarantee", "workmanship"}

    @pytest.mark.asyncio
    async def test_warranty_status_active(self, db_session, sample_building):
        intv = _make_intervention(sample_building.id, date_end=date.today())
        db_session.add(intv)
        await db_session.commit()

        result = await get_building_warranty_report(sample_building.id, db_session)
        # All warranties should be active (just started today)
        for w in result.warranties:
            assert w.status in ("active", "expiring_soon")

    @pytest.mark.asyncio
    async def test_warranty_status_expired(self, db_session, sample_building):
        intv = _make_intervention(sample_building.id, date_end=date.today() - timedelta(days=2000))
        db_session.add(intv)
        await db_session.commit()

        result = await get_building_warranty_report(sample_building.id, db_session)
        expired = [w for w in result.warranties if w.status == "expired"]
        assert len(expired) >= 1  # At least workmanship expired

    @pytest.mark.asyncio
    async def test_asbestos_material_guarantee_is_60_months(self, db_session, sample_building):
        diag = _make_diagnostic(sample_building.id, diagnostic_type="asbestos")
        intv = _make_intervention(sample_building.id, date_end=date.today())
        db_session.add_all([diag, intv])
        await db_session.commit()

        result = await get_building_warranty_report(sample_building.id, db_session)
        mg = [w for w in result.warranties if w.warranty_type == "material_guarantee"]
        assert len(mg) == 1
        assert mg[0].duration_months == 60

    @pytest.mark.asyncio
    async def test_non_asbestos_material_guarantee_is_36_months(self, db_session, sample_building):
        intv = _make_intervention(sample_building.id, date_end=date.today())
        db_session.add(intv)
        await db_session.commit()

        result = await get_building_warranty_report(sample_building.id, db_session)
        mg = [w for w in result.warranties if w.warranty_type == "material_guarantee"]
        assert len(mg) == 1
        assert mg[0].duration_months == 36

    @pytest.mark.asyncio
    async def test_coverage_score_calculation(self, db_session, sample_building):
        # 2 interventions, both recent → active warranties → score capped at 1.0
        i1 = _make_intervention(sample_building.id, date_end=date.today())
        i2 = _make_intervention(sample_building.id, date_end=date.today())
        db_session.add_all([i1, i2])
        await db_session.commit()

        result = await get_building_warranty_report(sample_building.id, db_session)
        assert result.coverage_score <= 1.0

    @pytest.mark.asyncio
    async def test_skips_non_completed_interventions(self, db_session, sample_building):
        intv = _make_intervention(sample_building.id, status="in_progress")
        db_session.add(intv)
        await db_session.commit()

        result = await get_building_warranty_report(sample_building.id, db_session)
        assert result.warranties == []


# ---------------------------------------------------------------------------
# Service tests — get_obligations_schedule
# ---------------------------------------------------------------------------


class TestGetObligationsSchedule:
    @pytest.mark.asyncio
    async def test_returns_none_for_missing_building(self, db_session):
        result = await get_obligations_schedule(uuid.uuid4(), db_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_obligations_when_clean(self, db_session, sample_building):
        result = await get_obligations_schedule(sample_building.id, db_session)
        assert result is not None
        assert result.obligations == []
        assert result.total_obligations == 0

    @pytest.mark.asyncio
    async def test_asbestos_exceeded_creates_air_monitoring(self, db_session, sample_building):
        diag = _make_diagnostic(
            sample_building.id,
            diagnostic_type="asbestos",
            date_inspection=date.today() - timedelta(days=400),
        )
        db_session.add(diag)
        await db_session.flush()
        sample = _make_sample(diag.id, pollutant_type="asbestos", threshold_exceeded=True)
        db_session.add(sample)
        await db_session.commit()

        result = await get_obligations_schedule(sample_building.id, db_session)
        air_obs = [o for o in result.obligations if o.obligation_type == "air_monitoring"]
        assert len(air_obs) == 1
        assert air_obs[0].pollutant_type == "asbestos"
        assert air_obs[0].frequency_months == 12

    @pytest.mark.asyncio
    async def test_pcb_exceeded_creates_surface_testing(self, db_session, sample_building):
        diag = _make_diagnostic(sample_building.id, diagnostic_type="pcb")
        db_session.add(diag)
        await db_session.flush()
        sample = _make_sample(diag.id, pollutant_type="pcb", threshold_exceeded=True)
        db_session.add(sample)
        await db_session.commit()

        result = await get_obligations_schedule(sample_building.id, db_session)
        surf = [o for o in result.obligations if o.obligation_type == "surface_testing"]
        assert len(surf) == 1
        assert surf[0].frequency_months == 24

    @pytest.mark.asyncio
    async def test_completed_intervention_creates_maintenance_check(self, db_session, sample_building):
        intv = _make_intervention(sample_building.id, date_end=date.today() - timedelta(days=30))
        db_session.add(intv)
        await db_session.commit()

        result = await get_obligations_schedule(sample_building.id, db_session)
        maint = [o for o in result.obligations if o.obligation_type == "maintenance_check"]
        assert len(maint) == 1

    @pytest.mark.asyncio
    async def test_overdue_detection(self, db_session, sample_building):
        diag = _make_diagnostic(
            sample_building.id,
            diagnostic_type="asbestos",
            date_inspection=date.today() - timedelta(days=500),
        )
        db_session.add(diag)
        await db_session.flush()
        sample = _make_sample(diag.id, threshold_exceeded=True)
        db_session.add(sample)
        await db_session.commit()

        result = await get_obligations_schedule(sample_building.id, db_session)
        assert result.overdue_count >= 1

    @pytest.mark.asyncio
    async def test_no_obligation_when_threshold_not_exceeded(self, db_session, sample_building):
        diag = _make_diagnostic(sample_building.id, diagnostic_type="asbestos")
        db_session.add(diag)
        await db_session.flush()
        sample = _make_sample(diag.id, threshold_exceeded=False)
        db_session.add(sample)
        await db_session.commit()

        result = await get_obligations_schedule(sample_building.id, db_session)
        assert result.total_obligations == 0


# ---------------------------------------------------------------------------
# Service tests — get_defect_summary
# ---------------------------------------------------------------------------


class TestGetDefectSummary:
    @pytest.mark.asyncio
    async def test_returns_none_for_missing_building(self, db_session):
        result = await get_defect_summary(uuid.uuid4(), db_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_claims_when_no_actions(self, db_session, sample_building):
        result = await get_defect_summary(sample_building.id, db_session)
        assert result is not None
        assert result.total_claims == 0
        assert result.resolution_rate == 0.0

    @pytest.mark.asyncio
    async def test_intervention_source_creates_claim(self, db_session, sample_building):
        action = _make_action(sample_building.id, source_type="intervention")
        db_session.add(action)
        await db_session.commit()

        result = await get_defect_summary(sample_building.id, db_session)
        assert result.total_claims == 1

    @pytest.mark.asyncio
    async def test_defect_action_type_creates_claim(self, db_session, sample_building):
        action = _make_action(
            sample_building.id,
            source_type="diagnostic",
            action_type="defect_repair",
        )
        db_session.add(action)
        await db_session.commit()

        result = await get_defect_summary(sample_building.id, db_session)
        assert result.total_claims == 1

    @pytest.mark.asyncio
    async def test_severity_mapping(self, db_session, sample_building):
        a1 = _make_action(sample_building.id, priority="critical")
        a2 = _make_action(sample_building.id, priority="high")
        a3 = _make_action(sample_building.id, priority="low")
        db_session.add_all([a1, a2, a3])
        await db_session.commit()

        result = await get_defect_summary(sample_building.id, db_session)
        severities = {c.severity for c in result.claims}
        assert "critical" in severities
        assert "major" in severities
        assert "minor" in severities

    @pytest.mark.asyncio
    async def test_resolution_rate(self, db_session, sample_building):
        a1 = _make_action(sample_building.id, status="completed")
        a2 = _make_action(sample_building.id, status="open")
        db_session.add_all([a1, a2])
        await db_session.commit()

        result = await get_defect_summary(sample_building.id, db_session)
        assert result.total_claims == 2
        assert result.resolution_rate == 0.5

    @pytest.mark.asyncio
    async def test_non_defect_action_ignored(self, db_session, sample_building):
        action = _make_action(
            sample_building.id,
            source_type="diagnostic",
            action_type="sampling",
        )
        db_session.add(action)
        await db_session.commit()

        result = await get_defect_summary(sample_building.id, db_session)
        assert result.total_claims == 0


# ---------------------------------------------------------------------------
# Service tests — get_portfolio_warranty_overview
# ---------------------------------------------------------------------------


class TestGetPortfolioWarrantyOverview:
    @pytest.mark.asyncio
    async def test_returns_none_for_missing_org(self, db_session):
        result = await get_portfolio_warranty_overview(uuid.uuid4(), db_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_org(self, db_session):
        org = Organization(
            id=uuid.uuid4(),
            name="Test Org",
            type="diagnostic_lab",
        )
        db_session.add(org)
        await db_session.commit()

        result = await get_portfolio_warranty_overview(org.id, db_session)
        assert result is not None
        assert result.total_buildings == 0

    @pytest.mark.asyncio
    async def test_aggregates_buildings(self, db_session):
        org = Organization(id=uuid.uuid4(), name="Test Org", type="diagnostic_lab")
        db_session.add(org)
        await db_session.flush()

        user = User(
            id=uuid.uuid4(),
            email="wo@test.ch",
            password_hash="hash",
            first_name="A",
            last_name="B",
            role="admin",
            is_active=True,
            language="fr",
            organization_id=org.id,
        )
        db_session.add(user)
        await db_session.flush()

        bldg = Building(
            id=uuid.uuid4(),
            address="Rue Test 10",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=1960,
            building_type="residential",
            created_by=user.id,
            status="active",
        )
        db_session.add(bldg)
        await db_session.flush()

        intv = _make_intervention(bldg.id, date_end=date.today())
        db_session.add(intv)
        await db_session.commit()

        result = await get_portfolio_warranty_overview(org.id, db_session)
        assert result.total_buildings == 1
        assert result.total_active_warranties >= 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestWarrantyObligationsAPI:
    @pytest.mark.asyncio
    async def test_warranties_endpoint(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/warranty-obligations/buildings/{sample_building.id}/warranties",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "warranties" in data
        assert "coverage_score" in data

    @pytest.mark.asyncio
    async def test_warranties_404(self, client, auth_headers):
        resp = await client.get(
            f"/api/v1/warranty-obligations/buildings/{uuid.uuid4()}/warranties",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_obligations_endpoint(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/warranty-obligations/buildings/{sample_building.id}/obligations",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "obligations" in data
        assert "overdue_count" in data

    @pytest.mark.asyncio
    async def test_defects_endpoint(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/warranty-obligations/buildings/{sample_building.id}/defects",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "claims" in data
        assert "resolution_rate" in data

    @pytest.mark.asyncio
    async def test_overview_endpoint(self, client, auth_headers, db_session):
        org = Organization(id=uuid.uuid4(), name="Test Org", type="diagnostic_lab")
        db_session.add(org)
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/warranty-obligations/organizations/{org.id}/overview",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_buildings" in data

    @pytest.mark.asyncio
    async def test_overview_404(self, client, auth_headers):
        resp = await client.get(
            f"/api/v1/warranty-obligations/organizations/{uuid.uuid4()}/overview",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client, sample_building):
        resp = await client.get(
            f"/api/v1/warranty-obligations/buildings/{sample_building.id}/warranties",
        )
        assert resp.status_code in (401, 403)
