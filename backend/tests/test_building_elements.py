import uuid


async def _create_zone(client, building_id, headers, **kwargs):
    """Helper to create a zone and return its id."""
    defaults = {"zone_type": "floor", "name": "Test Zone"}
    defaults.update(kwargs)
    resp = await client.post(
        f"/api/v1/buildings/{building_id}/zones",
        json=defaults,
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_element(client, building_id, zone_id, headers, **kwargs):
    """Helper to create an element and return its id."""
    defaults = {"element_type": "wall", "name": "Test Element"}
    defaults.update(kwargs)
    resp = await client.post(
        f"/api/v1/buildings/{building_id}/zones/{zone_id}/elements",
        json=defaults,
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestCreateElement:
    async def test_create_element(self, client, admin_user, auth_headers, sample_building):
        zone_id = await _create_zone(client, sample_building.id, auth_headers)
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}/elements",
            json={
                "element_type": "wall",
                "name": "Mur Nord",
                "description": "Mur porteur",
                "condition": "good",
                "installation_year": 1965,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["element_type"] == "wall"
        assert data["name"] == "Mur Nord"
        assert data["condition"] == "good"
        assert data["created_by"] == str(admin_user.id)
        assert data["materials_count"] == 0

    async def test_owner_cannot_create_element(
        self, client, admin_user, auth_headers, owner_user, owner_headers, sample_building
    ):
        zone_id = await _create_zone(client, sample_building.id, auth_headers)
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}/elements",
            json={"element_type": "wall", "name": "Test"},
            headers=owner_headers,
        )
        assert response.status_code in (401, 403)


class TestListElements:
    async def test_list_elements(self, client, admin_user, auth_headers, sample_building):
        zone_id = await _create_zone(client, sample_building.id, auth_headers)
        for name in ["Mur 1", "Mur 2"]:
            await _create_element(client, sample_building.id, zone_id, auth_headers, name=name)
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}/elements",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_elements_filtered_by_type(self, client, admin_user, auth_headers, sample_building):
        zone_id = await _create_zone(client, sample_building.id, auth_headers)
        await _create_element(
            client,
            sample_building.id,
            zone_id,
            auth_headers,
            element_type="wall",
            name="Mur",
        )
        await _create_element(
            client,
            sample_building.id,
            zone_id,
            auth_headers,
            element_type="ceiling",
            name="Plafond",
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}/elements",
            params={"element_type": "wall"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["element_type"] == "wall"


class TestGetElement:
    async def test_get_element_with_materials_count(self, client, admin_user, auth_headers, sample_building):
        zone_id = await _create_zone(client, sample_building.id, auth_headers)
        element_id = await _create_element(client, sample_building.id, zone_id, auth_headers)

        # Add a material
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}/elements/{element_id}/materials",
            json={"material_type": "coating", "name": "Peinture"},
            headers=auth_headers,
        )

        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}/elements/{element_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["materials_count"] == 1

    async def test_element_not_in_zone_404(self, client, admin_user, auth_headers, sample_building):
        zone_id = await _create_zone(client, sample_building.id, auth_headers)
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}/elements/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_zone_not_in_building_404(self, client, admin_user, auth_headers, sample_building):
        fake_zone = uuid.uuid4()
        fake_element = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/zones/{fake_zone}/elements/{fake_element}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdateElement:
    async def test_update_element(self, client, admin_user, auth_headers, sample_building):
        zone_id = await _create_zone(client, sample_building.id, auth_headers)
        element_id = await _create_element(client, sample_building.id, zone_id, auth_headers)

        response = await client.put(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}/elements/{element_id}",
            json={"name": "Updated Wall", "condition": "poor"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Wall"
        assert data["condition"] == "poor"
        assert data["element_type"] == "wall"  # unchanged


class TestDeleteElement:
    async def test_delete_element(self, client, admin_user, auth_headers, sample_building):
        zone_id = await _create_zone(client, sample_building.id, auth_headers)
        element_id = await _create_element(client, sample_building.id, zone_id, auth_headers)

        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}/elements/{element_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    async def test_delete_element_with_materials_409(self, client, admin_user, auth_headers, sample_building):
        zone_id = await _create_zone(client, sample_building.id, auth_headers)
        element_id = await _create_element(client, sample_building.id, zone_id, auth_headers)

        # Add material
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}/elements/{element_id}/materials",
            json={"material_type": "coating", "name": "Peinture"},
            headers=auth_headers,
        )

        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}/elements/{element_id}",
            headers=auth_headers,
        )
        assert response.status_code == 409
