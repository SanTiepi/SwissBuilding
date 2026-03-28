"""Dossier Workflow API routes -- Safe-to-Start dossier lifecycle."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.services.dossier_workflow_service import DossierWorkflowService

router = APIRouter()

_service = DossierWorkflowService()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class GeneratePackRequest(BaseModel):
    org_id: UUID | None = None


class SubmitRequest(BaseModel):
    pack_id: UUID
    submission_reference: str | None = None


class ComplementRequest(BaseModel):
    pack_id: UUID
    complement_details: str


class ResubmitRequest(BaseModel):
    org_id: UUID | None = None


class AcknowledgeRequest(BaseModel):
    pack_id: UUID


class FixBlockerRequest(BaseModel):
    blocker_type: str
    resolution_data: dict = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_building_or_404(db: AsyncSession, building_id: UUID, user: User | None = None):
    """Fetch building by ID.  If *user* is provided (non-admin), also verify
    that the building belongs to the user's organization."""
    from app.services.building_service import get_building

    building = await get_building(db, building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    if user and getattr(user, "role", None) != "admin":
        user_org = getattr(user, "organization_id", None)
        if user_org and building.organization_id != user_org:
            raise HTTPException(status_code=404, detail="Building not found")
    return building


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/buildings/{building_id}/dossier/{work_type}/status")
async def get_dossier_status(
    building_id: UUID,
    work_type: str,
    current_user: User = Depends(require_permission("readiness", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the current dossier lifecycle status for a building + work type."""
    await _get_building_or_404(db, building_id, current_user)
    try:
        return await _service.get_dossier_status(db, building_id, work_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/buildings/{building_id}/dossier/{work_type}/fix-blocker")
async def fix_blocker(
    building_id: UUID,
    work_type: str,
    body: FixBlockerRequest,
    current_user: User = Depends(require_permission("readiness", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a specific blocker and re-evaluate readiness."""
    await _get_building_or_404(db, building_id, current_user)
    try:
        return await _service.fix_blocker(db, building_id, body.blocker_type, body.resolution_data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/buildings/{building_id}/dossier/{work_type}/generate-pack")
async def generate_dossier_pack(
    building_id: UUID,
    work_type: str,
    body: GeneratePackRequest | None = None,
    current_user: User = Depends(require_permission("readiness", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Generate the authority-ready pack for this dossier."""
    await _get_building_or_404(db, building_id, current_user)
    org_id = body.org_id if body else None
    try:
        return await _service.generate_dossier_pack(db, building_id, work_type, current_user.id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/buildings/{building_id}/dossier/{work_type}/submit")
async def submit_to_authority(
    building_id: UUID,
    work_type: str,
    body: SubmitRequest,
    current_user: User = Depends(require_permission("readiness", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Mark the pack as submitted to the authority."""
    await _get_building_or_404(db, building_id, current_user)
    try:
        return await _service.submit_to_authority(
            db,
            building_id,
            body.pack_id,
            current_user.id,
            org_id=current_user.organization_id,
            submission_reference=body.submission_reference,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/buildings/{building_id}/dossier/{work_type}/complement")
async def handle_complement(
    building_id: UUID,
    work_type: str,
    body: ComplementRequest,
    current_user: User = Depends(require_permission("readiness", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Handle authority complement request."""
    await _get_building_or_404(db, building_id, current_user)
    try:
        return await _service.handle_complement_request(
            db,
            building_id,
            body.pack_id,
            body.complement_details,
            current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/buildings/{building_id}/dossier/{work_type}/resubmit")
async def resubmit_pack(
    building_id: UUID,
    work_type: str,
    body: ResubmitRequest | None = None,
    current_user: User = Depends(require_permission("readiness", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate and resubmit after fixing complement issues."""
    await _get_building_or_404(db, building_id, current_user)
    org_id = body.org_id if body else None
    try:
        return await _service.resubmit_pack(db, building_id, work_type, current_user.id, org_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post("/buildings/{building_id}/dossier/{work_type}/acknowledge")
async def acknowledge_receipt(
    building_id: UUID,
    work_type: str,
    body: AcknowledgeRequest,
    current_user: User = Depends(require_permission("readiness", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Record that the authority acknowledged the submission."""
    await _get_building_or_404(db, building_id, current_user)
    try:
        return await _service.acknowledge_receipt(
            db,
            building_id,
            body.pack_id,
            current_user.id,
            org_id=current_user.organization_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
