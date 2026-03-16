"""Audit readiness API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.audit_readiness import (
    AuditChecklist,
    AuditReadinessResult,
    AuditSimulationResult,
    PortfolioAuditReadiness,
)
from app.services.audit_readiness_service import (
    evaluate_audit_readiness,
    get_audit_checklist,
    get_portfolio_audit_readiness,
    simulate_audit_outcome,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/audit-readiness",
    response_model=AuditReadinessResult,
)
async def get_building_audit_readiness(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate audit readiness score (0-100) for a building."""
    result = await evaluate_audit_readiness(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/buildings/{building_id}/audit-readiness/checklist",
    response_model=AuditChecklist,
)
async def get_building_audit_checklist(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get actionable audit checklist for a building."""
    result = await get_audit_checklist(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/buildings/{building_id}/audit-readiness/simulate",
    response_model=AuditSimulationResult,
)
async def simulate_building_audit(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Simulate audit outcome for a building."""
    result = await simulate_audit_outcome(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/organizations/{org_id}/audit-readiness",
    response_model=PortfolioAuditReadiness,
)
async def get_org_audit_readiness(
    org_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio-level audit readiness for an organisation."""
    result = await get_portfolio_audit_readiness(db, org_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Organisation not found")
    return result
