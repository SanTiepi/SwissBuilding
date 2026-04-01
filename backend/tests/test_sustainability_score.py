"""Tests for sustainability_score_service — composite sustainability evaluation."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.climate_exposure import ClimateExposureProfile
from app.models.diagnostic import Diagnostic
from app.models.material import Material
from app.models.sample import Sample
from app.models.zone import Zone
from app.services.sustainability_score_service import compute_sustainability_score

# ── Helpers ────────────────────────────────────────────────────────


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


async def _create_climate_profile(db, building_id, *, moisture="low", thermal="low", uv="low"):
    p = ClimateExposureProfile(
        id=uuid.uuid4(),
        building_id=building_id,
        moisture_stress=moisture,
        thermal_stress=thermal,
        uv_exposure=uv,
    )
    db.add(p)
    await db.flush()
    return p


async def _create_diagnostic_with_samples(db, building_id, *, contaminated_count=0, clean_count=3):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db.add(diag)
    await db.flush()

    for i in range(clean_count):
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number=f"S-clean-{i}",
            pollutant_type="asbestos",
            concentration=0.0,
            unit="mg/kg",
            threshold_exceeded=False,
            waste_disposal_type=None,
        )
        db.add(s)

    for i in range(contaminated_count):
        s = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number=f"S-contam-{i}",
            pollutant_type="asbestos",
            concentration=50.0,
            unit="mg/kg",
            threshold_exceeded=True,
            waste_disposal_type="type_b" if i % 2 == 0 else None,
        )
        db.add(s)

    await db.flush()
    return diag


# ── Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_building_not_found(db_session, admin_user):
    """Non-existent building → score 0, grade F."""
    result = await compute_sustainability_score(db_session, uuid.uuid4())
    assert result["score"] == 0
    assert result["grade"] == "F"


@pytest.mark.asyncio
async def test_modern_clean_building(db_session, admin_user):
    """Modern building (2015), clean, good climate → high score."""
    building = await _create_building(db_session, admin_user, construction_year=2015)
    await _create_climate_profile(db_session, building.id, moisture="low", thermal="low", uv="low")
    await _create_diagnostic_with_samples(db_session, building.id, contaminated_count=0, clean_count=5)

    result = await compute_sustainability_score(db_session, building.id)
    assert result["score"] >= 70
    assert result["grade"] in ("A", "B")
    assert "breakdown" in result
    assert len(result["recommendations"]) == 0 or all(isinstance(r, str) for r in result["recommendations"])


@pytest.mark.asyncio
async def test_old_contaminated_building(db_session, admin_user):
    """Old building (1960), contaminated, high stress → low score."""
    building = await _create_building(db_session, admin_user, construction_year=1960)
    await _create_climate_profile(db_session, building.id, moisture="high", thermal="high", uv="high")
    await _create_diagnostic_with_samples(db_session, building.id, contaminated_count=5, clean_count=0)

    result = await compute_sustainability_score(db_session, building.id)
    assert result["score"] < 50
    assert result["grade"] in ("D", "E", "F")
    assert len(result["recommendations"]) >= 2


@pytest.mark.asyncio
async def test_score_range_0_100(db_session, admin_user):
    """Score always between 0 and 100."""
    building = await _create_building(db_session, admin_user, construction_year=1985)
    result = await compute_sustainability_score(db_session, building.id)
    assert 0 <= result["score"] <= 100


@pytest.mark.asyncio
async def test_breakdown_has_all_dimensions(db_session, admin_user):
    """Breakdown contains all 5 dimension keys."""
    building = await _create_building(db_session, admin_user)
    result = await compute_sustainability_score(db_session, building.id)

    breakdown = result["breakdown"]
    expected_keys = {
        "energy_performance",
        "pollutant_status",
        "climate_resilience",
        "material_health",
        "waste_management",
    }
    assert set(breakdown.keys()) == expected_keys

    for key in expected_keys:
        dim = breakdown[key]
        assert "score" in dim
        assert "weight" in dim
        assert "explanation" in dim


@pytest.mark.asyncio
async def test_no_diagnostics_defaults(db_session, admin_user):
    """Building with no diagnostics → pollutant and waste use defaults."""
    building = await _create_building(db_session, admin_user)
    result = await compute_sustainability_score(db_session, building.id)

    # Pollutant default is 50.0, waste default is 50.0
    assert result["breakdown"]["pollutant_status"]["score"] == 50.0
    assert result["breakdown"]["waste_management"]["score"] == 50.0


@pytest.mark.asyncio
async def test_no_climate_profile_defaults(db_session, admin_user):
    """No ClimateExposureProfile → climate default 50.0."""
    building = await _create_building(db_session, admin_user)
    result = await compute_sustainability_score(db_session, building.id)
    assert result["breakdown"]["climate_resilience"]["score"] == 50.0


@pytest.mark.asyncio
async def test_grade_boundaries(db_session, admin_user):
    """Grade mapping from score works correctly."""
    # Modern, clean, good climate → should be A or B
    building_good = await _create_building(db_session, admin_user, construction_year=2020)
    await _create_climate_profile(db_session, building_good.id, moisture="low", thermal="low", uv="low")
    await _create_diagnostic_with_samples(db_session, building_good.id, contaminated_count=0, clean_count=10)

    result_good = await compute_sustainability_score(db_session, building_good.id)
    assert result_good["grade"] in ("A", "B", "C")  # should be high

    # Very old, contaminated, stressed → should be D, E, or F
    building_bad = await _create_building(db_session, admin_user, construction_year=1950)
    await _create_climate_profile(db_session, building_bad.id, moisture="high", thermal="high", uv="high")
    await _create_diagnostic_with_samples(db_session, building_bad.id, contaminated_count=10, clean_count=0)

    # Add risky materials
    zone = Zone(id=uuid.uuid4(), building_id=building_bad.id, zone_type="floor", name="Ground")
    db_session.add(zone)
    await db_session.flush()
    elem = BuildingElement(id=uuid.uuid4(), zone_id=zone.id, element_type="floor", name="Floor")
    db_session.add(elem)
    await db_session.flush()
    mat = Material(
        id=uuid.uuid4(),
        element_id=elem.id,
        material_type="flocage",
        name="Flocage 1960",
        installation_year=1960,
    )
    db_session.add(mat)
    await db_session.flush()

    result_bad = await compute_sustainability_score(db_session, building_bad.id)
    assert result_bad["score"] < result_good["score"]
