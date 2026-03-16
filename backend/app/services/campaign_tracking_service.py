"""
SwissBuildingOS - Campaign Tracking Service

Per-building execution tracking within campaigns.
Stores tracking data in campaign.criteria_json under a "tracking" key.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.schemas.campaign_tracking import (
    BuildingCampaignStatus,
    BuildingStatusUpdate,
    CampaignExecutionSummary,
    CampaignProgress,
)

VALID_STATUSES = {"not_started", "in_progress", "blocked", "completed", "skipped"}
STALE_THRESHOLD_DAYS = 7


async def _get_campaign_or_404(db: AsyncSession, campaign_id: UUID) -> Campaign:
    """Fetch campaign or raise 404."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


def _get_tracking_data(campaign: Campaign) -> dict:
    """Extract tracking dict from criteria_json."""
    criteria = campaign.criteria_json or {}
    return criteria.get("tracking", {})


def _building_ids(campaign: Campaign) -> list[str]:
    """Get building IDs from the campaign as strings."""
    return campaign.building_ids or []


def _build_status(building_id_str: str, data: dict) -> BuildingCampaignStatus:
    """Build a BuildingCampaignStatus from raw tracking data."""
    return BuildingCampaignStatus(
        building_id=UUID(building_id_str),
        status=data.get("status", "not_started"),
        started_at=_parse_dt(data.get("started_at")),
        completed_at=_parse_dt(data.get("completed_at")),
        blocker_reason=data.get("blocker_reason"),
        notes=data.get("notes"),
        progress_pct=data.get("progress_pct", 0.0),
    )


def _parse_dt(val: str | None) -> datetime | None:
    if val is None:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


async def get_building_statuses(db: AsyncSession, campaign_id: UUID) -> list[BuildingCampaignStatus]:
    """Return status for each building in the campaign."""
    campaign = await _get_campaign_or_404(db, campaign_id)
    tracking = _get_tracking_data(campaign)
    bids = _building_ids(campaign)

    result = []
    for bid in bids:
        entry = tracking.get(bid, {})
        result.append(_build_status(bid, entry))
    return result


async def update_building_status(
    db: AsyncSession,
    campaign_id: UUID,
    building_id: UUID,
    update: BuildingStatusUpdate,
) -> BuildingCampaignStatus:
    """Update a building's tracking status within a campaign."""
    campaign = await _get_campaign_or_404(db, campaign_id)
    bid_str = str(building_id)
    bids = _building_ids(campaign)

    if bid_str not in bids:
        raise HTTPException(
            status_code=404,
            detail="Building not found in this campaign",
        )

    if update.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {update.status}")

    criteria = campaign.criteria_json or {}
    tracking = criteria.get("tracking", {})
    entry = tracking.get(bid_str, {})

    now_iso = datetime.now(UTC).isoformat()

    # Status transitions
    old_status = entry.get("status", "not_started")
    entry["status"] = update.status
    entry["updated_at"] = now_iso

    if update.status == "in_progress" and old_status == "not_started":
        entry["started_at"] = now_iso
    elif update.status == "completed":
        entry["completed_at"] = now_iso
        entry["progress_pct"] = 100.0
    elif update.status == "blocked":
        entry["blocker_reason"] = update.blocker_reason

    if update.blocker_reason is not None:
        entry["blocker_reason"] = update.blocker_reason
    if update.notes is not None:
        entry["notes"] = update.notes
    if update.progress_pct is not None and update.status != "completed":
        entry["progress_pct"] = update.progress_pct

    tracking[bid_str] = entry
    criteria["tracking"] = tracking
    campaign.criteria_json = criteria

    # Force SQLAlchemy to detect JSON mutation
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(campaign, "criteria_json")

    await db.commit()
    await db.refresh(campaign)

    return _build_status(bid_str, entry)


async def get_campaign_progress(db: AsyncSession, campaign_id: UUID) -> CampaignProgress:
    """Compute aggregated progress metrics."""
    campaign = await _get_campaign_or_404(db, campaign_id)
    tracking = _get_tracking_data(campaign)
    bids = _building_ids(campaign)
    total = len(bids)

    by_status: dict[str, int] = {}
    total_progress = 0.0
    completed_count = 0
    at_risk = 0
    now = datetime.now(UTC)

    for bid in bids:
        entry = tracking.get(bid, {})
        status = entry.get("status", "not_started")
        by_status[status] = by_status.get(status, 0) + 1
        total_progress += entry.get("progress_pct", 0.0)

        if status == "completed":
            completed_count += 1
        if status == "blocked":
            at_risk += 1
        elif status == "in_progress":
            updated_at = _parse_dt(entry.get("updated_at"))
            if updated_at and (now - updated_at) > timedelta(days=STALE_THRESHOLD_DAYS):
                at_risk += 1

    overall_pct = (total_progress / total) if total > 0 else 0.0

    # Velocity: completed buildings / elapsed days
    velocity: float | None = None
    estimated: datetime | None = None
    if campaign.date_start:
        start_dt = datetime(
            campaign.date_start.year,
            campaign.date_start.month,
            campaign.date_start.day,
            tzinfo=UTC,
        )
        elapsed_days = max((now - start_dt).days, 1)
        velocity = completed_count / elapsed_days
        remaining = total - completed_count
        if velocity > 0 and remaining > 0:
            days_left = remaining / velocity
            estimated = now + timedelta(days=days_left)

    return CampaignProgress(
        campaign_id=campaign_id,
        total_buildings=total,
        by_status=by_status,
        overall_progress_pct=round(overall_pct, 1),
        estimated_completion=estimated,
        velocity_per_day=round(velocity, 4) if velocity is not None else None,
        at_risk_count=at_risk,
    )


async def get_execution_summary(db: AsyncSession, campaign_id: UUID) -> CampaignExecutionSummary:
    """Full summary with recent updates and stale detection."""
    campaign = await _get_campaign_or_404(db, campaign_id)
    progress = await get_campaign_progress(db, campaign_id)
    tracking = _get_tracking_data(campaign)
    bids = _building_ids(campaign)
    now = datetime.now(UTC)

    # Recent updates: entries with updated_at, sorted desc, top 10
    updates: list[dict] = []
    stale: list[UUID] = []

    for bid in bids:
        entry = tracking.get(bid, {})
        updated_at = _parse_dt(entry.get("updated_at"))
        status = entry.get("status", "not_started")

        if updated_at:
            updates.append(
                {
                    "building_id": bid,
                    "status": status,
                    "updated_at": entry["updated_at"],
                }
            )
            if status not in ("completed", "skipped") and (now - updated_at) > timedelta(days=STALE_THRESHOLD_DAYS):
                stale.append(UUID(bid))
        elif status == "not_started":
            # Never updated and campaign is active — stale if campaign started 7+ days ago
            if campaign.date_start:
                start_dt = datetime(
                    campaign.date_start.year,
                    campaign.date_start.month,
                    campaign.date_start.day,
                    tzinfo=UTC,
                )
                if (now - start_dt) > timedelta(days=STALE_THRESHOLD_DAYS):
                    stale.append(UUID(bid))

    updates.sort(key=lambda x: x["updated_at"], reverse=True)
    recent = updates[:10]

    return CampaignExecutionSummary(
        campaign_id=campaign_id,
        campaign_name=campaign.title,
        progress=progress,
        recent_updates=recent,
        stale_buildings=stale,
    )


async def get_blocked_buildings(db: AsyncSession, campaign_id: UUID) -> list[BuildingCampaignStatus]:
    """Return only blocked buildings."""
    statuses = await get_building_statuses(db, campaign_id)
    return [s for s in statuses if s.status == "blocked"]


async def batch_update_status(
    db: AsyncSession,
    campaign_id: UUID,
    building_ids: list[UUID],
    status: str,
) -> int:
    """Batch update multiple buildings to the same status. Returns count updated."""
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    campaign = await _get_campaign_or_404(db, campaign_id)
    bids = _building_ids(campaign)
    criteria = campaign.criteria_json or {}
    tracking = criteria.get("tracking", {})
    now_iso = datetime.now(UTC).isoformat()

    count = 0
    for bid_uuid in building_ids:
        bid_str = str(bid_uuid)
        if bid_str not in bids:
            continue
        entry = tracking.get(bid_str, {})
        old_status = entry.get("status", "not_started")
        entry["status"] = status
        entry["updated_at"] = now_iso

        if status == "in_progress" and old_status == "not_started":
            entry["started_at"] = now_iso
        elif status == "completed":
            entry["completed_at"] = now_iso
            entry["progress_pct"] = 100.0

        tracking[bid_str] = entry
        count += 1

    criteria["tracking"] = tracking
    campaign.criteria_json = criteria

    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(campaign, "criteria_json")

    await db.commit()
    return count
