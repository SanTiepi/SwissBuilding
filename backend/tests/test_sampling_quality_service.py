"""Tests for the Sampling Quality Score service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.zone import Zone
from app.services.sampling_quality_service import (
    _applicable_pollutants,
    _confidence_level,
    _score_to_grade,
    evaluate_building_sampling_quality,
    evaluate_sampling_quality,
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
        "floors_above": 4,
        "floors_below": 1,
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
        "methodology": "FACH 2021",
        "date_inspection": datetime.now(UTC).date(),
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_zone(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "zone_type": "room",
        "name": f"Zone-{uuid.uuid4().hex[:6]}",
    }
    defaults.update(kwargs)
    z = Zone(**defaults)
    db.add(z)
    await db.flush()
    return z


async def _create_sample(db, diagnostic_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic_id,
        "sample_number": f"S-{uuid.uuid4().hex[:6]}",
        "pollutant_type": "asbestos",
        "location_floor": "1",
        "location_room": "Room A",
        "material_category": "insulation",
        "concentration": 0.5,
        "unit": "f/cm3",
        "risk_level": "low",
        "cfst_work_category": "minor",
        "threshold_exceeded": False,
    }
    defaults.update(kwargs)
    s = Sample(**defaults)
    db.add(s)
    await db.flush()
    return s


# ── Unit tests for helpers ──────────────────────────────────────────


class TestScoreToGrade:
    def test_grade_a(self):
        assert _score_to_grade(85) == "A"
        assert _score_to_grade(100) == "A"

    def test_grade_b(self):
        assert _score_to_grade(70) == "B"
        assert _score_to_grade(84) == "B"

    def test_grade_c(self):
        assert _score_to_grade(55) == "C"
        assert _score_to_grade(69) == "C"

    def test_grade_d(self):
        assert _score_to_grade(40) == "D"
        assert _score_to_grade(54) == "D"

    def test_grade_f(self):
        assert _score_to_grade(0) == "F"
        assert _score_to_grade(39) == "F"


class TestConfidenceLevel:
    def test_high(self):
        assert _confidence_level(80) == "high"
        assert _confidence_level(100) == "high"

    def test_medium(self):
        assert _confidence_level(60) == "medium"
        assert _confidence_level(79) == "medium"

    def test_low(self):
        assert _confidence_level(40) == "low"
        assert _confidence_level(59) == "low"

    def test_very_low(self):
        assert _confidence_level(0) == "very_low"
        assert _confidence_level(39) == "very_low"


class TestApplicablePollutants:
    def test_old_building(self):
        result = _applicable_pollutants(1950)
        assert "asbestos" in result
        assert "pcb" in result
        assert "lead" in result
        assert "hap" in result

    def test_modern_building(self):
        result = _applicable_pollutants(2010)
        assert "asbestos" not in result
        assert "pcb" not in result
        assert "radon" in result

    def test_unknown_year(self):
        result = _applicable_pollutants(None)
        assert len(result) == 6  # all pollutants


# ── Integration tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_diagnostic_not_found(db_session):
    """Returns None for a nonexistent diagnostic."""
    result = await evaluate_sampling_quality(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_good_sampling_high_score(db_session, admin_user):
    """Diagnostic with thorough sampling should score well."""
    building = await _create_building(db_session, admin_user)

    # Create zones
    for i in range(4):
        await _create_zone(db_session, building.id, name=f"Zone {i}", floor_number=i)

    diag = await _create_diagnostic(db_session, building.id)

    # Create well-documented samples across multiple zones, floors, pollutants, materials
    pollutants = ["asbestos", "pcb", "lead"]
    materials = ["insulation", "joint_compound", "tile", "coating", "pipe_lagging", "flooring"]
    for floor in range(4):
        for room_idx in range(2):
            room = f"Room {floor}-{room_idx}"
            for p_idx, poll in enumerate(pollutants):
                await _create_sample(
                    db_session,
                    diag.id,
                    location_floor=str(floor),
                    location_room=room,
                    pollutant_type=poll,
                    material_category=materials[p_idx % len(materials)],
                    concentration=0.1 * (p_idx + 1),
                    unit="mg/kg" if poll != "asbestos" else "f/cm3",
                    risk_level="low",
                    cfst_work_category="minor",
                    threshold_exceeded=False,
                )

    # Add a negative control
    await _create_sample(
        db_session,
        diag.id,
        location_floor="0",
        location_room="Control Room",
        pollutant_type="asbestos",
        material_category="concrete",
        concentration=0,
        threshold_exceeded=False,
    )

    result = await evaluate_sampling_quality(db_session, diag.id)
    assert result is not None
    assert result["diagnostic_id"] == str(diag.id)
    assert result["overall_score"] >= 50  # should be decent
    assert result["grade"] in ("A", "B", "C")
    assert len(result["criteria"]) == 10
    assert result["confidence_level"] in ("high", "medium")
    assert "evaluated_at" in result


@pytest.mark.asyncio
async def test_poor_sampling_low_score(db_session, admin_user):
    """Diagnostic with minimal sampling should score poorly."""
    building = await _create_building(db_session, admin_user)

    # Create zones but no samples match them
    for i in range(5):
        await _create_zone(db_session, building.id, name=f"Zone {i}")

    diag = await _create_diagnostic(
        db_session,
        building.id,
        methodology=None,
        suva_notification_required=True,
        suva_notification_date=None,
    )

    # Single incomplete sample
    await _create_sample(
        db_session,
        diag.id,
        location_floor=None,
        location_room=None,
        material_category=None,
        pollutant_type=None,
        concentration=None,
        unit=None,
        risk_level=None,
        cfst_work_category=None,
        threshold_exceeded=None,
    )

    result = await evaluate_sampling_quality(db_session, diag.id)
    assert result is not None
    assert result["overall_score"] < 40
    assert result["grade"] in ("D", "F")
    assert len(result["warnings"]) > 0


@pytest.mark.asyncio
async def test_each_criterion_present(db_session, admin_user):
    """Verify all 10 criteria are returned."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building.id)
    await _create_sample(db_session, diag.id)

    result = await evaluate_sampling_quality(db_session, diag.id)
    assert result is not None

    criterion_names = {c["name"] for c in result["criteria"]}
    expected = {
        "coverage",
        "density",
        "pollutant_breadth",
        "material_diversity",
        "location_spread",
        "temporal_consistency",
        "lab_turnaround",
        "documentation",
        "negative_controls",
        "protocol_compliance",
    }
    assert criterion_names == expected

    # Each criterion has required fields
    for c in result["criteria"]:
        assert 0 <= c["score"] <= c["max"]
        assert isinstance(c["detail"], str)
        assert isinstance(c["recommendation"], str)


@pytest.mark.asyncio
async def test_building_level_aggregation(db_session, admin_user):
    """Building aggregation returns avg, best, worst."""
    building = await _create_building(db_session, admin_user)

    # Two diagnostics with different quality
    diag1 = await _create_diagnostic(db_session, building.id, diagnostic_type="asbestos")
    diag2 = await _create_diagnostic(db_session, building.id, diagnostic_type="pcb")

    # Good sampling on diag1
    for i in range(5):
        await _create_sample(
            db_session,
            diag1.id,
            location_floor=str(i),
            location_room=f"Room {i}",
            material_category=["insulation", "tile", "coating", "joint", "pipe"][i],
            pollutant_type="asbestos",
        )

    # Poor sampling on diag2
    await _create_sample(
        db_session,
        diag2.id,
        location_floor=None,
        location_room=None,
        material_category=None,
        concentration=None,
        unit=None,
    )

    result = await evaluate_building_sampling_quality(db_session, building.id)
    assert result is not None
    assert result["building_id"] == str(building.id)
    assert isinstance(result["avg_score"], int)
    assert len(result["diagnostics"]) == 2
    assert result["best_diagnostic"] is not None
    assert result["worst_diagnostic"] is not None
    assert result["best_diagnostic"] != result["worst_diagnostic"]


@pytest.mark.asyncio
async def test_building_not_found(db_session):
    """Returns None for nonexistent building."""
    result = await evaluate_building_sampling_quality(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_building_no_diagnostics(db_session, admin_user):
    """Building with no diagnostics returns empty aggregation."""
    building = await _create_building(db_session, admin_user)
    result = await evaluate_building_sampling_quality(db_session, building.id)
    assert result is not None
    assert result["avg_score"] == 0
    assert result["diagnostics"] == []
