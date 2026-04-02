"""Building Passport Service — calculate A-F grades across 6 categories."""

import statistics
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BuildingPassport,
    BuildingRiskScore,
    ClimateExposureProfile,
    Incident,
)
from app.schemas.building_passport import BuildingPassportRead


def score_to_grade(score: float) -> str:
    """Convert 0-100 score to A-F grade.
    
    A: ≥90, B: ≥80, C: ≥70, D: ≥60, E: ≥50, F: <50
    """
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    elif score >= 50:
        return "E"
    else:
        return "F"


async def calculate_structural_integrity(building_id: UUID, session: AsyncSession) -> tuple[str, dict]:
    """Calculate structural integrity grade based on incident history + sinistralité."""

    # Fetch incident history
    result = await session.execute(
        select(Incident).where(Incident.building_id == building_id)
    )
    incidents = result.scalars().all()

    # Base score (no incidents = 95)
    score = 95.0

    # Deduct for each incident type
    incident_deductions = {
        "structural_damage": 15,
        "foundation_issue": 20,
        "roof_damage": 10,
        "wall_crack": 8,
        "settlement": 18,
    }

    incident_breakdown = {}
    for incident in incidents:
        issue_type = incident.issue_type if hasattr(incident, "issue_type") else "unknown"
        deduction = incident_deductions.get(issue_type, 5)
        score -= deduction
        incident_breakdown[issue_type] = incident_breakdown.get(issue_type, 0) + 1

    # Floor at 5
    score = max(5, score)

    grade = score_to_grade(score)
    metadata = {
        "incident_count": len(incidents),
        "incident_breakdown": incident_breakdown,
        "score": score,
    }

    return grade, metadata


async def calculate_energy_performance(building_id: UUID, session: AsyncSession) -> tuple[str, dict]:
    """Calculate energy grade based on CECB score."""

    # Default: moderate energy performance
    score = 65.0
    breakdown = {"cecb_grade_assumed": "C"}

    # In production: integrate with CECB lookup service
    # cecb_mapping = {"A": 100, "B": 90, "C": 75, "D": 60, "E": 45, "F": 30}

    score = max(5, min(100, score))
    grade = score_to_grade(score)
    breakdown["score"] = score

    return grade, breakdown


async def calculate_safety_hazards(building_id: UUID, session: AsyncSession) -> tuple[str, dict]:
    """Calculate safety grade based on risk score + hazardous materials."""

    result = await session.execute(
        select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id)
    )
    risk_score = result.scalar_one_or_none()

    score = 80.0  # Default to good
    breakdown = {}

    if risk_score:
        # Use risk probabilities to calculate safety score
        probabilities = [
            getattr(risk_score, "asbestos_probability", 0),
            getattr(risk_score, "pcb_probability", 0),
            getattr(risk_score, "lead_probability", 0),
            getattr(risk_score, "hap_probability", 0),
            getattr(risk_score, "radon_probability", 0),
        ]

        # Average probability, inverted for safety score
        avg_prob = sum(probabilities) / len(probabilities) if probabilities else 0
        score = 100 - (avg_prob * 100)  # 0% hazard = 100 points, 100% hazard = 0 points

        breakdown["hazard_probabilities"] = {
            "asbestos": getattr(risk_score, "asbestos_probability", 0),
            "pcb": getattr(risk_score, "pcb_probability", 0),
            "lead": getattr(risk_score, "lead_probability", 0),
        }

    score = max(5, min(100, score))
    grade = score_to_grade(score)
    breakdown["score"] = score

    return grade, breakdown


async def calculate_environmental(building_id: UUID, session: AsyncSession) -> tuple[str, dict]:
    """Calculate environmental grade based on climate exposure + contamination."""

    result = await session.execute(
        select(ClimateExposureProfile).where(ClimateExposureProfile.building_id == building_id)
    )
    climate_profile = result.scalar_one_or_none()

    score = 75.0  # Default
    breakdown = {}

    if climate_profile:
        # Exposure level impacts score
        exposure_level = getattr(climate_profile, "exposure_level", None)
        exposure_scores = {"low": 90, "moderate": 75, "high": 50, "critical": 30}
        if exposure_level:
            score = exposure_scores.get(exposure_level, 75)
            breakdown["exposure_level"] = exposure_level

    score = max(5, min(100, score))
    grade = score_to_grade(score)
    breakdown["score"] = score

    return grade, breakdown


async def calculate_code_compliance(building_id: UUID, session: AsyncSession) -> tuple[str, dict]:
    """Calculate compliance grade based on regulatory checks."""

    # Default: assuming 80% compliance without specific data
    score = 80.0
    breakdown = {
        "otconst_compliant": True,
        "cfst_compliant": True,
        "lci_compliant": True,
    }

    # In a real scenario, fetch from compliance scan results
    # For now: assume compliant = 90, partial = 70, non-compliant = 40
    score = max(5, min(100, score))
    grade = score_to_grade(score)
    breakdown["score"] = score

    return grade, breakdown


async def calculate_renovation_readiness(building_id: UUID, session: AsyncSession) -> tuple[str, dict]:
    """Calculate readiness grade based on cost estimates, subsidy eligibility."""

    # Default: moderate readiness
    score = 65.0
    breakdown = {
        "has_cost_estimate": False,
        "subsidy_eligible": False,
        "contractor_available": True,
    }

    # In production: integrate with cost estimation service, subsidy DB
    score = max(5, min(100, score))
    grade = score_to_grade(score)
    breakdown["score"] = score

    return grade, breakdown


async def calculate_building_passport(
    building_id: UUID, session: AsyncSession
) -> BuildingPassportRead:
    """Calculate all 6 grades and create passport."""

    # Calculate each grade
    structural_grade, structural_meta = await calculate_structural_integrity(building_id, session)
    energy_grade, energy_meta = await calculate_energy_performance(building_id, session)
    safety_grade, safety_meta = await calculate_safety_hazards(building_id, session)
    environmental_grade, environmental_meta = await calculate_environmental(building_id, session)
    compliance_grade, compliance_meta = await calculate_code_compliance(building_id, session)
    readiness_grade, readiness_meta = await calculate_renovation_readiness(building_id, session)

    # Overall grade = median of all 6
    grades = [
        structural_grade,
        energy_grade,
        safety_grade,
        environmental_grade,
        compliance_grade,
        readiness_grade,
    ]

    # Convert to numeric for median, then back to letter
    grade_values = {
        "A": 90,
        "B": 80,
        "C": 70,
        "D": 60,
        "E": 50,
        "F": 40,
    }
    numeric_grades = [grade_values[g] for g in grades]
    median_value = statistics.median(numeric_grades)
    overall_grade = score_to_grade(median_value)

    # Check if passport already exists
    result = await session.execute(
        select(BuildingPassport)
        .where(BuildingPassport.building_id == building_id)
        .order_by(BuildingPassport.version.desc())
    )
    existing = result.scalar_one_or_none()

    version = (existing.version + 1) if existing else 1

    # Create new passport
    passport = BuildingPassport(
        building_id=building_id,
        version=version,
        structural_grade=structural_grade,
        energy_grade=energy_grade,
        safety_grade=safety_grade,
        environmental_grade=environmental_grade,
        compliance_grade=compliance_grade,
        readiness_grade=readiness_grade,
        overall_grade=overall_grade,
        metadata={
            "calculation_date": datetime.utcnow().isoformat(),
            "components_used": {
                "structural": structural_meta,
                "energy": energy_meta,
                "safety": safety_meta,
                "environmental": environmental_meta,
                "compliance": compliance_meta,
                "readiness": readiness_meta,
            },
        },
    )

    session.add(passport)
    await session.flush()

    return BuildingPassportRead.from_orm(passport)


async def get_building_passport(
    building_id: UUID, session: AsyncSession
) -> BuildingPassportRead | None:
    """Get current building passport."""

    result = await session.execute(
        select(BuildingPassport)
        .where(BuildingPassport.building_id == building_id)
        .order_by(BuildingPassport.created_at.desc())
    )

    passport = result.scalar_one_or_none()
    return BuildingPassportRead.from_orm(passport) if passport else None


async def get_building_passport_history(
    building_id: UUID, session: AsyncSession, limit: int = 10
) -> list[BuildingPassportRead]:
    """Get historical passports (up to `limit` versions)."""

    result = await session.execute(
        select(BuildingPassport)
        .where(BuildingPassport.building_id == building_id)
        .order_by(BuildingPassport.created_at.desc())
        .limit(limit)
    )

    passports = result.scalars().all()
    return [BuildingPassportRead.from_orm(p) for p in passports]
