import uuid

import pytest

from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.zone import Zone

PLAN_PAYLOAD = {
    "plan_type": "floor_plan",
    "title": "Ground floor plan",
    "file_path": "/plans/ground_floor.pdf",
    "file_name": "ground_floor.pdf",
}

ANNOTATION_PAYLOAD = {
    "annotation_type": "marker",
    "label": "Amiante detecte",
    "x": 0.5,
    "y": 0.3,
    "description": "Presence d'amiante dans le faux plafond",
    "color": "#FF0000",
    "icon": "warning",
}


def _url(building_id, plan_id, annotation_id=None):
    base = f"/api/v1/buildings/{building_id}/plans/{plan_id}/annotations"
    if annotation_id:
        return f"{base}/{annotation_id}"
    return base


@pytest.fixture
async def sample_plan(db_session, sample_building, admin_user):
    plan = TechnicalPlan(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        uploaded_by=admin_user.id,
        **PLAN_PAYLOAD,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


@pytest.fixture
async def sample_zone(db_session, sample_building, admin_user):
    zone = Zone(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        zone_type="room",
        name="Bureau 101",
        created_by=admin_user.id,
    )
    db_session.add(zone)
    await db_session.commit()
    await db_session.refresh(zone)
    return zone


@pytest.fixture
async def sample_sample(db_session, sample_building, admin_user):
    """Create a sample record for reference tests."""
    from app.models.diagnostic import Diagnostic

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(diag)
    await db_session.commit()

    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        material_category="insulation",
        location_detail="Faux plafond bureau 101",
    )
    db_session.add(sample)
    await db_session.commit()
    await db_session.refresh(sample)
    return sample


class TestCreateAnnotation:
    async def test_create_annotation(self, client, admin_user, auth_headers, sample_building, sample_plan):
        response = await client.post(
            _url(sample_building.id, sample_plan.id),
            json=ANNOTATION_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["annotation_type"] == "marker"
        assert data["label"] == "Amiante detecte"
        assert data["x"] == 0.5
        assert data["y"] == 0.3
        assert data["color"] == "#FF0000"
        assert data["building_id"] == str(sample_building.id)
        assert data["plan_id"] == str(sample_plan.id)
        assert data["created_by"] == str(admin_user.id)

    async def test_create_annotation_building_not_found(self, client, admin_user, auth_headers, sample_plan):
        fake_building = uuid.uuid4()
        response = await client.post(
            _url(fake_building, sample_plan.id),
            json=ANNOTATION_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_create_annotation_plan_not_found(self, client, admin_user, auth_headers, sample_building):
        fake_plan = uuid.uuid4()
        response = await client.post(
            _url(sample_building.id, fake_plan),
            json=ANNOTATION_PAYLOAD,
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListAnnotations:
    async def test_list_annotations(self, client, admin_user, auth_headers, sample_building, sample_plan):
        # Create two annotations
        await client.post(
            _url(sample_building.id, sample_plan.id),
            json=ANNOTATION_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            _url(sample_building.id, sample_plan.id),
            json={**ANNOTATION_PAYLOAD, "label": "PCB detecte", "annotation_type": "observation"},
            headers=auth_headers,
        )

        response = await client.get(
            _url(sample_building.id, sample_plan.id),
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_list_annotations_filter_by_type(
        self, client, admin_user, auth_headers, sample_building, sample_plan
    ):
        await client.post(
            _url(sample_building.id, sample_plan.id),
            json=ANNOTATION_PAYLOAD,
            headers=auth_headers,
        )
        await client.post(
            _url(sample_building.id, sample_plan.id),
            json={**ANNOTATION_PAYLOAD, "label": "Zone dangereuse", "annotation_type": "hazard_zone"},
            headers=auth_headers,
        )

        response = await client.get(
            _url(sample_building.id, sample_plan.id),
            params={"annotation_type": "hazard_zone"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["annotation_type"] == "hazard_zone"


class TestGetAnnotation:
    async def test_get_annotation(self, client, admin_user, auth_headers, sample_building, sample_plan):
        create_resp = await client.post(
            _url(sample_building.id, sample_plan.id),
            json=ANNOTATION_PAYLOAD,
            headers=auth_headers,
        )
        annotation_id = create_resp.json()["id"]

        response = await client.get(
            _url(sample_building.id, sample_plan.id, annotation_id),
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == annotation_id

    async def test_annotation_not_found_404(self, client, admin_user, auth_headers, sample_building, sample_plan):
        fake_id = uuid.uuid4()
        response = await client.get(
            _url(sample_building.id, sample_plan.id, fake_id),
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdateAnnotation:
    async def test_update_annotation(self, client, admin_user, auth_headers, sample_building, sample_plan):
        create_resp = await client.post(
            _url(sample_building.id, sample_plan.id),
            json=ANNOTATION_PAYLOAD,
            headers=auth_headers,
        )
        annotation_id = create_resp.json()["id"]

        response = await client.put(
            _url(sample_building.id, sample_plan.id, annotation_id),
            json={"label": "Updated label", "x": 0.8},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Updated label"
        assert data["x"] == 0.8
        # y should remain unchanged
        assert data["y"] == 0.3


class TestDeleteAnnotation:
    async def test_delete_annotation(self, client, admin_user, auth_headers, sample_building, sample_plan):
        create_resp = await client.post(
            _url(sample_building.id, sample_plan.id),
            json=ANNOTATION_PAYLOAD,
            headers=auth_headers,
        )
        annotation_id = create_resp.json()["id"]

        response = await client.delete(
            _url(sample_building.id, sample_plan.id, annotation_id),
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify it's gone
        get_resp = await client.get(
            _url(sample_building.id, sample_plan.id, annotation_id),
            headers=auth_headers,
        )
        assert get_resp.status_code == 404


class TestAnnotationReferences:
    async def test_annotation_with_zone_reference(
        self, client, admin_user, auth_headers, sample_building, sample_plan, sample_zone
    ):
        payload = {
            **ANNOTATION_PAYLOAD,
            "annotation_type": "zone_reference",
            "zone_id": str(sample_zone.id),
        }
        response = await client.post(
            _url(sample_building.id, sample_plan.id),
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["zone_id"] == str(sample_zone.id)
        assert data["annotation_type"] == "zone_reference"

    async def test_annotation_with_sample_reference(
        self, client, admin_user, auth_headers, sample_building, sample_plan, sample_sample
    ):
        payload = {
            **ANNOTATION_PAYLOAD,
            "annotation_type": "sample_location",
            "sample_id": str(sample_sample.id),
        }
        response = await client.post(
            _url(sample_building.id, sample_plan.id),
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sample_id"] == str(sample_sample.id)
        assert data["annotation_type"] == "sample_location"


class TestAnnotationTypeValidation:
    async def test_annotation_type_validation(self, client, admin_user, auth_headers, sample_building, sample_plan):
        payload = {**ANNOTATION_PAYLOAD, "annotation_type": "invalid_type"}
        response = await client.post(
            _url(sample_building.id, sample_plan.id),
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_coordinate_out_of_range(self, client, admin_user, auth_headers, sample_building, sample_plan):
        payload = {**ANNOTATION_PAYLOAD, "x": 1.5}
        response = await client.post(
            _url(sample_building.id, sample_plan.id),
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 422
