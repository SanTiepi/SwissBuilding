import uuid

import pytest

from app.models.assignment import Assignment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_assignment(db, target_type, target_id, user_id, created_by, role="responsible"):
    a = Assignment(
        id=uuid.uuid4(),
        target_type=target_type,
        target_id=target_id,
        user_id=user_id,
        role=role,
        created_by=created_by,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


# ---------------------------------------------------------------------------
# POST /assignments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_assignment(client, admin_user, auth_headers, diagnostician_user):
    target_id = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/assignments",
        json={
            "target_type": "building",
            "target_id": target_id,
            "user_id": str(diagnostician_user.id),
            "role": "diagnostician",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["target_type"] == "building"
    assert data["target_id"] == target_id
    assert data["user_id"] == str(diagnostician_user.id)
    assert data["role"] == "diagnostician"
    assert data["created_by"] == str(admin_user.id)


@pytest.mark.asyncio
async def test_create_assignment_forbidden_for_owner(client, owner_user, owner_headers):
    resp = await client.post(
        "/api/v1/assignments",
        json={
            "target_type": "building",
            "target_id": str(uuid.uuid4()),
            "user_id": str(owner_user.id),
            "role": "owner_contact",
        },
        headers=owner_headers,
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /assignments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_assignments_empty(client, admin_user, auth_headers):
    resp = await client.get("/api/v1/assignments", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_assignments_with_data(client, admin_user, auth_headers, db_session, diagnostician_user):
    building_id = uuid.uuid4()
    await _make_assignment(db_session, "building", building_id, diagnostician_user.id, admin_user.id)
    await _make_assignment(db_session, "building", building_id, admin_user.id, admin_user.id, role="reviewer")

    resp = await client.get("/api/v1/assignments", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_assignments_filter_by_target_type(client, admin_user, auth_headers, db_session, diagnostician_user):
    building_id = uuid.uuid4()
    diag_id = uuid.uuid4()
    await _make_assignment(db_session, "building", building_id, diagnostician_user.id, admin_user.id)
    await _make_assignment(db_session, "diagnostic", diag_id, diagnostician_user.id, admin_user.id)

    resp = await client.get("/api/v1/assignments?target_type=building", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["target_type"] == "building"


@pytest.mark.asyncio
async def test_list_assignments_filter_by_user_id(client, admin_user, auth_headers, db_session, diagnostician_user):
    building_id = uuid.uuid4()
    await _make_assignment(db_session, "building", building_id, diagnostician_user.id, admin_user.id)
    await _make_assignment(db_session, "building", building_id, admin_user.id, admin_user.id, role="reviewer")

    resp = await client.get(f"/api/v1/assignments?user_id={diagnostician_user.id}", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["user_id"] == str(diagnostician_user.id)


@pytest.mark.asyncio
async def test_list_assignments_filter_by_target_id(client, admin_user, auth_headers, db_session, diagnostician_user):
    b1 = uuid.uuid4()
    b2 = uuid.uuid4()
    await _make_assignment(db_session, "building", b1, diagnostician_user.id, admin_user.id)
    await _make_assignment(db_session, "building", b2, diagnostician_user.id, admin_user.id)

    resp = await client.get(f"/api/v1/assignments?target_id={b1}", headers=auth_headers)
    data = resp.json()
    assert data["total"] == 1


# ---------------------------------------------------------------------------
# DELETE /assignments/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_assignment(client, admin_user, auth_headers, db_session, diagnostician_user):
    building_id = uuid.uuid4()
    a = await _make_assignment(db_session, "building", building_id, diagnostician_user.id, admin_user.id)

    resp = await client.delete(f"/api/v1/assignments/{a.id}", headers=auth_headers)
    assert resp.status_code == 204

    # Verify it's gone
    resp2 = await client.get("/api/v1/assignments", headers=auth_headers)
    assert resp2.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_assignment_not_found(client, admin_user, auth_headers):
    resp = await client.delete(f"/api/v1/assignments/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_assignment_forbidden_for_diagnostician(
    client, diagnostician_user, diag_headers, db_session, admin_user
):
    building_id = uuid.uuid4()
    a = await _make_assignment(db_session, "building", building_id, diagnostician_user.id, admin_user.id)

    resp = await client.delete(f"/api/v1/assignments/{a.id}", headers=diag_headers)
    assert resp.status_code == 403
