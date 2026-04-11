"""Pack export API — PDF generation + shared artifact links."""

import os
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.shared_artifact import SharedArtifact
from app.models.user import User
from app.services.pdf_generator_service import PDFGeneratorService

router = APIRouter()
_pdf_svc = PDFGeneratorService()


# ---------------------------------------------------------------------------
# Schemas (local — not large enough for a separate file)
# ---------------------------------------------------------------------------


class ShareLinkResponse(BaseModel):
    share_url: str
    access_token: str
    expires_at: datetime
    artifact_id: str


class SharedArtifactView(BaseModel):
    title: str
    artifact_type: str
    artifact_data: dict
    redacted: bool
    created_at: datetime | None = None
    expires_at: datetime


class PDFResultResponse(BaseModel):
    filename: str
    size_bytes: int
    sha256: str
    generated_at: datetime


# ---------------------------------------------------------------------------
# PDF generation endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/packs/authority/pdf",
    response_class=FileResponse,
    status_code=200,
)
async def generate_authority_pdf(
    building_id: UUID,
    redact_financials: bool = False,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return authority pack as a PDF file download."""
    try:
        result = await _pdf_svc.generate_authority_pack_pdf(
            db,
            building_id,
            org_id=getattr(current_user, "organization_id", None),
            created_by_id=current_user.id,
            redact_financials=redact_financials,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    pdf_path = result["pdf_path"]
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return FileResponse(
        path=pdf_path,
        filename=result["filename"],
        media_type="application/pdf" if pdf_path.endswith(".pdf") else "text/html",
    )


@router.post(
    "/buildings/{building_id}/packs/transaction/pdf",
    response_class=FileResponse,
    status_code=200,
)
async def generate_transaction_pdf(
    building_id: UUID,
    redact_financials: bool = True,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return transaction pack as a PDF file download."""
    try:
        result = await _pdf_svc.generate_transaction_pack_pdf(
            db,
            building_id,
            org_id=getattr(current_user, "organization_id", None),
            created_by_id=current_user.id,
            redact_financials=redact_financials,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    pdf_path = result["pdf_path"]
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return FileResponse(
        path=pdf_path,
        filename=result["filename"],
        media_type="application/pdf" if pdf_path.endswith(".pdf") else "text/html",
    )


# ---------------------------------------------------------------------------
# Shared artifact endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/buildings/{building_id}/packs/{pack_type}/share",
    response_model=ShareLinkResponse,
    status_code=201,
)
async def create_share_link(
    building_id: UUID,
    pack_type: str,
    expires_days: int = 7,
    redact_financials: bool = True,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Create a time-limited read-only share link for a pack."""
    if pack_type not in ("authority", "transaction"):
        raise HTTPException(status_code=400, detail="pack_type must be 'authority' or 'transaction'")

    if expires_days < 1 or expires_days > 90:
        raise HTTPException(status_code=400, detail="expires_days must be between 1 and 90")

    # Generate the pack data
    try:
        if pack_type == "authority":
            from app.schemas.authority_pack import AuthorityPackConfig
            from app.services.authority_pack_service import generate_authority_pack

            config = AuthorityPackConfig(
                building_id=building_id,
                redact_financials=redact_financials,
            )
            result = await generate_authority_pack(db, building_id, config, current_user.id)
            artifact_data = result.model_dump(mode="json")
            title = f"Pack Autorite — {artifact_data.get('canton', 'CH')}"
        else:
            from app.services.pack_builder_service import generate_pack

            result = await generate_pack(
                db,
                building_id,
                "transaction",
                org_id=getattr(current_user, "organization_id", None),
                created_by_id=current_user.id,
                redact_financials=redact_financials,
            )
            artifact_data = result.model_dump(mode="json")
            title = "Pack Transaction"
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    # Create shared artifact
    access_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(days=expires_days)

    artifact = SharedArtifact(
        building_id=building_id,
        organization_id=getattr(current_user, "organization_id", None),
        created_by_id=current_user.id,
        artifact_type=f"{pack_type}_pack",
        artifact_data=artifact_data,
        access_token=access_token,
        expires_at=expires_at,
        title=title,
        redacted=redact_financials,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)

    return ShareLinkResponse(
        share_url=f"/api/v1/shared-artifacts/{access_token}",
        access_token=access_token,
        expires_at=expires_at,
        artifact_id=str(artifact.id),
    )


@router.get(
    "/shared-artifacts/{access_token}",
    response_model=SharedArtifactView,
)
async def view_shared_artifact(
    access_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — no auth required. View a shared pack artifact."""
    result = await db.execute(select(SharedArtifact).where(SharedArtifact.access_token == access_token))
    artifact = result.scalar_one_or_none()

    if not artifact:
        raise HTTPException(status_code=404, detail="Shared artifact not found")

    # Check expiry
    now = datetime.now(UTC)
    expires = artifact.expires_at if artifact.expires_at.tzinfo else artifact.expires_at.replace(tzinfo=UTC)
    if expires < now:
        raise HTTPException(status_code=410, detail="Share link has expired")

    # Increment view count
    artifact.view_count = (artifact.view_count or 0) + 1
    await db.commit()

    return SharedArtifactView(
        title=artifact.title,
        artifact_type=artifact.artifact_type,
        artifact_data=artifact.artifact_data,
        redacted=artifact.redacted or False,
        created_at=artifact.created_at,
        expires_at=artifact.expires_at,
    )
