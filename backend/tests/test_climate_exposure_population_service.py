"""Tests for the standalone climate exposure population service.

Tests the new climate_exposure_population_service.py which provides
independent climate profile population (outside the full enrichment pipeline).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.climate_exposure import ClimateExposureProfile
from app.models.user import User
from app.services.climate_exposure_population_service import (
    _compute_moisture_stress,
    _compute_thermal_stress,
    _compute_uv_exposure,
    _estimate_freeze_thaw,
    _estimate_wind_exposure,
    _lookup_dju,
    populate_climate_profile,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SVC = "app.services.climate_exposure_population_service"


async def _make_user(db: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"clim-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Clim",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
    )
    db.add(user)
    await db.flush()
    return user


async def _make_building(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    postal_code: str = "1000",
    canton: str = "VD",
    latitude: float | None = 46.52,
    longitude: float | None = 6.63,
) -> Building:
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue du Test 1",
        postal_code=postal_code,
        city="Lausanne",
        canton=canton,
        latitude=latitude,
        longitude=longitude,
        construction_year=1975,
        building_type="residential",
        created_by=user_id,
        status="active",
    )
    db.add(bldg)
    await db.flush()
    return bldg


def _mock_fetchers():
    """Return a context manager that mocks all geo.admin fetchers."""
    return (
        patch(f"{_SVC}.fetch_radon_risk", new_callable=AsyncMock, return_value={"radon_zone": "moderate"}),
        patch(f"{_SVC}.fetch_noise_data", new_callable=AsyncMock, return_value={"road_noise_day_db": 55}),
        patch(f"{_SVC}.fetch_solar_potential", new_callable=AsyncMock, return_value={"solar_potential_kwh": 1100}),
        patch(f"{_SVC}.fetch_natural_hazards", new_callable=AsyncMock, return_value={}),
        patch(f"{_SVC}.fetch_heritage_status", new_callable=AsyncMock, return_value={}),
        patch(f"{_SVC}.fetch_water_protection", new_callable=AsyncMock, return_value={}),
    )


# ---------------------------------------------------------------------------
# Unit tests — pure lookup functions
# ---------------------------------------------------------------------------


class TestDjuLookup:
    def test_lausanne(self):
        assert _lookup_dju("1000") == 3100

    def test_geneve(self):
        assert _lookup_dju("1200") == 2900

    def test_bern(self):
        assert _lookup_dju("3000") == 3400

    def test_zurich(self):
        assert _lookup_dju("8000") == 3300

    def test_ticino(self):
        assert _lookup_dju("6500") == 2500

    def test_grisons_high(self):
        assert _lookup_dju("7500") == 4200

    def test_unknown_returns_none(self):
        assert _lookup_dju("9999") is None

    def test_none_returns_none(self):
        assert _lookup_dju(None) is None

    def test_truncates_to_4(self):
        assert _lookup_dju("10001") == 3100


class TestFreezeThaw:
    def test_vaud(self):
        assert _estimate_freeze_thaw("VD", None) == 60

    def test_ticino_low(self):
        assert _estimate_freeze_thaw("TI", None) == 30

    def test_grisons_high(self):
        assert _estimate_freeze_thaw("GR", None) == 120

    def test_altitude_correction(self):
        base = _estimate_freeze_thaw("VD", None)
        high = _estimate_freeze_thaw("VD", 1200.0)
        assert high > base

    def test_unknown_canton(self):
        assert _estimate_freeze_thaw("XX", None) == 65


class TestWindExposure:
    def test_sheltered(self):
        assert _estimate_wind_exposure(400.0) == "sheltered"

    def test_moderate(self):
        assert _estimate_wind_exposure(1000.0) == "moderate"

    def test_exposed(self):
        assert _estimate_wind_exposure(2000.0) == "exposed"

    def test_none(self):
        assert _estimate_wind_exposure(None) == "moderate"


class TestStressIndicators:
    def test_moisture_levels(self):
        assert _compute_moisture_stress(1600.0) == "high"
        assert _compute_moisture_stress(1200.0) == "moderate"
        assert _compute_moisture_stress(800.0) == "low"
        assert _compute_moisture_stress(None) == "unknown"

    def test_thermal_levels(self):
        assert _compute_thermal_stress(120) == "high"
        assert _compute_thermal_stress(80) == "moderate"
        assert _compute_thermal_stress(50) == "low"
        assert _compute_thermal_stress(None) == "unknown"

    def test_uv_levels(self):
        assert _compute_uv_exposure(2000.0) == "high"
        assert _compute_uv_exposure(1000.0) == "moderate"
        assert _compute_uv_exposure(500.0) == "low"
        assert _compute_uv_exposure(None) == "unknown"


# ---------------------------------------------------------------------------
# Integration — populate_climate_profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_creates_profile_with_all_sources(db: AsyncSession):
    """Full population creates profile with DJU, geo.admin data, and stress indicators."""
    user = await _make_user(db)
    bldg = await _make_building(db, user.id)
    mocks = _mock_fetchers()

    with mocks[0], mocks[1], mocks[2], mocks[3], mocks[4], mocks[5]:
        profile = await populate_climate_profile(db, bldg.id)

    assert profile.building_id == bldg.id
    assert profile.heating_degree_days == 3100  # NPA 1000 → VD
    assert profile.radon_zone == "moderate"
    assert profile.noise_exposure_day_db == 55.0
    assert profile.solar_potential_kwh == 1100.0
    assert profile.avg_annual_precipitation_mm == 1050  # VD canton
    assert profile.freeze_thaw_cycles_per_year is not None
    assert profile.wind_exposure in ("sheltered", "moderate", "exposed")
    assert profile.moisture_stress in ("low", "moderate", "high")
    assert profile.thermal_stress in ("low", "moderate", "high", "unknown")
    assert profile.uv_exposure in ("low", "moderate", "high", "unknown")
    assert profile.last_updated is not None
    assert len(profile.data_sources) >= 3


@pytest.mark.asyncio
async def test_upsert_no_duplicate(db: AsyncSession):
    """Calling twice updates the same row."""
    user = await _make_user(db)
    bldg = await _make_building(db, user.id)

    p1 = await populate_climate_profile(db, bldg.id, skip_external=True)
    p2 = await populate_climate_profile(db, bldg.id, skip_external=True)

    assert p1.id == p2.id
    rows = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == bldg.id))
    assert len(rows.scalars().all()) == 1


@pytest.mark.asyncio
async def test_building_not_found(db: AsyncSession):
    """Raises ValueError for missing building."""
    with pytest.raises(ValueError, match="not found"):
        await populate_climate_profile(db, uuid.uuid4())


@pytest.mark.asyncio
async def test_skip_external(db: AsyncSession):
    """skip_external=True skips geo.admin calls, uses local data only."""
    user = await _make_user(db)
    bldg = await _make_building(db, user.id)

    profile = await populate_climate_profile(db, bldg.id, skip_external=True)

    assert profile.heating_degree_days == 3100
    assert profile.avg_annual_precipitation_mm == 1050
    assert profile.freeze_thaw_cycles_per_year is not None
    assert profile.radon_zone is None
    assert profile.noise_exposure_day_db is None
    assert profile.solar_potential_kwh is None


@pytest.mark.asyncio
async def test_no_coords(db: AsyncSession):
    """Building without lat/lon still gets postal-code and canton data."""
    user = await _make_user(db)
    bldg = await _make_building(db, user.id, latitude=None, longitude=None)

    profile = await populate_climate_profile(db, bldg.id, skip_external=True)

    assert profile.heating_degree_days == 3100
    assert profile.avg_annual_precipitation_mm == 1050
    assert profile.freeze_thaw_cycles_per_year == 60
    assert profile.altitude_m is None


@pytest.mark.asyncio
async def test_geneve_values(db: AsyncSession):
    """Geneva building gets GE-specific values."""
    user = await _make_user(db)
    bldg = await _make_building(db, user.id, postal_code="1200", canton="GE")

    profile = await populate_climate_profile(db, bldg.id, skip_external=True)

    assert profile.heating_degree_days == 2900
    assert profile.avg_annual_precipitation_mm == 950
    # Base GE=50, plus altitude correction from heuristic (coords present)
    assert profile.freeze_thaw_cycles_per_year >= 50


@pytest.mark.asyncio
async def test_ticino_values(db: AsyncSession):
    """Ticino has low DJU and freeze-thaw."""
    user = await _make_user(db)
    bldg = await _make_building(db, user.id, postal_code="6500", canton="TI")

    profile = await populate_climate_profile(db, bldg.id, skip_external=True)

    assert profile.heating_degree_days == 2500
    # Base TI=30, plus altitude correction from heuristic (coords present)
    assert profile.freeze_thaw_cycles_per_year >= 30


@pytest.mark.asyncio
async def test_fetcher_failure_graceful(db: AsyncSession):
    """If a geo.admin fetcher raises, service continues with other data."""
    user = await _make_user(db)
    bldg = await _make_building(db, user.id)

    with (
        patch(f"{_SVC}.fetch_radon_risk", new_callable=AsyncMock, side_effect=Exception("API down")),
        patch(f"{_SVC}.fetch_noise_data", new_callable=AsyncMock, return_value={"road_noise_day_db": 60}),
        patch(f"{_SVC}.fetch_solar_potential", new_callable=AsyncMock, return_value={}),
        patch(f"{_SVC}.fetch_natural_hazards", new_callable=AsyncMock, return_value={}),
        patch(f"{_SVC}.fetch_heritage_status", new_callable=AsyncMock, return_value={}),
        patch(f"{_SVC}.fetch_water_protection", new_callable=AsyncMock, return_value={}),
    ):
        profile = await populate_climate_profile(db, bldg.id)

    assert profile.radon_zone is None  # failed
    assert profile.noise_exposure_day_db == 60.0  # succeeded
    assert profile.heating_degree_days == 3100  # local data unaffected
