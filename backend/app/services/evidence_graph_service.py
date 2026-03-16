"""Evidence link graph traversal service.

Builds navigable graphs of evidence relationships for a building,
showing how diagnostics, samples, documents, zones, interventions,
and other entities are connected through evidence links.
"""

import uuid
from collections import defaultdict, deque

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.evidence_graph import (
    EntityNeighbors,
    EvidenceEdge,
    EvidenceGraph,
    EvidenceGraphStats,
    EvidenceNode,
    EvidencePath,
    EvidencePathStep,
)

# Mapping of entity_type strings to (model_class, building_id_column, optional_label_column)
_ENTITY_MODELS: dict[str, tuple] = {
    "diagnostic": (Diagnostic, Diagnostic.building_id, "diagnostic_type"),
    "sample": (Sample, None, "sample_number"),  # via diagnostic
    "document": (Document, Document.building_id, "file_name"),
    "zone": (Zone, Zone.building_id, "name"),
    "intervention": (Intervention, Intervention.building_id, "title"),
    "risk_score": (BuildingRiskScore, BuildingRiskScore.building_id, None),
    "action_item": (ActionItem, ActionItem.building_id, "title"),
}


async def _collect_building_entity_ids(db: AsyncSession, building_id: uuid.UUID) -> dict[str, set[uuid.UUID]]:
    """Collect all entity IDs that belong to a building, grouped by type."""
    entity_ids: dict[str, set[uuid.UUID]] = {}

    # Direct building_id FK models
    for entity_type, (model, building_col, _label_col) in _ENTITY_MODELS.items():
        if entity_type == "sample":
            continue  # handled below via diagnostic
        if building_col is None:
            continue
        result = await db.execute(select(model.id).where(building_col == building_id))
        ids = {row[0] for row in result.all()}
        if ids:
            entity_ids[entity_type] = ids

    # Samples via diagnostics
    diag_ids = entity_ids.get("diagnostic", set())
    if diag_ids:
        result = await db.execute(select(Sample.id).where(Sample.diagnostic_id.in_(diag_ids)))
        sample_ids = {row[0] for row in result.all()}
        if sample_ids:
            entity_ids["sample"] = sample_ids

    # Include the building itself
    entity_ids["building"] = {building_id}

    return entity_ids


async def _get_all_building_links(
    db: AsyncSession, entity_ids_by_type: dict[str, set[uuid.UUID]]
) -> list[EvidenceLink]:
    """Get all evidence links involving any of the collected entity IDs."""
    all_ids: set[uuid.UUID] = set()
    for ids in entity_ids_by_type.values():
        all_ids.update(ids)

    if not all_ids:
        return []

    query = select(EvidenceLink).where(
        or_(
            EvidenceLink.source_id.in_(all_ids),
            EvidenceLink.target_id.in_(all_ids),
        )
    )
    result = await db.execute(query)
    return list(result.scalars().all())


def _link_to_edge(link: EvidenceLink) -> EvidenceEdge:
    return EvidenceEdge(
        source_type=link.source_type,
        source_id=link.source_id,
        target_type=link.target_type,
        target_id=link.target_id,
        relationship=link.relationship,
        confidence=link.confidence,
        legal_reference=link.legal_reference,
        explanation=link.explanation,
        created_at=link.created_at,
    )


def _compute_connected_components(
    nodes: set[tuple[str, uuid.UUID]],
    edges: list[EvidenceEdge],
) -> int:
    """Union-find to count connected components."""
    if not nodes:
        return 0

    parent: dict[tuple[str, uuid.UUID], tuple[str, uuid.UUID]] = {n: n for n in nodes}
    rank: dict[tuple[str, uuid.UUID], int] = {n: 0 for n in nodes}

    def find(x: tuple[str, uuid.UUID]) -> tuple[str, uuid.UUID]:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: tuple[str, uuid.UUID], b: tuple[str, uuid.UUID]) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1

    for edge in edges:
        src = (edge.source_type, edge.source_id)
        tgt = (edge.target_type, edge.target_id)
        if src in parent and tgt in parent:
            union(src, tgt)

    roots = {find(n) for n in nodes}
    return len(roots)


def _compute_component_lists(
    nodes: set[tuple[str, uuid.UUID]],
    edges: list[EvidenceEdge],
) -> list[list[EvidenceNode]]:
    """Union-find returning actual component lists."""
    if not nodes:
        return []

    parent: dict[tuple[str, uuid.UUID], tuple[str, uuid.UUID]] = {n: n for n in nodes}
    rank: dict[tuple[str, uuid.UUID], int] = {n: 0 for n in nodes}

    def find(x: tuple[str, uuid.UUID]) -> tuple[str, uuid.UUID]:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: tuple[str, uuid.UUID], b: tuple[str, uuid.UUID]) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1

    for edge in edges:
        src = (edge.source_type, edge.source_id)
        tgt = (edge.target_type, edge.target_id)
        if src in parent and tgt in parent:
            union(src, tgt)

    components: dict[tuple[str, uuid.UUID], list[EvidenceNode]] = defaultdict(list)
    for node in nodes:
        root = find(node)
        components[root].append(EvidenceNode(entity_type=node[0], entity_id=node[1]))

    return list(components.values())


async def build_evidence_graph(db: AsyncSession, building_id: uuid.UUID) -> EvidenceGraph:
    """Build the full evidence graph for a building."""
    entity_ids_by_type = await _collect_building_entity_ids(db, building_id)
    links = await _get_all_building_links(db, entity_ids_by_type)
    edges = [_link_to_edge(link) for link in links]

    # Collect all nodes from entity_ids + any referenced in edges
    node_set: set[tuple[str, uuid.UUID]] = set()
    for entity_type, ids in entity_ids_by_type.items():
        for eid in ids:
            node_set.add((entity_type, eid))
    for edge in edges:
        node_set.add((edge.source_type, edge.source_id))
        node_set.add((edge.target_type, edge.target_id))

    nodes = [EvidenceNode(entity_type=t, entity_id=i) for t, i in node_set]
    cc = _compute_connected_components(node_set, edges)

    return EvidenceGraph(
        building_id=building_id,
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
        connected_components=cc,
    )


async def get_entity_neighbors(db: AsyncSession, entity_type: str, entity_id: uuid.UUID) -> EntityNeighbors:
    """Find all directly connected entities (incoming and outgoing links)."""
    outgoing_q = select(EvidenceLink).where(
        EvidenceLink.source_type == entity_type,
        EvidenceLink.source_id == entity_id,
    )
    incoming_q = select(EvidenceLink).where(
        EvidenceLink.target_type == entity_type,
        EvidenceLink.target_id == entity_id,
    )

    out_result = await db.execute(outgoing_q)
    in_result = await db.execute(incoming_q)

    outgoing = [_link_to_edge(link) for link in out_result.scalars().all()]
    incoming = [_link_to_edge(link) for link in in_result.scalars().all()]

    return EntityNeighbors(
        entity_type=entity_type,
        entity_id=entity_id,
        incoming=incoming,
        outgoing=outgoing,
        total_connections=len(incoming) + len(outgoing),
    )


async def find_evidence_path(
    db: AsyncSession,
    source_type: str,
    source_id: uuid.UUID,
    target_type: str,
    target_id: uuid.UUID,
    max_hops: int = 5,
) -> EvidencePath | None:
    """BFS traversal to find shortest path between two entities through evidence links."""
    start = (source_type, source_id)
    goal = (target_type, target_id)

    if start == goal:
        return EvidencePath(
            steps=[EvidencePathStep(entity_type=source_type, entity_id=source_id)],
            total_hops=0,
            min_confidence=None,
        )

    # Load all evidence links into memory for BFS
    all_links = await db.execute(select(EvidenceLink))
    links = list(all_links.scalars().all())

    # Build adjacency
    adj: dict[tuple[str, uuid.UUID], list[tuple[tuple[str, uuid.UUID], str, float | None]]] = defaultdict(list)
    for link in links:
        src = (link.source_type, link.source_id)
        tgt = (link.target_type, link.target_id)
        adj[src].append((tgt, link.relationship, link.confidence))
        adj[tgt].append((src, link.relationship, link.confidence))

    # BFS
    visited: set[tuple[str, uuid.UUID]] = {start}
    queue: deque[tuple[tuple[str, uuid.UUID], list[tuple[tuple[str, uuid.UUID], str | None, float | None]]]] = deque()
    queue.append((start, [(start, None, None)]))

    while queue:
        current, path = queue.popleft()
        if len(path) - 1 >= max_hops:
            continue

        for neighbor, relationship, confidence in adj.get(current, []):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            new_path = [*path, (neighbor, relationship, confidence)]

            if neighbor == goal:
                steps = []
                for node, rel, _conf in new_path:
                    steps.append(
                        EvidencePathStep(
                            entity_type=node[0],
                            entity_id=node[1],
                            relationship=rel,
                        )
                    )
                confidences = [c for _, _, c in new_path if c is not None]
                return EvidencePath(
                    steps=steps,
                    total_hops=len(steps) - 1,
                    min_confidence=min(confidences) if confidences else None,
                )

            queue.append((neighbor, new_path))

    return None


async def get_evidence_graph_stats(db: AsyncSession, building_id: uuid.UUID) -> EvidenceGraphStats:
    """Compute graph statistics for a building's evidence network."""
    entity_ids_by_type = await _collect_building_entity_ids(db, building_id)
    links = await _get_all_building_links(db, entity_ids_by_type)
    edges = [_link_to_edge(link) for link in links]

    by_relationship: dict[str, int] = defaultdict(int)
    by_entity_type: dict[str, int] = defaultdict(int)
    confidences: list[float] = []

    connected_entity_keys: set[tuple[str, uuid.UUID]] = set()

    for edge in edges:
        by_relationship[edge.relationship] += 1
        connected_entity_keys.add((edge.source_type, edge.source_id))
        connected_entity_keys.add((edge.target_type, edge.target_id))
        if edge.confidence is not None:
            confidences.append(edge.confidence)

    # Count entities by type
    for entity_type, ids in entity_ids_by_type.items():
        by_entity_type[entity_type] = len(ids)

    avg_confidence = sum(confidences) / len(confidences) if confidences else None

    # Weakest links (lowest confidence, sorted ascending)
    links_with_confidence = [e for e in edges if e.confidence is not None]
    links_with_confidence.sort(key=lambda e: e.confidence)  # type: ignore[arg-type]
    weakest_links = links_with_confidence[:5]

    # Orphan entities: those in entity_ids_by_type but not connected by any link
    all_entity_keys: set[tuple[str, uuid.UUID]] = set()
    for entity_type, ids in entity_ids_by_type.items():
        for eid in ids:
            all_entity_keys.add((entity_type, eid))

    orphan_keys = all_entity_keys - connected_entity_keys
    orphan_entities = [EvidenceNode(entity_type=t, entity_id=i) for t, i in orphan_keys]

    return EvidenceGraphStats(
        building_id=building_id,
        total_links=len(edges),
        by_relationship=dict(by_relationship),
        by_entity_type=dict(by_entity_type),
        avg_confidence=avg_confidence,
        weakest_links=weakest_links,
        orphan_entities=orphan_entities,
    )


async def get_connected_components(db: AsyncSession, building_id: uuid.UUID) -> list[list[EvidenceNode]]:
    """Find disconnected subgraphs within the building's evidence network."""
    entity_ids_by_type = await _collect_building_entity_ids(db, building_id)
    links = await _get_all_building_links(db, entity_ids_by_type)
    edges = [_link_to_edge(link) for link in links]

    node_set: set[tuple[str, uuid.UUID]] = set()
    for entity_type, ids in entity_ids_by_type.items():
        for eid in ids:
            node_set.add((entity_type, eid))
    for edge in edges:
        node_set.add((edge.source_type, edge.source_id))
        node_set.add((edge.target_type, edge.target_id))

    return _compute_component_lists(node_set, edges)


async def get_evidence_chain_for_entity(
    db: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    depth: int = 3,
) -> EvidenceGraph:
    """Build a subgraph centered on a specific entity, expanding outward to the given depth."""
    visited: set[tuple[str, uuid.UUID]] = set()
    frontier: set[tuple[str, uuid.UUID]] = {(entity_type, entity_id)}
    all_edges: list[EvidenceEdge] = []
    seen_edge_keys: set[tuple[str, uuid.UUID, str, uuid.UUID]] = set()

    for _level in range(depth):
        if not frontier:
            break

        next_frontier: set[tuple[str, uuid.UUID]] = set()
        visited.update(frontier)

        for etype, eid in frontier:
            # Outgoing
            out_q = select(EvidenceLink).where(
                EvidenceLink.source_type == etype,
                EvidenceLink.source_id == eid,
            )
            out_result = await db.execute(out_q)
            for link in out_result.scalars().all():
                edge_key = (link.source_type, link.source_id, link.target_type, link.target_id)
                if edge_key not in seen_edge_keys:
                    seen_edge_keys.add(edge_key)
                    all_edges.append(_link_to_edge(link))
                neighbor = (link.target_type, link.target_id)
                if neighbor not in visited:
                    next_frontier.add(neighbor)

            # Incoming
            in_q = select(EvidenceLink).where(
                EvidenceLink.target_type == etype,
                EvidenceLink.target_id == eid,
            )
            in_result = await db.execute(in_q)
            for link in in_result.scalars().all():
                edge_key = (link.source_type, link.source_id, link.target_type, link.target_id)
                if edge_key not in seen_edge_keys:
                    seen_edge_keys.add(edge_key)
                    all_edges.append(_link_to_edge(link))
                neighbor = (link.source_type, link.source_id)
                if neighbor not in visited:
                    next_frontier.add(neighbor)

        frontier = next_frontier

    # Include any remaining frontier nodes
    visited.update(frontier)

    nodes = [EvidenceNode(entity_type=t, entity_id=i) for t, i in visited]
    cc = _compute_connected_components(visited, all_edges)

    # Use a zero UUID as placeholder building_id for entity-centered graphs
    return EvidenceGraph(
        building_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        nodes=nodes,
        edges=all_edges,
        total_nodes=len(nodes),
        total_edges=len(all_edges),
        connected_components=cc,
    )
