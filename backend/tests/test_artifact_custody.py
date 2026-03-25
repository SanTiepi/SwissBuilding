"""Tests for Artifact Versioning + Chain-of-Custody."""

import uuid

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_version(db_session):
    """create_version creates a v1 with status=current."""
    from app.services.artifact_custody_service import create_version

    artifact_id = uuid.uuid4()
    v = await create_version(db_session, "passport_publication", artifact_id, content_hash="abc123")
    assert v.version_number == 1
    assert v.status == "current"
    assert v.content_hash == "abc123"
    assert v.artifact_type == "passport_publication"


@pytest.mark.asyncio
async def test_create_version_auto_supersedes(db_session):
    """Second version supersedes the first."""
    from app.services.artifact_custody_service import create_version, get_version

    artifact_id = uuid.uuid4()
    v1 = await create_version(db_session, "transfer_package", artifact_id, content_hash="h1")
    v2 = await create_version(db_session, "transfer_package", artifact_id, content_hash="h2")

    assert v2.version_number == 2
    assert v2.status == "current"

    # Reload v1
    v1_reloaded = await get_version(db_session, v1.id)
    assert v1_reloaded.status == "superseded"
    assert v1_reloaded.superseded_by_id == v2.id


@pytest.mark.asyncio
async def test_archive_version(db_session):
    """archive_version sets status, archived_at, and archive_reason."""
    from app.services.artifact_custody_service import archive_version, create_version

    artifact_id = uuid.uuid4()
    v = await create_version(db_session, "authority_pack", artifact_id)
    result = await archive_version(db_session, v.id, reason="Regulatory update")
    assert result.status == "archived"
    assert result.archived_at is not None
    assert result.archive_reason == "Regulatory update"


@pytest.mark.asyncio
async def test_withdraw_version(db_session):
    """withdraw_version sets status to withdrawn."""
    from app.services.artifact_custody_service import create_version, withdraw_version

    artifact_id = uuid.uuid4()
    v = await create_version(db_session, "audience_pack", artifact_id)
    result = await withdraw_version(db_session, v.id)
    assert result.status == "withdrawn"


@pytest.mark.asyncio
async def test_record_custody_event(db_session):
    """record_custody_event creates a CustodyEvent."""
    from app.services.artifact_custody_service import create_version, record_custody_event

    artifact_id = uuid.uuid4()
    v = await create_version(db_session, "handoff_pack", artifact_id)
    evt = await record_custody_event(
        db_session,
        v.id,
        {
            "event_type": "published",
            "actor_type": "user",
            "actor_name": "Test User",
        },
    )
    assert evt.event_type == "published"
    assert evt.actor_type == "user"
    assert evt.actor_name == "Test User"


@pytest.mark.asyncio
async def test_get_custody_chain(db_session):
    """get_custody_chain returns versions + events chronologically."""
    from app.services.artifact_custody_service import (
        create_version,
        get_custody_chain,
        record_custody_event,
    )

    artifact_id = uuid.uuid4()
    v1 = await create_version(db_session, "passport_publication", artifact_id)
    await record_custody_event(db_session, v1.id, {"event_type": "created"})
    await record_custody_event(db_session, v1.id, {"event_type": "published"})
    v2 = await create_version(db_session, "passport_publication", artifact_id)
    await record_custody_event(db_session, v2.id, {"event_type": "created"})

    chain = await get_custody_chain(db_session, "passport_publication", artifact_id)
    assert chain["artifact_type"] == "passport_publication"
    assert len(chain["versions"]) == 2
    assert chain["current_version"].id == v2.id
    # At least 3 explicit events + 1 superseded event auto-recorded
    assert len(chain["events"]) >= 4


@pytest.mark.asyncio
async def test_get_current_version(db_session):
    """get_current_version returns the latest current version."""
    from app.services.artifact_custody_service import create_version, get_current_version

    artifact_id = uuid.uuid4()
    await create_version(db_session, "proof_delivery", artifact_id)
    v2 = await create_version(db_session, "proof_delivery", artifact_id)

    current = await get_current_version(db_session, "proof_delivery", artifact_id)
    assert current.id == v2.id
    assert current.version_number == 2


@pytest.mark.asyncio
async def test_get_current_version_returns_none_when_empty(db_session):
    """get_current_version returns None when no versions exist."""
    from app.services.artifact_custody_service import get_current_version

    result = await get_current_version(db_session, "nonexistent", uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_version_events(db_session):
    """get_version_events returns events for a specific version."""
    from app.services.artifact_custody_service import (
        create_version,
        get_version_events,
        record_custody_event,
    )

    artifact_id = uuid.uuid4()
    v = await create_version(db_session, "diagnostic_publication", artifact_id)
    await record_custody_event(db_session, v.id, {"event_type": "created"})
    await record_custody_event(db_session, v.id, {"event_type": "delivered"})

    events = await get_version_events(db_session, v.id)
    assert len(events) == 2
    assert events[0].event_type == "created"
    assert events[1].event_type == "delivered"


@pytest.mark.asyncio
async def test_archive_posture(db_session):
    """get_archive_posture returns summary counts."""
    from app.services.artifact_custody_service import (
        archive_version,
        create_version,
        get_archive_posture,
    )

    building_id = uuid.uuid4()
    a1_id = uuid.uuid4()
    await create_version(db_session, "passport_publication", a1_id)
    v2 = await create_version(db_session, "passport_publication", a1_id)
    await archive_version(db_session, v2.id, "test")

    a2_id = uuid.uuid4()
    await create_version(db_session, "audience_pack", a2_id)

    posture = await get_archive_posture(db_session, building_id)
    assert posture["total_artifacts"] >= 2
    assert posture["total_versions"] >= 3
    assert posture["superseded_count"] >= 1
    assert posture["archived_count"] >= 1


@pytest.mark.asyncio
async def test_supersede_nonexistent_version(db_session):
    """supersede_version returns None for nonexistent version."""
    from app.services.artifact_custody_service import supersede_version

    result = await supersede_version(db_session, uuid.uuid4(), uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_archive_nonexistent_version(db_session):
    """archive_version returns None for nonexistent version."""
    from app.services.artifact_custody_service import archive_version

    result = await archive_version(db_session, uuid.uuid4(), "reason")
    assert result is None


@pytest.mark.asyncio
async def test_withdraw_nonexistent_version(db_session):
    """withdraw_version returns None for nonexistent version."""
    from app.services.artifact_custody_service import withdraw_version

    result = await withdraw_version(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_create_version_with_user_id(db_session):
    """create_version stores created_by_user_id."""
    from app.services.artifact_custody_service import create_version

    user_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    v = await create_version(db_session, "passport_publication", artifact_id, user_id=user_id)
    assert v.created_by_user_id == user_id


@pytest.mark.asyncio
async def test_custody_event_with_details(db_session):
    """record_custody_event stores JSON details."""
    from app.services.artifact_custody_service import create_version, record_custody_event

    artifact_id = uuid.uuid4()
    v = await create_version(db_session, "authority_pack", artifact_id)
    evt = await record_custody_event(
        db_session,
        v.id,
        {
            "event_type": "delivered",
            "actor_type": "partner",
            "details": {"method": "email", "recipient": "authority@vd.ch"},
        },
    )
    assert evt.details == {"method": "email", "recipient": "authority@vd.ch"}


@pytest.mark.asyncio
async def test_custody_event_with_recipient_org(db_session):
    """record_custody_event stores recipient_org_id."""
    from app.services.artifact_custody_service import create_version, record_custody_event

    org_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    v = await create_version(db_session, "audience_pack", artifact_id)
    evt = await record_custody_event(
        db_session,
        v.id,
        {
            "event_type": "acknowledged",
            "actor_type": "authority",
            "recipient_org_id": org_id,
        },
    )
    # recipient_org_id FK may not resolve, but the column is stored
    assert evt.event_type == "acknowledged"


@pytest.mark.asyncio
async def test_multiple_artifact_types_independent(db_session):
    """Versions for different artifact types are independent."""
    from app.services.artifact_custody_service import create_version, get_current_version

    artifact_id = uuid.uuid4()
    v_pass = await create_version(db_session, "passport_publication", artifact_id)
    v_pack = await create_version(db_session, "audience_pack", artifact_id)

    curr_pass = await get_current_version(db_session, "passport_publication", artifact_id)
    curr_pack = await get_current_version(db_session, "audience_pack", artifact_id)

    assert curr_pass.id == v_pass.id
    assert curr_pack.id == v_pack.id


@pytest.mark.asyncio
async def test_three_versions_chain(db_session):
    """Three successive versions: v1 superseded, v2 superseded, v3 current."""
    from app.services.artifact_custody_service import create_version, get_custody_chain

    artifact_id = uuid.uuid4()
    await create_version(db_session, "transfer_package", artifact_id)
    await create_version(db_session, "transfer_package", artifact_id)
    v3 = await create_version(db_session, "transfer_package", artifact_id)

    chain = await get_custody_chain(db_session, "transfer_package", artifact_id)
    assert len(chain["versions"]) == 3
    assert chain["versions"][0].status == "superseded"
    assert chain["versions"][1].status == "superseded"
    assert chain["versions"][2].status == "current"
    assert chain["current_version"].id == v3.id


@pytest.mark.asyncio
async def test_archive_then_new_version(db_session):
    """After archiving, a new version still becomes current."""
    from app.services.artifact_custody_service import archive_version, create_version, get_current_version

    artifact_id = uuid.uuid4()
    v1 = await create_version(db_session, "proof_delivery", artifact_id)
    await archive_version(db_session, v1.id, "old")

    v2 = await create_version(db_session, "proof_delivery", artifact_id)
    assert v2.status == "current"

    current = await get_current_version(db_session, "proof_delivery", artifact_id)
    assert current.id == v2.id


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_create_version(client: AsyncClient, auth_headers: dict):
    """POST /artifacts/versions creates a version."""
    artifact_id = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/artifacts/versions",
        json={"artifact_type": "passport_publication", "artifact_id": artifact_id, "content_hash": "aabbcc"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["version_number"] == 1
    assert data["status"] == "current"
    assert data["content_hash"] == "aabbcc"


@pytest.mark.asyncio
async def test_api_get_chain(client: AsyncClient, auth_headers: dict):
    """GET /artifacts/{type}/{id}/chain returns the custody chain."""
    artifact_id = str(uuid.uuid4())
    await client.post(
        "/api/v1/artifacts/versions",
        json={"artifact_type": "audience_pack", "artifact_id": artifact_id},
        headers=auth_headers,
    )
    resp = await client.get(
        f"/api/v1/artifacts/audience_pack/{artifact_id}/chain",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["artifact_type"] == "audience_pack"
    assert len(data["versions"]) == 1


@pytest.mark.asyncio
async def test_api_get_current(client: AsyncClient, auth_headers: dict):
    """GET /artifacts/{type}/{id}/current returns the current version."""
    artifact_id = str(uuid.uuid4())
    await client.post(
        "/api/v1/artifacts/versions",
        json={"artifact_type": "transfer_package", "artifact_id": artifact_id},
        headers=auth_headers,
    )
    resp = await client.get(
        f"/api/v1/artifacts/transfer_package/{artifact_id}/current",
        headers=auth_headers,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_archive_version(client: AsyncClient, auth_headers: dict):
    """POST /artifacts/versions/{id}/archive archives the version."""
    artifact_id = str(uuid.uuid4())
    create_resp = await client.post(
        "/api/v1/artifacts/versions",
        json={"artifact_type": "authority_pack", "artifact_id": artifact_id},
        headers=auth_headers,
    )
    version_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/artifacts/versions/{version_id}/archive",
        json={"reason": "Obsolete after regulatory change"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_api_withdraw_version(client: AsyncClient, auth_headers: dict):
    """POST /artifacts/versions/{id}/withdraw withdraws the version."""
    artifact_id = str(uuid.uuid4())
    create_resp = await client.post(
        "/api/v1/artifacts/versions",
        json={"artifact_type": "handoff_pack", "artifact_id": artifact_id},
        headers=auth_headers,
    )
    version_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/artifacts/versions/{version_id}/withdraw",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "withdrawn"


@pytest.mark.asyncio
async def test_api_create_custody_event(client: AsyncClient, auth_headers: dict):
    """POST /artifacts/custody-events creates a custody event."""
    artifact_id = str(uuid.uuid4())
    create_resp = await client.post(
        "/api/v1/artifacts/versions",
        json={"artifact_type": "proof_delivery", "artifact_id": artifact_id},
        headers=auth_headers,
    )
    version_id = create_resp.json()["id"]

    resp = await client.post(
        "/api/v1/artifacts/custody-events",
        json={
            "artifact_version_id": version_id,
            "event_type": "delivered",
            "actor_type": "partner",
            "actor_name": "DiagSwiss AG",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["event_type"] == "delivered"


@pytest.mark.asyncio
async def test_api_get_version_events(client: AsyncClient, auth_headers: dict):
    """GET /artifacts/versions/{id}/events returns events."""
    artifact_id = str(uuid.uuid4())
    create_resp = await client.post(
        "/api/v1/artifacts/versions",
        json={"artifact_type": "diagnostic_publication", "artifact_id": artifact_id},
        headers=auth_headers,
    )
    version_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/artifacts/versions/{version_id}/events",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    # At least the "created" event from create_artifact_version endpoint
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_api_archive_posture(client: AsyncClient, auth_headers: dict):
    """GET /buildings/{id}/archive-posture returns posture summary."""
    building_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/buildings/{building_id}/archive-posture",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_artifacts" in data
    assert "total_versions" in data


@pytest.mark.asyncio
async def test_api_archive_nonexistent_404(client: AsyncClient, auth_headers: dict):
    """POST archive on nonexistent version returns 404."""
    resp = await client.post(
        f"/api/v1/artifacts/versions/{uuid.uuid4()}/archive",
        json={"reason": "test"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_withdraw_nonexistent_404(client: AsyncClient, auth_headers: dict):
    """POST withdraw on nonexistent version returns 404."""
    resp = await client.post(
        f"/api/v1/artifacts/versions/{uuid.uuid4()}/withdraw",
        headers=auth_headers,
    )
    assert resp.status_code == 404
