"""API routes for generic background job tracking."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.background_job import BackgroundJobList, BackgroundJobRead
from app.services import background_job_service

router = APIRouter()


@router.get("/jobs", response_model=BackgroundJobList)
async def list_jobs(
    job_type: str | None = Query(None),
    status: str | None = Query(None),
    building_id: UUID | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permission("exports", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List background jobs with optional filters."""
    jobs = await background_job_service.list_jobs(
        db,
        job_type=job_type,
        building_id=building_id,
        status=status,
        limit=limit,
    )
    return BackgroundJobList(
        items=[BackgroundJobRead.model_validate(j) for j in jobs],
        total=len(jobs),
    )


@router.get("/jobs/{job_id}", response_model=BackgroundJobRead)
async def get_job(
    job_id: UUID,
    current_user: User = Depends(require_permission("exports", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single background job by ID."""
    job = await background_job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return BackgroundJobRead.model_validate(job)


@router.post("/jobs/{job_id}/cancel", response_model=BackgroundJobRead)
async def cancel_job(
    job_id: UUID,
    current_user: User = Depends(require_permission("exports", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a queued background job."""
    try:
        job = await background_job_service.cancel_job(db, job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return BackgroundJobRead.model_validate(job)
