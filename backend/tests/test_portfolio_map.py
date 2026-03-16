"""Tests for the portfolio map-buildings endpoint."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.user import User

pytestmark = pytest.mark.anyio


def _make_token(user_id: str) -> str:
    """Create a JWT token for the given user id."""
    payload = {
        "sub": user_id,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")


@pytest.fixture
async def admin_with_token(db_session):
    """Create an admin user and return (user, token, headers)."""
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email="map-admin@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Map",
        last_name="Admin",
        role="admin",
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token = _make_token(str(user.id))
    return user, token, {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def buildings_with_coords(db_session, admin_with_token):
    """Create buildings, some with coordinates and some without."""
    user, _, _ = admin_with_token

    buildings = []
    coords = [
        (6.6323, 46.5197, "VD"),
        (6.1466, 46.2044, "GE"),
        (7.4474, 46.9480, "BE"),
        (None, None, "ZH"),  # No coordinates
    ]

    for i, (lon, lat, canton) in enumerate(coords):
        b = Building(
            id=uuid.uuid4(),
            address=f"Test Street {i + 1}",
            postal_code="1000",
            city=f"City{i + 1}",
            canton=canton,
            building_type="residential",
            created_by=user.id,
            status="active",
            longitude=lon,
            latitude=lat,
            construction_year=1960 + i * 10,
        )
        db_session.add(b)
        buildings.append(b)

    await db_session.commit()
    for b in buildings:
        await db_session.refresh(b)

    # Add risk scores for the first 3 buildings (those with coordinates)
    risk_levels = ["high", "critical", "low"]
    for i, b in enumerate(buildings[:3]):
        risk = BuildingRiskScore(
            id=uuid.uuid4(),
            building_id=b.id,
            overall_risk_level=risk_levels[i],
            confidence=0.5 + i * 0.15,
        )
        db_session.add(risk)

    await db_session.commit()
    return buildings


async def test_returns_geojson_feature_collection(client, admin_with_token, buildings_with_coords):
    """Endpoint returns a valid GeoJSON FeatureCollection."""
    _, _, headers = admin_with_token
    resp = await client.get("/api/v1/portfolio/map-buildings", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert isinstance(data["features"], list)


async def test_feature_has_required_properties(client, admin_with_token, buildings_with_coords):
    """Each feature has the required properties."""
    _, _, headers = admin_with_token
    resp = await client.get("/api/v1/portfolio/map-buildings", headers=headers)
    data = resp.json()
    assert len(data["features"]) > 0

    for feature in data["features"]:
        assert feature["type"] == "Feature"
        props = feature["properties"]
        assert "id" in props
        assert "address" in props
        assert "city" in props
        assert "canton" in props
        assert "overall_risk_level" in props
        assert "risk_score" in props
        assert "completeness_score" in props
        assert "construction_year" in props


async def test_geometry_type_is_point(client, admin_with_token, buildings_with_coords):
    """Each feature geometry is a Point with coordinates."""
    _, _, headers = admin_with_token
    resp = await client.get("/api/v1/portfolio/map-buildings", headers=headers)
    data = resp.json()

    for feature in data["features"]:
        assert feature["geometry"]["type"] == "Point"
        coords = feature["geometry"]["coordinates"]
        assert isinstance(coords, list)
        assert len(coords) == 2


async def test_buildings_without_coordinates_excluded(client, admin_with_token, buildings_with_coords):
    """Buildings without latitude/longitude are excluded."""
    _, _, headers = admin_with_token
    resp = await client.get("/api/v1/portfolio/map-buildings", headers=headers)
    data = resp.json()

    # We created 4 buildings but only 3 have coordinates
    assert len(data["features"]) == 3

    cantons = {f["properties"]["canton"] for f in data["features"]}
    assert "ZH" not in cantons  # The one without coordinates


async def test_risk_level_filter(client, admin_with_token, buildings_with_coords):
    """Risk level filter returns only matching buildings."""
    _, _, headers = admin_with_token

    resp = await client.get("/api/v1/portfolio/map-buildings?risk_level=high", headers=headers)
    data = resp.json()
    assert len(data["features"]) == 1
    assert data["features"][0]["properties"]["overall_risk_level"] == "high"

    # Multiple risk levels
    resp = await client.get("/api/v1/portfolio/map-buildings?risk_level=high,critical", headers=headers)
    data = resp.json()
    assert len(data["features"]) == 2
    levels = {f["properties"]["overall_risk_level"] for f in data["features"]}
    assert levels == {"high", "critical"}


async def test_canton_filter(client, admin_with_token, buildings_with_coords):
    """Canton filter returns only buildings in the specified canton."""
    _, _, headers = admin_with_token

    resp = await client.get("/api/v1/portfolio/map-buildings?canton=VD", headers=headers)
    data = resp.json()
    assert len(data["features"]) == 1
    assert data["features"][0]["properties"]["canton"] == "VD"


async def test_empty_result_when_no_buildings_with_coords(client, admin_with_token, db_session):
    """Returns empty FeatureCollection when no buildings have coordinates."""
    user, _, headers = admin_with_token

    # Create a building without coordinates
    b = Building(
        id=uuid.uuid4(),
        address="No Coords Street 1",
        postal_code="1000",
        city="Nowhere",
        canton="VD",
        building_type="residential",
        created_by=user.id,
        status="active",
        longitude=None,
        latitude=None,
    )
    db_session.add(b)
    await db_session.commit()

    resp = await client.get("/api/v1/portfolio/map-buildings", headers=headers)
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 0


async def test_authenticated_user_can_access(client, admin_with_token, buildings_with_coords):
    """Authenticated user with buildings read permission can access the endpoint."""
    _, _, headers = admin_with_token
    resp = await client.get("/api/v1/portfolio/map-buildings", headers=headers)
    assert resp.status_code == 200


async def test_unauthenticated_user_rejected(client):
    """Unauthenticated user is rejected."""
    resp = await client.get("/api/v1/portfolio/map-buildings")
    assert resp.status_code in (401, 403)
