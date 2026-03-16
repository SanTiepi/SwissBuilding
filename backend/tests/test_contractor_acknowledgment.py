"""Tests for the Contractor Acknowledgment workflow."""

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.building import Building
from app.models.contractor_acknowledgment import ContractorAcknowledgment
from app.models.intervention import Intervention
from app.schemas.contractor_acknowledgment import ContractorAcknowledgmentCreate
from app.services.contractor_acknowledgment_service import (
    acknowledge,
    check_expired,
    create_acknowledgment,
    get_acknowledgment,
    get_intervention_ack_status,
    list_for_building,
    list_for_contractor,
    refuse,
    send_acknowledgment,
    view_acknowledgment,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAFETY_REQS = [
    {"item": "Full-face respirator required", "category": "PPE"},
    {"item": "Containment zone must be set up", "category": "site_prep"},
]


def _make_building(db_session, *, building_id=None, created_by=None):
    b = Building(
        id=building_id or uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=created_by,
        status="active",
    )
    db_session.add(b)
    return b


def _make_intervention(db_session, building_id, *, intervention_id=None):
    i = Intervention(
        id=intervention_id or uuid.uuid4(),
        building_id=building_id,
        intervention_type="asbestos_removal",
        title="Remove asbestos insulation",
        status="planned",
    )
    db_session.add(i)
    return i


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_acknowledgment_happy_path(db_session, admin_user):
    """Create an acknowledgment successfully."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    assert ack.status == "pending"
    assert ack.intervention_id == intervention.id
    assert ack.building_id == building.id
    assert ack.contractor_user_id == admin_user.id
    assert ack.safety_requirements == _SAFETY_REQS


@pytest.mark.asyncio
async def test_create_with_invalid_intervention(db_session, admin_user):
    """Creating with a non-existent intervention raises ValueError."""
    building = _make_building(db_session, created_by=admin_user.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=uuid.uuid4(),
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    with pytest.raises(ValueError, match="Intervention not found"):
        await create_acknowledgment(db_session, building.id, data, admin_user.id)


@pytest.mark.asyncio
async def test_create_with_wrong_building_intervention(db_session, admin_user):
    """Creating with an intervention from a different building raises ValueError."""
    building_a = _make_building(db_session, created_by=admin_user.id)
    building_b = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building_a.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    with pytest.raises(ValueError, match="Intervention not found"):
        await create_acknowledgment(db_session, building_b.id, data, admin_user.id)


@pytest.mark.asyncio
async def test_full_lifecycle_acknowledge(db_session, admin_user):
    """Full lifecycle: create -> send -> view -> acknowledge."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    # Send
    ack = await send_acknowledgment(db_session, ack.id)
    assert ack.status == "sent"
    assert ack.sent_at is not None
    await db_session.commit()

    # View
    ack = await view_acknowledgment(db_session, ack.id)
    assert ack.status == "viewed"
    assert ack.viewed_at is not None
    await db_session.commit()

    # Acknowledge
    ack = await acknowledge(db_session, ack.id, notes="All clear", ip_address="192.168.1.1")
    assert ack.status == "acknowledged"
    assert ack.acknowledged_at is not None
    assert ack.contractor_notes == "All clear"
    assert ack.ip_address == "192.168.1.1"
    assert ack.acknowledgment_hash is not None


@pytest.mark.asyncio
async def test_full_lifecycle_refuse(db_session, admin_user):
    """Full lifecycle: create -> send -> refuse."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    ack = await send_acknowledgment(db_session, ack.id)
    await db_session.commit()

    ack = await refuse(db_session, ack.id, reason="Missing PPE specification")
    assert ack.status == "refused"
    assert ack.refused_at is not None
    assert ack.refusal_reason == "Missing PPE specification"


@pytest.mark.asyncio
async def test_acknowledge_computes_correct_hash(db_session, admin_user):
    """Acknowledge computes SHA-256 hash matching manual computation."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    ack = await send_acknowledgment(db_session, ack.id)
    await db_session.commit()

    ack = await acknowledge(db_session, ack.id)
    expected_hash = hashlib.sha256(
        json.dumps(_SAFETY_REQS, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    assert ack.acknowledgment_hash == expected_hash


@pytest.mark.asyncio
async def test_expire_overdue_acks(db_session, admin_user):
    """Check_expired finds and expires overdue acknowledgments."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    # Create an ack that expired in the past
    ack = ContractorAcknowledgment(
        intervention_id=intervention.id,
        building_id=building.id,
        contractor_user_id=admin_user.id,
        status="sent",
        sent_at=datetime.now(UTC) - timedelta(days=10),
        safety_requirements=_SAFETY_REQS,
        expires_at=datetime.now(UTC) - timedelta(days=1),
        created_by=admin_user.id,
    )
    db_session.add(ack)
    await db_session.commit()

    expired = await check_expired(db_session)
    assert len(expired) == 1
    assert expired[0].status == "expired"


@pytest.mark.asyncio
async def test_expire_does_not_touch_acknowledged(db_session, admin_user):
    """Acknowledged acks are not expired even if past expires_at."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    ack = ContractorAcknowledgment(
        intervention_id=intervention.id,
        building_id=building.id,
        contractor_user_id=admin_user.id,
        status="acknowledged",
        safety_requirements=_SAFETY_REQS,
        expires_at=datetime.now(UTC) - timedelta(days=1),
        created_by=admin_user.id,
    )
    db_session.add(ack)
    await db_session.commit()

    expired = await check_expired(db_session)
    assert len(expired) == 0


@pytest.mark.asyncio
async def test_list_for_building(db_session, admin_user):
    """List acknowledgments for a building returns all acks."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    for _ in range(3):
        data = ContractorAcknowledgmentCreate(
            intervention_id=intervention.id,
            contractor_user_id=admin_user.id,
            safety_requirements=_SAFETY_REQS,
        )
        await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    items = await list_for_building(db_session, building.id)
    assert len(items) == 3


@pytest.mark.asyncio
async def test_list_for_contractor(db_session, admin_user):
    """List acknowledgments for a contractor user."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    items = await list_for_contractor(db_session, admin_user.id)
    assert len(items) == 1
    assert items[0].contractor_user_id == admin_user.id


@pytest.mark.asyncio
async def test_cannot_acknowledge_if_pending(db_session, admin_user):
    """Cannot acknowledge if status is still pending (not sent/viewed)."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    with pytest.raises(ValueError, match="Cannot acknowledge"):
        await acknowledge(db_session, ack.id)


@pytest.mark.asyncio
async def test_cannot_view_if_not_sent(db_session, admin_user):
    """Cannot view if status is not sent."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    with pytest.raises(ValueError, match="Cannot view"):
        await view_acknowledgment(db_session, ack.id)


@pytest.mark.asyncio
async def test_cannot_send_if_already_sent(db_session, admin_user):
    """Cannot send if already sent."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    await send_acknowledgment(db_session, ack.id)
    await db_session.commit()

    with pytest.raises(ValueError, match="Cannot send"):
        await send_acknowledgment(db_session, ack.id)


@pytest.mark.asyncio
async def test_intervention_ack_status_all_acknowledged(db_session, admin_user):
    """Get intervention ack status shows all_acknowledged=True when all acked."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    ack = await send_acknowledgment(db_session, ack.id)
    await db_session.commit()
    ack = await acknowledge(db_session, ack.id)
    await db_session.commit()

    status = await get_intervention_ack_status(db_session, intervention.id)
    assert status["all_acknowledged"] is True
    assert status["total"] == 1
    assert status["acknowledged"] == 1


@pytest.mark.asyncio
async def test_intervention_ack_status_partial(db_session, admin_user):
    """Get intervention ack status shows all_acknowledged=False when partial."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    # Create two acks, only acknowledge one
    for _ in range(2):
        data = ContractorAcknowledgmentCreate(
            intervention_id=intervention.id,
            contractor_user_id=admin_user.id,
            safety_requirements=_SAFETY_REQS,
        )
        await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    items = await list_for_building(db_session, building.id)
    # Send and acknowledge only the first one
    ack = await send_acknowledgment(db_session, items[0].id)
    await db_session.commit()
    await acknowledge(db_session, ack.id)
    await db_session.commit()

    status = await get_intervention_ack_status(db_session, intervention.id)
    assert status["all_acknowledged"] is False
    assert status["total"] == 2
    assert status["acknowledged"] == 1


@pytest.mark.asyncio
async def test_get_acknowledgment(db_session, admin_user):
    """Get a single acknowledgment by ID."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    fetched = await get_acknowledgment(db_session, ack.id)
    assert fetched is not None
    assert fetched.id == ack.id


@pytest.mark.asyncio
async def test_get_acknowledgment_not_found(db_session):
    """Get returns None for non-existent ID."""
    result = await get_acknowledgment(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_acknowledge_from_sent_directly(db_session, admin_user):
    """Can acknowledge directly from sent status (skipping view)."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    data = ContractorAcknowledgmentCreate(
        intervention_id=intervention.id,
        contractor_user_id=admin_user.id,
        safety_requirements=_SAFETY_REQS,
    )
    ack = await create_acknowledgment(db_session, building.id, data, admin_user.id)
    await db_session.commit()

    ack = await send_acknowledgment(db_session, ack.id)
    await db_session.commit()

    # Acknowledge directly from sent (skipping view)
    ack = await acknowledge(db_session, ack.id, notes="Understood")
    assert ack.status == "acknowledged"
    assert ack.contractor_notes == "Understood"


@pytest.mark.asyncio
async def test_api_create_endpoint(client, db_session, admin_user, auth_headers):
    """POST /buildings/{id}/contractor-acknowledgments creates via API."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/buildings/{building.id}/contractor-acknowledgments",
        json={
            "intervention_id": str(intervention.id),
            "contractor_user_id": str(admin_user.id),
            "safety_requirements": _SAFETY_REQS,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["building_id"] == str(building.id)
    assert data["intervention_id"] == str(intervention.id)


@pytest.mark.asyncio
async def test_api_list_building_endpoint(client, db_session, admin_user, auth_headers):
    """GET /buildings/{id}/contractor-acknowledgments lists acks."""
    building = _make_building(db_session, created_by=admin_user.id)
    intervention = _make_intervention(db_session, building.id)
    await db_session.commit()

    # Create one
    await client.post(
        f"/api/v1/buildings/{building.id}/contractor-acknowledgments",
        json={
            "intervention_id": str(intervention.id),
            "contractor_user_id": str(admin_user.id),
            "safety_requirements": _SAFETY_REQS,
        },
        headers=auth_headers,
    )

    resp = await client.get(
        f"/api/v1/buildings/{building.id}/contractor-acknowledgments",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert len(data["items"]) == 1
