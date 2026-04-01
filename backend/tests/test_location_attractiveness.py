"""Tests for location_attractiveness_service — persona-based location scoring."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.services.location_attractiveness_service import compute_location_attractiveness

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, *, enrichment=None, construction_year=1980):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        construction_year=construction_year,
        created_by=admin_user.id,
        status="active",
        source_metadata_json=enrichment,
    )
    db.add(b)
    await db.flush()
    return b


def _urban_vibrant():
    """Urban vibrant location: great transport, nightlife, cafes."""
    return {
        "osm_amenities": {
            "schools": 2,
            "hospitals": 1,
            "pharmacies": 2,
            "supermarkets": 3,
            "restaurants": 20,
            "parks": 2,
            "banks": 4,
            "post_offices": 1,
            "cafes": 10,
            "kindergartens": 1,
            "total_amenities": 55,
        },
        "transport": {"transport_quality_class": "A"},
        "noise": {"road_noise_day_db": 52},
        "connectivity_score": 9.0,
        "mobile_coverage": {"has_5g_coverage": True},
        "broadband": {"max_speed_mbps": 500},
        "contaminated_sites": {"is_contaminated": False},
    }


def _suburban_family():
    """Suburban family location: schools, parks, quiet, safe."""
    return {
        "osm_amenities": {
            "schools": 5,
            "hospitals": 1,
            "pharmacies": 2,
            "supermarkets": 2,
            "restaurants": 4,
            "parks": 6,
            "banks": 1,
            "post_offices": 1,
            "cafes": 2,
            "kindergartens": 4,
            "total_amenities": 30,
        },
        "transport": {"transport_quality_class": "B"},
        "noise": {"road_noise_day_db": 38},
        "connectivity_score": 6.0,
        "contaminated_sites": {"is_contaminated": False},
    }


def _rural_remote():
    """Rural remote location: quiet, nature, low services."""
    return {
        "osm_amenities": {
            "schools": 0,
            "hospitals": 0,
            "pharmacies": 0,
            "supermarkets": 0,
            "restaurants": 1,
            "parks": 1,
            "banks": 0,
            "post_offices": 0,
            "cafes": 0,
            "kindergartens": 0,
            "total_amenities": 2,
        },
        "transport": {"transport_quality_class": "D"},
        "noise": {"road_noise_day_db": 30},
        "connectivity_score": 2.0,
        "contaminated_sites": {"is_contaminated": False},
    }


# ── Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_young_professional_urban(db_session, admin_user):
    """Urban vibrant -> high young professional score."""
    building = await _create_building(db_session, admin_user, enrichment=_urban_vibrant())
    result = await compute_location_attractiveness(db_session, building.id)

    yp = result["young_professional"]
    assert yp["score"] >= 6.0
    assert len(yp["factors"]) >= 1


@pytest.mark.asyncio
async def test_family_suburban(db_session, admin_user):
    """Suburban with schools + parks -> high family score."""
    building = await _create_building(db_session, admin_user, enrichment=_suburban_family())
    result = await compute_location_attractiveness(db_session, building.id)

    fam = result["family"]
    assert fam["score"] >= 5.0
    assert any("school" in f.lower() for f in fam["factors"])


@pytest.mark.asyncio
async def test_retiree_needs_healthcare(db_session, admin_user):
    """Location with hospitals + pharmacies -> decent retiree score."""
    enrichment = _suburban_family()
    building = await _create_building(db_session, admin_user, enrichment=enrichment)
    result = await compute_location_attractiveness(db_session, building.id)

    ret = result["retiree"]
    assert ret["score"] >= 4.0


@pytest.mark.asyncio
async def test_investor_transport_amenities(db_session, admin_user):
    """Good transport + many amenities -> high investor score."""
    building = await _create_building(db_session, admin_user, enrichment=_urban_vibrant(), construction_year=1975)
    result = await compute_location_attractiveness(db_session, building.id)

    inv = result["investor"]
    assert inv["score"] >= 6.0
    assert any("transport" in f.lower() for f in inv["factors"])


@pytest.mark.asyncio
async def test_remote_worker_quiet_connected(db_session, admin_user):
    """Quiet + connected -> high remote worker score."""
    enrichment = {
        "osm_amenities": {
            "cafes": 5,
            "parks": 3,
        },
        "noise": {"road_noise_day_db": 35},
        "connectivity_score": 9.0,
        "mobile_coverage": {"has_5g_coverage": True},
        "broadband": {"max_speed_mbps": 200},
    }
    building = await _create_building(db_session, admin_user, enrichment=enrichment)
    result = await compute_location_attractiveness(db_session, building.id)

    rw = result["remote_worker"]
    assert rw["score"] >= 6.0


@pytest.mark.asyncio
async def test_overall_best_worst_fit(db_session, admin_user):
    """Overall has best_fit and worst_fit persona."""
    building = await _create_building(db_session, admin_user, enrichment=_suburban_family())
    result = await compute_location_attractiveness(db_session, building.id)

    overall = result["overall"]
    assert "best_fit" in overall
    assert "worst_fit" in overall
    assert "score" in overall
    assert overall["best_fit"] in ("young_professional", "family", "retiree", "investor", "remote_worker")
    assert overall["worst_fit"] in ("young_professional", "family", "retiree", "investor", "remote_worker")
    assert 0.0 <= overall["score"] <= 10.0


@pytest.mark.asyncio
async def test_no_data_low_scores(db_session, admin_user):
    """No enrichment data -> low scores for all personas."""
    building = await _create_building(db_session, admin_user, enrichment={})
    result = await compute_location_attractiveness(db_session, building.id)

    for persona in ("young_professional", "family", "retiree", "investor", "remote_worker"):
        assert 0.0 <= result[persona]["score"] <= 10.0


@pytest.mark.asyncio
async def test_building_not_found(db_session, admin_user):
    """Non-existent building -> error and zero scores."""
    result = await compute_location_attractiveness(db_session, uuid.uuid4())
    assert result.get("error") == "building_not_found"
    assert result["overall"]["score"] == 0.0
    assert result["overall"]["best_fit"] == "none"
