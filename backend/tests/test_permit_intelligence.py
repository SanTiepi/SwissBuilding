"""Tests for the Permit Intelligence Service."""

import uuid
from datetime import datetime, timedelta

import pytest

from app.models.building import Building
from app.models.permit_procedure import PermitProcedure
from app.models.user import User
from app.services.permit_intelligence_service import (
    _check_no_permit_flag,
    _generate_permit_insights,
    analyze_permit_history,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(db):
    user = User(
        id=uuid.uuid4(),
        email=f"permit-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Permit",
        last_name="Tester",
        role="admin",
        is_active=True,
        language="fr",
    )
    db.add(user)
    await db.flush()
    return user


async def _create_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_permit(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "procedure_type": "construction_permit",
        "title": "Renovation toiture",
        "status": "approved",
        "submitted_at": datetime(2020, 3, 15),
        "approved_at": datetime(2020, 6, 1),
        "authority_name": "Commune de Lausanne",
    }
    defaults.update(kwargs)
    p = PermitProcedure(**defaults)
    db.add(p)
    await db.flush()
    return p


# ---------------------------------------------------------------------------
# Full analysis tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_with_permits(db_session):
    """Analysis with permits returns structured data."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    await _create_permit(db_session, building.id)
    await _create_permit(
        db_session,
        building.id,
        procedure_type="suva_notification",
        title="Notification amiante",
        submitted_at=datetime(2022, 1, 10),
        approved_at=datetime(2022, 2, 5),
    )
    await db_session.commit()

    result = await analyze_permit_history(db_session, building.id)

    assert result["total_permits"] == 2
    assert result["last_permit"] is not None
    assert result["years_since_last_permit"] is not None
    assert result["building_without_permit_flag"] is False  # has recent permits
    assert isinstance(result["permits"], list)
    assert len(result["permits"]) == 2


@pytest.mark.asyncio
async def test_analyze_no_permits(db_session):
    """Building with no permits returns empty list."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    await db_session.commit()

    result = await analyze_permit_history(db_session, building.id)

    assert result["total_permits"] == 0
    assert result["last_permit"] is None
    assert result["years_since_last_permit"] is None
    assert result["permits"] == []


@pytest.mark.asyncio
async def test_no_permit_flag_old_building(db_session):
    """Pre-1990 building with no permits gets flagged."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id, construction_year=1960)
    await db_session.commit()

    result = await analyze_permit_history(db_session, building.id)

    assert result["building_without_permit_flag"] is True
    assert any("non declares" in i for i in result["insights"])


@pytest.mark.asyncio
async def test_no_flag_recent_building(db_session):
    """Post-1990 building without permits is NOT flagged."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id, construction_year=2005)
    await db_session.commit()

    result = await analyze_permit_history(db_session, building.id)

    assert result["building_without_permit_flag"] is False


@pytest.mark.asyncio
async def test_no_permit_flag_old_permit(db_session):
    """Pre-1990 building with old permit (20+ years ago) gets flagged."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id, construction_year=1960)
    await _create_permit(
        db_session,
        building.id,
        submitted_at=datetime(2000, 1, 1),
        approved_at=datetime(2000, 6, 1),
    )
    await db_session.commit()

    result = await analyze_permit_history(db_session, building.id)

    assert result["building_without_permit_flag"] is True
    assert result["years_since_last_permit"] >= 20


@pytest.mark.asyncio
async def test_recent_permit_insight(db_session):
    """Recent permit generates 'recent activity' insight."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    now = datetime.now()
    await _create_permit(
        db_session,
        building.id,
        submitted_at=now - timedelta(days=180),
        approved_at=now - timedelta(days=30),
    )
    await db_session.commit()

    result = await analyze_permit_history(db_session, building.id)

    assert result["years_since_last_permit"] is not None
    assert result["years_since_last_permit"] <= 1


@pytest.mark.asyncio
async def test_rejected_permit_insight(db_session):
    """Rejected permits generate a warning insight."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    await _create_permit(db_session, building.id, status="rejected")
    await db_session.commit()

    result = await analyze_permit_history(db_session, building.id)

    assert any("refuse" in i for i in result["insights"])


@pytest.mark.asyncio
async def test_analyze_not_found(db_session):
    """Non-existent building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await analyze_permit_history(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


class TestCheckNoPermitFlag:
    def test_pre_1990_no_permits(self):
        assert _check_no_permit_flag(construction_year=1960, total_permits=0, years_since_last=None) is True

    def test_pre_1990_old_permit(self):
        assert _check_no_permit_flag(construction_year=1960, total_permits=1, years_since_last=25) is True

    def test_pre_1990_recent_permit(self):
        assert _check_no_permit_flag(construction_year=1960, total_permits=1, years_since_last=5) is False

    def test_post_1990_no_permits(self):
        assert _check_no_permit_flag(construction_year=2000, total_permits=0, years_since_last=None) is False

    def test_no_construction_year(self):
        assert _check_no_permit_flag(construction_year=None, total_permits=0, years_since_last=None) is False


class TestGeneratePermitInsights:
    def test_no_permits(self):
        insights = _generate_permit_insights(
            construction_year=2000,
            total_permits=0,
            last_permit=None,
            years_since_last=None,
            building_without_permit_flag=False,
            permits=[],
        )
        assert any("aucun" in i.lower() for i in insights)

    def test_flagged_building(self):
        insights = _generate_permit_insights(
            construction_year=1960,
            total_permits=0,
            last_permit=None,
            years_since_last=None,
            building_without_permit_flag=True,
            permits=[],
        )
        assert any("non declares" in i for i in insights)

    def test_pending_permits(self):
        permits = [
            {
                "type": "construction_permit",
                "date": "2025-01-01",
                "status": "submitted",
                "authority": "test",
                "description": "test",
            }
        ]
        insights = _generate_permit_insights(
            construction_year=1970,
            total_permits=1,
            last_permit={"type": "construction_permit", "date": "2025-01-01"},
            years_since_last=1,
            building_without_permit_flag=False,
            permits=permits,
        )
        assert any("en cours" in i for i in insights)
