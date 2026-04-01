"""
BatiConnect - Insurance Risk Profiler (Programme AA)

Composite insurance risk profiling for buildings:
fire, water, storm, earthquake, pollution, structural, liability.

Uses building metadata, diagnostic results, incident history,
geo context, and climate exposure to compute a 0-100 risk score
with estimated premium factor and coverage gap detection.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_geo_context import BuildingGeoContext
from app.models.climate_exposure import ClimateExposureProfile
from app.models.diagnostic import Diagnostic
from app.models.incident import IncidentEpisode
from app.models.insurance_policy import InsurancePolicy
from app.models.intervention import Intervention
from app.models.sample import Sample

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RISK_WEIGHTS: dict[str, float] = {
    "fire": 2.5,
    "water": 2.0,
    "storm": 1.5,
    "earthquake": 2.0,
    "pollution": 3.0,
    "structural": 2.5,
    "liability": 1.5,
}

GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (80, "F"),  # 80-100 = very high risk
    (60, "E"),
    (40, "D"),
    (25, "C"),
    (10, "B"),
    (0, "A"),  # 0-10 = very low risk
]

# Premium factor bounds: score 0 -> 0.8x, score 100 -> 2.0x
_PREMIUM_MIN = 0.8
_PREMIUM_MAX = 2.0

# Fire system types that reduce fire risk
_FIRE_SYSTEMS = {"sprinkler", "fire_alarm", "extinguisher", "hydrant", "smoke_detector"}

# Insurance policy types expected per risk dimension
_EXPECTED_COVERAGE: dict[str, set[str]] = {
    "fire": {"building_eca"},
    "water": {"building_eca", "natural_hazard"},
    "storm": {"natural_hazard"},
    "earthquake": {"natural_hazard"},
    "pollution": {"complementary", "rc_building"},
    "structural": {"building_eca", "construction_risk"},
    "liability": {"rc_owner", "rc_building"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _score_to_grade(score: float) -> str:
    """Convert 0-100 risk score to A-F grade (A=safest, F=riskiest)."""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "A"


def _score_to_level(score: float) -> str:
    """Convert dimension score to textual level."""
    if score >= 70:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _compute_premium_factor(overall_score: float) -> float:
    """Linear interpolation: score 0 → 0.8, score 100 → 2.0."""
    factor = _PREMIUM_MIN + (overall_score / 100.0) * (_PREMIUM_MAX - _PREMIUM_MIN)
    return round(factor, 2)


# ---------------------------------------------------------------------------
# Dimension scorers (each returns 0-100, higher = more risky)
# ---------------------------------------------------------------------------


def _compute_fire_risk(
    building: Building,
    incidents: list[IncidentEpisode],
    interventions: list[Intervention],
) -> tuple[float, list[str]]:
    """Fire risk from age, incidents, and fire systems."""
    score = 0.0
    factors: list[str] = []

    # Age penalty: older buildings = more risk
    year = building.construction_year
    if year:
        age = datetime.now(UTC).year - year
        if age > 80:
            score += 35
            factors.append(f"Building very old ({age} years)")
        elif age > 50:
            score += 25
            factors.append(f"Building old ({age} years)")
        elif age > 30:
            score += 15
            factors.append(f"Building aging ({age} years)")
        else:
            score += 5
    else:
        score += 20
        factors.append("Construction year unknown")

    # Fire incidents
    fire_incidents = [i for i in incidents if i.incident_type == "fire"]
    if fire_incidents:
        score += min(40, len(fire_incidents) * 20)
        factors.append(f"{len(fire_incidents)} fire incident(s) recorded")

    # Fire system check from interventions (presence of fire system installations)
    fire_interventions = [
        i for i in interventions if i.intervention_type in ("fire_protection", "safety") and i.status == "completed"
    ]
    if fire_interventions:
        score -= 15
        factors.append("Fire protection system installed")
    else:
        score += 10
        factors.append("No fire protection system detected")

    return _clamp(score), factors


def _compute_water_risk(
    building: Building,
    incidents: list[IncidentEpisode],
    climate: ClimateExposureProfile | None,
) -> tuple[float, list[str]]:
    """Water risk from incidents (leak/flooding), plumbing age, groundwater."""
    score = 0.0
    factors: list[str] = []

    # Water-related incidents
    water_types = {"leak", "flooding", "mold"}
    water_incidents = [i for i in incidents if i.incident_type in water_types]
    if water_incidents:
        score += min(50, len(water_incidents) * 15)
        factors.append(f"{len(water_incidents)} water-related incident(s)")
    else:
        factors.append("No water incidents recorded")

    # Plumbing age estimate from construction year
    year = building.construction_year
    if year:
        age = datetime.now(UTC).year - year
        if age > 50:
            score += 25
            factors.append("Plumbing likely original and aged")
        elif age > 30:
            score += 15
            factors.append("Plumbing aging")
    else:
        score += 10

    # Groundwater from climate exposure
    if climate and climate.groundwater_zone:
        gw = climate.groundwater_zone.lower()
        if "protection" in gw or "high" in gw:
            score += 15
            factors.append(f"Groundwater zone: {climate.groundwater_zone}")

    return _clamp(score), factors


def _compute_storm_risk(
    building: Building,
    incidents: list[IncidentEpisode],
    climate: ClimateExposureProfile | None,
) -> tuple[float, list[str]]:
    """Storm risk from geo hazards, wind exposure, altitude, incidents."""
    score = 0.0
    factors: list[str] = []

    # Wind exposure
    if climate and climate.wind_exposure:
        wind = climate.wind_exposure.lower()
        if wind == "exposed":
            score += 30
            factors.append("High wind exposure")
        elif wind == "moderate":
            score += 15
            factors.append("Moderate wind exposure")

    # Altitude penalty (hail/storm more frequent at altitude)
    if climate and climate.altitude_m:
        alt = climate.altitude_m
        if alt > 1500:
            score += 20
            factors.append(f"High altitude ({alt}m)")
        elif alt > 800:
            score += 10
            factors.append(f"Moderate altitude ({alt}m)")

    # Storm/hail incidents
    storm_incidents = [i for i in incidents if i.incident_type in ("storm_damage", "equipment_failure")]
    if storm_incidents:
        score += min(30, len(storm_incidents) * 15)
        factors.append(f"{len(storm_incidents)} storm-related incident(s)")

    # Natural hazard zones
    if climate and climate.natural_hazard_zones:
        hazards = climate.natural_hazard_zones
        if isinstance(hazards, list) and len(hazards) > 0:
            score += 15
            factors.append(f"{len(hazards)} natural hazard zone(s)")

    return _clamp(score), factors


def _compute_earthquake_risk(
    geo_context: BuildingGeoContext | None,
    climate: ClimateExposureProfile | None,
) -> tuple[float, list[str]]:
    """Earthquake risk from seismic zone (Swiss zones 1-3b)."""
    score = 0.0
    factors: list[str] = []

    seismic_zone: str | None = None

    # Try geo_context first
    if geo_context and geo_context.context_data:
        seismic_data = geo_context.context_data.get("seismic", {})
        seismic_zone = seismic_data.get("seismic_zone")

    if seismic_zone:
        zone = str(seismic_zone).lower()
        if zone in ("3b", "3a"):
            score = 80
            factors.append(f"Seismic zone {seismic_zone} (high risk)")
        elif zone == "2":
            score = 50
            factors.append(f"Seismic zone {seismic_zone} (moderate risk)")
        elif zone == "1":
            score = 20
            factors.append(f"Seismic zone {seismic_zone} (low risk)")
        else:
            score = 10
            factors.append(f"Seismic zone {seismic_zone}")
    else:
        score = 15
        factors.append("Seismic zone unknown")

    return _clamp(score), factors


def _compute_pollution_risk(
    samples: list[Sample],
    diagnostics: list[Diagnostic],
) -> tuple[float, list[str]]:
    """Pollution risk from diagnostic results and threshold exceedances."""
    score = 0.0
    factors: list[str] = []

    if not diagnostics:
        score = 40
        factors.append("No pollutant diagnostics — risk unknown")
        return score, factors

    completed = [d for d in diagnostics if d.status in ("completed", "validated")]
    if not completed:
        score = 35
        factors.append("Diagnostics started but not completed")
        return score, factors

    if not samples:
        score = 25
        factors.append("Diagnostics completed but no samples")
        return score, factors

    exceeded = [s for s in samples if s.threshold_exceeded]
    high_risk = [s for s in samples if s.risk_level in ("high", "critical")]

    if exceeded:
        # Each exceedance adds significantly
        score += min(60, len(exceeded) * 15)
        pollutant_types = {s.pollutant_type for s in exceeded}
        factors.append(f"{len(exceeded)} threshold exceedance(s) ({', '.join(sorted(pollutant_types))})")

    if high_risk:
        score += min(30, len(high_risk) * 10)
        factors.append(f"{len(high_risk)} high/critical risk sample(s)")

    if not exceeded and not high_risk:
        score = 5
        factors.append("All samples within thresholds")

    return _clamp(score), factors


def _compute_structural_risk(
    building: Building,
    incidents: list[IncidentEpisode],
    interventions: list[Intervention],
) -> tuple[float, list[str]]:
    """Structural risk from age, incidents (subsidence, cracks), maintenance."""
    score = 0.0
    factors: list[str] = []

    # Age factor
    year = building.construction_year
    if year:
        age = datetime.now(UTC).year - year
        if age > 100:
            score += 35
            factors.append(f"Very old structure ({age} years)")
        elif age > 60:
            score += 25
            factors.append(f"Old structure ({age} years)")
        elif age > 30:
            score += 15
    else:
        score += 20
        factors.append("Construction year unknown")

    # Structural incidents
    structural_types = {"subsidence", "movement", "structural"}
    struct_incidents = [i for i in incidents if i.incident_type in structural_types]
    if struct_incidents:
        critical = [i for i in struct_incidents if i.severity in ("major", "critical")]
        score += min(40, len(struct_incidents) * 15 + len(critical) * 10)
        factors.append(f"{len(struct_incidents)} structural incident(s)")

    # Maintenance interventions reduce risk
    maintenance = [i for i in interventions if i.status == "completed"]
    if len(maintenance) >= 3:
        score -= 15
        factors.append("Good maintenance history")
    elif maintenance:
        score -= 5
        factors.append("Some maintenance performed")
    else:
        score += 10
        factors.append("No maintenance records")

    return _clamp(score), factors


def _compute_liability_risk(
    building: Building,
    samples: list[Sample],
) -> tuple[float, list[str]]:
    """Liability risk from occupant count (estimated from floors), public access, hazardous materials."""
    score = 0.0
    factors: list[str] = []

    # Estimate occupancy from floors
    floors = (building.floors_above or 1) + (building.floors_below or 0)
    if floors > 10:
        score += 30
        factors.append(f"Large building ({floors} floors) — high occupancy")
    elif floors > 5:
        score += 20
        factors.append(f"Medium building ({floors} floors)")
    elif floors > 2:
        score += 10
    else:
        score += 5

    # Building type hints at public access
    btype = (building.building_type or "").lower()
    if btype in ("commercial", "public", "mixed", "education", "healthcare"):
        score += 20
        factors.append(f"Public-access building type: {building.building_type}")

    # Hazardous materials presence
    hazardous = [s for s in samples if s.threshold_exceeded and s.risk_level in ("high", "critical")]
    if hazardous:
        score += min(30, len(hazardous) * 10)
        factors.append(f"{len(hazardous)} hazardous material finding(s)")

    return _clamp(score), factors


# ---------------------------------------------------------------------------
# Coverage gap detection
# ---------------------------------------------------------------------------


def _detect_gaps(
    dimension_scores: dict[str, dict],
    policies: list[InsurancePolicy],
) -> list[dict]:
    """Compare insurance policies vs actual risks. High risk + no coverage = gap."""
    active_types: set[str] = set()
    for p in policies:
        if p.status == "active":
            active_types.add(p.policy_type)

    gaps: list[dict] = []
    for dim, info in dimension_scores.items():
        if info["score"] < 30:
            continue  # low risk, no gap concern

        expected = _EXPECTED_COVERAGE.get(dim, set())
        missing = expected - active_types
        if missing:
            level = info["level"]
            gaps.append(
                {
                    "type": dim,
                    "description": (
                        f"{dim.replace('_', ' ').title()} risk is {level} "
                        f"(score {info['score']:.0f}) but missing coverage: {', '.join(sorted(missing))}"
                    ),
                    "recommendation": f"Consider adding {', '.join(sorted(missing))} coverage",
                    "risk_score": info["score"],
                }
            )

    return sorted(gaps, key=lambda g: g["risk_score"], reverse=True)


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------


async def compute_insurance_risk_profile(db: AsyncSession, building_id: UUID) -> dict:
    """Compute composite insurance risk profile for a building.

    Returns:
        {
            overall_score: 0-100 (lower=safer),
            grade: A-F,
            breakdown: {dimension: {score, level, factors}},
            estimated_premium_factor: 0.8-2.0,
            coverage_gaps: [{type, description, recommendation}],
            top_risks: [top 3 dimensions],
            computed_at: ISO timestamp,
        }
    """
    # Load building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return {
            "overall_score": 0,
            "grade": "A",
            "breakdown": {},
            "estimated_premium_factor": 1.0,
            "coverage_gaps": [],
            "top_risks": [],
            "computed_at": datetime.now(UTC).isoformat(),
            "error": "Building not found",
        }

    # Load related data
    incidents_q = await db.execute(select(IncidentEpisode).where(IncidentEpisode.building_id == building_id))
    incidents = list(incidents_q.scalars().all())

    interventions_q = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(interventions_q.scalars().all())

    diag_q = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_q.scalars().all())

    diag_ids = [d.id for d in diagnostics]
    samples: list[Sample] = []
    if diag_ids:
        samples_q = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(samples_q.scalars().all())

    geo_q = await db.execute(select(BuildingGeoContext).where(BuildingGeoContext.building_id == building_id))
    geo_context = geo_q.scalar_one_or_none()

    climate_q = await db.execute(
        select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building_id)
    )
    climate = climate_q.scalar_one_or_none()

    policies_q = await db.execute(select(InsurancePolicy).where(InsurancePolicy.building_id == building_id))
    policies = list(policies_q.scalars().all())

    # Compute each dimension
    fire_score, fire_factors = _compute_fire_risk(building, incidents, interventions)
    water_score, water_factors = _compute_water_risk(building, incidents, climate)
    storm_score, storm_factors = _compute_storm_risk(building, incidents, climate)
    eq_score, eq_factors = _compute_earthquake_risk(geo_context, climate)
    poll_score, poll_factors = _compute_pollution_risk(samples, diagnostics)
    struct_score, struct_factors = _compute_structural_risk(building, incidents, interventions)
    liab_score, liab_factors = _compute_liability_risk(building, samples)

    breakdown: dict[str, dict] = {
        "fire": {"score": round(fire_score, 1), "level": _score_to_level(fire_score), "factors": fire_factors},
        "water": {"score": round(water_score, 1), "level": _score_to_level(water_score), "factors": water_factors},
        "storm": {"score": round(storm_score, 1), "level": _score_to_level(storm_score), "factors": storm_factors},
        "earthquake": {"score": round(eq_score, 1), "level": _score_to_level(eq_score), "factors": eq_factors},
        "pollution": {
            "score": round(poll_score, 1),
            "level": _score_to_level(poll_score),
            "factors": poll_factors,
        },
        "structural": {
            "score": round(struct_score, 1),
            "level": _score_to_level(struct_score),
            "factors": struct_factors,
        },
        "liability": {
            "score": round(liab_score, 1),
            "level": _score_to_level(liab_score),
            "factors": liab_factors,
        },
    }

    # Weighted average
    total_weight = sum(RISK_WEIGHTS.values())
    weighted_sum = (
        fire_score * RISK_WEIGHTS["fire"]
        + water_score * RISK_WEIGHTS["water"]
        + storm_score * RISK_WEIGHTS["storm"]
        + eq_score * RISK_WEIGHTS["earthquake"]
        + poll_score * RISK_WEIGHTS["pollution"]
        + struct_score * RISK_WEIGHTS["structural"]
        + liab_score * RISK_WEIGHTS["liability"]
    )
    overall_score = round(_clamp(weighted_sum / total_weight), 1)

    # Top risks
    sorted_dims = sorted(breakdown.items(), key=lambda x: x[1]["score"], reverse=True)
    top_risks = [{"dimension": dim, "score": info["score"], "level": info["level"]} for dim, info in sorted_dims[:3]]

    # Coverage gaps
    coverage_gaps = _detect_gaps(breakdown, policies)

    return {
        "overall_score": overall_score,
        "grade": _score_to_grade(overall_score),
        "breakdown": breakdown,
        "estimated_premium_factor": _compute_premium_factor(overall_score),
        "coverage_gaps": coverage_gaps,
        "top_risks": top_risks,
        "computed_at": datetime.now(UTC).isoformat(),
    }


async def detect_coverage_gaps(db: AsyncSession, building_id: UUID) -> list[dict]:
    """Compare insurance policies vs actual risks.

    E.g., high flood risk but no elementaire coverage = gap.
    """
    profile = await compute_insurance_risk_profile(db, building_id)
    return profile.get("coverage_gaps", [])
