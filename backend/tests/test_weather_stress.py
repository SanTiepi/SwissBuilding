"""Tests for weather stress service (Programme S)."""

import uuid

import pytest

from app.models.building import Building
from app.services.weather_stress_service import (
    _compute_facade_scores,
    _score_to_grade,
    _score_to_level,
    compute_facade_stress,
    compute_optimal_work_season,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_building(created_by_id, climate=None, **kwargs):
    meta = {}
    if climate:
        meta["climate"] = climate
    return Building(
        id=uuid.uuid4(),
        address=kwargs.get("address", "Rue Test 1"),
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=kwargs.get("construction_year", 1970),
        building_type="residential",
        created_by=created_by_id,
        status="active",
        latitude=kwargs.get("latitude", 46.52),
        longitude=kwargs.get("longitude", 6.63),
        source_metadata_json=meta if meta else None,
    )


_LAUSANNE_CLIMATE = {
    "avg_temp_c": 9.5,
    "precipitation_mm": 1100,
    "frost_days": 80,
    "sunshine_hours": 1650,
    "heating_degree_days": 2300,
    "tropical_days": 3,
    "estimated_altitude_m": 500,
}

_ALPINE_CLIMATE = {
    "avg_temp_c": 2.0,
    "precipitation_mm": 1800,
    "frost_days": 170,
    "sunshine_hours": 1400,
    "heating_degree_days": 4000,
    "tropical_days": 0,
    "estimated_altitude_m": 1800,
}

_WARM_CLIMATE = {
    "avg_temp_c": 12.0,
    "precipitation_mm": 850,
    "frost_days": 45,
    "sunshine_hours": 2000,
    "heating_degree_days": 1750,
    "tropical_days": 15,
    "estimated_altitude_m": 300,
}


# ---------------------------------------------------------------------------
# compute_facade_stress tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_facade_stress_lausanne(db_session, admin_user):
    """Standard plateau building should have moderate stress."""
    b = _make_building(admin_user.id, climate=_LAUSANNE_CLIMATE)
    db_session.add(b)
    await db_session.commit()

    result = await compute_facade_stress(db_session, b.id)
    assert result["climate_data_available"] is True
    assert "facades" in result
    assert set(result["facades"].keys()) == {"north", "south", "east", "west"}
    assert result["most_stressed_facade"] is not None
    assert result["overall_stress_grade"] in ("A", "B", "C", "D", "E")
    assert len(result["recommendations"]) > 0


@pytest.mark.asyncio
async def test_facade_stress_alpine(db_session, admin_user):
    """Alpine building should have high frost on north facade."""
    b = _make_building(admin_user.id, climate=_ALPINE_CLIMATE)
    db_session.add(b)
    await db_session.commit()

    result = await compute_facade_stress(db_session, b.id)
    north = result["facades"]["north"]
    assert north["frost"] in ("high", "critical")
    # North should be among the most stressed
    assert result["most_stressed_facade"] in ("north", "east")
    # Should recommend frost inspection
    recs = " ".join(result["recommendations"])
    assert "gel" in recs.lower() or "frost" in recs.lower() or "UV" in recs


@pytest.mark.asyncio
async def test_facade_stress_warm_low_altitude(db_session, admin_user):
    """Warm low-altitude building (Ticino-like) should have low frost."""
    b = _make_building(admin_user.id, climate=_WARM_CLIMATE)
    db_session.add(b)
    await db_session.commit()

    result = await compute_facade_stress(db_session, b.id)
    north = result["facades"]["north"]
    # Low frost days = low frost score
    assert north["frost"] in ("low", "medium")
    # South should have relatively higher UV
    south = result["facades"]["south"]
    assert south["uv_score"] > north["uv_score"]


@pytest.mark.asyncio
async def test_facade_stress_no_climate_data(db_session, admin_user):
    """Building without climate data should return graceful empty result."""
    b = _make_building(admin_user.id, climate=None)
    db_session.add(b)
    await db_session.commit()

    result = await compute_facade_stress(db_session, b.id)
    assert result["climate_data_available"] is False
    assert result["facades"] == {}
    assert result["most_stressed_facade"] is None
    assert result["overall_stress_grade"] is None
    assert len(result["recommendations"]) == 1


@pytest.mark.asyncio
async def test_facade_stress_building_not_found(db_session):
    """Should raise ValueError for non-existent building."""
    with pytest.raises(ValueError, match="not found"):
        await compute_facade_stress(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_south_facade_higher_uv_than_north(db_session, admin_user):
    """South facade should always have higher UV than north."""
    b = _make_building(admin_user.id, climate=_LAUSANNE_CLIMATE)
    db_session.add(b)
    await db_session.commit()

    result = await compute_facade_stress(db_session, b.id)
    assert result["facades"]["south"]["uv_score"] > result["facades"]["north"]["uv_score"]


@pytest.mark.asyncio
async def test_north_facade_higher_frost_than_south(db_session, admin_user):
    """North facade should always have higher frost than south."""
    b = _make_building(admin_user.id, climate=_LAUSANNE_CLIMATE)
    db_session.add(b)
    await db_session.commit()

    result = await compute_facade_stress(db_session, b.id)
    assert result["facades"]["north"]["frost_score"] > result["facades"]["south"]["frost_score"]


# ---------------------------------------------------------------------------
# compute_optimal_work_season tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_work_season_lausanne(db_session, admin_user):
    """Standard building should recommend summer months for exterior work."""
    b = _make_building(admin_user.id, climate=_LAUSANNE_CLIMATE)
    db_session.add(b)
    await db_session.commit()

    result = await compute_optimal_work_season(db_session, b.id)
    assert result["climate_data_available"] is True
    ext_months = result["exterior"]["best_months"]
    # Summer months should be included
    assert any(m in ext_months for m in [6, 7, 8])
    # Winter months should be worst
    assert 1 in result["worst_months"] or 12 in result["worst_months"]
    assert result["exterior"]["confidence"] > 0.3


@pytest.mark.asyncio
async def test_work_season_alpine_shorter(db_session, admin_user):
    """Alpine building should have fewer good exterior months."""
    b = _make_building(admin_user.id, climate=_ALPINE_CLIMATE)
    db_session.add(b)
    await db_session.commit()

    result = await compute_optimal_work_season(db_session, b.id)
    ext_months = result["exterior"]["best_months"]
    # Fewer good months at high altitude
    assert len(ext_months) <= 7  # At most 7 months


@pytest.mark.asyncio
async def test_work_season_no_climate_data(db_session, admin_user):
    """No climate data should return sensible defaults."""
    b = _make_building(admin_user.id, climate=None)
    db_session.add(b)
    await db_session.commit()

    result = await compute_optimal_work_season(db_session, b.id)
    assert result["climate_data_available"] is False
    assert result["exterior"]["best_months"] == [5, 6, 7, 8, 9]
    assert result["exterior"]["confidence"] == 0.5


@pytest.mark.asyncio
async def test_work_season_building_not_found(db_session):
    """Should raise ValueError for non-existent building."""
    with pytest.raises(ValueError, match="not found"):
        await compute_optimal_work_season(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Pure function unit tests
# ---------------------------------------------------------------------------


def test_score_to_level():
    assert _score_to_level(0.0) == "low"
    assert _score_to_level(0.29) == "low"
    assert _score_to_level(0.3) == "medium"
    assert _score_to_level(0.59) == "medium"
    assert _score_to_level(0.6) == "high"
    assert _score_to_level(0.84) == "high"
    assert _score_to_level(0.85) == "critical"
    assert _score_to_level(1.0) == "critical"


def test_score_to_grade():
    assert _score_to_grade(0.1) == "A"
    assert _score_to_grade(0.3) == "B"
    assert _score_to_grade(0.5) == "C"
    assert _score_to_grade(0.7) == "D"
    assert _score_to_grade(0.9) == "E"


def test_facade_scores_keys():
    """All four orientations should be present."""
    scores = _compute_facade_scores(_LAUSANNE_CLIMATE)
    assert set(scores.keys()) == {"north", "south", "east", "west"}
    for orient in scores.values():
        assert "uv" in orient
        assert "frost" in orient
        assert "wind" in orient
        assert "rain" in orient
        assert "overall" in orient
        assert "overall_score" in orient
