import uuid

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.organization import Organization
from app.schemas.campaign import CampaignCreate, CampaignUpdate
from app.services.campaign_service import (
    create_campaign,
    delete_campaign,
    get_campaign,
    link_actions_to_campaign,
    list_campaign_actions,
    list_campaigns,
    update_campaign,
    update_campaign_progress,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _make_org(db, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test Org",
        "type": "property_management",
    }
    defaults.update(kwargs)
    org = Organization(**defaults)
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def _make_action(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "source_type": "manual",
        "action_type": "task",
        "title": "Test action",
        "priority": "medium",
        "status": "open",
    }
    defaults.update(kwargs)
    a = ActionItem(**defaults)
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


# ---------------------------------------------------------------------------
# Service-level CRUD tests
# ---------------------------------------------------------------------------


class TestCampaignCRUD:
    async def test_create_campaign(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        data = CampaignCreate(
            title="Test Campaign",
            campaign_type="diagnostic",
            description="A test campaign",
            priority="high",
            building_ids=[building.id],
        )
        campaign = await create_campaign(db_session, data, created_by=admin_user.id)
        assert campaign.id is not None
        assert campaign.title == "Test Campaign"
        assert campaign.campaign_type == "diagnostic"
        assert campaign.priority == "high"
        assert campaign.status == "draft"
        assert campaign.target_count == 1
        assert campaign.created_by == admin_user.id

    async def test_create_campaign_no_buildings(self, db_session, admin_user):
        data = CampaignCreate(
            title="Empty Campaign",
            campaign_type="maintenance",
        )
        campaign = await create_campaign(db_session, data, created_by=admin_user.id)
        assert campaign.target_count == 0
        assert campaign.building_ids is None

    async def test_create_campaign_invalid_building_ids(self, db_session, admin_user):
        import pytest
        from fastapi import HTTPException

        data = CampaignCreate(
            title="Bad Campaign",
            campaign_type="diagnostic",
            building_ids=[uuid.uuid4()],
        )
        with pytest.raises(HTTPException) as exc_info:
            await create_campaign(db_session, data)
        assert exc_info.value.status_code == 400

    async def test_get_campaign(self, db_session, admin_user):
        data = CampaignCreate(title="Get Me", campaign_type="inspection")
        campaign = await create_campaign(db_session, data)
        fetched = await get_campaign(db_session, campaign.id)
        assert fetched is not None
        assert fetched.id == campaign.id

    async def test_get_campaign_not_found(self, db_session):
        result = await get_campaign(db_session, uuid.uuid4())
        assert result is None

    async def test_update_campaign(self, db_session, admin_user):
        data = CampaignCreate(title="Old Title", campaign_type="diagnostic")
        campaign = await create_campaign(db_session, data)
        updated = await update_campaign(
            db_session,
            campaign.id,
            CampaignUpdate(title="New Title", status="active", priority="critical"),
        )
        assert updated is not None
        assert updated.title == "New Title"
        assert updated.status == "active"
        assert updated.priority == "critical"

    async def test_update_campaign_not_found(self, db_session):
        result = await update_campaign(db_session, uuid.uuid4(), CampaignUpdate(title="x"))
        assert result is None

    async def test_update_campaign_building_ids(self, db_session, admin_user):
        b1 = await _make_building(db_session, admin_user.id)
        b2 = await _make_building(db_session, admin_user.id, address="Rue Test 2")
        data = CampaignCreate(title="Scope Test", campaign_type="diagnostic", building_ids=[b1.id])
        campaign = await create_campaign(db_session, data)
        assert campaign.target_count == 1

        updated = await update_campaign(db_session, campaign.id, CampaignUpdate(building_ids=[b1.id, b2.id]))
        assert updated is not None
        assert updated.target_count == 2

    async def test_delete_campaign(self, db_session, admin_user):
        data = CampaignCreate(title="Delete Me", campaign_type="other")
        campaign = await create_campaign(db_session, data)
        result = await delete_campaign(db_session, campaign.id)
        assert result is True
        assert await get_campaign(db_session, campaign.id) is None

    async def test_delete_campaign_not_found(self, db_session):
        result = await delete_campaign(db_session, uuid.uuid4())
        assert result is False


# ---------------------------------------------------------------------------
# Listing and filtering
# ---------------------------------------------------------------------------


class TestCampaignList:
    async def test_list_campaigns(self, db_session, admin_user):
        for i in range(3):
            await create_campaign(
                db_session,
                CampaignCreate(title=f"Campaign {i}", campaign_type="diagnostic"),
            )
        items, total = await list_campaigns(db_session)
        assert total == 3
        assert len(items) == 3

    async def test_list_campaigns_filter_status(self, db_session, admin_user):
        await create_campaign(db_session, CampaignCreate(title="Draft", campaign_type="diagnostic"))
        c2 = await create_campaign(db_session, CampaignCreate(title="Active", campaign_type="diagnostic"))
        await update_campaign(db_session, c2.id, CampaignUpdate(status="active"))

        items, total = await list_campaigns(db_session, status="draft")
        assert total == 1
        assert items[0].title == "Draft"

    async def test_list_campaigns_filter_type(self, db_session, admin_user):
        await create_campaign(db_session, CampaignCreate(title="Diag", campaign_type="diagnostic"))
        await create_campaign(db_session, CampaignCreate(title="Maint", campaign_type="maintenance"))
        items, total = await list_campaigns(db_session, campaign_type="maintenance")
        assert total == 1
        assert items[0].title == "Maint"

    async def test_list_campaigns_filter_organization(self, db_session, admin_user):
        org = await _make_org(db_session)
        await create_campaign(
            db_session,
            CampaignCreate(title="Org Campaign", campaign_type="diagnostic", organization_id=org.id),
        )
        await create_campaign(db_session, CampaignCreate(title="No Org", campaign_type="diagnostic"))
        items, total = await list_campaigns(db_session, organization_id=org.id)
        assert total == 1
        assert items[0].title == "Org Campaign"

    async def test_list_campaigns_pagination(self, db_session, admin_user):
        for i in range(5):
            await create_campaign(
                db_session,
                CampaignCreate(title=f"C{i}", campaign_type="diagnostic"),
            )
        items, total = await list_campaigns(db_session, page=1, size=2)
        assert total == 5
        assert len(items) == 2

        items2, _ = await list_campaigns(db_session, page=3, size=2)
        assert len(items2) == 1


# ---------------------------------------------------------------------------
# Action linking and progress
# ---------------------------------------------------------------------------


class TestCampaignActions:
    async def test_link_actions(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        campaign = await create_campaign(db_session, CampaignCreate(title="Link Test", campaign_type="diagnostic"))
        a1 = await _make_action(db_session, building.id, title="Action 1")
        a2 = await _make_action(db_session, building.id, title="Action 2")

        linked = await link_actions_to_campaign(db_session, campaign.id, [a1.id, a2.id])
        assert linked == 2

        actions = await list_campaign_actions(db_session, campaign.id)
        assert len(actions) == 2

    async def test_link_actions_campaign_not_found(self, db_session):
        import pytest
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await link_actions_to_campaign(db_session, uuid.uuid4(), [uuid.uuid4()])
        assert exc_info.value.status_code == 404

    async def test_progress_empty_campaign(self, db_session, admin_user):
        campaign = await create_campaign(db_session, CampaignCreate(title="Empty", campaign_type="diagnostic"))
        updated = await update_campaign_progress(db_session, campaign.id)
        assert updated is not None
        assert updated.completed_count == 0

    async def test_progress_all_done(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        campaign = await create_campaign(
            db_session,
            CampaignCreate(
                title="All Done",
                campaign_type="diagnostic",
                building_ids=[building.id],
            ),
        )
        a1 = await _make_action(db_session, building.id, title="Done 1", status="done")
        a2 = await _make_action(db_session, building.id, title="Done 2", status="done")
        await link_actions_to_campaign(db_session, campaign.id, [a1.id, a2.id])

        updated = await update_campaign_progress(db_session, campaign.id)
        assert updated is not None
        assert updated.completed_count == 2

    async def test_progress_partial(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        campaign = await create_campaign(db_session, CampaignCreate(title="Partial", campaign_type="diagnostic"))
        a1 = await _make_action(db_session, building.id, title="Done", status="done")
        a2 = await _make_action(db_session, building.id, title="Open", status="open")
        await link_actions_to_campaign(db_session, campaign.id, [a1.id, a2.id])

        updated = await update_campaign_progress(db_session, campaign.id)
        assert updated.completed_count == 1

    async def test_progress_not_found(self, db_session):
        result = await update_campaign_progress(db_session, uuid.uuid4())
        assert result is None


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestCampaignAPI:
    async def test_create_campaign_endpoint(self, client, admin_user, auth_headers):
        response = await client.post(
            "/api/v1/campaigns",
            json={
                "title": "API Campaign",
                "campaign_type": "diagnostic",
                "priority": "high",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "API Campaign"
        assert data["campaign_type"] == "diagnostic"
        assert data["status"] == "draft"
        assert data["progress_pct"] == 0.0

    async def test_list_campaigns_endpoint(self, client, admin_user, auth_headers):
        await client.post(
            "/api/v1/campaigns",
            json={"title": "Listed", "campaign_type": "diagnostic"},
            headers=auth_headers,
        )
        response = await client.get("/api/v1/campaigns", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    async def test_get_campaign_endpoint(self, client, admin_user, auth_headers):
        create_resp = await client.post(
            "/api/v1/campaigns",
            json={"title": "Get Me", "campaign_type": "inspection"},
            headers=auth_headers,
        )
        campaign_id = create_resp.json()["id"]
        response = await client.get(f"/api/v1/campaigns/{campaign_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Get Me"

    async def test_get_campaign_not_found(self, client, admin_user, auth_headers):
        response = await client.get(f"/api/v1/campaigns/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404

    async def test_update_campaign_endpoint(self, client, admin_user, auth_headers):
        create_resp = await client.post(
            "/api/v1/campaigns",
            json={"title": "Update Me", "campaign_type": "diagnostic"},
            headers=auth_headers,
        )
        campaign_id = create_resp.json()["id"]
        response = await client.put(
            f"/api/v1/campaigns/{campaign_id}",
            json={"title": "Updated", "status": "active"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated"
        assert response.json()["status"] == "active"

    async def test_delete_campaign_endpoint(self, client, admin_user, auth_headers):
        create_resp = await client.post(
            "/api/v1/campaigns",
            json={"title": "Delete Me", "campaign_type": "other"},
            headers=auth_headers,
        )
        campaign_id = create_resp.json()["id"]
        response = await client.delete(f"/api/v1/campaigns/{campaign_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        get_resp = await client.get(f"/api/v1/campaigns/{campaign_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    async def test_link_actions_endpoint(self, client, admin_user, auth_headers, sample_building):
        # Create campaign
        camp_resp = await client.post(
            "/api/v1/campaigns",
            json={"title": "Link API", "campaign_type": "diagnostic"},
            headers=auth_headers,
        )
        campaign_id = camp_resp.json()["id"]

        # Create action
        act_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/actions",
            json={"action_type": "task", "title": "Linkable"},
            headers=auth_headers,
        )
        action_id = act_resp.json()["id"]

        # Link
        response = await client.post(
            f"/api/v1/campaigns/{campaign_id}/actions",
            json={"action_item_ids": [action_id]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["linked"] == 1

    async def test_list_campaign_actions_endpoint(self, client, admin_user, auth_headers, sample_building):
        camp_resp = await client.post(
            "/api/v1/campaigns",
            json={"title": "Actions List", "campaign_type": "diagnostic"},
            headers=auth_headers,
        )
        campaign_id = camp_resp.json()["id"]

        act_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/actions",
            json={"action_type": "task", "title": "Listed"},
            headers=auth_headers,
        )
        action_id = act_resp.json()["id"]

        await client.post(
            f"/api/v1/campaigns/{campaign_id}/actions",
            json={"action_item_ids": [action_id]},
            headers=auth_headers,
        )

        response = await client.get(
            f"/api/v1/campaigns/{campaign_id}/actions",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_progress_endpoint(self, client, admin_user, auth_headers):
        camp_resp = await client.post(
            "/api/v1/campaigns",
            json={"title": "Progress", "campaign_type": "diagnostic"},
            headers=auth_headers,
        )
        campaign_id = camp_resp.json()["id"]
        response = await client.get(
            f"/api/v1/campaigns/{campaign_id}/progress",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["completed_count"] == 0


# ---------------------------------------------------------------------------
# Permission tests
# ---------------------------------------------------------------------------


class TestCampaignPermissions:
    async def test_diagnostician_cannot_create(self, client, diagnostician_user, diag_headers):
        response = await client.post(
            "/api/v1/campaigns",
            json={"title": "Forbidden", "campaign_type": "diagnostic"},
            headers=diag_headers,
        )
        assert response.status_code in (401, 403)

    async def test_diagnostician_can_list(self, client, diagnostician_user, diag_headers):
        response = await client.get("/api/v1/campaigns", headers=diag_headers)
        assert response.status_code == 200

    async def test_owner_can_create(self, client, owner_user, owner_headers):
        response = await client.post(
            "/api/v1/campaigns",
            json={"title": "Owner Campaign", "campaign_type": "maintenance"},
            headers=owner_headers,
        )
        assert response.status_code == 201

    async def test_unauthorized_cannot_list(self, client):
        response = await client.get("/api/v1/campaigns")
        assert response.status_code in (401, 403)
