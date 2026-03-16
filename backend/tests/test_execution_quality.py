"""Tests for execution quality module."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.user import User
from app.services.execution_quality_service import (
    evaluate_intervention_quality,
    get_acceptance_criteria,
    get_building_acceptance_report,
    get_portfolio_quality_dashboard,
)

# ── Helpers ──────────────────────────────────────────────────────────


async def _create_org(db: AsyncSession) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="diagnostic_lab",
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def _create_user_with_org(db: AsyncSession, org_id: uuid.UUID) -> User:
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email=f"user-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_building(db: AsyncSession, created_by: uuid.UUID) -> Building:
    building = Building(
        id=uuid.uuid4(),
        address="Rue Test 99",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=created_by,
        status="active",
    )
    db.add(building)
    await db.commit()
    await db.refresh(building)
    return building


async def _create_intervention(
    db: AsyncSession,
    building_id: uuid.UUID,
    intervention_type: str = "removal",
    status: str = "completed",
) -> Intervention:
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type=intervention_type,
        title=f"Test {intervention_type}",
        status=status,
        created_at=datetime.now(UTC),
    )
    db.add(intervention)
    await db.commit()
    await db.refresh(intervention)
    return intervention


# ── FN1: evaluate_intervention_quality ───────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_no_intervention(db_session: AsyncSession):
    """Returns None when intervention does not exist."""
    result = await evaluate_intervention_quality(uuid.uuid4(), db_session)
    assert result is None


@pytest.mark.asyncio
async def test_evaluate_completed_removal(db_session: AsyncSession, sample_building: Building):
    """Completed removal intervention has visual_inspection + air_measurement, all passed."""
    iv = await _create_intervention(db_session, sample_building.id, "removal", "completed")
    report = await evaluate_intervention_quality(iv.id, db_session)
    assert report is not None
    assert report.intervention_type == "removal"
    assert report.overall_status == "acceptable"
    assert report.pass_rate == 1.0
    assert len(report.quality_checks) == 2
    check_types = {c.check_type for c in report.quality_checks}
    assert check_types == {"visual_inspection", "air_measurement"}


@pytest.mark.asyncio
async def test_evaluate_in_progress_containment(db_session: AsyncSession, sample_building: Building):
    """In-progress containment has pending checks."""
    iv = await _create_intervention(db_session, sample_building.id, "containment", "in_progress")
    report = await evaluate_intervention_quality(iv.id, db_session)
    assert report is not None
    assert report.overall_status == "pending"
    assert report.pass_rate == 0.0
    check_types = {c.check_type for c in report.quality_checks}
    assert check_types == {"visual_inspection", "surface_test"}


@pytest.mark.asyncio
async def test_evaluate_cancelled_intervention(db_session: AsyncSession, sample_building: Building):
    """Cancelled intervention has waived checks."""
    iv = await _create_intervention(db_session, sample_building.id, "removal", "cancelled")
    report = await evaluate_intervention_quality(iv.id, db_session)
    assert report is not None
    assert all(c.status == "waived" for c in report.quality_checks)


@pytest.mark.asyncio
async def test_evaluate_monitoring_type(db_session: AsyncSession, sample_building: Building):
    """Monitoring intervention generates lab_verification check."""
    iv = await _create_intervention(db_session, sample_building.id, "monitoring", "completed")
    report = await evaluate_intervention_quality(iv.id, db_session)
    assert report is not None
    assert len(report.quality_checks) == 1
    assert report.quality_checks[0].check_type == "lab_verification"


@pytest.mark.asyncio
async def test_evaluate_encapsulation_type(db_session: AsyncSession, sample_building: Building):
    """Encapsulation generates visual_inspection + air_measurement."""
    iv = await _create_intervention(db_session, sample_building.id, "encapsulation", "completed")
    report = await evaluate_intervention_quality(iv.id, db_session)
    assert report is not None
    assert len(report.quality_checks) == 2
    check_types = {c.check_type for c in report.quality_checks}
    assert check_types == {"visual_inspection", "air_measurement"}


@pytest.mark.asyncio
async def test_evaluate_unknown_type_default_checks(db_session: AsyncSession, sample_building: Building):
    """Unknown intervention type defaults to visual_inspection only."""
    iv = await _create_intervention(db_session, sample_building.id, "custom_work", "completed")
    report = await evaluate_intervention_quality(iv.id, db_session)
    assert report is not None
    assert len(report.quality_checks) == 1
    assert report.quality_checks[0].check_type == "visual_inspection"


# ── FN2: get_acceptance_criteria ─────────────────────────────────────


@pytest.mark.asyncio
async def test_criteria_asbestos():
    """Asbestos returns 2 criteria entries."""
    criteria = await get_acceptance_criteria("asbestos")
    assert len(criteria) == 2
    assert all(c.pollutant_type == "asbestos" for c in criteria)
    refs = {c.regulation_ref for c in criteria}
    assert "VDI 3492" in refs


@pytest.mark.asyncio
async def test_criteria_pcb():
    """PCB returns 1 criteria entry with 50 mg/kg threshold."""
    criteria = await get_acceptance_criteria("pcb")
    assert len(criteria) == 1
    assert criteria[0].threshold_value == 50.0
    assert criteria[0].regulation_ref == "ORRChim Annexe 2.15"


@pytest.mark.asyncio
async def test_criteria_lead():
    """Lead returns 1 criteria entry."""
    criteria = await get_acceptance_criteria("lead")
    assert len(criteria) == 1
    assert criteria[0].threshold_value == 5000.0


@pytest.mark.asyncio
async def test_criteria_hap():
    """HAP returns 1 criteria entry."""
    criteria = await get_acceptance_criteria("hap")
    assert len(criteria) == 1
    assert criteria[0].threshold_value == 50.0


@pytest.mark.asyncio
async def test_criteria_radon():
    """Radon returns 1 criteria entry at 300 Bq/m3."""
    criteria = await get_acceptance_criteria("radon")
    assert len(criteria) == 1
    assert criteria[0].threshold_value == 300.0
    assert criteria[0].regulation_ref == "ORaP Art. 110"


@pytest.mark.asyncio
async def test_criteria_unknown_pollutant():
    """Unknown pollutant type returns empty list."""
    criteria = await get_acceptance_criteria("unknown_substance")
    assert criteria == []


# ── FN3: get_building_acceptance_report ──────────────────────────────


@pytest.mark.asyncio
async def test_acceptance_building_not_found(db_session: AsyncSession):
    """Returns None for non-existent building."""
    result = await get_building_acceptance_report(uuid.uuid4(), db_session)
    assert result is None


@pytest.mark.asyncio
async def test_acceptance_no_interventions(db_session: AsyncSession, sample_building: Building):
    """Building with no interventions returns zero counts."""
    report = await get_building_acceptance_report(sample_building.id, db_session)
    assert report is not None
    assert report.interventions_total == 0
    assert report.acceptance_rate == 0.0


@pytest.mark.asyncio
async def test_acceptance_mixed_statuses(db_session: AsyncSession, sample_building: Building):
    """Building with mixed intervention statuses reports correct counts."""
    await _create_intervention(db_session, sample_building.id, "removal", "completed")
    await _create_intervention(db_session, sample_building.id, "containment", "in_progress")
    await _create_intervention(db_session, sample_building.id, "monitoring", "cancelled")

    report = await get_building_acceptance_report(sample_building.id, db_session)
    assert report is not None
    assert report.interventions_total == 3
    assert report.interventions_accepted == 1
    assert report.interventions_pending == 1
    assert report.interventions_rejected == 1
    assert report.acceptance_rate == pytest.approx(1 / 3)


@pytest.mark.asyncio
async def test_acceptance_all_completed(db_session: AsyncSession, sample_building: Building):
    """All completed interventions give 100% acceptance rate."""
    await _create_intervention(db_session, sample_building.id, "removal", "completed")
    await _create_intervention(db_session, sample_building.id, "containment", "completed")

    report = await get_building_acceptance_report(sample_building.id, db_session)
    assert report is not None
    assert report.acceptance_rate == 1.0


# ── FN4: get_portfolio_quality_dashboard ─────────────────────────────


@pytest.mark.asyncio
async def test_portfolio_empty_org(db_session: AsyncSession):
    """Organization with no users returns empty dashboard."""
    org = await _create_org(db_session)
    dashboard = await get_portfolio_quality_dashboard(org.id, db_session)
    assert dashboard is not None
    assert dashboard.total_interventions == 0
    assert dashboard.by_building == []
    assert dashboard.overall_acceptance_rate == 0.0


@pytest.mark.asyncio
async def test_portfolio_with_buildings(db_session: AsyncSession):
    """Organization with buildings and interventions returns aggregated data."""
    org = await _create_org(db_session)
    user = await _create_user_with_org(db_session, org.id)
    bld = await _create_building(db_session, user.id)
    await _create_intervention(db_session, bld.id, "removal", "completed")
    await _create_intervention(db_session, bld.id, "monitoring", "in_progress")

    dashboard = await get_portfolio_quality_dashboard(org.id, db_session)
    assert dashboard is not None
    assert dashboard.total_interventions == 2
    assert dashboard.overall_acceptance_rate == 0.5
    assert len(dashboard.by_building) == 1
    assert dashboard.by_building[0].building_id == bld.id
    assert dashboard.by_building[0].acceptance_rate == 0.5
    assert dashboard.by_building[0].pending_checks == 1
    assert len(dashboard.trends) == 4


@pytest.mark.asyncio
async def test_portfolio_trends_length(db_session: AsyncSession):
    """Dashboard always returns 4 trend entries."""
    org = await _create_org(db_session)
    _ = await _create_user_with_org(db_session, org.id)
    dashboard = await get_portfolio_quality_dashboard(org.id, db_session)
    assert dashboard is not None
    assert len(dashboard.trends) == 4


# ── API endpoint tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_intervention_report(
    client: AsyncClient, auth_headers: dict, sample_building: Building, db_session: AsyncSession
):
    """GET intervention quality report returns 200."""
    iv = await _create_intervention(db_session, sample_building.id, "removal", "completed")
    resp = await client.get(f"/api/v1/execution-quality/interventions/{iv.id}/report", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["intervention_type"] == "removal"
    assert data["overall_status"] == "acceptable"


@pytest.mark.asyncio
async def test_api_intervention_not_found(client: AsyncClient, auth_headers: dict):
    """GET intervention quality report returns 404 for missing intervention."""
    resp = await client.get(f"/api/v1/execution-quality/interventions/{uuid.uuid4()}/report", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_pollutant_criteria(client: AsyncClient, auth_headers: dict):
    """GET pollutant criteria returns 200."""
    resp = await client.get("/api/v1/execution-quality/pollutants/asbestos/criteria", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_api_building_acceptance(client: AsyncClient, auth_headers: dict, sample_building: Building):
    """GET building acceptance report returns 200."""
    resp = await client.get(
        f"/api/v1/execution-quality/buildings/{sample_building.id}/acceptance", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_building_acceptance_not_found(client: AsyncClient, auth_headers: dict):
    """GET building acceptance returns 404 for missing building."""
    resp = await client.get(f"/api/v1/execution-quality/buildings/{uuid.uuid4()}/acceptance", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_org_dashboard(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    """GET org quality dashboard returns 200."""
    org = await _create_org(db_session)
    resp = await client.get(f"/api/v1/execution-quality/organizations/{org.id}/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_id"] == str(org.id)


@pytest.mark.asyncio
async def test_api_pollutant_criteria_unknown(client: AsyncClient, auth_headers: dict):
    """GET unknown pollutant returns empty list."""
    resp = await client.get("/api/v1/execution-quality/pollutants/unknown_x/criteria", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_evaluate_building_id_matches(db_session: AsyncSession, sample_building: Building):
    """Report building_id matches the intervention's building."""
    iv = await _create_intervention(db_session, sample_building.id, "removal", "completed")
    report = await evaluate_intervention_quality(iv.id, db_session)
    assert report is not None
    assert report.building_id == sample_building.id
