"""BatiConnect Certificate API routes.

Signed, verifiable building state certificates for insurance, banks,
authorities, and buyers. The verify endpoint is PUBLIC (no auth required).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.certificate import (
    CertificateGenerateRequest,
    CertificateListRead,
    CertificateRead,
    CertificateVerifyRead,
)
from app.services.certificate_service import (
    generate_certificate,
    list_certificates,
    verify_certificate,
)

router = APIRouter()

VALID_TYPES = {"standard", "authority", "transaction"}


@router.post(
    "/buildings/{building_id}/certificates",
    response_model=CertificateRead,
    status_code=201,
)
async def create_certificate(
    building_id: UUID,
    body: CertificateGenerateRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new BatiConnect Certificate for a building."""
    cert_type = body.certificate_type if body else "standard"
    if cert_type not in VALID_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid certificate type. Must be one of: {', '.join(sorted(VALID_TYPES))}",
        )

    result = await generate_certificate(db, building_id, current_user.id, cert_type)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/certificates/{certificate_id}",
    response_model=CertificateRead,
)
async def get_certificate(
    certificate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a certificate by its ID."""
    from sqlalchemy import select

    from app.models.building_certificate import BuildingCertificate

    result = await db.execute(select(BuildingCertificate).where(BuildingCertificate.id == certificate_id))
    cert = result.scalar_one_or_none()
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return cert.content_json


@router.get(
    "/certificates/{certificate_id}/verify",
    response_model=CertificateVerifyRead,
)
async def verify_certificate_endpoint(
    certificate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """PUBLIC endpoint — verify a certificate's validity and integrity.

    No authentication required. This is the whole point of certificates:
    anyone with the certificate_id can verify it.
    """
    return await verify_certificate(db, certificate_id)


@router.get(
    "/buildings/{building_id}/certificates",
    response_model=CertificateListRead,
)
async def list_building_certificates(
    building_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List certificates for a specific building."""
    items, total = await list_certificates(db, building_id=building_id, page=page, size=size)
    return CertificateListRead(items=items, total=total, page=page, size=size)


@router.get(
    "/portfolio/certificates",
    response_model=CertificateListRead,
)
async def list_portfolio_certificates(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all certificates for the current user's organization."""
    items, total = await list_certificates(db, page=page, size=size)
    return CertificateListRead(items=items, total=total, page=page, size=size)
