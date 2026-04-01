"""Tests for rental benchmark service — Programme R."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.unit import Unit
from app.models.user import User
from app.services.rental_benchmark_service import (
    RENTAL_BENCHMARKS,
    benchmark_rental,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _user(db: AsyncSession) -> User:
    u = User(
        id=uuid.uuid4(),
        email=f"rb-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="RB",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
    )
    db.add(u)
    await db.flush()
    return u


async def _building(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    city: str = "Lausanne",
    canton: str = "VD",
    surface: float | None = 200.0,
) -> Building:
    b = Building(
        id=uuid.uuid4(),
        address=f"Rue Bench {uuid.uuid4().hex[:4]}",
        postal_code="1000",
        city=city,
        canton=canton,
        building_type="residential",
        construction_year=1990,
        surface_area_m2=surface,
        created_by=user_id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _add_unit(
    db: AsyncSession,
    building_id: uuid.UUID,
    *,
    rooms: float = 3.0,
    surface: float = 70.0,
    unit_type: str = "residential",
) -> Unit:
    u = Unit(
        id=uuid.uuid4(),
        building_id=building_id,
        unit_type=unit_type,
        reference_code=f"U-{uuid.uuid4().hex[:6]}",
        rooms=rooms,
        surface_m2=surface,
        status="active",
    )
    db.add(u)
    await db.flush()
    return u


# ===========================================================================
# benchmark_rental
# ===========================================================================


@pytest.mark.asyncio
async def test_benchmark_known_commune(db_session):
    """Lausanne should use specific benchmark rates."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id, city="Lausanne")
    await _add_unit(db_session, bldg.id, rooms=3.0, surface=70.0)
    await db_session.commit()

    result = await benchmark_rental(db_session, bldg.id)
    assert result["city"] == "Lausanne"
    assert len(result["units"]) == 1
    unit = result["units"][0]
    assert unit["benchmark_rate_m2"] == RENTAL_BENCHMARKS["Lausanne"]["3_rooms"]
    assert unit["benchmark_monthly"] == 70 * 19  # Lausanne 3_rooms = 19


@pytest.mark.asyncio
async def test_benchmark_unknown_commune(db_session):
    """Unknown commune should fall back to _default rates."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id, city="Kleinstadt")
    await _add_unit(db_session, bldg.id, rooms=2.0, surface=50.0)
    await db_session.commit()

    result = await benchmark_rental(db_session, bldg.id)
    unit = result["units"][0]
    assert unit["benchmark_rate_m2"] == RENTAL_BENCHMARKS["_default"]["2_rooms"]


@pytest.mark.asyncio
async def test_benchmark_no_units(db_session):
    """Building without units should estimate from building surface."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id, surface=150.0)
    await db_session.commit()

    result = await benchmark_rental(db_session, bldg.id)
    assert len(result["units"]) == 1
    assert result["units"][0]["unit_type"] == "estimated"
    assert result["units"][0]["surface_m2"] == 150.0


@pytest.mark.asyncio
async def test_benchmark_multiple_units(db_session):
    """Multiple units should each get their own benchmark."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id, city="Genève", canton="GE")
    await _add_unit(db_session, bldg.id, rooms=2.0, surface=45.0)
    await _add_unit(db_session, bldg.id, rooms=4.0, surface=90.0)
    await db_session.commit()

    result = await benchmark_rental(db_session, bldg.id)
    assert len(result["units"]) == 2
    # Total benchmark should be sum of both
    total = sum(u["benchmark_monthly"] for u in result["units"])
    assert result["total_benchmark_monthly"] == total


@pytest.mark.asyncio
async def test_benchmark_verdict_at_market(db_session):
    """Unit without lease should default to at_market verdict."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id)
    await _add_unit(db_session, bldg.id, rooms=3.0, surface=70.0)
    await db_session.commit()

    result = await benchmark_rental(db_session, bldg.id)
    # No lease means delta_pct = 0 → at_market
    assert result["units"][0]["verdict"] == "at_market"


@pytest.mark.asyncio
async def test_benchmark_not_found(db_session):
    """Non-existent building should raise ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await benchmark_rental(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_benchmark_annual_rent(db_session):
    """Annual benchmark should be monthly x 12."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id, city="Bern", canton="BE")
    await _add_unit(db_session, bldg.id, rooms=3.0, surface=80.0)
    await db_session.commit()

    result = await benchmark_rental(db_session, bldg.id)
    expected_monthly = 80 * RENTAL_BENCHMARKS["Bern"]["3_rooms"]
    assert result["annual_benchmark_rent"] == expected_monthly * 12


@pytest.mark.asyncio
async def test_benchmark_geneve_rates(db_session):
    """Geneva should have highest benchmark rates."""
    user = await _user(db_session)
    bldg_ge = await _building(db_session, user.id, city="Genève", canton="GE")
    bldg_be = await _building(db_session, user.id, city="Bern", canton="BE")
    await _add_unit(db_session, bldg_ge.id, rooms=3.0, surface=70.0)
    await _add_unit(db_session, bldg_be.id, rooms=3.0, surface=70.0)
    await db_session.commit()

    result_ge = await benchmark_rental(db_session, bldg_ge.id)
    result_be = await benchmark_rental(db_session, bldg_be.id)
    assert result_ge["units"][0]["benchmark_rate_m2"] > result_be["units"][0]["benchmark_rate_m2"]
