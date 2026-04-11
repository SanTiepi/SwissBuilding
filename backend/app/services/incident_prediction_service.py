"""
BatiConnect - Incident Prediction Service (Programme S)

Takes correlation rules + weather forecast and predicts probable incidents.

If a building has historical pattern "infiltrations preceded by >40mm rain"
and the forecast shows >40mm rain tomorrow → trigger alert with probability.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.services.meteo_incident_correlation_service import (
    HEAVY_RAIN_MM,
    HIGH_WIND_KMH,
    analyze_correlations,
)

# ---------------------------------------------------------------------------
# Forecast condition matchers
# ---------------------------------------------------------------------------

_CONDITION_MATCHERS = {
    f"heavy_rain >{HEAVY_RAIN_MM}mm": lambda day: day.get("precip_mm", 0) >= HEAVY_RAIN_MM,
    f"high_wind >{HIGH_WIND_KMH}km/h": lambda day: day.get("wind_kmh", 0) >= HIGH_WIND_KMH,
    "freeze_thaw": lambda day: (
        abs(day.get("temp_max_c", 5) - day.get("temp_min_c", 0)) >= 8 and day.get("temp_min_c", 5) < 0
    ),
}

_RECOMMENDED_ACTIONS = {
    "leak": "Vérifier gouttières, joints et étanchéité toiture",
    "flooding": "Contrôler pompes de relevage et drains, sécuriser sous-sol",
    "mold": "Aérer les zones sensibles, contrôler VMC",
    "storm_damage": "Sécuriser éléments extérieurs, vérifier toiture et façades",
    "movement": "Surveiller fissures existantes, contrôle visuel fondations",
    "structural": "Inspection visuelle des éléments porteurs",
}

_RISK_THRESHOLDS = {
    "high": 0.6,
    "medium": 0.3,
    "low": 0.0,
}


def _assess_risk_level(probability: float) -> str:
    """Map probability to risk level."""
    if probability >= _RISK_THRESHOLDS["high"]:
        return "high"
    if probability >= _RISK_THRESHOLDS["medium"]:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def predict_incidents(
    db: AsyncSession,
    building_id: UUID,
    forecast: list[dict] | None = None,
) -> dict:
    """Predict incidents based on correlations + forecast.

    Parameters
    ----------
    db : database session
    building_id : target building
    forecast : list of daily forecast dicts with keys:
               date, precip_mm, wind_kmh, temp_max_c, temp_min_c

    Returns
    -------
    dict with risk level and predicted incidents.
    """
    # Get correlations first
    corr_result = await analyze_correlations(db, building_id)
    correlations = corr_result.get("correlations", {})

    if not correlations:
        return {
            "building_id": str(building_id),
            "building_risk_level": "none",
            "predicted_incidents": [],
            "forecast_available": forecast is not None and len(forecast) > 0,
            "correlation_data": "no_history",
        }

    # Use provided forecast or generate a default empty one
    if not forecast:
        return {
            "building_id": str(building_id),
            "building_risk_level": "unknown",
            "predicted_incidents": [],
            "forecast_available": False,
            "correlation_data": "available",
            "correlations_summary": {
                itype: {"probability": c["probability"], "sample_count": c["sample_count"]}
                for itype, c in correlations.items()
            },
        }

    # Match forecast conditions against correlation rules
    predicted: list[dict] = []

    for itype, corr in correlations.items():
        conditions = corr.get("weather_conditions", [])
        probability = corr.get("probability", 0.0)
        sample_count = corr.get("sample_count", 0)

        if sample_count < 2:
            continue  # not enough data for reliable prediction

        # Check if any forecast day matches any correlated condition
        for day in forecast:
            matched_conditions: list[str] = []
            for cond in conditions:
                matcher = _CONDITION_MATCHERS.get(cond)
                if matcher and matcher(day):
                    matched_conditions.append(cond)

            if matched_conditions:
                day_label = day.get("date", "prochains jours")
                trigger_desc = ", ".join(matched_conditions)
                predicted.append(
                    {
                        "type": itype,
                        "trigger": f"{trigger_desc} prévu ({day_label})",
                        "probability": probability,
                        "sample_count": sample_count,
                        "risk_level": _assess_risk_level(probability),
                        "recommended_action": _RECOMMENDED_ACTIONS.get(itype, "Inspection préventive recommandée"),
                        "forecast_day": day_label,
                    }
                )
                break  # one alert per incident type is enough

    # Overall building risk = highest predicted risk
    if predicted:
        risk_levels = [p["risk_level"] for p in predicted]
        if "high" in risk_levels:
            building_risk = "high"
        elif "medium" in risk_levels:
            building_risk = "medium"
        else:
            building_risk = "low"
    else:
        building_risk = "none"

    return {
        "building_id": str(building_id),
        "building_risk_level": building_risk,
        "predicted_incidents": predicted,
        "forecast_available": True,
        "correlation_data": "available",
    }


async def get_building_forecast_stub(db: AsyncSession, building_id: UUID) -> list[dict]:
    """Stub: generate a plausible 10-day forecast from building climate data.

    In production, this would call MeteoSwiss API using building lat/lon.
    """
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        return []

    meta = building.source_metadata_json or {}
    climate = meta.get("climate", {})
    avg_temp = climate.get("avg_temp_c", 9.0)

    import math
    import random
    from datetime import datetime, timedelta

    random.seed(int(datetime.utcnow().timestamp()) // 86400)  # stable per day
    now = datetime.utcnow()

    forecast: list[dict] = []
    for d in range(10):
        date = now + timedelta(days=d)
        day_of_year = date.timetuple().tm_yday
        seasonal = 12 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
        temp_base = avg_temp + seasonal

        temp_max = round(temp_base + random.uniform(2, 6), 1)
        temp_min = round(temp_base - random.uniform(2, 6), 1)
        precip = round(max(0, random.expovariate(1 / 3.0)), 1)
        if random.random() < 0.05:
            precip = round(random.uniform(35, 70), 1)
        wind = round(max(0, random.gauss(15, 8)), 1)
        if random.random() < 0.03:
            wind = round(random.uniform(70, 110), 1)

        forecast.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "temp_max_c": temp_max,
                "temp_min_c": temp_min,
                "precip_mm": precip,
                "wind_kmh": wind,
            }
        )

    return forecast
