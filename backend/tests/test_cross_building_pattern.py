"""Tests for Cross-Building Pattern Detection Service and API."""

from __future__ import annotations

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.cross_building_pattern_service import (
    detect_patterns,
    find_similar_buildings,
    get_geographic_clusters,
    predict_undiscovered_pollutants,
)

# ── Helpers ────────────────────────────────────────────────────────


async def _create_org(db, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test Org",
        "type": "property_management",
    }
    defaults.update(kwargs)
    org = Organization(**defaults)
    db.add(org)
    await db.flush()
    return org


async def _create_user(db, org_id=None, **kwargs):
    from tests.conftest import _HASH_ADMIN

    defaults = {
        "id": uuid.uuid4(),
        "email": f"user-{uuid.uuid4().hex[:8]}@test.ch",
        "password_hash": _HASH_ADMIN,
        "first_name": "Test",
        "last_name": "User",
        "role": "admin",
        "is_active": True,
        "language": "fr",
        "organization_id": org_id,
    }
    defaults.update(kwargs)
    u = User(**defaults)
    db.add(u)
    await db.flush()
    return u


async def _create_building(db, created_by, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1975,
        "building_type": "residential",
        "created_by": created_by,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


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
        "sample_number": f"S-{uuid.uuid4().hex[:6]}",
        "pollutant_type": "asbestos",
        "threshold_exceeded": True,
        "risk_level": "high",
    }
    defaults.update(kwargs)
    s = Sample(**defaults)
    db.add(s)
    await db.flush()
    return s


async def _create_intervention(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "intervention_type": "removal",
        "title": "Test intervention",
        "status": "completed",
    }
    defaults.update(kwargs)
    iv = Intervention(**defaults)
    db.add(iv)
    await db.flush()
    return iv


# ── detect_patterns tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_detect_patterns_empty_org(db_session):
    """No buildings → empty result."""
    org = await _create_org(db_session)
    result = await detect_patterns(db_session, org.id)
    assert result.total_buildings_analyzed == 0
    assert result.patterns == []
    assert result.organization_id == org.id


@pytest.mark.asyncio
async def test_detect_patterns_systemic_pollutant(db_session):
    """Two 1970s buildings with asbestos → systemic pattern."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)

    b1 = await _create_building(db_session, user.id, construction_year=1972)
    b2 = await _create_building(db_session, user.id, construction_year=1978, address="Rue Test 2")

    d1 = await _create_diagnostic(db_session, b1.id)
    d2 = await _create_diagnostic(db_session, b2.id)
    await _create_sample(db_session, d1.id, pollutant_type="asbestos")
    await _create_sample(db_session, d2.id, pollutant_type="asbestos")
    await db_session.commit()

    result = await detect_patterns(db_session, org.id)
    assert result.total_buildings_analyzed == 2
    systemic = [p for p in result.patterns if p.pattern_type == "systemic_pollutant"]
    assert len(systemic) >= 1
    assert len(systemic[0].affected_buildings) == 2


@pytest.mark.asyncio
async def test_detect_patterns_no_systemic_different_decades(db_session):
    """Buildings from different decades with same pollutant → no systemic pattern."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)

    b1 = await _create_building(db_session, user.id, construction_year=1960)
    b2 = await _create_building(db_session, user.id, construction_year=1990, address="Rue Test 2")

    d1 = await _create_diagnostic(db_session, b1.id)
    d2 = await _create_diagnostic(db_session, b2.id)
    await _create_sample(db_session, d1.id, pollutant_type="asbestos")
    await _create_sample(db_session, d2.id, pollutant_type="asbestos")
    await db_session.commit()

    result = await detect_patterns(db_session, org.id)
    systemic = [p for p in result.patterns if p.pattern_type == "systemic_pollutant"]
    assert len(systemic) == 0


@pytest.mark.asyncio
async def test_detect_patterns_contractor_quality(db_session):
    """Same contractor with cancelled interventions across buildings → pattern."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)

    b1 = await _create_building(db_session, user.id)
    b2 = await _create_building(db_session, user.id, address="Rue Test 2")

    await _create_intervention(db_session, b1.id, contractor_name="BadCorp", status="cancelled")
    await _create_intervention(db_session, b2.id, contractor_name="BadCorp", status="cancelled")
    await db_session.commit()

    result = await detect_patterns(db_session, org.id)
    contractor = [p for p in result.patterns if p.pattern_type == "contractor_quality"]
    assert len(contractor) >= 1
    assert "BadCorp" in contractor[0].label


@pytest.mark.asyncio
async def test_detect_patterns_geographic_radon(db_session):
    """Two buildings in same postal code with radon → geographic pattern."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)

    b1 = await _create_building(db_session, user.id, postal_code="1260")
    b2 = await _create_building(db_session, user.id, postal_code="1260", address="Rue Test 2")

    d1 = await _create_diagnostic(db_session, b1.id, diagnostic_type="radon")
    d2 = await _create_diagnostic(db_session, b2.id, diagnostic_type="radon")
    await _create_sample(db_session, d1.id, pollutant_type="radon")
    await _create_sample(db_session, d2.id, pollutant_type="radon")
    await db_session.commit()

    result = await detect_patterns(db_session, org.id)
    geo = [p for p in result.patterns if p.pattern_type == "geographic"]
    assert len(geo) >= 1
    assert "1260" in geo[0].label


@pytest.mark.asyncio
async def test_detect_patterns_confidence_calculation(db_session):
    """Confidence = affected / group size."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)

    # 3 buildings in 1970s, 2 have asbestos → confidence = 2/3
    b1 = await _create_building(db_session, user.id, construction_year=1970)
    b2 = await _create_building(db_session, user.id, construction_year=1975, address="Rue 2")
    await _create_building(db_session, user.id, construction_year=1979, address="Rue 3")

    d1 = await _create_diagnostic(db_session, b1.id)
    d2 = await _create_diagnostic(db_session, b2.id)
    await _create_sample(db_session, d1.id, pollutant_type="asbestos")
    await _create_sample(db_session, d2.id, pollutant_type="asbestos")
    await db_session.commit()

    result = await detect_patterns(db_session, org.id)
    systemic = [p for p in result.patterns if p.pattern_type == "systemic_pollutant"]
    assert len(systemic) == 1
    assert abs(systemic[0].confidence - 2 / 3) < 0.01


# ── find_similar_buildings tests ──────────────────────────────────


@pytest.mark.asyncio
async def test_find_similar_buildings_same_canton_era(db_session, admin_user):
    """Buildings in same canton + era score higher."""
    ref = await _create_building(db_session, admin_user.id, canton="VD", construction_year=1975)
    sim = await _create_building(db_session, admin_user.id, canton="VD", construction_year=1972, address="Rue Sim")
    diff = await _create_building(db_session, admin_user.id, canton="GE", construction_year=2010, address="Rue Diff")
    await db_session.commit()

    result = await find_similar_buildings(db_session, ref.id)
    ids = [s.building_id for s in result.similar_buildings]
    assert sim.id in ids
    # sim should score higher than diff
    sim_entry = next(s for s in result.similar_buildings if s.building_id == sim.id)
    diff_entries = [s for s in result.similar_buildings if s.building_id == diff.id]
    if diff_entries:
        assert sim_entry.similarity_score >= diff_entries[0].similarity_score


@pytest.mark.asyncio
async def test_find_similar_buildings_not_found(db_session):
    """Non-existent building → ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await find_similar_buildings(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_find_similar_buildings_shared_pollutants(db_session, admin_user):
    """Shared pollutant profile increases similarity."""
    ref = await _create_building(db_session, admin_user.id, canton="VD", construction_year=1975)
    peer = await _create_building(db_session, admin_user.id, canton="VD", construction_year=1978, address="Rue Peer")

    d1 = await _create_diagnostic(db_session, ref.id)
    d2 = await _create_diagnostic(db_session, peer.id)
    await _create_sample(db_session, d1.id, pollutant_type="asbestos")
    await _create_sample(db_session, d2.id, pollutant_type="asbestos")
    await db_session.commit()

    result = await find_similar_buildings(db_session, ref.id)
    peer_entry = next(s for s in result.similar_buildings if s.building_id == peer.id)
    assert "shared_pollutants:asbestos" in peer_entry.shared_traits


@pytest.mark.asyncio
async def test_find_similar_buildings_same_type(db_session, admin_user):
    """Same building_type is a trait."""
    ref = await _create_building(db_session, admin_user.id, building_type="commercial", canton="VD")
    peer = await _create_building(db_session, admin_user.id, building_type="commercial", canton="VD", address="Rue P")
    await db_session.commit()

    result = await find_similar_buildings(db_session, ref.id)
    peer_entry = next(s for s in result.similar_buildings if s.building_id == peer.id)
    assert any("same_type" in t for t in peer_entry.shared_traits)


@pytest.mark.asyncio
async def test_find_similar_buildings_max_20(db_session, admin_user):
    """At most 20 similar buildings returned."""
    ref = await _create_building(db_session, admin_user.id, canton="VD")
    for i in range(25):
        await _create_building(db_session, admin_user.id, canton="VD", address=f"Rue {i}")
    await db_session.commit()

    result = await find_similar_buildings(db_session, ref.id)
    assert len(result.similar_buildings) <= 20


# ── get_geographic_clusters tests ─────────────────────────────────


@pytest.mark.asyncio
async def test_geographic_clusters_empty(db_session):
    """Org with no geo-buildings → empty clusters."""
    org = await _create_org(db_session)
    result = await get_geographic_clusters(db_session, org.id)
    assert result.clusters == []
    assert result.total_buildings == 0


@pytest.mark.asyncio
async def test_geographic_clusters_basic(db_session):
    """Two buildings with lat/lon in same postal code → one cluster."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)

    await _create_building(
        db_session,
        user.id,
        postal_code="1000",
        latitude=46.5197,
        longitude=6.6323,
    )
    await _create_building(
        db_session,
        user.id,
        postal_code="1000",
        latitude=46.5210,
        longitude=6.6350,
        address="Rue Cluster 2",
    )
    await db_session.commit()

    result = await get_geographic_clusters(db_session, org.id)
    assert len(result.clusters) == 1
    assert result.total_buildings == 2
    assert len(result.clusters[0].buildings) == 2
    assert result.clusters[0].center_lat is not None


@pytest.mark.asyncio
async def test_geographic_clusters_no_cluster_single_building(db_session):
    """Single building in a postal code → no cluster."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)

    await _create_building(db_session, user.id, postal_code="9999", latitude=47.0, longitude=8.0)
    await db_session.commit()

    result = await get_geographic_clusters(db_session, org.id)
    assert len(result.clusters) == 0


@pytest.mark.asyncio
async def test_geographic_clusters_risk_factor(db_session):
    """Cluster with dominant pollutant shows it as risk_factor."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)

    b1 = await _create_building(db_session, user.id, postal_code="1260", latitude=46.4, longitude=6.2)
    b2 = await _create_building(db_session, user.id, postal_code="1260", latitude=46.41, longitude=6.21, address="R2")

    d1 = await _create_diagnostic(db_session, b1.id, diagnostic_type="radon")
    d2 = await _create_diagnostic(db_session, b2.id, diagnostic_type="radon")
    await _create_sample(db_session, d1.id, pollutant_type="radon")
    await _create_sample(db_session, d2.id, pollutant_type="radon")
    await db_session.commit()

    result = await get_geographic_clusters(db_session, org.id)
    assert len(result.clusters) == 1
    assert result.clusters[0].risk_factor == "radon"


# ── predict_undiscovered_pollutants tests ─────────────────────────


@pytest.mark.asyncio
async def test_predict_undiscovered_not_found(db_session):
    """Non-existent building → ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await predict_undiscovered_pollutants(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_predict_undiscovered_basic(db_session, admin_user):
    """Peer building has PCB but ref untested → prediction."""
    ref = await _create_building(db_session, admin_user.id, canton="VD", construction_year=1975)
    peer = await _create_building(db_session, admin_user.id, canton="VD", construction_year=1972, address="Peer")

    # Peer has PCB
    d_peer = await _create_diagnostic(db_session, peer.id, diagnostic_type="pcb")
    await _create_sample(db_session, d_peer.id, pollutant_type="pcb")
    await db_session.commit()

    result = await predict_undiscovered_pollutants(db_session, ref.id)
    assert result.peer_buildings_used >= 1
    pcb_preds = [p for p in result.predictions if p.pollutant_type == "pcb"]
    assert len(pcb_preds) == 1
    assert pcb_preds[0].probability > 0


@pytest.mark.asyncio
async def test_predict_undiscovered_already_tested(db_session, admin_user):
    """Pollutant already tested on ref → not predicted."""
    ref = await _create_building(db_session, admin_user.id, canton="VD", construction_year=1975)
    peer = await _create_building(db_session, admin_user.id, canton="VD", construction_year=1972, address="Peer")

    # Both have asbestos tested
    d_ref = await _create_diagnostic(db_session, ref.id, diagnostic_type="asbestos")
    d_peer = await _create_diagnostic(db_session, peer.id, diagnostic_type="asbestos")
    await _create_sample(db_session, d_ref.id, pollutant_type="asbestos")
    await _create_sample(db_session, d_peer.id, pollutant_type="asbestos")
    await db_session.commit()

    result = await predict_undiscovered_pollutants(db_session, ref.id)
    asbestos_preds = [p for p in result.predictions if p.pollutant_type == "asbestos"]
    assert len(asbestos_preds) == 0


@pytest.mark.asyncio
async def test_predict_undiscovered_no_peers(db_session, admin_user):
    """No peers → no predictions."""
    ref = await _create_building(db_session, admin_user.id, canton="ZH", construction_year=2020)
    await db_session.commit()

    result = await predict_undiscovered_pollutants(db_session, ref.id)
    assert result.predictions == []
    assert result.peer_buildings_used == 0


@pytest.mark.asyncio
async def test_predict_undiscovered_sorted_by_probability(db_session, admin_user):
    """Predictions sorted by probability descending."""
    ref = await _create_building(db_session, admin_user.id, canton="VD", construction_year=1975)
    # 3 peers: 3 have lead, 1 has hap
    for i in range(3):
        p = await _create_building(
            db_session,
            admin_user.id,
            canton="VD",
            construction_year=1970 + i,
            address=f"Peer {i}",
        )
        d = await _create_diagnostic(db_session, p.id)
        await _create_sample(db_session, d.id, pollutant_type="lead")
        if i == 0:
            await _create_sample(db_session, d.id, pollutant_type="hap")
    await db_session.commit()

    result = await predict_undiscovered_pollutants(db_session, ref.id)
    probs = [p.probability for p in result.predictions]
    assert probs == sorted(probs, reverse=True)


# ── API endpoint tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_detect_patterns(client, db_session, admin_user, auth_headers):
    """GET /organizations/{org_id}/cross-building-patterns returns 200."""
    org = await _create_org(db_session)
    user = await _create_user(db_session, org_id=org.id)
    await _create_building(db_session, user.id)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/organizations/{org.id}/cross-building-patterns",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "patterns" in data
    assert data["total_buildings_analyzed"] >= 1


@pytest.mark.asyncio
async def test_api_similar_buildings(client, db_session, admin_user, auth_headers, sample_building):
    """GET /buildings/{id}/similar returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/similar",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "similar_buildings" in data
    assert data["reference_building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_similar_buildings_404(client, auth_headers):
    """GET /buildings/{bad_id}/similar returns 404."""
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/similar",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_geographic_clusters(client, db_session, admin_user, auth_headers):
    """GET /organizations/{org_id}/geographic-clusters returns 200."""
    org = await _create_org(db_session)
    resp = await client.get(
        f"/api/v1/organizations/{org.id}/geographic-clusters",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "clusters" in data


@pytest.mark.asyncio
async def test_api_undiscovered_pollutants(client, db_session, admin_user, auth_headers, sample_building):
    """GET /buildings/{id}/undiscovered-pollutants returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/undiscovered-pollutants",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "predictions" in data


@pytest.mark.asyncio
async def test_api_undiscovered_pollutants_404(client, auth_headers):
    """GET /buildings/{bad_id}/undiscovered-pollutants returns 404."""
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/undiscovered-pollutants",
        headers=auth_headers,
    )
    assert resp.status_code == 404
