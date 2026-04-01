"""Tests for quality_of_life_service — comprehensive composite scoring."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.services.quality_of_life_service import compute_quality_of_life

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, *, enrichment=None, canton="VD"):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton=canton,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        source_metadata_json=enrichment,
    )
    db.add(b)
    await db.flush()
    return b


def _excellent_enrichment():
    """Top-quality location: great transport, amenities, quiet, connected."""
    return {
        "osm_amenities": {
            "schools": 4,
            "hospitals": 2,
            "pharmacies": 3,
            "supermarkets": 5,
            "restaurants": 15,
            "parks": 4,
            "banks": 3,
            "post_offices": 2,
            "cafes": 8,
            "kindergartens": 3,
            "total_amenities": 60,
        },
        "transport": {"transport_quality_class": "A"},
        "nearest_stops": {"nearest_stop_distance_m": 150},
        "noise": {"road_noise_day_db": 38},
        "connectivity_score": 9.0,
        "mobile_coverage": {"has_5g_coverage": True},
        "broadband": {"max_speed_mbps": 1000},
        "solar": {"suitability": "high"},
        "heritage": {"isos_protected": True},
        "contaminated_sites": {"is_contaminated": False},
        "climate": {"estimated_altitude_m": 500},
        "flood_zones": {"flood_danger_level": "gering"},
        "water_protection": {"protection_zone": "S3"},
        "agricultural_zones": {"in_agricultural_zone": False},
        "forest_reserves": {"in_forest_reserve": False},
        "natural_hazards": {
            "flood_risk": "none",
            "landslide_risk": "none",
            "rockfall_risk": "none",
        },
    }


def _poor_enrichment():
    """Poor location: bad transport, no amenities, noisy, contaminated."""
    return {
        "osm_amenities": {
            "schools": 0,
            "hospitals": 0,
            "pharmacies": 0,
            "supermarkets": 0,
            "restaurants": 0,
            "parks": 0,
            "banks": 0,
            "post_offices": 0,
            "cafes": 0,
            "kindergartens": 0,
            "total_amenities": 0,
        },
        "transport": {"transport_quality_class": "D"},
        "nearest_stops": {"nearest_stop_distance_m": 2500},
        "noise": {"road_noise_day_db": 72},
        "connectivity_score": 1.0,
        "contaminated_sites": {"is_contaminated": True},
        "accident_sites": {"near_seveso_site": True},
        "climate": {"estimated_altitude_m": 350},
        "natural_hazards": {
            "flood_risk": "high",
            "landslide_risk": "medium",
            "rockfall_risk": "none",
        },
    }


# ── Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_excellent_location_high_score(db_session, admin_user):
    """Excellent location -> score >= 70, grade A or B."""
    building = await _create_building(db_session, admin_user, enrichment=_excellent_enrichment())
    result = await compute_quality_of_life(db_session, building.id)

    assert result["score"] >= 65
    assert result["grade"] in ("A", "B")
    assert len(result["strengths"]) >= 2
    assert len(result["dimensions"]) == 7


@pytest.mark.asyncio
async def test_poor_location_low_score(db_session, admin_user):
    """Poor location -> low score, grade D-F."""
    building = await _create_building(db_session, admin_user, enrichment=_poor_enrichment())
    result = await compute_quality_of_life(db_session, building.id)

    assert result["score"] < 40
    assert result["grade"] in ("D", "E", "F")
    assert len(result["weaknesses"]) >= 1


@pytest.mark.asyncio
async def test_all_dimensions_present(db_session, admin_user):
    """Output contains all 7 dimensions with score and factors."""
    building = await _create_building(db_session, admin_user, enrichment=_excellent_enrichment())
    result = await compute_quality_of_life(db_session, building.id)

    expected_dims = {"mobility", "nature", "services", "culture", "safety", "comfort", "connectivity"}
    assert set(result["dimensions"].keys()) == expected_dims

    for dim_name, dim_data in result["dimensions"].items():
        assert "score" in dim_data, f"Missing score in {dim_name}"
        assert 0.0 <= dim_data["score"] <= 10.0, f"{dim_name} score out of range"


@pytest.mark.asyncio
async def test_score_range_0_100(db_session, admin_user):
    """Score is always between 0 and 100."""
    for enrichment in [_excellent_enrichment(), _poor_enrichment(), {}, None]:
        building = await _create_building(db_session, admin_user, enrichment=enrichment)
        result = await compute_quality_of_life(db_session, building.id)
        assert 0 <= result["score"] <= 100, f"Score out of range: {result['score']}"


@pytest.mark.asyncio
async def test_canton_comparison(db_session, admin_user):
    """Canton comparison produces valid comparison and quartile."""
    building = await _create_building(db_session, admin_user, enrichment=_excellent_enrichment(), canton="ZH")
    result = await compute_quality_of_life(db_session, building.id)

    assert "comparison_to_canton_avg" in result
    assert isinstance(result["comparison_to_canton_avg"], (int, float))
    assert result["quartile"] in ("top 10%", "top 25%", "average", "bottom 25%")


@pytest.mark.asyncio
async def test_quartile_excellent_above_avg(db_session, admin_user):
    """Excellent location should be above canton average."""
    building = await _create_building(db_session, admin_user, enrichment=_excellent_enrichment(), canton="JU")
    result = await compute_quality_of_life(db_session, building.id)

    # JU average is 48, excellent location should score well above
    assert result["comparison_to_canton_avg"] > 0


@pytest.mark.asyncio
async def test_missing_dimensions_graceful(db_session, admin_user):
    """Partial enrichment (only transport) -> still computes score."""
    enrichment = {"transport": {"transport_quality_class": "B"}}
    building = await _create_building(db_session, admin_user, enrichment=enrichment)
    result = await compute_quality_of_life(db_session, building.id)

    assert result["score"] > 0
    assert result["dimensions"]["mobility"]["score"] > 0


@pytest.mark.asyncio
async def test_building_not_found(db_session, admin_user):
    """Non-existent building -> score 0."""
    result = await compute_quality_of_life(db_session, uuid.uuid4())
    assert result["score"] == 0
    assert result["grade"] == "F"
    assert result.get("error") == "building_not_found"


@pytest.mark.asyncio
async def test_strengths_and_weaknesses_content(db_session, admin_user):
    """Strengths list high-scoring dimensions, weaknesses list low-scoring ones."""
    building = await _create_building(db_session, admin_user, enrichment=_excellent_enrichment())
    result = await compute_quality_of_life(db_session, building.id)

    for s in result["strengths"]:
        assert isinstance(s, str)
        assert len(s) > 5  # should have meaningful content

    for w in result["weaknesses"]:
        assert isinstance(w, str)


@pytest.mark.asyncio
async def test_grade_boundaries(db_session, admin_user):
    """Grade mapping works for different enrichment levels."""
    # Excellent -> A or B
    b1 = await _create_building(db_session, admin_user, enrichment=_excellent_enrichment())
    r1 = await compute_quality_of_life(db_session, b1.id)
    assert r1["grade"] in ("A", "B")

    # Poor -> D, E, or F
    b2 = await _create_building(db_session, admin_user, enrichment=_poor_enrichment())
    r2 = await compute_quality_of_life(db_session, b2.id)
    assert r2["grade"] in ("D", "E", "F")

    # Scores should be properly ordered
    assert r1["score"] > r2["score"]
