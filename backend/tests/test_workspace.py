"""BatiConnect — Workspace membership tests (service-layer + route-level)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.api.workspace import router as workspace_router
from app.main import app
from app.models.organization import Organization
from app.models.workspace_membership import DEFAULT_SCOPE_BY_ROLE, WORKSPACE_ROLES
from app.services.workspace_service import (
    add_member,
    check_access,
    enrich_membership,
    get_member,
    get_member_count,
    get_members,
    remove_member,
    update_member_scope,
)

# Register workspace router for HTTP tests (not yet in router.py hub file)
app.include_router(workspace_router, prefix="/api/v1")


# ---- Fixtures ----


@pytest.fixture
async def sample_org(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="DiagSwiss SA",
        type="diagnostic_lab",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


# ---- Service-layer: add_member ----


@pytest.mark.asyncio
async def test_add_member_basic(db_session, sample_building, admin_user):
    membership = await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "owner"},
        granted_by=admin_user.id,
    )
    assert membership.id is not None
    assert membership.building_id == sample_building.id
    assert membership.role == "owner"
    assert membership.is_active is True


@pytest.mark.asyncio
async def test_add_member_with_org(db_session, sample_building, admin_user, sample_org):
    membership = await add_member(
        db_session,
        sample_building.id,
        {"organization_id": sample_org.id, "role": "diagnostician"},
        granted_by=admin_user.id,
    )
    assert membership.organization_id == sample_org.id
    assert membership.user_id is None


@pytest.mark.asyncio
async def test_add_member_default_scope(db_session, sample_building, admin_user):
    membership = await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "viewer"},
        granted_by=admin_user.id,
    )
    expected = DEFAULT_SCOPE_BY_ROLE["viewer"]
    assert membership.access_scope == expected


@pytest.mark.asyncio
async def test_add_member_custom_scope(db_session, sample_building, admin_user):
    custom_scope = {
        "documents": True,
        "diagnostics": False,
        "financial": True,
        "interventions": False,
        "contracts": False,
        "leases": False,
        "ownership": False,
    }
    membership = await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "viewer", "access_scope": custom_scope},
        granted_by=admin_user.id,
    )
    assert membership.access_scope["financial"] is True
    assert membership.access_scope["diagnostics"] is False


@pytest.mark.asyncio
async def test_add_member_invalid_role(db_session, sample_building, admin_user):
    with pytest.raises(ValueError, match="Invalid workspace role"):
        await add_member(
            db_session,
            sample_building.id,
            {"user_id": admin_user.id, "role": "superadmin"},
            granted_by=admin_user.id,
        )


@pytest.mark.asyncio
async def test_add_member_with_expiry(db_session, sample_building, admin_user):
    expires = datetime.now(UTC) + timedelta(days=30)
    membership = await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "contractor", "expires_at": expires},
        granted_by=admin_user.id,
    )
    assert membership.expires_at is not None


# ---- Service-layer: get_members ----


@pytest.mark.asyncio
async def test_get_members(db_session, sample_building, admin_user):
    for role in ["owner", "manager", "viewer"]:
        await add_member(
            db_session,
            sample_building.id,
            {"user_id": admin_user.id, "role": role},
            granted_by=admin_user.id,
        )
    members = await get_members(db_session, sample_building.id)
    assert len(members) == 3


@pytest.mark.asyncio
async def test_get_members_active_only(db_session, sample_building, admin_user):
    m1 = await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "owner"},
        granted_by=admin_user.id,
    )
    await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "viewer"},
        granted_by=admin_user.id,
    )
    await remove_member(db_session, m1.id)

    active = await get_members(db_session, sample_building.id, active_only=True)
    assert len(active) == 1
    all_members = await get_members(db_session, sample_building.id, active_only=False)
    assert len(all_members) == 2


# ---- Service-layer: remove_member ----


@pytest.mark.asyncio
async def test_remove_member(db_session, sample_building, admin_user):
    membership = await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "owner"},
        granted_by=admin_user.id,
    )
    removed = await remove_member(db_session, membership.id)
    assert removed.is_active is False


@pytest.mark.asyncio
async def test_remove_member_not_found(db_session):
    result = await remove_member(db_session, uuid.uuid4())
    assert result is None


# ---- Service-layer: update_member_scope ----


@pytest.mark.asyncio
async def test_update_member_scope(db_session, sample_building, admin_user):
    membership = await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "viewer"},
        granted_by=admin_user.id,
    )
    updated = await update_member_scope(db_session, membership.id, {"role": "manager"})
    assert updated.role == "manager"


@pytest.mark.asyncio
async def test_update_member_scope_not_found(db_session):
    result = await update_member_scope(db_session, uuid.uuid4(), {"role": "viewer"})
    assert result is None


# ---- Service-layer: check_access ----


@pytest.mark.asyncio
async def test_check_access_direct_user(db_session, sample_building, admin_user):
    await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "owner"},
        granted_by=admin_user.id,
    )
    assert await check_access(db_session, admin_user.id, sample_building.id, "documents") is True
    assert await check_access(db_session, admin_user.id, sample_building.id, "financial") is True


@pytest.mark.asyncio
async def test_check_access_viewer_no_financial(db_session, sample_building, admin_user):
    await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "viewer"},
        granted_by=admin_user.id,
    )
    assert await check_access(db_session, admin_user.id, sample_building.id, "documents") is True
    assert await check_access(db_session, admin_user.id, sample_building.id, "financial") is False


@pytest.mark.asyncio
async def test_check_access_no_membership(db_session, sample_building, admin_user):
    assert await check_access(db_session, admin_user.id, sample_building.id, "documents") is False


@pytest.mark.asyncio
async def test_check_access_expired_membership(db_session, sample_building, admin_user):
    past = datetime.now(UTC) - timedelta(days=1)
    await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "owner", "expires_at": past},
        granted_by=admin_user.id,
    )
    assert await check_access(db_session, admin_user.id, sample_building.id, "documents") is False


@pytest.mark.asyncio
async def test_check_access_inactive_membership(db_session, sample_building, admin_user):
    m = await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "owner"},
        granted_by=admin_user.id,
    )
    await remove_member(db_session, m.id)
    assert await check_access(db_session, admin_user.id, sample_building.id, "documents") is False


@pytest.mark.asyncio
async def test_check_access_via_organization(db_session, sample_building, admin_user, sample_org):
    # Assign user to org
    admin_user.organization_id = sample_org.id
    await db_session.flush()

    # Add org membership (not user directly)
    await add_member(
        db_session,
        sample_building.id,
        {"organization_id": sample_org.id, "role": "diagnostician"},
        granted_by=admin_user.id,
    )
    assert await check_access(db_session, admin_user.id, sample_building.id, "diagnostics") is True
    assert await check_access(db_session, admin_user.id, sample_building.id, "financial") is False


# ---- Service-layer: get_member_count ----


@pytest.mark.asyncio
async def test_get_member_count(db_session, sample_building, admin_user):
    assert await get_member_count(db_session, sample_building.id) == 0
    await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "owner"},
        granted_by=admin_user.id,
    )
    assert await get_member_count(db_session, sample_building.id) == 1


# ---- Service-layer: enrich_membership ----


@pytest.mark.asyncio
async def test_enrich_membership(db_session, sample_building, admin_user, sample_org):
    membership = await add_member(
        db_session,
        sample_building.id,
        {"organization_id": sample_org.id, "user_id": admin_user.id, "role": "manager"},
        granted_by=admin_user.id,
    )
    enriched = await enrich_membership(db_session, membership)
    assert enriched["organization_name"] == "DiagSwiss SA"
    assert enriched["user_display_name"] == "Admin Test"
    assert enriched["granted_by_display_name"] == "Admin Test"


# ---- Service-layer: get_member ----


@pytest.mark.asyncio
async def test_get_member(db_session, sample_building, admin_user):
    membership = await add_member(
        db_session,
        sample_building.id,
        {"user_id": admin_user.id, "role": "owner"},
        granted_by=admin_user.id,
    )
    found = await get_member(db_session, membership.id)
    assert found is not None
    assert found.id == membership.id


@pytest.mark.asyncio
async def test_get_member_not_found(db_session):
    found = await get_member(db_session, uuid.uuid4())
    assert found is None


# ---- Model constants ----


def test_workspace_roles_tuple():
    assert "owner" in WORKSPACE_ROLES
    assert "viewer" in WORKSPACE_ROLES
    assert len(WORKSPACE_ROLES) == 7


def test_default_scopes_exist_for_all_roles():
    for role in WORKSPACE_ROLES:
        assert role in DEFAULT_SCOPE_BY_ROLE


# ---- Route-level tests ----


@pytest.mark.asyncio
async def test_route_list_members_empty(client, auth_headers, sample_building):
    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/workspace/members", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_route_create_member(client, auth_headers, sample_building, admin_user):
    payload = {
        "user_id": str(admin_user.id),
        "role": "owner",
    }
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/workspace/members",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "owner"
    assert data["building_id"] == str(sample_building.id)
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_route_create_member_invalid_role(client, auth_headers, sample_building, admin_user):
    payload = {
        "user_id": str(admin_user.id),
        "role": "superadmin",
    }
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/workspace/members",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_route_create_member_missing_org_and_user(client, auth_headers, sample_building):
    payload = {"role": "viewer"}
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/workspace/members",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
async def test_route_update_member(client, auth_headers, sample_building, admin_user):
    # Create
    create_resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/workspace/members",
        json={"user_id": str(admin_user.id), "role": "viewer"},
        headers=auth_headers,
    )
    membership_id = create_resp.json()["id"]

    # Update
    resp = await client.put(
        f"/api/v1/workspace/members/{membership_id}",
        json={"role": "manager"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "manager"


@pytest.mark.asyncio
async def test_route_delete_member(client, auth_headers, sample_building, admin_user):
    create_resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/workspace/members",
        json={"user_id": str(admin_user.id), "role": "viewer"},
        headers=auth_headers,
    )
    membership_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/workspace/members/{membership_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_route_delete_member_not_found(client, auth_headers):
    resp = await client.delete(
        f"/api/v1/workspace/members/{uuid.uuid4()}",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_route_building_not_found(client, auth_headers):
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/workspace/members",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_route_list_after_create(client, auth_headers, sample_building, admin_user):
    await client.post(
        f"/api/v1/buildings/{sample_building.id}/workspace/members",
        json={"user_id": str(admin_user.id), "role": "owner"},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/buildings/{sample_building.id}/workspace/members",
        json={"user_id": str(admin_user.id), "role": "viewer"},
        headers=auth_headers,
    )
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/workspace/members",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_route_update_not_found(client, auth_headers):
    resp = await client.put(
        f"/api/v1/workspace/members/{uuid.uuid4()}",
        json={"role": "viewer"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
