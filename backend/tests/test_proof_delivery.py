"""BatiConnect — Proof Delivery tests (service-layer + route-level)."""

import hashlib
import uuid

import pytest

from app.api.proof_delivery import router as proof_delivery_router
from app.main import app
from app.models.proof_delivery import ProofDelivery
from app.services.proof_delivery_service import (
    compute_content_hash,
    create_delivery,
    get_deliveries_for_building,
    get_deliveries_for_target,
    get_delivery,
    mark_acknowledged,
    mark_delivered,
    mark_failed,
    mark_sent,
    mark_viewed,
)

# Register router for HTTP tests (not yet in router.py hub file)
app.include_router(proof_delivery_router, prefix="/api/v1")


# ---- Unit: compute_content_hash ----


def test_compute_content_hash_string():
    result = compute_content_hash("hello")
    expected = hashlib.sha256(b"hello").hexdigest()
    assert result == expected
    assert len(result) == 64


def test_compute_content_hash_bytes():
    data = b"\x00\x01\x02"
    result = compute_content_hash(data)
    expected = hashlib.sha256(data).hexdigest()
    assert result == expected


def test_compute_content_hash_deterministic():
    assert compute_content_hash("test") == compute_content_hash("test")


def test_compute_content_hash_different_inputs():
    assert compute_content_hash("a") != compute_content_hash("b")


# ---- Service-layer tests ----


@pytest.mark.asyncio
async def test_create_delivery_service(db_session, sample_building, admin_user):
    data = {
        "target_type": "document",
        "target_id": uuid.uuid4(),
        "audience": "owner",
        "delivery_method": "email",
        "recipient_email": "owner@example.ch",
    }
    delivery = await create_delivery(db_session, sample_building.id, data, created_by=admin_user.id)
    assert delivery.id is not None
    assert delivery.status == "queued"
    assert delivery.content_hash is not None
    assert len(delivery.content_hash) == 64
    assert delivery.building_id == sample_building.id
    assert delivery.created_by == admin_user.id


@pytest.mark.asyncio
async def test_create_delivery_with_explicit_hash(db_session, sample_building):
    data = {
        "target_type": "pack",
        "target_id": uuid.uuid4(),
        "audience": "authority",
        "delivery_method": "download",
        "content_hash": "a" * 64,
    }
    delivery = await create_delivery(db_session, sample_building.id, data)
    assert delivery.content_hash == "a" * 64


@pytest.mark.asyncio
async def test_get_delivery_service(db_session, sample_building):
    data = {
        "target_type": "document",
        "target_id": uuid.uuid4(),
        "audience": "insurer",
        "delivery_method": "api",
    }
    created = await create_delivery(db_session, sample_building.id, data)
    found = await get_delivery(db_session, created.id)
    assert found is not None
    assert found.id == created.id


@pytest.mark.asyncio
async def test_get_delivery_not_found(db_session):
    found = await get_delivery(db_session, uuid.uuid4())
    assert found is None


@pytest.mark.asyncio
async def test_get_deliveries_for_building(db_session, sample_building):
    target_id = uuid.uuid4()
    for audience in ["owner", "authority", "insurer"]:
        await create_delivery(
            db_session,
            sample_building.id,
            {
                "target_type": "document",
                "target_id": target_id,
                "audience": audience,
                "delivery_method": "email",
            },
        )
    deliveries = await get_deliveries_for_building(db_session, sample_building.id)
    assert len(deliveries) == 3


@pytest.mark.asyncio
async def test_get_deliveries_for_building_filter_audience(db_session, sample_building):
    target_id = uuid.uuid4()
    for audience in ["owner", "authority", "owner"]:
        await create_delivery(
            db_session,
            sample_building.id,
            {
                "target_type": "document",
                "target_id": target_id,
                "audience": audience,
                "delivery_method": "email",
            },
        )
    deliveries = await get_deliveries_for_building(db_session, sample_building.id, audience="owner")
    assert len(deliveries) == 2


@pytest.mark.asyncio
async def test_get_deliveries_for_building_filter_status(db_session, sample_building):
    d1 = await create_delivery(
        db_session,
        sample_building.id,
        {
            "target_type": "document",
            "target_id": uuid.uuid4(),
            "audience": "owner",
            "delivery_method": "email",
        },
    )
    await create_delivery(
        db_session,
        sample_building.id,
        {
            "target_type": "document",
            "target_id": uuid.uuid4(),
            "audience": "owner",
            "delivery_method": "email",
        },
    )
    await mark_sent(db_session, d1.id)
    deliveries = await get_deliveries_for_building(db_session, sample_building.id, status="sent")
    assert len(deliveries) == 1


@pytest.mark.asyncio
async def test_get_deliveries_for_target(db_session, sample_building):
    target_id = uuid.uuid4()
    for _ in range(2):
        await create_delivery(
            db_session,
            sample_building.id,
            {
                "target_type": "authority_pack",
                "target_id": target_id,
                "audience": "authority",
                "delivery_method": "email",
            },
        )
    # Different target
    await create_delivery(
        db_session,
        sample_building.id,
        {
            "target_type": "authority_pack",
            "target_id": uuid.uuid4(),
            "audience": "authority",
            "delivery_method": "email",
        },
    )
    deliveries = await get_deliveries_for_target(db_session, "authority_pack", target_id)
    assert len(deliveries) == 2


@pytest.mark.asyncio
async def test_mark_sent(db_session, sample_building):
    delivery = await create_delivery(
        db_session,
        sample_building.id,
        {
            "target_type": "document",
            "target_id": uuid.uuid4(),
            "audience": "owner",
            "delivery_method": "email",
        },
    )
    updated = await mark_sent(db_session, delivery.id)
    assert updated.status == "sent"
    assert updated.sent_at is not None


@pytest.mark.asyncio
async def test_mark_delivered(db_session, sample_building):
    delivery = await create_delivery(
        db_session,
        sample_building.id,
        {
            "target_type": "document",
            "target_id": uuid.uuid4(),
            "audience": "lender",
            "delivery_method": "api",
        },
    )
    await mark_sent(db_session, delivery.id)
    updated = await mark_delivered(db_session, delivery.id)
    assert updated.status == "delivered"
    assert updated.delivered_at is not None


@pytest.mark.asyncio
async def test_mark_viewed(db_session, sample_building):
    delivery = await create_delivery(
        db_session,
        sample_building.id,
        {
            "target_type": "pack",
            "target_id": uuid.uuid4(),
            "audience": "fiduciary",
            "delivery_method": "download",
        },
    )
    updated = await mark_viewed(db_session, delivery.id)
    assert updated.status == "viewed"
    assert updated.viewed_at is not None


@pytest.mark.asyncio
async def test_mark_acknowledged(db_session, sample_building):
    delivery = await create_delivery(
        db_session,
        sample_building.id,
        {
            "target_type": "transfer_package",
            "target_id": uuid.uuid4(),
            "audience": "contractor",
            "delivery_method": "handoff",
        },
    )
    updated = await mark_acknowledged(db_session, delivery.id)
    assert updated.status == "acknowledged"
    assert updated.acknowledged_at is not None


@pytest.mark.asyncio
async def test_mark_failed(db_session, sample_building):
    delivery = await create_delivery(
        db_session,
        sample_building.id,
        {
            "target_type": "document",
            "target_id": uuid.uuid4(),
            "audience": "owner",
            "delivery_method": "email",
        },
    )
    updated = await mark_failed(db_session, delivery.id, error_message="SMTP timeout")
    assert updated.status == "failed"
    assert updated.error_message == "SMTP timeout"


@pytest.mark.asyncio
async def test_mark_sent_with_notes(db_session, sample_building):
    delivery = await create_delivery(
        db_session,
        sample_building.id,
        {
            "target_type": "document",
            "target_id": uuid.uuid4(),
            "audience": "owner",
            "delivery_method": "email",
        },
    )
    updated = await mark_sent(db_session, delivery.id, notes="Sent via registered mail")
    assert updated.notes == "Sent via registered mail"


@pytest.mark.asyncio
async def test_mark_nonexistent_delivery(db_session):
    result = await mark_sent(db_session, uuid.uuid4())
    assert result is None
    result = await mark_delivered(db_session, uuid.uuid4())
    assert result is None
    result = await mark_viewed(db_session, uuid.uuid4())
    assert result is None
    result = await mark_acknowledged(db_session, uuid.uuid4())
    assert result is None
    result = await mark_failed(db_session, uuid.uuid4(), "err")
    assert result is None


@pytest.mark.asyncio
async def test_full_lifecycle(db_session, sample_building):
    """Test the full queued → sent → delivered → viewed → acknowledged lifecycle."""
    delivery = await create_delivery(
        db_session,
        sample_building.id,
        {
            "target_type": "authority_pack",
            "target_id": uuid.uuid4(),
            "audience": "authority",
            "delivery_method": "email",
            "recipient_email": "canton@vd.ch",
        },
    )
    assert delivery.status == "queued"

    delivery = await mark_sent(db_session, delivery.id)
    assert delivery.status == "sent"
    assert delivery.sent_at is not None

    delivery = await mark_delivered(db_session, delivery.id)
    assert delivery.status == "delivered"
    assert delivery.delivered_at is not None

    delivery = await mark_viewed(db_session, delivery.id)
    assert delivery.status == "viewed"
    assert delivery.viewed_at is not None

    delivery = await mark_acknowledged(db_session, delivery.id)
    assert delivery.status == "acknowledged"
    assert delivery.acknowledged_at is not None


# ---- Model-level tests ----


def test_proof_delivery_table_name():
    assert ProofDelivery.__tablename__ == "proof_deliveries"


def test_proof_delivery_has_provenance_columns():
    cols = {c.key for c in ProofDelivery.__table__.columns}
    assert "source_type" in cols
    assert "confidence" in cols
    assert "source_ref" in cols


# ---- Route-level tests ----


@pytest.mark.asyncio
async def test_create_proof_delivery_api(client, auth_headers, sample_building):
    target_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/proof-deliveries",
        json={
            "target_type": "document",
            "target_id": target_id,
            "audience": "owner",
            "delivery_method": "email",
            "recipient_email": "owner@test.ch",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "queued"
    assert data["target_id"] == target_id
    assert data["content_hash"] is not None


@pytest.mark.asyncio
async def test_list_proof_deliveries_api(client, auth_headers, sample_building):
    # Create two deliveries
    for _ in range(2):
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/proof-deliveries",
            json={
                "target_type": "document",
                "target_id": str(uuid.uuid4()),
                "audience": "owner",
                "delivery_method": "email",
            },
            headers=auth_headers,
        )
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/proof-deliveries",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_proof_delivery_api(client, auth_headers, sample_building):
    create_resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/proof-deliveries",
        json={
            "target_type": "pack",
            "target_id": str(uuid.uuid4()),
            "audience": "authority",
            "delivery_method": "download",
        },
        headers=auth_headers,
    )
    delivery_id = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/proof-deliveries/{delivery_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == delivery_id


@pytest.mark.asyncio
async def test_get_proof_delivery_not_found_api(client, auth_headers):
    resp = await client.get(f"/api/v1/proof-deliveries/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mark_sent_api(client, auth_headers, sample_building):
    create_resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/proof-deliveries",
        json={
            "target_type": "document",
            "target_id": str(uuid.uuid4()),
            "audience": "owner",
            "delivery_method": "email",
        },
        headers=auth_headers,
    )
    delivery_id = create_resp.json()["id"]
    resp = await client.post(f"/api/v1/proof-deliveries/{delivery_id}/sent", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "sent"


@pytest.mark.asyncio
async def test_mark_failed_api_requires_error_message(client, auth_headers, sample_building):
    create_resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/proof-deliveries",
        json={
            "target_type": "document",
            "target_id": str(uuid.uuid4()),
            "audience": "owner",
            "delivery_method": "email",
        },
        headers=auth_headers,
    )
    delivery_id = create_resp.json()["id"]
    # No error_message
    resp = await client.post(
        f"/api/v1/proof-deliveries/{delivery_id}/failed",
        json={"notes": "something"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_mark_failed_api_with_error(client, auth_headers, sample_building):
    create_resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/proof-deliveries",
        json={
            "target_type": "document",
            "target_id": str(uuid.uuid4()),
            "audience": "owner",
            "delivery_method": "email",
        },
        headers=auth_headers,
    )
    delivery_id = create_resp.json()["id"]
    resp = await client.post(
        f"/api/v1/proof-deliveries/{delivery_id}/failed",
        json={"error_message": "SMTP timeout", "notes": "Will retry"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"
    assert resp.json()["error_message"] == "SMTP timeout"


@pytest.mark.asyncio
async def test_lifecycle_via_api(client, auth_headers, sample_building):
    """Full lifecycle via API endpoints."""
    create_resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/proof-deliveries",
        json={
            "target_type": "authority_pack",
            "target_id": str(uuid.uuid4()),
            "audience": "authority",
            "delivery_method": "email",
            "recipient_email": "canton@vd.ch",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    delivery_id = create_resp.json()["id"]

    for transition in ["sent", "delivered", "viewed", "acknowledged"]:
        resp = await client.post(
            f"/api/v1/proof-deliveries/{delivery_id}/{transition}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == transition


@pytest.mark.asyncio
async def test_filter_by_audience_api(client, auth_headers, sample_building):
    for audience in ["owner", "authority", "owner"]:
        await client.post(
            f"/api/v1/buildings/{sample_building.id}/proof-deliveries",
            json={
                "target_type": "document",
                "target_id": str(uuid.uuid4()),
                "audience": audience,
                "delivery_method": "email",
            },
            headers=auth_headers,
        )
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/proof-deliveries?audience=owner",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ---- Schema tests ----


def test_trust_state_schema():
    from app.schemas.trust_semantics import TrustState

    ts = TrustState(confidence_level="auto_safe", freshness_state="current")
    assert ts.confidence_level == "auto_safe"
    assert ts.review_required is False


def test_trust_state_defaults():
    from app.schemas.trust_semantics import TrustState

    ts = TrustState()
    assert ts.confidence_level is None
    assert ts.freshness_state is None
    assert ts.identity_match_type is None
    assert ts.review_required is False


def test_trust_semantics_mixin_columns():
    from app.models.trust_semantics import TrustSemanticsMixin

    attrs = [
        "confidence_level",
        "confidence_reason",
        "freshness_state",
        "freshness_checked_at",
        "identity_match_type",
        "identity_match_confidence",
        "review_required",
        "review_reason",
        "reviewed_by_user_id",
        "reviewed_at",
    ]
    for attr in attrs:
        assert hasattr(TrustSemanticsMixin, attr), f"Missing mixin attr: {attr}"
