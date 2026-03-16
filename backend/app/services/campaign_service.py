"""
SwissBuildingOS - Campaign Service

Business logic for campaign CRUD and progress tracking.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ACTION_STATUS_DONE, ACTION_STATUS_IN_PROGRESS
from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.campaign import Campaign
from app.schemas.campaign import CampaignCreate, CampaignImpact, CampaignUpdate


async def create_campaign(
    db: AsyncSession,
    data: CampaignCreate,
    created_by: UUID | None = None,
) -> Campaign:
    """Create a new campaign. Validates building_ids exist and sets target_count."""
    building_ids_str: list[str] | None = None
    target_count = 0

    if data.building_ids:
        # Validate that all building IDs exist
        stmt = select(func.count()).select_from(Building).where(Building.id.in_(data.building_ids))
        result = await db.execute(stmt)
        count = result.scalar() or 0
        if count != len(data.building_ids):
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="One or more building IDs do not exist")
        building_ids_str = [str(bid) for bid in data.building_ids]
        target_count = len(data.building_ids)

    campaign = Campaign(
        title=data.title,
        description=data.description,
        campaign_type=data.campaign_type,
        priority=data.priority,
        organization_id=data.organization_id,
        building_ids=building_ids_str,
        target_count=target_count,
        date_start=data.date_start,
        date_end=data.date_end,
        budget_chf=data.budget_chf,
        criteria_json=data.criteria_json,
        notes=data.notes,
        created_by=created_by,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def get_campaign(db: AsyncSession, campaign_id: UUID) -> Campaign | None:
    """Get a single campaign by ID."""
    stmt = select(Campaign).where(Campaign.id == campaign_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_campaign(
    db: AsyncSession,
    campaign_id: UUID,
    data: CampaignUpdate,
) -> Campaign | None:
    """Update an existing campaign. Returns None if not found."""
    campaign = await get_campaign(db, campaign_id)
    if campaign is None:
        return None

    update_data = data.model_dump(exclude_unset=True)

    # If building_ids are being updated, recompute target_count
    if "building_ids" in update_data and update_data["building_ids"] is not None:
        building_ids = update_data["building_ids"]
        if building_ids:
            stmt = select(func.count()).select_from(Building).where(Building.id.in_(building_ids))
            result = await db.execute(stmt)
            count = result.scalar() or 0
            if count != len(building_ids):
                from fastapi import HTTPException

                raise HTTPException(status_code=400, detail="One or more building IDs do not exist")
            update_data["building_ids"] = [str(bid) for bid in building_ids]
            update_data["target_count"] = len(building_ids)
        else:
            update_data["target_count"] = 0

    for field, value in update_data.items():
        setattr(campaign, field, value)

    await db.commit()
    await db.refresh(campaign)
    return campaign


async def delete_campaign(db: AsyncSession, campaign_id: UUID) -> bool:
    """Delete a campaign. Returns False if not found."""
    campaign = await get_campaign(db, campaign_id)
    if campaign is None:
        return False
    await db.delete(campaign)
    await db.commit()
    return True


async def list_campaigns(
    db: AsyncSession,
    *,
    status: str | None = None,
    campaign_type: str | None = None,
    organization_id: UUID | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Campaign], int]:
    """List campaigns with optional filters and pagination. Returns (items, total)."""
    query = select(Campaign).order_by(Campaign.created_at.desc())
    count_query = select(func.count()).select_from(Campaign)

    if status:
        query = query.where(Campaign.status == status)
        count_query = count_query.where(Campaign.status == status)
    if campaign_type:
        query = query.where(Campaign.campaign_type == campaign_type)
        count_query = count_query.where(Campaign.campaign_type == campaign_type)
    if organization_id:
        query = query.where(Campaign.organization_id == organization_id)
        count_query = count_query.where(Campaign.organization_id == organization_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def link_actions_to_campaign(
    db: AsyncSession,
    campaign_id: UUID,
    action_item_ids: list[UUID],
) -> int:
    """Link action items to a campaign. Returns count of linked items."""
    campaign = await get_campaign(db, campaign_id)
    if campaign is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Campaign not found")

    linked = 0
    for aid in action_item_ids:
        stmt = select(ActionItem).where(ActionItem.id == aid)
        result = await db.execute(stmt)
        action = result.scalar_one_or_none()
        if action is not None:
            action.campaign_id = campaign_id
            linked += 1

    await db.commit()
    return linked


async def list_campaign_actions(
    db: AsyncSession,
    campaign_id: UUID,
) -> list[ActionItem]:
    """List all action items linked to a campaign."""
    stmt = select(ActionItem).where(ActionItem.campaign_id == campaign_id).order_by(ActionItem.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_campaign_progress(db: AsyncSession, campaign_id: UUID) -> Campaign | None:
    """Recompute completed_count from linked actions with status 'done'."""
    campaign = await get_campaign(db, campaign_id)
    if campaign is None:
        return None

    stmt = (
        select(func.count())
        .select_from(ActionItem)
        .where(ActionItem.campaign_id == campaign_id, ActionItem.status == ACTION_STATUS_DONE)
    )
    result = await db.execute(stmt)
    done_count = result.scalar() or 0

    campaign.completed_count = done_count
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def get_campaign_impact(db: AsyncSession, campaign_id: UUID) -> CampaignImpact | None:
    """Compute impact metrics for a campaign."""
    campaign = await get_campaign(db, campaign_id)
    if campaign is None:
        return None

    # Count buildings affected
    building_ids = campaign.building_ids or []
    buildings_affected = len(building_ids)

    # Count actions by status
    total_stmt = select(func.count()).select_from(ActionItem).where(ActionItem.campaign_id == campaign_id)
    total_result = await db.execute(total_stmt)
    actions_total = total_result.scalar() or 0

    done_stmt = (
        select(func.count())
        .select_from(ActionItem)
        .where(ActionItem.campaign_id == campaign_id, ActionItem.status == ACTION_STATUS_DONE)
    )
    done_result = await db.execute(done_stmt)
    actions_completed = done_result.scalar() or 0

    in_progress_stmt = (
        select(func.count())
        .select_from(ActionItem)
        .where(
            ActionItem.campaign_id == campaign_id,
            ActionItem.status == ACTION_STATUS_IN_PROGRESS,
        )
    )
    in_progress_result = await db.execute(in_progress_stmt)
    actions_in_progress = in_progress_result.scalar() or 0

    # Completion rate
    completion_rate = actions_completed / actions_total if actions_total > 0 else 0.0

    # Velocity: actions completed per day since date_start
    today = date.today()
    velocity = 0.0
    if campaign.date_start and actions_completed > 0:
        days_elapsed = (today - campaign.date_start).days
        if days_elapsed > 0:
            velocity = actions_completed / days_elapsed

    # Budget utilization
    budget_chf = campaign.budget_chf or 0.0
    spent_chf = campaign.spent_chf or 0.0
    budget_utilization = spent_chf / budget_chf if budget_chf > 0 else 0.0

    # Estimated completion date
    estimated_completion_date: date | None = None
    if velocity > 0 and actions_total > 0 and campaign.date_start:
        days_needed = actions_total / velocity
        estimated_completion_date = campaign.date_start + timedelta(days=int(days_needed))

    # Days remaining
    days_remaining: int | None = None
    if campaign.date_end:
        days_remaining = (campaign.date_end - today).days

    # At-risk detection
    is_at_risk = False
    if campaign.date_start and campaign.date_end and actions_total > 0:
        total_duration = (campaign.date_end - campaign.date_start).days
        elapsed = (today - campaign.date_start).days
        if total_duration > 0 and elapsed > 0:
            expected_rate = elapsed / total_duration
            is_at_risk = completion_rate < expected_rate and (days_remaining is not None and days_remaining < 30)

    return CampaignImpact(
        buildings_affected=buildings_affected,
        actions_total=actions_total,
        actions_completed=actions_completed,
        actions_in_progress=actions_in_progress,
        completion_rate=round(completion_rate, 4),
        velocity=round(velocity, 4),
        budget_utilization=round(budget_utilization, 4),
        estimated_completion_date=estimated_completion_date,
        days_remaining=days_remaining,
        is_at_risk=is_at_risk,
    )
