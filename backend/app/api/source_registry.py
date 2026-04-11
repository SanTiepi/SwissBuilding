"""Source registry API — source catalogue and health monitoring."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.source_registry import (
    SourceHealthDashboard,
    SourceRegistryRead,
)
from app.services.source_registry_service import SourceRegistryService

router = APIRouter()


@router.get("/sources", response_model=list[SourceRegistryRead], tags=["Source Registry"])
async def list_sources(
    family: str | None = Query(None, description="Filter by family (identity, spatial, constraint, etc.)"),
    circle: int | None = Query(None, description="Filter by circle (1, 2, 3)"),
    status: str | None = Query(None, description="Filter by status (active, degraded, unavailable, etc.)"),
    priority: str | None = Query(None, description="Filter by priority (now, next, later, partner_gated)"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List all registered data sources with optional filters."""
    sources = await SourceRegistryService.get_all_sources(
        db, family=family, circle=circle, status=status, priority=priority
    )
    return sources


@router.get("/sources/health-dashboard", response_model=SourceHealthDashboard, tags=["Source Registry"])
async def get_health_dashboard(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get health overview across all active sources."""
    return await SourceRegistryService.get_health_dashboard(db)


@router.get("/sources/{source_name}", response_model=SourceRegistryRead, tags=["Source Registry"])
async def get_source(
    source_name: str,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific source by name."""
    source = await SourceRegistryService.get_source(db, source_name)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Source '{source_name}' not found")
    return source


@router.get("/sources/{source_name}/health", tags=["Source Registry"])
async def get_source_health(
    source_name: str,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get current health status and recent events for a source."""
    result = await SourceRegistryService.get_source_health(db, source_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=f"Source '{source_name}' not found")
    return result
