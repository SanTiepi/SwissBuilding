"""Compliance gap analysis API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.compliance_gap import (
    ComplianceCostEstimate,
    ComplianceGapReport,
    ComplianceRoadmap,
    PortfolioComplianceGaps,
)
from app.services.compliance_gap_service import (
    estimate_compliance_cost,
    generate_compliance_roadmap,
    get_portfolio_compliance_gaps,
    identify_compliance_gaps,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/compliance-gaps",
    response_model=ComplianceGapReport,
)
async def get_compliance_gaps(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Identify all non-compliance items for a building."""
    try:
        return await identify_compliance_gaps(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/compliance-roadmap",
    response_model=ComplianceRoadmap,
)
async def get_compliance_roadmap(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate ordered steps to achieve full compliance."""
    try:
        return await generate_compliance_roadmap(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/buildings/{building_id}/compliance-cost",
    response_model=ComplianceCostEstimate,
)
async def get_compliance_cost(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Estimate total cost to reach full compliance."""
    try:
        return await estimate_compliance_cost(db, building_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/organizations/{org_id}/compliance-gaps",
    response_model=PortfolioComplianceGaps,
)
async def get_org_compliance_gaps(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get compliance gap summary for an entire organization."""
    try:
        return await get_portfolio_compliance_gaps(db, org_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
