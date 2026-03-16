"""Service for generic background job tracking."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.background_job import BackgroundJob


async def create_job(
    db: AsyncSession,
    job_type: str,
    building_id: UUID | None = None,
    org_id: UUID | None = None,
    user_id: UUID | None = None,
    params: dict[str, Any] | None = None,
) -> BackgroundJob:
    """Create a new background job in queued status."""
    job = BackgroundJob(
        job_type=job_type,
        status="queued",
        building_id=building_id,
        organization_id=org_id,
        created_by=user_id,
        params_json=params,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def start_job(db: AsyncSession, job_id: UUID) -> BackgroundJob:
    """Mark a job as running."""
    job = await _get_or_raise(db, job_id)
    job.status = "running"
    job.started_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(job)
    return job


async def complete_job(
    db: AsyncSession,
    job_id: UUID,
    result: dict[str, Any] | None = None,
) -> BackgroundJob:
    """Mark a job as completed with optional result."""
    job = await _get_or_raise(db, job_id)
    job.status = "completed"
    job.result_json = result
    job.completed_at = datetime.now(UTC)
    job.progress_pct = 100
    await db.commit()
    await db.refresh(job)
    return job


async def fail_job(
    db: AsyncSession,
    job_id: UUID,
    error_message: str,
) -> BackgroundJob:
    """Mark a job as failed with an error message."""
    job = await _get_or_raise(db, job_id)
    job.status = "failed"
    job.error_message = error_message
    job.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: UUID) -> BackgroundJob | None:
    """Get a single job by ID."""
    result = await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))
    return result.scalar_one_or_none()


async def list_jobs(
    db: AsyncSession,
    job_type: str | None = None,
    building_id: UUID | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[BackgroundJob]:
    """List jobs with optional filters."""
    query = select(BackgroundJob)
    if job_type:
        query = query.where(BackgroundJob.job_type == job_type)
    if building_id:
        query = query.where(BackgroundJob.building_id == building_id)
    if status:
        query = query.where(BackgroundJob.status == status)
    query = query.order_by(BackgroundJob.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def cancel_job(db: AsyncSession, job_id: UUID) -> BackgroundJob:
    """Cancel a queued job."""
    job = await _get_or_raise(db, job_id)
    if job.status != "queued":
        msg = "Only queued jobs can be cancelled"
        raise ValueError(msg)
    job.status = "cancelled"
    job.completed_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(job)
    return job


async def update_progress(
    db: AsyncSession,
    job_id: UUID,
    progress_pct: int,
) -> BackgroundJob:
    """Update job progress percentage (0-100)."""
    job = await _get_or_raise(db, job_id)
    job.progress_pct = min(max(progress_pct, 0), 100)
    await db.commit()
    await db.refresh(job)
    return job


async def _get_or_raise(db: AsyncSession, job_id: UUID) -> BackgroundJob:
    """Get a job by ID or raise ValueError."""
    job = await get_job(db, job_id)
    if not job:
        msg = f"Job {job_id} not found"
        raise ValueError(msg)
    return job
