"""Tests for neighborhood analysis service (Programme W)."""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.services.neighborhood_analysis_service import (
    _compute_homogeneity,
    _haversine_m,
    analyze_neighborhood,
    compute_neighborhood_risk_propagation,
    detect_construction_activity,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_building(created_by_id, lat=46.52, lon=6.63, **kwargs):
    return Building(
        id=kwargs.get("id", uuid.uuid4()),
        address=kwargs.get("address", "Rue Test 1"),
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=kwargs.get("construction_year", 1970),
        building_type=kwargs.get("building_type", "residential"),
        created_by=created_by_id,
        status="active",
        latitude=lat,
        longitude=lon,
        floors_above=kwargs.get("floors_above", 4),
    )


# Lausanne center: 46.5197, 6.6323
# ~50m offset ≈ 0.00045 degrees latitude
_CENTER_LAT = 46.5197
_CENTER_LON = 6.6323


# ---------------------------------------------------------------------------
# analyze_neighborhood tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_neighborhood_with_nearby_buildings(db_session, admin_user):
    """Should find neighbors within radius."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON, construction_year=1965)
    # Neighbor ~30m away
    n1 = _make_building(
        admin_user.id,
        _CENTER_LAT + 0.0003,
        _CENTER_LON,
        construction_year=1968,
        address="Voisin 1",
    )
    # Neighbor ~50m away
    n2 = _make_building(
        admin_user.id,
        _CENTER_LAT,
        _CENTER_LON + 0.0005,
        construction_year=1972,
        address="Voisin 2",
    )
    db_session.add_all([center, n1, n2])
    await db_session.commit()

    result = await analyze_neighborhood(db_session, center.id, radius_m=100)
    assert result["coordinates_available"] is True
    assert result["buildings_in_radius"] == 2
    assert result["avg_construction_year"] is not None
    assert result["dominant_type"] == "residential"


@pytest.mark.asyncio
async def test_neighborhood_era_distribution(db_session, admin_user):
    """Construction era distribution should reflect neighbor years."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON, construction_year=1965)
    n1 = _make_building(
        admin_user.id,
        _CENTER_LAT + 0.0003,
        _CENTER_LON,
        construction_year=1962,
    )
    n2 = _make_building(
        admin_user.id,
        _CENTER_LAT - 0.0003,
        _CENTER_LON,
        construction_year=1968,
    )
    n3 = _make_building(
        admin_user.id,
        _CENTER_LAT,
        _CENTER_LON + 0.0003,
        construction_year=1985,
    )
    db_session.add_all([center, n1, n2, n3])
    await db_session.commit()

    result = await analyze_neighborhood(db_session, center.id, radius_m=100)
    dist = result["construction_era_distribution"]
    assert "1960-1970" in dist
    assert dist["1960-1970"] >= 2  # n1 and n2


@pytest.mark.asyncio
async def test_neighborhood_homogeneity_high(db_session, admin_user):
    """Buildings from same decade should have high homogeneity."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON, construction_year=1965)
    n1 = _make_building(admin_user.id, _CENTER_LAT + 0.0003, _CENTER_LON, construction_year=1963)
    n2 = _make_building(admin_user.id, _CENTER_LAT - 0.0003, _CENTER_LON, construction_year=1967)
    db_session.add_all([center, n1, n2])
    await db_session.commit()

    result = await analyze_neighborhood(db_session, center.id, radius_m=100)
    assert result["homogeneity_score"] is not None
    assert result["homogeneity_score"] > 70  # Very similar years


@pytest.mark.asyncio
async def test_neighborhood_empty(db_session, admin_user):
    """No neighbors should return empty result."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON)
    db_session.add(center)
    await db_session.commit()

    result = await analyze_neighborhood(db_session, center.id, radius_m=50)
    assert result["buildings_in_radius"] == 0
    assert result["shadow_risk"] == "none"
    assert result["density_score"] == 0.0


@pytest.mark.asyncio
async def test_neighborhood_no_coordinates(db_session, admin_user):
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

    result = await analyze_neighborhood(db_session, b.id, radius_m=100)
    assert result["coordinates_available"] is False
    assert result["buildings_in_radius"] == 0


@pytest.mark.asyncio
async def test_neighborhood_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await analyze_neighborhood(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_neighborhood_with_diagnosed_neighbor(db_session, admin_user):
    """Should detect neighbors with diagnostic findings."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON)
    neighbor = _make_building(admin_user.id, _CENTER_LAT + 0.0003, _CENTER_LON, address="Voisin diag")
    db_session.add_all([center, neighbor])
    await db_session.commit()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=neighbor.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(diag)
    await db_session.commit()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S001",
        pollutant_type="asbestos",
        material_category="floor_tile",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(sample)
    await db_session.commit()

    result = await analyze_neighborhood(db_session, center.id, radius_m=100)
    assert result["has_diagnosed_neighbors"] == 1
    assert len(result["neighbor_findings"]) == 1
    assert result["neighbor_findings"][0]["pollutant"] == "asbestos"


# ---------------------------------------------------------------------------
# detect_construction_activity tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_active_interventions(db_session, admin_user):
    """Should detect nearby buildings with active interventions."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON)
    neighbor = _make_building(admin_user.id, _CENTER_LAT + 0.0003, _CENTER_LON, address="Chantier")
    db_session.add_all([center, neighbor])
    await db_session.commit()

    intv = Intervention(
        id=uuid.uuid4(),
        building_id=neighbor.id,
        intervention_type="asbestos_removal",
        title="Désamiantage",
        status="in_progress",
    )
    db_session.add(intv)
    await db_session.commit()

    result = await detect_construction_activity(db_session, center.id, radius_m=200)
    assert len(result) == 1
    assert result[0]["intervention_type"] == "asbestos_removal"
    assert result[0]["potential_impact"] == "poussière/contamination"


@pytest.mark.asyncio
async def test_detect_no_activity(db_session, admin_user):
    """No active interventions should return empty list."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON)
    db_session.add(center)
    await db_session.commit()

    result = await detect_construction_activity(db_session, center.id)
    assert result == []


# ---------------------------------------------------------------------------
# compute_neighborhood_risk_propagation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_propagation_close_building(db_session, admin_user):
    """Very close building should trigger fire propagation risk."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON)
    # Very close neighbor (~3m)
    very_close = _make_building(
        admin_user.id,
        _CENTER_LAT + 0.00003,
        _CENTER_LON,
        address="Très proche",
        floors_above=6,
    )
    db_session.add_all([center, very_close])
    await db_session.commit()

    result = await compute_neighborhood_risk_propagation(db_session, center.id, radius_m=50)
    assert result["risk_count"] > 0
    risk_types = [r["type"] for r in result["propagation_risks"]]
    # Should detect at least fire or structural risk
    assert any(t in risk_types for t in ["fire_propagation", "structural_subsidence"])


@pytest.mark.asyncio
async def test_propagation_no_neighbors(db_session, admin_user):
    """No neighbors should return no risks."""
    center = _make_building(admin_user.id, _CENTER_LAT, _CENTER_LON)
    db_session.add(center)
    await db_session.commit()

    result = await compute_neighborhood_risk_propagation(db_session, center.id, radius_m=50)
    assert result["risk_count"] == 0
    assert result["highest_severity"] is None


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


def test_homogeneity_identical():
    assert _compute_homogeneity([1965, 1965, 1965]) == 100.0


def test_homogeneity_spread():
    score = _compute_homogeneity([1940, 1970, 2000])
    assert score < 60  # Spread across 60 years


def test_haversine_known_distance():
    """~111km between 1 degree latitude at equator, less in Switzerland."""
    dist = _haversine_m(46.0, 6.0, 47.0, 6.0)
    assert 110_000 < dist < 112_000  # ~111km
