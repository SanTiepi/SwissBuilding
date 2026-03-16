"""Tests for the constraint graph service and API endpoints."""

import uuid

from app.models.action_item import ActionItem
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.readiness_assessment import ReadinessAssessment
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue
from app.services.constraint_graph_service import (
    build_constraint_graph,
    find_critical_path,
    get_next_best_action,
    get_readiness_blockers,
    get_unlock_analysis,
    simulate_completion,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_diagnostic(building_id, *, status="draft", diagnostic_type="full", context="AvT"):
    return Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type=diagnostic_type,
        diagnostic_context=context,
        status=status,
    )


def _make_action(building_id, *, title="Test action", status="open", priority="high", diagnostic_id=None):
    return ActionItem(
        id=uuid.uuid4(),
        building_id=building_id,
        title=title,
        action_type="remediation",
        source_type="diagnostic",
        status=status,
        priority=priority,
        diagnostic_id=diagnostic_id,
    )


def _make_intervention(building_id, *, title="Test intervention", status="planned", diagnostic_id=None):
    return Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type="removal",
        title=title,
        status=status,
        diagnostic_id=diagnostic_id,
    )


def _make_readiness(building_id, *, readiness_type="safe_to_start", status="not_ready", score=0.3):
    return ReadinessAssessment(
        id=uuid.uuid4(),
        building_id=building_id,
        readiness_type=readiness_type,
        status=status,
        score=score,
    )


def _make_sample(diagnostic_id, *, pollutant_type="asbestos", concentration=None):
    return Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        location_floor="1",
        location_room="Room 1",
        pollutant_type=pollutant_type,
        concentration=concentration,
        unit="mg/kg" if concentration is not None else None,
    )


def _make_unknown(building_id, *, title="Unknown issue", blocks_readiness=True):
    return UnknownIssue(
        id=uuid.uuid4(),
        building_id=building_id,
        unknown_type="missing_data",
        severity="high",
        status="open",
        title=title,
        blocks_readiness=blocks_readiness,
    )


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestBuildConstraintGraph:
    async def test_empty_graph_no_data(self, db_session, sample_building):
        """Building with no diagnostics/actions/interventions only has compliance check nodes."""
        graph = await build_constraint_graph(db_session, sample_building.id)
        assert graph.building_id == sample_building.id
        # 5 compliance check nodes (one per unevaluated pollutant)
        assert graph.total_nodes == 5
        assert all(n.node_type == "compliance_check" for n in graph.nodes)
        assert graph.total_edges == 0

    async def test_nonexistent_building(self, db_session):
        """Nonexistent building returns empty graph."""
        fake_id = uuid.uuid4()
        graph = await build_constraint_graph(db_session, fake_id)
        assert graph.total_nodes == 0

    async def test_diagnostic_node(self, db_session, sample_building):
        """A draft diagnostic appears as a ready node."""
        diag = _make_diagnostic(sample_building.id, status="draft")
        db_session.add(diag)
        await db_session.commit()

        graph = await build_constraint_graph(db_session, sample_building.id)
        assert graph.total_nodes >= 1
        diag_nodes = [n for n in graph.nodes if n.node_type == "diagnostic"]
        assert len(diag_nodes) == 1
        assert diag_nodes[0].status == "ready"

    async def test_completed_diagnostic_node(self, db_session, sample_building):
        """A completed diagnostic has completed status."""
        diag = _make_diagnostic(sample_building.id, status="completed")
        db_session.add(diag)
        await db_session.commit()

        graph = await build_constraint_graph(db_session, sample_building.id)
        diag_nodes = [n for n in graph.nodes if n.node_type == "diagnostic"]
        assert diag_nodes[0].status == "completed"

    async def test_diagnostic_intervention_dependency(self, db_session, sample_building):
        """Intervention linked to a diagnostic creates a blocking edge."""
        diag = _make_diagnostic(sample_building.id, status="draft")
        db_session.add(diag)
        await db_session.flush()

        interv = _make_intervention(sample_building.id, diagnostic_id=diag.id)
        db_session.add(interv)
        await db_session.commit()

        graph = await build_constraint_graph(db_session, sample_building.id)
        blocking_edges = [e for e in graph.edges if e.edge_type == "blocks" and "diag-" in e.from_node]
        assert len(blocking_edges) >= 1
        # Intervention should be blocked because diagnostic is not completed
        interv_nodes = [n for n in graph.nodes if n.node_type == "intervention"]
        assert interv_nodes[0].status == "blocked"

    async def test_action_readiness_gate_dependency(self, db_session, sample_building):
        """Open critical action blocks readiness gate."""
        action = _make_action(sample_building.id, status="open", priority="critical")
        gate = _make_readiness(sample_building.id, status="not_ready")
        db_session.add_all([action, gate])
        await db_session.commit()

        graph = await build_constraint_graph(db_session, sample_building.id)
        gate_nodes = [n for n in graph.nodes if n.node_type == "readiness_gate"]
        assert len(gate_nodes) == 1
        assert gate_nodes[0].status == "blocked"

        blocking_edges = [
            e for e in graph.edges if e.edge_type == "blocks" and "action-" in e.from_node and "gate-" in e.to_node
        ]
        assert len(blocking_edges) >= 1

    async def test_compliance_check_nodes(self, db_session, sample_building):
        """Missing pollutant evaluations produce compliance check nodes."""
        diag = _make_diagnostic(sample_building.id, status="completed")
        db_session.add(diag)
        await db_session.flush()

        # Only add asbestos sample with results
        s = _make_sample(diag.id, pollutant_type="asbestos", concentration=0.05)
        db_session.add(s)
        await db_session.commit()

        graph = await build_constraint_graph(db_session, sample_building.id)
        compliance_nodes = [n for n in graph.nodes if n.node_type == "compliance_check"]
        # Should have nodes for pcb, lead, hap, radon (4 missing)
        assert len(compliance_nodes) == 4
        pollutants = {n.metadata["pollutant"] for n in compliance_nodes}
        assert pollutants == {"pcb", "lead", "hap", "radon"}

    async def test_evidence_requirement_node(self, db_session, sample_building):
        """Unknown issues create evidence requirement nodes."""
        unknown = _make_unknown(sample_building.id, title="Missing roof survey")
        db_session.add(unknown)
        await db_session.commit()

        graph = await build_constraint_graph(db_session, sample_building.id)
        evidence_nodes = [n for n in graph.nodes if n.node_type == "evidence_requirement"]
        assert len(evidence_nodes) == 1
        assert evidence_nodes[0].label == "Evidence: Missing roof survey"
        assert evidence_nodes[0].status == "blocked"

    async def test_hard_vs_soft_dependencies(self, db_session, sample_building):
        """Diagnostic-to-intervention is hard; diagnostic-to-action is soft."""
        diag = _make_diagnostic(sample_building.id, status="draft")
        db_session.add(diag)
        await db_session.flush()

        interv = _make_intervention(sample_building.id, diagnostic_id=diag.id)
        action = _make_action(sample_building.id, diagnostic_id=diag.id)
        db_session.add_all([interv, action])
        await db_session.commit()

        graph = await build_constraint_graph(db_session, sample_building.id)

        hard_edges = [e for e in graph.edges if e.is_hard and "diag-" in e.from_node]
        soft_edges = [e for e in graph.edges if not e.is_hard and "diag-" in e.from_node]
        assert len(hard_edges) >= 1  # diagnostic blocks intervention
        assert len(soft_edges) >= 1  # diagnostic triggers action

    async def test_multiple_independent_chains(self, db_session, sample_building):
        """Two independent diagnostic-intervention chains."""
        diag1 = _make_diagnostic(sample_building.id, status="draft", diagnostic_type="asbestos")
        diag2 = _make_diagnostic(sample_building.id, status="in_progress", diagnostic_type="pcb")
        db_session.add_all([diag1, diag2])
        await db_session.flush()

        interv1 = _make_intervention(sample_building.id, title="Remove asbestos", diagnostic_id=diag1.id)
        interv2 = _make_intervention(sample_building.id, title="Remove PCB", diagnostic_id=diag2.id)
        db_session.add_all([interv1, interv2])
        await db_session.commit()

        graph = await build_constraint_graph(db_session, sample_building.id)
        interv_nodes = [n for n in graph.nodes if n.node_type == "intervention"]
        assert len(interv_nodes) == 2
        # Both should be blocked since their diagnostics are not completed
        assert all(n.status == "blocked" for n in interv_nodes)


class TestCriticalPath:
    async def test_empty_critical_path(self, db_session, sample_building):
        """Building with only compliance checks has a minimal critical path."""
        cp = await find_critical_path(db_session, sample_building.id)
        assert cp.building_id == sample_building.id
        # Compliance check nodes exist but are independent (no chain)
        assert cp.total_steps >= 1
        assert cp.blocked_steps >= 1

    async def test_critical_path_with_chain(self, db_session, sample_building):
        """Diagnostic -> intervention chain produces a critical path."""
        diag = _make_diagnostic(sample_building.id, status="draft")
        db_session.add(diag)
        await db_session.flush()

        interv = _make_intervention(sample_building.id, diagnostic_id=diag.id)
        gate = _make_readiness(sample_building.id)
        db_session.add_all([interv, gate])
        await db_session.commit()

        cp = await find_critical_path(db_session, sample_building.id)
        assert cp.total_steps >= 1
        assert cp.estimated_unlock_value is not None


class TestUnlockAnalysis:
    async def test_unlock_analysis_ranking(self, db_session, sample_building):
        """Actions that unblock more nodes score higher."""
        diag = _make_diagnostic(sample_building.id, status="draft")
        db_session.add(diag)
        await db_session.flush()

        interv = _make_intervention(sample_building.id, diagnostic_id=diag.id)
        action = _make_action(sample_building.id, status="open", priority="critical")
        gate = _make_readiness(sample_building.id)
        db_session.add_all([interv, action, gate])
        await db_session.commit()

        analyses = await get_unlock_analysis(db_session, sample_building.id)
        assert len(analyses) >= 1
        # Sorted by priority_score descending
        for i in range(len(analyses) - 1):
            assert analyses[i].priority_score >= analyses[i + 1].priority_score

    async def test_unlock_analysis_compliance_only(self, db_session, sample_building):
        """Building with only compliance checks returns those in analysis."""
        analyses = await get_unlock_analysis(db_session, sample_building.id)
        # 5 compliance check nodes with no downstream unlocks
        assert len(analyses) == 5
        assert all(a.unlock_count == 0 for a in analyses)


class TestNextBestAction:
    async def test_next_best_action_exists(self, db_session, sample_building):
        """Returns the highest-leverage action."""
        action = _make_action(sample_building.id, status="open", priority="critical")
        gate = _make_readiness(sample_building.id)
        db_session.add_all([action, gate])
        await db_session.commit()

        result = await get_next_best_action(db_session, sample_building.id)
        assert result is not None
        assert result.building_id == sample_building.id

    async def test_next_best_action_nonexistent_building(self, db_session):
        """Returns None for a nonexistent building."""
        fake_id = uuid.uuid4()
        result = await get_next_best_action(db_session, fake_id)
        assert result is None


class TestReadinessBlockers:
    async def test_blockers_listing(self, db_session, sample_building):
        """Readiness blockers are listed with suggestions."""
        action = _make_action(sample_building.id, status="open", priority="high")
        gate = _make_readiness(sample_building.id)
        db_session.add_all([action, gate])
        await db_session.commit()

        blockers = await get_readiness_blockers(db_session, sample_building.id)
        assert len(blockers) >= 1
        assert blockers[0].blocker_type == "action"
        assert len(blockers[0].can_unblock) >= 1

    async def test_no_blockers(self, db_session, sample_building):
        """Building with no readiness gates returns no blockers."""
        blockers = await get_readiness_blockers(db_session, sample_building.id)
        assert blockers == []

    async def test_evidence_blocker(self, db_session, sample_building):
        """Unknown issue blocking readiness appears as a blocker."""
        unknown = _make_unknown(sample_building.id, title="Missing asbestos survey", blocks_readiness=True)
        gate = _make_readiness(sample_building.id)
        db_session.add_all([unknown, gate])
        await db_session.commit()

        blockers = await get_readiness_blockers(db_session, sample_building.id)
        evidence_blockers = [b for b in blockers if b.blocker_type == "evidence_requirement"]
        assert len(evidence_blockers) >= 1


class TestSimulateCompletion:
    async def test_simulate_unblocks_downstream(self, db_session, sample_building):
        """Simulating diagnostic completion unblocks dependent intervention."""
        diag = _make_diagnostic(sample_building.id, status="draft")
        db_session.add(diag)
        await db_session.flush()

        interv = _make_intervention(sample_building.id, diagnostic_id=diag.id)
        db_session.add(interv)
        await db_session.commit()

        diag_nid = f"diag-{diag.id}"
        interv_nid = f"interv-{interv.id}"

        # Before simulation: intervention is blocked
        graph = await build_constraint_graph(db_session, sample_building.id)
        interv_node = next(n for n in graph.nodes if n.node_id == interv_nid)
        assert interv_node.status == "blocked"

        # After simulation: intervention should be unblocked
        sim_graph = await simulate_completion(db_session, sample_building.id, [diag_nid])
        sim_diag = next(n for n in sim_graph.nodes if n.node_id == diag_nid)
        assert sim_diag.status == "completed"
        sim_interv = next(n for n in sim_graph.nodes if n.node_id == interv_nid)
        assert sim_interv.status == "ready"

    async def test_simulate_no_effect_on_db(self, db_session, sample_building):
        """Simulation does not modify actual database records."""
        diag = _make_diagnostic(sample_building.id, status="draft")
        db_session.add(diag)
        await db_session.commit()

        diag_nid = f"diag-{diag.id}"
        await simulate_completion(db_session, sample_building.id, [diag_nid])

        # Original graph should still show draft
        graph = await build_constraint_graph(db_session, sample_building.id)
        diag_node = next(n for n in graph.nodes if n.node_id == diag_nid)
        assert diag_node.status == "ready"  # draft maps to ready


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestConstraintGraphAPI:
    async def test_get_graph(self, client, admin_user, auth_headers, sample_building):
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/constraint-graph",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["building_id"] == str(sample_building.id)
        assert "nodes" in data
        assert "edges" in data
        assert "total_nodes" in data

    async def test_get_graph_404(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{fake_id}/constraint-graph",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_get_critical_path(self, client, admin_user, auth_headers, sample_building):
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/constraint-graph/critical-path",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert "total_steps" in data

    async def test_get_unlock_analysis(self, client, admin_user, auth_headers, sample_building):
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/constraint-graph/unlock-analysis",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_blockers(self, client, admin_user, auth_headers, sample_building):
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/constraint-graph/blockers",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_next_best_action(self, client, admin_user, auth_headers, sample_building):
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/constraint-graph/next-best-action",
            headers=auth_headers,
        )
        assert response.status_code == 200

    async def test_simulate_completion(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/constraint-graph/simulate",
            json={"node_ids": ["diag-fake"]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["building_id"] == str(sample_building.id)

    async def test_simulate_404(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/buildings/{fake_id}/constraint-graph/simulate",
            json={"node_ids": []},
            headers=auth_headers,
        )
        assert response.status_code == 404
