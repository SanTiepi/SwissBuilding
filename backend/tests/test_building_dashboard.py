"""Tests for the Building Dashboard aggregate service and API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_snapshot import BuildingSnapshot
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.unknown_issue import UnknownIssue
from app.models.zone import Zone
from app.schemas.building_dashboard import (
    DashboardActivitySummary,
    DashboardAlertsSummary,
    DashboardCompletenessSummary,
    DashboardComplianceSummary,
    DashboardReadinessSummary,
    DashboardRiskSummary,
    DashboardTrustSummary,
)
from app.services.building_dashboard_service import (
    get_building_dashboard,
    get_buildings_dashboard_list,
    get_dashboard_quick,
)

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": admin_user.id,
        "owner_id": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_intervention(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "intervention_type": "asbestos_removal",
        "title": "Test Intervention",
        "status": "planned",
    }
    defaults.update(kwargs)
    i = Intervention(**defaults)
    db.add(i)
    await db.flush()
    return i


async def _create_document(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "file_name": "test.pdf",
        "file_path": "/test/path.pdf",
        "document_type": "lab_report",
    }
    defaults.update(kwargs)
    d = Document(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_action(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "title": "Test Action",
        "action_type": "diagnostic",
        "source_type": "manual",
        "priority": "medium",
        "status": "open",
    }
    defaults.update(kwargs)
    a = ActionItem(**defaults)
    db.add(a)
    await db.flush()
    return a


async def _create_zone(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "name": "Floor 1",
        "zone_type": "floor",
    }
    defaults.update(kwargs)
    z = Zone(**defaults)
    db.add(z)
    await db.flush()
    return z


async def _create_snapshot(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "snapshot_type": "manual",
        "passport_grade": "B",
        "overall_trust": 0.75,
        "completeness_score": 0.80,
        "captured_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    s = BuildingSnapshot(**defaults)
    db.add(s)
    await db.flush()
    return s


async def _create_risk_score(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "asbestos_probability": 0.8,
        "pcb_probability": 0.3,
        "lead_probability": 0.1,
        "hap_probability": 0.05,
        "radon_probability": 0.02,
        "overall_risk_level": "high",
        "confidence": 0.7,
    }
    defaults.update(kwargs)
    r = BuildingRiskScore(**defaults)
    db.add(r)
    await db.flush()
    return r


async def _create_unknown(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "unknown_type": "missing_data",
        "severity": "medium",
        "status": "open",
        "title": "Test Unknown",
    }
    defaults.update(kwargs)
    u = UnknownIssue(**defaults)
    db.add(u)
    await db.flush()
    return u


async def _create_quality_issue(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "issue_type": "missing_field",
        "severity": "medium",
        "status": "open",
        "description": "Missing field",
    }
    defaults.update(kwargs)
    qi = DataQualityIssue(**defaults)
    db.add(qi)
    await db.flush()
    return qi


# ── Service Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dashboard_building_not_found(db_session, admin_user):
    """Dashboard returns None for a non-existent building."""
    result = await get_building_dashboard(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_dashboard_empty_building(db_session, admin_user):
    """Dashboard for a building with no data returns zeroed summaries."""
    b = await _create_building(db_session, admin_user)
    await db_session.commit()

    result = await get_building_dashboard(db_session, b.id)
    assert result is not None
    assert result.building_id == b.id
    assert result.address == "Rue Test 1"
    assert result.city == "Lausanne"
    assert result.canton == "VD"
    assert result.passport_grade is None
    assert result.activity.total_diagnostics == 0
    assert result.activity.completed_diagnostics == 0
    assert result.activity.total_interventions == 0
    assert result.activity.open_actions == 0
    assert result.activity.total_documents == 0
    assert result.activity.total_zones == 0
    assert result.activity.total_samples == 0
    assert result.alerts.open_unknowns == 0


@pytest.mark.asyncio
async def test_dashboard_with_diagnostics(db_session, admin_user):
    """Dashboard correctly counts diagnostics."""
    b = await _create_building(db_session, admin_user)
    await _create_diagnostic(db_session, b.id, status="completed")
    await _create_diagnostic(db_session, b.id, status="draft")
    await _create_diagnostic(db_session, b.id, status="validated")
    await db_session.commit()

    result = await get_building_dashboard(db_session, b.id)
    assert result.activity.total_diagnostics == 3
    assert result.activity.completed_diagnostics == 2  # completed + validated


@pytest.mark.asyncio
async def test_dashboard_with_interventions(db_session, admin_user):
    """Dashboard correctly counts interventions."""
    b = await _create_building(db_session, admin_user)
    await _create_intervention(db_session, b.id, status="in_progress")
    await _create_intervention(db_session, b.id, status="planned")
    await _create_intervention(db_session, b.id, status="completed")
    await db_session.commit()

    result = await get_building_dashboard(db_session, b.id)
    assert result.activity.total_interventions == 3
    assert result.activity.active_interventions == 2  # in_progress + planned


@pytest.mark.asyncio
async def test_dashboard_with_documents(db_session, admin_user):
    """Dashboard correctly counts documents."""
    b = await _create_building(db_session, admin_user)
    await _create_document(db_session, b.id)
    await _create_document(db_session, b.id, file_name="report2.pdf")
    await db_session.commit()

    result = await get_building_dashboard(db_session, b.id)
    assert result.activity.total_documents == 2


@pytest.mark.asyncio
async def test_dashboard_with_open_actions(db_session, admin_user):
    """Dashboard correctly counts open actions."""
    b = await _create_building(db_session, admin_user)
    await _create_action(db_session, b.id, status="open")
    await _create_action(db_session, b.id, status="open")
    await _create_action(db_session, b.id, status="completed")
    await db_session.commit()

    result = await get_building_dashboard(db_session, b.id)
    assert result.activity.open_actions == 2


@pytest.mark.asyncio
async def test_dashboard_with_zones(db_session, admin_user):
    """Dashboard correctly counts zones."""
    b = await _create_building(db_session, admin_user)
    await _create_zone(db_session, b.id, name="Floor 1")
    await _create_zone(db_session, b.id, name="Floor 2")
    await _create_zone(db_session, b.id, name="Basement")
    await db_session.commit()

    result = await get_building_dashboard(db_session, b.id)
    assert result.activity.total_zones == 3


@pytest.mark.asyncio
async def test_dashboard_with_snapshot(db_session, admin_user):
    """Dashboard picks up grade and trust from latest snapshot."""
    b = await _create_building(db_session, admin_user)
    await _create_snapshot(db_session, b.id, passport_grade="C", overall_trust=0.65)
    await db_session.commit()

    result = await get_building_dashboard(db_session, b.id)
    assert result.passport_grade == "C"
    assert result.trust.score == 0.65
    assert result.trust.level == "medium"


@pytest.mark.asyncio
async def test_dashboard_with_risk_score(db_session, admin_user):
    """Dashboard picks up risk information."""
    b = await _create_building(db_session, admin_user)
    await _create_risk_score(db_session, b.id, overall_risk_level="high", asbestos_probability=0.9)
    await db_session.commit()

    result = await get_building_dashboard(db_session, b.id)
    assert result.risk.risk_level == "high"
    assert result.risk.risk_score == 0.9
    assert result.risk.pollutant_risks is not None
    assert result.risk.pollutant_risks["asbestos"] == "critical"


@pytest.mark.asyncio
async def test_dashboard_with_unknowns(db_session, admin_user):
    """Dashboard counts open unknowns."""
    b = await _create_building(db_session, admin_user)
    await _create_unknown(db_session, b.id, status="open")
    await _create_unknown(db_session, b.id, status="open")
    await _create_unknown(db_session, b.id, status="resolved")
    await db_session.commit()

    result = await get_building_dashboard(db_session, b.id)
    assert result.alerts.open_unknowns == 2


@pytest.mark.asyncio
async def test_dashboard_trust_level_high(db_session, admin_user):
    """Trust level 'high' for score >= 0.7."""
    b = await _create_building(db_session, admin_user)
    await _create_snapshot(db_session, b.id, overall_trust=0.85)
    await db_session.commit()

    result = await get_building_dashboard(db_session, b.id)
    assert result.trust.level == "high"


@pytest.mark.asyncio
async def test_dashboard_trust_level_low(db_session, admin_user):
    """Trust level 'low' for score < 0.4."""
    b = await _create_building(db_session, admin_user)
    await _create_snapshot(db_session, b.id, overall_trust=0.2)
    await db_session.commit()

    result = await get_building_dashboard(db_session, b.id)
    assert result.trust.level == "low"


# ── Batch Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_batch_dashboards(db_session, admin_user):
    """Batch dashboard returns results for multiple buildings."""
    b1 = await _create_building(db_session, admin_user, address="Rue A 1")
    b2 = await _create_building(db_session, admin_user, address="Rue B 2")
    await db_session.commit()

    results = await get_buildings_dashboard_list(db_session, [b1.id, b2.id])
    assert len(results) == 2
    addresses = {r.address for r in results}
    assert "Rue A 1" in addresses
    assert "Rue B 2" in addresses


@pytest.mark.asyncio
async def test_batch_dashboards_skips_missing(db_session, admin_user):
    """Batch dashboard skips non-existent building IDs."""
    b = await _create_building(db_session, admin_user)
    await db_session.commit()

    results = await get_buildings_dashboard_list(db_session, [b.id, uuid.uuid4()])
    assert len(results) == 1


# ── Quick Dashboard Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_quick_dashboard_not_found(db_session, admin_user):
    """Quick dashboard returns None for missing building."""
    result = await get_dashboard_quick(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_quick_dashboard(db_session, admin_user):
    """Quick dashboard returns counts and grade."""
    b = await _create_building(db_session, admin_user)
    await _create_snapshot(db_session, b.id, passport_grade="A", overall_trust=0.9)
    await _create_diagnostic(db_session, b.id, status="completed")
    await _create_document(db_session, b.id)
    await db_session.commit()

    result = await get_dashboard_quick(db_session, b.id)
    assert result is not None
    assert result["passport_grade"] == "A"
    assert result["trust_score"] == 0.9
    assert result["activity"]["total_diagnostics"] == 1
    assert result["activity"]["total_documents"] == 1


# ── API Endpoint Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_dashboard_404(client, auth_headers):
    """API returns 404 for non-existent building."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/dashboard", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_dashboard_success(client, db_session, admin_user, auth_headers):
    """API returns dashboard for existing building."""
    b = await _create_building(db_session, admin_user)
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{b.id}/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(b.id)
    assert "trust" in data
    assert "activity" in data
    assert "alerts" in data


@pytest.mark.asyncio
async def test_api_quick_dashboard_404(client, auth_headers):
    """Quick API returns 404 for non-existent building."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/dashboard/quick", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_quick_dashboard_success(client, db_session, admin_user, auth_headers):
    """Quick API returns data for existing building."""
    b = await _create_building(db_session, admin_user)
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{b.id}/dashboard/quick", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(b.id)
    assert "activity" in data


@pytest.mark.asyncio
async def test_api_batch_dashboards(client, db_session, admin_user, auth_headers):
    """Batch API returns dashboards for valid buildings."""
    b = await _create_building(db_session, admin_user)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/buildings/dashboards",
        json={"building_ids": [str(b.id)]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["building_id"] == str(b.id)


@pytest.mark.asyncio
async def test_api_batch_dashboards_empty(client, auth_headers):
    """Batch API returns empty list for empty input."""
    resp = await client.post(
        "/api/v1/buildings/dashboards",
        json={"building_ids": []},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── Schema Tests ──────────────────────────────────────────────────


def test_dashboard_schema_defaults():
    """All dashboard sub-schemas have correct defaults."""
    trust = DashboardTrustSummary()
    assert trust.score is None
    assert trust.level is None
    assert trust.trend is None

    readiness = DashboardReadinessSummary()
    assert readiness.overall_status is None
    assert readiness.blocked_count == 0

    completeness = DashboardCompletenessSummary()
    assert completeness.overall_score is None
    assert completeness.missing_count == 0

    risk = DashboardRiskSummary()
    assert risk.risk_level is None
    assert risk.pollutant_risks is None

    compliance = DashboardComplianceSummary()
    assert compliance.status is None
    assert compliance.overdue_count == 0
    assert compliance.upcoming_deadlines == 0
    assert compliance.gap_count == 0

    activity = DashboardActivitySummary()
    assert activity.total_diagnostics == 0
    assert activity.total_samples == 0

    alerts = DashboardAlertsSummary()
    assert alerts.weak_signals == 0
    assert alerts.constraint_blockers == 0
    assert alerts.quality_issues == 0
    assert alerts.open_unknowns == 0
