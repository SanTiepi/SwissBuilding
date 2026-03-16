from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.action_item import ActionItemRead
from app.schemas.campaign import (
    CampaignCreate,
    CampaignImpact,
    CampaignListResponse,
    CampaignResponse,
    CampaignUpdate,
)
from app.services.audit_service import log_action
from app.services.campaign_service import (
    create_campaign,
    delete_campaign,
    get_campaign,
    get_campaign_impact,
    link_actions_to_campaign,
    list_campaign_actions,
    list_campaigns,
    update_campaign,
    update_campaign_progress,
)

router = APIRouter()


def _campaign_to_response(campaign) -> dict:
    """Convert a Campaign ORM object to a response dict with computed progress_pct."""
    target = campaign.target_count or 0
    completed = campaign.completed_count or 0
    progress_pct = (completed / target * 100.0) if target > 0 else 0.0
    return {
        "id": campaign.id,
        "title": campaign.title,
        "description": campaign.description,
        "campaign_type": campaign.campaign_type,
        "status": campaign.status,
        "priority": campaign.priority,
        "organization_id": campaign.organization_id,
        "building_ids": campaign.building_ids,
        "target_count": target,
        "completed_count": completed,
        "progress_pct": round(progress_pct, 1),
        "date_start": campaign.date_start,
        "date_end": campaign.date_end,
        "budget_chf": campaign.budget_chf,
        "spent_chf": campaign.spent_chf,
        "criteria_json": campaign.criteria_json,
        "notes": campaign.notes,
        "created_by": campaign.created_by,
        "created_at": campaign.created_at,
        "updated_at": campaign.updated_at,
    }


@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign_endpoint(
    data: CampaignCreate,
    current_user: User = Depends(require_permission("campaigns", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new campaign."""
    campaign = await create_campaign(db, data, created_by=current_user.id)
    await log_action(db, current_user.id, "create", "campaign", campaign.id)
    return _campaign_to_response(campaign)


@router.get("/campaigns", response_model=CampaignListResponse)
async def list_campaigns_endpoint(
    status: str | None = None,
    campaign_type: str | None = None,
    organization_id: UUID | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permission("campaigns", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List campaigns with optional filters and pagination."""
    items, total = await list_campaigns(
        db,
        status=status,
        campaign_type=campaign_type,
        organization_id=organization_id,
        page=page,
        size=size,
    )
    pages = (total + size - 1) // size if total > 0 else 0
    return {
        "items": [_campaign_to_response(c) for c in items],
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.get("/campaigns/recommendations")
async def get_campaign_recommendations(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-recommended campaigns based on portfolio analysis."""
    from app.services.campaign_recommender import recommend_campaigns

    return await recommend_campaigns(db, owner_id=current_user.id, limit=limit)


@router.get("/campaigns/{campaign_id}/impact", response_model=CampaignImpact)
async def get_campaign_impact_endpoint(
    campaign_id: UUID,
    current_user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get impact metrics for a campaign."""
    impact = await get_campaign_impact(db, campaign_id)
    if not impact:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return impact


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign_endpoint(
    campaign_id: UUID,
    current_user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single campaign."""
    campaign = await get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_to_response(campaign)


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign_endpoint(
    campaign_id: UUID,
    data: CampaignUpdate,
    current_user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing campaign."""
    campaign = await update_campaign(db, campaign_id, data)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await log_action(db, current_user.id, "update", "campaign", campaign_id)
    return _campaign_to_response(campaign)


@router.delete("/campaigns/{campaign_id}", status_code=204)
async def delete_campaign_endpoint(
    campaign_id: UUID,
    current_user: User = Depends(require_permission("campaigns", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a campaign."""
    deleted = await delete_campaign(db, campaign_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await log_action(db, current_user.id, "delete", "campaign", campaign_id)


class LinkActionsRequest(BaseModel):
    action_item_ids: list[UUID]


@router.post("/campaigns/{campaign_id}/actions", status_code=200)
async def link_actions_endpoint(
    campaign_id: UUID,
    data: LinkActionsRequest,
    current_user: User = Depends(require_permission("campaigns", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Link action items to a campaign."""
    linked = await link_actions_to_campaign(db, campaign_id, data.action_item_ids)
    return {"linked": linked}


@router.get("/campaigns/{campaign_id}/actions", response_model=list[ActionItemRead])
async def list_campaign_actions_endpoint(
    campaign_id: UUID,
    current_user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all action items linked to a campaign."""
    campaign = await get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    actions = await list_campaign_actions(db, campaign_id)
    return actions


@router.get("/campaigns/{campaign_id}/progress", response_model=CampaignResponse)
async def get_campaign_progress_endpoint(
    campaign_id: UUID,
    current_user: User = Depends(require_permission("campaigns", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compute and return updated progress for a campaign."""
    campaign = await update_campaign_progress(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_to_response(campaign)
