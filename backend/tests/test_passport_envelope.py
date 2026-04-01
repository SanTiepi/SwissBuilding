"""Tests for the Building Passport Envelope service."""

import uuid

import pytest

from app.models.building import Building
from app.models.organization import Organization
from app.services.passport_envelope_service import (
    acknowledge_receipt,
    create_envelope,
    freeze_envelope,
    get_envelope_history,
    get_latest_envelope,
    publish_envelope,
    reimport_envelope,
    supersede_envelope,
    transfer_envelope,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_org(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db_session.add(org)
    return org


def _make_building(db_session, *, created_by=None, org_id=None):
    b = Building(
        id=uuid.uuid4(),
        address="Rue du Passeport 42",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        construction_year=1975,
        building_type="residential",
        created_by=created_by,
        organization_id=org_id,
        status="active",
    )
    db_session.add(b)
    return b


# ---------------------------------------------------------------------------
# Tests — create
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_envelope_happy_path(db_session, admin_user):
    """Create an envelope from a building's current passport state."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.commit()

    envelope = await create_envelope(
        db_session,
        building_id=building.id,
        org_id=org.id,
        created_by_id=admin_user.id,
    )
    await db_session.commit()

    assert envelope.status == "draft"
    assert envelope.version == 1
    assert envelope.is_sovereign is True
    assert envelope.content_hash is not None
    assert len(envelope.content_hash) == 64  # SHA-256
    assert envelope.passport_data is not None
    assert isinstance(envelope.sections_included, list)


@pytest.mark.asyncio
async def test_create_envelope_nonexistent_building(db_session, admin_user):
    """Create envelope for missing building raises ValueError."""
    fake_id = uuid.uuid4()
    org_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Building not found"):
        await create_envelope(
            db_session,
            building_id=fake_id,
            org_id=org_id,
            created_by_id=admin_user.id,
        )


@pytest.mark.asyncio
async def test_create_envelope_auto_increments_version(db_session, admin_user):
    """Second envelope for same building gets version 2."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.commit()

    env1 = await create_envelope(
        db_session,
        building_id=building.id,
        org_id=org.id,
        created_by_id=admin_user.id,
    )
    await db_session.commit()

    env2 = await create_envelope(
        db_session,
        building_id=building.id,
        org_id=org.id,
        created_by_id=admin_user.id,
    )
    await db_session.commit()

    assert env1.version == 1
    assert env2.version == 2
    # Old envelope should no longer be sovereign
    await db_session.refresh(env1)
    assert env1.is_sovereign is False
    assert env2.is_sovereign is True


@pytest.mark.asyncio
async def test_create_envelope_with_redaction(db_session, admin_user):
    """Create envelope with financial redaction profile."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.commit()

    envelope = await create_envelope(
        db_session,
        building_id=building.id,
        org_id=org.id,
        created_by_id=admin_user.id,
        redaction_profile="financial",
    )
    await db_session.commit()

    assert envelope.financials_redacted is True
    assert envelope.personal_data_redacted is False
    assert envelope.redaction_profile == "financial"


# ---------------------------------------------------------------------------
# Tests — lifecycle: freeze, publish
# ---------------------------------------------------------------------------


async def _create_test_envelope(db_session, admin_user):
    """Helper: create org + building + draft envelope, return (org, building, envelope)."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.commit()
    envelope = await create_envelope(db_session, building_id=building.id, org_id=org.id, created_by_id=admin_user.id)
    await db_session.commit()
    return org, building, envelope


@pytest.mark.asyncio
async def test_freeze_envelope(db_session, admin_user):
    """Freeze a draft envelope."""
    _org, _building, envelope = await _create_test_envelope(db_session, admin_user)

    frozen = await freeze_envelope(db_session, envelope.id, admin_user.id)
    await db_session.commit()

    assert frozen.status == "frozen"
    assert frozen.frozen_at is not None
    assert frozen.frozen_by_id == admin_user.id


@pytest.mark.asyncio
async def test_freeze_non_draft_raises(db_session, admin_user):
    """Cannot freeze an already frozen envelope."""
    _org, _building, envelope = await _create_test_envelope(db_session, admin_user)

    await freeze_envelope(db_session, envelope.id, admin_user.id)
    await db_session.commit()

    with pytest.raises(ValueError, match="Cannot freeze"):
        await freeze_envelope(db_session, envelope.id, admin_user.id)


@pytest.mark.asyncio
async def test_publish_envelope(db_session, admin_user):
    """Publish a frozen envelope."""
    _org, _building, envelope = await _create_test_envelope(db_session, admin_user)

    await freeze_envelope(db_session, envelope.id, admin_user.id)
    await db_session.commit()

    published = await publish_envelope(db_session, envelope.id, admin_user.id)
    await db_session.commit()

    assert published.status == "published"
    assert published.published_at is not None


@pytest.mark.asyncio
async def test_publish_non_frozen_raises(db_session, admin_user):
    """Cannot publish a draft envelope."""
    _org, _building, envelope = await _create_test_envelope(db_session, admin_user)

    with pytest.raises(ValueError, match="must be frozen"):
        await publish_envelope(db_session, envelope.id, admin_user.id)


# ---------------------------------------------------------------------------
# Tests — transfer and acknowledge
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transfer_and_acknowledge(db_session, admin_user):
    """Full flow: create -> freeze -> publish -> transfer -> acknowledge."""
    org, _building, envelope = await _create_test_envelope(db_session, admin_user)

    await freeze_envelope(db_session, envelope.id, admin_user.id)
    await db_session.commit()

    await publish_envelope(db_session, envelope.id, admin_user.id)
    await db_session.commit()

    receipt = await transfer_envelope(
        db_session,
        envelope_id=envelope.id,
        transferred_by_id=admin_user.id,
        sender_org_id=org.id,
        recipient_type="person",
        recipient_name="Marie Dupont",
        delivery_method="email",
    )
    await db_session.commit()

    assert receipt.delivery_method == "email"
    assert receipt.delivery_proof_hash is not None
    assert receipt.acknowledged is False

    # Acknowledge
    ack_receipt = await acknowledge_receipt(
        db_session,
        receipt_id=receipt.id,
        acknowledged_by_name="Marie Dupont",
    )
    await db_session.commit()

    assert ack_receipt.acknowledged is True
    assert ack_receipt.acknowledged_by_name == "Marie Dupont"
    assert ack_receipt.receipt_hash is not None

    # Envelope should also be updated
    await db_session.refresh(envelope)
    assert envelope.status == "acknowledged"


@pytest.mark.asyncio
async def test_transfer_draft_raises(db_session, admin_user):
    """Cannot transfer a draft envelope."""
    org, _building, envelope = await _create_test_envelope(db_session, admin_user)

    with pytest.raises(ValueError, match="must be published"):
        await transfer_envelope(
            db_session,
            envelope_id=envelope.id,
            transferred_by_id=admin_user.id,
            sender_org_id=org.id,
            recipient_type="person",
            recipient_name="Test",
        )


# ---------------------------------------------------------------------------
# Tests — supersede
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_supersede_envelope(db_session, admin_user):
    """Supersede an old envelope with a new one."""
    org, building, env_old = await _create_test_envelope(db_session, admin_user)

    env_new = await create_envelope(db_session, building_id=building.id, org_id=org.id, created_by_id=admin_user.id)
    await db_session.commit()

    await supersede_envelope(db_session, env_old.id, env_new.id)
    await db_session.commit()

    await db_session.refresh(env_old)
    await db_session.refresh(env_new)

    assert env_old.status == "superseded"
    assert env_old.is_sovereign is False
    assert env_new.supersedes_id == env_old.id
    assert env_new.is_sovereign is True


# ---------------------------------------------------------------------------
# Tests — reimport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reimport_envelope(db_session, admin_user):
    """Re-import an exported envelope into a building."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.commit()

    envelope_data = {
        "version": 3,
        "passport_data": {
            "building_id": str(uuid.uuid4()),
            "passport_grade": "B",
            "knowledge_state": {"overall_trust": 0.72},
        },
        "sections_included": ["knowledge_state", "passport_grade"],
        "content_hash": "abc123",
        "redaction_profile": "none",
    }

    imported = await reimport_envelope(
        db_session,
        envelope_data=envelope_data,
        building_id=building.id,
        imported_by_id=admin_user.id,
        org_id=org.id,
    )
    await db_session.commit()

    assert imported.version == 1
    assert imported.status == "frozen"  # imported envelopes are immutable
    assert imported.is_sovereign is False
    assert "Imported from previous owner" in imported.version_label


# ---------------------------------------------------------------------------
# Tests — queries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_envelope_history(db_session, admin_user):
    """Get version history returns all envelopes ordered by version desc."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.commit()

    for _ in range(3):
        await create_envelope(db_session, building_id=building.id, org_id=org.id, created_by_id=admin_user.id)
        await db_session.commit()

    history = await get_envelope_history(db_session, building.id)
    assert len(history) == 3
    assert history[0].version == 3
    assert history[2].version == 1


@pytest.mark.asyncio
async def test_get_latest_envelope(db_session, admin_user):
    """Get latest sovereign envelope."""
    org = _make_org(db_session)
    building = _make_building(db_session, created_by=admin_user.id, org_id=org.id)
    await db_session.commit()

    await create_envelope(db_session, building_id=building.id, org_id=org.id, created_by_id=admin_user.id)
    await db_session.commit()

    env2 = await create_envelope(db_session, building_id=building.id, org_id=org.id, created_by_id=admin_user.id)
    await db_session.commit()

    latest = await get_latest_envelope(db_session, building.id)
    assert latest is not None
    assert latest.id == env2.id
    assert latest.is_sovereign is True


@pytest.mark.asyncio
async def test_get_latest_envelope_none(db_session, admin_user):
    """Returns None when no envelopes exist for building."""
    result = await get_latest_envelope(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_double_acknowledge_raises(db_session, admin_user):
    """Cannot acknowledge the same receipt twice."""
    org, _building, envelope = await _create_test_envelope(db_session, admin_user)

    await freeze_envelope(db_session, envelope.id, admin_user.id)
    await db_session.commit()

    await publish_envelope(db_session, envelope.id, admin_user.id)
    await db_session.commit()

    receipt = await transfer_envelope(
        db_session,
        envelope_id=envelope.id,
        transferred_by_id=admin_user.id,
        sender_org_id=org.id,
        recipient_type="organization",
        recipient_name="Buyer Corp",
    )
    await db_session.commit()

    await acknowledge_receipt(db_session, receipt.id, "Buyer Corp")
    await db_session.commit()

    with pytest.raises(ValueError, match="already acknowledged"):
        await acknowledge_receipt(db_session, receipt.id, "Buyer Corp")
