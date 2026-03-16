"""Knowledge gap analysis endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.knowledge_gap import (
    InvestigationPriorityResult,
    KnowledgeCompletenessResult,
    KnowledgeGapResult,
    PortfolioKnowledgeOverview,
)
from app.services.knowledge_gap_service import (
    analyze_knowledge_gaps,
    estimate_knowledge_completeness,
    get_investigation_priorities,
    get_portfolio_knowledge_overview,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/knowledge-gaps",
    response_model=KnowledgeGapResult,
)
async def get_building_knowledge_gaps(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Identify knowledge gaps for a building."""
    result = await analyze_knowledge_gaps(db, building_id)
    if result.total_gaps == 0 and not result.gaps:
        # Check if building exists by trying completeness
        completeness = await estimate_knowledge_completeness(db, building_id)
        if completeness.overall_score == 0.0 and not completeness.pollutant_scores:
            raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/buildings/{building_id}/investigation-priorities",
    response_model=InvestigationPriorityResult,
)
async def get_building_investigation_priorities(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get ranked investigation priorities for a building."""
    result = await get_investigation_priorities(db, building_id)
    return result


@router.get(
    "/buildings/{building_id}/knowledge-completeness",
    response_model=KnowledgeCompletenessResult,
)
async def get_building_knowledge_completeness(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge completeness score for a building."""
    result = await estimate_knowledge_completeness(db, building_id)
    if result.overall_score == 0.0 and not result.pollutant_scores:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/organizations/{org_id}/knowledge-overview",
    response_model=PortfolioKnowledgeOverview,
)
async def get_org_knowledge_overview(
    org_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-level knowledge overview for an organisation."""
    result = await get_portfolio_knowledge_overview(db, org_id)
    return result
