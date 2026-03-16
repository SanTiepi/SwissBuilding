from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.sample import SampleCreate, SampleRead, SampleUpdate
from app.services.audit_service import log_action
from app.services.compliance_engine import auto_classify_sample

router = APIRouter()


@router.get("/diagnostics/{diagnostic_id}/samples", response_model=list[SampleRead])
async def list_samples_endpoint(
    diagnostic_id: UUID,
    current_user: User = Depends(require_permission("samples", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List all samples for a diagnostic."""
    from app.services.diagnostic_service import get_diagnostic

    diagnostic = await get_diagnostic(db, diagnostic_id)
    if not diagnostic:
        raise HTTPException(status_code=404, detail="Diagnostic not found")

    from sqlalchemy import select

    from app.models.sample import Sample

    result = await db.execute(select(Sample).where(Sample.diagnostic_id == diagnostic_id).order_by(Sample.created_at))
    samples = result.scalars().all()
    return samples


@router.post("/diagnostics/{diagnostic_id}/samples", response_model=SampleRead, status_code=201)
async def create_sample_endpoint(
    diagnostic_id: UUID,
    data: SampleCreate,
    current_user: User = Depends(require_permission("samples", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new sample for a diagnostic, with automatic compliance classification."""
    from app.models.sample import Sample
    from app.services.diagnostic_service import get_diagnostic

    diagnostic = await get_diagnostic(db, diagnostic_id)
    if not diagnostic:
        raise HTTPException(status_code=404, detail="Diagnostic not found")

    sample = Sample(diagnostic_id=diagnostic_id, **data.model_dump())

    # Auto-classify the sample based on Swiss OLED/OPAir/OMoD regulations
    sample_dict = data.model_dump()
    classified = auto_classify_sample(sample_dict)
    for field, value in classified.items():
        setattr(sample, field, value)

    db.add(sample)
    await db.commit()
    await db.refresh(sample)
    await log_action(db, current_user.id, "create", "sample", sample.id)
    from app.services.action_service import sync_building_system_actions

    await sync_building_system_actions(db, diagnostic.building_id)
    return sample


@router.put("/samples/{sample_id}", response_model=SampleRead)
async def update_sample_endpoint(
    sample_id: UUID,
    data: SampleUpdate,
    current_user: User = Depends(require_permission("samples", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing sample."""
    from sqlalchemy import select

    from app.models.sample import Sample

    result = await db.execute(select(Sample).where(Sample.id == sample_id))
    sample = result.scalar_one_or_none()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sample, field, value)

    # Re-classify after update
    sample_dict = {c.key: getattr(sample, c.key) for c in sample.__table__.columns}
    classified = auto_classify_sample(sample_dict)
    for field, value in classified.items():
        setattr(sample, field, value)

    await db.commit()
    await db.refresh(sample)
    await log_action(db, current_user.id, "update", "sample", sample_id)
    return sample


@router.delete("/samples/{sample_id}", status_code=204)
async def delete_sample_endpoint(
    sample_id: UUID,
    current_user: User = Depends(require_permission("samples", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a sample."""
    from sqlalchemy import select

    from app.models.sample import Sample

    result = await db.execute(select(Sample).where(Sample.id == sample_id))
    sample = result.scalar_one_or_none()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    await db.delete(sample)
    await db.commit()
    await log_action(db, current_user.id, "delete", "sample", sample_id)
