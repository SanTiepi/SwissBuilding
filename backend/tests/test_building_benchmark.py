"""Tests for the Building Benchmark Service and API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_snapshot import BuildingSnapshot
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.building_benchmark_service import (
    benchmark_building,
    compare_buildings_benchmark,
    get_canton_benchmarks,
    get_peer_group,
)

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1975,
        "building_type": "residential",
        "created_by": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_risk_score(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "asbestos_probability": 0.5,
        "pcb_probability": 0.3,
        "lead_probability": 0.2,
        "hap_probability": 0.1,
        "radon_probability": 0.4,
        "overall_risk_level": "medium",
        "confidence": 0.7,
    }
    defaults.update(kwargs)
    rs = BuildingRiskScore(**defaults)
    db.add(rs)
    await db.flush()
    return rs


async def _create_snapshot(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "snapshot_type": "manual",
        "passport_grade": "C",
        "overall_trust": 0.6,
        "completeness_score": 0.5,
        "captured_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    snap = BuildingSnapshot(**defaults)
    db.add(snap)
    await db.flush()
    return snap


async def _create_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _create_sample(db, diagnostic_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic_id,
        "sample_number": "S-001",
    }
    defaults.update(kwargs)
    s = Sample(**defaults)
    db.add(s)
    await db.flush()
    return s


# ── Peer Group Tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_peer_group_same_canton_type_decade(db_session, admin_user):
    """Peers share canton, building_type, and construction decade."""
    b1 = await _create_building(db_session, admin_user, construction_year=1975)
    b2 = await _create_building(db_session, admin_user, construction_year=1972)
    # Different decade -> not a peer
    await _create_building(db_session, admin_user, construction_year=1965)
    # Different canton -> not a peer
    await _create_building(db_session, admin_user, canton="GE", construction_year=1975)
    # Different type -> not a peer
    await _create_building(db_session, admin_user, building_type="commercial", construction_year=1978)
    await db_session.commit()

    pg = await get_peer_group(db_session, b1.id)
    assert pg.peer_count == 2
    assert set(pg.building_ids) == {b1.id, b2.id}
    assert pg.criteria["canton"] == "VD"
    assert pg.criteria["building_type"] == "residential"
    assert pg.criteria["decade"] == "1970s"


@pytest.mark.asyncio
async def test_peer_group_no_construction_year(db_session, admin_user):
    """Buildings with no construction year form their own peer group."""
    b1 = await _create_building(db_session, admin_user, construction_year=None)
    b2 = await _create_building(db_session, admin_user, construction_year=None)
    # Has a year -> not a peer
    await _create_building(db_session, admin_user, construction_year=1975)
    await db_session.commit()

    pg = await get_peer_group(db_session, b1.id)
    assert pg.peer_count == 2
    assert set(pg.building_ids) == {b1.id, b2.id}
    assert pg.criteria["decade"] is None


@pytest.mark.asyncio
async def test_peer_group_building_not_found(db_session, admin_user):
    """Non-existent building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await get_peer_group(db_session, uuid.uuid4())


# ── Benchmark Tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_benchmark_with_peers(db_session, admin_user):
    """Benchmark against peers returns dimensions with percentiles."""
    b1 = await _create_building(db_session, admin_user, construction_year=1975)
    b2 = await _create_building(db_session, admin_user, construction_year=1978)
    b3 = await _create_building(db_session, admin_user, construction_year=1971)

    # Risk scores: b1 has lowest risk -> should be best on risk
    await _create_risk_score(
        db_session,
        b1.id,
        asbestos_probability=0.1,
        pcb_probability=0.1,
        lead_probability=0.1,
        hap_probability=0.1,
        radon_probability=0.1,
    )
    await _create_risk_score(
        db_session,
        b2.id,
        asbestos_probability=0.5,
        pcb_probability=0.5,
        lead_probability=0.5,
        hap_probability=0.5,
        radon_probability=0.5,
    )
    await _create_risk_score(
        db_session,
        b3.id,
        asbestos_probability=0.9,
        pcb_probability=0.9,
        lead_probability=0.9,
        hap_probability=0.9,
        radon_probability=0.9,
    )

    # Snapshots
    await _create_snapshot(db_session, b1.id, passport_grade="A", completeness_score=0.9, overall_trust=0.8)
    await _create_snapshot(db_session, b2.id, passport_grade="C", completeness_score=0.5, overall_trust=0.5)
    await _create_snapshot(db_session, b3.id, passport_grade="E", completeness_score=0.2, overall_trust=0.3)

    await db_session.commit()

    bm = await benchmark_building(db_session, b1.id)

    assert bm.building_id == b1.id
    assert bm.peer_group.peer_count == 3
    assert len(bm.dimensions) == 6
    assert bm.overall_percentile is not None

    # b1 has lowest risk -> risk percentile should be high (inverted: lower is better)
    risk_dim = next(d for d in bm.dimensions if d.name == "risk_score")
    assert risk_dim.building_value is not None
    assert risk_dim.percentile is not None
    assert risk_dim.better_than_peers is True

    # b1 has best completeness
    comp_dim = next(d for d in bm.dimensions if d.name == "completeness_score")
    assert comp_dim.building_value == 0.9
    assert comp_dim.better_than_peers is True


@pytest.mark.asyncio
async def test_benchmark_no_peers(db_session, admin_user):
    """A building alone in its peer group still gets a benchmark."""
    b1 = await _create_building(db_session, admin_user, canton="TI", construction_year=1990)
    await _create_risk_score(db_session, b1.id)
    await _create_snapshot(db_session, b1.id)
    await db_session.commit()

    bm = await benchmark_building(db_session, b1.id)
    assert bm.building_id == b1.id
    assert bm.peer_group.peer_count == 1  # only itself
    assert len(bm.dimensions) == 6


@pytest.mark.asyncio
async def test_benchmark_no_snapshot(db_session, admin_user):
    """Building with no snapshots has None for snapshot-derived dimensions."""
    b1 = await _create_building(db_session, admin_user)
    await db_session.commit()

    bm = await benchmark_building(db_session, b1.id)
    comp_dim = next(d for d in bm.dimensions if d.name == "completeness_score")
    assert comp_dim.building_value is None

    trust_dim = next(d for d in bm.dimensions if d.name == "trust_score")
    assert trust_dim.building_value is None

    grade_dim = next(d for d in bm.dimensions if d.name == "passport_grade")
    assert grade_dim.building_value is None


@pytest.mark.asyncio
async def test_benchmark_no_risk_score(db_session, admin_user):
    """Building without a risk score has None for risk dimension."""
    b1 = await _create_building(db_session, admin_user)
    await db_session.commit()

    bm = await benchmark_building(db_session, b1.id)
    risk_dim = next(d for d in bm.dimensions if d.name == "risk_score")
    assert risk_dim.building_value is None


@pytest.mark.asyncio
async def test_benchmark_not_found(db_session, admin_user):
    """Benchmarking a non-existent building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await benchmark_building(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_benchmark_diagnostic_and_sample_counts(db_session, admin_user):
    """Diagnostic and sample counts are correctly reflected."""
    b1 = await _create_building(db_session, admin_user)
    d1 = await _create_diagnostic(db_session, b1.id)
    d2 = await _create_diagnostic(db_session, b1.id, diagnostic_type="pcb")
    await _create_sample(db_session, d1.id, sample_number="S-001")
    await _create_sample(db_session, d1.id, sample_number="S-002")
    await _create_sample(db_session, d2.id, sample_number="S-003")
    await db_session.commit()

    bm = await benchmark_building(db_session, b1.id)
    diag_dim = next(d for d in bm.dimensions if d.name == "diagnostic_count")
    assert diag_dim.building_value == 2.0

    sample_dim = next(d for d in bm.dimensions if d.name == "sample_count")
    assert sample_dim.building_value == 3.0


@pytest.mark.asyncio
async def test_percentile_ranking(db_session, admin_user):
    """Percentile correctly ranks buildings among peers."""
    buildings = []
    for i in range(5):
        b = await _create_building(db_session, admin_user, construction_year=1975)
        await _create_snapshot(db_session, b.id, completeness_score=0.2 * (i + 1), overall_trust=0.5)
        buildings.append(b)
    await db_session.commit()

    # Last building has highest completeness (1.0)
    bm = await benchmark_building(db_session, buildings[4].id)
    comp_dim = next(d for d in bm.dimensions if d.name == "completeness_score")
    assert comp_dim.percentile is not None
    assert comp_dim.percentile >= 80.0  # Should be in top percentile

    # First building has lowest completeness (0.2)
    bm_low = await benchmark_building(db_session, buildings[0].id)
    comp_low = next(d for d in bm_low.dimensions if d.name == "completeness_score")
    assert comp_low.percentile is not None
    assert comp_low.percentile <= 20.0


# ── Compare Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compare_buildings(db_session, admin_user):
    """Compare multiple buildings returns best/worst."""
    # Same peer group so percentiles differ
    b1 = await _create_building(db_session, admin_user, construction_year=1975)
    b2 = await _create_building(db_session, admin_user, construction_year=1978)

    await _create_snapshot(db_session, b1.id, completeness_score=0.9, overall_trust=0.9, passport_grade="A")
    await _create_snapshot(db_session, b2.id, completeness_score=0.2, overall_trust=0.2, passport_grade="E")
    await _create_risk_score(
        db_session,
        b1.id,
        asbestos_probability=0.1,
        pcb_probability=0.1,
        lead_probability=0.1,
        hap_probability=0.1,
        radon_probability=0.1,
    )
    await _create_risk_score(
        db_session,
        b2.id,
        asbestos_probability=0.9,
        pcb_probability=0.9,
        lead_probability=0.9,
        hap_probability=0.9,
        radon_probability=0.9,
    )
    await db_session.commit()

    comparison = await compare_buildings_benchmark(db_session, [b1.id, b2.id])
    assert len(comparison.buildings) == 2
    assert comparison.best_building_id is not None
    assert comparison.worst_building_id is not None
    assert comparison.best_building_id != comparison.worst_building_id


@pytest.mark.asyncio
async def test_compare_single_building(db_session, admin_user):
    """Comparing a single building still works."""
    b1 = await _create_building(db_session, admin_user)
    await db_session.commit()

    comparison = await compare_buildings_benchmark(db_session, [b1.id])
    assert len(comparison.buildings) == 1


# ── Canton Benchmarks Tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_canton_benchmarks_aggregation(db_session, admin_user):
    """Canton benchmarks aggregate stats correctly."""
    # VD buildings
    b1 = await _create_building(db_session, admin_user, canton="VD")
    b2 = await _create_building(db_session, admin_user, canton="VD")
    # GE building
    b3 = await _create_building(db_session, admin_user, canton="GE")

    await _create_risk_score(
        db_session,
        b1.id,
        asbestos_probability=0.4,
        pcb_probability=0.4,
        lead_probability=0.4,
        hap_probability=0.4,
        radon_probability=0.4,
    )
    await _create_risk_score(
        db_session,
        b2.id,
        asbestos_probability=0.6,
        pcb_probability=0.6,
        lead_probability=0.6,
        hap_probability=0.6,
        radon_probability=0.6,
    )
    await _create_risk_score(
        db_session,
        b3.id,
        asbestos_probability=0.2,
        pcb_probability=0.2,
        lead_probability=0.2,
        hap_probability=0.2,
        radon_probability=0.2,
    )

    await _create_snapshot(db_session, b1.id, completeness_score=0.8, overall_trust=0.7, passport_grade="B")
    await _create_snapshot(db_session, b2.id, completeness_score=0.6, overall_trust=0.5, passport_grade="C")
    await _create_snapshot(db_session, b3.id, completeness_score=0.9, overall_trust=0.9, passport_grade="A")
    await db_session.commit()

    cantons = await get_canton_benchmarks(db_session)
    assert len(cantons) == 2

    vd = next(c for c in cantons if c.canton == "VD")
    assert vd.building_count == 2
    assert vd.avg_risk_score is not None
    assert vd.avg_completeness is not None
    assert vd.avg_trust is not None

    ge = next(c for c in cantons if c.canton == "GE")
    assert ge.building_count == 1
    assert ge.avg_risk_score is not None


@pytest.mark.asyncio
async def test_canton_benchmarks_no_data(db_session, admin_user):
    """Canton with buildings but no scores returns Nones."""
    await _create_building(db_session, admin_user, canton="VS")
    await db_session.commit()

    cantons = await get_canton_benchmarks(db_session)
    vs = next(c for c in cantons if c.canton == "VS")
    assert vs.building_count == 1
    assert vs.avg_risk_score is None
    assert vs.avg_completeness is None


@pytest.mark.asyncio
async def test_canton_benchmarks_grade_distribution(db_session, admin_user):
    """Grade distribution counts grades correctly."""
    b1 = await _create_building(db_session, admin_user, canton="VD")
    b2 = await _create_building(db_session, admin_user, canton="VD")
    b3 = await _create_building(db_session, admin_user, canton="VD")

    await _create_snapshot(db_session, b1.id, passport_grade="A")
    await _create_snapshot(db_session, b2.id, passport_grade="A")
    await _create_snapshot(db_session, b3.id, passport_grade="C")
    await db_session.commit()

    cantons = await get_canton_benchmarks(db_session)
    vd = next(c for c in cantons if c.canton == "VD")
    assert vd.grade_distribution.get("A", 0) == 2
    assert vd.grade_distribution.get("C", 0) == 1


# ── API Endpoint Tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_benchmark_success(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/benchmark returns 200."""
    b = await _create_building(db_session, admin_user)
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{b.id}/benchmark", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(b.id)
    assert "dimensions" in data
    assert "peer_group" in data


@pytest.mark.asyncio
async def test_api_benchmark_not_found(client, auth_headers):
    """GET /buildings/{id}/benchmark returns 404 for missing building."""
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/benchmark", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_peer_group_success(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/peer-group returns 200."""
    b = await _create_building(db_session, admin_user)
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{b.id}/peer-group", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "criteria" in data
    assert "peer_count" in data


@pytest.mark.asyncio
async def test_api_peer_group_not_found(client, auth_headers):
    """GET /buildings/{id}/peer-group returns 404 for missing building."""
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/peer-group", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_compare_success(client, db_session, admin_user, auth_headers):
    """POST /buildings/benchmark/compare returns 200."""
    b1 = await _create_building(db_session, admin_user)
    b2 = await _create_building(db_session, admin_user, canton="GE")
    await db_session.commit()

    resp = await client.post(
        "/api/v1/buildings/benchmark/compare",
        json={"building_ids": [str(b1.id), str(b2.id)]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["buildings"]) == 2


@pytest.mark.asyncio
async def test_api_canton_benchmarks(client, db_session, admin_user, auth_headers):
    """GET /benchmarks/cantons returns 200."""
    await _create_building(db_session, admin_user, canton="VD")
    await db_session.commit()

    resp = await client.get("/api/v1/benchmarks/cantons", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
