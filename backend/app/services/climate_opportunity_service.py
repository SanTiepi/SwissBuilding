"""Climate exposure and opportunity window engine.

Builds structured climate/environmental profiles from geo.admin data
and detects favorable windows for building actions.
"""

from __future__ import annotations

import calendar
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_geo_context import BuildingGeoContext
from app.models.climate_exposure import ClimateExposureProfile, OpportunityWindow
from app.models.insurance_policy import InsurancePolicy

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Swiss climate constants
# ---------------------------------------------------------------------------

# Swiss plateau heating degree days (Zurich reference ~3400)
ALTITUDE_HDD_BASE = 3400.0
HDD_PER_100M = 100.0  # +100 HDD per 100m above 400m reference

# Swiss seasonal patterns
DRY_SEASON_START_MONTH = 4  # avril
DRY_SEASON_END_MONTH = 10  # octobre
SUMMER_START_MONTH = 6
SUMMER_END_MONTH = 9
WINTER_START_MONTH = 11
WINTER_END_MONTH = 3

# Vacation low-occupancy periods (Swiss context)
SUMMER_VACATION_START = (7, 1)  # 1er juillet
SUMMER_VACATION_END = (8, 15)  # 15 aout
WINTER_VACATION_START = (12, 20)
WINTER_VACATION_END = (1, 5)

# Altitude thresholds
ALTITUDE_LOW = 500
ALTITUDE_MID = 1000
ALTITUDE_HIGH = 1500

# Work type to seasonal mapping (French labels)
WORK_TYPE_SEASONS: dict[str, dict[str, Any]] = {
    "facade": {
        "label": "Travaux de facade",
        "best_months": [5, 6, 7, 8, 9],
        "reason": "Saison seche, temperatures moderees pour le sechage des enduits",
    },
    "toiture": {
        "label": "Travaux de toiture",
        "best_months": [4, 5, 6, 7, 8, 9],
        "reason": "Periode seche pour l'etancheite et la securite sur le toit",
    },
    "desamiantage": {
        "label": "Desamiantage",
        "best_months": [4, 5, 6, 7, 8, 9, 10],
        "reason": "Meilleure ventilation naturelle, conditions de travail plus sures",
    },
    "chauffage": {
        "label": "Installation/remplacement chauffage",
        "best_months": [5, 6, 7, 8, 9],
        "reason": "Travaux sur le systeme de chauffage en dehors de la saison de chauffe",
    },
    "ventilation": {
        "label": "Travaux de ventilation",
        "best_months": [4, 5, 6, 9, 10],
        "reason": "Mi-saison, conditions thermiques favorables pour les tests",
    },
    "interieur": {
        "label": "Travaux interieurs",
        "best_months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        "reason": "Travaux interieurs possibles toute l'annee",
    },
    "demolition": {
        "label": "Demolition",
        "best_months": [4, 5, 6, 7, 8, 9],
        "reason": "Sol sec, journees longues, conditions favorables pour la gestion des debris",
    },
    "terrassement": {
        "label": "Terrassement",
        "best_months": [4, 5, 6, 7, 8, 9],
        "reason": "Sol non gele, faible pluviometrie, meilleure portance du terrain",
    },
    "peinture": {
        "label": "Peinture exterieure",
        "best_months": [5, 6, 7, 8, 9],
        "reason": "Temperature et humidite ideales pour le sechage",
    },
    "radon": {
        "label": "Assainissement radon",
        "best_months": [4, 5, 6, 7, 8, 9],
        "reason": "Periode de ventilation naturelle optimale",
    },
    "pcb": {
        "label": "Decontamination PCB",
        "best_months": [4, 5, 6, 7, 8, 9, 10],
        "reason": "Ventilation naturelle disponible, conditions de travail controlees",
    },
    "plomb": {
        "label": "Retrait plomb",
        "best_months": [4, 5, 6, 7, 8, 9, 10],
        "reason": "Bonne ventilation naturelle pour la protection des travailleurs",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_float(val: Any) -> float | None:
    """Try to extract a float from various types."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            # Handle values like "45.2 dB" by stripping non-numeric suffix
            cleaned = val.strip().split()[0] if " " in val.strip() else val.strip()
            return float(cleaned)
        except (ValueError, IndexError):
            return None
    return None


def _derive_altitude(building: Building, geo_data: dict[str, Any]) -> float | None:
    """Derive altitude from building data or geo context."""
    # Building might have altitude from import metadata
    if building.source_metadata_json and isinstance(building.source_metadata_json, dict):
        alt = building.source_metadata_json.get("altitude") or building.source_metadata_json.get("hoehe")
        if alt is not None:
            return _safe_float(alt)
    return None


def _derive_stress(
    altitude: float | None,
    precipitation: float | None,
    hdd: float | None,
) -> dict[str, str]:
    """Derive stress indicators from climate data."""
    moisture = "unknown"
    thermal = "unknown"
    uv = "unknown"

    # Moisture stress
    if precipitation is not None:
        if precipitation > 1500:
            moisture = "high"
        elif precipitation > 1000:
            moisture = "moderate"
        else:
            moisture = "low"

    # Thermal stress (freeze-thaw based on altitude/HDD)
    if hdd is not None:
        if hdd > 4500:
            thermal = "high"
        elif hdd > 3500:
            thermal = "moderate"
        else:
            thermal = "low"

    # UV exposure (altitude-based)
    if altitude is not None:
        if altitude > ALTITUDE_HIGH:
            uv = "high"
        elif altitude > ALTITUDE_MID:
            uv = "moderate"
        else:
            uv = "low"

    return {"moisture": moisture, "thermal": thermal, "uv": uv}


def _estimate_hdd(altitude: float | None) -> float | None:
    """Estimate heating degree days from altitude (Swiss plateau reference)."""
    if altitude is None:
        return None
    extra = max(0, altitude - 400) * (HDD_PER_100M / 100)
    return ALTITUDE_HDD_BASE + extra


def _estimate_precipitation(altitude: float | None) -> float | None:
    """Rough estimate of precipitation from altitude (Swiss context)."""
    if altitude is None:
        return None
    # Swiss plateau ~1000mm, increases with altitude
    return 1000 + max(0, altitude - 400) * 0.5


def _estimate_freeze_thaw(altitude: float | None) -> int | None:
    """Estimate freeze-thaw cycles from altitude."""
    if altitude is None:
        return None
    if altitude > ALTITUDE_HIGH:
        return 120
    if altitude > ALTITUDE_MID:
        return 90
    if altitude > ALTITUDE_LOW:
        return 60
    return 40


def _wind_from_altitude(altitude: float | None) -> str | None:
    """Rough wind exposure from altitude."""
    if altitude is None:
        return None
    if altitude > ALTITUDE_HIGH:
        return "exposed"
    if altitude > ALTITUDE_MID:
        return "moderate"
    return "sheltered"


# ---------------------------------------------------------------------------
# Profile builder
# ---------------------------------------------------------------------------


async def build_exposure_profile(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> ClimateExposureProfile:
    """Build or update climate exposure profile from geo.admin data + building attributes.

    Merges geo_context data into a structured profile. Does not duplicate
    the raw geo_context -- derives structured climate fields from it.
    """
    # Load building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    # Load geo context (cached data)
    geo_result = await db.execute(select(BuildingGeoContext).where(BuildingGeoContext.building_id == building_id))
    geo_ctx = geo_result.scalar_one_or_none()
    geo_data: dict[str, Any] = {}
    if geo_ctx and geo_ctx.context_data:
        geo_data = geo_ctx.context_data

    now = datetime.now(UTC)
    data_sources: list[dict[str, str]] = []

    # --- Extract from geo.admin layers ---

    # Radon
    radon_zone = None
    radon_layer = geo_data.get("radon")
    if radon_layer:
        radon_zone = radon_layer.get("zone") or radon_layer.get("value")
        data_sources.append({"source": "geo.admin/radon", "fetched_at": now.isoformat()})

    # Noise
    noise_day = None
    noise_night = None
    for noise_key in ("noise_road", "noise_rail"):
        layer = geo_data.get(noise_key)
        if layer and layer.get("level_db"):
            val = _safe_float(layer["level_db"])
            if val is not None:
                noise_day = max(noise_day or 0, val)
                data_sources.append({"source": f"geo.admin/{noise_key}", "fetched_at": now.isoformat()})

    # Solar
    solar_kwh = None
    solar_layer = geo_data.get("solar")
    if solar_layer:
        solar_kwh = _safe_float(solar_layer.get("potential_kwh"))
        data_sources.append({"source": "geo.admin/solar", "fetched_at": now.isoformat()})

    # Natural hazards
    hazard_zones = None
    hazard_layer = geo_data.get("natural_hazards")
    if hazard_layer:
        level = hazard_layer.get("hazard_level")
        if level:
            hazard_zones = [{"type": "crue", "level": str(level)}]
            data_sources.append({"source": "geo.admin/natural_hazards", "fetched_at": now.isoformat()})

    # Groundwater
    gw_zone = None
    gw_layer = geo_data.get("groundwater_protection")
    if gw_layer:
        gw_zone = gw_layer.get("zone_type")
        data_sources.append({"source": "geo.admin/groundwater", "fetched_at": now.isoformat()})

    # Contaminated site
    contaminated = None
    contam_layer = geo_data.get("contaminated_sites")
    if contam_layer:
        contaminated = True
        data_sources.append({"source": "geo.admin/contaminated_sites", "fetched_at": now.isoformat()})

    # Heritage
    heritage = None
    heritage_layer = geo_data.get("heritage_isos")
    if heritage_layer:
        heritage = heritage_layer.get("status") or heritage_layer.get("name")
        data_sources.append({"source": "geo.admin/heritage_isos", "fetched_at": now.isoformat()})

    # --- Derive climate context ---
    altitude = _derive_altitude(building, geo_data)
    hdd = _estimate_hdd(altitude)
    precip = _estimate_precipitation(altitude)
    freeze_thaw = _estimate_freeze_thaw(altitude)
    wind = _wind_from_altitude(altitude)
    stress = _derive_stress(altitude, precip, hdd)

    # --- Upsert profile ---
    existing_result = await db.execute(
        select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building_id)
    )
    profile = existing_result.scalar_one_or_none()

    if profile is None:
        profile = ClimateExposureProfile(
            building_id=building_id,
        )
        db.add(profile)

    profile.radon_zone = radon_zone
    profile.noise_exposure_day_db = noise_day
    profile.noise_exposure_night_db = noise_night
    profile.solar_potential_kwh = solar_kwh
    profile.natural_hazard_zones = hazard_zones
    profile.groundwater_zone = gw_zone
    profile.contaminated_site = contaminated
    profile.heritage_status = heritage

    profile.heating_degree_days = hdd
    profile.avg_annual_precipitation_mm = precip
    profile.freeze_thaw_cycles_per_year = freeze_thaw
    profile.wind_exposure = wind
    profile.altitude_m = altitude

    profile.moisture_stress = stress["moisture"]
    profile.thermal_stress = stress["thermal"]
    profile.uv_exposure = stress["uv"]

    profile.data_sources = data_sources
    profile.last_updated = now

    await db.flush()
    return profile


async def get_exposure_profile(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> ClimateExposureProfile | None:
    """Get cached exposure profile for a building."""
    result = await db.execute(select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Opportunity window detection
# ---------------------------------------------------------------------------


def _weather_windows(today: date, horizon: date, building: Building) -> list[dict[str, Any]]:
    """Detect weather-based opportunity windows (dry season for exterior works)."""
    windows: list[dict[str, Any]] = []
    year = today.year

    for y in (year, year + 1):
        dry_start = date(y, DRY_SEASON_START_MONTH, 1)
        dry_end = date(y, DRY_SEASON_END_MONTH, 31)

        if dry_end < today or dry_start > horizon:
            continue

        effective_start = max(dry_start, today)
        effective_end = min(dry_end, horizon)

        if effective_start >= effective_end:
            continue

        windows.append(
            {
                "window_type": "weather",
                "title": f"Saison seche {y} — travaux exterieurs",
                "description": (
                    "Periode favorable pour les travaux exterieurs (facade, toiture, terrassement). "
                    "Conditions meteorologiques stables et faible pluviometrie."
                ),
                "window_start": effective_start,
                "window_end": effective_end,
                "optimal_date": date(y, 6, 15),
                "advantage": "Saison seche, temperatures favorables",
                "expiry_risk": "medium" if (effective_end - today).days < 60 else "low",
                "confidence": 0.85,
            }
        )

    return windows


def _seasonal_windows(today: date, horizon: date) -> list[dict[str, Any]]:
    """Detect seasonal windows for specific work types."""
    windows: list[dict[str, Any]] = []
    year = today.year

    for y in (year, year + 1):
        # Summer window for HVAC work
        summer_start = date(y, SUMMER_START_MONTH, 1)
        summer_end = date(y, SUMMER_END_MONTH, 30)
        if summer_start <= horizon and summer_end >= today:
            eff_start = max(summer_start, today)
            eff_end = min(summer_end, horizon)
            if eff_start < eff_end:
                windows.append(
                    {
                        "window_type": "seasonal",
                        "title": f"Ete {y} — travaux de chauffage/ventilation",
                        "description": (
                            "Periode ideale pour remplacer ou entretenir les systemes de chauffage "
                            "et de ventilation, en dehors de la saison de chauffe."
                        ),
                        "window_start": eff_start,
                        "window_end": eff_end,
                        "optimal_date": date(y, 7, 15),
                        "advantage": "Hors saison de chauffe",
                        "expiry_risk": "medium" if (eff_end - today).days < 45 else "low",
                        "confidence": 0.90,
                    }
                )

    return windows


def _occupancy_windows(today: date, horizon: date) -> list[dict[str, Any]]:
    """Detect low-occupancy periods (vacations) for disruptive works."""
    windows: list[dict[str, Any]] = []
    year = today.year

    for y in (year, year + 1):
        # Summer vacation
        sv_start = date(y, *SUMMER_VACATION_START)
        sv_end = date(y, *SUMMER_VACATION_END)
        if sv_start <= horizon and sv_end >= today:
            eff_start = max(sv_start, today)
            eff_end = min(sv_end, horizon)
            if eff_start < eff_end:
                windows.append(
                    {
                        "window_type": "occupancy",
                        "title": f"Vacances d'ete {y} — faible occupation",
                        "description": (
                            "Periode de vacances scolaires avec faible occupation des immeubles. "
                            "Ideal pour les travaux bruyants ou perturbateurs."
                        ),
                        "window_start": eff_start,
                        "window_end": eff_end,
                        "optimal_date": date(y, 7, 20),
                        "advantage": "Faible occupation, moins de nuisances",
                        "expiry_risk": "medium" if (eff_end - today).days < 30 else "low",
                        "confidence": 0.75,
                    }
                )

        # Winter vacation (crosses year boundary)
        wv_start = date(y, *WINTER_VACATION_START)
        wv_end_year = y + 1 if WINTER_VACATION_END[0] < WINTER_VACATION_START[0] else y
        wv_end = date(wv_end_year, *WINTER_VACATION_END)
        if wv_start <= horizon and wv_end >= today:
            eff_start = max(wv_start, today)
            eff_end = min(wv_end, horizon)
            if eff_start < eff_end:
                windows.append(
                    {
                        "window_type": "occupancy",
                        "title": f"Vacances d'hiver {y}/{y + 1} — faible occupation",
                        "description": (
                            "Periode de vacances de fin d'annee avec faible occupation. "
                            "Ideal pour les travaux interieurs non perturbateurs."
                        ),
                        "window_start": eff_start,
                        "window_end": eff_end,
                        "advantage": "Faible occupation, periode calme",
                        "expiry_risk": "low",
                        "confidence": 0.70,
                    }
                )

    return windows


async def _insurance_windows(
    db: AsyncSession,
    building_id: uuid.UUID,
    today: date,
    horizon: date,
) -> list[dict[str, Any]]:
    """Detect insurance renewal windows."""
    windows: list[dict[str, Any]] = []
    result = await db.execute(
        select(InsurancePolicy).where(
            and_(
                InsurancePolicy.building_id == building_id,
                InsurancePolicy.status.in_(["active", "pending"]),
            )
        )
    )
    policies = list(result.scalars().all())

    for pol in policies:
        if pol.date_end is None:
            continue
        end_date = pol.date_end if isinstance(pol.date_end, date) else pol.date_end.date()
        if end_date < today or end_date > horizon:
            continue

        # Renewal window = 60 days before end
        renewal_start = end_date - timedelta(days=60)
        eff_start = max(renewal_start, today)

        windows.append(
            {
                "window_type": "insurance",
                "title": f"Renouvellement assurance {pol.policy_type}",
                "description": (
                    f"La police {pol.policy_number} ({pol.insurer_name}) arrive a echeance "
                    f"le {end_date.isoformat()}. Periode de renouvellement ou renegociation."
                ),
                "window_start": eff_start,
                "window_end": end_date,
                "optimal_date": renewal_start if renewal_start >= today else today,
                "advantage": "Possibilite de renegocier les conditions avant echeance",
                "expiry_risk": "high" if (end_date - today).days < 30 else "medium",
                "cost_of_missing": "Risque de non-couverture ou renouvellement automatique sans renegociation",
                "confidence": 0.95,
            }
        )

    return windows


async def detect_opportunity_windows(
    db: AsyncSession,
    building_id: uuid.UUID,
    case_id: uuid.UUID | None = None,
    horizon_days: int = 365,
) -> list[OpportunityWindow]:
    """Detect opportunity windows for a building.

    Sources:
    - Weather: dry season for exterior works (Apr-Oct in CH)
    - Seasonal: HVAC in summer, roof in dry season
    - Occupancy: vacation periods for disruptive works
    - Insurance: renewal windows
    """
    # Verify building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    today = datetime.now(UTC).date()
    horizon = today + timedelta(days=horizon_days)

    # Collect all raw window dicts
    raw_windows: list[dict[str, Any]] = []
    raw_windows.extend(_weather_windows(today, horizon, building))
    raw_windows.extend(_seasonal_windows(today, horizon))
    raw_windows.extend(_occupancy_windows(today, horizon))
    raw_windows.extend(await _insurance_windows(db, building_id, today, horizon))

    # Expire old windows
    existing_result = await db.execute(
        select(OpportunityWindow).where(
            and_(
                OpportunityWindow.building_id == building_id,
                OpportunityWindow.status == "active",
                OpportunityWindow.window_end < today,
            )
        )
    )
    for expired in existing_result.scalars().all():
        expired.status = "expired"

    # Create new windows (idempotent — skip if same type+title+period exists)
    created: list[OpportunityWindow] = []
    for raw in raw_windows:
        # Check for existing active window with same type, title, and period
        check = await db.execute(
            select(OpportunityWindow).where(
                and_(
                    OpportunityWindow.building_id == building_id,
                    OpportunityWindow.window_type == raw["window_type"],
                    OpportunityWindow.title == raw["title"],
                    OpportunityWindow.status.in_(["active", "used"]),
                )
            )
        )
        if check.scalar_one_or_none() is not None:
            continue

        window = OpportunityWindow(
            building_id=building_id,
            case_id=case_id,
            window_type=raw["window_type"],
            title=raw["title"],
            description=raw.get("description"),
            window_start=raw["window_start"],
            window_end=raw["window_end"],
            optimal_date=raw.get("optimal_date"),
            advantage=raw.get("advantage"),
            expiry_risk=raw.get("expiry_risk", "low"),
            cost_of_missing=raw.get("cost_of_missing"),
            detected_by="system",
            confidence=raw.get("confidence", 0.7),
            status="active",
        )
        db.add(window)
        created.append(window)

    await db.flush()
    return created


async def get_active_windows(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> list[OpportunityWindow]:
    """Get current active opportunity windows for a building."""
    today = datetime.now(UTC).date()
    result = await db.execute(
        select(OpportunityWindow).where(
            and_(
                OpportunityWindow.building_id == building_id,
                OpportunityWindow.status == "active",
                OpportunityWindow.window_end >= today,
            )
        )
    )
    return list(result.scalars().all())


async def get_best_timing(
    db: AsyncSession,
    building_id: uuid.UUID,
    work_type: str,
) -> dict[str, Any]:
    """Recommend best timing for a specific work type based on windows and Swiss patterns.

    Returns a recommendation dict with period, reasoning, and matching windows.
    """
    today = datetime.now(UTC).date()
    year = today.year

    # Get seasonal recommendation from static knowledge
    season_info = WORK_TYPE_SEASONS.get(work_type)
    warnings: list[str] = []

    recommended_start: date | None = None
    recommended_end: date | None = None
    reason: str | None = None
    recommended_period: str | None = None

    if season_info:
        best_months = season_info["best_months"]
        reason = season_info["reason"]

        # Find the next best period
        for y in (year, year + 1):
            for month in best_months:
                candidate = date(y, month, 1)
                if candidate >= today:
                    recommended_start = candidate
                    break
            if recommended_start:
                break

        if recommended_start:
            # End of the best season
            last_month = best_months[-1]
            end_year = recommended_start.year if last_month >= recommended_start.month else recommended_start.year + 1
            last_day = calendar.monthrange(end_year, last_month)[1]
            recommended_end = date(end_year, last_month, last_day)
            recommended_period = (
                f"{season_info['label']}: {recommended_start.isoformat()} - {recommended_end.isoformat()}"
            )
    else:
        reason = f"Type de travaux « {work_type} » non reference dans la base saisonniere"
        warnings.append(f"Type de travaux « {work_type} » inconnu — recommandation generique")
        # Generic: dry season
        for y in (year, year + 1):
            candidate = date(y, DRY_SEASON_START_MONTH, 1)
            if candidate >= today:
                recommended_start = candidate
                recommended_end = date(y, DRY_SEASON_END_MONTH, 31)
                recommended_period = f"Saison seche: {recommended_start.isoformat()} - {recommended_end.isoformat()}"
                reason = "Recommandation generique — saison seche pour les travaux"
                break

    # Get matching active windows
    active = await get_active_windows(db, building_id)
    matching = [w for w in active if w.window_type in ("weather", "seasonal")]

    # Load exposure profile for warnings
    profile = await get_exposure_profile(db, building_id)
    if profile:
        if profile.heritage_status:
            warnings.append(f"Batiment protege (patrimoine: {profile.heritage_status}) — autorisations supplementaires")
        if profile.contaminated_site:
            warnings.append("Site contamine — mesures de protection supplementaires requises")
        if profile.natural_hazard_zones:
            warnings.append("Zone a risques naturels — verifier les restrictions de chantier")
        if profile.moisture_stress == "high":
            warnings.append("Stress hydrique eleve — prevoir une protection contre l'humidite")

    return {
        "work_type": work_type,
        "recommended_period": recommended_period,
        "recommended_start": recommended_start,
        "recommended_end": recommended_end,
        "reason": reason,
        "matching_windows": matching,
        "warnings": warnings,
    }
