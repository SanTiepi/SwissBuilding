"""Tests for shadow analysis service (Programme W)."""

import uuid

import pytest

from app.models.building import Building
from app.services.shadow_analysis_service import (
    _cardinal,
    _shadow_length,
    _solar_panel_impact,
    compute_shadow_impact,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CENTER_LAT = 46.5197
_CENTER_LON = 6.6323


def _make_building(created_by_id, lat=_CENTER_LAT, lon=_CENTER_LON, **kwargs):
    return Building(
        id=kwargs.get("id", uuid.uuid4()),
        address=kwargs.get("address", "Rue Test 1"),
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=kwargs.get("construction_year", 1970),
        building_type="residential",
        created_by=created_by_id,
        status="active",
        latitude=lat,
        longitude=lon,
        floors_above=kwargs.get("floors_above", 3),
        source_metadata_json=kwargs.get("source_metadata_json"),
    )


# ---------------------------------------------------------------------------
# compute_shadow_impact tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shadow_from_tall_building_south(db_session, admin_user):
    """Tall building to the south should cast significant winter shadow."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON, floors_above=3)
    # Building to the south (~40m away), much taller
    south_tower = _make_building(
        admin_user.id,
        _CENTER_LAT - 0.0004,  # south = lower latitude
        _CENTER_LON,
        floors_above=12,
        address="Tour Sud",
    )
    db_session.add_all([center, south_tower])
    await db_session.commit()

    result = await compute_shadow_impact(db_session, center.id)
    assert result["coordinates_available"] is True
    assert len(result["shadow_sources"]) > 0
    assert result["winter_shadow_hours"] > 0
    # Winter shadow should be worse than summer
    assert result["winter_shadow_hours"] >= result["summer_shadow_hours"]


@pytest.mark.asyncio
async def test_no_shadow_from_short_neighbors(db_session, admin_user):
    """Shorter or equal height neighbors should not cast shadows."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON, floors_above=5)
    # Shorter neighbor to the south
    short = _make_building(
        admin_user.id,
        _CENTER_LAT - 0.0004,
        _CENTER_LON,
        floors_above=3,
        address="Petit voisin",
    )
    db_session.add_all([center, short])
    await db_session.commit()

    result = await compute_shadow_impact(db_session, center.id)
    assert len(result["shadow_sources"]) == 0
    assert result["winter_shadow_hours"] == 0.0
    assert result["summer_shadow_hours"] == 0.0


@pytest.mark.asyncio
async def test_no_shadow_from_north(db_session, admin_user):
    """Tall building to the north should not cast shadows on us."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON, floors_above=3)
    # Tall building to the north
    north_tower = _make_building(
        admin_user.id,
        _CENTER_LAT + 0.0004,  # north = higher latitude
        _CENTER_LON,
        floors_above=15,
        address="Tour Nord",
    )
    db_session.add_all([center, north_tower])
    await db_session.commit()

    result = await compute_shadow_impact(db_session, center.id)
    # Building to the north shouldn't create shadow (sun is from the south)
    assert result["winter_shadow_hours"] == 0.0


@pytest.mark.asyncio
async def test_shadow_solar_panel_impact(db_session, admin_user):
    """Heavy shadow should indicate solar panel impact."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON, floors_above=2)
    # Very tall, very close to the south
    tower = _make_building(
        admin_user.id,
        _CENTER_LAT - 0.0002,  # ~20m south
        _CENTER_LON,
        floors_above=20,
        address="Grande Tour",
    )
    db_session.add_all([center, tower])
    await db_session.commit()

    result = await compute_shadow_impact(db_session, center.id)
    assert result["solar_panel_impact"] in ("minor", "significant", "severe")


@pytest.mark.asyncio
async def test_shadow_no_neighbors(db_session, admin_user):
    """Isolated building should have no shadow impact."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON)
    db_session.add(center)
    await db_session.commit()

    result = await compute_shadow_impact(db_session, center.id)
    assert result["shadow_sources"] == []
    assert result["winter_shadow_hours"] == 0.0
    assert result["solar_panel_impact"] == "none"
    assert "potentiel solaire" in result["recommendation"].lower() or "ombrage" in result["recommendation"].lower()


@pytest.mark.asyncio
async def test_shadow_no_coordinates(db_session, admin_user):
    """Building without coordinates should return graceful result."""
    b = Building(
        id=uuid.uuid4(),
        address="No coords",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        latitude=None,
        longitude=None,
    )
    db_session.add(b)
    await db_session.commit()

    result = await compute_shadow_impact(db_session, b.id)
    assert result["coordinates_available"] is False
    assert result["solar_panel_impact"] == "unknown"


@pytest.mark.asyncio
async def test_shadow_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await compute_shadow_impact(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_shadow_with_osm_height_data(db_session, admin_user):
    """Building with OSM height data should use it."""
    center = _make_building(
        admin_user.id,
        _CENTER_LAT,
        _CENTER_LON,
        floors_above=3,
        source_metadata_json={"osm_building": {"height": "9.5"}},
    )
    tower = _make_building(
        admin_user.id,
        _CENTER_LAT - 0.0003,
        _CENTER_LON,
        floors_above=10,
        address="Voisin haut",
        source_metadata_json={"osm_building": {"height": "32.0"}},
    )
    db_session.add_all([center, tower])
    await db_session.commit()

    result = await compute_shadow_impact(db_session, center.id)
    assert result["building_height_m"] == 9.5
    if result["shadow_sources"]:
        assert result["shadow_sources"][0]["height_m"] == 32.0


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


def test_shadow_length_winter():
    """20-degree sun angle, 10m height diff -> long shadow."""
    length = _shadow_length(10, 20)
    assert length > 25  # tan(20) ≈ 0.364, so 10/0.364 ≈ 27.5m


def test_shadow_length_summer():
    """66-degree sun angle, 10m height diff -> short shadow."""
    length = _shadow_length(10, 66)
    assert length < 5  # tan(66) ≈ 2.24, so 10/2.24 ≈ 4.5m


def test_solar_panel_impact_none():
    assert _solar_panel_impact(0.0, 0.0) == "none"


def test_solar_panel_impact_severe():
    assert _solar_panel_impact(4.0, 2.0) == "severe"


def test_cardinal_directions():
    assert _cardinal(0) == "north"
    assert _cardinal(90) == "east"
    assert _cardinal(180) == "south"
    assert _cardinal(270) == "west"
    assert _cardinal(45) == "northeast"
    assert _cardinal(135) == "southeast"
    assert _cardinal(225) == "southwest"
    assert _cardinal(315) == "northwest"
