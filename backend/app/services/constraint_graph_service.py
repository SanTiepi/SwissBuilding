"""
SwissBuildingOS - Constraint Graph Service

Models what blocks what in a building's journey toward readiness.
Builds a dependency graph from diagnostics, actions, interventions,
compliance checks, readiness gates, and evidence requirements,
then analyses critical paths and highest-leverage unlock points.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.readiness_assessment import ReadinessAssessment
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue
from app.schemas.constraint_graph import (
    ConstraintEdge,
    ConstraintGraph,
    ConstraintNode,
    CriticalPath,
    ReadinessBlocker,
    UnlockAnalysis,
)

# ---------------------------------------------------------------------------
# Priority mapping
# ---------------------------------------------------------------------------

_PRIORITY_MAP: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

_STATUS_COMPLETE = {"completed", "validated", "done", "resolved", "closed"}
_STATUS_IN_PROGRESS = {"in_progress"}


# ---------------------------------------------------------------------------
# Internal: fetch data for a building
# ---------------------------------------------------------------------------


async def _fetch_building_data(
    db: AsyncSession,
    building_id: UUID,
) -> tuple[
    Building | None,
    list[Diagnostic],
    list[ActionItem],
    list[Intervention],
    list[ReadinessAssessment],
    list[Sample],
    list[UnknownIssue],
]:
    """Fetch all entities needed to build the constraint graph."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None, [], [], [], [], [], []

    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = list(action_result.scalars().all())

    interv_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(interv_result.scalars().all())

    readiness_result = await db.execute(
        select(ReadinessAssessment).where(ReadinessAssessment.building_id == building_id)
    )
    readiness_assessments = list(readiness_result.scalars().all())

    # Samples via diagnostics
    samples: list[Sample] = []
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    unknown_result = await db.execute(
        select(UnknownIssue).where(
            UnknownIssue.building_id == building_id,
            UnknownIssue.status != "resolved",
        )
    )
    unknowns = list(unknown_result.scalars().all())

    return building, diagnostics, actions, interventions, readiness_assessments, samples, unknowns


# ---------------------------------------------------------------------------
# Internal: determine node status
# ---------------------------------------------------------------------------


def _node_status(raw_status: str | None) -> str:
    """Map a raw model status to a constraint-graph node status."""
    s = (raw_status or "").lower()
    if s in _STATUS_COMPLETE:
        return "completed"
    if s in _STATUS_IN_PROGRESS:
        return "in_progress"
    if s in ("not_applicable",):
        return "not_applicable"
    return "ready"


# ---------------------------------------------------------------------------
# Internal: build nodes and edges
# ---------------------------------------------------------------------------


def _build_nodes_and_edges(
    diagnostics: list[Diagnostic],
    actions: list[ActionItem],
    interventions: list[Intervention],
    readiness_assessments: list[ReadinessAssessment],
    samples: list[Sample],
    unknowns: list[UnknownIssue],
) -> tuple[list[ConstraintNode], list[ConstraintEdge]]:
    """Build all nodes and edges from the building's entities."""
    nodes: list[ConstraintNode] = []
    edges: list[ConstraintEdge] = []
    node_ids: set[str] = set()

    # --- Diagnostic nodes ---
    for d in diagnostics:
        nid = f"diag-{d.id}"
        node_ids.add(nid)
        nodes.append(
            ConstraintNode(
                node_id=nid,
                node_type="diagnostic",
                label=f"Diagnostic: {d.diagnostic_type} ({d.diagnostic_context or 'AvT'})",
                status=_node_status(d.status),
                priority=3 if d.status == "draft" else 2,
                metadata={"diagnostic_type": d.diagnostic_type, "context": d.diagnostic_context},
            )
        )

    # --- Action nodes ---
    for a in actions:
        nid = f"action-{a.id}"
        node_ids.add(nid)
        nodes.append(
            ConstraintNode(
                node_id=nid,
                node_type="action",
                label=f"Action: {a.title}",
                status=_node_status(a.status),
                priority=_PRIORITY_MAP.get(a.priority or "medium", 2),
                metadata={"action_type": a.action_type, "source_type": a.source_type},
            )
        )

    # --- Intervention nodes ---
    for i in interventions:
        nid = f"interv-{i.id}"
        node_ids.add(nid)
        nodes.append(
            ConstraintNode(
                node_id=nid,
                node_type="intervention",
                label=f"Intervention: {i.title}",
                status=_node_status(i.status),
                priority=2,
                metadata={"intervention_type": i.intervention_type},
            )
        )

    # --- Readiness gate nodes ---
    for r in readiness_assessments:
        nid = f"gate-{r.id}"
        node_ids.add(nid)
        gate_status = "completed" if r.status in ("ready", "passed") else "blocked"
        nodes.append(
            ConstraintNode(
                node_id=nid,
                node_type="readiness_gate",
                label=f"Readiness: {r.readiness_type}",
                status=gate_status,
                priority=4,
                metadata={"readiness_type": r.readiness_type, "score": r.score},
            )
        )

    # --- Evidence requirement nodes (from unknown issues) ---
    for u in unknowns:
        nid = f"evidence-{u.id}"
        node_ids.add(nid)
        nodes.append(
            ConstraintNode(
                node_id=nid,
                node_type="evidence_requirement",
                label=f"Evidence: {u.title}",
                status="blocked" if u.blocks_readiness else "ready",
                priority=3 if u.blocks_readiness else 1,
                metadata={"unknown_type": u.unknown_type, "severity": u.severity},
            )
        )

    # --- Compliance check nodes (one per pollutant that lacks completed samples) ---
    evaluated_pollutants: set[str] = set()
    for s in samples:
        pt = (s.pollutant_type or "").lower()
        if pt and s.concentration is not None:
            evaluated_pollutants.add(pt)

    all_pollutants = {"asbestos", "pcb", "lead", "hap", "radon"}
    for pollutant in sorted(all_pollutants - evaluated_pollutants):
        nid = f"compliance-{pollutant}"
        node_ids.add(nid)
        nodes.append(
            ConstraintNode(
                node_id=nid,
                node_type="compliance_check",
                label=f"Compliance: {pollutant} evaluation needed",
                status="blocked",
                priority=3,
                metadata={"pollutant": pollutant},
            )
        )

    # --- Build edges ---

    # Interventions with a diagnostic_id depend on that diagnostic being completed
    for i in interventions:
        interv_nid = f"interv-{i.id}"
        if i.diagnostic_id:
            diag_nid = f"diag-{i.diagnostic_id}"
            if diag_nid in node_ids:
                edges.append(
                    ConstraintEdge(
                        from_node=diag_nid,
                        to_node=interv_nid,
                        edge_type="blocks",
                        description="Diagnostic must complete before intervention can start",
                        is_hard=True,
                    )
                )

    # Actions linked to diagnostics depend on them
    for a in actions:
        action_nid = f"action-{a.id}"
        if a.diagnostic_id:
            diag_nid = f"diag-{a.diagnostic_id}"
            if diag_nid in node_ids:
                edges.append(
                    ConstraintEdge(
                        from_node=diag_nid,
                        to_node=action_nid,
                        edge_type="triggers",
                        description="Diagnostic triggers this action",
                        is_hard=False,
                    )
                )

    # Compliance checks require at least one incomplete diagnostic
    incomplete_diag_nids = [f"diag-{d.id}" for d in diagnostics if d.status not in _STATUS_COMPLETE]
    for pollutant in sorted(all_pollutants - evaluated_pollutants):
        compliance_nid = f"compliance-{pollutant}"
        for diag_nid in incomplete_diag_nids:
            edges.append(
                ConstraintEdge(
                    from_node=diag_nid,
                    to_node=compliance_nid,
                    edge_type="enables",
                    description=f"Completing diagnostic may provide {pollutant} evaluation",
                    is_hard=False,
                )
            )

    # Readiness gates are blocked by open critical/high actions
    gate_nids = [f"gate-{r.id}" for r in readiness_assessments]
    critical_action_nids = [
        f"action-{a.id}" for a in actions if a.status == "open" and a.priority in ("critical", "high")
    ]
    for gate_nid in gate_nids:
        for action_nid in critical_action_nids:
            edges.append(
                ConstraintEdge(
                    from_node=action_nid,
                    to_node=gate_nid,
                    edge_type="blocks",
                    description="Critical/high action blocks readiness gate",
                    is_hard=True,
                )
            )

    # Evidence requirements block readiness gates if blocks_readiness is set
    for u in unknowns:
        if u.blocks_readiness:
            evidence_nid = f"evidence-{u.id}"
            for gate_nid in gate_nids:
                edges.append(
                    ConstraintEdge(
                        from_node=evidence_nid,
                        to_node=gate_nid,
                        edge_type="blocks",
                        description=f"Unknown issue '{u.title}' blocks readiness",
                        is_hard=True,
                    )
                )

    # Compliance checks block readiness gates
    for pollutant in sorted(all_pollutants - evaluated_pollutants):
        compliance_nid = f"compliance-{pollutant}"
        for gate_nid in gate_nids:
            edges.append(
                ConstraintEdge(
                    from_node=compliance_nid,
                    to_node=gate_nid,
                    edge_type="blocks",
                    description=f"Missing {pollutant} compliance blocks readiness",
                    is_hard=True,
                )
            )

    # Apply blocked status: nodes whose hard dependencies are not all completed
    _apply_blocked_status(nodes, edges)

    return nodes, edges


def _apply_blocked_status(
    nodes: list[ConstraintNode],
    edges: list[ConstraintEdge],
) -> None:
    """Mark nodes as blocked if any hard dependency is not completed."""
    node_map = {n.node_id: n for n in nodes}
    # Build reverse lookup: node_id -> list of hard from_nodes that block it
    hard_deps: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e.is_hard and e.edge_type == "blocks":
            hard_deps[e.to_node].append(e.from_node)

    for nid, dep_nids in hard_deps.items():
        node = node_map.get(nid)
        if not node or node.status in ("completed", "not_applicable"):
            continue
        for dep_nid in dep_nids:
            dep = node_map.get(dep_nid)
            if dep and dep.status != "completed":
                node.status = "blocked"
                break


# ---------------------------------------------------------------------------
# Internal: graph traversal
# ---------------------------------------------------------------------------


def _build_adjacency(edges: list[ConstraintEdge]) -> dict[str, list[str]]:
    """Build from_node -> [to_node] adjacency list."""
    adj: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        adj[e.from_node].append(e.to_node)
    return adj


def _build_reverse_adjacency(edges: list[ConstraintEdge]) -> dict[str, list[str]]:
    """Build to_node -> [from_node] reverse adjacency list."""
    rev: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        rev[e.to_node].append(e.from_node)
    return rev


def _find_longest_path(
    nodes: list[ConstraintNode],
    edges: list[ConstraintEdge],
) -> list[ConstraintNode]:
    """Find the longest chain of non-completed dependencies (DFS longest path)."""
    node_map = {n.node_id: n for n in nodes}
    adj = _build_adjacency(edges)

    non_complete = {n.node_id for n in nodes if n.status != "completed"}
    if not non_complete:
        return []

    memo: dict[str, list[str]] = {}

    def dfs(nid: str, visited: set[str]) -> list[str]:
        if nid in memo:
            return memo[nid]
        if nid not in non_complete:
            return []

        best: list[str] = [nid]
        for neighbor in adj.get(nid, []):
            if neighbor in visited or neighbor not in non_complete:
                continue
            visited.add(neighbor)
            sub = dfs(neighbor, visited)
            candidate = [nid, *sub]
            if len(candidate) > len(best):
                best = candidate
            visited.discard(neighbor)

        memo[nid] = best
        return best

    longest: list[str] = []
    for nid in non_complete:
        path = dfs(nid, {nid})
        if len(path) > len(longest):
            longest = path

    return [node_map[nid] for nid in longest if nid in node_map]


def _compute_downstream_unlocks(
    node_id: str,
    nodes: list[ConstraintNode],
    edges: list[ConstraintEdge],
) -> list[str]:
    """Compute all nodes that would become unblocked if node_id were completed."""
    node_map = {n.node_id: n for n in nodes}
    adj = _build_adjacency(edges)
    hard_blocking_edges = [e for e in edges if e.is_hard and e.edge_type == "blocks"]

    # Build: to_node -> set of non-completed hard blockers
    hard_blockers: dict[str, set[str]] = defaultdict(set)
    for e in hard_blocking_edges:
        dep = node_map.get(e.from_node)
        if dep and dep.status != "completed":
            hard_blockers[e.to_node].add(e.from_node)

    # If completing node_id, which nodes have all hard blockers resolved?
    unlocked: list[str] = []
    # BFS: completing node_id, check direct and transitive unlocks
    queue = [node_id]
    visited = {node_id}
    while queue:
        current = queue.pop(0)
        for neighbor in adj.get(current, []):
            if neighbor in visited:
                continue
            target = node_map.get(neighbor)
            if not target or target.status in ("completed", "not_applicable"):
                continue
            remaining = hard_blockers.get(neighbor, set()) - visited
            if not remaining:
                unlocked.append(neighbor)
                visited.add(neighbor)
                queue.append(neighbor)

    return unlocked


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _make_graph(
    building_id: UUID,
    nodes: list[ConstraintNode],
    edges: list[ConstraintEdge],
) -> ConstraintGraph:
    """Assemble a ConstraintGraph from nodes and edges."""
    return ConstraintGraph(
        building_id=building_id,
        nodes=nodes,
        edges=edges,
        total_nodes=len(nodes),
        total_edges=len(edges),
        blocked_count=sum(1 for n in nodes if n.status == "blocked"),
        ready_count=sum(1 for n in nodes if n.status == "ready"),
    )


async def build_constraint_graph(
    db: AsyncSession,
    building_id: UUID,
) -> ConstraintGraph:
    """Build the full constraint graph for a building."""
    data = await _fetch_building_data(db, building_id)
    building, diagnostics, actions, interventions, readiness_assessments, samples, unknowns = data
    if not building:
        return _make_graph(building_id, [], [])

    nodes, edges = _build_nodes_and_edges(diagnostics, actions, interventions, readiness_assessments, samples, unknowns)
    return _make_graph(building_id, nodes, edges)


async def find_critical_path(
    db: AsyncSession,
    building_id: UUID,
) -> CriticalPath:
    """Find the longest chain of blocked dependencies."""
    graph = await build_constraint_graph(db, building_id)
    path = _find_longest_path(graph.nodes, graph.edges)

    # Determine what completing this path unlocks
    unlock_value = None
    if path:
        gate_nodes = [n for n in path if n.node_type == "readiness_gate"]
        if gate_nodes:
            unlock_value = f"Unlocks readiness gate: {gate_nodes[-1].label}"
        else:
            unlock_value = f"Resolves {len(path)} dependency chain"

    return CriticalPath(
        building_id=building_id,
        path=path,
        total_steps=len(path),
        blocked_steps=sum(1 for n in path if n.status == "blocked"),
        estimated_unlock_value=unlock_value,
    )


async def get_unlock_analysis(
    db: AsyncSession,
    building_id: UUID,
) -> list[UnlockAnalysis]:
    """For each non-completed node, compute how many others it would unblock."""
    graph = await build_constraint_graph(db, building_id)
    results: list[UnlockAnalysis] = []

    non_complete = [n for n in graph.nodes if n.status not in ("completed", "not_applicable")]
    for node in non_complete:
        unlocks = _compute_downstream_unlocks(node.node_id, graph.nodes, graph.edges)
        priority_score = len(unlocks) * 1.0 + (node.priority or 0) * 0.5
        results.append(
            UnlockAnalysis(
                building_id=building_id,
                node_id=node.node_id,
                label=node.label,
                unlocks=unlocks,
                unlock_count=len(unlocks),
                priority_score=priority_score,
            )
        )

    results.sort(key=lambda x: x.priority_score, reverse=True)
    return results


async def get_readiness_blockers(
    db: AsyncSession,
    building_id: UUID,
) -> list[ReadinessBlocker]:
    """Return human-readable blockers preventing readiness."""
    graph = await build_constraint_graph(db, building_id)
    node_map = {n.node_id: n for n in graph.nodes}

    # Build reverse: which nodes block each gate
    gate_blockers: dict[str, list[str]] = defaultdict(list)
    for e in graph.edges:
        target = node_map.get(e.to_node)
        if target and target.node_type == "readiness_gate" and e.is_hard and e.edge_type == "blocks":
            source = node_map.get(e.from_node)
            if source and source.status != "completed":
                gate_blockers[e.to_node].append(e.from_node)

    blockers: list[ReadinessBlocker] = []
    for gate_nid, blocker_nids in gate_blockers.items():
        gate = node_map[gate_nid]
        for blocker_nid in blocker_nids:
            blocker = node_map[blocker_nid]
            # Suggest unblock actions based on blocker type
            can_unblock: list[str] = []
            if blocker.node_type == "action":
                can_unblock.append(f"Complete action: {blocker.label}")
            elif blocker.node_type == "diagnostic":
                can_unblock.append(f"Complete diagnostic: {blocker.label}")
            elif blocker.node_type == "compliance_check":
                can_unblock.append(f"Perform evaluation: {blocker.label}")
            elif blocker.node_type == "evidence_requirement":
                can_unblock.append(f"Resolve unknown: {blocker.label}")
            else:
                can_unblock.append(f"Complete: {blocker.label}")

            blockers.append(
                ReadinessBlocker(
                    building_id=building_id,
                    blocker_type=blocker.node_type,
                    description=f"{blocker.label} blocks {gate.label}",
                    blocked_by=[blocker_nid],
                    can_unblock=can_unblock,
                )
            )

    return blockers


async def get_next_best_action(
    db: AsyncSession,
    building_id: UUID,
) -> UnlockAnalysis | None:
    """Return the single highest-leverage action."""
    analyses = await get_unlock_analysis(db, building_id)
    return analyses[0] if analyses else None


async def simulate_completion(
    db: AsyncSession,
    building_id: UUID,
    node_ids: list[str],
) -> ConstraintGraph:
    """Return what the graph would look like if given nodes were completed."""
    graph = await build_constraint_graph(db, building_id)

    # Deep copy nodes and mark simulated ones as completed
    sim_nodes = []
    for n in graph.nodes:
        if n.node_id in node_ids:
            sim_nodes.append(n.model_copy(update={"status": "completed"}))
        else:
            sim_nodes.append(n.model_copy())

    # Re-apply blocked status with updated nodes
    # Reset non-completed nodes to ready first, then re-apply
    for n in sim_nodes:
        if n.status not in ("completed", "not_applicable"):
            n.status = "ready"

    _apply_blocked_status(sim_nodes, graph.edges)

    return _make_graph(building_id, sim_nodes, graph.edges)
