"""Building certification readiness endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.building_certification import (
    AvailableCertifications,
    CertificationReadiness,
    CertificationRoadmap,
    PortfolioCertificationStatus,
)
from app.services.building_certification_service import (
    evaluate_certification_readiness,
    generate_certification_roadmap,
    get_available_certifications,
    get_portfolio_certification_status,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/certification-readiness",
    response_model=CertificationReadiness,
)
async def certification_readiness_endpoint(
    building_id: uuid.UUID,
    certification_type: str = Query(..., pattern="^(minergie|cecb|snbs|geak)$"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate building readiness for a specific certification type."""
    result = await evaluate_certification_readiness(building_id, certification_type, db)
    if result.readiness_score == 0 and any(r.id == "building_not_found" for r in result.missing_requirements):
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/buildings/{building_id}/available-certifications",
    response_model=AvailableCertifications,
)
async def available_certifications_endpoint(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List certifications a building could pursue with eligibility status."""
    result = await get_available_certifications(building_id, db)
    # Check if building was not found
    if result.certifications and all(
        c.eligibility == "ineligible" and c.blockers == ["Building not found"] for c in result.certifications
    ):
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/buildings/{building_id}/certification-roadmap",
    response_model=CertificationRoadmap,
)
async def certification_roadmap_endpoint(
    building_id: uuid.UUID,
    certification_type: str = Query(..., pattern="^(minergie|cecb|snbs|geak)$"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate ordered steps to achieve a certification."""
    result = await generate_certification_roadmap(building_id, certification_type, db)
    if result.steps and result.steps[0].description.startswith("Building not found"):
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/organizations/{org_id}/certification-status",
    response_model=PortfolioCertificationStatus,
)
async def portfolio_certification_status_endpoint(
    org_id: uuid.UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get certification status summary across all organization buildings."""
    return await get_portfolio_certification_status(org_id, db)
