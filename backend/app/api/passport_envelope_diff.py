"""Passport envelope diffing, machine-readable export, transfer manifest, and reimport validation."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services import passport_exchange_service as svc

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas (local, lightweight)
# ---------------------------------------------------------------------------


class ReimportValidationRequest(BaseModel):
    envelope_data: dict


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/passport-envelope/{envelope_id}/diff/{other_envelope_id}")
async def diff_envelopes_endpoint(
    envelope_id: UUID,
    other_envelope_id: UUID,
    current_user: User = Depends(require_permission("evidence_packs", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Compare two passport envelope versions and return a structured diff."""
    try:
        return await svc.diff_envelopes(db, envelope_id, other_envelope_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.get("/passport-envelope/{envelope_id}/export")
async def export_machine_readable_endpoint(
    envelope_id: UUID,
    format: str = Query(default="json", pattern="^(json|csv-summary)$"),
    current_user: User = Depends(require_permission("evidence_packs", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Export envelope in machine-readable format (json or csv-summary).

    For CSV format, the CSV content is returned inside a wrapper dict
    ``{"format": "csv-summary", "content": "<csv-string>"}``.
    """
    try:
        result = await svc.export_machine_readable(db, envelope_id, format=format)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None

    if isinstance(result, str):
        return {"format": "csv-summary", "content": result}
    return result


@router.get("/passport-envelope/{envelope_id}/transfer-manifest")
async def transfer_manifest_endpoint(
    envelope_id: UUID,
    current_user: User = Depends(require_permission("evidence_packs", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a transfer manifest for a passport envelope."""
    try:
        return await svc.generate_transfer_manifest(db, envelope_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None


@router.post("/passport-envelope/validate-reimport")
async def validate_reimport_endpoint(
    data: ReimportValidationRequest,
    current_user: User = Depends(require_permission("evidence_packs", "read")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate that envelope data is structurally valid for reimport."""
    return await svc.validate_reimport(db, data.envelope_data)
