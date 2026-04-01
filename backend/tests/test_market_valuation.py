"""Tests for market valuation service — Programme R."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.user import User
from app.services.market_valuation_service import (
    PRICE_PER_M2_REFERENCE,
    estimate_market_value,
    estimate_renovation_value_impact,
    estimate_rental_yield,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _user(db: AsyncSession) -> User:
    u = User(
        id=uuid.uuid4(),
        email=f"mv-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="MV",
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
    canton: str = "VD",
    building_type: str = "residential",
    surface: float | None = 150.0,
    construction_year: int | None = 1990,
    renovation_year: int | None = None,
) -> Building:
    b = Building(
        id=uuid.uuid4(),
        address=f"Rue Test {uuid.uuid4().hex[:4]}",
        postal_code="1000",
        city="Lausanne",
        canton=canton,
        building_type=building_type,
        construction_year=construction_year,
        renovation_year=renovation_year,
        surface_area_m2=surface,
        created_by=user_id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _add_pollutants(
    db: AsyncSession,
    building_id: uuid.UUID,
    samples: list[dict],
) -> None:
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="pollutant",
        status="completed",
    )
    db.add(diag)
    await db.flush()
    for i, s in enumerate(samples):
        db.add(
            Sample(
                id=uuid.uuid4(),
                diagnostic_id=diag.id,
                sample_number=f"S-{i + 1}",
                pollutant_type=s.get("pollutant_type", "asbestos"),
                risk_level=s.get("risk_level", "high"),
                threshold_exceeded=s.get("threshold_exceeded", True),
            )
        )
    await db.flush()


# ===========================================================================
# estimate_market_value
# ===========================================================================


@pytest.mark.asyncio
async def test_market_value_basic(db_session):
    """Basic value estimation for a VD apartment-type building."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id, surface=100.0, construction_year=2020)
    await db_session.commit()

    result = await estimate_market_value(db_session, bldg.id)
    assert result["price_per_m2"] == PRICE_PER_M2_REFERENCE["VD"]["apartment"]
    assert result["estimated_value_median"] > 0
    assert result["estimated_value_min"] < result["estimated_value_median"] < result["estimated_value_max"]


@pytest.mark.asyncio
async def test_market_value_unknown_canton(db_session):
    """Unknown canton should fall back to default prices."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id, canton="TI", surface=100.0)
    await db_session.commit()

    result = await estimate_market_value(db_session, bldg.id)
    # Should use _DEFAULT_PRICES
    assert result["price_per_m2"] == 7000
    assert result["estimated_value_median"] > 0


@pytest.mark.asyncio
async def test_market_value_age_adjustment(db_session):
    """Old building should have lower value than new one (same surface/canton)."""
    user = await _user(db_session)
    new_bldg = await _building(db_session, user.id, surface=100.0, construction_year=2022)
    old_bldg = await _building(db_session, user.id, surface=100.0, construction_year=1950)
    await db_session.commit()

    new_val = await estimate_market_value(db_session, new_bldg.id)
    old_val = await estimate_market_value(db_session, old_bldg.id)
    assert new_val["estimated_value_median"] > old_val["estimated_value_median"]


@pytest.mark.asyncio
async def test_market_value_pollutant_adjustment(db_session):
    """Building with critical pollutant should be valued lower."""
    user = await _user(db_session)
    clean = await _building(db_session, user.id, surface=100.0, construction_year=2000)
    polluted = await _building(db_session, user.id, surface=100.0, construction_year=2000)
    await _add_pollutants(
        db_session,
        polluted.id,
        [{"pollutant_type": "asbestos", "risk_level": "critical", "threshold_exceeded": True}],
    )
    await db_session.commit()

    clean_val = await estimate_market_value(db_session, clean.id)
    polluted_val = await estimate_market_value(db_session, polluted.id)
    assert clean_val["estimated_value_median"] > polluted_val["estimated_value_median"]


@pytest.mark.asyncio
async def test_market_value_renovation_boost(db_session):
    """Recently renovated building should get condition bonus."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id, surface=100.0, construction_year=1970, renovation_year=2024)
    await db_session.commit()

    result = await estimate_market_value(db_session, bldg.id)
    has_condition = any(a["factor"] == "condition" for a in result["adjustments"])
    assert has_condition


@pytest.mark.asyncio
async def test_market_value_not_found(db_session):
    """Non-existent building should raise ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await estimate_market_value(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_market_value_commercial_type(db_session):
    """Commercial building type should use commercial price reference."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id, building_type="commercial", surface=200.0, construction_year=2010)
    await db_session.commit()

    result = await estimate_market_value(db_session, bldg.id)
    assert result["price_per_m2"] == PRICE_PER_M2_REFERENCE["VD"]["commercial"]
    assert result["building_type"] == "commercial"


# ===========================================================================
# estimate_rental_yield
# ===========================================================================


@pytest.mark.asyncio
async def test_rental_yield_basic(db_session):
    """Rental yield should return positive percentage."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id, surface=100.0)
    await db_session.commit()

    result = await estimate_rental_yield(db_session, bldg.id)
    assert result["gross_yield_pct"] > 0
    assert result["annual_rent_estimate"] > 0
    assert result["market_value"] > 0
    assert result["canton_avg_yield"] > 0


@pytest.mark.asyncio
async def test_rental_yield_comparison(db_session):
    """Yield comparison should be above, below, or at."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id, surface=100.0)
    await db_session.commit()

    result = await estimate_rental_yield(db_session, bldg.id)
    assert result["comparison"] in ("above", "below", "at")
    assert isinstance(result["recommendation"], str)
    assert len(result["recommendation"]) > 0


# ===========================================================================
# estimate_renovation_value_impact
# ===========================================================================


@pytest.mark.asyncio
async def test_renovation_impact_positive_roi(db_session):
    """Renovation of old polluted building should show positive value increase."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id, surface=200.0, construction_year=1960)
    await _add_pollutants(
        db_session,
        bldg.id,
        [{"pollutant_type": "asbestos", "risk_level": "high", "threshold_exceeded": True}],
    )
    await db_session.commit()

    result = await estimate_renovation_value_impact(db_session, bldg.id, renovation_cost=50000)
    assert result["current_value"] > 0
    assert result["post_renovation_value"] > result["current_value"]
    assert result["value_increase"] > 0
    assert result["renovation_cost"] == 50000


@pytest.mark.asyncio
async def test_renovation_impact_zero_cost(db_session):
    """Zero renovation cost should return zero ROI."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id, surface=100.0)
    await db_session.commit()

    result = await estimate_renovation_value_impact(db_session, bldg.id, renovation_cost=0)
    assert result["roi_pct"] == 0.0
