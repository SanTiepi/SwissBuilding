"""Tests for the Spatial Risk Mapping service and API."""

import uuid

import pytest

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.material import Material
from app.models.sample import Sample
from app.models.zone import Zone
from app.services.spatial_risk_mapping_service import (
    get_building_risk_map,
    get_floor_risk_profile,
    get_risk_propagation_analysis,
    get_spatial_coverage_gaps,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def building(db_session, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Spatial 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def zones_with_hierarchy(db_session, building, admin_user):
    """Create a parent zone (floor 1) with two child zones."""
    parent = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="floor",
        name="Etage 1",
        floor_number=1,
        created_by=admin_user.id,
    )
    db_session.add(parent)
    await db_session.flush()

    child1 = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        parent_zone_id=parent.id,
        zone_type="room",
        name="Bureau 101",
        floor_number=1,
        surface_area_m2=20.0,
        created_by=admin_user.id,
    )
    child2 = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        parent_zone_id=parent.id,
        zone_type="room",
        name="Bureau 102",
        floor_number=1,
        surface_area_m2=25.0,
        created_by=admin_user.id,
    )
    db_session.add_all([child1, child2])
    await db_session.commit()
    for z in [parent, child1, child2]:
        await db_session.refresh(z)
    return parent, child1, child2


@pytest.fixture
async def zone_floor0(db_session, building, admin_user):
    """A single zone on floor 0 with no samples (coverage gap)."""
    z = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="room",
        name="Hall",
        floor_number=0,
        created_by=admin_user.id,
    )
    db_session.add(z)
    await db_session.commit()
    await db_session.refresh(z)
    return z


@pytest.fixture
async def diagnostic(db_session, building, admin_user):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest.fixture
async def samples_in_zones(db_session, diagnostic, zones_with_hierarchy):
    """Samples matched to child zones by location_floor containing zone name."""
    _parent, _child1, _child2 = zones_with_hierarchy

    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic.id,
        sample_number="S-001",
        location_floor="Bureau 101",
        pollutant_type="asbestos",
        risk_level="high",
        concentration=5.0,
        unit="%",
        threshold_exceeded=True,
    )
    s2 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic.id,
        sample_number="S-002",
        location_floor="Bureau 102",
        pollutant_type="pcb",
        risk_level="low",
        concentration=20.0,
        unit="mg/kg",
        threshold_exceeded=False,
    )
    s3 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic.id,
        sample_number="S-003",
        location_floor="Bureau 101",
        pollutant_type="lead",
        risk_level="medium",
        concentration=3000.0,
        unit="mg/kg",
        threshold_exceeded=False,
    )
    db_session.add_all([s1, s2, s3])
    await db_session.commit()
    return s1, s2, s3


@pytest.fixture
async def material_pollutant(db_session, zones_with_hierarchy, admin_user):
    """A material with confirmed pollutant on child1's element."""
    _parent, child1, _child2 = zones_with_hierarchy
    elem = BuildingElement(
        id=uuid.uuid4(),
        zone_id=child1.id,
        element_type="pipe",
        name="Calorifuge",
        created_by=admin_user.id,
    )
    db_session.add(elem)
    await db_session.flush()

    mat = Material(
        id=uuid.uuid4(),
        element_id=elem.id,
        material_type="insulation",
        name="Flocage amiante",
        contains_pollutant=True,
        pollutant_type="asbestos",
        pollutant_confirmed=True,
        created_by=admin_user.id,
    )
    db_session.add(mat)
    await db_session.commit()
    return mat


# ---------------------------------------------------------------------------
# FN1: get_building_risk_map
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_risk_map_empty_building(db_session, building):
    """Building with no zones returns empty risk map."""
    result = await get_building_risk_map(db_session, building.id)
    assert result.building_id == building.id
    assert result.total_zones == 0
    assert result.zones == []
    assert result.overall_risk_score == 0.0


@pytest.mark.asyncio
async def test_risk_map_zones_no_samples(db_session, building, zones_with_hierarchy):
    """Zones without samples → green, score 0."""
    result = await get_building_risk_map(db_session, building.id)
    assert result.total_zones == 3
    assert result.zones_at_risk == 0
    for z in result.zones:
        assert z.composite_risk_score == 0.0
        assert z.color_tier == "green"
        assert z.sample_density == 0


@pytest.mark.asyncio
async def test_risk_map_with_samples(db_session, building, zones_with_hierarchy, diagnostic, samples_in_zones):
    """Zones with high-risk samples get elevated scores and correct color tiers."""
    result = await get_building_risk_map(db_session, building.id)
    assert result.total_zones == 3
    assert result.zones_at_risk >= 1
    assert result.overall_risk_score > 0.0

    # Find the zone with asbestos (Bureau 101 matched)
    zone_map = {z.zone_name: z for z in result.zones}
    bureau101 = zone_map["Bureau 101"]
    assert bureau101.composite_risk_score >= 0.75  # threshold_exceeded
    assert bureau101.color_tier in ("orange", "red")
    assert bureau101.dominant_pollutant is not None
    assert bureau101.sample_density >= 2  # s1 + s3 matched


@pytest.mark.asyncio
async def test_risk_map_with_materials(db_session, building, zones_with_hierarchy, material_pollutant):
    """Materials with confirmed pollutants contribute to zone risk."""
    result = await get_building_risk_map(db_session, building.id)
    zone_map = {z.zone_name: z for z in result.zones}
    bureau101 = zone_map["Bureau 101"]
    assert bureau101.composite_risk_score >= 0.5
    assert "asbestos" in bureau101.pollutant_types


@pytest.mark.asyncio
async def test_risk_map_building_not_found(db_session):
    """Non-existent building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await get_building_risk_map(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# FN2: get_floor_risk_profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_floor_profile_empty_floor(db_session, building, zones_with_hierarchy):
    """Floor with zones but no samples → unknown status, 0% coverage."""
    result = await get_floor_risk_profile(db_session, building.id, floor=1)
    assert result.floor_number == 1
    assert len(result.zones) == 3  # parent + 2 children
    assert result.coverage_percentage == 0.0
    assert result.unknown_zones == 3


@pytest.mark.asyncio
async def test_floor_profile_with_samples(db_session, building, zones_with_hierarchy, diagnostic, samples_in_zones):
    """Floor with samples → pollutant distribution, safe/restricted areas."""
    result = await get_floor_risk_profile(db_session, building.id, floor=1)
    assert result.floor_number == 1
    assert len(result.zones) == 3
    assert result.coverage_percentage > 0.0
    assert result.restricted_zones >= 1
    assert len(result.pollutant_distribution) >= 1

    # Check pollutant distribution
    pt_map = {p.pollutant_type: p for p in result.pollutant_distribution}
    assert "asbestos" in pt_map
    assert pt_map["asbestos"].sample_count >= 1


@pytest.mark.asyncio
async def test_floor_profile_nonexistent_floor(db_session, building, zones_with_hierarchy):
    """Floor with no zones → empty result."""
    result = await get_floor_risk_profile(db_session, building.id, floor=99)
    assert result.floor_number == 99
    assert len(result.zones) == 0
    assert result.coverage_percentage == 0.0


@pytest.mark.asyncio
async def test_floor_profile_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await get_floor_risk_profile(db_session, uuid.uuid4(), floor=0)


# ---------------------------------------------------------------------------
# FN3: get_risk_propagation_analysis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_propagation_no_risk(db_session, building, zones_with_hierarchy):
    """No pollutants → no propagation edges, all scores 0."""
    result = await get_risk_propagation_analysis(db_session, building.id)
    assert result.total_zones == 3
    assert result.zones_with_elevated_risk == 0
    assert result.edges == []
    for z in result.zones:
        assert z.own_risk_score == 0.0
        assert z.propagated_risk_score == 0.0


@pytest.mark.asyncio
async def test_propagation_with_contaminated_child(
    db_session, building, zones_with_hierarchy, diagnostic, samples_in_zones
):
    """Child zone with asbestos propagates risk to parent and sibling via adjacency."""
    result = await get_risk_propagation_analysis(db_session, building.id)
    assert result.total_zones == 3
    assert len(result.edges) > 0

    zone_map = {z.zone_name: z for z in result.zones}

    # Bureau 101 has own risk from samples
    bureau101 = zone_map["Bureau 101"]
    assert bureau101.own_risk_score > 0.0

    # Parent (Etage 1) should receive propagated risk from children
    etage1 = zone_map["Etage 1"]
    assert etage1.propagated_risk_score > 0.0
    assert len(etage1.contributing_zones) > 0


@pytest.mark.asyncio
async def test_propagation_dampening(db_session, building, zones_with_hierarchy, diagnostic, samples_in_zones):
    """Propagated risk is dampened (less than source risk)."""
    result = await get_risk_propagation_analysis(db_session, building.id)

    for edge in result.edges:
        assert edge.propagated_risk_score < edge.source_risk_score
        assert edge.propagated_risk_score == pytest.approx(edge.source_risk_score * 0.4, abs=0.01)


@pytest.mark.asyncio
async def test_propagation_empty_building(db_session, building):
    """Building with no zones → empty propagation."""
    result = await get_risk_propagation_analysis(db_session, building.id)
    assert result.total_zones == 0
    assert result.edges == []


@pytest.mark.asyncio
async def test_propagation_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await get_risk_propagation_analysis(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# FN4: get_spatial_coverage_gaps
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coverage_gaps_no_zones(db_session, building):
    """Building with no zones → 0 coverage, no gaps."""
    result = await get_spatial_coverage_gaps(db_session, building.id)
    assert result.total_zones == 0
    assert result.overall_coverage_percentage == 0.0
    assert result.sampled_zones == 0


@pytest.mark.asyncio
async def test_coverage_gaps_unsampled_zones(db_session, building, zones_with_hierarchy):
    """Zones without samples are reported as gaps."""
    result = await get_spatial_coverage_gaps(db_session, building.id)
    assert result.total_zones == 3
    assert result.unsampled_zones == 3
    assert result.overall_coverage_percentage == 0.0

    unsampled_gaps = [g for g in result.gaps if g.gap_type == "unsampled_zone"]
    assert len(unsampled_gaps) == 3

    # No diagnostics gap
    no_diag = [g for g in result.gaps if g.gap_type == "no_diagnostics"]
    assert len(no_diag) == 1
    assert no_diag[0].priority == "critical"


@pytest.mark.asyncio
async def test_coverage_gaps_with_samples(db_session, building, zones_with_hierarchy, diagnostic, samples_in_zones):
    """Zones with samples reduce the gap count."""
    result = await get_spatial_coverage_gaps(db_session, building.id)
    assert result.total_zones == 3
    assert result.sampled_zones >= 2  # Bureau 101 and 102 have samples
    assert result.overall_coverage_percentage > 0.0
    assert result.unsampled_zones <= 1  # parent zone might be unsampled


@pytest.mark.asyncio
async def test_coverage_gaps_priority_ranking(db_session, building, zones_with_hierarchy):
    """Gaps are sorted by priority: critical first."""
    result = await get_spatial_coverage_gaps(db_session, building.id)
    priorities = [g.priority for g in result.gaps]
    # Critical should come before high/medium
    critical_indices = [i for i, p in enumerate(priorities) if p == "critical"]
    high_indices = [i for i, p in enumerate(priorities) if p == "high"]
    if critical_indices and high_indices:
        assert max(critical_indices) < min(high_indices)


@pytest.mark.asyncio
async def test_coverage_gaps_habitable_zones_high_priority(db_session, building, zones_with_hierarchy):
    """Habitable zones (room, floor) get high priority gaps."""
    result = await get_spatial_coverage_gaps(db_session, building.id)
    zone_gaps = [g for g in result.gaps if g.gap_type == "unsampled_zone"]
    for g in zone_gaps:
        if g.zone_type in ("room", "floor", "staircase"):
            assert g.priority == "high"


@pytest.mark.asyncio
async def test_coverage_gaps_floor_coverage(
    db_session, building, zones_with_hierarchy, zone_floor0, diagnostic, samples_in_zones
):
    """Floor coverage status is reported per floor."""
    result = await get_spatial_coverage_gaps(db_session, building.id)
    floor_map = {fc.floor_number: fc for fc in result.floor_coverage}

    assert 1 in floor_map
    assert 0 in floor_map

    # Floor 0 has no samples → 0% coverage
    assert floor_map[0].coverage_percentage == 0.0
    assert floor_map[0].total_zones == 1

    # Floor 1 has samples in at least 2 of 3 zones
    assert floor_map[1].coverage_percentage > 0.0


@pytest.mark.asyncio
async def test_coverage_gaps_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await get_spatial_coverage_gaps(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_risk_map(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/risk-map", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "zones" in data


@pytest.mark.asyncio
async def test_api_risk_map_404(client, auth_headers):
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/risk-map", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_floor_risk(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/floor-risk/0", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["floor_number"] == 0


@pytest.mark.asyncio
async def test_api_risk_propagation(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/risk-propagation", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_coverage_gaps(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/coverage-gaps", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "gaps" in data


@pytest.mark.asyncio
async def test_api_unauthenticated(client, sample_building):
    """Endpoints require authentication."""
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/risk-map")
    assert resp.status_code in (401, 403)
