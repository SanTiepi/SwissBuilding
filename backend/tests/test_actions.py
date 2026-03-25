import uuid
from datetime import date

from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.schemas.action_item import ActionItemCreate, ActionItemUpdate
from app.services.action_service import (
    create_action,
    get_action,
    list_actions,
    list_building_actions,
    sync_building_system_actions,
    update_action,
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


async def _make_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "diagnostic_context": "AvT",
        "status": "draft",
        "date_inspection": date(2025, 1, 15),
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def _make_risk_score(db, building_id, overall_risk_level="unknown"):
    rs = BuildingRiskScore(
        id=uuid.uuid4(),
        building_id=building_id,
        overall_risk_level=overall_risk_level,
    )
    db.add(rs)
    await db.commit()
    await db.refresh(rs)
    return rs


async def _make_document(db, building_id, document_type="other"):
    doc = Document(
        id=uuid.uuid4(),
        building_id=building_id,
        file_path="/fake/path.pdf",
        file_name="report.pdf",
        document_type=document_type,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# Service-level CRUD tests
# ---------------------------------------------------------------------------


class TestActionCRUD:
    async def test_create_action(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        data = ActionItemCreate(
            action_type="custom_task",
            title="Do something",
            description="Details here",
            priority="high",
        )
        action = await create_action(db_session, building.id, data, created_by=admin_user.id)
        assert action.id is not None
        assert action.building_id == building.id
        assert action.action_type == "custom_task"
        assert action.title == "Do something"
        assert action.priority == "high"
        assert action.status == "open"
        assert action.source_type == "manual"
        assert action.created_by == admin_user.id

    async def test_get_action(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        data = ActionItemCreate(action_type="task", title="Test")
        action = await create_action(db_session, building.id, data)
        fetched = await get_action(db_session, action.id)
        assert fetched is not None
        assert fetched.id == action.id

    async def test_get_action_not_found(self, db_session):
        result = await get_action(db_session, uuid.uuid4())
        assert result is None

    async def test_update_action(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        data = ActionItemCreate(action_type="task", title="Old title")
        action = await create_action(db_session, building.id, data)

        update_data = ActionItemUpdate(title="New title", status="in_progress", priority="critical")
        updated = await update_action(db_session, action.id, update_data)
        assert updated is not None
        assert updated.title == "New title"
        assert updated.status == "in_progress"
        assert updated.priority == "critical"

    async def test_update_action_done_sets_completed_at(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        data = ActionItemCreate(action_type="task", title="Complete me")
        action = await create_action(db_session, building.id, data)
        assert action.completed_at is None

        updated = await update_action(db_session, action.id, ActionItemUpdate(status="done"))
        assert updated is not None
        assert updated.completed_at is not None

    async def test_update_action_not_found(self, db_session):
        result = await update_action(db_session, uuid.uuid4(), ActionItemUpdate(title="x"))
        assert result is None

    async def test_list_actions_no_filter(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        for i in range(3):
            await create_action(
                db_session,
                building.id,
                ActionItemCreate(action_type="task", title=f"Task {i}"),
            )
        actions = await list_actions(db_session)
        assert len(actions) == 3

    async def test_list_actions_filter_status(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        a1 = await create_action(db_session, building.id, ActionItemCreate(action_type="t", title="Open"))
        a2 = await create_action(db_session, building.id, ActionItemCreate(action_type="t", title="Done"))
        await update_action(db_session, a2.id, ActionItemUpdate(status="done"))

        open_actions = await list_actions(db_session, status="open")
        assert len(open_actions) == 1
        assert open_actions[0].id == a1.id

    async def test_list_actions_filter_priority(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await create_action(db_session, building.id, ActionItemCreate(action_type="t", title="Low", priority="low"))
        await create_action(
            db_session,
            building.id,
            ActionItemCreate(action_type="t", title="High", priority="high"),
        )
        high_actions = await list_actions(db_session, priority="high")
        assert len(high_actions) == 1
        assert high_actions[0].title == "High"

    async def test_list_actions_filter_building_id(self, db_session, admin_user):
        b1 = await _make_building(db_session, admin_user.id)
        b2 = await _make_building(db_session, admin_user.id, address="Rue Test 2")
        await create_action(db_session, b1.id, ActionItemCreate(action_type="t", title="B1"))
        await create_action(db_session, b2.id, ActionItemCreate(action_type="t", title="B2"))

        b1_actions = await list_actions(db_session, building_id=b1.id)
        assert len(b1_actions) == 1
        assert b1_actions[0].title == "B1"

    async def test_list_building_actions(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await create_action(db_session, building.id, ActionItemCreate(action_type="t", title="A"))
        actions = await list_building_actions(db_session, building.id)
        assert len(actions) == 1


# ---------------------------------------------------------------------------
# System-action sync tests
# ---------------------------------------------------------------------------


class TestSyncBuildingSystemActions:
    async def test_sync_creates_create_diagnostic_for_high_risk(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_risk_score(db_session, building.id, "high")

        created = await sync_building_system_actions(db_session, building.id)
        assert len(created) == 1
        assert created[0].action_type == "create_diagnostic"
        assert created[0].priority == "high"
        assert created[0].source_type == "system"

    async def test_sync_creates_create_diagnostic_for_critical_risk(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_risk_score(db_session, building.id, "critical")

        created = await sync_building_system_actions(db_session, building.id)
        assert any(a.action_type == "create_diagnostic" and a.priority == "critical" for a in created)

    async def test_sync_no_create_diagnostic_when_diagnostic_exists(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_risk_score(db_session, building.id, "high")
        await _make_diagnostic(db_session, building.id, status="draft")

        created = await sync_building_system_actions(db_session, building.id)
        assert not any(a.action_type == "create_diagnostic" for a in created)

    async def test_sync_creates_add_samples_for_draft_no_samples(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_diagnostic(db_session, building.id, status="draft")

        created = await sync_building_system_actions(db_session, building.id)
        assert any(a.action_type == "add_samples" for a in created)

    async def test_sync_creates_upload_report_for_completed_no_report(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_diagnostic(db_session, building.id, status="completed", report_file_path=None)

        created = await sync_building_system_actions(db_session, building.id)
        assert any(a.action_type == "upload_report" for a in created)

    async def test_sync_creates_notify_suva(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_diagnostic(
            db_session,
            building.id,
            suva_notification_required=True,
            suva_notification_date=None,
            canton_notification_date=None,
        )

        created = await sync_building_system_actions(db_session, building.id)
        assert any(a.action_type == "notify_suva" for a in created)
        assert any(a.action_type == "notify_canton" for a in created)

    async def test_sync_creates_complete_dossier_for_validated_no_doc(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_diagnostic(db_session, building.id, status="validated")

        created = await sync_building_system_actions(db_session, building.id)
        assert any(a.action_type == "complete_dossier" for a in created)

    async def test_sync_no_complete_dossier_when_report_doc_exists(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_diagnostic(db_session, building.id, status="validated")
        await _make_document(db_session, building.id, document_type="diagnostic_report")

        created = await sync_building_system_actions(db_session, building.id)
        assert not any(a.action_type == "complete_dossier" for a in created)

    async def test_sync_idempotent_no_duplicates(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_risk_score(db_session, building.id, "high")

        created1 = await sync_building_system_actions(db_session, building.id)
        assert len(created1) == 1

        created2 = await sync_building_system_actions(db_session, building.id)
        assert len(created2) == 0

        # Only one action total
        all_actions = await list_actions(db_session, building_id=building.id)
        system_actions = [a for a in all_actions if a.source_type == "system"]
        assert len(system_actions) == 1

    async def test_sync_marks_resolved_as_done(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        await _make_risk_score(db_session, building.id, "high")

        # First sync creates the action
        await sync_building_system_actions(db_session, building.id)

        # Now add a diagnostic to resolve the need
        await _make_diagnostic(db_session, building.id, status="draft")

        # Second sync should mark the action as done
        await sync_building_system_actions(db_session, building.id)

        all_actions = await list_actions(db_session, building_id=building.id)
        create_diag_actions = [
            a for a in all_actions if a.action_type == "create_diagnostic" and a.source_type == "system"
        ]
        assert len(create_diag_actions) == 1
        assert create_diag_actions[0].status == "done"
        assert create_diag_actions[0].completed_at is not None

    async def test_sync_nonexistent_building_returns_empty(self, db_session):
        result = await sync_building_system_actions(db_session, uuid.uuid4())
        assert result == []


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestActionAPI:
    async def test_create_action_endpoint(self, client, admin_user, auth_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/actions",
            json={
                "action_type": "custom_task",
                "title": "API created action",
                "priority": "high",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["action_type"] == "custom_task"
        assert data["title"] == "API created action"
        assert data["priority"] == "high"
        assert data["status"] == "open"
        assert data["source_type"] == "manual"

    async def test_create_action_building_not_found(self, client, admin_user, auth_headers):
        response = await client.post(
            f"/api/v1/buildings/{uuid.uuid4()}/actions",
            json={"action_type": "task", "title": "Orphan"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_list_actions_endpoint(self, client, admin_user, auth_headers, sample_building):
        # Create an action first
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/actions",
            json={"action_type": "task", "title": "Listed"},
            headers=auth_headers,
        )
        response = await client.get("/api/v1/actions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_list_actions_filter_status(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/actions",
            json={"action_type": "task", "title": "Open one"},
            headers=auth_headers,
        )
        response = await client.get("/api/v1/actions", params={"status": "open"}, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(a["status"] == "open" for a in data)

    async def test_list_building_actions_endpoint(self, client, admin_user, auth_headers, sample_building):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/actions",
            json={"action_type": "task", "title": "Building action"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/buildings/{sample_building.id}/actions",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_list_building_actions_not_found(self, client, admin_user, auth_headers):
        response = await client.get(
            f"/api/v1/buildings/{uuid.uuid4()}/actions",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_update_action_endpoint(self, client, admin_user, auth_headers, sample_building):
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/actions",
            json={"action_type": "task", "title": "Update me"},
            headers=auth_headers,
        )
        action_id = create_resp.json()["id"]

        response = await client.put(
            f"/api/v1/actions/{action_id}",
            json={"status": "in_progress", "title": "Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["title"] == "Updated"

    async def test_update_action_not_found(self, client, admin_user, auth_headers):
        response = await client.put(
            f"/api/v1/actions/{uuid.uuid4()}",
            json={"title": "Ghost"},
            headers=auth_headers,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Permission tests
# ---------------------------------------------------------------------------


class TestActionPermissions:
    async def test_owner_cannot_create_action(self, client, owner_user, owner_headers, sample_building):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/actions",
            json={"action_type": "task", "title": "Forbidden"},
            headers=owner_headers,
        )
        assert response.status_code in (401, 403)

    async def test_owner_can_list_actions(self, client, owner_user, owner_headers):
        response = await client.get("/api/v1/actions", headers=owner_headers)
        assert response.status_code == 200

    async def test_diagnostician_can_create_action(
        self, client, db_session, diagnostician_user, diag_headers, sample_building
    ):
        response = await client.post(
            f"/api/v1/buildings/{sample_building.id}/actions",
            json={"action_type": "task", "title": "Diag action"},
            headers=diag_headers,
        )
        assert response.status_code == 201

    async def test_owner_cannot_update_action(
        self, client, db_session, admin_user, auth_headers, owner_user, owner_headers, sample_building
    ):
        # Admin creates
        create_resp = await client.post(
            f"/api/v1/buildings/{sample_building.id}/actions",
            json={"action_type": "task", "title": "Locked"},
            headers=auth_headers,
        )
        action_id = create_resp.json()["id"]

        # Owner tries to update
        response = await client.put(
            f"/api/v1/actions/{action_id}",
            json={"title": "Hacked"},
            headers=owner_headers,
        )
        assert response.status_code in (401, 403)

    async def test_unauthorized_cannot_list_actions(self, client):
        response = await client.get("/api/v1/actions")
        assert response.status_code in (401, 403)
