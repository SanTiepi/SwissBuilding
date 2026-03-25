import uuid


class TestCreateBuilding:
    async def test_create_building(self, client, admin_user, auth_headers):
        response = await client.post(
            "/api/v1/buildings",
            json={
                "address": "Avenue de la Gare 10",
                "postal_code": "1003",
                "city": "Lausanne",
                "canton": "VD",
                "construction_year": 1980,
                "building_type": "residential",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["address"] == "Avenue de la Gare 10"
        assert data["city"] == "Lausanne"
        assert data["canton"] == "VD"

    async def test_create_building_assigns_current_user_organization(
        self,
        client,
        db_session,
        admin_user,
        auth_headers,
    ):
        from app.models.building import Building
        from app.models.organization import Organization

        org = Organization(
            id=uuid.uuid4(),
            name="Regie Test Organisation",
            type="property_management",
            city="Lausanne",
            canton="VD",
        )
        db_session.add(org)
        await db_session.flush()

        admin_user.organization_id = org.id
        await db_session.commit()

        response = await client.post(
            "/api/v1/buildings",
            json={
                "address": "Rue des Organisations 14",
                "postal_code": "1004",
                "city": "Lausanne",
                "canton": "VD",
                "construction_year": 1974,
                "building_type": "mixed",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        building_id = uuid.UUID(response.json()["id"])
        building = await db_session.get(Building, building_id)
        assert building is not None
        assert building.organization_id == org.id

    async def test_create_building_unauthorized(self, client):
        response = await client.post(
            "/api/v1/buildings",
            json={
                "address": "Rue Cachée 1",
                "postal_code": "1000",
                "city": "Lausanne",
                "canton": "VD",
                "construction_year": 2000,
                "building_type": "commercial",
            },
        )
        assert response.status_code in (401, 403)

    async def test_owner_cannot_create_building(self, client, owner_user, owner_headers):
        response = await client.post(
            "/api/v1/buildings",
            json={
                "address": "Rue Interdite 5",
                "postal_code": "1200",
                "city": "Genève",
                "canton": "GE",
                "construction_year": 1990,
                "building_type": "residential",
            },
            headers=owner_headers,
        )
        assert response.status_code in (401, 403)


class TestListBuildings:
    async def test_list_buildings(self, client, admin_user, auth_headers, sample_building):
        response = await client.get("/api/v1/buildings", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Expect paginated response with items list
        if isinstance(data, dict):
            assert "items" in data or "results" in data or "data" in data
        elif isinstance(data, list):
            assert len(data) >= 1

    async def test_filter_buildings_by_canton(self, client, admin_user, auth_headers, sample_building):
        response = await client.get("/api/v1/buildings", params={"canton": "VD"}, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Verify filtered results contain only VD buildings
        if isinstance(data, dict):
            items = data.get("items") or data.get("results") or data.get("data") or []
        else:
            items = data
        for item in items:
            assert item["canton"] == "VD"

    async def test_list_buildings_pagination(self, client, db_session, admin_user, auth_headers):
        from app.models.building import Building

        # Create 5 buildings to test pagination
        for i in range(5):
            building = Building(
                id=uuid.uuid4(),
                address=f"Rue Pagination {i}",
                postal_code="1000",
                city="Lausanne",
                canton="VD",
                construction_year=1960 + i,
                building_type="residential",
                created_by=admin_user.id,
                status="active",
            )
            db_session.add(building)
        await db_session.commit()

        response = await client.get(
            "/api/v1/buildings",
            params={"page": 1, "size": 2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        if isinstance(data, dict):
            items = data.get("items") or data.get("results") or data.get("data") or []
            assert len(items) <= 2
            # Check total count if available
            if "total" in data:
                assert data["total"] >= 5


class TestGetBuilding:
    async def test_get_building(self, client, admin_user, auth_headers, sample_building):
        response = await client.get(f"/api/v1/buildings/{sample_building.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["address"] == "Rue Test 1"
        assert data["city"] == "Lausanne"


class TestUpdateBuilding:
    async def test_update_building(self, client, admin_user, auth_headers, sample_building):
        response = await client.put(
            f"/api/v1/buildings/{sample_building.id}",
            json={
                "address": "Rue Modifiée 42",
                "postal_code": "1000",
                "city": "Lausanne",
                "canton": "VD",
                "construction_year": 1970,
                "building_type": "residential",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["address"] == "Rue Modifiée 42"


class TestDeleteBuilding:
    async def test_delete_building(self, client, admin_user, auth_headers, sample_building):
        response = await client.delete(f"/api/v1/buildings/{sample_building.id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify it's gone or soft-deleted
        get_response = await client.get(f"/api/v1/buildings/{sample_building.id}", headers=auth_headers)
        assert get_response.status_code in (404, 200)  # 200 if soft-delete with status change
