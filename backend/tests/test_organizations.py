import uuid

from app.models.organization import Organization
from app.models.user import User
from tests.conftest import _HASH_DIAG


class TestCreateOrganization:
    async def test_create_organization(self, client, admin_user, auth_headers):
        response = await client.post(
            "/api/v1/organizations",
            json={
                "name": "DiagSwiss SA",
                "type": "diagnostic_lab",
                "address": "Rue du Lac 10",
                "postal_code": "1000",
                "city": "Lausanne",
                "canton": "VD",
                "email": "info@diagswiss.ch",
                "suva_recognized": True,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "DiagSwiss SA"
        assert data["type"] == "diagnostic_lab"
        assert data["city"] == "Lausanne"
        assert data["suva_recognized"] is True
        assert data["member_count"] == 0

    async def test_create_organization_minimal(self, client, admin_user, auth_headers):
        response = await client.post(
            "/api/v1/organizations",
            json={"name": "Minimal Org", "type": "contractor"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Org"
        assert data["suva_recognized"] is False
        assert data["fach_approved"] is False

    async def test_create_organization_unauthorized(self, client):
        response = await client.post(
            "/api/v1/organizations",
            json={"name": "Unauthorized Org", "type": "diagnostic_lab"},
        )
        assert response.status_code in (401, 403)

    async def test_create_organization_forbidden_for_diagnostician(self, client, diagnostician_user, diag_headers):
        response = await client.post(
            "/api/v1/organizations",
            json={"name": "Forbidden Org", "type": "diagnostic_lab"},
            headers=diag_headers,
        )
        assert response.status_code == 403

    async def test_create_organization_forbidden_for_owner(self, client, owner_user, owner_headers):
        response = await client.post(
            "/api/v1/organizations",
            json={"name": "Owner Org", "type": "property_management"},
            headers=owner_headers,
        )
        assert response.status_code == 403


class TestListOrganizations:
    async def test_list_organizations_empty(self, client, admin_user, auth_headers):
        response = await client.get("/api/v1/organizations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_organizations(self, client, db_session, admin_user, auth_headers):
        org = Organization(id=uuid.uuid4(), name="Test Org", type="diagnostic_lab")
        db_session.add(org)
        await db_session.commit()

        response = await client.get("/api/v1/organizations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Test Org"
        assert data["items"][0]["member_count"] == 0

    async def test_list_organizations_type_filter(self, client, db_session, admin_user, auth_headers):
        org1 = Organization(id=uuid.uuid4(), name="Lab A", type="diagnostic_lab")
        org2 = Organization(id=uuid.uuid4(), name="Firm B", type="architecture_firm")
        db_session.add_all([org1, org2])
        await db_session.commit()

        response = await client.get("/api/v1/organizations", params={"type": "diagnostic_lab"}, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Lab A"

    async def test_list_organizations_pagination(self, client, db_session, admin_user, auth_headers):
        for i in range(5):
            db_session.add(Organization(id=uuid.uuid4(), name=f"Org {i}", type="contractor"))
        await db_session.commit()

        response = await client.get("/api/v1/organizations", params={"page": 1, "size": 2}, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["pages"] == 3

    async def test_list_organizations_with_member_count(self, client, db_session, admin_user, auth_headers):
        org = Organization(id=uuid.uuid4(), name="Org With Members", type="diagnostic_lab")
        db_session.add(org)
        await db_session.flush()

        member = User(
            id=uuid.uuid4(),
            email="member@test.ch",
            password_hash=_HASH_DIAG,
            first_name="Member",
            last_name="Test",
            role="diagnostician",
            is_active=True,
            language="fr",
            organization_id=org.id,
        )
        db_session.add(member)
        await db_session.commit()

        response = await client.get("/api/v1/organizations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        org_data = next(item for item in data["items"] if item["name"] == "Org With Members")
        assert org_data["member_count"] == 1


class TestGetOrganization:
    async def test_get_organization(self, client, db_session, admin_user, auth_headers):
        org_id = uuid.uuid4()
        org = Organization(id=org_id, name="Get Me", type="authority", city="Bern", canton="BE")
        db_session.add(org)
        await db_session.commit()

        response = await client.get(f"/api/v1/organizations/{org_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Get Me"
        assert data["city"] == "Bern"
        assert data["member_count"] == 0

    async def test_get_organization_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/v1/organizations/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    async def test_diagnostician_can_read_organization(self, client, db_session, diagnostician_user, diag_headers):
        org_id = uuid.uuid4()
        org = Organization(id=org_id, name="Readable Org", type="diagnostic_lab")
        db_session.add(org)
        await db_session.commit()

        response = await client.get(f"/api/v1/organizations/{org_id}", headers=diag_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Readable Org"


class TestUpdateOrganization:
    async def test_update_organization(self, client, db_session, admin_user, auth_headers):
        org_id = uuid.uuid4()
        org = Organization(id=org_id, name="Old Name", type="contractor")
        db_session.add(org)
        await db_session.commit()

        response = await client.put(
            f"/api/v1/organizations/{org_id}",
            json={"name": "New Name", "suva_recognized": True},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["suva_recognized"] is True
        assert data["type"] == "contractor"  # unchanged

    async def test_update_organization_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.put(
            f"/api/v1/organizations/{fake_id}",
            json={"name": "Ghost"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_update_organization_forbidden_for_owner(self, client, db_session, owner_user, owner_headers):
        org_id = uuid.uuid4()
        org = Organization(id=org_id, name="Cannot Update", type="contractor")
        db_session.add(org)
        await db_session.commit()

        response = await client.put(
            f"/api/v1/organizations/{org_id}",
            json={"name": "Should Fail"},
            headers=owner_headers,
        )
        assert response.status_code == 403


class TestDeleteOrganization:
    async def test_delete_organization(self, client, db_session, admin_user, auth_headers):
        org_id = uuid.uuid4()
        org = Organization(id=org_id, name="Delete Me", type="contractor")
        db_session.add(org)
        await db_session.commit()

        response = await client.delete(f"/api/v1/organizations/{org_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(f"/api/v1/organizations/{org_id}", headers=auth_headers)
        assert response.status_code == 404

    async def test_delete_organization_with_members(self, client, db_session, admin_user, auth_headers):
        org_id = uuid.uuid4()
        org = Organization(id=org_id, name="Has Members", type="diagnostic_lab")
        db_session.add(org)
        await db_session.flush()

        member = User(
            id=uuid.uuid4(),
            email="nodelete@test.ch",
            password_hash=_HASH_DIAG,
            first_name="No",
            last_name="Delete",
            role="diagnostician",
            is_active=True,
            language="fr",
            organization_id=org_id,
        )
        db_session.add(member)
        await db_session.commit()

        response = await client.delete(f"/api/v1/organizations/{org_id}", headers=auth_headers)
        assert response.status_code == 409
        assert "members" in response.json()["detail"].lower()

    async def test_delete_organization_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.delete(f"/api/v1/organizations/{fake_id}", headers=auth_headers)
        assert response.status_code == 404


class TestListOrganizationMembers:
    async def test_list_members(self, client, db_session, admin_user, auth_headers):
        org_id = uuid.uuid4()
        org = Organization(id=org_id, name="Members Org", type="diagnostic_lab")
        db_session.add(org)
        await db_session.flush()

        for i in range(3):
            db_session.add(
                User(
                    id=uuid.uuid4(),
                    email=f"member{i}@test.ch",
                    password_hash=_HASH_DIAG,
                    first_name=f"First{i}",
                    last_name=f"Last{i}",
                    role="diagnostician",
                    is_active=True,
                    language="fr",
                    organization_id=org_id,
                )
            )
        await db_session.commit()

        response = await client.get(f"/api/v1/organizations/{org_id}/members", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    async def test_list_members_empty(self, client, db_session, admin_user, auth_headers):
        org_id = uuid.uuid4()
        org = Organization(id=org_id, name="Empty Org", type="contractor")
        db_session.add(org)
        await db_session.commit()

        response = await client.get(f"/api/v1/organizations/{org_id}/members", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_members_org_not_found(self, client, admin_user, auth_headers):
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/v1/organizations/{fake_id}/members", headers=auth_headers)
        assert response.status_code == 404
