"""Tests for field observations API — site visit capture and verification."""

import uuid
from datetime import UTC, datetime

import pytest

from app.models.building import Building
from app.models.field_observation import FieldObservation
from app.models.user import User
from app.models.zone import Zone


@pytest.fixture
async def building(db_session, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue du Champ 10",
        postal_code="1003",
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
async def zone(db_session, building, admin_user):
    z = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type="floor",
        name="1er étage",
        created_by=admin_user.id,
    )
    db_session.add(z)
    await db_session.commit()
    await db_session.refresh(z)
    return z


@pytest.fixture
async def observation(db_session, building, admin_user):
    obs = FieldObservation(
        id=uuid.uuid4(),
        building_id=building.id,
        observer_id=admin_user.id,
        observation_type="visual_inspection",
        severity="minor",
        title="Fissure mur est",
        description="Fissure visible sur le mur est du 2e étage",
        observed_at=datetime.now(UTC),
        status="draft",
    )
    db_session.add(obs)
    await db_session.commit()
    await db_session.refresh(obs)
    return obs


# --- CRUD Tests ---


@pytest.mark.asyncio
async def test_create_observation(client, auth_headers, building):
    payload = {
        "building_id": str(building.id),
        "observation_type": "visual_inspection",
        "severity": "minor",
        "title": "Dégât d'eau visible",
        "description": "Traces d'humidité au plafond",
    }
    resp = await client.post(f"/api/v1/buildings/{building.id}/field-observations", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Dégât d'eau visible"
    assert data["observation_type"] == "visual_inspection"
    assert data["severity"] == "minor"
    assert data["verified"] is False
    assert data["status"] == "draft"
    assert data["observer_name"] is not None


@pytest.mark.asyncio
async def test_create_observation_with_zone(client, auth_headers, building, zone):
    payload = {
        "building_id": str(building.id),
        "observation_type": "material_condition",
        "severity": "moderate",
        "title": "Revêtement dégradé",
        "zone_id": str(zone.id),
    }
    resp = await client.post(f"/api/v1/buildings/{building.id}/field-observations", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["zone_id"] == str(zone.id)


@pytest.mark.asyncio
async def test_create_observation_building_not_found(client, auth_headers):
    fake_id = uuid.uuid4()
    payload = {
        "building_id": str(fake_id),
        "observation_type": "general_note",
        "severity": "info",
        "title": "Test",
    }
    resp = await client.post(f"/api/v1/buildings/{fake_id}/field-observations", json=payload, headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_observations(client, auth_headers, building, observation):
    resp = await client.get(f"/api/v1/buildings/{building.id}/field-observations", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Fissure mur est"


@pytest.mark.asyncio
async def test_list_observations_empty(client, auth_headers, building):
    resp = await client.get(f"/api/v1/buildings/{building.id}/field-observations", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_get_observation(client, auth_headers, observation):
    resp = await client.get(f"/api/v1/field-observations/{observation.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(observation.id)
    assert resp.json()["title"] == "Fissure mur est"


@pytest.mark.asyncio
async def test_get_observation_not_found(client, auth_headers):
    resp = await client.get(f"/api/v1/field-observations/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_observation(client, auth_headers, observation):
    payload = {"title": "Fissure mur est (mise à jour)", "severity": "major"}
    resp = await client.put(f"/api/v1/field-observations/{observation.id}", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Fissure mur est (mise à jour)"
    assert data["severity"] == "major"


@pytest.mark.asyncio
async def test_update_observation_not_found(client, auth_headers):
    payload = {"title": "nope"}
    resp = await client.put(f"/api/v1/field-observations/{uuid.uuid4()}", json=payload, headers=auth_headers)
    assert resp.status_code == 404


# --- Verification Tests ---


@pytest.mark.asyncio
async def test_verify_observation(client, auth_headers, observation):
    payload = {"verified": True, "notes": "Confirmé sur site"}
    resp = await client.post(f"/api/v1/field-observations/{observation.id}/verify", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is True
    assert data["verified_by_id"] is not None
    assert data["verified_at"] is not None


@pytest.mark.asyncio
async def test_unverify_observation(client, auth_headers, observation, db_session):
    # First verify
    observation.verified = True
    observation.verified_by_id = (await db_session.get(User, observation.observer_id)).id
    observation.verified_at = datetime.now(UTC)
    await db_session.commit()

    # Then unverify
    payload = {"verified": False}
    resp = await client.post(f"/api/v1/field-observations/{observation.id}/verify", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["verified"] is False
    assert resp.json()["verified_by_id"] is None


@pytest.mark.asyncio
async def test_verify_observation_not_found(client, auth_headers):
    payload = {"verified": True}
    resp = await client.post(f"/api/v1/field-observations/{uuid.uuid4()}/verify", json=payload, headers=auth_headers)
    assert resp.status_code == 404


# --- Summary Tests ---


@pytest.mark.asyncio
async def test_summary_empty(client, auth_headers, building):
    resp = await client.get(f"/api/v1/buildings/{building.id}/field-observations/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_observations"] == 0
    assert data["by_type"] == {}
    assert data["by_severity"] == {}
    assert data["unverified_count"] == 0


@pytest.mark.asyncio
async def test_summary_with_observations(client, auth_headers, building, observation, db_session):
    # Add a second observation
    obs2 = FieldObservation(
        id=uuid.uuid4(),
        building_id=building.id,
        observer_id=observation.observer_id,
        observation_type="safety_hazard",
        severity="critical",
        title="Amiante exposé",
        observed_at=datetime.now(UTC),
        status="submitted",
    )
    db_session.add(obs2)
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{building.id}/field-observations/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_observations"] == 2
    assert data["by_type"]["visual_inspection"] == 1
    assert data["by_type"]["safety_hazard"] == 1
    assert data["by_severity"]["minor"] == 1
    assert data["by_severity"]["critical"] == 1
    assert data["unverified_count"] == 2


@pytest.mark.asyncio
async def test_summary_building_not_found(client, auth_headers):
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/field-observations/summary", headers=auth_headers)
    assert resp.status_code == 404


# --- Filter Tests ---


@pytest.mark.asyncio
async def test_filter_by_type(client, auth_headers, building, db_session, admin_user):
    for obs_type in ["visual_inspection", "safety_hazard", "visual_inspection"]:
        db_session.add(
            FieldObservation(
                id=uuid.uuid4(),
                building_id=building.id,
                observer_id=admin_user.id,
                observation_type=obs_type,
                severity="info",
                title=f"Obs {obs_type}",
                observed_at=datetime.now(UTC),
                status="draft",
            )
        )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{building.id}/field-observations",
        params={"observation_type": "visual_inspection"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


@pytest.mark.asyncio
async def test_filter_by_severity(client, auth_headers, building, db_session, admin_user):
    for sev in ["info", "critical", "critical"]:
        db_session.add(
            FieldObservation(
                id=uuid.uuid4(),
                building_id=building.id,
                observer_id=admin_user.id,
                observation_type="general_note",
                severity=sev,
                title=f"Obs {sev}",
                observed_at=datetime.now(UTC),
                status="draft",
            )
        )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{building.id}/field-observations",
        params={"severity": "critical"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


@pytest.mark.asyncio
async def test_filter_by_status(client, auth_headers, building, db_session, admin_user):
    for st in ["draft", "submitted", "submitted"]:
        db_session.add(
            FieldObservation(
                id=uuid.uuid4(),
                building_id=building.id,
                observer_id=admin_user.id,
                observation_type="general_note",
                severity="info",
                title=f"Obs {st}",
                observed_at=datetime.now(UTC),
                status=st,
            )
        )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{building.id}/field-observations",
        params={"status": "submitted"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


@pytest.mark.asyncio
async def test_filter_by_zone(client, auth_headers, building, zone, db_session, admin_user):
    db_session.add(
        FieldObservation(
            id=uuid.uuid4(),
            building_id=building.id,
            observer_id=admin_user.id,
            observation_type="visual_inspection",
            severity="info",
            title="In zone",
            zone_id=zone.id,
            observed_at=datetime.now(UTC),
            status="draft",
        )
    )
    db_session.add(
        FieldObservation(
            id=uuid.uuid4(),
            building_id=building.id,
            observer_id=admin_user.id,
            observation_type="visual_inspection",
            severity="info",
            title="No zone",
            observed_at=datetime.now(UTC),
            status="draft",
        )
    )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{building.id}/field-observations",
        params={"zone_id": str(zone.id)},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["title"] == "In zone"


# --- Pagination Tests ---


@pytest.mark.asyncio
async def test_pagination(client, auth_headers, building, db_session, admin_user):
    for i in range(5):
        db_session.add(
            FieldObservation(
                id=uuid.uuid4(),
                building_id=building.id,
                observer_id=admin_user.id,
                observation_type="general_note",
                severity="info",
                title=f"Obs {i}",
                observed_at=datetime.now(UTC),
                status="draft",
            )
        )
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/buildings/{building.id}/field-observations",
        params={"page": 1, "size": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["pages"] == 3


# --- Permission Tests ---


@pytest.mark.asyncio
async def test_create_observation_no_auth(client, building):
    payload = {
        "building_id": str(building.id),
        "observation_type": "general_note",
        "severity": "info",
        "title": "Test",
    }
    resp = await client.post(f"/api/v1/buildings/{building.id}/field-observations", json=payload)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_observations_no_auth(client, building):
    resp = await client.get(f"/api/v1/buildings/{building.id}/field-observations")
    assert resp.status_code == 403
