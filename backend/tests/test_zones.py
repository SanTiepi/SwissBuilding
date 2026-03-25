import uuid


class TestCreateZone:
    async def test_create_zone_admin(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={
                "zone_type": "floor",
                "name": "Rez-de-chaussée",
                "floor_number": 0,
                "surface_area_m2": 120.5,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["zone_type"] == "floor"
        assert data["name"] == "Rez-de-chaussée"
        assert data["floor_number"] == 0
        assert data["surface_area_m2"] == 120.5
        assert data["building_id"] == str(sample_building.id)
        assert data["created_by"] == str(admin_user.id)
        assert data["children_count"] == 0
        assert data["elements_count"] == 0

    async def test_create_zone_with_parent(self, client, admin_user, auth_headers, sample_building):
        # Create parent zone
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "floor", "name": "Étage 1", "floor_number": 1},
            headers=auth_headers,
        )
        parent_id = resp.json()["id"]

        # Create child zone
        resp2 = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={
                "zone_type": "room",
                "name": "Bureau 101",
                "parent_zone_id": parent_id,
            },
            headers=auth_headers,
        )
        assert resp2.status_code == 201
        assert resp2.json()["parent_zone_id"] == parent_id

    async def test_create_zone_building_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/buildings/{fake_id}/zones",
            json={"zone_type": "floor", "name": "Test"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_diagnostician_can_create_zone(self, client, diagnostician_user, diag_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "floor", "name": "RDC"},
            headers=diag_headers,
        )
        assert response.status_code == 201
        assert response.json()["created_by"] == str(diagnostician_user.id)

    async def test_owner_cannot_create_zone(self, client, owner_user, owner_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "floor", "name": "RDC"},
            headers=owner_headers,
        )
        assert response.status_code in (401, 403)


class TestListZones:
    async def test_list_zones(self, client, admin_user, auth_headers, sample_building):
        # Create two zones
        for name in ["Étage 1", "Étage 2"]:
            await client.post(
                f"/api/v1/buildings/{sample_building.id}/zones",
                json={"zone_type": "floor", "name": name},
                headers=auth_headers,
            )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/zones",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["page"] == 1

    async def test_list_zones_filtered_by_type(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "floor", "name": "Étage 1"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "room", "name": "Bureau"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/zones",
            params={"zone_type": "floor"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["zone_type"] == "floor"

    async def test_list_zones_filtered_by_parent(self, client, admin_user, auth_headers, sample_building):
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "floor", "name": "Étage 1"},
            headers=auth_headers,
        )
        parent_id = resp.json()["id"]
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "room", "name": "Bureau", "parent_zone_id": parent_id},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "room", "name": "Cuisine"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/zones",
            params={"parent_zone_id": parent_id},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Bureau"

    async def test_list_zones_pagination(self, client, admin_user, auth_headers, sample_building):
        for i in range(5):
            await client.post(
                f"/api/v1/buildings/{sample_building.id}/zones",
                json={"zone_type": "room", "name": f"Room {i}"},
                headers=auth_headers,
            )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/zones",
            params={"page": 1, "size": 2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["pages"] == 3

    async def test_list_zones_accepts_explorer_batch_size(self, client, admin_user, auth_headers, sample_building):
        for i in range(3):
            await client.post(
                f"/api/v1/buildings/{sample_building.id}/zones",
                json={"zone_type": "room", "name": f"Explorer {i}"},
                headers=auth_headers,
            )

        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/zones",
            params={"size": 200},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["size"] == 200
        assert data["total"] == 3


class TestGetZone:
    async def test_get_zone_with_counts(self, client, admin_user, auth_headers, sample_building):
        # Create zone
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "floor", "name": "Étage 1"},
            headers=auth_headers,
        )
        zone_id = resp.json()["id"]

        # Create child zone
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "room", "name": "Bureau", "parent_zone_id": zone_id},
            headers=auth_headers,
        )

        # Create element in zone
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}/elements",
            json={"element_type": "wall", "name": "Mur Nord"},
            headers=auth_headers,
        )

        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["children_count"] == 1
        assert data["elements_count"] == 1

    async def test_get_zone_not_found(self, client, admin_user, auth_headers, sample_building):
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/zones/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_get_zone_wrong_building(self, client, db_session, admin_user, auth_headers, sample_building):
        """Zone belongs to building A but requested via building B."""
        from app.models.building import Building

        other_building = Building(
            id=uuid.uuid4(),
            address="Rue Autre 5",
            postal_code="1200",
            city="Genève",
            canton="GE",
            construction_year=1990,
            building_type="commercial",
            created_by=admin_user.id,
            status="active",
        )
        db_session.add(other_building)
        await db_session.commit()

        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "floor", "name": "Test"},
            headers=auth_headers,
        )
        zone_id = resp.json()["id"]

        response = await client.get(
            f"/api/v1/buildings/{other_building.id}/zones/{zone_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestUpdateZone:
    async def test_update_zone(self, client, admin_user, auth_headers, sample_building):
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "floor", "name": "Ancien nom"},
            headers=auth_headers,
        )
        zone_id = resp.json()["id"]

        response = await client.put(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}",
            json={"name": "Nouveau nom", "description": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Nouveau nom"
        assert data["description"] == "Updated"
        assert data["zone_type"] == "floor"  # unchanged


class TestDeleteZone:
    async def test_delete_zone(self, client, admin_user, auth_headers, sample_building):
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "floor", "name": "To delete"},
            headers=auth_headers,
        )
        zone_id = resp.json()["id"]

        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify deleted
        get_resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}",
            headers=auth_headers,
        )
        assert get_resp.status_code == 404

    async def test_delete_zone_with_children_409(self, client, admin_user, auth_headers, sample_building):
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "floor", "name": "Parent"},
            headers=auth_headers,
        )
        parent_id = resp.json()["id"]

        await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "room", "name": "Child", "parent_zone_id": parent_id},
            headers=auth_headers,
        )

        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/zones/{parent_id}",
            headers=auth_headers,
        )
        assert response.status_code == 409

    async def test_delete_zone_with_elements_409(self, client, admin_user, auth_headers, sample_building):
        resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones",
            json={"zone_type": "floor", "name": "With elements"},
            headers=auth_headers,
        )
        zone_id = resp.json()["id"]

        await client.post(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}/elements",
            json={"element_type": "wall", "name": "Mur"},
            headers=auth_headers,
        )

        response = await client.delete(
            f"/api/v1/buildings/{sample_building.id}/zones/{zone_id}",
            headers=auth_headers,
        )
        assert response.status_code == 409
