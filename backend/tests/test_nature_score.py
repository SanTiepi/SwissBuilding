"""Tests for nature_score_service — green environment quality scoring."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.services.nature_score_service import compute_nature_score

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, *, enrichment=None):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        source_metadata_json=enrichment,
    )
    db.add(b)
    await db.flush()
    return b


def _full_nature_enrichment():
    """Ideal nature environment: parks, forest, water, clean air, altitude."""
    return {
        "osm_amenities": {"parks": 5},
        "flood_zones": {"flood_danger_level": "gering"},
        "water_protection": {"protection_zone": "S2"},
        "agricultural_zones": {"in_agricultural_zone": True},
        "forest_reserves": {"in_forest_reserve": True},
        "noise": {"road_noise_day_db": 35},
        "contaminated_sites": {"is_contaminated": False},
        "railway_noise": {"railway_noise_day_db": 25},
        "aircraft_noise": {"aircraft_noise_db": 20},
        "climate": {"estimated_altitude_m": 1200},
        "natural_hazards": {
            "flood_risk": "none",
            "landslide_risk": "none",
            "rockfall_risk": "none",
        },
    }


def _urban_noisy_enrichment():
    """Urban, noisy, contaminated, no parks."""
    return {
        "osm_amenities": {"parks": 0},
        "noise": {"road_noise_day_db": 70},
        "contaminated_sites": {"is_contaminated": True},
        "railway_noise": {"railway_noise_day_db": 62},
        "aircraft_noise": {"aircraft_noise_db": 60},
        "climate": {"estimated_altitude_m": 350},
        "natural_hazards": {
            "flood_risk": "high",
            "landslide_risk": "medium",
            "rockfall_risk": "none",
        },
    }


# ── Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_nature_high_score(db_session, admin_user):
    """Full nature enrichment -> high score."""
    building = await _create_building(db_session, admin_user, enrichment=_full_nature_enrichment())
    result = await compute_nature_score(db_session, building.id)

    assert result["score"] >= 6.0
    assert result["grade"] in ("A", "B", "C")
    assert "breakdown" in result
    assert len(result["breakdown"]) == 6
    assert len(result["highlights"]) >= 2


@pytest.mark.asyncio
async def test_no_parks_low_park_score(db_session, admin_user):
    """No parks -> parks dimension score is 0."""
    enrichment = _full_nature_enrichment()
    enrichment["osm_amenities"]["parks"] = 0
    building = await _create_building(db_session, admin_user, enrichment=enrichment)
    result = await compute_nature_score(db_session, building.id)

    assert result["breakdown"]["parks_nearby"]["score"] == 0.0
    assert any("park" in r.lower() for r in result["recommendations"])


@pytest.mark.asyncio
async def test_high_altitude_bonus(db_session, admin_user):
    """High altitude -> altitude bonus is high."""
    enrichment = {"climate": {"estimated_altitude_m": 1800}}
    building = await _create_building(db_session, admin_user, enrichment=enrichment)
    result = await compute_nature_score(db_session, building.id)

    assert result["breakdown"]["altitude_bonus"]["score"] >= 7.0
    assert any("mountain" in h.lower() or "alpine" in h.lower() for h in result["highlights"])


@pytest.mark.asyncio
async def test_hazard_penalty(db_session, admin_user):
    """High natural hazards -> penalty applied."""
    enrichment = {
        "natural_hazards": {
            "flood_risk": "high",
            "landslide_risk": "high",
            "rockfall_risk": "high",
        },
        "osm_amenities": {"parks": 3},
        "noise": {"road_noise_day_db": 40},
        "climate": {"estimated_altitude_m": 600},
    }
    building = await _create_building(db_session, admin_user, enrichment=enrichment)
    result = await compute_nature_score(db_session, building.id)

    penalty = result["breakdown"]["nature_hazard_penalty"]["score"]
    assert penalty >= 6.0  # high hazards = high penalty value
    assert any("hazard" in r.lower() for r in result["recommendations"])


@pytest.mark.asyncio
async def test_urban_noisy_low_score(db_session, admin_user):
    """Urban noisy contaminated -> low nature score."""
    building = await _create_building(db_session, admin_user, enrichment=_urban_noisy_enrichment())
    result = await compute_nature_score(db_session, building.id)

    assert result["score"] < 4.0
    assert result["grade"] in ("D", "E", "F")
    assert len(result["recommendations"]) >= 1


@pytest.mark.asyncio
async def test_score_range_0_10(db_session, admin_user):
    """Score is always between 0 and 10."""
    # Test with extreme data
    for enrichment in [_full_nature_enrichment(), _urban_noisy_enrichment(), {}, None]:
        building = await _create_building(db_session, admin_user, enrichment=enrichment)
        result = await compute_nature_score(db_session, building.id)
        assert 0.0 <= result["score"] <= 10.0, f"Score out of range: {result['score']}"


@pytest.mark.asyncio
async def test_building_not_found(db_session, admin_user):
    """Non-existent building -> score 0, grade F."""
    result = await compute_nature_score(db_session, uuid.uuid4())
    assert result["score"] == 0.0
    assert result["grade"] == "F"


@pytest.mark.asyncio
async def test_air_quality_clean(db_session, admin_user):
    """Low noise, no contamination -> high air quality score."""
    enrichment = {
        "noise": {"road_noise_day_db": 35},
        "contaminated_sites": {"is_contaminated": False},
        "railway_noise": {"railway_noise_day_db": 20},
        "aircraft_noise": {"aircraft_noise_db": 15},
    }
    building = await _create_building(db_session, admin_user, enrichment=enrichment)
    result = await compute_nature_score(db_session, building.id)

    assert result["breakdown"]["air_quality"]["score"] == 10.0
    assert any("air" in h.lower() for h in result["highlights"])
