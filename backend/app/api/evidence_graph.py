"""Evidence graph traversal API routes."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.evidence_graph import (
    EntityNeighbors,
    EvidenceGraph,
    EvidenceGraphStats,
    EvidenceNode,
    EvidencePath,
)
from app.services.evidence_graph_service import (
    build_evidence_graph,
    find_evidence_path,
    get_connected_components,
    get_entity_neighbors,
    get_evidence_chain_for_entity,
    get_evidence_graph_stats,
)

router = APIRouter()


@router.get(
    "/buildings/{building_id}/evidence-graph",
    response_model=EvidenceGraph,
)
async def get_building_evidence_graph(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("evidence", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Build and return the full evidence graph for a building."""
    return await build_evidence_graph(db, building_id)


@router.get(
    "/evidence-graph/neighbors/{entity_type}/{entity_id}",
    response_model=EntityNeighbors,
)
async def get_neighbors(
    entity_type: str,
    entity_id: uuid.UUID,
    current_user: User = Depends(require_permission("evidence", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Find all directly connected entities for a given entity."""
    return await get_entity_neighbors(db, entity_type, entity_id)


@router.get(
    "/evidence-graph/path",
    response_model=EvidencePath | None,
)
async def find_path(
    source_type: str = Query(...),
    source_id: uuid.UUID = Query(...),
    target_type: str = Query(...),
    target_id: uuid.UUID = Query(...),
    max_hops: int = Query(default=5, ge=1, le=10),
    current_user: User = Depends(require_permission("evidence", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Find the shortest path between two entities through evidence links."""
    return await find_evidence_path(db, source_type, source_id, target_type, target_id, max_hops)


@router.get(
    "/buildings/{building_id}/evidence-graph/stats",
    response_model=EvidenceGraphStats,
)
async def get_graph_stats(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("evidence", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Compute evidence graph statistics for a building."""
    return await get_evidence_graph_stats(db, building_id)


@router.get(
    "/buildings/{building_id}/evidence-graph/components",
    response_model=list[list[EvidenceNode]],
)
async def get_components(
    building_id: uuid.UUID,
    current_user: User = Depends(require_permission("evidence", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Find disconnected subgraphs within the building's evidence network."""
    return await get_connected_components(db, building_id)


@router.get(
    "/evidence-graph/chain/{entity_type}/{entity_id}",
    response_model=EvidenceGraph,
)
async def get_chain(
    entity_type: str,
    entity_id: uuid.UUID,
    depth: int = Query(default=3, ge=1, le=10),
    current_user: User = Depends(require_permission("evidence", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Build a subgraph centered on a specific entity, expanding outward to the given depth."""
    return await get_evidence_chain_for_entity(db, entity_type, entity_id, depth)
