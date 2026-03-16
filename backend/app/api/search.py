"""
SwissBuildingOS - Search API

Cross-entity full-text search via Meilisearch.
"""

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.models.user import User
from app.services import search_service

router = APIRouter()


@router.get("")
async def search_endpoint(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    type: str | None = Query(None, description="Filter by index: buildings, diagnostics, documents"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Cross-entity full-text search.

    Returns combined results from buildings, diagnostics, and documents indexes.
    """
    results = search_service.search_all(query=q, index_filter=type, limit=limit)
    return results
