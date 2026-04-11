"""Tests for the Evidence Score Service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.building import Building
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.sample import Sample
from app.services.evidence_score_service import (
    _compute_freshness,
    _score_to_grade,
    compute_evidence_score,
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


async def _create_trust_score(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "overall_score": 0.6,
        "percent_proven": 0.4,
        "percent_inferred": 0.1,
        "percent_declared": 0.3,
        "percent_obsolete": 0.1,
        "percent_contradictory": 0.1,
        "total_data_points": 10,
        "proven_count": 4,
        "inferred_count": 1,
        "declared_count": 3,
        "obsolete_count": 1,
        "contradictory_count": 1,
        "trend": "stable",
        "assessed_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    ts = BuildingTrustScore(**defaults)
    db.add(ts)
    await db.flush()
    return ts


async def _create_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
        "date_inspection": datetime.now(UTC).date(),
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_document(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "document_type": "lab_report",
        "file_name": "report.pdf",
        "file_path": "/files/report.pdf",
        "created_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    d = Document(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_sample(db, diagnostic_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic_id,
        "sample_number": "S001",
        "pollutant_type": "asbestos",
        "location_room": "Room 1",
        "concentration": 0.5,
        "unit": "f/cm3",
        "risk_level": "low",
    }
    defaults.update(kwargs)
    s = Sample(**defaults)
    db.add(s)
    await db.flush()
    return s


# ── Tests ──────────────────────────────────────────────────────────


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


class TestComputeFreshness:
    def test_recent_evidence(self):
        recent = datetime.now(UTC) - timedelta(days=30)
        assert _compute_freshness(recent) == 1.0

    def test_one_to_three_years(self):
        old = datetime.now(UTC) - timedelta(days=400)
        assert _compute_freshness(old) == 0.5

    def test_three_to_five_years(self):
        old = datetime.now(UTC) - timedelta(days=1300)
        assert _compute_freshness(old) == 0.2

    def test_over_five_years(self):
        old = datetime.now(UTC) - timedelta(days=2000)
        assert _compute_freshness(old) == 0.0

    def test_none_date(self):
        assert _compute_freshness(None) == 0.0


@pytest.mark.asyncio
async def test_compute_evidence_score_building_not_found(db_session):
    """Returns None for a nonexistent building."""
    result = await compute_evidence_score(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_compute_evidence_score_empty_building(db_session, admin_user):
    """Empty building gets a low score with valid structure."""
    building = await _create_building(db_session, admin_user)

    result = await compute_evidence_score(db_session, building.id)
    assert result is not None
    assert result["building_id"] == str(building.id)
    assert isinstance(result["score"], int)
    assert 0 <= result["score"] <= 100
    assert result["grade"] in ("A", "B", "C", "D", "F")
    assert result["trust"] == 0.0
    assert result["freshness"] == 0.0
    assert "breakdown" in result
    assert "computed_at" in result


@pytest.mark.asyncio
async def test_compute_evidence_score_with_data(db_session, admin_user):
    """Building with trust score, diagnostics, and documents gets a higher score."""
    building = await _create_building(db_session, admin_user)

    # Add trust score
    await _create_trust_score(db_session, building.id, overall_score=0.8)

    # Add recent diagnostic
    diag = await _create_diagnostic(db_session, building.id)

    # Add sample
    await _create_sample(db_session, diag.id)

    # Add document
    await _create_document(db_session, building.id)

    result = await compute_evidence_score(db_session, building.id)
    assert result is not None
    assert result["trust"] == 0.8
    assert result["freshness"] == 1.0  # recent data
    assert result["score"] > 0

    # Verify breakdown sums
    breakdown = result["breakdown"]
    total_weighted = (
        breakdown["trust_weighted"]
        + breakdown["completeness_weighted"]
        + breakdown["freshness_weighted"]
        + breakdown["gap_penalty_weighted"]
    )
    assert abs(result["score"] - round(total_weighted * 100)) <= 1


@pytest.mark.asyncio
async def test_compute_evidence_score_grade_thresholds(db_session, admin_user):
    """Verify that grade assignment follows defined thresholds."""
    building = await _create_building(db_session, admin_user)

    result = await compute_evidence_score(db_session, building.id)
    assert result is not None
    score = result["score"]
    grade = result["grade"]

    # Verify grade matches score
    if score >= 85:
        assert grade == "A"
    elif score >= 70:
        assert grade == "B"
    elif score >= 55:
        assert grade == "C"
    elif score >= 40:
        assert grade == "D"
    else:
        assert grade == "F"
