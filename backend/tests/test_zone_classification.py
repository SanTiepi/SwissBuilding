"""
Tests for zone classification service and API.

Covers: classify_zones, get_zone_hierarchy, identify_boundary_zones,
get_zone_transition_history — service layer + HTTP endpoints.
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.field_observation import FieldObservation
from app.models.intervention import Intervention
from app.models.material import Material
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.zone_classification import ContaminationStatus
from app.services.zone_classification_service import (
    _classify_zone_status,
    _worst_status,
    classify_zones,
    get_zone_hierarchy,
    get_zone_transition_history,
    identify_boundary_zones,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_zone(building_id, name="Zone A", zone_type="room", floor_number=0, parent_zone_id=None):
    return Zone(
        id=uuid.uuid4(),
        building_id=building_id,
        name=name,
        zone_type=zone_type,
        floor_number=floor_number,
        parent_zone_id=parent_zone_id,
        created_at=datetime.now(UTC),
    )


def _make_element(zone_id, name="Wall"):
    return BuildingElement(
        id=uuid.uuid4(),
        zone_id=zone_id,
        element_type="wall",
        name=name,
        created_at=datetime.now(UTC),
    )


def _make_material(
    element_id, contains_pollutant=False, pollutant_type=None, pollutant_confirmed=False, sample_id=None
):
    return Material(
        id=uuid.uuid4(),
        element_id=element_id,
        material_type="coating",
        name="Test Material",
        contains_pollutant=contains_pollutant,
        pollutant_type=pollutant_type,
        pollutant_confirmed=pollutant_confirmed,
        sample_id=sample_id,
        created_at=datetime.now(UTC),
    )


def _make_diagnostic(building_id, status="completed"):
    return Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="asbestos",
        status=status,
        created_at=datetime.now(UTC),
    )


def _make_sample(diagnostic_id, threshold_exceeded=False, risk_level="low", pollutant_type="asbestos"):
    return Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic_id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        threshold_exceeded=threshold_exceeded,
        risk_level=risk_level,
        created_at=datetime.now(UTC),
    )


def _make_intervention(building_id, intervention_type="remediation", status="completed", zones_affected=None):
    return Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type=intervention_type,
        title="Test intervention",
        status=status,
        zones_affected=zones_affected,
        created_at=datetime.now(UTC),
    )


def _make_observation(building_id, zone_id, observation_type="contamination", severity="warning", observer_id=None):
    return FieldObservation(
        id=uuid.uuid4(),
        building_id=building_id,
        zone_id=zone_id,
        observer_id=observer_id or uuid.uuid4(),
        observation_type=observation_type,
        severity=severity,
        title="Test observation",
        created_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Unit tests -_worst_status
# ---------------------------------------------------------------------------


class TestWorstStatus:
    def test_same_status(self):
        assert _worst_status(ContaminationStatus.clean, ContaminationStatus.clean) == ContaminationStatus.clean

    def test_clean_vs_confirmed_high(self):
        assert (
            _worst_status(ContaminationStatus.clean, ContaminationStatus.confirmed_high)
            == ContaminationStatus.confirmed_high
        )

    def test_suspected_vs_confirmed_low(self):
        assert (
            _worst_status(ContaminationStatus.suspected, ContaminationStatus.confirmed_low)
            == ContaminationStatus.confirmed_low
        )

    def test_remediated_vs_under_monitoring(self):
        assert (
            _worst_status(ContaminationStatus.remediated, ContaminationStatus.under_monitoring)
            == ContaminationStatus.under_monitoring
        )


# ---------------------------------------------------------------------------
# Unit tests -_classify_zone_status
# ---------------------------------------------------------------------------


class TestClassifyZoneStatus:
    def test_clean_zone_no_data(self):
        status, pollutants, sc, tc = _classify_zone_status([], [], [], [])
        assert status == ContaminationStatus.clean
        assert pollutants == []
        assert sc == 0
        assert tc == 0

    def test_suspected_from_material(self):
        elem_id = uuid.uuid4()
        mat = _make_material(elem_id, contains_pollutant=True, pollutant_type="asbestos", pollutant_confirmed=False)
        status, pollutants, _, _ = _classify_zone_status([mat], [], [], [])
        assert status == ContaminationStatus.suspected
        assert "asbestos" in pollutants

    def test_confirmed_low_from_sample(self):
        diag_id = uuid.uuid4()
        sample = _make_sample(diag_id, threshold_exceeded=True, risk_level="low")
        status, _, _, tc = _classify_zone_status([], [sample], [], [])
        assert status == ContaminationStatus.confirmed_low
        assert tc == 1

    def test_confirmed_high_from_sample(self):
        diag_id = uuid.uuid4()
        sample = _make_sample(diag_id, threshold_exceeded=True, risk_level="high")
        status, _, _, _ = _classify_zone_status([], [sample], [], [])
        assert status == ContaminationStatus.confirmed_high

    def test_confirmed_low_from_confirmed_material(self):
        elem_id = uuid.uuid4()
        mat = _make_material(elem_id, contains_pollutant=True, pollutant_type="pcb", pollutant_confirmed=True)
        status, pollutants, _, _ = _classify_zone_status([mat], [], [], [])
        assert status == ContaminationStatus.confirmed_low
        assert "pcb" in pollutants

    def test_remediated_after_completed_remediation(self):
        building_id = uuid.uuid4()
        zone_id = uuid.uuid4()
        intervention = _make_intervention(building_id, status="completed", zones_affected=[str(zone_id)])
        status, _, _, _ = _classify_zone_status([], [], [intervention], [])
        assert status == ContaminationStatus.remediated

    def test_under_monitoring_during_remediation(self):
        building_id = uuid.uuid4()
        zone_id = uuid.uuid4()
        intervention = _make_intervention(building_id, status="in_progress", zones_affected=[str(zone_id)])
        status, _, _, _ = _classify_zone_status([], [], [intervention], [])
        assert status == ContaminationStatus.under_monitoring

    def test_suspected_from_field_observation(self):
        building_id = uuid.uuid4()
        zone_id = uuid.uuid4()
        obs = _make_observation(building_id, zone_id, observation_type="contamination", severity="warning")
        status, _, _, _ = _classify_zone_status([], [], [], [obs])
        assert status == ContaminationStatus.suspected


# ---------------------------------------------------------------------------
# Integration tests -classify_zones (service)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_zones_empty_building(db_session, sample_building):
    result = await classify_zones(db_session, sample_building.id)
    assert result.building_id == sample_building.id
    assert result.total_zones == 0
    assert result.classified_zones == []


@pytest.mark.asyncio
async def test_classify_zones_clean_zone(db_session, sample_building):
    zone = _make_zone(sample_building.id, name="Clean Room")
    db_session.add(zone)
    await db_session.commit()

    result = await classify_zones(db_session, sample_building.id)
    assert result.total_zones == 1
    assert result.classified_zones[0].contamination_status == ContaminationStatus.clean
    assert result.summary["clean"] == 1


@pytest.mark.asyncio
async def test_classify_zones_suspected_material(db_session, sample_building):
    zone = _make_zone(sample_building.id)
    db_session.add(zone)
    await db_session.flush()

    element = _make_element(zone.id)
    db_session.add(element)
    await db_session.flush()

    material = _make_material(element.id, contains_pollutant=True, pollutant_type="asbestos")
    db_session.add(material)
    await db_session.commit()

    result = await classify_zones(db_session, sample_building.id)
    assert result.classified_zones[0].contamination_status == ContaminationStatus.suspected
    assert "asbestos" in result.classified_zones[0].pollutants_found


@pytest.mark.asyncio
async def test_classify_zones_confirmed_high(db_session, sample_building):
    zone = _make_zone(sample_building.id)
    db_session.add(zone)
    await db_session.flush()

    element = _make_element(zone.id)
    db_session.add(element)
    await db_session.flush()

    diagnostic = _make_diagnostic(sample_building.id)
    db_session.add(diagnostic)
    await db_session.flush()

    sample = _make_sample(diagnostic.id, threshold_exceeded=True, risk_level="critical")
    db_session.add(sample)
    await db_session.flush()

    material = _make_material(element.id, contains_pollutant=True, pollutant_type="asbestos", sample_id=sample.id)
    db_session.add(material)
    await db_session.commit()

    result = await classify_zones(db_session, sample_building.id)
    assert result.classified_zones[0].contamination_status == ContaminationStatus.confirmed_high


# ---------------------------------------------------------------------------
# Integration tests -get_zone_hierarchy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zone_hierarchy_empty(db_session, sample_building):
    result = await get_zone_hierarchy(db_session, sample_building.id)
    assert result.building_status == ContaminationStatus.clean
    assert result.tree == []
    assert result.floor_summaries == []


@pytest.mark.asyncio
async def test_zone_hierarchy_rollup(db_session, sample_building):
    parent = _make_zone(sample_building.id, name="Floor 1", zone_type="floor", floor_number=1)
    db_session.add(parent)
    await db_session.flush()

    child = _make_zone(sample_building.id, name="Room 101", zone_type="room", floor_number=1, parent_zone_id=parent.id)
    db_session.add(child)
    await db_session.flush()

    # Add contaminated material to child
    element = _make_element(child.id)
    db_session.add(element)
    await db_session.flush()

    material = _make_material(element.id, contains_pollutant=True, pollutant_type="lead", pollutant_confirmed=True)
    db_session.add(material)
    await db_session.commit()

    result = await get_zone_hierarchy(db_session, sample_building.id)
    assert result.building_status == ContaminationStatus.confirmed_low

    # Parent should roll up child's status
    assert len(result.tree) == 1
    parent_node = result.tree[0]
    assert parent_node.own_status == ContaminationStatus.clean
    assert parent_node.rolled_up_status == ContaminationStatus.confirmed_low
    assert len(parent_node.children) == 1
    assert parent_node.children[0].own_status == ContaminationStatus.confirmed_low


@pytest.mark.asyncio
async def test_zone_hierarchy_floor_summaries(db_session, sample_building):
    z1 = _make_zone(sample_building.id, name="Room A", floor_number=0)
    z2 = _make_zone(sample_building.id, name="Room B", floor_number=1)
    db_session.add_all([z1, z2])
    await db_session.commit()

    result = await get_zone_hierarchy(db_session, sample_building.id)
    assert len(result.floor_summaries) == 2
    assert result.floor_summaries[0].floor_number == 0
    assert result.floor_summaries[1].floor_number == 1


# ---------------------------------------------------------------------------
# Integration tests -identify_boundary_zones
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_boundary_zones_no_contamination(db_session, sample_building):
    zone = _make_zone(sample_building.id)
    db_session.add(zone)
    await db_session.commit()

    result = await identify_boundary_zones(db_session, sample_building.id)
    assert result.total_boundary_zones == 0


@pytest.mark.asyncio
async def test_boundary_zones_sibling_detection(db_session, sample_building):
    parent = _make_zone(sample_building.id, name="Floor 1", zone_type="floor", floor_number=1)
    db_session.add(parent)
    await db_session.flush()

    contaminated = _make_zone(
        sample_building.id, name="Room A", zone_type="room", floor_number=1, parent_zone_id=parent.id
    )
    clean = _make_zone(sample_building.id, name="Room B", zone_type="room", floor_number=1, parent_zone_id=parent.id)
    db_session.add_all([contaminated, clean])
    await db_session.flush()

    # Make Room A contaminated
    element = _make_element(contaminated.id)
    db_session.add(element)
    await db_session.flush()

    diag = _make_diagnostic(sample_building.id)
    db_session.add(diag)
    await db_session.flush()

    sample = _make_sample(diag.id, threshold_exceeded=True, risk_level="high")
    db_session.add(sample)
    await db_session.flush()

    mat = _make_material(element.id, contains_pollutant=True, pollutant_type="asbestos", sample_id=sample.id)
    db_session.add(mat)
    await db_session.commit()

    result = await identify_boundary_zones(db_session, sample_building.id)
    # Clean Room B should be identified as boundary
    boundary_ids = {bz.zone_id for bz in result.boundary_zones}
    assert clean.id in boundary_ids
    # Should recommend containment measures
    clean_boundary = next(bz for bz in result.boundary_zones if bz.zone_id == clean.id)
    assert "containment_barrier" in clean_boundary.recommended_measures


@pytest.mark.asyncio
async def test_boundary_zones_adjacent_floor(db_session, sample_building):
    floor0 = _make_zone(sample_building.id, name="Room F0", zone_type="room", floor_number=0)
    floor1 = _make_zone(sample_building.id, name="Room F1", zone_type="room", floor_number=1)
    db_session.add_all([floor0, floor1])
    await db_session.flush()

    # Contaminate floor0
    element = _make_element(floor0.id)
    db_session.add(element)
    await db_session.flush()

    diag = _make_diagnostic(sample_building.id)
    db_session.add(diag)
    await db_session.flush()

    sample = _make_sample(diag.id, threshold_exceeded=True, risk_level="low")
    db_session.add(sample)
    await db_session.flush()

    mat = _make_material(element.id, contains_pollutant=True, sample_id=sample.id)
    db_session.add(mat)
    await db_session.commit()

    result = await identify_boundary_zones(db_session, sample_building.id)
    boundary_ids = {bz.zone_id for bz in result.boundary_zones}
    assert floor1.id in boundary_ids


# ---------------------------------------------------------------------------
# Integration tests -get_zone_transition_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transition_history_clean_zone(db_session, sample_building):
    zone = _make_zone(sample_building.id)
    db_session.add(zone)
    await db_session.commit()

    result = await get_zone_transition_history(db_session, sample_building.id)
    assert len(result.zone_histories) == 1
    history = result.zone_histories[0]
    assert history.current_status == ContaminationStatus.clean
    assert len(history.transitions) >= 1
    assert history.transitions[0].to_status == ContaminationStatus.clean
    assert history.transitions[0].reason == "zone_created"


@pytest.mark.asyncio
async def test_transition_history_with_contamination(db_session, sample_building):
    zone = _make_zone(sample_building.id)
    db_session.add(zone)
    await db_session.flush()

    element = _make_element(zone.id)
    db_session.add(element)
    await db_session.flush()

    # Add suspected material
    mat = _make_material(element.id, contains_pollutant=True, pollutant_type="pcb")
    db_session.add(mat)
    await db_session.flush()

    # Add confirming sample
    diag = _make_diagnostic(sample_building.id)
    db_session.add(diag)
    await db_session.flush()

    sample = _make_sample(diag.id, threshold_exceeded=True, risk_level="low", pollutant_type="pcb")
    db_session.add(sample)
    await db_session.flush()

    mat2 = _make_material(
        element.id, contains_pollutant=True, pollutant_type="pcb", pollutant_confirmed=True, sample_id=sample.id
    )
    db_session.add(mat2)
    await db_session.commit()

    result = await get_zone_transition_history(db_session, sample_building.id)
    history = result.zone_histories[0]
    # Should have: zone_created -> suspected -> confirmed
    assert len(history.transitions) >= 2
    statuses = [t.to_status for t in history.transitions]
    assert ContaminationStatus.clean in statuses
    assert ContaminationStatus.suspected in statuses or ContaminationStatus.confirmed_low in statuses


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_classify_zones(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/zone-classification", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert data["total_zones"] == 0


@pytest.mark.asyncio
async def test_api_classify_zones_building_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake_id}/zone-classification", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_zone_hierarchy(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/zone-hierarchy", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_status"] == "clean"


@pytest.mark.asyncio
async def test_api_boundary_zones(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/boundary-zones", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_boundary_zones"] == 0


@pytest.mark.asyncio
async def test_api_zone_transitions(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/zone-transitions", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_unauthenticated(client, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/zone-classification")
    assert resp.status_code in (401, 403)
