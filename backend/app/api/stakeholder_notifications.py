"""Stakeholder-targeted notification API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.stakeholder_notification import (
    AuthorityNotificationReport,
    DiagnosticianBrief,
    OwnerBriefing,
    StakeholderDigest,
)
from app.services.stakeholder_notification_service import (
    VALID_DIGEST_ROLES,
    generate_authority_report,
    generate_diagnostician_brief,
    generate_owner_briefing,
    get_stakeholder_digest,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/stakeholder-owner-briefing",
    response_model=OwnerBriefing,
)
async def owner_briefing(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate an owner-focused briefing for a building."""
    result = await generate_owner_briefing(building_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/buildings/{building_id}/stakeholder-diagnostician-brief",
    response_model=DiagnosticianBrief,
)
async def diagnostician_brief(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a diagnostician-focused brief for fieldwork planning."""
    result = await generate_diagnostician_brief(building_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/buildings/{building_id}/stakeholder-authority-report",
    response_model=AuthorityNotificationReport,
)
async def authority_report(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate an authority-focused compliance notification report."""
    result = await generate_authority_report(building_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/organizations/{org_id}/stakeholder-digest",
    response_model=StakeholderDigest,
)
async def stakeholder_digest(
    org_id: uuid.UUID,
    role: str = Query(..., description="Stakeholder role filter"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a role-filtered notification digest across org buildings."""
    if role not in VALID_DIGEST_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(VALID_DIGEST_ROLES)}",
        )
    result = await get_stakeholder_digest(org_id, role, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return result
