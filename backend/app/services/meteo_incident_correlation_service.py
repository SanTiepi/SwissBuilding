"""
BatiConnect - Meteo/Incident Correlation Service (Programme S)

Analyse historical incidents against preceding weather conditions to detect
patterns like "80% of infiltrations occur after >40mm rain".

For each incident type, looks back 14 days for weather triggers:
  - Heavy rain (>40mm/day)
  - Freeze-thaw cycles
  - High winds (>80 km/h)
  - Prolonged humidity (>85% for 3+ days)

Outputs correlation rules with probability and sample count.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.incident import IncidentEpisode

# ---------------------------------------------------------------------------
# Weather condition thresholds
# ---------------------------------------------------------------------------

HEAVY_RAIN_MM = 40.0
HIGH_WIND_KMH = 80.0
FREEZE_THAW_DELTA_C = 8.0  # swing across 0°C within 24h
HUMIDITY_THRESHOLD_PCT = 85.0
HUMIDITY_CONSECUTIVE_DAYS = 3

# Incident types most correlated with weather
WEATHER_SENSITIVE_TYPES = [
    "leak",
    "flooding",
    "mold",
    "storm_damage",
    "movement",
    "structural",
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _classify_weather_conditions(daily_meteo: list[dict]) -> list[dict]:
    """Tag each day with detected weather conditions.

    Each daily record expected: {date, temp_c, precip_mm, wind_kmh, humidity_pct}
    """
    tagged: list[dict] = []
    for i, day in enumerate(daily_meteo):
        conditions: list[str] = []
        precip = day.get("precip_mm", 0.0)
        wind = day.get("wind_kmh", 0.0)
        temp = day.get("temp_c", 10.0)
        humidity = day.get("humidity_pct", 50.0)

        if precip >= HEAVY_RAIN_MM:
            conditions.append(f"heavy_rain >{HEAVY_RAIN_MM}mm")

        if wind >= HIGH_WIND_KMH:
            conditions.append(f"high_wind >{HIGH_WIND_KMH}km/h")

        # Freeze-thaw: temp crossed 0 with large swing
        if i > 0:
            prev_temp = daily_meteo[i - 1].get("temp_c", 10.0)
            crossed_zero = (prev_temp < 0 and temp > 0) or (prev_temp > 0 and temp < 0)
            if crossed_zero and abs(temp - prev_temp) >= FREEZE_THAW_DELTA_C:
                conditions.append("freeze_thaw")

        # Prolonged humidity
        if humidity >= HUMIDITY_THRESHOLD_PCT:
            consecutive = 1
            for j in range(max(0, i - HUMIDITY_CONSECUTIVE_DAYS + 1), i):
                if daily_meteo[j].get("humidity_pct", 0) >= HUMIDITY_THRESHOLD_PCT:
                    consecutive += 1
            if consecutive >= HUMIDITY_CONSECUTIVE_DAYS:
                conditions.append(f"prolonged_humidity >{HUMIDITY_THRESHOLD_PCT}%")

        tagged.append({**day, "conditions": conditions})
    return tagged


def _find_preceding_conditions(
    incident_date: datetime,
    meteo_data: list[dict],
    lookback_days: int = 14,
) -> list[dict]:
    """Find weather conditions in the lookback window before an incident."""
    start = incident_date - timedelta(days=lookback_days)
    end = incident_date
    matches: list[dict] = []
    for day in meteo_data:
        day_date = day.get("date")
        if day_date is None:
            continue
        if isinstance(day_date, str):
            day_date = datetime.fromisoformat(day_date)
        if start <= day_date <= end and day.get("conditions"):
            days_before = (end - day_date).days
            matches.append(
                {
                    "date": day_date.isoformat() if isinstance(day_date, datetime) else day_date,
                    "days_before_incident": days_before,
                    "conditions": day["conditions"],
                }
            )
    return matches


def _build_correlations(
    incidents: list[IncidentEpisode],
    meteo_data: list[dict],
) -> dict:
    """Build correlation map: incident_type → weather triggers → stats."""
    tagged_meteo = _classify_weather_conditions(meteo_data)
    correlations: dict[str, dict] = {}

    for incident in incidents:
        itype = incident.incident_type
        if itype not in WEATHER_SENSITIVE_TYPES:
            continue

        incident_date = incident.discovered_at
        if incident_date is None:
            continue

        preceding = _find_preceding_conditions(incident_date, tagged_meteo)
        if not preceding:
            continue

        if itype not in correlations:
            correlations[itype] = {
                "total_incidents": 0,
                "weather_preceded": 0,
                "precedes_by_days": [],
                "weather_conditions": set(),
                "probability": 0.0,
                "sample_count": 0,
            }

        correlations[itype]["total_incidents"] += 1
        correlations[itype]["weather_preceded"] += 1
        for match in preceding:
            correlations[itype]["precedes_by_days"].append(match["days_before_incident"])
            for cond in match["conditions"]:
                correlations[itype]["weather_conditions"].add(cond)

    # Count incidents without weather preceding
    for incident in incidents:
        itype = incident.incident_type
        if itype not in WEATHER_SENSITIVE_TYPES or itype not in correlations:
            continue
        # Already counted in weather_preceded pass above;
        # but total_incidents should include ALL incidents of that type
    for incident in incidents:
        itype = incident.incident_type
        if itype in WEATHER_SENSITIVE_TYPES and itype in correlations:
            pass  # already counted above

    # Recalculate total_incidents from all incidents (not just weather-preceded)
    type_totals: dict[str, int] = {}
    for incident in incidents:
        itype = incident.incident_type
        if itype in WEATHER_SENSITIVE_TYPES:
            type_totals[itype] = type_totals.get(itype, 0) + 1

    for itype, corr in correlations.items():
        total = type_totals.get(itype, corr["weather_preceded"])
        corr["total_incidents"] = total
        corr["sample_count"] = corr["weather_preceded"]
        if total > 0:
            corr["probability"] = round(corr["weather_preceded"] / total, 2)
        corr["weather_conditions"] = sorted(corr["weather_conditions"])

    return correlations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def analyze_correlations(
    db: AsyncSession,
    building_id: UUID,
    lookback_years: int = 2,
    meteo_data: list[dict] | None = None,
) -> dict:
    """Analyze incident/weather correlations for a building.

    Parameters
    ----------
    db : database session
    building_id : target building UUID
    lookback_years : how far back to scan incidents (default 2 years)
    meteo_data : optional pre-fetched meteo history; if None, uses
                 climate data from building enrichment as synthetic proxy.

    Returns
    -------
    dict with correlation rules per incident type.
    """
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    cutoff = datetime.utcnow() - timedelta(days=lookback_years * 365)
    stmt_incidents = (
        select(IncidentEpisode)
        .where(
            IncidentEpisode.building_id == building_id,
            IncidentEpisode.discovered_at >= cutoff,
        )
        .order_by(IncidentEpisode.discovered_at)
    )
    result_inc = await db.execute(stmt_incidents)
    incidents = list(result_inc.scalars().all())

    if not incidents:
        return {
            "building_id": str(building_id),
            "correlations": {},
            "incident_count": 0,
            "analysis_window_years": lookback_years,
            "data_quality": "no_incidents",
        }

    # Use provided meteo data or generate synthetic from climate enrichment
    if meteo_data is None:
        meteo_data = _generate_synthetic_meteo(building, lookback_years)

    correlations = _build_correlations(incidents, meteo_data)

    return {
        "building_id": str(building_id),
        "correlations": correlations,
        "incident_count": len(incidents),
        "analysis_window_years": lookback_years,
        "data_quality": "synthetic" if meteo_data else "historical",
    }


def _generate_synthetic_meteo(building: Building, years: int) -> list[dict]:
    """Generate synthetic daily meteo from building climate enrichment.

    Uses source_metadata_json.climate averages + seasonal variation
    to produce plausible daily records for correlation analysis.
    """
    meta = building.source_metadata_json or {}
    climate = meta.get("climate", {})

    avg_temp = climate.get("avg_temp_c", 9.0)
    precip_mm = climate.get("precipitation_mm", 1100)

    daily_precip_avg = precip_mm / 365
    days = years * 365
    start = datetime.utcnow() - timedelta(days=days)

    import math
    import random

    random.seed(42)  # reproducible for tests

    records: list[dict] = []
    for d in range(days):
        date = start + timedelta(days=d)
        day_of_year = date.timetuple().tm_yday

        # Seasonal temperature variation (sinusoidal, peak in July)
        seasonal_offset = 12 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
        temp = avg_temp + seasonal_offset + random.gauss(0, 3)

        # Precipitation: higher in summer, with occasional heavy events
        rain_factor = 1.0 + 0.3 * math.sin(2 * math.pi * (day_of_year - 60) / 365)
        precip = max(0, random.expovariate(1 / (daily_precip_avg * rain_factor)))
        # Occasional heavy rain events
        if random.random() < 0.02:
            precip = random.uniform(35, 80)

        wind = max(0, random.gauss(15, 10))
        if random.random() < 0.01:
            wind = random.uniform(70, 120)

        humidity = min(100, max(20, random.gauss(65, 15)))
        if precip > 10:
            humidity = min(100, humidity + 15)

        records.append(
            {
                "date": date,
                "temp_c": round(temp, 1),
                "precip_mm": round(precip, 1),
                "wind_kmh": round(wind, 1),
                "humidity_pct": round(humidity, 1),
            }
        )

    return records
