"""Tests for permit service."""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4

from app.models.permit import PermitStatus
from app.services.permit_service import (
    create_permit,
    delete_permit,
    get_building_permits,
    get_permit,
    get_permit_alerts,
    mark_expired_permits,
    update_permit,
)


@pytest.mark.asyncio
async def test_create_permit(db_session):
    """Test creating a new permit."""
    building_id = uuid4()
    now = datetime.now(UTC)
    issued_date = now - timedelta(days=30)
    expiry_date = now + timedelta(days=60)

    permit = await create_permit(
        db_session,
        building_id,
        permit_type="renovation",
        issued_date=issued_date,
        expiry_date=expiry_date,
        subsidy_amount=50000.0,
        notes="Test permit",
    )

    assert permit.id is not None
    assert permit.building_id == building_id
    assert permit.permit_type == "renovation"
    assert permit.status == PermitStatus.PENDING
    assert permit.subsidy_amount == 50000.0


@pytest.mark.asyncio
async def test_create_permit_invalid_dates(db_session):
    """Test creating permit with invalid dates raises error."""
    building_id = uuid4()
    now = datetime.now(UTC)

    with pytest.raises(ValueError, match="expiry_date must be greater"):
        await create_permit(
            db_session,
            building_id,
            permit_type="renovation",
            issued_date=now,
            expiry_date=now - timedelta(days=1),
        )


@pytest.mark.asyncio
async def test_get_permit(db_session):
    """Test retrieving a permit."""
    building_id = uuid4()
    now = datetime.now(UTC)

    permit = await create_permit(
        db_session,
        building_id,
        permit_type="subsidy",
        issued_date=now - timedelta(days=10),
        expiry_date=now + timedelta(days=20),
    )

    retrieved = await get_permit(db_session, permit.id)
    assert retrieved is not None
    assert retrieved.id == permit.id
    assert retrieved.permit_type == "subsidy"


@pytest.mark.asyncio
async def test_update_permit(db_session):
    """Test updating permit status."""
    building_id = uuid4()
    now = datetime.now(UTC)

    permit = await create_permit(
        db_session,
        building_id,
        permit_type="declaration",
        issued_date=now - timedelta(days=5),
        expiry_date=now + timedelta(days=25),
    )

    updated = await update_permit(
        db_session,
        permit.id,
        status=PermitStatus.APPROVED,
    )

    assert updated.status == PermitStatus.APPROVED


@pytest.mark.asyncio
async def test_delete_permit(db_session):
    """Test deleting a permit."""
    building_id = uuid4()
    now = datetime.now(UTC)

    permit = await create_permit(
        db_session,
        building_id,
        permit_type="renovation",
        issued_date=now - timedelta(days=30),
        expiry_date=now + timedelta(days=60),
    )

    success = await delete_permit(db_session, permit.id)
    assert success is True

    retrieved = await get_permit(db_session, permit.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_get_permit_alerts_expiring_soon(db_session):
    """Test alert generation for permits expiring within threshold."""
    building_id = uuid4()
    now = datetime.now(UTC)

    # Create permit expiring in 5 days (should alert)
    permit = await create_permit(
        db_session,
        building_id,
        permit_type="renovation",
        issued_date=now - timedelta(days=30),
        expiry_date=now + timedelta(days=5),
    )

    alerts = await get_permit_alerts(db_session, building_id)

    assert len(alerts) > 0
    alert = [a for a in alerts if a["permit_id"] == permit.id][0]
    assert alert["alert_level"] == "red"  # < 7 days
    assert alert["days_until_expiry"] == 5
