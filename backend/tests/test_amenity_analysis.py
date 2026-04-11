"""Tests for amenity_analysis_service — deep amenity scoring from enrichment."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.services.amenity_analysis_service import (
    analyze_amenities,
    score_from_distance,
)

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


def _rich_enrichment():
    """Full enrichment with many amenities."""
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
        "noise": {"road_noise_day_db": 40},
        "connectivity_score": 8.0,
        "climate": {"estimated_altitude_m": 450},
    }


def _sparse_enrichment():
    """Enrichment with very few amenities."""
    return {
        "osm_amenities": {
            "schools": 0,
            "hospitals": 0,
            "pharmacies": 1,
            "supermarkets": 0,
            "restaurants": 1,
            "parks": 0,
            "banks": 0,
            "post_offices": 0,
            "cafes": 0,
            "kindergartens": 0,
            "total_amenities": 2,
        },
        "transport": {"transport_quality_class": "D"},
        "noise": {"road_noise_day_db": 68},
        "connectivity_score": 2.0,
    }


# ── Distance Scoring Tests ─────────────────────────────────────────


class TestDistanceScoring:
    def test_very_close(self):
        assert score_from_distance(100) == 10.0

    def test_medium_distance(self):
        assert score_from_distance(300) == 8.0

    def test_far_distance(self):
        assert score_from_distance(1500) == 3.0

    def test_very_far(self):
        assert score_from_distance(5000) == 1.0

    def test_none_distance(self):
        assert score_from_distance(None) == 0.0

    def test_zero_distance(self):
        assert score_from_distance(0) == 10.0


# ── Amenity Analysis Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_rich_amenities_high_scores(db_session, admin_user):
    """Rich amenity area -> high scores across the board."""
    building = await _create_building(db_session, admin_user, enrichment=_rich_enrichment())
    result = await analyze_amenities(db_session, building.id)

    assert "amenities" in result
    assert result["walking_convenience"] > 0.0
    assert result["daily_needs_score"] > 0.0
    assert result["family_score"] > 0.0
    assert result["senior_score"] > 0.0
    assert result["remote_work_score"] > 0.0
    # With rich amenities, walking convenience should be high
    assert result["walking_convenience"] >= 5.0


@pytest.mark.asyncio
async def test_sparse_amenities_low_scores(db_session, admin_user):
    """Sparse amenity area -> low scores."""
    building = await _create_building(db_session, admin_user, enrichment=_sparse_enrichment())
    result = await analyze_amenities(db_session, building.id)

    assert result["family_score"] < 3.0
    assert result["daily_needs_score"] < 5.0


@pytest.mark.asyncio
async def test_all_amenity_types_present(db_session, admin_user):
    """All expected amenity categories appear in output."""
    building = await _create_building(db_session, admin_user, enrichment=_rich_enrichment())
    result = await analyze_amenities(db_session, building.id)

    expected_keys = {
        "schools",
        "hospitals",
        "pharmacies",
        "supermarkets",
        "restaurants",
        "parks",
        "banks",
        "post_offices",
        "cafes",
        "kindergartens",
    }
    assert set(result["amenities"].keys()) == expected_keys

    for cat_data in result["amenities"].values():
        assert "count" in cat_data
        assert "nearest_distance_m" in cat_data
        assert "score_0_10" in cat_data
        assert 0.0 <= cat_data["score_0_10"] <= 10.0


@pytest.mark.asyncio
async def test_empty_enrichment(db_session, admin_user):
    """No enrichment data -> all scores zero or default."""
    building = await _create_building(db_session, admin_user, enrichment={})
    result = await analyze_amenities(db_session, building.id)

    assert result["walking_convenience"] == 0.0
    assert result["daily_needs_score"] == 0.0
    assert result["family_score"] == 0.0
    # All amenity counts should be 0
    for cat_data in result["amenities"].values():
        assert cat_data["count"] == 0


@pytest.mark.asyncio
async def test_no_enrichment_at_all(db_session, admin_user):
    """Building with null source_metadata_json."""
    building = await _create_building(db_session, admin_user, enrichment=None)
    result = await analyze_amenities(db_session, building.id)

    assert result["walking_convenience"] == 0.0
    # Should not raise


@pytest.mark.asyncio
async def test_building_not_found(db_session, admin_user):
    """Non-existent building returns error."""
    result = await analyze_amenities(db_session, uuid.uuid4())
    assert result.get("error") == "building_not_found"


@pytest.mark.asyncio
async def test_persona_scores_range(db_session, admin_user):
    """All persona scores are within 0-10 range."""
    building = await _create_building(db_session, admin_user, enrichment=_rich_enrichment())
    result = await analyze_amenities(db_session, building.id)

    for key in ("walking_convenience", "daily_needs_score", "family_score", "senior_score", "remote_work_score"):
        assert 0.0 <= result[key] <= 10.0, f"{key} out of range: {result[key]}"


@pytest.mark.asyncio
async def test_senior_score_with_good_transport(db_session, admin_user):
    """Good transport + hospitals -> high senior score."""
    enrichment = {
        "osm_amenities": {
            "hospitals": 2,
            "pharmacies": 3,
            "supermarkets": 2,
            "post_offices": 1,
        },
        "transport": {"transport_quality_class": "A"},
        "climate": {"estimated_altitude_m": 400},
    }
    building = await _create_building(db_session, admin_user, enrichment=enrichment)
    result = await analyze_amenities(db_session, building.id)

    assert result["senior_score"] >= 5.0


@pytest.mark.asyncio
async def test_remote_work_quiet_connected(db_session, admin_user):
    """Quiet + connected + cafes -> high remote work score."""
    enrichment = {
        "osm_amenities": {
            "cafes": 6,
            "parks": 3,
        },
        "noise": {"road_noise_day_db": 38},
        "connectivity_score": 9.0,
    }
    building = await _create_building(db_session, admin_user, enrichment=enrichment)
    result = await analyze_amenities(db_session, building.id)

    assert result["remote_work_score"] >= 6.0


@pytest.mark.asyncio
async def test_daily_needs_close(db_session, admin_user):
    """Supermarket + pharmacy + post all present -> good daily needs score."""
    enrichment = {
        "osm_amenities": {
            "supermarkets": 3,
            "pharmacies": 2,
            "post_offices": 1,
        },
    }
    building = await _create_building(db_session, admin_user, enrichment=enrichment)
    result = await analyze_amenities(db_session, building.id)

    assert result["daily_needs_score"] >= 5.0
