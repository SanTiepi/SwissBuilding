"""BatiConnect — DefectShield service: construction defect deadline calculator.

Legal basis:
- Art. 367 al. 1bis CO: 60 calendar days from discovery to notify (since 01.01.2026)
- Art. 371 CO: 5-year prescription for hidden defects, 2 years for manifest
- New-build guarantee: right to free rectification within 2 years of purchase
- Swiss legal practice: if deadline falls on weekend/holiday, extends to next business day
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import NamedTuple
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

# Valid status transitions for DefectTimeline
VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "active": {"notified", "expired", "resolved"},
    "notified": {"resolved"},
    "expired": {"resolved"},  # allow resolution even after expiry (late notification)
    "resolved": set(),  # terminal state
}


# ---------------------------------------------------------------------------
# Swiss public holidays (federal + common cantonal)
# ---------------------------------------------------------------------------


def _swiss_holidays(year: int) -> set[date]:
    """Return Swiss federal + widely observed cantonal holidays for a given year.

    Includes: New Year, Berchtoldstag, Good Friday, Easter Monday,
    Ascension, Whit Monday, National Day, Christmas, St Stephen's.
    Easter is computed via the anonymous Gregorian algorithm.
    """
    # Anonymous Gregorian Easter algorithm
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    easter = date(year, month, day)

    return {
        date(year, 1, 1),  # New Year
        date(year, 1, 2),  # Berchtoldstag
        easter - timedelta(days=2),  # Good Friday
        easter + timedelta(days=1),  # Easter Monday
        easter + timedelta(days=39),  # Ascension Thursday
        easter + timedelta(days=50),  # Whit Monday
        date(year, 8, 1),  # Swiss National Day
        date(year, 12, 25),  # Christmas
        date(year, 12, 26),  # St Stephen's Day
    }


def _is_business_day(d: date) -> bool:
    """Check if a date is a Swiss business day (not weekend, not holiday)."""
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return d not in _swiss_holidays(d.year)


def _next_business_day(d: date) -> date:
    """Advance to next business day if d falls on weekend or holiday."""
    while not _is_business_day(d):
        d += timedelta(days=1)
    return d


class NotificationDeadlineResult(NamedTuple):
    """Result of calc_notification_deadline()."""

    deadline: date
    days_remaining: int
    extended: bool  # True if deadline was moved from the raw +60 days


def calc_notification_deadline(
    discovery_date: date,
    reference_date: date | None = None,
) -> NotificationDeadlineResult:
    """Calculate notification deadline per Art. 367 al. 1bis CO.

    - 60 calendar days from discovery_date
    - If the 60th day falls on a weekend or Swiss public holiday,
      the deadline extends to the next business day (Swiss legal practice)
    - Returns the effective deadline, days remaining from reference_date, and
      whether the deadline was extended

    Args:
        discovery_date: Date the defect was discovered.
        reference_date: Date to compute days_remaining from (defaults to today).
    """
    if reference_date is None:
        reference_date = date.today()

    raw_deadline = discovery_date + timedelta(days=NOTIFICATION_DAYS)
    effective_deadline = _next_business_day(raw_deadline)
    days_remaining = (effective_deadline - reference_date).days
    extended = effective_deadline != raw_deadline

    return NotificationDeadlineResult(
        deadline=effective_deadline,
        days_remaining=days_remaining,
        extended=extended,
    )


def compute_deadline(discovery_date: date) -> date:
    """Art. 367 al. 1bis CO: 60 calendar days from discovery, business-day adjusted."""
    return calc_notification_deadline(discovery_date).deadline


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


async def update_defect_status(
    db: AsyncSession,
    timeline_id: UUID,
    new_status: str,
    **kwargs,
) -> DefectTimeline:
    """Transition a DefectTimeline to a new status with validation.

    Raises:
        ValueError: If the timeline doesn't exist or the transition is invalid.
    """
    timeline = await get_timeline(db, timeline_id)
    if not timeline:
        raise ValueError(f"DefectTimeline {timeline_id} not found")

    allowed = VALID_STATUS_TRANSITIONS.get(timeline.status, set())
    if new_status not in allowed:
        raise ValueError(
            f"Invalid transition: {timeline.status} → {new_status}. "
            f"Allowed: {sorted(allowed) if allowed else 'none (terminal state)'}"
        )

    timeline.status = new_status
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
