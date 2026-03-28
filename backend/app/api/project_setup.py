"""API routes for project setup wizard (Lancer un projet de travaux)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.intervention import InterventionRead
from app.schemas.project_setup import ProjectCreateRequest, ProjectDraftRequest

router = APIRouter()


@router.post("/buildings/{building_id}/projects/generate")
async def generate_project_draft_endpoint(
    building_id: UUID,
    data: ProjectDraftRequest,
    current_user: User = Depends(require_permission("interventions", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a pre-filled project draft from building dossier data."""
    from app.services.project_setup_service import generate_project_draft

    try:
        draft = await generate_project_draft(
            db,
            building_id,
            data.intervention_type,
            current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return draft


@router.post(
    "/buildings/{building_id}/projects",
    response_model=InterventionRead,
    status_code=201,
)
async def create_project_endpoint(
    building_id: UUID,
    data: ProjectCreateRequest,
    current_user: User = Depends(require_permission("interventions", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create an intervention from the project wizard data."""
    from app.services.project_setup_service import create_project_from_wizard

    try:
        intervention = await create_project_from_wizard(
            db,
            building_id,
            data.model_dump(),
            current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return intervention
