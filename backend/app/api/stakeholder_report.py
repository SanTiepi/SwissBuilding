"""Stakeholder-specific report API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.stakeholder_report import (
    AuthorityReport,
    ContractorBriefing,
    OwnerReport,
    PortfolioExecutiveSummary,
)
from app.services.stakeholder_report_service import (
    generate_authority_report,
    generate_contractor_briefing,
    generate_owner_report,
    generate_portfolio_executive_summary,
)

router = APIRouter()


@router.get("/buildings/{building_id}/report/owner", response_model=OwnerReport)
async def owner_report(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate an owner-facing building report with plain language summaries."""
    result = await generate_owner_report(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get("/buildings/{building_id}/report/authority", response_model=AuthorityReport)
async def authority_report(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate an authority-facing regulatory compliance report."""
    result = await generate_authority_report(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get("/buildings/{building_id}/report/contractor", response_model=ContractorBriefing)
async def contractor_report(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a contractor-facing work briefing with safety requirements."""
    result = await generate_contractor_briefing(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get("/organizations/{org_id}/report/executive", response_model=PortfolioExecutiveSummary)
async def executive_report(
    org_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a C-level portfolio executive summary."""
    result = await generate_portfolio_executive_summary(db, org_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return result
