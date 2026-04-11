"""BatiConnect — Predictive Readiness API routes.

Proactively scans buildings for upcoming readiness risks and generates
preventive actions.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.predictive_readiness_service import (
    generate_predictive_actions,
    scan_building,
    scan_portfolio,
)

router = APIRouter()


@router.get("/portfolio/predictive-readiness", tags=["Predictive Readiness"])
async def get_portfolio_predictive_readiness(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Scan all buildings in the user's organization for upcoming readiness risks."""
    org_id = current_user.organization_id
    if org_id is None:
        return {
            "alerts": [],
            "summary": {
                "critical": 0,
                "warning": 0,
                "info": 0,
                "buildings_at_risk": 0,
                "diagnostics_expiring_90d": 0,
            },
            "projections": [],
        }

    result = await scan_portfolio(db, org_id)
    return result


@router.get(
    "/buildings/{building_id}/predictive-readiness",
    tags=["Predictive Readiness"],
)
async def get_building_predictive_readiness(
    building_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Scan a single building for upcoming readiness risks."""
    result = await scan_building(db, building_id)
    return result


@router.post("/portfolio/predictive-actions", tags=["Predictive Readiness"])
async def create_predictive_actions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate preventive ActionItems for predicted risks. Idempotent."""
    org_id = current_user.organization_id
    if org_id is None:
        raise HTTPException(status_code=400, detail="User has no organization")

    created = await generate_predictive_actions(db, org_id)
    await db.commit()
    return {
        "created_count": len(created),
        "actions": created,
    }
