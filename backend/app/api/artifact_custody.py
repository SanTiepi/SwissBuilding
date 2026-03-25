"""Artifact Versioning + Chain-of-Custody — API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.artifact_custody import (
    ArchivePostureRead,
    ArchiveRequest,
    ArtifactVersionCreate,
    ArtifactVersionRead,
    CustodyChainRead,
    CustodyEventCreate,
    CustodyEventRead,
)
from app.services.artifact_custody_service import (
    archive_version,
    create_version,
    get_archive_posture,
    get_current_version,
    get_custody_chain,
    get_version,
    get_version_events,
    record_custody_event,
    withdraw_version,
)

router = APIRouter()


@router.post(
    "/artifacts/versions",
    response_model=ArtifactVersionRead,
    status_code=201,
    tags=["Artifact Custody"],
)
async def create_artifact_version(
    payload: ArtifactVersionCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new artifact version (auto-supersedes prior current versions)."""
    version = await create_version(
        db,
        artifact_type=payload.artifact_type,
        artifact_id=payload.artifact_id,
        content_hash=payload.content_hash,
        user_id=current_user.id,
    )
    # Record creation event
    await record_custody_event(
        db,
        version.id,
        {
            "event_type": "created",
            "actor_type": "user",
            "actor_id": current_user.id,
            "actor_name": current_user.full_name if hasattr(current_user, "full_name") else None,
        },
    )
    await db.commit()
    return version


@router.get(
    "/artifacts/{artifact_type}/{artifact_id}/chain",
    response_model=CustodyChainRead,
    tags=["Artifact Custody"],
)
async def get_artifact_chain(
    artifact_type: str,
    artifact_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get full custody chain for an artifact."""
    return await get_custody_chain(db, artifact_type, artifact_id)


@router.get(
    "/artifacts/{artifact_type}/{artifact_id}/current",
    response_model=ArtifactVersionRead | None,
    tags=["Artifact Custody"],
)
async def get_artifact_current_version(
    artifact_type: str,
    artifact_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get the current version of an artifact."""
    return await get_current_version(db, artifact_type, artifact_id)


@router.post(
    "/artifacts/versions/{version_id}/archive",
    response_model=ArtifactVersionRead,
    tags=["Artifact Custody"],
)
async def archive_artifact_version(
    version_id: UUID,
    payload: ArchiveRequest,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Archive a version with a reason."""
    version = await get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Artifact version not found")
    result = await archive_version(db, version_id, reason=payload.reason, user_id=current_user.id)
    await db.commit()
    return result


@router.post(
    "/artifacts/versions/{version_id}/withdraw",
    response_model=ArtifactVersionRead,
    tags=["Artifact Custody"],
)
async def withdraw_artifact_version(
    version_id: UUID,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw a version."""
    version = await get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Artifact version not found")
    result = await withdraw_version(db, version_id, user_id=current_user.id)
    await db.commit()
    return result


@router.post(
    "/artifacts/custody-events",
    response_model=CustodyEventRead,
    status_code=201,
    tags=["Artifact Custody"],
)
async def create_custody_event(
    payload: CustodyEventCreate,
    current_user: User = Depends(require_permission("buildings", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Record a custody event for a version."""
    version = await get_version(db, payload.artifact_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Artifact version not found")
    event_data = payload.model_dump(exclude_unset=True)
    event_data.pop("artifact_version_id", None)
    evt = await record_custody_event(db, payload.artifact_version_id, event_data)
    await db.commit()
    return evt


@router.get(
    "/buildings/{building_id}/archive-posture",
    response_model=ArchivePostureRead,
    tags=["Artifact Custody"],
)
async def get_building_archive_posture(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get archive posture summary for a building."""
    return await get_archive_posture(db, building_id)


@router.get(
    "/artifacts/versions/{version_id}/events",
    response_model=list[CustodyEventRead],
    tags=["Artifact Custody"],
)
async def get_artifact_version_events(
    version_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get custody events for a specific version."""
    version = await get_version(db, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Artifact version not found")
    return await get_version_events(db, version_id)
