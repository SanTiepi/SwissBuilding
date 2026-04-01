"""Tests for the Readiness Radar Service."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.diagnostic import Diagnostic
from app.models.readiness_assessment import ReadinessAssessment
from app.models.sample import Sample
from app.services.readiness_radar_service import (
    _score_to_grade,
    compute_readiness_radar,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue du Radar 7",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": admin_user.id,
        "owner_id": admin_user.id,
        "status": "active",
        "floors_above": 3,
        "surface_area_m2": 400.0,
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_trust_score(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "overall_score": 0.7,
        "percent_proven": 0.5,
        "percent_inferred": 0.1,
        "percent_declared": 0.2,
        "percent_obsolete": 0.1,
        "percent_contradictory": 0.1,
        "total_data_points": 20,
        "proven_count": 10,
        "inferred_count": 2,
        "declared_count": 4,
        "obsolete_count": 2,
        "contradictory_count": 2,
        "trend": "stable",
        "assessed_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    ts = BuildingTrustScore(**defaults)
    db.add(ts)
    await db.flush()
    return ts


async def _create_risk_score(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "asbestos_probability": 0.5,
        "pcb_probability": 0.3,
        "lead_probability": 0.2,
        "hap_probability": 0.1,
        "radon_probability": 0.05,
        "overall_risk_level": "medium",
        "confidence": 0.6,
    }
    defaults.update(kwargs)
    rs = BuildingRiskScore(**defaults)
    db.add(rs)
    await db.flush()
    return rs


async def _create_readiness(db, building_id, readiness_type, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "readiness_type": readiness_type,
        "status": "ready",
        "score": 0.85,
        "checks_json": [],
        "blockers_json": [],
        "conditions_json": [],
    }
    defaults.update(kwargs)
    ra = ReadinessAssessment(**defaults)
    db.add(ra)
    await db.flush()
    return ra


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_radar_building_not_found(db_session, admin_user):
    """Radar returns None for non-existent building."""
    result = await compute_readiness_radar(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_radar_returns_7_axes(db_session, admin_user):
    """Radar always returns exactly 7 axes."""
    b = await _create_building(db_session, admin_user)
    result = await compute_readiness_radar(db_session, b.id)

    assert result is not None
    assert len(result["axes"]) == 7
    axis_names = {a["name"] for a in result["axes"]}
    assert axis_names == {
        "safe_to_start",
        "safe_to_sell",
        "safe_to_insure",
        "safe_to_finance",
        "safe_to_renovate",
        "safe_to_occupy",
        "safe_to_transfer",
    }


@pytest.mark.asyncio
async def test_radar_scores_in_range(db_session, admin_user):
    """All axis scores must be 0-100."""
    b = await _create_building(db_session, admin_user)
    await _create_trust_score(db_session, b.id)
    await _create_risk_score(db_session, b.id)
    result = await compute_readiness_radar(db_session, b.id)

    for axis in result["axes"]:
        assert 0 <= axis["score"] <= 100, f"Axis {axis['name']} score {axis['score']} out of range"
        assert axis["grade"] in ("A", "B", "C", "D", "E", "F"), f"Invalid grade {axis['grade']}"


@pytest.mark.asyncio
async def test_radar_overall_score_is_average(db_session, admin_user):
    """Overall score = average of axis scores."""
    b = await _create_building(db_session, admin_user)
    result = await compute_readiness_radar(db_session, b.id)

    axis_scores = [a["score"] for a in result["axes"]]
    expected = round(sum(axis_scores) / len(axis_scores))
    assert result["overall_score"] == expected


@pytest.mark.asyncio
async def test_radar_with_readiness_assessment(db_session, admin_user):
    """Radar uses ReadinessAssessment when available for safe_to_start."""
    b = await _create_building(db_session, admin_user)
    await _create_readiness(db_session, b.id, "safe_to_start", status="ready", score=0.9)
    result = await compute_readiness_radar(db_session, b.id)

    start_axis = next(a for a in result["axes"] if a["name"] == "safe_to_start")
    assert start_axis["score"] >= 85  # ready status boosts to >= 85


@pytest.mark.asyncio
async def test_radar_blockers_populated(db_session, admin_user):
    """Blockers are populated when conditions fail."""
    b = await _create_building(db_session, admin_user)
    # Low trust + no docs → multiple blockers
    await _create_trust_score(db_session, b.id, overall_score=0.2)
    result = await compute_readiness_radar(db_session, b.id)

    # safe_to_finance should have blockers with low trust
    finance_axis = next(a for a in result["axes"] if a["name"] == "safe_to_finance")
    assert len(finance_axis["blockers"]) > 0


@pytest.mark.asyncio
async def test_radar_high_risk_samples_impact_insurance(db_session, admin_user):
    """High-risk samples reduce insurance readiness."""
    b = await _create_building(db_session, admin_user)
    await _create_risk_score(db_session, b.id, overall_risk_level="high")

    # Create diagnostic with high-risk samples
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="full",
        diagnostic_context="AvT",
        status="completed",
        date_inspection=date(2024, 1, 15),
    )
    db_session.add(diag)
    await db_session.flush()

    for i in range(3):
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number=f"S-INS-{i + 1}",
            material_description=f"Material {i}",
            pollutant_type="asbestos",
            risk_level="high",
            threshold_exceeded=True,
            concentration=5.0,
            unit="percent_weight",
        )
        db_session.add(sample)
    await db_session.flush()

    result = await compute_readiness_radar(db_session, b.id)
    insure_axis = next(a for a in result["axes"] if a["name"] == "safe_to_insure")
    # High risk + 3 high samples should reduce score
    assert insure_axis["score"] < 70


@pytest.mark.asyncio
async def test_radar_critical_samples_impact_occupancy(db_session, admin_user):
    """Critical-risk samples severely reduce occupancy readiness."""
    b = await _create_building(db_session, admin_user)

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="full",
        diagnostic_context="AvT",
        status="completed",
        date_inspection=date(2024, 1, 15),
    )
    db_session.add(diag)
    await db_session.flush()

    for i in range(2):
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number=f"S-OCC-{i + 1}",
            material_description=f"Critical material {i}",
            pollutant_type="asbestos",
            risk_level="critical",
            threshold_exceeded=True,
            concentration=10.0,
            unit="percent_weight",
        )
        db_session.add(sample)
    await db_session.flush()

    result = await compute_readiness_radar(db_session, b.id)
    occupy_axis = next(a for a in result["axes"] if a["name"] == "safe_to_occupy")
    assert occupy_axis["score"] < 80
    assert len(occupy_axis["blockers"]) > 0


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_score_to_grade():
    assert _score_to_grade(90) == "A"
    assert _score_to_grade(75) == "B"
    assert _score_to_grade(55) == "C"
    assert _score_to_grade(40) == "D"
    assert _score_to_grade(25) == "E"
    assert _score_to_grade(10) == "F"
    assert _score_to_grade(0) == "F"
    assert _score_to_grade(100) == "A"
