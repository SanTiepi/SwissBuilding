"""Building passport export API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.passport_exchange import PassportExchangeDocument
from app.schemas.passport_export import (
    BuildingPassportExport,
    PassportComparison,
    PassportValidation,
    PortfolioPassportSummary,
)
from app.services.passport_exchange_service import export_passport
from app.services.passport_export_service import (
    compare_passports,
    generate_building_passport,
    get_portfolio_passport_summary,
    validate_passport,
)

router = APIRouter()


@router.get(
    "/passport-export/buildings/{building_id}/generate",
    response_model=BuildingPassportExport,
)
async def generate_passport_endpoint(
    building_id: UUID,
    format: str = Query(default="json", pattern="^(json|summary)$"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> BuildingPassportExport:
    """Generate a comprehensive building passport export."""
    result = await generate_building_passport(building_id, db, format_type=format)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/passport-export/buildings/{building_id}/validate",
    response_model=PassportValidation,
)
async def validate_passport_endpoint(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> PassportValidation:
    """Validate passport readiness for a building."""
    result = await validate_passport(building_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/passport-export/compare",
    response_model=PassportComparison,
)
async def compare_passports_endpoint(
    building_a: UUID = Query(...),
    building_b: UUID = Query(...),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> PassportComparison:
    """Compare passports for two buildings."""
    result = await compare_passports(building_a, building_b, db)
    if result is None:
        raise HTTPException(status_code=404, detail="One or both buildings not found")
    return result


@router.get(
    "/passport-export/organizations/{org_id}/summary",
    response_model=PortfolioPassportSummary,
)
async def portfolio_summary_endpoint(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> PortfolioPassportSummary:
    """Get a portfolio-level passport summary for an organization."""
    result = await get_portfolio_passport_summary(org_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return result


@router.get(
    "/buildings/{building_id}/passport/export",
    response_model=PassportExchangeDocument,
)
async def export_passport_exchange(
    building_id: UUID,
    format: str = Query(default="json", pattern="^json$"),
    include_transfer: bool = Query(default=False),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
) -> PassportExchangeDocument:
    """Export a building passport as a standardized JSON exchange document."""
    result = await export_passport(db, building_id, include_transfer=include_transfer)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
