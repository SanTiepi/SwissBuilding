"""Tests for incident_intelligence_service — pattern detection, scoring, correlation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from app.models.building import Building
from app.models.incident import IncidentEpisode
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.zone import Zone
from app.services.incident_intelligence_service import (
    compute_sinistralite_score,
    correlate_incidents_interventions,
    detect_recurring_patterns,
)

# ── Helpers ────────────────────────────────────────────────────────


async def _create_org(db):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="owner",
    )
    db.add(org)
    await db.flush()
    return org


async def _create_building(db, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _create_zone(db, building_id):
    z = Zone(
        id=uuid.uuid4(),
        building_id=building_id,
        zone_type="floor",
        name="Ground floor",
    )
    db.add(z)
    await db.flush()
    return z


async def _create_incident(
    db,
    building_id,
    org_id,
    *,
    incident_type="leak",
    severity="minor",
    zone_id=None,
    discovered_at=None,
    resolved_at=None,
    recurring=False,
    title="Test Incident",
):
    inc = IncidentEpisode(
        id=uuid.uuid4(),
        building_id=building_id,
        organization_id=org_id,
        incident_type=incident_type,
        severity=severity,
        zone_id=zone_id,
        discovered_at=discovered_at or datetime.utcnow(),
        resolved_at=resolved_at,
        recurring=recurring,
        title=title,
    )
    db.add(inc)
    await db.flush()
    return inc


async def _create_intervention(
    db,
    building_id,
    *,
    intervention_type="remediation",
    date_start=None,
    date_end=None,
    title="Test Intervention",
):
    intv = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type=intervention_type,
        title=title,
        status="completed",
        date_start=date_start,
        date_end=date_end,
    )
    db.add(intv)
    await db.flush()
    return intv


# ── Recurring Pattern Tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_no_incidents_no_patterns(db_session, admin_user):
    """Building with no incidents → empty patterns."""
    building = await _create_building(db_session, admin_user)
    patterns = await detect_recurring_patterns(db_session, building.id)
    assert patterns == []


@pytest.mark.asyncio
async def test_single_incident_no_pattern(db_session, admin_user):
    """Single incident → no recurring pattern."""
    building = await _create_building(db_session, admin_user)
    org = await _create_org(db_session)
    await _create_incident(db_session, building.id, org.id, incident_type="leak")

    patterns = await detect_recurring_patterns(db_session, building.id)
    assert patterns == []


@pytest.mark.asyncio
async def test_two_same_type_detected(db_session, admin_user):
    """Two leaks in same zone → recurring pattern detected."""
    building = await _create_building(db_session, admin_user)
    org = await _create_org(db_session)
    zone = await _create_zone(db_session, building.id)

    now = datetime.utcnow()
    await _create_incident(
        db_session,
        building.id,
        org.id,
        incident_type="leak",
        zone_id=zone.id,
        discovered_at=now - timedelta(days=30),
    )
    await _create_incident(
        db_session,
        building.id,
        org.id,
        incident_type="leak",
        zone_id=zone.id,
        discovered_at=now,
    )

    patterns = await detect_recurring_patterns(db_session, building.id)
    assert len(patterns) == 1
    assert patterns[0]["type"] == "leak"
    assert patterns[0]["count"] == 2


@pytest.mark.asyncio
async def test_severity_trend_worsening(db_session, admin_user):
    """Incidents with escalating severity → worsening trend."""
    building = await _create_building(db_session, admin_user)
    org = await _create_org(db_session)
    zone = await _create_zone(db_session, building.id)

    now = datetime.utcnow()
    await _create_incident(
        db_session,
        building.id,
        org.id,
        incident_type="mold",
        zone_id=zone.id,
        severity="minor",
        discovered_at=now - timedelta(days=300),
    )
    await _create_incident(
        db_session,
        building.id,
        org.id,
        incident_type="mold",
        zone_id=zone.id,
        severity="minor",
        discovered_at=now - timedelta(days=200),
    )
    await _create_incident(
        db_session,
        building.id,
        org.id,
        incident_type="mold",
        zone_id=zone.id,
        severity="major",
        discovered_at=now - timedelta(days=100),
    )
    await _create_incident(
        db_session,
        building.id,
        org.id,
        incident_type="mold",
        zone_id=zone.id,
        severity="critical",
        discovered_at=now,
    )

    patterns = await detect_recurring_patterns(db_session, building.id)
    assert len(patterns) == 1
    assert patterns[0]["severity_trend"] == "worsening"


# ── Sinistralite Score Tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_score_no_incidents(db_session, admin_user):
    """No incidents → score 0, grade A."""
    building = await _create_building(db_session, admin_user)
    result = await compute_sinistralite_score(db_session, building.id)
    assert result["score"] == 0
    assert result["grade"] == "A"
    assert result["top_issues"] == []


@pytest.mark.asyncio
async def test_score_single_minor(db_session, admin_user):
    """Single minor resolved incident → low score."""
    building = await _create_building(db_session, admin_user)
    org = await _create_org(db_session)
    now = datetime.utcnow()
    await _create_incident(
        db_session,
        building.id,
        org.id,
        severity="minor",
        discovered_at=now - timedelta(days=10),
        resolved_at=now,
    )

    result = await compute_sinistralite_score(db_session, building.id)
    assert 0 < result["score"] < 30
    assert result["grade"] in ("A", "B")


@pytest.mark.asyncio
async def test_score_many_critical_unresolved(db_session, admin_user):
    """Many critical unresolved incidents → high score, bad grade."""
    building = await _create_building(db_session, admin_user)
    org = await _create_org(db_session)
    now = datetime.utcnow()

    for i in range(10):
        await _create_incident(
            db_session,
            building.id,
            org.id,
            severity="critical",
            recurring=True,
            discovered_at=now - timedelta(days=i * 30),
            title=f"Critical incident {i}",
        )

    result = await compute_sinistralite_score(db_session, building.id)
    assert result["score"] >= 70
    assert result["grade"] in ("D", "E", "F")
    assert len(result["top_issues"]) <= 5


@pytest.mark.asyncio
async def test_score_range_0_100(db_session, admin_user):
    """Score always between 0 and 100."""
    building = await _create_building(db_session, admin_user)
    org = await _create_org(db_session)

    for i in range(5):
        await _create_incident(
            db_session,
            building.id,
            org.id,
            severity="moderate",
            discovered_at=datetime.utcnow() - timedelta(days=i * 10),
        )

    result = await compute_sinistralite_score(db_session, building.id)
    assert 0 <= result["score"] <= 100


@pytest.mark.asyncio
async def test_score_breakdown_present(db_session, admin_user):
    """Score result contains all breakdown fields."""
    building = await _create_building(db_session, admin_user)
    org = await _create_org(db_session)
    await _create_incident(db_session, building.id, org.id)

    result = await compute_sinistralite_score(db_session, building.id)
    breakdown = result["breakdown"]
    assert "incident_count_score" in breakdown
    assert "severity_score" in breakdown
    assert "recurrence_score" in breakdown
    assert "resolution_score" in breakdown


# ── Correlation Tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_correlation_no_data(db_session, admin_user):
    """No incidents or interventions → empty correlation."""
    building = await _create_building(db_session, admin_user)
    result = await correlate_incidents_interventions(db_session, building.id)
    assert result == []


@pytest.mark.asyncio
async def test_correlation_resolved(db_session, admin_user):
    """Incidents stop after intervention → effectiveness 'resolved'."""
    building = await _create_building(db_session, admin_user)
    org = await _create_org(db_session)

    base = datetime(2024, 1, 1)

    # 3 leaks before intervention
    for i in range(3):
        await _create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="leak",
            discovered_at=base + timedelta(days=i * 30),
        )

    # Intervention in June 2024
    await _create_intervention(
        db_session,
        building.id,
        date_start=base + timedelta(days=150),
        date_end=base + timedelta(days=160),
        title="Pipe repair",
    )
    # No leaks after

    result = await correlate_incidents_interventions(db_session, building.id)
    leak_corr = [c for c in result if c["incident_type"] == "leak"]
    assert len(leak_corr) == 1
    assert leak_corr[0]["incidents_before"] == 3
    assert leak_corr[0]["incidents_after"] == 0
    assert leak_corr[0]["effectiveness"] == "resolved"


@pytest.mark.asyncio
async def test_correlation_improved(db_session, admin_user):
    """Fewer incidents after intervention → 'improved'."""
    building = await _create_building(db_session, admin_user)
    org = await _create_org(db_session)

    base = datetime(2024, 1, 1)

    # 3 mold before
    for i in range(3):
        await _create_incident(
            db_session,
            building.id,
            org.id,
            incident_type="mold",
            discovered_at=base + timedelta(days=i * 30),
        )

    # Intervention
    await _create_intervention(
        db_session,
        building.id,
        date_start=base + timedelta(days=100),
        date_end=base + timedelta(days=110),
        title="Mold treatment",
    )

    # 1 mold after
    await _create_incident(
        db_session,
        building.id,
        org.id,
        incident_type="mold",
        discovered_at=base + timedelta(days=200),
    )

    result = await correlate_incidents_interventions(db_session, building.id)
    mold_corr = [c for c in result if c["incident_type"] == "mold"]
    assert len(mold_corr) == 1
    assert mold_corr[0]["effectiveness"] == "improved"
