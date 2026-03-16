"""Tests for the audience-bounded sharing link model."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.services.shared_link_service import (
    create_shared_link,
    get_shared_link,
    list_shared_links,
    record_access,
    revoke_shared_link,
    validate_shared_link,
)

# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_link_returns_valid_token(db_session, admin_user):
    """Create link -> valid token returned."""
    link = await create_shared_link(
        db_session,
        resource_type="building",
        resource_id=uuid.uuid4(),
        audience_type="buyer",
        created_by=admin_user.id,
    )
    await db_session.commit()

    assert link.token is not None
    assert len(link.token) > 30
    assert link.resource_type == "building"
    assert link.audience_type == "buyer"
    assert link.is_active is True
    assert link.view_count == 0


@pytest.mark.asyncio
async def test_validate_active_link_success(db_session, admin_user):
    """Validate active link -> success."""
    resource_id = uuid.uuid4()
    link = await create_shared_link(
        db_session,
        resource_type="diagnostic",
        resource_id=resource_id,
        audience_type="insurer",
        created_by=admin_user.id,
    )
    await db_session.commit()

    validated = await validate_shared_link(db_session, link.token)
    assert validated is not None
    assert validated.resource_id == resource_id
    assert validated.resource_type == "diagnostic"


@pytest.mark.asyncio
async def test_validate_expired_link_rejected(db_session, admin_user):
    """Validate expired link -> rejected."""
    link = await create_shared_link(
        db_session,
        resource_type="building",
        resource_id=uuid.uuid4(),
        audience_type="lender",
        created_by=admin_user.id,
        expires_in_days=0,
    )
    # Manually set expires_at in the past
    link.expires_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.commit()

    validated = await validate_shared_link(db_session, link.token)
    assert validated is None


@pytest.mark.asyncio
async def test_validate_over_max_views_rejected(db_session, admin_user):
    """Validate over max_views -> rejected."""
    link = await create_shared_link(
        db_session,
        resource_type="passport",
        resource_id=uuid.uuid4(),
        audience_type="buyer",
        created_by=admin_user.id,
        max_views=2,
    )
    link.view_count = 2
    await db_session.commit()

    validated = await validate_shared_link(db_session, link.token)
    assert validated is None


@pytest.mark.asyncio
async def test_revoke_link_no_longer_valid(db_session, admin_user):
    """Revoke link -> no longer valid."""
    link = await create_shared_link(
        db_session,
        resource_type="building",
        resource_id=uuid.uuid4(),
        audience_type="authority",
        created_by=admin_user.id,
    )
    await db_session.commit()

    revoked = await revoke_shared_link(db_session, link.id, admin_user.id)
    assert revoked is not None
    assert revoked.is_active is False
    await db_session.commit()

    validated = await validate_shared_link(db_session, link.token)
    assert validated is None


@pytest.mark.asyncio
async def test_record_access_increments_view_count(db_session, admin_user):
    """Record access -> view_count incremented."""
    link = await create_shared_link(
        db_session,
        resource_type="authority_pack",
        resource_id=uuid.uuid4(),
        audience_type="contractor",
        created_by=admin_user.id,
    )
    await db_session.commit()

    accessed = await record_access(db_session, link.token)
    assert accessed is not None
    assert accessed.view_count == 1
    assert accessed.last_accessed_at is not None

    accessed = await record_access(db_session, link.token)
    assert accessed.view_count == 2


@pytest.mark.asyncio
async def test_record_access_invalid_token_returns_none(db_session):
    """Record access with invalid token returns None."""
    result = await record_access(db_session, "nonexistent-token")
    assert result is None


@pytest.mark.asyncio
async def test_revoke_by_non_creator_raises(db_session, admin_user):
    """Only the creator can revoke a link."""
    link = await create_shared_link(
        db_session,
        resource_type="building",
        resource_id=uuid.uuid4(),
        audience_type="tenant",
        created_by=admin_user.id,
    )
    await db_session.commit()

    other_user_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Only the link creator"):
        await revoke_shared_link(db_session, link.id, other_user_id)


@pytest.mark.asyncio
async def test_list_shared_links_filtered(db_session, admin_user):
    """List shared links with filters."""
    resource_id = uuid.uuid4()
    for audience in ("buyer", "insurer", "lender"):
        await create_shared_link(
            db_session,
            resource_type="building",
            resource_id=resource_id,
            audience_type=audience,
            created_by=admin_user.id,
        )
    await db_session.commit()

    # All links for this user
    all_links = await list_shared_links(db_session, created_by=admin_user.id)
    assert len(all_links) == 3

    # Filter by resource_type
    building_links = await list_shared_links(db_session, resource_type="building", created_by=admin_user.id)
    assert len(building_links) == 3


@pytest.mark.asyncio
async def test_create_link_with_allowed_sections(db_session, admin_user):
    """Create link with allowed_sections constraint."""
    sections = ["overview", "risk_analysis"]
    link = await create_shared_link(
        db_session,
        resource_type="passport",
        resource_id=uuid.uuid4(),
        audience_type="buyer",
        created_by=admin_user.id,
        allowed_sections=sections,
    )
    await db_session.commit()

    assert link.allowed_sections == sections


@pytest.mark.asyncio
async def test_get_shared_link_by_id(db_session, admin_user):
    """Get a shared link by ID."""
    link = await create_shared_link(
        db_session,
        resource_type="building",
        resource_id=uuid.uuid4(),
        audience_type="buyer",
        created_by=admin_user.id,
    )
    await db_session.commit()

    fetched = await get_shared_link(db_session, link.id)
    assert fetched is not None
    assert fetched.id == link.id


@pytest.mark.asyncio
async def test_get_shared_link_not_found(db_session):
    """Get returns None for non-existent ID."""
    result = await get_shared_link(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_validate_inactive_link_rejected(db_session, admin_user):
    """Validate inactive (revoked) link returns None."""
    link = await create_shared_link(
        db_session,
        resource_type="building",
        resource_id=uuid.uuid4(),
        audience_type="buyer",
        created_by=admin_user.id,
    )
    link.is_active = False
    await db_session.commit()

    validated = await validate_shared_link(db_session, link.token)
    assert validated is None


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_create_shared_link(client, db_session, admin_user, auth_headers):
    """POST /shared-links creates a link."""
    resource_id = uuid.uuid4()
    resp = await client.post(
        "/api/v1/shared-links",
        json={
            "resource_type": "building",
            "resource_id": str(resource_id),
            "audience_type": "buyer",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["resource_type"] == "building"
    assert data["audience_type"] == "buyer"
    assert data["is_active"] is True
    assert len(data["token"]) > 30


@pytest.mark.asyncio
async def test_api_list_shared_links(client, db_session, admin_user, auth_headers):
    """GET /shared-links lists user's links."""
    resource_id = uuid.uuid4()
    await client.post(
        "/api/v1/shared-links",
        json={
            "resource_type": "building",
            "resource_id": str(resource_id),
            "audience_type": "buyer",
        },
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/shared-links", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1


@pytest.mark.asyncio
async def test_api_access_shared_link(client, db_session, admin_user, auth_headers):
    """GET /shared/{token} validates and accesses a link (no auth)."""
    resource_id = uuid.uuid4()
    create_resp = await client.post(
        "/api/v1/shared-links",
        json={
            "resource_type": "passport",
            "resource_id": str(resource_id),
            "audience_type": "insurer",
            "allowed_sections": ["overview", "risk"],
        },
        headers=auth_headers,
    )
    token = create_resp.json()["token"]

    resp = await client.get(f"/api/v1/shared/{token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["resource_type"] == "passport"
    assert data["audience_type"] == "insurer"
    assert data["allowed_sections"] == ["overview", "risk"]


@pytest.mark.asyncio
async def test_api_access_invalid_token(client, db_session):
    """GET /shared/{token} with bad token returns is_valid=False."""
    resp = await client.get("/api/v1/shared/nonexistent-token-abc")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is False


@pytest.mark.asyncio
async def test_api_revoke_shared_link(client, db_session, admin_user, auth_headers):
    """DELETE /shared-links/{id} revokes the link."""
    resource_id = uuid.uuid4()
    create_resp = await client.post(
        "/api/v1/shared-links",
        json={
            "resource_type": "building",
            "resource_id": str(resource_id),
            "audience_type": "buyer",
        },
        headers=auth_headers,
    )
    link_id = create_resp.json()["id"]
    token = create_resp.json()["token"]

    # Revoke
    resp = await client.delete(f"/api/v1/shared-links/{link_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Verify no longer valid
    access_resp = await client.get(f"/api/v1/shared/{token}")
    assert access_resp.json()["is_valid"] is False
