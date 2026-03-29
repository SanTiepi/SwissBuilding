"""Compliance Nudge Engine API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.nudge import NudgeListRead, NudgeRead
from app.services.nudge_engine import generate_nudges, generate_portfolio_nudges

router = APIRouter()


@router.get(
    "/buildings/{building_id}/nudges",
    response_model=NudgeListRead,
)
async def get_building_nudges(
    building_id: UUID,
    context: str = Query(default="dashboard", pattern="^(dashboard|detail|email)$"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get behavioral compliance nudges for a building."""
    nudges = await generate_nudges(db, building_id, context=context)
    return NudgeListRead(
        entity_id=building_id,
        nudges=[NudgeRead(**n) for n in nudges],
        total=len(nudges),
        context=context,
    )


@router.get(
    "/portfolio/nudges",
    response_model=NudgeListRead,
)
async def get_portfolio_nudges(
    context: str = Query(default="dashboard", pattern="^(dashboard|detail|email)$"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-level behavioral compliance nudges."""
    org_id = current_user.organization_id
    if org_id is None:
        return NudgeListRead(
            entity_id=current_user.id,
            nudges=[],
            total=0,
            context=context,
        )

    nudges = await generate_portfolio_nudges(db, org_id, context=context)
    return NudgeListRead(
        entity_id=org_id,
        nudges=[NudgeRead(**n) for n in nudges],
        total=len(nudges),
        context=context,
    )
