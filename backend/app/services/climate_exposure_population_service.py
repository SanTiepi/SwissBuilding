"""Standalone climate exposure population service.

Populates ClimateExposureProfile for a building by combining:
- MeteoSwiss-derived climate data (DJU, precipitation, frost days)
- geo.admin fetchers (radon, noise, solar, hazards, heritage, water, contaminated)
- Derived stress indicators (moisture, thermal, UV)

Can be called independently of the full enrichment orchestrator.
"""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.climate_exposure import ClimateExposureProfile
from app.services.enrichment.geo_admin_fetchers import (
    fetch_heritage_status,
    fetch_natural_hazards,
    fetch_noise_data,
    fetch_radon_risk,
    fetch_solar_potential,
    fetch_water_protection,
)
from app.services.enrichment.osm_fetchers import fetch_climate_data

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MeteoSwiss DJU lookup by postal code prefix (IDAWEB reference data)
# ---------------------------------------------------------------------------
# Heating degree days (base 20°C) per postal code region.
# Source: MeteoSwiss norm values 1991-2020, aggregated by NPA region.
_DJU_BY_NPA: dict[str, float] = {
    # Vaud
    "1000": 3100,
    "1003": 3100,
    "1004": 3100,
    "1005": 3100,
    "1006": 3100,
    "1007": 3100,
    "1010": 3100,
    "1012": 3050,
    "1018": 3050,
    "1020": 3050,
    "1022": 3050,
    "1024": 3050,
    "1025": 3050,
    "1026": 3100,
    "1028": 3100,
    "1030": 3050,
    "1032": 3050,
    "1033": 3050,
    "1034": 3050,
    "1036": 3050,
    "1040": 3100,
    "1041": 3150,
    "1042": 3200,
    "1044": 3200,
    "1052": 3100,
    "1053": 3100,
    "1058": 3200,
    "1066": 3200,
    "1070": 3150,
    "1110": 3200,
    "1170": 3250,
    "1260": 3050,
    "1290": 3050,
    "1400": 3150,
    "1450": 3200,
    "1510": 3200,
    "1530": 3250,
    "1580": 3150,
    "1800": 3200,
    "1820": 3250,
    # Genève
    "1200": 2900,
    "1201": 2900,
    "1202": 2900,
    "1203": 2900,
    "1204": 2900,
    "1205": 2900,
    "1206": 2900,
    "1207": 2900,
    "1208": 2900,
    "1209": 2900,
    "1211": 2900,
    "1212": 2900,
    "1213": 2900,
    "1214": 2900,
    "1215": 2900,
    "1216": 2900,
    "1217": 2900,
    "1218": 2900,
    "1219": 2900,
    "1220": 2900,
    "1222": 2900,
    "1223": 2900,
    "1224": 2900,
    "1225": 2900,
    "1226": 2900,
    "1227": 2900,
    "1228": 2900,
    "1231": 2900,
    "1232": 2900,
    "1233": 2900,
    "1234": 2900,
    "1236": 2900,
    "1237": 2900,
    "1239": 2900,
    "1241": 2900,
    "1242": 2900,
    "1243": 2900,
    "1244": 2900,
    "1245": 2900,
    "1246": 2900,
    "1247": 2900,
    "1248": 2900,
    "1251": 2900,
    "1252": 2900,
    "1253": 2900,
    "1254": 2900,
    "1255": 2900,
    "1256": 2900,
    "1257": 2900,
    "1258": 2900,
    # Bern
    "3000": 3400,
    "3001": 3400,
    "3004": 3400,
    "3006": 3400,
    "3007": 3400,
    "3008": 3400,
    "3010": 3400,
    "3011": 3400,
    "3012": 3400,
    "3013": 3400,
    "3014": 3400,
    "3015": 3400,
    "3018": 3400,
    "3027": 3400,
    # Zürich
    "8000": 3300,
    "8001": 3300,
    "8002": 3300,
    "8003": 3300,
    "8004": 3300,
    "8005": 3300,
    "8006": 3300,
    "8008": 3300,
    "8032": 3300,
    "8037": 3300,
    "8038": 3300,
    "8041": 3300,
    "8044": 3300,
    "8045": 3300,
    "8046": 3300,
    "8047": 3300,
    "8048": 3300,
    "8049": 3300,
    "8050": 3300,
    "8051": 3300,
    "8052": 3300,
    "8053": 3300,
    "8055": 3300,
    "8057": 3300,
    # Basel
    "4000": 3100,
    "4001": 3100,
    "4051": 3100,
    "4052": 3100,
    "4053": 3100,
    "4054": 3100,
    "4055": 3100,
    "4056": 3100,
    "4057": 3100,
    "4058": 3100,
    # Luzern
    "6000": 3350,
    "6003": 3350,
    "6004": 3350,
    "6005": 3350,
    "6006": 3350,
    # Fribourg
    "1700": 3250,
    "1701": 3250,
    # Valais
    "1870": 3300,
    "1920": 3200,
    "1950": 3400,
    "3900": 3500,
    "3920": 3600,
    "3930": 3700,
    # Ticino
    "6500": 2500,
    "6600": 2600,
    "6900": 2400,
    "6901": 2400,
    # Neuchâtel
    "2000": 3300,
    "2300": 3400,
    # Jura
    "2800": 3500,
    "2900": 3500,
    # St. Gallen
    "9000": 3350,
    # Graubünden
    "7000": 3800,
    "7260": 4000,
    "7500": 4200,
}

# Precipitation by canton (mm/year, MeteoSwiss norm 1991-2020)
_PRECIP_BY_CANTON: dict[str, int] = {
    "VD": 1050,
    "GE": 950,
    "BE": 1100,
    "ZH": 1100,
    "BS": 850,
    "BL": 900,
    "LU": 1200,
    "FR": 1100,
    "VS": 600,
    "TI": 1800,
    "NE": 1000,
    "JU": 1100,
    "SG": 1300,
    "GR": 850,
    "AG": 1050,
    "TG": 1000,
    "SO": 1050,
    "SZ": 1500,
    "ZG": 1250,
    "NW": 1400,
    "OW": 1500,
    "UR": 1400,
    "GL": 1400,
    "SH": 900,
    "AR": 1500,
    "AI": 1600,
}

# Freeze-thaw cycles per year by canton (estimated from MeteoSwiss frost days)
_FREEZE_THAW_BY_CANTON: dict[str, int] = {
    "VD": 60,
    "GE": 50,
    "BE": 90,
    "ZH": 70,
    "BS": 55,
    "BL": 60,
    "LU": 80,
    "FR": 75,
    "VS": 100,
    "TI": 30,
    "NE": 80,
    "JU": 95,
    "SG": 85,
    "GR": 120,
    "AG": 65,
    "TG": 70,
    "SO": 65,
    "SZ": 90,
    "ZG": 75,
    "NW": 85,
    "OW": 90,
    "UR": 95,
    "GL": 95,
    "SH": 65,
    "AR": 100,
    "AI": 105,
}


def _safe_float(value: Any) -> float | None:
    """Convert to float, return None on failure."""
    if value is None:
        return None
    with contextlib.suppress(ValueError, TypeError):
        return float(value)
    return None


def _lookup_dju(postal_code: str | None) -> float | None:
    """Look up heating degree days from MeteoSwiss reference data by NPA."""
    if not postal_code:
        return None
    npa = postal_code.strip()[:4]
    return _DJU_BY_NPA.get(npa)


def _estimate_precipitation(canton: str | None, postal_code: str | None) -> float | None:
    """Estimate annual precipitation from canton data."""
    if canton and canton in _PRECIP_BY_CANTON:
        return float(_PRECIP_BY_CANTON[canton])
    return None


def _estimate_freeze_thaw(canton: str | None, altitude_m: float | None) -> int | None:
    """Estimate freeze-thaw cycles from canton + altitude correction."""
    base = _FREEZE_THAW_BY_CANTON.get(canton or "", 65)
    if altitude_m is not None and altitude_m > 800:
        base = int(base + (altitude_m - 800) * 0.03)
    return base


def _estimate_wind_exposure(altitude_m: float | None) -> str:
    """Estimate wind exposure from altitude."""
    if altitude_m is None:
        return "moderate"
    if altitude_m > 1500:
        return "exposed"
    if altitude_m > 800:
        return "moderate"
    return "sheltered"


def _compute_moisture_stress(precipitation_mm: float | None) -> str:
    if precipitation_mm is None:
        return "unknown"
    if precipitation_mm > 1500:
        return "high"
    if precipitation_mm > 1000:
        return "moderate"
    return "low"


def _compute_thermal_stress(freeze_thaw: int | None) -> str:
    if freeze_thaw is None:
        return "unknown"
    if freeze_thaw > 100:
        return "high"
    if freeze_thaw > 60:
        return "moderate"
    return "low"


def _compute_uv_exposure(altitude_m: float | None) -> str:
    if altitude_m is None:
        return "unknown"
    if altitude_m > 1500:
        return "high"
    if altitude_m > 800:
        return "moderate"
    return "low"


async def populate_climate_profile(
    db: AsyncSession,
    building_id: UUID,
    *,
    skip_external: bool = False,
) -> ClimateExposureProfile:
    """Populate climate exposure profile for a building.

    Combines MeteoSwiss reference data with geo.admin fetchers.
    If *skip_external* is True, only uses local lookup tables (no API calls).
    """
    stmt = select(Building).where(Building.id == building_id)
    row = await db.execute(stmt)
    building = row.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")

    # --- Upsert profile ---
    existing = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building_id))
    profile = existing.scalar_one_or_none()
    if profile is None:
        profile = ClimateExposureProfile(building_id=building_id)
        db.add(profile)

    has_coords = building.latitude is not None and building.longitude is not None
    data_sources: list[dict[str, str]] = []
    now = datetime.now(UTC)

    # ------------------------------------------------------------------
    # 1. MeteoSwiss DJU lookup by postal code
    # ------------------------------------------------------------------
    dju = _lookup_dju(building.postal_code)
    if dju is not None:
        profile.heating_degree_days = dju
        data_sources.append({"source": "meteoswiss/dju", "fetched_at": now.isoformat()})

    # ------------------------------------------------------------------
    # 2. Climate heuristics (altitude, precipitation, frost)
    # ------------------------------------------------------------------
    if has_coords:
        climate = fetch_climate_data(building.latitude, building.longitude)
        altitude_m = _safe_float(climate.get("estimated_altitude_m"))
        profile.altitude_m = altitude_m
        # Override DJU with heuristic if postal code lookup missed
        if profile.heating_degree_days is None:
            profile.heating_degree_days = _safe_float(climate.get("heating_degree_days"))
        data_sources.append({"source": "enrichment/climate_heuristic", "fetched_at": now.isoformat()})
    else:
        altitude_m = None

    # Precipitation from canton
    precip = _estimate_precipitation(building.canton, building.postal_code)
    if precip is not None:
        profile.avg_annual_precipitation_mm = precip
        data_sources.append({"source": "meteoswiss/precipitation", "fetched_at": now.isoformat()})

    # Freeze-thaw cycles
    freeze_thaw = _estimate_freeze_thaw(building.canton, altitude_m)
    profile.freeze_thaw_cycles_per_year = freeze_thaw

    # Wind exposure
    profile.wind_exposure = _estimate_wind_exposure(altitude_m)

    # ------------------------------------------------------------------
    # 3. geo.admin fetchers (radon, noise, solar, hazards, heritage, water)
    # ------------------------------------------------------------------
    if has_coords and not skip_external:
        # Radon
        try:
            radon = await fetch_radon_risk(building.latitude, building.longitude)
            if radon:
                profile.radon_zone = str(radon.get("radon_zone", "")) or None
                data_sources.append({"source": "geo.admin/radon", "fetched_at": now.isoformat()})
        except Exception as exc:
            logger.warning("Radon fetch failed for %s: %s", building_id, exc)

        # Noise (sonBASE)
        try:
            noise = await fetch_noise_data(building.latitude, building.longitude)
            if noise:
                profile.noise_exposure_day_db = _safe_float(noise.get("road_noise_day_db"))
                profile.noise_exposure_night_db = _safe_float(noise.get("road_noise_night_db"))
                data_sources.append({"source": "geo.admin/noise", "fetched_at": now.isoformat()})
        except Exception as exc:
            logger.warning("Noise fetch failed for %s: %s", building_id, exc)

        # Solar potential
        try:
            solar = await fetch_solar_potential(building.latitude, building.longitude)
            if solar:
                profile.solar_potential_kwh = _safe_float(solar.get("solar_potential_kwh"))
                data_sources.append({"source": "geo.admin/solar", "fetched_at": now.isoformat()})
        except Exception as exc:
            logger.warning("Solar fetch failed for %s: %s", building_id, exc)

        # Natural hazards
        try:
            hazards = await fetch_natural_hazards(building.latitude, building.longitude)
            if hazards:
                zones: list[dict[str, str]] = []
                for ht in ("flood", "landslide", "rockfall"):
                    lvl = hazards.get(f"{ht}_risk")
                    if lvl and lvl != "unknown":
                        zones.append({"type": ht, "level": str(lvl)})
                profile.natural_hazard_zones = zones or None
                data_sources.append({"source": "geo.admin/natural_hazards", "fetched_at": now.isoformat()})
        except Exception as exc:
            logger.warning("Natural hazards fetch failed for %s: %s", building_id, exc)

        # Heritage / ISOS
        try:
            heritage = await fetch_heritage_status(building.latitude, building.longitude)
            if heritage and heritage.get("isos_protected"):
                profile.heritage_status = heritage.get("isos_category") or heritage.get("site_name") or "protected"
                data_sources.append({"source": "geo.admin/heritage", "fetched_at": now.isoformat()})
        except Exception as exc:
            logger.warning("Heritage fetch failed for %s: %s", building_id, exc)

        # Water protection / groundwater
        try:
            water = await fetch_water_protection(building.latitude, building.longitude)
            if water:
                zone_val = water.get("protection_zone") or water.get("zone_type")
                if zone_val:
                    profile.groundwater_zone = str(zone_val)
                    data_sources.append({"source": "geo.admin/water_protection", "fetched_at": now.isoformat()})
        except Exception as exc:
            logger.warning("Water protection fetch failed for %s: %s", building_id, exc)

    # ------------------------------------------------------------------
    # 4. Stress indicators (derived)
    # ------------------------------------------------------------------
    profile.moisture_stress = _compute_moisture_stress(profile.avg_annual_precipitation_mm)
    profile.thermal_stress = _compute_thermal_stress(profile.freeze_thaw_cycles_per_year)
    profile.uv_exposure = _compute_uv_exposure(profile.altitude_m)

    # ------------------------------------------------------------------
    # 5. Metadata
    # ------------------------------------------------------------------
    profile.data_sources = data_sources
    profile.last_updated = now

    await db.flush()
    return profile
