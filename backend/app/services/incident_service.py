"""
BatiConnect - Incident & Damage Memory Service

CRUD + analytics for incidents and damage observations.
Auto-creates BuildingEvents in the change grammar when incidents are recorded.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import DamageObservation, IncidentEpisode
from app.services import change_tracker_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Incident CRUD
# ---------------------------------------------------------------------------


async def create_incident(
    db: AsyncSession,
    building_id: UUID,
    organization_id: UUID,
    *,
    incident_type: str,
    title: str,
    severity: str = "minor",
    discovered_at: datetime | None = None,
    created_by: UUID | None = None,
    **kwargs,
) -> IncidentEpisode:
    """Record a new incident. Auto-creates a BuildingEvent in change grammar."""
    incident = IncidentEpisode(
        building_id=building_id,
        organization_id=organization_id,
        incident_type=incident_type,
        title=title,
        severity=severity,
        discovered_at=discovered_at or datetime.now(UTC),
        created_by=created_by,
        **kwargs,
    )
    db.add(incident)
    await db.flush()
    await db.refresh(incident)

    # Wire into change grammar
    await change_tracker_service.record_event(
        db,
        building_id,
        "incident_reported",
        title,
        severity=_map_severity_to_event(severity),
        source_type="incident_episode",
        source_id=incident.id,
        description=f"Incident de type {incident_type} signalé (gravité: {severity})",
    )

    logger.info("Created incident %s for building %s: %s", incident.id, building_id, title)
    return incident


async def update_incident(
    db: AsyncSession,
    incident_id: UUID,
    **updates,
) -> IncidentEpisode | None:
    """Update incident status, resolution, cost, etc."""
    result = await db.execute(select(IncidentEpisode).where(IncidentEpisode.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        return None

    for key, value in updates.items():
        if hasattr(incident, key):
            setattr(incident, key, value)

    await db.flush()
    await db.refresh(incident)
    return incident


async def resolve_incident(
    db: AsyncSession,
    incident_id: UUID,
    resolution_description: str,
    repair_cost_chf: float | None = None,
) -> IncidentEpisode | None:
    """Mark incident as resolved."""
    result = await db.execute(select(IncidentEpisode).where(IncidentEpisode.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        return None

    incident.status = "resolved"
    incident.resolved_at = datetime.now(UTC)
    incident.response_description = resolution_description
    if repair_cost_chf is not None:
        incident.repair_cost_chf = repair_cost_chf

    await db.flush()
    await db.refresh(incident)

    # Wire resolution into change grammar
    await change_tracker_service.record_event(
        db,
        incident.building_id,
        "incident_resolved",
        f"Incident résolu: {incident.title}",
        severity="info",
        source_type="incident_episode",
        source_id=incident.id,
        description=resolution_description,
    )

    logger.info("Resolved incident %s", incident_id)
    return incident


async def get_incident(
    db: AsyncSession,
    incident_id: UUID,
) -> IncidentEpisode | None:
    """Get a single incident by ID."""
    result = await db.execute(select(IncidentEpisode).where(IncidentEpisode.id == incident_id))
    return result.scalar_one_or_none()


async def get_building_incidents(
    db: AsyncSession,
    building_id: UUID,
    *,
    status: str | None = None,
    incident_type: str | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[IncidentEpisode], int]:
    """List incidents for a building with optional filters."""
    query = select(IncidentEpisode).where(IncidentEpisode.building_id == building_id)
    count_query = select(func.count()).select_from(IncidentEpisode).where(IncidentEpisode.building_id == building_id)

    if status:
        query = query.where(IncidentEpisode.status == status)
        count_query = count_query.where(IncidentEpisode.status == status)
    if incident_type:
        query = query.where(IncidentEpisode.incident_type == incident_type)
        count_query = count_query.where(IncidentEpisode.incident_type == incident_type)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(IncidentEpisode.discovered_at.desc()).offset((page - 1) * size).limit(size)
    items = (await db.execute(query)).scalars().all()
    return list(items), total


async def get_recurring_incidents(
    db: AsyncSession,
    building_id: UUID,
) -> list[IncidentEpisode]:
    """Find recurring incidents (recurring=True or same type+zone pattern)."""
    # Explicitly flagged recurring
    query = (
        select(IncidentEpisode)
        .where(
            IncidentEpisode.building_id == building_id,
            IncidentEpisode.recurring.is_(True),
        )
        .order_by(IncidentEpisode.discovered_at.desc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Damage Observations
# ---------------------------------------------------------------------------


async def add_damage_observation(
    db: AsyncSession,
    building_id: UUID,
    *,
    damage_type: str,
    location_description: str,
    severity: str = "cosmetic",
    progression: str = "unknown",
    observed_at: datetime | None = None,
    observed_by_id: UUID | None = None,
    incident_id: UUID | None = None,
    zone_id: UUID | None = None,
    element_id: UUID | None = None,
    photo_document_ids: list | None = None,
    notes: str | None = None,
) -> DamageObservation:
    """Record a damage observation."""
    obs = DamageObservation(
        building_id=building_id,
        incident_id=incident_id,
        damage_type=damage_type,
        location_description=location_description,
        severity=severity,
        progression=progression,
        observed_at=observed_at or datetime.now(UTC),
        observed_by_id=observed_by_id,
        zone_id=zone_id,
        element_id=element_id,
        photo_document_ids=photo_document_ids,
        notes=notes,
    )
    db.add(obs)
    await db.flush()
    await db.refresh(obs)
    logger.info("Recorded damage observation %s for building %s", obs.id, building_id)
    return obs


# ---------------------------------------------------------------------------
# Risk Profile & Insurer Summary
# ---------------------------------------------------------------------------


async def get_incident_risk_profile(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Risk profile based on incident history."""
    all_q = select(IncidentEpisode).where(IncidentEpisode.building_id == building_id)
    all_incidents = list((await db.execute(all_q)).scalars().all())

    unresolved = [i for i in all_incidents if i.status not in ("resolved",)]
    recurring = [i for i in all_incidents if i.recurring]

    # By type
    type_counts: dict[str, int] = {}
    for i in all_incidents:
        type_counts[i.incident_type] = type_counts.get(i.incident_type, 0) + 1

    # By severity
    severity_counts: dict[str, int] = {}
    for i in all_incidents:
        severity_counts[i.severity] = severity_counts.get(i.severity, 0) + 1

    # Total repair cost
    total_cost = sum(i.repair_cost_chf or 0 for i in all_incidents)

    # Avg resolution time (for resolved incidents)
    resolved = [i for i in all_incidents if i.resolved_at and i.discovered_at]
    avg_days = None
    if resolved:
        total_days = sum((i.resolved_at - i.discovered_at).total_seconds() / 86400 for i in resolved)
        avg_days = round(total_days / len(resolved), 1)

    # Most common type/cause
    most_type = max(type_counts, key=type_counts.get) if type_counts else None
    cause_counts: dict[str, int] = {}
    for i in all_incidents:
        if i.cause_category and i.cause_category != "unknown":
            cause_counts[i.cause_category] = cause_counts.get(i.cause_category, 0) + 1
    most_cause = max(cause_counts, key=cause_counts.get) if cause_counts else None

    return {
        "building_id": str(building_id),
        "total_incidents": len(all_incidents),
        "unresolved_count": len(unresolved),
        "recurring_count": len(recurring),
        "by_type": [{"incident_type": k, "count": v} for k, v in sorted(type_counts.items(), key=lambda x: -x[1])],
        "by_severity": [{"severity": k, "count": v} for k, v in sorted(severity_counts.items(), key=lambda x: -x[1])],
        "total_repair_cost_chf": total_cost,
        "avg_resolution_days": avg_days,
        "most_common_type": most_type,
        "most_common_cause": most_cause,
    }


async def get_insurer_incident_summary(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Summary formatted for insurer readiness (safe_to_insure)."""
    all_q = select(IncidentEpisode).where(IncidentEpisode.building_id == building_id)
    all_incidents = list((await db.execute(all_q)).scalars().all())

    claims_filed = [i for i in all_incidents if i.insurance_claim_filed]
    unresolved = [i for i in all_incidents if i.status not in ("resolved",)]
    recurring = [i for i in all_incidents if i.recurring]
    occupant_impact = [i for i in all_incidents if i.occupant_impact]
    critical = [i for i in all_incidents if i.severity == "critical"]
    total_cost = sum(i.repair_cost_chf or 0 for i in all_incidents)

    # Last incident date
    last_incident = max((i.discovered_at for i in all_incidents), default=None) if all_incidents else None

    # Risk rating
    risk_rating = _compute_insurer_risk_rating(
        total=len(all_incidents),
        unresolved=len(unresolved),
        recurring=len(recurring),
        critical=len(critical),
    )

    return {
        "building_id": str(building_id),
        "total_incidents": len(all_incidents),
        "claims_filed": len(claims_filed),
        "unresolved_incidents": len(unresolved),
        "recurring_risks": len(recurring),
        "total_damage_cost_chf": total_cost,
        "occupant_impact_incidents": len(occupant_impact),
        "critical_incidents": len(critical),
        "last_incident_at": last_incident.isoformat() if last_incident else None,
        "risk_rating": risk_rating,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _map_severity_to_event(severity: str) -> str:
    """Map incident severity to BuildingEvent severity."""
    mapping = {
        "minor": "minor",
        "moderate": "minor",
        "major": "significant",
        "critical": "critical",
    }
    return mapping.get(severity, "info")


def _compute_insurer_risk_rating(
    *,
    total: int,
    unresolved: int,
    recurring: int,
    critical: int,
) -> str:
    """Compute a simple insurer risk rating based on incident history."""
    if critical >= 2 or unresolved >= 3 or recurring >= 3:
        return "high"
    if critical >= 1 or unresolved >= 2 or recurring >= 2 or total >= 5:
        return "elevated"
    if total >= 2 or unresolved >= 1 or recurring >= 1:
        return "moderate"
    return "low"
