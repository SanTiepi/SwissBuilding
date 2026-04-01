"""BatiConnect — DefectShield service: construction defect deadline calculator.

Legal basis:
- Art. 367 al. 1bis CO: 60 calendar days from discovery to notify (since 01.01.2026)
- Art. 371 CO: 5-year prescription for hidden defects, 2 years for manifest
- New-build guarantee: right to free rectification within 2 years of purchase
"""

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.defect_timeline import DefectTimeline
from app.schemas.defect_timeline import DefectAlertResponse, DefectTimelineCreate

# ---------------------------------------------------------------------------
# Pure computation functions (no DB)
# ---------------------------------------------------------------------------

NOTIFICATION_DAYS = 60  # Art. 367 al. 1bis CO
NEW_BUILD_GUARANTEE_DAYS = 730  # 2 years
HIDDEN_DEFECT_PRESCRIPTION_DAYS = 5 * 365  # 5 years (CO 371)
MANIFEST_DEFECT_PRESCRIPTION_DAYS = 2 * 365  # 2 years

HIDDEN_DEFECT_TYPES = {"pollutant", "structural"}


def compute_deadline(discovery_date: date) -> date:
    """Art. 367 al. 1bis CO: 60 calendar days from discovery."""
    return discovery_date + timedelta(days=NOTIFICATION_DAYS)


def check_new_build_guarantee(purchase_date: date, discovery_date: date) -> bool:
    """New build <2 years: right to free rectification."""
    return (discovery_date - purchase_date).days < NEW_BUILD_GUARANTEE_DAYS


def compute_prescription(purchase_date: date, defect_type: str) -> date:
    """Prescription: 5 years for hidden defects (CO 371), 2 years for manifest."""
    if defect_type in HIDDEN_DEFECT_TYPES:
        return purchase_date + timedelta(days=HIDDEN_DEFECT_PRESCRIPTION_DAYS)
    return purchase_date + timedelta(days=MANIFEST_DEFECT_PRESCRIPTION_DAYS)


def classify_urgency(days_remaining: int) -> str:
    """Classify urgency based on days remaining until notification deadline."""
    if days_remaining <= 7:
        return "critical"
    if days_remaining <= 15:
        return "urgent"
    if days_remaining <= 30:
        return "warning"
    return "normal"


# ---------------------------------------------------------------------------
# DB-bound service functions
# ---------------------------------------------------------------------------


async def create_timeline(db: AsyncSession, data: DefectTimelineCreate) -> DefectTimeline:
    """Create a DefectTimeline with computed fields."""
    notification_deadline = compute_deadline(data.discovery_date)

    guarantee_type = "standard"
    prescription_date = None

    if data.purchase_date:
        if check_new_build_guarantee(data.purchase_date, data.discovery_date):
            guarantee_type = "new_build_rectification"
        prescription_date = compute_prescription(data.purchase_date, data.defect_type)

    timeline = DefectTimeline(
        building_id=data.building_id,
        diagnostic_id=data.diagnostic_id,
        defect_type=data.defect_type,
        description=data.description,
        discovery_date=data.discovery_date,
        purchase_date=data.purchase_date,
        notification_deadline=notification_deadline,
        guarantee_type=guarantee_type,
        prescription_date=prescription_date,
        status="active",
    )
    db.add(timeline)
    await db.commit()
    await db.refresh(timeline)
    return timeline


async def list_building_timelines(db: AsyncSession, building_id: UUID) -> list[DefectTimeline]:
    """List all defect timelines for a building."""
    result = await db.execute(
        select(DefectTimeline)
        .where(DefectTimeline.building_id == building_id)
        .order_by(DefectTimeline.notification_deadline.asc())
    )
    return list(result.scalars().all())


async def get_timeline(db: AsyncSession, timeline_id: UUID) -> DefectTimeline | None:
    """Get a single DefectTimeline by ID."""
    result = await db.execute(select(DefectTimeline).where(DefectTimeline.id == timeline_id))
    return result.scalar_one_or_none()


async def update_timeline_status(db: AsyncSession, timeline_id: UUID, status: str, **kwargs) -> DefectTimeline | None:
    """Update timeline status and optional fields."""
    timeline = await get_timeline(db, timeline_id)
    if not timeline:
        return None
    timeline.status = status
    for key, value in kwargs.items():
        if hasattr(timeline, key):
            setattr(timeline, key, value)
    await db.commit()
    await db.refresh(timeline)
    return timeline


async def get_active_alerts(
    db: AsyncSession, days_threshold: int = 45, building_id: UUID | None = None
) -> list[DefectAlertResponse]:
    """Get all active defects with deadline within N days."""
    today = date.today()
    threshold_date = today + timedelta(days=days_threshold)

    query = select(DefectTimeline).where(
        DefectTimeline.status == "active",
        DefectTimeline.notification_deadline <= threshold_date,
        DefectTimeline.notification_deadline >= today,
    )
    if building_id:
        query = query.where(DefectTimeline.building_id == building_id)

    query = query.order_by(DefectTimeline.notification_deadline.asc())
    result = await db.execute(query)
    timelines = result.scalars().all()

    alerts = []
    for t in timelines:
        days_remaining = (t.notification_deadline - today).days
        alerts.append(
            DefectAlertResponse(
                building_id=t.building_id,
                defect_id=t.id,
                defect_type=t.defect_type,
                description=t.description,
                notification_deadline=t.notification_deadline,
                days_remaining=days_remaining,
                urgency=classify_urgency(days_remaining),
            )
        )
    return alerts


async def detect_expired(db: AsyncSession) -> list[DefectTimeline]:
    """Detect and mark expired active defects (deadline passed without notification)."""
    today = date.today()
    result = await db.execute(
        select(DefectTimeline).where(
            DefectTimeline.status == "active",
            DefectTimeline.notification_deadline < today,
        )
    )
    expired = list(result.scalars().all())
    for t in expired:
        t.status = "expired"
    if expired:
        await db.commit()
    return expired
