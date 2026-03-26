"""BatiConnect - Ecosystem Engagement service.

Universal engagement system where any ecosystem actor can leave a binding trace
in SwissBuilding: seen, accepted, contested, confirmed, reserved, refused,
acknowledged, certified.

Chaque engagement est une trace opposable -- il materialise la responsabilite
de l'acteur dans l'ecosysteme immobilier.
"""

import hashlib
import json
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ecosystem_engagement import EcosystemEngagement
from app.schemas.ecosystem_engagement import (
    ActorBuildingEngagement,
    ActorEngagementProfile,
    EcosystemEngagementCreate,
    EcosystemEngagementRead,
    EngagementCountByActor,
    EngagementCountByType,
    EngagementDepth,
    EngagementSummary,
    EngagementTimeline,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# French labels for engagement types (for domain events / notifications)
# ---------------------------------------------------------------------------
ENGAGEMENT_TYPE_LABELS_FR: dict[str, str] = {
    "seen": "Vu",
    "accepted": "Accepte",
    "contested": "Conteste",
    "confirmed": "Confirme",
    "reserved": "Reserve",
    "refused": "Refuse",
    "acknowledged": "Pris en connaissance",
    "certified": "Certifie",
}

ACTOR_TYPE_LABELS_FR: dict[str, str] = {
    "diagnostician": "Diagnostiqueur",
    "contractor": "Entrepreneur",
    "property_manager": "Gerant",
    "owner": "Proprietaire",
    "insurer": "Assureur",
    "authority": "Autorite",
    "fiduciary": "Fiduciaire",
}

# Max distinct engagement types for depth scoring
_MAX_ENGAGEMENT_TYPES = len(ENGAGEMENT_TYPE_LABELS_FR)


def _compute_content_hash(data: dict | list | str | None) -> str | None:
    """Compute SHA-256 hash of content for integrity verification."""
    if data is None:
        return None
    raw = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def create_engagement(
    db: AsyncSession,
    building_id: UUID,
    data: EcosystemEngagementCreate,
    user_id: UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> EcosystemEngagement:
    """Record a binding engagement. Creates DomainEvent."""
    engagement = EcosystemEngagement(
        building_id=building_id,
        actor_type=data.actor_type,
        actor_org_id=data.actor_org_id,
        actor_user_id=data.actor_user_id or user_id,
        actor_name=data.actor_name,
        actor_email=data.actor_email,
        subject_type=data.subject_type,
        subject_id=data.subject_id,
        subject_label=data.subject_label,
        engagement_type=data.engagement_type,
        status="active",
        comment=data.comment,
        conditions=data.conditions,
        content_hash=data.content_hash or _compute_content_hash(data.conditions),
        content_version=data.content_version,
        engaged_at=datetime.utcnow(),
        expires_at=data.expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
        source_type="manual",
        confidence="declared",
    )
    db.add(engagement)

    # Emit DomainEvent
    await _emit_domain_event(db, engagement, user_id)

    logger.info(
        "Engagement created: %s %s on %s/%s for building %s",
        data.actor_type,
        data.engagement_type,
        data.subject_type,
        data.subject_id,
        building_id,
    )
    return engagement


async def list_engagements(
    db: AsyncSession,
    building_id: UUID,
    actor_type: str | None = None,
    subject_type: str | None = None,
    engagement_type: str | None = None,
) -> list[EcosystemEngagement]:
    """List engagements for a building with optional filters."""
    stmt = (
        select(EcosystemEngagement)
        .where(EcosystemEngagement.building_id == building_id)
        .order_by(EcosystemEngagement.engaged_at.desc())
    )
    if actor_type:
        stmt = stmt.where(EcosystemEngagement.actor_type == actor_type)
    if subject_type:
        stmt = stmt.where(EcosystemEngagement.subject_type == subject_type)
    if engagement_type:
        stmt = stmt.where(EcosystemEngagement.engagement_type == engagement_type)

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_engagement_summary(db: AsyncSession, building_id: UUID) -> EngagementSummary:
    """Aggregate engagement stats for a building."""
    base = select(EcosystemEngagement).where(
        EcosystemEngagement.building_id == building_id,
        EcosystemEngagement.status == "active",
    )

    # Total count
    count_result = await db.execute(select(sa_func.count()).select_from(base.subquery()))
    total = count_result.scalar() or 0

    # By actor type
    actor_stmt = (
        select(
            EcosystemEngagement.actor_type,
            sa_func.count().label("cnt"),
        )
        .where(
            EcosystemEngagement.building_id == building_id,
            EcosystemEngagement.status == "active",
        )
        .group_by(EcosystemEngagement.actor_type)
    )
    actor_result = await db.execute(actor_stmt)
    by_actor = [EngagementCountByActor(actor_type=r[0], count=r[1]) for r in actor_result.all()]

    # By engagement type
    type_stmt = (
        select(
            EcosystemEngagement.engagement_type,
            sa_func.count().label("cnt"),
        )
        .where(
            EcosystemEngagement.building_id == building_id,
            EcosystemEngagement.status == "active",
        )
        .group_by(EcosystemEngagement.engagement_type)
    )
    type_result = await db.execute(type_stmt)
    by_type = [EngagementCountByType(engagement_type=r[0], count=r[1]) for r in type_result.all()]

    # Latest 5
    latest_stmt = (
        select(EcosystemEngagement)
        .where(
            EcosystemEngagement.building_id == building_id,
            EcosystemEngagement.status == "active",
        )
        .order_by(EcosystemEngagement.engaged_at.desc())
        .limit(5)
    )
    latest_result = await db.execute(latest_stmt)
    latest = [EcosystemEngagementRead.model_validate(e) for e in latest_result.scalars().all()]

    return EngagementSummary(
        building_id=building_id,
        total=total,
        by_actor_type=by_actor,
        by_engagement_type=by_type,
        latest=latest,
    )


async def get_engagement_timeline(db: AsyncSession, building_id: UUID) -> EngagementTimeline:
    """Chronological engagement history."""
    stmt = (
        select(EcosystemEngagement)
        .where(EcosystemEngagement.building_id == building_id)
        .order_by(EcosystemEngagement.engaged_at.asc())
    )
    result = await db.execute(stmt)
    items = [EcosystemEngagementRead.model_validate(e) for e in result.scalars().all()]
    return EngagementTimeline(
        building_id=building_id,
        engagements=items,
        count=len(items),
    )


async def get_actor_engagements(
    db: AsyncSession,
    org_id: UUID | None = None,
    user_id: UUID | None = None,
) -> ActorEngagementProfile:
    """What has this actor engaged on across all buildings."""
    stmt = select(EcosystemEngagement).where(EcosystemEngagement.status == "active")
    if org_id:
        stmt = stmt.where(EcosystemEngagement.actor_org_id == org_id)
    if user_id:
        stmt = stmt.where(EcosystemEngagement.actor_user_id == user_id)
    stmt = stmt.order_by(EcosystemEngagement.engaged_at.desc())

    result = await db.execute(stmt)
    rows = result.scalars().all()
    engagements = [
        ActorBuildingEngagement(
            building_id=e.building_id,
            engagement_type=e.engagement_type,
            subject_type=e.subject_type,
            engaged_at=e.engaged_at,
        )
        for e in rows
    ]
    return ActorEngagementProfile(
        actor_org_id=org_id,
        actor_user_id=user_id,
        total=len(engagements),
        engagements=engagements,
    )


async def contest_engagement(
    db: AsyncSession,
    engagement_id: UUID,
    comment: str,
    user_id: UUID | None = None,
    ip_address: str | None = None,
) -> EcosystemEngagement:
    """Contest a previous engagement (creates new engagement of type 'contested')."""
    original = await _get_or_raise(db, engagement_id)

    contested = EcosystemEngagement(
        building_id=original.building_id,
        actor_type=original.actor_type,
        actor_org_id=original.actor_org_id,
        actor_user_id=user_id or original.actor_user_id,
        actor_name=original.actor_name,
        actor_email=original.actor_email,
        subject_type=original.subject_type,
        subject_id=original.subject_id,
        subject_label=original.subject_label,
        engagement_type="contested",
        status="active",
        comment=comment,
        content_hash=original.content_hash,
        content_version=original.content_version,
        engaged_at=datetime.utcnow(),
        ip_address=ip_address,
        source_type="manual",
        confidence="declared",
    )
    db.add(contested)

    await _emit_domain_event(db, contested, user_id)

    logger.info(
        "Engagement %s contested with comment: %s",
        engagement_id,
        comment[:80],
    )
    return contested


async def supersede_engagement(
    db: AsyncSession,
    engagement_id: UUID,
    new_data: EcosystemEngagementCreate,
    user_id: UUID | None = None,
    ip_address: str | None = None,
) -> EcosystemEngagement:
    """Replace an engagement with a new one (marks old as superseded)."""
    original = await _get_or_raise(db, engagement_id)
    original.status = "superseded"

    new_engagement = EcosystemEngagement(
        building_id=original.building_id,
        actor_type=new_data.actor_type,
        actor_org_id=new_data.actor_org_id,
        actor_user_id=new_data.actor_user_id or user_id,
        actor_name=new_data.actor_name,
        actor_email=new_data.actor_email,
        subject_type=new_data.subject_type,
        subject_id=new_data.subject_id,
        subject_label=new_data.subject_label,
        engagement_type=new_data.engagement_type,
        status="active",
        comment=new_data.comment,
        conditions=new_data.conditions,
        content_hash=new_data.content_hash or _compute_content_hash(new_data.conditions),
        content_version=new_data.content_version,
        engaged_at=datetime.utcnow(),
        expires_at=new_data.expires_at,
        ip_address=ip_address,
        source_type="manual",
        confidence="declared",
    )
    db.add(new_engagement)

    await _emit_domain_event(db, new_engagement, user_id)

    logger.info(
        "Engagement %s superseded by new engagement",
        engagement_id,
    )
    return new_engagement


async def compute_engagement_depth(db: AsyncSession, building_id: UUID) -> EngagementDepth:
    """How deeply the ecosystem is engaged. Measures lock-in strength.

    More unique actors + more engagement types = harder to replace.
    """
    active = select(EcosystemEngagement).where(
        EcosystemEngagement.building_id == building_id,
        EcosystemEngagement.status == "active",
    )

    # Total
    total_result = await db.execute(select(sa_func.count()).select_from(active.subquery()))
    total = total_result.scalar() or 0

    # Unique actors (by user_id or org_id or actor_email)
    actor_stmt = select(sa_func.count(sa_func.distinct(EcosystemEngagement.actor_user_id))).where(
        EcosystemEngagement.building_id == building_id,
        EcosystemEngagement.status == "active",
        EcosystemEngagement.actor_user_id.isnot(None),
    )
    actor_result = await db.execute(actor_stmt)
    unique_actors = actor_result.scalar() or 0

    # Unique orgs
    org_stmt = select(sa_func.count(sa_func.distinct(EcosystemEngagement.actor_org_id))).where(
        EcosystemEngagement.building_id == building_id,
        EcosystemEngagement.status == "active",
        EcosystemEngagement.actor_org_id.isnot(None),
    )
    org_result = await db.execute(org_stmt)
    unique_orgs = org_result.scalar() or 0

    # Engagement type coverage
    type_stmt = select(sa_func.count(sa_func.distinct(EcosystemEngagement.engagement_type))).where(
        EcosystemEngagement.building_id == building_id,
        EcosystemEngagement.status == "active",
    )
    type_result = await db.execute(type_stmt)
    type_coverage = type_result.scalar() or 0

    # Depth score: normalized 0.0 - 1.0
    # Weighted: 40% actor diversity, 30% org diversity, 30% type coverage
    actor_score = min(unique_actors / 5.0, 1.0) if unique_actors > 0 else 0.0
    org_score = min(unique_orgs / 3.0, 1.0) if unique_orgs > 0 else 0.0
    type_score = min(type_coverage / _MAX_ENGAGEMENT_TYPES, 1.0)
    depth_score = round(0.4 * actor_score + 0.3 * org_score + 0.3 * type_score, 3)

    return EngagementDepth(
        building_id=building_id,
        unique_actors=unique_actors,
        unique_orgs=unique_orgs,
        engagement_type_coverage=type_coverage,
        total_engagements=total,
        depth_score=depth_score,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_or_raise(db: AsyncSession, engagement_id: UUID) -> EcosystemEngagement:
    """Fetch engagement by ID or raise ValueError."""
    result = await db.execute(select(EcosystemEngagement).where(EcosystemEngagement.id == engagement_id))
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise ValueError(f"Engagement {engagement_id} not found")
    return engagement


async def _emit_domain_event(
    db: AsyncSession,
    engagement: EcosystemEngagement,
    actor_user_id: UUID | None,
) -> None:
    """Persist a DomainEvent for the engagement."""
    try:
        from app.models.domain_event import DomainEvent

        label_fr = ENGAGEMENT_TYPE_LABELS_FR.get(engagement.engagement_type, engagement.engagement_type)
        actor_label = ACTOR_TYPE_LABELS_FR.get(engagement.actor_type, engagement.actor_type)

        event = DomainEvent(
            event_type="ecosystem_engagement_created",
            aggregate_type="building",
            aggregate_id=engagement.building_id,
            payload={
                "engagement_id": str(engagement.id),
                "actor_type": engagement.actor_type,
                "actor_label_fr": actor_label,
                "subject_type": engagement.subject_type,
                "subject_id": str(engagement.subject_id),
                "engagement_type": engagement.engagement_type,
                "engagement_label_fr": label_fr,
                "comment": engagement.comment,
            },
            actor_user_id=actor_user_id,
            occurred_at=engagement.engaged_at,
        )
        db.add(event)
    except Exception:
        logger.warning("Failed to emit DomainEvent for engagement %s", engagement.id, exc_info=True)
