"""Tests for the evidence graph traversal service and API."""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.zone import Zone
from app.services.evidence_graph_service import (
    build_evidence_graph,
    find_evidence_path,
    get_connected_components,
    get_entity_neighbors,
    get_evidence_chain_for_entity,
    get_evidence_graph_stats,
)

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=user_id,
        status="active",
    )
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _make_diagnostic(db, building_id):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def _make_sample(db, diagnostic_id):
    s = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number="S-001",
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _make_document(db, building_id):
    doc = Document(
        id=uuid.uuid4(),
        building_id=building_id,
        file_path="/docs/test.pdf",
        file_name="test.pdf",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def _make_zone(db, building_id):
    z = Zone(
        id=uuid.uuid4(),
        building_id=building_id,
        zone_type="room",
        name="Room A",
    )
    db.add(z)
    await db.commit()
    await db.refresh(z)
    return z


async def _make_intervention(db, building_id):
    i = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type="removal",
        title="Remove asbestos",
        status="planned",
    )
    db.add(i)
    await db.commit()
    await db.refresh(i)
    return i


async def _make_evidence_link(
    db,
    source_type,
    source_id,
    target_type,
    target_id,
    relationship="supports",
    confidence=0.9,
    legal_reference=None,
    explanation=None,
):
    link = EvidenceLink(
        id=uuid.uuid4(),
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        relationship=relationship,
        confidence=confidence,
        legal_reference=legal_reference,
        explanation=explanation,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


# ---------------------------------------------------------------------------
# Service tests: build_evidence_graph
# ---------------------------------------------------------------------------


async def test_build_graph_empty(db_session, admin_user):
    """Build graph for building with no links yields empty graph."""
    building = await _make_building(db_session, admin_user.id)
    graph = await build_evidence_graph(db_session, building.id)
    assert graph.building_id == building.id
    assert graph.total_edges == 0
    # building itself is a node
    assert graph.total_nodes >= 1
    assert graph.connected_components >= 1


async def test_build_graph_with_links(db_session, admin_user):
    """Build graph with multiple links across entity types."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    sample = await _make_sample(db_session, diag.id)
    doc = await _make_document(db_session, building.id)

    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id)
    await _make_evidence_link(db_session, "document", doc.id, "diagnostic", diag.id)

    graph = await build_evidence_graph(db_session, building.id)
    assert graph.total_edges == 2
    assert graph.total_nodes >= 4  # building, diag, sample, doc
    assert graph.connected_components >= 1


async def test_build_graph_connected_components(db_session, admin_user):
    """Graph with two disconnected subgraphs reports 2+ components."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    sample = await _make_sample(db_session, diag.id)
    doc = await _make_document(db_session, building.id)
    zone = await _make_zone(db_session, building.id)

    # Subgraph 1: diag <-> sample
    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id)
    # Subgraph 2: doc <-> zone
    await _make_evidence_link(db_session, "document", doc.id, "zone", zone.id)

    graph = await build_evidence_graph(db_session, building.id)
    # building node is isolated (no links), diag-sample cluster, doc-zone cluster
    assert graph.connected_components >= 3


# ---------------------------------------------------------------------------
# Service tests: get_entity_neighbors
# ---------------------------------------------------------------------------


async def test_entity_neighbors_both_directions(db_session, admin_user):
    """Neighbors include both incoming and outgoing links."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    sample = await _make_sample(db_session, diag.id)
    doc = await _make_document(db_session, building.id)

    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id)
    await _make_evidence_link(db_session, "document", doc.id, "diagnostic", diag.id)

    neighbors = await get_entity_neighbors(db_session, "diagnostic", diag.id)
    assert neighbors.entity_type == "diagnostic"
    assert neighbors.entity_id == diag.id
    assert len(neighbors.outgoing) == 1
    assert len(neighbors.incoming) == 1
    assert neighbors.total_connections == 2


async def test_entity_neighbors_no_links(db_session, admin_user):
    """Entity with no links returns empty neighbors."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)

    neighbors = await get_entity_neighbors(db_session, "diagnostic", diag.id)
    assert neighbors.total_connections == 0
    assert neighbors.incoming == []
    assert neighbors.outgoing == []


# ---------------------------------------------------------------------------
# Service tests: find_evidence_path
# ---------------------------------------------------------------------------


async def test_find_path_direct(db_session, admin_user):
    """Find path between directly connected entities."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    sample = await _make_sample(db_session, diag.id)

    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id, confidence=0.8)

    path = await find_evidence_path(db_session, "diagnostic", diag.id, "sample", sample.id)
    assert path is not None
    assert path.total_hops == 1
    assert len(path.steps) == 2
    assert path.min_confidence == 0.8


async def test_find_path_multi_hop(db_session, admin_user):
    """Find path through intermediate entities."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    sample = await _make_sample(db_session, diag.id)
    doc = await _make_document(db_session, building.id)

    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id, confidence=0.9)
    await _make_evidence_link(db_session, "sample", sample.id, "document", doc.id, confidence=0.7)

    path = await find_evidence_path(db_session, "diagnostic", diag.id, "document", doc.id)
    assert path is not None
    assert path.total_hops == 2
    assert len(path.steps) == 3
    assert path.min_confidence == 0.7


async def test_find_path_disconnected(db_session, admin_user):
    """Returns None for disconnected entities."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    doc = await _make_document(db_session, building.id)

    # No link between them
    path = await find_evidence_path(db_session, "diagnostic", diag.id, "document", doc.id)
    assert path is None


async def test_find_path_max_hops_exceeded(db_session, admin_user):
    """Returns None when path exceeds max_hops."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    sample = await _make_sample(db_session, diag.id)
    doc = await _make_document(db_session, building.id)

    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id)
    await _make_evidence_link(db_session, "sample", sample.id, "document", doc.id)

    # Max 1 hop can't reach doc from diag (needs 2)
    path = await find_evidence_path(db_session, "diagnostic", diag.id, "document", doc.id, max_hops=1)
    assert path is None


async def test_find_path_same_entity(db_session, admin_user):
    """Path from entity to itself is zero hops."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)

    path = await find_evidence_path(db_session, "diagnostic", diag.id, "diagnostic", diag.id)
    assert path is not None
    assert path.total_hops == 0


# ---------------------------------------------------------------------------
# Service tests: get_evidence_graph_stats
# ---------------------------------------------------------------------------


async def test_stats_empty(db_session, admin_user):
    """Stats for building with no links."""
    building = await _make_building(db_session, admin_user.id)
    stats = await get_evidence_graph_stats(db_session, building.id)
    assert stats.building_id == building.id
    assert stats.total_links == 0
    assert stats.by_relationship == {}
    assert stats.avg_confidence is None
    assert stats.weakest_links == []


async def test_stats_counts(db_session, admin_user):
    """Stats correctly count by_relationship and by_entity_type."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    sample = await _make_sample(db_session, diag.id)
    doc = await _make_document(db_session, building.id)

    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id, relationship="supports")
    await _make_evidence_link(db_session, "document", doc.id, "diagnostic", diag.id, relationship="references")

    stats = await get_evidence_graph_stats(db_session, building.id)
    assert stats.total_links == 2
    assert stats.by_relationship.get("supports") == 1
    assert stats.by_relationship.get("references") == 1
    assert stats.by_entity_type.get("diagnostic") == 1
    assert stats.by_entity_type.get("sample") == 1
    assert stats.by_entity_type.get("document") == 1


async def test_stats_weakest_links(db_session, admin_user):
    """Weakest links sorted by lowest confidence."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    sample = await _make_sample(db_session, diag.id)
    doc = await _make_document(db_session, building.id)

    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id, confidence=0.3)
    await _make_evidence_link(db_session, "document", doc.id, "diagnostic", diag.id, confidence=0.9)

    stats = await get_evidence_graph_stats(db_session, building.id)
    assert len(stats.weakest_links) == 2
    assert stats.weakest_links[0].confidence == 0.3
    assert stats.weakest_links[1].confidence == 0.9


async def test_stats_avg_confidence(db_session, admin_user):
    """Average confidence computed correctly."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    sample = await _make_sample(db_session, diag.id)

    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id, confidence=0.6)

    stats = await get_evidence_graph_stats(db_session, building.id)
    assert stats.avg_confidence == pytest.approx(0.6)


async def test_stats_orphan_entities(db_session, admin_user):
    """Orphan entities are those with no evidence links."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    await _make_document(db_session, building.id)  # orphan - no links

    await _make_sample(db_session, diag.id)  # orphan - no links

    stats = await get_evidence_graph_stats(db_session, building.id)
    # All entities are orphans since no links
    assert len(stats.orphan_entities) >= 3  # building, diag, doc, sample


# ---------------------------------------------------------------------------
# Service tests: get_connected_components
# ---------------------------------------------------------------------------


async def test_connected_components_single(db_session, admin_user):
    """One connected component when all entities are linked."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    sample = await _make_sample(db_session, diag.id)

    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id)

    components = await get_connected_components(db_session, building.id)
    # building is isolated, diag+sample are connected
    connected = [c for c in components if len(c) > 1]
    assert len(connected) >= 1


async def test_connected_components_multiple(db_session, admin_user):
    """Multiple disconnected subgraphs detected."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    sample = await _make_sample(db_session, diag.id)
    doc = await _make_document(db_session, building.id)
    zone = await _make_zone(db_session, building.id)

    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id)
    await _make_evidence_link(db_session, "document", doc.id, "zone", zone.id)

    components = await get_connected_components(db_session, building.id)
    assert len(components) >= 3  # diag+sample, doc+zone, building alone


# ---------------------------------------------------------------------------
# Service tests: get_evidence_chain_for_entity
# ---------------------------------------------------------------------------


async def test_chain_depth_1(db_session, admin_user):
    """Chain with depth=1 returns immediate neighbors only."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    sample = await _make_sample(db_session, diag.id)
    doc = await _make_document(db_session, building.id)

    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id)
    await _make_evidence_link(db_session, "sample", sample.id, "document", doc.id)

    chain = await get_evidence_chain_for_entity(db_session, "diagnostic", diag.id, depth=1)
    # depth=1: diag + sample (direct neighbor). doc is 2 hops away.
    assert chain.total_nodes == 2
    assert chain.total_edges == 1


async def test_chain_depth_2(db_session, admin_user):
    """Chain with depth=2 reaches 2-hop entities."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)
    sample = await _make_sample(db_session, diag.id)
    doc = await _make_document(db_session, building.id)

    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id)
    await _make_evidence_link(db_session, "sample", sample.id, "document", doc.id)

    chain = await get_evidence_chain_for_entity(db_session, "diagnostic", diag.id, depth=2)
    assert chain.total_nodes == 3  # diag, sample, doc
    assert chain.total_edges == 2


async def test_chain_isolated_entity(db_session, admin_user):
    """Chain for entity with no links returns just the entity itself."""
    building = await _make_building(db_session, admin_user.id)
    diag = await _make_diagnostic(db_session, building.id)

    chain = await get_evidence_chain_for_entity(db_session, "diagnostic", diag.id, depth=3)
    assert chain.total_nodes == 1
    assert chain.total_edges == 0


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


async def test_api_building_evidence_graph(client, auth_headers, sample_building):
    """GET /buildings/{id}/evidence-graph returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/evidence-graph",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "nodes" in data
    assert "edges" in data


async def test_api_neighbors(client, auth_headers, sample_building, db_session):
    """GET /evidence-graph/neighbors/{type}/{id} returns 200."""
    diag = await _make_diagnostic(db_session, sample_building.id)
    resp = await client.get(
        f"/api/v1/evidence-graph/neighbors/diagnostic/{diag.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_type"] == "diagnostic"


async def test_api_path(client, auth_headers, sample_building, db_session):
    """GET /evidence-graph/path returns path or null."""
    diag = await _make_diagnostic(db_session, sample_building.id)
    sample = await _make_sample(db_session, diag.id)
    await _make_evidence_link(db_session, "diagnostic", diag.id, "sample", sample.id)

    resp = await client.get(
        "/api/v1/evidence-graph/path",
        params={
            "source_type": "diagnostic",
            "source_id": str(diag.id),
            "target_type": "sample",
            "target_id": str(sample.id),
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_hops"] == 1


async def test_api_stats(client, auth_headers, sample_building):
    """GET /buildings/{id}/evidence-graph/stats returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/evidence-graph/stats",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "total_links" in data


async def test_api_components(client, auth_headers, sample_building):
    """GET /buildings/{id}/evidence-graph/components returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/evidence-graph/components",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_api_chain(client, auth_headers, sample_building, db_session):
    """GET /evidence-graph/chain/{type}/{id} returns 200."""
    diag = await _make_diagnostic(db_session, sample_building.id)
    resp = await client.get(
        f"/api/v1/evidence-graph/chain/diagnostic/{diag.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
