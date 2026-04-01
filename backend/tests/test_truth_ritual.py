"""Tests for the Truth Rituals service."""

import uuid

import pytest

from app.models.building import Building
from app.models.organization import Organization
from app.models.user import User
from app.services.ritual_service import (
    acknowledge,
    compute_content_hash,
    freeze,
    get_ritual_history,
    publish,
    receipt,
    reopen,
    supersede,
    transfer,
    validate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ORG_ID = uuid.uuid4()
_USER_ID = uuid.uuid4()
_BUILDING_ID = uuid.uuid4()


def _make_org(db_session):
    org = Organization(
        id=_ORG_ID,
        name="Test Org",
        type="diagnostic_lab",
    )
    db_session.add(org)
    return org


def _make_user(db_session):
    u = User(
        id=_USER_ID,
        email="ritual@test.ch",
        password_hash="$2b$12$LJ3m4ys3Lg2nkMYOkbQ.eOGOzRSaEntYBtcnGYMBzQMJkPYNq6b1a",
        first_name="Ritual",
        last_name="Tester",
        role="admin",
        organization_id=_ORG_ID,
    )
    db_session.add(u)
    return u


def _make_building(db_session):
    b = Building(
        id=_BUILDING_ID,
        address="Rue Rituel 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=_USER_ID,
        status="active",
    )
    db_session.add(b)
    return b


async def _setup(db_session):
    _make_org(db_session)
    _make_user(db_session)
    _make_building(db_session)
    await db_session.flush()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_ritual(db_session):
    await _setup(db_session)
    target_id = uuid.uuid4()
    ritual = await validate(
        db_session,
        building_id=_BUILDING_ID,
        target_type="evidence",
        target_id=target_id,
        validated_by_id=_USER_ID,
        org_id=_ORG_ID,
        reason="Expert review passed",
    )
    assert ritual.ritual_type == "validate"
    assert ritual.performed_by_id == _USER_ID
    assert ritual.target_type == "evidence"
    assert ritual.target_id == target_id
    assert ritual.reason == "Expert review passed"
    assert ritual.performed_at is not None


@pytest.mark.asyncio
async def test_freeze_with_hash(db_session):
    await _setup(db_session)
    target_id = uuid.uuid4()
    content = {"pollutant": "asbestos", "level": "high"}
    ritual = await freeze(
        db_session,
        building_id=_BUILDING_ID,
        target_type="document",
        target_id=target_id,
        frozen_by_id=_USER_ID,
        org_id=_ORG_ID,
        content=content,
        reason="Locked for submission",
    )
    assert ritual.ritual_type == "freeze"
    assert ritual.content_hash is not None
    assert len(ritual.content_hash) == 64
    assert ritual.content_hash == compute_content_hash(content)


@pytest.mark.asyncio
async def test_publish_increments_version(db_session):
    await _setup(db_session)
    target_id = uuid.uuid4()
    r1 = await publish(
        db_session,
        building_id=_BUILDING_ID,
        target_type="passport",
        target_id=target_id,
        published_by_id=_USER_ID,
        org_id=_ORG_ID,
    )
    assert r1.version == 1

    r2 = await publish(
        db_session,
        building_id=_BUILDING_ID,
        target_type="passport",
        target_id=target_id,
        published_by_id=_USER_ID,
        org_id=_ORG_ID,
    )
    assert r2.version == 2


@pytest.mark.asyncio
async def test_transfer_ritual(db_session):
    await _setup(db_session)
    target_id = uuid.uuid4()
    recipient_id = uuid.uuid4()
    ritual = await transfer(
        db_session,
        building_id=_BUILDING_ID,
        target_type="pack",
        target_id=target_id,
        transferred_by_id=_USER_ID,
        org_id=_ORG_ID,
        recipient_type="authority",
        recipient_id=recipient_id,
        delivery_method="email",
    )
    assert ritual.ritual_type == "transfer"
    assert ritual.recipient_type == "authority"
    assert ritual.recipient_id == recipient_id
    assert ritual.delivery_method == "email"


@pytest.mark.asyncio
async def test_acknowledge_ritual(db_session):
    await _setup(db_session)
    target_id = uuid.uuid4()
    ritual = await acknowledge(
        db_session,
        building_id=_BUILDING_ID,
        target_type="pack",
        target_id=target_id,
        acknowledged_by_id=_USER_ID,
        org_id=_ORG_ID,
        receipt_hash="abc123def456",
    )
    assert ritual.ritual_type == "acknowledge"
    assert ritual.acknowledged_by_id == _USER_ID
    assert ritual.receipt_hash == "abc123def456"


@pytest.mark.asyncio
async def test_reopen_requires_reason(db_session):
    await _setup(db_session)
    target_id = uuid.uuid4()
    with pytest.raises(ValueError, match="non-empty reason"):
        await reopen(
            db_session,
            building_id=_BUILDING_ID,
            target_type="document",
            target_id=target_id,
            reopened_by_id=_USER_ID,
            org_id=_ORG_ID,
            reason="",
        )


@pytest.mark.asyncio
async def test_reopen_with_reason(db_session):
    await _setup(db_session)
    target_id = uuid.uuid4()
    ritual = await reopen(
        db_session,
        building_id=_BUILDING_ID,
        target_type="document",
        target_id=target_id,
        reopened_by_id=_USER_ID,
        org_id=_ORG_ID,
        reason="New evidence found",
    )
    assert ritual.ritual_type == "reopen"
    assert ritual.reopen_reason == "New evidence found"
    assert ritual.reason == "New evidence found"


@pytest.mark.asyncio
async def test_supersede_links_old_to_new(db_session):
    await _setup(db_session)
    old_id = uuid.uuid4()
    new_id = uuid.uuid4()
    ritual = await supersede(
        db_session,
        building_id=_BUILDING_ID,
        target_type="publication",
        target_id=old_id,
        superseded_by_id=_USER_ID,
        org_id=_ORG_ID,
        new_target_id=new_id,
        reason="Updated diagnostic results",
    )
    assert ritual.ritual_type == "supersede"
    assert ritual.target_id == old_id
    assert ritual.supersedes_id == new_id


@pytest.mark.asyncio
async def test_receipt_ritual(db_session):
    await _setup(db_session)
    target_id = uuid.uuid4()
    recipient_id = uuid.uuid4()
    hash_val = compute_content_hash({"delivered": True})
    ritual = await receipt(
        db_session,
        building_id=_BUILDING_ID,
        target_type="pack",
        target_id=target_id,
        recipient_id=recipient_id,
        org_id=_ORG_ID,
        receipt_hash=hash_val,
        delivery_method="download",
        performed_by_id=_USER_ID,
    )
    assert ritual.ritual_type == "receipt"
    assert ritual.receipt_hash == hash_val
    assert ritual.delivery_method == "download"


@pytest.mark.asyncio
async def test_get_ritual_history(db_session):
    await _setup(db_session)
    target_id = uuid.uuid4()
    await validate(
        db_session,
        building_id=_BUILDING_ID,
        target_type="evidence",
        target_id=target_id,
        validated_by_id=_USER_ID,
        org_id=_ORG_ID,
    )
    await freeze(
        db_session,
        building_id=_BUILDING_ID,
        target_type="evidence",
        target_id=target_id,
        frozen_by_id=_USER_ID,
        org_id=_ORG_ID,
    )
    history = await get_ritual_history(db_session, building_id=_BUILDING_ID)
    assert len(history) == 2

    # Filter by type
    validates = await get_ritual_history(db_session, building_id=_BUILDING_ID, ritual_type="validate")
    assert len(validates) == 1
    assert validates[0].ritual_type == "validate"


@pytest.mark.asyncio
async def test_invalid_ritual_type(db_session):
    await _setup(db_session)
    with pytest.raises(ValueError, match="Invalid target_type"):
        await validate(
            db_session,
            building_id=_BUILDING_ID,
            target_type="invalid_type",
            target_id=uuid.uuid4(),
            validated_by_id=_USER_ID,
            org_id=_ORG_ID,
        )


def test_compute_content_hash_deterministic():
    content = {"b": 2, "a": 1}
    h1 = compute_content_hash(content)
    h2 = compute_content_hash(content)
    assert h1 == h2
    assert len(h1) == 64


def test_compute_content_hash_string():
    h = compute_content_hash("hello world")
    assert len(h) == 64
