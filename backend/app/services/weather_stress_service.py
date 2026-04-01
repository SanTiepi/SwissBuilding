"""
SwissBuildingOS - Weather Stress Service (Programme S)

Compute cumulative weather stress on building facades using climate data
from the enrichment pipeline (source_metadata_json.climate).

Facade orientation stress model:
  - South/West: highest UV exposure (altitude-adjusted)
  - North/East: highest frost exposure
  - Altitude increases wind + UV, precipitation varies by orientation
  - Returns per-facade breakdown + optimal work season
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building

# ---------------------------------------------------------------------------
# Stress level thresholds
# ---------------------------------------------------------------------------

_STRESS_LEVELS = ["low", "medium", "high", "critical"]

_GRADE_THRESHOLDS = [
    (0.25, "A"),  # excellent
    (0.45, "B"),  # good
    (0.65, "C"),  # moderate
    (0.85, "D"),  # poor
    (1.0, "E"),  # critical
]


def _score_to_level(score: float) -> str:
    """Map 0-1 score to stress level."""
    if score < 0.3:
        return "low"
    if score < 0.6:
        return "medium"
    if score < 0.85:
        return "high"
    return "critical"


def _score_to_grade(avg_score: float) -> str:
    """Map average facade stress score to A-E grade."""
    for threshold, grade in _GRADE_THRESHOLDS:
        if avg_score <= threshold:
            return grade
    return "E"


# ---------------------------------------------------------------------------
# Facade stress factors per orientation (base multipliers)
# ---------------------------------------------------------------------------

# UV exposure: south and west get the most direct sun in the northern hemisphere
_UV_BASE = {"north": 0.2, "south": 0.9, "east": 0.5, "west": 0.75}

# Frost/freeze-thaw: north and east facades stay cold longer (less sun to thaw)
_FROST_BASE = {"north": 0.9, "south": 0.2, "east": 0.7, "west": 0.35}

# Wind exposure: west and north get prevailing winds in Switzerland
_WIND_BASE = {"north": 0.7, "south": 0.3, "east": 0.5, "west": 0.8}

# Rain exposure: west and east facades get more driving rain
_RAIN_BASE = {"north": 0.5, "south": 0.3, "east": 0.7, "west": 0.8}

_ORIENTATIONS = ["north", "south", "east", "west"]


def _compute_facade_scores(climate: dict) -> dict[str, dict]:
    """Compute stress scores per facade from climate data."""
    altitude = climate.get("estimated_altitude_m", 500)
    frost_days = climate.get("frost_days", 80)
    precipitation = climate.get("precipitation_mm", 1000)
    sunshine = climate.get("sunshine_hours", 1600)

    # Altitude factor: higher = more UV (thinner atmosphere) + more wind
    altitude_factor = min(1.0, altitude / 2000)

    # Frost intensity: normalized 0-1 from frost days (40-200 range)
    frost_intensity = min(1.0, max(0.0, (frost_days - 40) / 160))

    # Rain intensity: normalized 0-1 from precipitation (800-2200 range)
    rain_intensity = min(1.0, max(0.0, (precipitation - 800) / 1400))

    # UV intensity: sunshine hours + altitude bonus
    uv_intensity = min(1.0, max(0.0, (sunshine - 1200) / 900 + altitude_factor * 0.3))

    # Wind intensity: altitude-driven
    wind_intensity = min(1.0, 0.3 + altitude_factor * 0.7)

    facades = {}
    for orient in _ORIENTATIONS:
        uv_score = min(1.0, _UV_BASE[orient] * uv_intensity)
        frost_score = min(1.0, _FROST_BASE[orient] * frost_intensity)
        wind_score = min(1.0, _WIND_BASE[orient] * wind_intensity)
        rain_score = min(1.0, _RAIN_BASE[orient] * rain_intensity)

        # Overall: weighted average (frost and rain are most damaging to facades)
        overall = uv_score * 0.2 + frost_score * 0.35 + wind_score * 0.15 + rain_score * 0.3

        facades[orient] = {
            "uv": _score_to_level(uv_score),
            "frost": _score_to_level(frost_score),
            "wind": _score_to_level(wind_score),
            "rain": _score_to_level(rain_score),
            "uv_score": round(uv_score, 3),
            "frost_score": round(frost_score, 3),
            "wind_score": round(wind_score, 3),
            "rain_score": round(rain_score, 3),
            "overall_score": round(overall, 3),
            "overall": _score_to_level(overall),
        }

    return facades


def _generate_recommendations(facades: dict, climate: dict) -> list[str]:
    """Generate actionable recommendations based on facade stress."""
    recs: list[str] = []
    frost_days = climate.get("frost_days", 80)
    precipitation = climate.get("precipitation_mm", 1000)
    altitude = climate.get("estimated_altitude_m", 500)

    # Find most stressed facade
    worst = max(facades.items(), key=lambda kv: kv[1]["overall_score"])
    worst_orient, worst_data = worst

    orient_labels = {
        "north": "nord",
        "south": "sud",
        "east": "est",
        "west": "ouest",
    }

    if worst_data["frost_score"] > 0.6:
        recs.append(f"Inspecter la façade {orient_labels[worst_orient]} pour fissures liées au gel")

    if worst_data["uv_score"] > 0.6:
        recs.append(
            f"Vérifier la dégradation UV de la façade {orient_labels[worst_orient]} (peinture, joints, revêtement)"
        )

    if frost_days > 120:
        recs.append("Gel fréquent (>120 jours/an) — vérifier l'étanchéité des joints de façade")

    if precipitation > 1500:
        recs.append("Précipitations élevées — contrôler l'évacuation des eaux et l'étanchéité")

    if altitude > 1200:
        recs.append("Altitude élevée — protection renforcée contre UV et vent recommandée")

    if not recs:
        recs.append("Exposition climatique modérée — entretien standard recommandé")

    return recs


# ---------------------------------------------------------------------------
# FN1: compute_facade_stress
# ---------------------------------------------------------------------------


async def compute_facade_stress(db: AsyncSession, building_id: UUID) -> dict:
    """Compute stress index per facade orientation (N/S/E/W).

    Uses climate data from enrichment (source_metadata_json.climate):
    - UV stress: south/west facades get more UV (altitude-adjusted)
    - Freeze-thaw stress: north/east facades get more frost
    - Wind stress: based on altitude + exposure
    - Rain stress: based on precipitation + facade orientation
    """
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    meta = building.source_metadata_json or {}
    climate = meta.get("climate", {})

    if not climate:
        return {
            "facades": {},
            "most_stressed_facade": None,
            "overall_stress_grade": None,
            "recommendations": ["Données climatiques non disponibles — lancer l'enrichissement du bâtiment"],
            "climate_data_available": False,
        }

    facades = _compute_facade_scores(climate)

    # Find most stressed facade
    most_stressed = max(facades.items(), key=lambda kv: kv[1]["overall_score"])
    most_stressed_facade = most_stressed[0]

    # Overall grade from average of all facade overall scores
    avg_score = sum(f["overall_score"] for f in facades.values()) / len(facades)
    overall_grade = _score_to_grade(avg_score)

    recommendations = _generate_recommendations(facades, climate)

    return {
        "facades": facades,
        "most_stressed_facade": most_stressed_facade,
        "overall_stress_grade": overall_grade,
        "recommendations": recommendations,
        "climate_data_available": True,
    }


# ---------------------------------------------------------------------------
# FN2: compute_optimal_work_season
# ---------------------------------------------------------------------------

# Swiss monthly climate averages (approximate, relative to annual mean)
# [Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec]
_MONTH_TEMP_OFFSET = [-6, -5, -1, 3, 7, 11, 13, 12, 8, 3, -2, -5]
_MONTH_RAIN_FACTOR = [0.7, 0.7, 0.8, 0.9, 1.1, 1.2, 1.1, 1.1, 0.9, 0.8, 0.9, 0.8]
_MONTH_FROST_PROB = [0.9, 0.85, 0.6, 0.3, 0.05, 0.0, 0.0, 0.0, 0.05, 0.3, 0.6, 0.85]


async def compute_optimal_work_season(db: AsyncSession, building_id: UUID) -> dict:
    """Based on climate data, determine best months for exterior and interior work.

    Exterior work: need dry + warm (no frost, low rain)
    Interior work: year-round but avoid heating season for ventilation
    """
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    meta = building.source_metadata_json or {}
    climate = meta.get("climate", {})

    if not climate:
        return {
            "exterior": {
                "best_months": [5, 6, 7, 8, 9],
                "confidence": 0.5,
                "reason": "Estimation par défaut — données climatiques non disponibles",
            },
            "interior": {
                "best_months": [4, 5, 6, 9, 10],
                "reason": "Estimation par défaut — hors saison de chauffe",
            },
            "worst_months": [12, 1, 2],
            "reason": "Estimation par défaut — gel probable",
            "climate_data_available": False,
        }

    avg_temp = climate.get("avg_temp_c", 8.0)
    frost_days = climate.get("frost_days", 80)
    altitude = climate.get("estimated_altitude_m", 500)

    # Compute monthly suitability for exterior work
    monthly_scores: list[float] = []
    for m in range(12):
        month_temp = avg_temp + _MONTH_TEMP_OFFSET[m]
        # Frost probability adjusted for altitude
        frost_prob = min(1.0, _MONTH_FROST_PROB[m] * (1 + (altitude - 500) / 2000))
        rain_factor = _MONTH_RAIN_FACTOR[m]

        # Score: higher is better for exterior work
        temp_score = min(1.0, max(0.0, (month_temp - 5) / 15))  # comfortable above 5C
        frost_penalty = 1.0 - frost_prob
        rain_score = 1.0 - rain_factor * 0.5  # less rain is better

        score = temp_score * 0.4 + frost_penalty * 0.35 + rain_score * 0.25
        monthly_scores.append(round(score, 3))

    # Best months for exterior work: score > 0.5
    threshold = 0.5
    exterior_months = [m + 1 for m, s in enumerate(monthly_scores) if s > threshold]
    if not exterior_months:
        # Fallback: take top 3 months
        sorted_months = sorted(range(12), key=lambda m: monthly_scores[m], reverse=True)
        exterior_months = sorted([m + 1 for m in sorted_months[:3]])

    # Confidence based on how many good months we have
    if exterior_months:
        avg_ext_score = sum(monthly_scores[m - 1] for m in exterior_months) / len(exterior_months)
        confidence = round(min(0.95, avg_ext_score), 2)
    else:
        confidence = 0.3

    # Compute dry day percentage for best months
    # Rough estimate: 30 days/month, frost_days spread across frost months
    dry_pct = int((1 - frost_days / 365) * 100)

    # Worst months for exterior work: bottom scores
    sorted_worst = sorted(range(12), key=lambda m: monthly_scores[m])
    worst_months = sorted([m + 1 for m in sorted_worst[:3]])

    # Interior work: avoid heating season (Oct-Mar at low alt, longer at high alt)
    heating_start = 10 if altitude < 800 else 9
    heating_end = 3 if altitude < 800 else 4
    interior_months = [m for m in range(1, 13) if not (m >= heating_start or m <= heating_end)]
    if not interior_months:
        interior_months = [5, 6, 7, 8]

    return {
        "exterior": {
            "best_months": exterior_months,
            "confidence": confidence,
            "reason": f"{dry_pct}% jours secs estimés sur les mois recommandés",
        },
        "interior": {
            "best_months": interior_months,
            "reason": "Hors saison de chauffe — ventilation optimale",
        },
        "worst_months": worst_months,
        "reason": "Gel fréquent + précipitations élevées",
        "monthly_scores": monthly_scores,
        "climate_data_available": True,
    }
