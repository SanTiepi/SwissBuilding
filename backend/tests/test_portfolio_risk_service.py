"""Tests for the Portfolio Risk Service."""

from __future__ import annotations

import uuid

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.organization import Organization
from app.models.user import User
from app.services.portfolio_risk_service import (
    _grade_to_risk_level,
    get_portfolio_risk_overview,
    get_risk_heatmap_data,
)

# ── Helpers ───────────���────────────────────────────────────────────


async def _create_org(db, name="TestOrg"):
    org = Organization(id=uuid.uuid4(), name=name, type="property_management")
    db.add(org)
    await db.flush()
    return org


async def _create_user(db, org_id, email="user@test.ch"):
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash="$2b$12$LJ3m4ys3uz3Det6vuDfl3eAb3dHKX/hZ3R8VBYGIzBz4m8M0mZ9Fi",
        first_name="Test",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org_id,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_building(db, created_by, org_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": created_by,
        "organization_id": org_id,
        "status": "active",
        "latitude": 46.5,
        "longitude": 6.6,
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_action(db, building_id, priority="medium", status="open"):
    a = ActionItem(
        id=uuid.uuid4(),
        building_id=building_id,
        source_type="manual",
        action_type="inspection",
        title="Test action",
        priority=priority,
        status=status,
    )
    db.add(a)
    await db.flush()
    return a


# ── Unit tests ────────────────────────────────────────────────────


class TestGradeToRiskLevel:
    def test_grade_a_is_low(self):
        assert _grade_to_risk_level("A") == "low"

    def test_grade_b_is_low(self):
        assert _grade_to_risk_level("B") == "low"

    def test_grade_c_is_medium(self):
        assert _grade_to_risk_level("C") == "medium"

    def test_grade_d_is_high(self):
        assert _grade_to_risk_level("D") == "high"

    def test_grade_f_is_critical(self):
        assert _grade_to_risk_level("F") == "critical"

    def test_unknown_grade(self):
        assert _grade_to_risk_level("X") == "unknown"


# ── Integration tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_org(db_session):
    """An org with no buildings returns empty overview."""
    org = await _create_org(db_session, "EmptyOrg")
    await _create_user(db_session, org.id, "empty@test.ch")
    await db_session.commit()

    result = await get_portfolio_risk_overview(db_session, org.id)

    assert result["total_buildings"] == 0
    assert result["avg_evidence_score"] == 0.0
    assert result["buildings_at_risk"] == 0
    assert result["buildings_ok"] == 0
    assert result["worst_building_id"] is None
    assert result["buildings"] == []
    assert result["distribution"]["grade_a"] == 0


@pytest.mark.asyncio
async def test_overview_with_buildings(db_session):
    """Overview includes building data and correct counts."""
    org = await _create_org(db_session, "TestOrgRisk")
    user = await _create_user(db_session, org.id, "risk@test.ch")

    b1 = await _create_building(db_session, user.id, org.id, city="Lausanne")
    b2 = await _create_building(db_session, user.id, org.id, city="Geneva")

    # Add some actions
    await _create_action(db_session, b1.id, priority="critical", status="open")
    await _create_action(db_session, b1.id, priority="medium", status="open")
    await _create_action(db_session, b2.id, priority="low", status="completed")
    await db_session.commit()

    result = await get_portfolio_risk_overview(db_session, org.id)

    assert result["total_buildings"] == 2
    assert len(result["buildings"]) == 2
    assert isinstance(result["avg_evidence_score"], float)
    assert result["worst_building_id"] is not None

    # Distribution should sum to total
    dist = result["distribution"]
    total_in_dist = dist["grade_a"] + dist["grade_b"] + dist["grade_c"] + dist["grade_d"] + dist["grade_f"]
    assert total_in_dist == 2


@pytest.mark.asyncio
async def test_distribution_counts(db_session):
    """Distribution counts should match building grades."""
    org = await _create_org(db_session, "DistOrg")
    user = await _create_user(db_session, org.id, "dist@test.ch")

    # Create 3 buildings (all will get F-grade with no evidence in test DB)
    for i in range(3):
        await _create_building(db_session, user.id, org.id, city=f"City{i}")

    await db_session.commit()

    result = await get_portfolio_risk_overview(db_session, org.id)

    dist = result["distribution"]
    total = dist["grade_a"] + dist["grade_b"] + dist["grade_c"] + dist["grade_d"] + dist["grade_f"]
    assert total == 3


@pytest.mark.asyncio
async def test_heatmap_data_format(db_session):
    """Heatmap returns correct minimal format with lat/lng."""
    org = await _create_org(db_session, "HeatOrg")
    user = await _create_user(db_session, org.id, "heat@test.ch")

    await _create_building(db_session, user.id, org.id, latitude=46.5, longitude=6.6)
    # Building without coordinates should be excluded
    await _create_building(db_session, user.id, org.id, latitude=None, longitude=None)
    await db_session.commit()

    result = await get_risk_heatmap_data(db_session, org.id)

    assert len(result) == 1
    point = result[0]
    assert "lat" in point
    assert "lng" in point
    assert "building_id" in point
    assert "score" in point
    assert "grade" in point
    assert "risk_level" in point
    assert "address" in point


@pytest.mark.asyncio
async def test_heatmap_empty_org(db_session):
    """Heatmap for empty org returns empty list."""
    org = await _create_org(db_session, "EmptyHeat")
    await db_session.commit()

    result = await get_risk_heatmap_data(db_session, org.id)
    assert result == []
