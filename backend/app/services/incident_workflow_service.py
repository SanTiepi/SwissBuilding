"""
BatiConnect - Incident Workflow Service

Full incident lifecycle management: create, escalate, resolve incidents,
auto-generate obligations from incident types, and detect recurring patterns.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    ACTION_PRIORITY_CRITICAL,
    ACTION_PRIORITY_HIGH,
    ACTION_PRIORITY_MEDIUM,
    ACTION_SOURCE_SYSTEM,
    ACTION_STATUS_OPEN,
    ACTION_TYPE_INVESTIGATION,
)
from app.models.action_item import ActionItem
from app.models.incident import IncidentEpisode
from app.models.obligation import Obligation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Incident → Obligation mapping
# ---------------------------------------------------------------------------

INCIDENT_OBLIGATION_MAP: dict[str, dict[str, Any]] = {
    "flooding": {"type": "structural_inspection", "deadline_days": 30, "title": "Post-flood structural inspection"},
    "fire": {"type": "fire_safety_review", "deadline_days": 14, "title": "Post-fire safety review"},
    "mold": {"type": "air_quality_test", "deadline_days": 60, "title": "Air quality test after mold discovery"},
    "subsidence": {
        "type": "structural_assessment",
        "deadline_days": 14,
        "title": "Structural assessment after subsidence",
    },
    "contamination": {
        "type": "environmental_assessment",
        "deadline_days": 30,
        "title": "Environmental assessment after contamination",
    },
}

# Severity → action priority mapping
_SEVERITY_PRIORITY: dict[str, str] = {
    "minor": ACTION_PRIORITY_MEDIUM,
    "moderate": ACTION_PRIORITY_HIGH,
    "major": ACTION_PRIORITY_HIGH,
    "critical": ACTION_PRIORITY_CRITICAL,
}

# Severity escalation order
_SEVERITY_ORDER = ("minor", "moderate", "major", "critical")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def create_incident(
    db: AsyncSession,
    building_id: UUID,
    organization_id: UUID,
    data: dict[str, Any],
    created_by_id: UUID | None = None,
) -> IncidentEpisode:
    """Create an incident with auto-generated action items.

    Args:
        db: Async database session.
        building_id: UUID of the building.
        organization_id: UUID of the organization.
        data: Incident data dict (incident_type, title, severity, etc.).
        created_by_id: UUID of the creating user.

    Returns:
        The persisted IncidentEpisode record.
    """
    incident = IncidentEpisode(
        building_id=building_id,
        organization_id=organization_id,
        incident_type=data.get("incident_type", "other"),
        title=data.get("title", "Untitled incident"),
        description=data.get("description"),
        severity=data.get("severity", "minor"),
        location_description=data.get("location_description"),
        zone_id=data.get("zone_id"),
        element_id=data.get("element_id"),
        cause_category=data.get("cause_category", "unknown"),
        occupant_impact=data.get("occupant_impact", False),
        service_disruption=data.get("service_disruption", False),
        status="reported",
        created_by=created_by_id,
    )
    db.add(incident)
    await db.flush()

    # Auto-generate action item for investigation
    priority = _SEVERITY_PRIORITY.get(incident.severity, ACTION_PRIORITY_MEDIUM)
    action = ActionItem(
        building_id=building_id,
        source_type=ACTION_SOURCE_SYSTEM,
        action_type=ACTION_TYPE_INVESTIGATION,
        title=f"Investigate incident: {incident.title}",
        priority=priority,
        status=ACTION_STATUS_OPEN,
        metadata_json={
            "system_key": f"incident_investigation_{incident.id}",
            "incident_id": str(incident.id),
            "incident_type": incident.incident_type,
        },
    )
    db.add(action)

    # Auto-generate obligation if incident type warrants it
    await auto_generate_obligation(db, incident)

    # Check for recurring pattern
    await _check_recurring(db, incident)

    await db.commit()
    await db.refresh(incident)

    logger.info("Created incident %s (type=%s, severity=%s)", incident.id, incident.incident_type, incident.severity)
    return incident


async def escalate_incident(
    db: AsyncSession,
    incident_id: UUID,
    new_severity: str,
) -> IncidentEpisode:
    """Escalate incident severity.

    Args:
        db: Async database session.
        incident_id: UUID of the incident to escalate.
        new_severity: New severity level (must be higher than current).

    Returns:
        The updated IncidentEpisode record.

    Raises:
        ValueError: If incident not found or severity is not an escalation.
    """
    result = await db.execute(select(IncidentEpisode).where(IncidentEpisode.id == incident_id))
    incident = result.scalar_one_or_none()
    if incident is None:
        raise ValueError(f"Incident {incident_id} not found")

    if new_severity not in _SEVERITY_ORDER:
        raise ValueError(f"Invalid severity '{new_severity}'. Must be one of: {', '.join(_SEVERITY_ORDER)}")

    current_idx = _SEVERITY_ORDER.index(incident.severity) if incident.severity in _SEVERITY_ORDER else 0
    new_idx = _SEVERITY_ORDER.index(new_severity)
    if new_idx <= current_idx:
        raise ValueError(
            f"Cannot escalate from '{incident.severity}' to '{new_severity}' — new severity must be higher than current"
        )

    old_severity = incident.severity
    incident.severity = new_severity

    # If escalating to critical, update status to investigating
    if new_severity == "critical" and incident.status == "reported":
        incident.status = "investigating"

    # Generate escalation action
    priority = _SEVERITY_PRIORITY.get(new_severity, ACTION_PRIORITY_HIGH)
    action = ActionItem(
        building_id=incident.building_id,
        source_type=ACTION_SOURCE_SYSTEM,
        action_type=ACTION_TYPE_INVESTIGATION,
        title=f"Escalation: {incident.title} ({old_severity} → {new_severity})",
        priority=priority,
        status=ACTION_STATUS_OPEN,
        metadata_json={
            "system_key": f"incident_escalation_{incident.id}_{new_severity}",
            "incident_id": str(incident.id),
            "old_severity": old_severity,
            "new_severity": new_severity,
        },
    )
    db.add(action)

    await db.commit()
    await db.refresh(incident)

    logger.info("Escalated incident %s from %s to %s", incident_id, old_severity, new_severity)
    return incident


async def resolve_incident(
    db: AsyncSession,
    incident_id: UUID,
    resolution_data: dict[str, Any],
) -> IncidentEpisode:
    """Mark incident as resolved, compute resolution time.

    Args:
        db: Async database session.
        incident_id: UUID of the incident to resolve.
        resolution_data: Dict with optional keys: response_description,
            repair_cost_chf, intervention_id.

    Returns:
        The updated IncidentEpisode record.

    Raises:
        ValueError: If incident not found or already resolved.
    """
    result = await db.execute(select(IncidentEpisode).where(IncidentEpisode.id == incident_id))
    incident = result.scalar_one_or_none()
    if incident is None:
        raise ValueError(f"Incident {incident_id} not found")

    if incident.status == "resolved":
        raise ValueError(f"Incident {incident_id} is already resolved")

    incident.status = "resolved"
    incident.resolved_at = datetime.utcnow()
    incident.response_description = resolution_data.get("response_description", incident.response_description)
    incident.repair_cost_chf = resolution_data.get("repair_cost_chf", incident.repair_cost_chf)

    await db.commit()
    await db.refresh(incident)

    logger.info("Resolved incident %s", incident_id)
    return incident


async def auto_generate_obligation(
    db: AsyncSession,
    incident: IncidentEpisode,
) -> Obligation | None:
    """Auto-create an obligation if the incident type warrants it.

    Idempotent: checks for existing obligations with the same system_key
    via linked_entity_id + linked_entity_type.

    Args:
        db: Async database session.
        incident: The IncidentEpisode to check.

    Returns:
        The created Obligation or None if not applicable.
    """
    mapping = INCIDENT_OBLIGATION_MAP.get(incident.incident_type)
    if mapping is None:
        return None

    # Dedup: check if obligation already exists for this incident
    existing = await db.execute(
        select(Obligation).where(
            and_(
                Obligation.building_id == incident.building_id,
                Obligation.linked_entity_type == "incident",
                Obligation.linked_entity_id == incident.id,
            )
        )
    )
    if existing.scalar_one_or_none() is not None:
        return None

    deadline = date.today() + timedelta(days=mapping["deadline_days"])
    priority = "high" if incident.severity in ("major", "critical") else "medium"

    obligation = Obligation(
        building_id=incident.building_id,
        title=mapping["title"],
        description=f"Auto-generated from incident: {incident.title}",
        obligation_type=mapping["type"],
        due_date=deadline,
        status="upcoming",
        priority=priority,
        linked_entity_type="incident",
        linked_entity_id=incident.id,
        notes=f"Auto-generated from {incident.incident_type} incident ({incident.severity})",
    )
    db.add(obligation)
    await db.flush()

    logger.info(
        "Auto-generated obligation %s (type=%s) from incident %s",
        obligation.id,
        mapping["type"],
        incident.id,
    )
    return obligation


async def get_incident_patterns(
    db: AsyncSession,
    building_id: UUID,
) -> dict[str, Any]:
    """Analyze recurring incident patterns for a building.

    Returns:
        Dict with pattern analysis: type_counts, recurring_count,
        avg_resolution_days, severity_distribution, high_risk_types.
    """
    result = await db.execute(select(IncidentEpisode).where(IncidentEpisode.building_id == building_id))
    incidents = list(result.scalars().all())

    if not incidents:
        return {
            "total_incidents": 0,
            "type_counts": {},
            "recurring_count": 0,
            "avg_resolution_days": None,
            "severity_distribution": {},
            "high_risk_types": [],
        }

    # Type counts
    type_counts: dict[str, int] = {}
    for inc in incidents:
        type_counts[inc.incident_type] = type_counts.get(inc.incident_type, 0) + 1

    # Recurring count
    recurring_count = sum(1 for inc in incidents if inc.recurring)

    # Average resolution time
    resolved = [inc for inc in incidents if inc.resolved_at is not None and inc.discovered_at is not None]
    avg_resolution_days: float | None = None
    if resolved:
        total_days = sum((inc.resolved_at - inc.discovered_at).total_seconds() / 86400 for inc in resolved)
        avg_resolution_days = round(total_days / len(resolved), 1)

    # Severity distribution
    severity_dist: dict[str, int] = {}
    for inc in incidents:
        severity_dist[inc.severity] = severity_dist.get(inc.severity, 0) + 1

    # High-risk types: types with 3+ occurrences or any critical severity
    high_risk_types = [t for t, count in type_counts.items() if count >= 3]
    critical_types = {inc.incident_type for inc in incidents if inc.severity == "critical"}
    high_risk_types = list(set(high_risk_types) | critical_types)

    return {
        "total_incidents": len(incidents),
        "type_counts": type_counts,
        "recurring_count": recurring_count,
        "avg_resolution_days": avg_resolution_days,
        "severity_distribution": severity_dist,
        "high_risk_types": high_risk_types,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _check_recurring(db: AsyncSession, incident: IncidentEpisode) -> None:
    """Check if this incident is part of a recurring pattern and mark accordingly."""
    result = await db.execute(
        select(func.count())
        .select_from(IncidentEpisode)
        .where(
            and_(
                IncidentEpisode.building_id == incident.building_id,
                IncidentEpisode.incident_type == incident.incident_type,
                IncidentEpisode.id != incident.id,
            )
        )
    )
    prior_count = result.scalar() or 0
    if prior_count >= 1:
        incident.recurring = True

        # Find the most recent prior incident of the same type
        prior_result = await db.execute(
            select(IncidentEpisode)
            .where(
                and_(
                    IncidentEpisode.building_id == incident.building_id,
                    IncidentEpisode.incident_type == incident.incident_type,
                    IncidentEpisode.id != incident.id,
                )
            )
            .order_by(IncidentEpisode.created_at.desc())
            .limit(1)
        )
        previous = prior_result.scalar_one_or_none()
        if previous is not None:
            incident.previous_incident_id = previous.id
