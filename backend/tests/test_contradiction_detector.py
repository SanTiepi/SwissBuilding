"""Tests for the contradiction_detector service."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.contradiction_detector import (
    detect_contradictions,
    get_contradiction_summary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_building(db, admin_user, *, construction_year=1970):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic(db, building, *, status="completed", date_inspection=None):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status=status,
        date_inspection=date_inspection or date(2025, 1, 15),
    )
    db.add(d)
    await db.flush()
    return d


async def _create_sample(
    db,
    diagnostic,
    *,
    pollutant_type="asbestos",
    location_room=None,
    material_category=None,
    threshold_exceeded=False,
    risk_level=None,
    concentration=500.0,
    unit="mg/kg",
):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic.id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        location_room=location_room,
        material_category=material_category,
        threshold_exceeded=threshold_exceeded,
        risk_level=risk_level,
        concentration=concentration,
        unit=unit,
    )
    db.add(s)
    await db.flush()
    return s


def _field_names(issues: list[DataQualityIssue]) -> list[str]:
    return sorted(i.field_name for i in issues if i.field_name)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detects_conflicting_sample_results(db_session, admin_user):
    """Same location + pollutant with different threshold_exceeded values."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building)

    await _create_sample(
        db_session,
        diag,
        location_room="Salon",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
    )
    await _create_sample(
        db_session,
        diag,
        location_room="Salon",
        pollutant_type="asbestos",
        threshold_exceeded=False,
        risk_level="low",
    )

    issues = await detect_contradictions(db_session, building.id)
    fields = _field_names(issues)
    assert "conflicting_sample_results" in fields

    conflict_issues = [i for i in issues if i.field_name == "conflicting_sample_results"]
    assert len(conflict_issues) == 1
    assert conflict_issues[0].severity == "high"
    assert "Salon" in conflict_issues[0].description


@pytest.mark.asyncio
async def test_detects_inconsistent_risk_levels(db_session, admin_user):
    """threshold_exceeded=True but risk_level='low'."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building)

    await _create_sample(
        db_session,
        diag,
        threshold_exceeded=True,
        risk_level="low",
    )

    issues = await detect_contradictions(db_session, building.id)
    fields = _field_names(issues)
    assert "inconsistent_risk_levels" in fields

    rl_issues = [i for i in issues if i.field_name == "inconsistent_risk_levels"]
    assert len(rl_issues) == 1
    assert rl_issues[0].severity == "medium"


@pytest.mark.asyncio
async def test_detects_inconsistent_risk_levels_reverse(db_session, admin_user):
    """threshold_exceeded=False but risk_level='critical'."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building)

    await _create_sample(
        db_session,
        diag,
        threshold_exceeded=False,
        risk_level="critical",
    )

    issues = await detect_contradictions(db_session, building.id)
    rl_issues = [i for i in issues if i.field_name == "inconsistent_risk_levels"]
    assert len(rl_issues) == 1
    assert "critical" in rl_issues[0].description


@pytest.mark.asyncio
async def test_detects_duplicate_samples_across_diagnostics(db_session, admin_user):
    """Same location+pollutant+material in different diagnostics."""
    building = await _create_building(db_session, admin_user)
    diag1 = await _create_diagnostic(db_session, building)
    diag2 = await _create_diagnostic(db_session, building)

    await _create_sample(
        db_session,
        diag1,
        location_room="Cuisine",
        pollutant_type="pcb",
        material_category="joint",
    )
    await _create_sample(
        db_session,
        diag2,
        location_room="Cuisine",
        pollutant_type="pcb",
        material_category="joint",
    )

    issues = await detect_contradictions(db_session, building.id)
    dup_issues = [i for i in issues if i.field_name == "duplicate_samples"]
    assert len(dup_issues) == 1
    assert "Cuisine" in dup_issues[0].description
    assert dup_issues[0].severity == "low"


@pytest.mark.asyncio
async def test_idempotent_no_duplicates(db_session, admin_user):
    """Running detector twice creates no duplicate issues."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building)

    await _create_sample(
        db_session,
        diag,
        threshold_exceeded=True,
        risk_level="low",
    )

    issues1 = await detect_contradictions(db_session, building.id)
    assert len(issues1) > 0

    issues2 = await detect_contradictions(db_session, building.id)
    assert len(issues2) == 0  # no new issues


@pytest.mark.asyncio
async def test_auto_resolves_when_contradiction_fixed(db_session, admin_user):
    """Fixing data causes the contradiction to be auto-resolved."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building)

    sample = await _create_sample(
        db_session,
        diag,
        threshold_exceeded=True,
        risk_level="low",
    )

    issues1 = await detect_contradictions(db_session, building.id)
    assert len(issues1) == 1
    assert issues1[0].status == "open"

    # Fix the contradiction
    sample.risk_level = "high"
    await db_session.flush()

    # Re-run detector
    await detect_contradictions(db_session, building.id)
    await db_session.refresh(issues1[0])
    assert issues1[0].status == "resolved"
    assert issues1[0].resolution_notes == "Auto-resolved: contradiction no longer detected"


@pytest.mark.asyncio
async def test_clean_building_no_contradictions(db_session, admin_user):
    """Building with consistent data returns no contradictions."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building)

    await _create_sample(
        db_session,
        diag,
        threshold_exceeded=True,
        risk_level="high",
    )
    await _create_sample(
        db_session,
        diag,
        threshold_exceeded=False,
        risk_level="low",
    )

    issues = await detect_contradictions(db_session, building.id)
    assert len(issues) == 0


@pytest.mark.asyncio
async def test_summary_returns_correct_counts(db_session, admin_user):
    """Summary endpoint returns correct totals by type."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building)

    # Create two types of contradictions
    await _create_sample(
        db_session,
        diag,
        threshold_exceeded=True,
        risk_level="low",
    )
    await _create_sample(
        db_session,
        diag,
        threshold_exceeded=False,
        risk_level="critical",
    )

    await detect_contradictions(db_session, building.id)
    summary = await get_contradiction_summary(db_session, building.id)

    assert summary["total"] == 2
    assert summary["unresolved"] == 2
    assert summary["resolved"] == 0
    assert "inconsistent_risk_levels" in summary["by_type"]
    assert summary["by_type"]["inconsistent_risk_levels"] == 2


@pytest.mark.asyncio
async def test_construction_year_conflict(db_session, admin_user):
    """Diagnostic inspection date before building construction year."""
    building = await _create_building(db_session, admin_user, construction_year=2020)
    await _create_diagnostic(
        db_session,
        building,
        date_inspection=date(2019, 6, 1),
    )

    issues = await detect_contradictions(db_session, building.id)
    year_issues = [i for i in issues if i.field_name == "construction_year_conflict"]
    assert len(year_issues) == 1
    assert "2020" in year_issues[0].description
    assert "2019" in year_issues[0].description


@pytest.mark.asyncio
async def test_pollutant_type_discrepancy(db_session, admin_user):
    """Same material_category with conflicting pollutant findings."""
    building = await _create_building(db_session, admin_user)
    diag = await _create_diagnostic(db_session, building)

    await _create_sample(
        db_session,
        diag,
        material_category="flocage",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
    )
    await _create_sample(
        db_session,
        diag,
        material_category="flocage",
        pollutant_type="asbestos",
        threshold_exceeded=False,
        risk_level="low",
    )

    issues = await detect_contradictions(db_session, building.id)
    disc_issues = [i for i in issues if i.field_name == "pollutant_type_discrepancy"]
    assert len(disc_issues) == 1
    assert "flocage" in disc_issues[0].description


@pytest.mark.asyncio
async def test_nonexistent_building_returns_empty(db_session, admin_user):
    """Calling with a non-existent building ID returns empty list."""
    fake_id = uuid.uuid4()
    issues = await detect_contradictions(db_session, fake_id)
    assert issues == []
