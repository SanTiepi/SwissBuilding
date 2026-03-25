import uuid


async def _setup_chain(client, building_id, headers):
    """Create zone + element and return (zone_id, element_id)."""
    zone_resp = await client.post(
        f"/api/v1/buildings/{building_id}/zones",
        json={"zone_type": "floor", "name": "Test Zone"},
        headers=headers,
    )
    assert zone_resp.status_code == 201
    zone_id = zone_resp.json()["id"]

    elem_resp = await client.post(
        f"/api/v1/buildings/{building_id}/zones/{zone_id}/elements",
        json={"element_type": "wall", "name": "Test Wall"},
        headers=headers,
    )
    assert elem_resp.status_code == 201
    element_id = elem_resp.json()["id"]

    return zone_id, element_id


def _materials_url(building_id, zone_id, element_id, material_id=None):
    base = f"/api/v1/buildings/{building_id}/zones/{zone_id}/elements/{element_id}/materials"
    if material_id:
        return f"{base}/{material_id}"
    return base


class TestCreateMaterial:
    async def test_create_material(self, client, admin_user, auth_headers, sample_building):
        zone_id, element_id = await _setup_chain(client, sample_building.id, auth_headers)
        response = await client.post(
            _materials_url(sample_building.id, zone_id, element_id),
            json={
                "material_type": "coating",
                "name": "Peinture blanche",
                "manufacturer": "Sika",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["material_type"] == "coating"
        assert data["name"] == "Peinture blanche"
        assert data["manufacturer"] == "Sika"
        assert data["created_by"] == str(admin_user.id)
        assert data["contains_pollutant"] is False

    async def test_create_material_with_pollutant(self, client, admin_user, auth_headers, sample_building):
        zone_id, element_id = await _setup_chain(client, sample_building.id, auth_headers)
        response = await client.post(
            _materials_url(sample_building.id, zone_id, element_id),
            json={
                "material_type": "insulation",
                "name": "Flocage amiante",
                "contains_pollutant": True,
                "pollutant_type": "asbestos",
                "pollutant_confirmed": True,
                "notes": "Chrysotile confirmed by lab",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["contains_pollutant"] is True
        assert data["pollutant_type"] == "asbestos"
        assert data["pollutant_confirmed"] is True


class TestListMaterials:
    async def test_list_materials(self, client, admin_user, auth_headers, sample_building):
        zone_id, element_id = await _setup_chain(client, sample_building.id, auth_headers)
        for name in ["Mat A", "Mat B"]:
            await client.post(
                _materials_url(sample_building.id, zone_id, element_id),
                json={"material_type": "coating", "name": name},
                headers=auth_headers,
            )

        response = await client.get(
            _materials_url(sample_building.id, zone_id, element_id),
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2


class TestDeleteMaterial:
    async def test_delete_material(self, client, admin_user, auth_headers, sample_building):
        zone_id, element_id = await _setup_chain(client, sample_building.id, auth_headers)
        resp = await client.post(
            _materials_url(sample_building.id, zone_id, element_id),
            json={"material_type": "coating", "name": "To delete"},
            headers=auth_headers,
        )
        material_id = resp.json()["id"]

        response = await client.delete(
            _materials_url(sample_building.id, zone_id, element_id, material_id),
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify deleted
        list_resp = await client.get(
            _materials_url(sample_building.id, zone_id, element_id),
            headers=auth_headers,
        )
        assert len(list_resp.json()) == 0

    async def test_delete_material_not_in_element(self, client, admin_user, auth_headers, sample_building):
        zone_id, element_id = await _setup_chain(client, sample_building.id, auth_headers)
        fake_id = uuid.uuid4()
        response = await client.delete(
            _materials_url(sample_building.id, zone_id, element_id, fake_id),
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestFullChainValidation:
    async def test_material_with_invalid_chain(self, client, admin_user, auth_headers, sample_building):
        """Verify that an invalid zone/element chain returns 404."""
        fake_zone = uuid.uuid4()
        fake_element = uuid.uuid4()
        response = await client.get(
            _materials_url(sample_building.id, fake_zone, fake_element),
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestPermissions:
    async def test_owner_cannot_create_material(
        self, client, admin_user, auth_headers, owner_user, owner_headers, sample_building
    ):
        zone_id, element_id = await _setup_chain(client, sample_building.id, auth_headers)
        response = await client.post(
            _materials_url(sample_building.id, zone_id, element_id),
            json={"material_type": "coating", "name": "Test"},
            headers=owner_headers,
        )
        assert response.status_code in (401, 403)

    async def test_owner_can_list_materials(
        self, client, admin_user, auth_headers, owner_user, owner_headers, sample_building
    ):
        zone_id, element_id = await _setup_chain(client, sample_building.id, auth_headers)
        response = await client.get(
            _materials_url(sample_building.id, zone_id, element_id),
            headers=owner_headers,
        )
        assert response.status_code == 200
