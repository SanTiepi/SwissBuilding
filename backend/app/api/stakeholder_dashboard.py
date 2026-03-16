"""Stakeholder-specific dashboard API endpoints.

Each endpoint auto-detects the current user's role and returns a
role-appropriate dashboard view.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.stakeholder_dashboard import (
    AuthorityDashboard,
    ContractorDashboard,
    DiagnosticianDashboard,
    OwnerDashboard,
)
from app.services.stakeholder_dashboard_service import (
    get_authority_dashboard,
    get_contractor_dashboard,
    get_diagnostician_dashboard,
    get_owner_dashboard,
)

router = APIRouter()


@router.get("/dashboard/owner", response_model=OwnerDashboard)
async def owner_dashboard(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Property owner dashboard: buildings, risk, deadlines, costs."""
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{current_user.role}' cannot access owner dashboard.",
        )
    return await get_owner_dashboard(db, current_user.id)


@router.get("/dashboard/diagnostician", response_model=DiagnosticianDashboard)
async def diagnostician_dashboard(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Diagnostician dashboard: assigned work, quality, validation backlog."""
    if current_user.role not in ("diagnostician", "admin"):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{current_user.role}' cannot access diagnostician dashboard.",
        )
    return await get_diagnostician_dashboard(db, current_user.id)


@router.get("/dashboard/authority", response_model=AuthorityDashboard)
async def authority_dashboard(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Authority dashboard: jurisdiction overview, compliance, approval queue."""
    if current_user.role not in ("authority", "admin"):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{current_user.role}' cannot access authority dashboard.",
        )
    return await get_authority_dashboard(db, current_user.id)


@router.get("/dashboard/contractor", response_model=ContractorDashboard)
async def contractor_dashboard(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Contractor dashboard: interventions, work status, certifications."""
    if current_user.role not in ("contractor", "admin"):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{current_user.role}' cannot access contractor dashboard.",
        )
    return await get_contractor_dashboard(db, current_user.id)
