"""Tests for ClimateExposureProfile population from enrichment pipeline data.

Covers:
- Mapping from enrichment_meta to model fields
- Stress indicator computation (moisture, thermal, UV)
- Graceful degradation with missing data
- Upsert behavior (create + update)
"""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.models.climate_exposure import ClimateExposureProfile
from app.services.enrichment.orchestrator import (
    _build_natural_hazard_zones,
    _compute_moisture_stress,
    _compute_thermal_stress,
    _compute_uv_exposure,
    populate_climate_exposure_profile,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Climate 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1980,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


def _full_enrichment_meta():
    """Return a complete enrichment_meta dict mimicking the real pipeline output."""
    return {
        "climate": {
            "avg_temp_c": 7.5,
            "precipitation_mm": 1200,
            "frost_days": 85,
            "sunshine_hours": 1500,
            "heating_degree_days": 3900,
            "tropical_days": 2,
            "estimated_altitude_m": 900,
        },
        "radon": {
            "radon_zone": "2",
            "radon_probability": 0.35,
            "radon_level": "medium",
        },
        "noise": {
            "road_noise_day_db": 52.3,
            "noise_level": "moderate",
        },
        "natural_hazards": {
            "flood_risk": "moderate",
            "landslide_risk": "low",
            "rockfall_risk": "unknown",
        },
        "solar": {
            "solar_potential_kwh": 1200.0,
            "roof_area_m2": 150.0,
            "suitability": "high",
        },
        "heritage": {
            "isos_protected": True,
            "isos_category": "national",
            "site_name": "Vieille Ville",
        },
        "water_protection": {
            "protection_zone": "S2",
            "zone_type": "Grundwasserschutzzone",
        },
        "contaminated_sites": {
            "is_contaminated": True,
            "site_type": "industrial",
        },
        "railway_noise": {
            "railway_noise_day_db": 48.5,
        },
    }


# ---------------------------------------------------------------------------
# Pure computation tests
# ---------------------------------------------------------------------------


class TestMoistureStress:
    def test_high_precipitation(self):
        assert _compute_moisture_stress(1600) == "high"
        assert _compute_moisture_stress(2000) == "high"

    def test_moderate_precipitation(self):
        assert _compute_moisture_stress(1200) == "moderate"
        assert _compute_moisture_stress(1001) == "moderate"

    def test_low_precipitation(self):
        assert _compute_moisture_stress(800) == "low"
        assert _compute_moisture_stress(1000) == "low"

    def test_none_precipitation(self):
        assert _compute_moisture_stress(None) == "unknown"

    def test_boundary_1500(self):
        assert _compute_moisture_stress(1500) == "moderate"

    def test_boundary_1501(self):
        assert _compute_moisture_stress(1501) == "high"


class TestThermalStress:
    def test_high_cycles(self):
        assert _compute_thermal_stress(120) == "high"
        assert _compute_thermal_stress(101) == "high"

    def test_moderate_cycles(self):
        assert _compute_thermal_stress(80) == "moderate"
        assert _compute_thermal_stress(61) == "moderate"

    def test_low_cycles(self):
        assert _compute_thermal_stress(40) == "low"
        assert _compute_thermal_stress(60) == "low"

    def test_none_cycles(self):
        assert _compute_thermal_stress(None) == "unknown"

    def test_boundary_100(self):
        assert _compute_thermal_stress(100) == "moderate"

    def test_boundary_101(self):
        assert _compute_thermal_stress(101) == "high"


class TestUvExposure:
    def test_high_altitude(self):
        assert _compute_uv_exposure(1600) == "high"
        assert _compute_uv_exposure(2500) == "high"

    def test_moderate_altitude(self):
        assert _compute_uv_exposure(900) == "moderate"
        assert _compute_uv_exposure(801) == "moderate"

    def test_low_altitude(self):
        assert _compute_uv_exposure(500) == "low"
        assert _compute_uv_exposure(800) == "low"

    def test_none_altitude(self):
        assert _compute_uv_exposure(None) == "unknown"

    def test_boundary_1500(self):
        assert _compute_uv_exposure(1500) == "moderate"

    def test_boundary_1501(self):
        assert _compute_uv_exposure(1501) == "high"


class TestBuildNaturalHazardZones:
    def test_full_hazards(self):
        hazards = {
            "flood_risk": "high",
            "landslide_risk": "moderate",
            "rockfall_risk": "low",
        }
        result = _build_natural_hazard_zones(hazards)
        assert result is not None
        assert len(result) == 3
        types = {z["type"] for z in result}
        assert types == {"flood", "landslide", "rockfall"}

    def test_unknown_excluded(self):
        hazards = {
            "flood_risk": "high",
            "landslide_risk": "unknown",
            "rockfall_risk": "unknown",
        }
        result = _build_natural_hazard_zones(hazards)
        assert result is not None
        assert len(result) == 1
        assert result[0]["type"] == "flood"
        assert result[0]["level"] == "high"

    def test_all_unknown_returns_none(self):
        hazards = {
            "flood_risk": "unknown",
            "landslide_risk": "unknown",
            "rockfall_risk": "unknown",
        }
        result = _build_natural_hazard_zones(hazards)
        assert result is None

    def test_empty_dict_returns_none(self):
        assert _build_natural_hazard_zones({}) is None

    def test_none_returns_none(self):
        assert _build_natural_hazard_zones(None) is None


# ---------------------------------------------------------------------------
# DB integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_populate_full_data(db, admin_user):
    """Full enrichment_meta populates all model fields."""
    building = await _make_building(db, admin_user.id)
    meta = _full_enrichment_meta()

    await populate_climate_exposure_profile(db, building.id, meta)
    await db.commit()

    from sqlalchemy import select

    result = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building.id))
    profile = result.scalar_one()

    # Radon
    assert profile.radon_zone == "2"

    # Climate context
    assert profile.heating_degree_days == 3900.0
    assert profile.freeze_thaw_cycles_per_year == 85
    assert profile.altitude_m == 900.0
    assert profile.avg_annual_precipitation_mm == 1200.0

    # Noise
    assert profile.noise_exposure_day_db == 52.3
    assert profile.noise_exposure_night_db == 48.5  # from railway_noise

    # Solar
    assert profile.solar_potential_kwh == 1200.0

    # Hazards
    assert profile.natural_hazard_zones is not None
    assert len(profile.natural_hazard_zones) == 2  # flood=moderate, landslide=low, rockfall=unknown excluded
    hazard_types = {z["type"] for z in profile.natural_hazard_zones}
    assert "flood" in hazard_types
    assert "landslide" in hazard_types

    # Groundwater
    assert profile.groundwater_zone == "S2"

    # Contaminated
    assert profile.contaminated_site is True

    # Heritage
    assert profile.heritage_status == "national"

    # Wind
    assert profile.wind_exposure == "moderate"  # altitude 900 > 800

    # Stress indicators
    assert profile.moisture_stress == "moderate"  # 1200mm > 1000
    assert profile.thermal_stress == "moderate"  # 85 > 60
    assert profile.uv_exposure == "moderate"  # 900 > 800

    # Data sources
    assert profile.data_sources is not None
    assert len(profile.data_sources) > 0
    source_names = {s["source"] for s in profile.data_sources}
    assert "enrichment/climate" in source_names
    assert "geo.admin/radon" in source_names

    # Timestamps
    assert profile.last_updated is not None
    assert profile.created_at is not None


@pytest.mark.asyncio
async def test_populate_empty_meta(db, admin_user):
    """Empty enrichment_meta still creates profile with defaults."""
    building = await _make_building(db, admin_user.id)

    await populate_climate_exposure_profile(db, building.id, {})
    await db.commit()

    from sqlalchemy import select

    result = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building.id))
    profile = result.scalar_one()

    # All mapped fields should be None
    assert profile.radon_zone is None
    assert profile.heating_degree_days is None
    assert profile.freeze_thaw_cycles_per_year is None
    assert profile.altitude_m is None
    assert profile.noise_exposure_day_db is None
    assert profile.noise_exposure_night_db is None
    assert profile.solar_potential_kwh is None
    assert profile.natural_hazard_zones is None
    assert profile.groundwater_zone is None
    assert profile.contaminated_site is None
    assert profile.heritage_status is None
    assert profile.wind_exposure is None

    # Stress indicators default to unknown
    assert profile.moisture_stress == "unknown"
    assert profile.thermal_stress == "unknown"
    assert profile.uv_exposure == "unknown"

    # Data sources empty
    assert profile.data_sources == []


@pytest.mark.asyncio
async def test_populate_partial_meta(db, admin_user):
    """Partial data populates available fields, leaves rest None."""
    building = await _make_building(db, admin_user.id)
    meta = {
        "climate": {
            "estimated_altitude_m": 1600,
            "frost_days": 120,
            "precipitation_mm": 1800,
            "heating_degree_days": 5000,
        },
        # no radon, noise, hazards, solar, heritage, water, contaminated
    }

    await populate_climate_exposure_profile(db, building.id, meta)
    await db.commit()

    from sqlalchemy import select

    result = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building.id))
    profile = result.scalar_one()

    # Climate fields populated
    assert profile.altitude_m == 1600.0
    assert profile.freeze_thaw_cycles_per_year == 120
    assert profile.avg_annual_precipitation_mm == 1800.0
    assert profile.heating_degree_days == 5000.0

    # Wind derived from altitude
    assert profile.wind_exposure == "exposed"  # 1600 > 1500

    # Stress indicators computed from available data
    assert profile.moisture_stress == "high"  # 1800 > 1500
    assert profile.thermal_stress == "high"  # 120 > 100
    assert profile.uv_exposure == "high"  # 1600 > 1500

    # Unmapped fields remain None
    assert profile.radon_zone is None
    assert profile.noise_exposure_day_db is None
    assert profile.solar_potential_kwh is None
    assert profile.natural_hazard_zones is None
    assert profile.heritage_status is None


@pytest.mark.asyncio
async def test_upsert_updates_existing(db, admin_user):
    """Calling populate twice updates the existing profile, not duplicates."""
    building = await _make_building(db, admin_user.id)

    # First population — low altitude
    meta_v1 = {
        "climate": {
            "estimated_altitude_m": 400,
            "frost_days": 50,
            "precipitation_mm": 900,
            "heating_degree_days": 3200,
        },
    }
    await populate_climate_exposure_profile(db, building.id, meta_v1)
    await db.commit()

    from sqlalchemy import select

    result = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building.id))
    profile = result.scalar_one()
    assert profile.altitude_m == 400.0
    assert profile.uv_exposure == "low"
    profile_id = profile.id

    # Second population — high altitude
    meta_v2 = {
        "climate": {
            "estimated_altitude_m": 2000,
            "frost_days": 150,
            "precipitation_mm": 1700,
            "heating_degree_days": 5500,
        },
        "radon": {"radon_zone": "3"},
    }
    await populate_climate_exposure_profile(db, building.id, meta_v2)
    await db.commit()

    result2 = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building.id))
    profile2 = result2.scalar_one()

    # Same row updated, not a new one
    assert profile2.id == profile_id
    assert profile2.altitude_m == 2000.0
    assert profile2.uv_exposure == "high"
    assert profile2.radon_zone == "3"


@pytest.mark.asyncio
async def test_heritage_not_protected(db, admin_user):
    """Heritage data with isos_protected=False produces no heritage_status."""
    building = await _make_building(db, admin_user.id)
    meta = {
        "heritage": {"isos_protected": False},
    }

    await populate_climate_exposure_profile(db, building.id, meta)
    await db.commit()

    from sqlalchemy import select

    result = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building.id))
    profile = result.scalar_one()
    assert profile.heritage_status is None


@pytest.mark.asyncio
async def test_heritage_protected_no_category(db, admin_user):
    """Protected heritage with no category falls back to 'protected'."""
    building = await _make_building(db, admin_user.id)
    meta = {
        "heritage": {"isos_protected": True},
    }

    await populate_climate_exposure_profile(db, building.id, meta)
    await db.commit()

    from sqlalchemy import select

    result = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building.id))
    profile = result.scalar_one()
    assert profile.heritage_status == "protected"


@pytest.mark.asyncio
async def test_malformed_numeric_values(db, admin_user):
    """Non-numeric values in numeric fields are handled gracefully."""
    building = await _make_building(db, admin_user.id)
    meta = {
        "climate": {
            "estimated_altitude_m": "not_a_number",
            "frost_days": "invalid",
            "precipitation_mm": None,
            "heating_degree_days": "abc",
        },
        "noise": {
            "road_noise_day_db": "loud",
        },
    }

    await populate_climate_exposure_profile(db, building.id, meta)
    await db.commit()

    from sqlalchemy import select

    result = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building.id))
    profile = result.scalar_one()

    # All should be None due to conversion failures
    assert profile.altitude_m is None
    assert profile.freeze_thaw_cycles_per_year is None
    assert profile.avg_annual_precipitation_mm is None
    assert profile.heating_degree_days is None
    assert profile.noise_exposure_day_db is None

    # Stress indicators unknown (no valid data)
    assert profile.moisture_stress == "unknown"
    assert profile.thermal_stress == "unknown"
    assert profile.uv_exposure == "unknown"


@pytest.mark.asyncio
async def test_wind_exposure_sheltered(db, admin_user):
    """Low altitude gives sheltered wind exposure."""
    building = await _make_building(db, admin_user.id)
    meta = {"climate": {"estimated_altitude_m": 400}}

    await populate_climate_exposure_profile(db, building.id, meta)
    await db.commit()

    from sqlalchemy import select

    result = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building.id))
    profile = result.scalar_one()
    assert profile.wind_exposure == "sheltered"


@pytest.mark.asyncio
async def test_contaminated_false(db, admin_user):
    """Non-contaminated site is stored correctly."""
    building = await _make_building(db, admin_user.id)
    meta = {"contaminated_sites": {"is_contaminated": False}}

    await populate_climate_exposure_profile(db, building.id, meta)
    await db.commit()

    from sqlalchemy import select

    result = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building.id))
    profile = result.scalar_one()
    assert profile.contaminated_site is False


@pytest.mark.asyncio
async def test_data_sources_tracked(db, admin_user):
    """Each present data source is tracked in data_sources list."""
    building = await _make_building(db, admin_user.id)
    meta = {
        "climate": {"estimated_altitude_m": 500},
        "radon": {"radon_zone": "1"},
    }

    await populate_climate_exposure_profile(db, building.id, meta)
    await db.commit()

    from sqlalchemy import select

    result = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building.id))
    profile = result.scalar_one()
    source_names = {s["source"] for s in profile.data_sources}
    assert "enrichment/climate" in source_names
    assert "geo.admin/radon" in source_names
    # Noise not present, so not tracked
    assert "geo.admin/noise" not in source_names
