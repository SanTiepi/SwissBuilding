"""Observation risk scorer — compute risk score from condition + risk flags."""

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.field_observation import FieldObservation
from app.models.observation_risk_score import ObservationRiskScore

CONDITION_SCORES: dict[str, float] = {
    "good": 10.0,
    "fair": 35.0,
    "poor": 60.0,
    "critical": 85.0,
}

RISK_MULTIPLIERS: dict[str, float] = {
    "water_stain": 1.3,
    "crack": 1.25,
    "mold": 1.4,
    "rust": 1.2,
    "deformation": 1.35,
}


def calculate_risk_score(condition: str | None, flags: list[str] | None) -> float:
    """Pure computation: risk score from condition + flags."""
    base = CONDITION_SCORES.get(condition or "", 0.0)
    if not flags:
        return min(base, 100.0)
    for flag in flags:
        base *= RISK_MULTIPLIERS.get(flag, 1.0)
    return min(round(base, 1), 100.0)


def determine_recommended_action(score: float) -> str:
    """Map score to recommended action."""
    if score >= 70:
        return "urgent_diagnosis"
    if score >= 40:
        return "investigate_further"
    return "monitor"


def determine_urgency_level(score: float) -> str:
    """Map score to urgency level."""
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


async def score_observation(db: AsyncSession, observation_id: UUID) -> ObservationRiskScore:
    """Calculate and persist risk score for a field observation."""
    result = await db.execute(select(FieldObservation).where(FieldObservation.id == observation_id))
    obs = result.scalar_one_or_none()
    if obs is None:
        raise ValueError(f"Observation {observation_id} not found")

    flags = json.loads(obs.risk_flags) if obs.risk_flags else []
    score = calculate_risk_score(obs.condition_assessment, flags)
    action = determine_recommended_action(score)
    urgency = determine_urgency_level(score)

    # Upsert risk score
    existing_result = await db.execute(
        select(ObservationRiskScore).where(ObservationRiskScore.field_observation_id == observation_id)
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.risk_score = score
        existing.recommended_action = action
        existing.urgency_level = urgency
        risk_entry = existing
    else:
        risk_entry = ObservationRiskScore(
            field_observation_id=observation_id,
            building_id=obs.building_id,
            risk_score=score,
            recommended_action=action,
            urgency_level=urgency,
        )
        db.add(risk_entry)

    await db.commit()
    await db.refresh(risk_entry)
    return risk_entry


async def get_risk_score(db: AsyncSession, observation_id: UUID) -> ObservationRiskScore | None:
    """Get risk score for an observation."""
    result = await db.execute(
        select(ObservationRiskScore).where(ObservationRiskScore.field_observation_id == observation_id)
    )
    return result.scalar_one_or_none()
