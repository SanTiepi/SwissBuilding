"""Tests for Adoption Loops — rollout + packaging layer."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.api.package_presets import router as package_presets_router
from app.api.rollout import router as rollout_router
from app.main import app
from app.models.bounded_embed import ExternalViewerProfile
from app.models.building import Building
from app.models.delegated_access import TenantBoundary
from app.models.organization import Organization
from app.models.package_preset import PackagePreset
from app.services.package_preset_service import (
    create_embed_token,
    get_preset,
    list_presets,
    list_viewer_profiles,
    preview_package,
    record_embed_view,
    validate_embed_token,
)
from app.services.rollout_service import (
    check_delegated_access,
    create_grant,
    get_grant,
    list_grants,
    list_privileged_events,
    log_privileged_event,
    revoke_grant,
)

# Register routers for HTTP tests (not yet in router.py hub file)
app.include_router(rollout_router, prefix="/api/v1")
app.include_router(package_presets_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_org(db, name="Test Org"):
    org = Organization(id=uuid.uuid4(), name=name, type="property_management")
    db.add(org)
    await db.flush()
    return org


async def _make_building(db, user_id, address="Rue Test 1"):
    b = Building(
        id=uuid.uuid4(),
        address=address,
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=user_id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _make_preset(db, code="wedge"):
    p = PackagePreset(
        preset_code=code,
        title=f"Preset {code}",
        audience_type="owner",
        included_sections=["building_identity", "diagnostics"],
        excluded_sections=["financial"],
        unknown_sections=["pending_reviews"],
    )
    db.add(p)
    await db.flush()
    return p


async def _make_viewer_profile(db, name="Test Viewer", viewer_type="authority"):
    vp = ExternalViewerProfile(
        name=name,
        viewer_type=viewer_type,
        allowed_sections=["building_identity", "diagnostics"],
        requires_acknowledgement=True,
    )
    db.add(vp)
    await db.flush()
    return vp


# ---------------------------------------------------------------------------
# TenantBoundary model tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_boundary_create(db_session, admin_user):
    org = await _make_org(db_session)
    tb = TenantBoundary(
        organization_id=org.id,
        boundary_name="Test Boundary",
        max_users=50,
        max_external_viewers=10,
    )
    db_session.add(tb)
    await db_session.flush()
    assert tb.id is not None
    assert tb.is_active is True
    assert tb.max_users == 50


@pytest.mark.asyncio
async def test_tenant_boundary_allowed_buildings_null_means_all(db_session, admin_user):
    org = await _make_org(db_session)
    tb = TenantBoundary(organization_id=org.id, boundary_name="All Access")
    db_session.add(tb)
    await db_session.flush()
    assert tb.allowed_building_ids is None  # null = all


@pytest.mark.asyncio
async def test_tenant_boundary_with_specific_buildings(db_session, admin_user):
    org = await _make_org(db_session)
    bid = str(uuid.uuid4())
    tb = TenantBoundary(
        organization_id=org.id,
        boundary_name="Limited",
        allowed_building_ids=[bid],
    )
    db_session.add(tb)
    await db_session.flush()
    assert tb.allowed_building_ids == [bid]


# ---------------------------------------------------------------------------
# DelegatedAccessGrant service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_grant(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    grant = await create_grant(
        db_session,
        building.id,
        {"grant_type": "viewer", "scope": {"documents": True, "diagnostics": True}},
        granted_by_user_id=admin_user.id,
    )
    assert grant.id is not None
    assert grant.grant_type == "viewer"
    assert grant.is_active is True


@pytest.mark.asyncio
async def test_create_grant_auto_logs_event(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    await create_grant(
        db_session,
        building.id,
        {"grant_type": "contributor"},
        granted_by_user_id=admin_user.id,
    )
    events, total = await list_privileged_events(db_session, building_id=building.id)
    assert total >= 1
    assert events[0].action_type == "grant_created"


@pytest.mark.asyncio
async def test_revoke_grant(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    grant = await create_grant(
        db_session,
        building.id,
        {"grant_type": "viewer"},
        granted_by_user_id=admin_user.id,
    )
    revoked = await revoke_grant(db_session, grant, revoked_by_user_id=admin_user.id)
    assert revoked.is_active is False
    assert revoked.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_grant_logs_event(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    grant = await create_grant(
        db_session,
        building.id,
        {"grant_type": "viewer"},
        granted_by_user_id=admin_user.id,
    )
    await revoke_grant(db_session, grant, revoked_by_user_id=admin_user.id)
    events, _ = await list_privileged_events(db_session, building_id=building.id)
    action_types = [e.action_type for e in events]
    assert "grant_revoked" in action_types


@pytest.mark.asyncio
async def test_list_grants_active_only(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    g1 = await create_grant(db_session, building.id, {"grant_type": "viewer"}, admin_user.id)
    await create_grant(db_session, building.id, {"grant_type": "contributor"}, admin_user.id)
    await revoke_grant(db_session, g1, admin_user.id)

    active = await list_grants(db_session, building.id, active_only=True)
    assert len(active) == 1
    assert active[0].grant_type == "contributor"

    all_grants = await list_grants(db_session, building.id, active_only=False)
    assert len(all_grants) == 2


@pytest.mark.asyncio
async def test_check_delegated_access_by_email(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    await create_grant(
        db_session,
        building.id,
        {"grant_type": "viewer", "granted_to_email": "partner@test.ch"},
        admin_user.id,
    )
    found = await check_delegated_access(db_session, building.id, email="partner@test.ch")
    assert found is not None
    assert found.grant_type == "viewer"

    not_found = await check_delegated_access(db_session, building.id, email="nobody@test.ch")
    assert not_found is None


@pytest.mark.asyncio
async def test_check_delegated_access_by_org(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    org = await _make_org(db_session)
    await create_grant(
        db_session,
        building.id,
        {"grant_type": "contributor", "granted_to_org_id": org.id},
        admin_user.id,
    )
    found = await check_delegated_access(db_session, building.id, org_id=org.id)
    assert found is not None


@pytest.mark.asyncio
async def test_check_delegated_access_no_criteria(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    result = await check_delegated_access(db_session, building.id)
    assert result is None


@pytest.mark.asyncio
async def test_get_grant(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    grant = await create_grant(db_session, building.id, {"grant_type": "support"}, admin_user.id)
    fetched = await get_grant(db_session, grant.id)
    assert fetched is not None
    assert fetched.grant_type == "support"


@pytest.mark.asyncio
async def test_get_grant_not_found(db_session):
    fetched = await get_grant(db_session, uuid.uuid4())
    assert fetched is None


# ---------------------------------------------------------------------------
# PrivilegedAccessEvent service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_privileged_event(db_session, admin_user):
    event = await log_privileged_event(
        db_session,
        user_id=admin_user.id,
        action_type="admin_override",
        details={"reason": "testing"},
        ip_address="192.168.1.1",
    )
    assert event.id is not None
    assert event.action_type == "admin_override"
    assert event.ip_address == "192.168.1.1"


@pytest.mark.asyncio
async def test_list_privileged_events_pagination(db_session, admin_user):
    for i in range(5):
        await log_privileged_event(db_session, user_id=admin_user.id, action_type=f"action_{i}")
    items, total = await list_privileged_events(db_session, page=1, size=3)
    assert total == 5
    assert len(items) == 3


@pytest.mark.asyncio
async def test_list_privileged_events_filter_by_user(db_session, admin_user, owner_user):
    await log_privileged_event(db_session, user_id=admin_user.id, action_type="admin_action")
    await log_privileged_event(db_session, user_id=owner_user.id, action_type="owner_action")
    items, total = await list_privileged_events(db_session, user_id=admin_user.id)
    assert total == 1
    assert items[0].action_type == "admin_action"


# ---------------------------------------------------------------------------
# PackagePreset service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_presets(db_session):
    await _make_preset(db_session, "wedge")
    await _make_preset(db_session, "operational")
    result = await list_presets(db_session)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_preset(db_session):
    await _make_preset(db_session, "wedge")
    preset = await get_preset(db_session, "wedge")
    assert preset is not None
    assert preset.preset_code == "wedge"


@pytest.mark.asyncio
async def test_get_preset_not_found(db_session):
    preset = await get_preset(db_session, "nonexistent")
    assert preset is None


@pytest.mark.asyncio
async def test_preview_package(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    await _make_preset(db_session, "wedge")
    result = await preview_package(db_session, building.id, "wedge")
    assert result is not None
    assert result["preset_code"] == "wedge"
    assert "building_identity" in result["included"]
    assert "financial" in result["excluded"]


@pytest.mark.asyncio
async def test_preview_package_not_found(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    result = await preview_package(db_session, building.id, "nonexistent")
    assert result is None


# ---------------------------------------------------------------------------
# Embed Token service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_embed_token(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    embed = await create_embed_token(
        db_session,
        building.id,
        admin_user.id,
        scope={"sections": ["diagnostics"], "max_views": 10},
    )
    assert embed.id is not None
    assert len(embed.token) > 20
    assert embed.view_count == 0


@pytest.mark.asyncio
async def test_validate_embed_token_valid(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    embed = await create_embed_token(db_session, building.id, admin_user.id)
    found = await validate_embed_token(db_session, embed.token)
    assert found is not None


@pytest.mark.asyncio
async def test_validate_embed_token_invalid(db_session):
    found = await validate_embed_token(db_session, "nonexistent-token")
    assert found is None


@pytest.mark.asyncio
async def test_validate_embed_token_max_views_exceeded(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    embed = await create_embed_token(
        db_session,
        building.id,
        admin_user.id,
        scope={"max_views": 2},
    )
    embed.view_count = 2
    await db_session.flush()
    found = await validate_embed_token(db_session, embed.token)
    assert found is None


@pytest.mark.asyncio
async def test_validate_embed_token_expired(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    embed = await create_embed_token(
        db_session,
        building.id,
        admin_user.id,
        scope={"expires_at": past},
    )
    found = await validate_embed_token(db_session, embed.token)
    assert found is None


@pytest.mark.asyncio
async def test_record_embed_view(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    embed = await create_embed_token(db_session, building.id, admin_user.id)
    assert embed.view_count == 0
    await record_embed_view(db_session, embed)
    assert embed.view_count == 1
    assert embed.last_viewed_at is not None


@pytest.mark.asyncio
async def test_create_embed_with_viewer_profile(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    profile = await _make_viewer_profile(db_session)
    embed = await create_embed_token(db_session, building.id, admin_user.id, viewer_profile_id=profile.id)
    assert embed.viewer_profile_id == profile.id


# ---------------------------------------------------------------------------
# ExternalViewerProfile service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_viewer_profiles(db_session):
    await _make_viewer_profile(db_session, "Profile A", "authority")
    await _make_viewer_profile(db_session, "Profile B", "insurer")
    profiles = await list_viewer_profiles(db_session)
    assert len(profiles) == 2


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_create_grant(client, auth_headers, sample_building):
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/access-grants",
        json={
            "grant_type": "viewer",
            "granted_to_email": "external@test.ch",
            "scope": {"documents": True},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["grant_type"] == "viewer"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_api_list_grants(client, auth_headers, sample_building):
    # Create first
    await client.post(
        f"/api/v1/buildings/{sample_building.id}/access-grants",
        json={"grant_type": "viewer"},
        headers=auth_headers,
    )
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/access-grants",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_api_revoke_grant(client, auth_headers, sample_building):
    create_resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/access-grants",
        json={"grant_type": "temporary_admin"},
        headers=auth_headers,
    )
    grant_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/access-grants/{grant_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_api_privileged_events(client, auth_headers, sample_building):
    # Create a grant to generate an event
    await client.post(
        f"/api/v1/buildings/{sample_building.id}/access-grants",
        json={"grant_type": "viewer"},
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/privileged-access-events", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_api_create_embed_token(client, auth_headers, sample_building):
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/embed-tokens",
        json={"scope": {"sections": ["diagnostics"], "max_views": 50}},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert data["view_count"] == 0


@pytest.mark.asyncio
async def test_api_access_embed_public(client, auth_headers, sample_building):
    # Create token
    create_resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/embed-tokens",
        json={"scope": {"sections": ["building_identity", "diagnostics"]}},
        headers=auth_headers,
    )
    token = create_resp.json()["token"]

    # Access without auth
    resp = await client.get(f"/api/v1/embed/{token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert "building_identity" in data["sections"]


@pytest.mark.asyncio
async def test_api_access_embed_invalid_token(client):
    resp = await client.get("/api/v1/embed/totally-invalid-token")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_list_package_presets(client, auth_headers, db_session):
    db_session.add(PackagePreset(preset_code="test_preset", title="Test", audience_type="owner"))
    await db_session.commit()
    resp = await client.get("/api/v1/package-presets", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_get_package_preset(client, auth_headers, db_session):
    db_session.add(PackagePreset(preset_code="wedge_api", title="Wedge API", audience_type="owner"))
    await db_session.commit()
    resp = await client.get("/api/v1/package-presets/wedge_api", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["preset_code"] == "wedge_api"


@pytest.mark.asyncio
async def test_api_get_package_preset_not_found(client, auth_headers):
    resp = await client.get("/api/v1/package-presets/nonexistent", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_preview_package(client, auth_headers, sample_building, db_session):
    db_session.add(
        PackagePreset(
            preset_code="preview_test",
            title="Preview",
            audience_type="manager",
            included_sections=["diagnostics"],
            excluded_sections=["financial"],
            unknown_sections=["reviews"],
        )
    )
    await db_session.commit()
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/package-preview/preview_test",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["preset_code"] == "preview_test"
    assert "diagnostics" in data["included"]


@pytest.mark.asyncio
async def test_api_list_viewer_profiles(client, auth_headers, db_session):
    db_session.add(ExternalViewerProfile(name="VP1", viewer_type="authority"))
    await db_session.commit()
    resp = await client.get("/api/v1/external-viewer-profiles", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
