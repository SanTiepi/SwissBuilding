"""ERP Integration — stable API endpoints for ERP consumption.

Exposes deterministic, versioned payloads that ERPs (Quorum, ImmoTop, etc.)
can poll or subscribe to. The output shape is a CONTRACT — version bumps
only on breaking changes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.erp_payload import ErpBuildingPayload, ErpPortfolioPayload, ErpVersionInfo
from app.services.erp_payload_service import get_erp_payload, get_erp_portfolio_payload

router = APIRouter()


@router.get(
    "/erp/buildings/{building_id}",
    response_model=ErpBuildingPayload,
    tags=["ERP Integration"],
    summary="Single building ERP payload",
)
async def erp_building(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> ErpBuildingPayload:
    """Return a stable, versioned ERP payload for a single building."""
    result = await get_erp_payload(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/erp/organizations/{org_id}/buildings",
    response_model=ErpPortfolioPayload,
    tags=["ERP Integration"],
    summary="Portfolio ERP payload for an organization",
)
async def erp_portfolio(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> ErpPortfolioPayload:
    """Return a stable, versioned ERP payload for all buildings in an organization."""
    result = await get_erp_portfolio_payload(db, org_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No buildings found for this organization")
    return result


@router.get(
    "/erp/version",
    response_model=ErpVersionInfo,
    tags=["ERP Integration"],
    summary="ERP payload version and changelog",
)
async def erp_version() -> ErpVersionInfo:
    """Return the current ERP payload version and changelog."""
    return ErpVersionInfo()
