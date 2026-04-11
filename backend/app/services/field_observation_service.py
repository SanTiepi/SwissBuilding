"""Field observation service — CRUD, verification, and summary."""

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.field_observation import FieldObservation
from app.schemas.field_observation import (
    FieldObservationCreate,
    FieldObservationUpdate,
    FieldObservationVerify,
)


async def create_observation(
    db: AsyncSession,
    building_id: UUID,
    observer_id: UUID,
    data: FieldObservationCreate,
) -> FieldObservation:
    """Create a new field observation."""
    obs = FieldObservation(
        building_id=building_id,
        observer_id=observer_id,
        observation_type=data.observation_type,
        severity=data.severity,
        title=data.title,
        description=data.description,
        zone_id=data.zone_id,
        element_id=data.element_id,
        location_description=data.location_description,
        observed_at=data.observed_at or datetime.now(UTC),
        photo_reference=data.photo_reference,
        metadata_json=data.metadata_json,
        observer_role=data.observer_role,
        tags=json.dumps(data.tags) if data.tags else None,
        context_json=json.dumps(data.context_json) if data.context_json else None,
        confidence=data.confidence,
        # Mobile fields
        condition_assessment=data.condition_assessment,
        risk_flags=json.dumps(data.risk_flags) if data.risk_flags else None,
        photos=json.dumps(data.photos) if data.photos else None,
        gps_lat=data.gps_lat,
        gps_lon=data.gps_lon,
        compass_direction=data.compass_direction,
        inspection_duration_minutes=data.inspection_duration_minutes,
        observer_name=data.observer_name,
    )
    db.add(obs)
    await db.commit()
    await db.refresh(obs)
    return obs


async def list_observations(
    db: AsyncSession,
    building_id: UUID,
    *,
    observation_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    zone_id: UUID | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[FieldObservation], int]:
    """List observations for a building with filters and pagination."""
    query = select(FieldObservation).where(FieldObservation.building_id == building_id)
    count_query = select(func.count()).select_from(FieldObservation).where(FieldObservation.building_id == building_id)

    if observation_type is not None:
        query = query.where(FieldObservation.observation_type == observation_type)
        count_query = count_query.where(FieldObservation.observation_type == observation_type)
    if severity is not None:
        query = query.where(FieldObservation.severity == severity)
        count_query = count_query.where(FieldObservation.severity == severity)
    if status is not None:
        query = query.where(FieldObservation.status == status)
        count_query = count_query.where(FieldObservation.status == status)
    if zone_id is not None:
        query = query.where(FieldObservation.zone_id == zone_id)
        count_query = count_query.where(FieldObservation.zone_id == zone_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(FieldObservation.observed_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = list(result.scalars().all())
    return items, total


async def get_observation(db: AsyncSession, observation_id: UUID) -> FieldObservation | None:
    """Get a single observation by ID."""
    result = await db.execute(select(FieldObservation).where(FieldObservation.id == observation_id))
    return result.scalar_one_or_none()


async def update_observation(
    db: AsyncSession,
    observation_id: UUID,
    data: FieldObservationUpdate,
) -> FieldObservation | None:
    """Update an observation. Returns None if not found."""
    obs = await get_observation(db, observation_id)
    if obs is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    # Serialize tags and context_json if present
    if "tags" in update_data and update_data["tags"] is not None:
        update_data["tags"] = json.dumps(update_data["tags"])
    if "context_json" in update_data and update_data["context_json"] is not None:
        update_data["context_json"] = json.dumps(update_data["context_json"])

    for field, value in update_data.items():
        setattr(obs, field, value)

    await db.commit()
    await db.refresh(obs)
    return obs


async def verify_observation(
    db: AsyncSession,
    observation_id: UUID,
    verifier_id: UUID,
    data: FieldObservationVerify,
) -> FieldObservation | None:
    """Verify or unverify an observation."""
    obs = await get_observation(db, observation_id)
    if obs is None:
        return None

    obs.verified = data.verified
    obs.is_verified = data.verified
    obs.verified_by_id = verifier_id if data.verified else None
    obs.verified_at = datetime.now(UTC) if data.verified else None

    if data.notes:
        # Append verification notes to description
        note_line = f"\n[Verification note: {data.notes}]"
        obs.description = (obs.description or "") + note_line

    await db.commit()
    await db.refresh(obs)
    return obs


async def get_observation_summary(db: AsyncSession, building_id: UUID) -> dict:
    """Get aggregated summary of observations for a building."""
    # Total
    total_result = await db.execute(
        select(func.count()).select_from(FieldObservation).where(FieldObservation.building_id == building_id)
    )
    total = total_result.scalar() or 0

    # By type
    type_result = await db.execute(
        select(FieldObservation.observation_type, func.count())
        .where(FieldObservation.building_id == building_id)
        .group_by(FieldObservation.observation_type)
    )
    by_type = dict(type_result.all())

    # By severity
    severity_result = await db.execute(
        select(FieldObservation.severity, func.count())
        .where(FieldObservation.building_id == building_id)
        .group_by(FieldObservation.severity)
    )
    by_severity = dict(severity_result.all())

    # Unverified count
    unverified_result = await db.execute(
        select(func.count())
        .select_from(FieldObservation)
        .where(FieldObservation.building_id == building_id, FieldObservation.verified.is_(False))
    )
    unverified_count = unverified_result.scalar() or 0

    # Latest observation
    latest_result = await db.execute(
        select(func.max(FieldObservation.observed_at)).where(FieldObservation.building_id == building_id)
    )
    latest = latest_result.scalar()

    return {
        "building_id": building_id,
        "total_observations": total,
        "by_type": by_type,
        "by_severity": by_severity,
        "unverified_count": unverified_count,
        "latest_observation_at": latest,
    }


async def get_unverified_observations(db: AsyncSession, building_id: UUID) -> list[FieldObservation]:
    """Get all unverified observations for a building."""
    result = await db.execute(
        select(FieldObservation)
        .where(FieldObservation.building_id == building_id, FieldObservation.verified.is_(False))
        .order_by(FieldObservation.observed_at.desc())
    )
    return list(result.scalars().all())
