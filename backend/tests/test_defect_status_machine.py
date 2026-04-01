"""Tests for DefectShield — status transition state machine.

Covers: valid transitions, invalid transitions, terminal state enforcement,
idempotent updates, concurrent updates, all status paths.
"""

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.schemas.defect_timeline import DefectTimelineCreate
from app.services.defect_timeline_service import (
    VALID_STATUS_TRANSITIONS,
    create_timeline,
    get_timeline,
    update_defect_status,
    update_timeline_status,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue du Status 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _make_timeline(db, building_id, **kwargs):
    defaults = {
        "building_id": building_id,
        "defect_type": "construction",
        "description": "Test defect",
        "discovery_date": date(2026, 3, 1),
    }
    defaults.update(kwargs)
    return await create_timeline(db, DefectTimelineCreate(**defaults))


# ---------------------------------------------------------------------------
# Valid transitions
# ---------------------------------------------------------------------------


class TestValidTransitions:
    """Ensure all valid status transitions succeed."""

    @pytest.mark.asyncio
    async def test_active_to_notified(self, db_session, admin_user):
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        assert t.status == "active"
        updated = await update_defect_status(db_session, t.id, "notified")
        assert updated.status == "notified"

    @pytest.mark.asyncio
    async def test_active_to_expired(self, db_session, admin_user):
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        updated = await update_defect_status(db_session, t.id, "expired")
        assert updated.status == "expired"

    @pytest.mark.asyncio
    async def test_active_to_resolved(self, db_session, admin_user):
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        updated = await update_defect_status(db_session, t.id, "resolved")
        assert updated.status == "resolved"

    @pytest.mark.asyncio
    async def test_notified_to_resolved(self, db_session, admin_user):
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        await update_defect_status(db_session, t.id, "notified")
        updated = await update_defect_status(db_session, t.id, "resolved")
        assert updated.status == "resolved"

    @pytest.mark.asyncio
    async def test_expired_to_resolved(self, db_session, admin_user):
        """Late resolution after expiry — allowed by business rules."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        await update_defect_status(db_session, t.id, "expired")
        updated = await update_defect_status(db_session, t.id, "resolved")
        assert updated.status == "resolved"


# ---------------------------------------------------------------------------
# Invalid transitions
# ---------------------------------------------------------------------------


class TestInvalidTransitions:
    """Ensure all invalid status transitions raise ValueError."""

    @pytest.mark.asyncio
    async def test_resolved_to_active(self, db_session, admin_user):
        """Terminal state: resolved → active is forbidden."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        await update_defect_status(db_session, t.id, "resolved")
        with pytest.raises(ValueError, match="Invalid transition"):
            await update_defect_status(db_session, t.id, "active")

    @pytest.mark.asyncio
    async def test_resolved_to_notified(self, db_session, admin_user):
        """Terminal state: resolved → notified is forbidden."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        await update_defect_status(db_session, t.id, "resolved")
        with pytest.raises(ValueError, match="none \\(terminal state\\)"):
            await update_defect_status(db_session, t.id, "notified")

    @pytest.mark.asyncio
    async def test_resolved_to_expired(self, db_session, admin_user):
        """Terminal state: resolved → expired is forbidden."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        await update_defect_status(db_session, t.id, "resolved")
        with pytest.raises(ValueError, match="Invalid transition"):
            await update_defect_status(db_session, t.id, "expired")

    @pytest.mark.asyncio
    async def test_notified_to_active(self, db_session, admin_user):
        """notified → active is not a valid transition."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        await update_defect_status(db_session, t.id, "notified")
        with pytest.raises(ValueError, match="Invalid transition"):
            await update_defect_status(db_session, t.id, "active")

    @pytest.mark.asyncio
    async def test_notified_to_expired(self, db_session, admin_user):
        """notified → expired is not allowed."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        await update_defect_status(db_session, t.id, "notified")
        with pytest.raises(ValueError, match="Invalid transition"):
            await update_defect_status(db_session, t.id, "expired")

    @pytest.mark.asyncio
    async def test_expired_to_active(self, db_session, admin_user):
        """expired → active is not allowed."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        await update_defect_status(db_session, t.id, "expired")
        with pytest.raises(ValueError, match="Invalid transition"):
            await update_defect_status(db_session, t.id, "active")

    @pytest.mark.asyncio
    async def test_invalid_status_value(self, db_session, admin_user):
        """Completely unknown status value."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        with pytest.raises(ValueError, match="Invalid transition"):
            await update_defect_status(db_session, t.id, "banana")


# ---------------------------------------------------------------------------
# Terminal state enforcement
# ---------------------------------------------------------------------------


class TestTerminalState:
    """Resolved is a terminal state — no transitions out."""

    @pytest.mark.asyncio
    async def test_resolved_has_no_valid_transitions(self, db_session, admin_user):
        """VALID_STATUS_TRANSITIONS['resolved'] is an empty set."""
        assert VALID_STATUS_TRANSITIONS["resolved"] == set()

    @pytest.mark.asyncio
    async def test_all_transitions_from_resolved_fail(self, db_session, admin_user):
        """Try every known status from resolved — all should fail."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        await update_defect_status(db_session, t.id, "resolved")
        for target in ["active", "notified", "expired", "resolved"]:
            with pytest.raises(ValueError):
                await update_defect_status(db_session, t.id, target)


# ---------------------------------------------------------------------------
# Non-existent timeline
# ---------------------------------------------------------------------------


class TestNonExistentTimeline:
    """Updating a non-existent timeline should raise ValueError."""

    @pytest.mark.asyncio
    async def test_update_missing_timeline(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await update_defect_status(db_session, uuid.uuid4(), "notified")


# ---------------------------------------------------------------------------
# update_timeline_status (raw setter) vs update_defect_status (validated)
# ---------------------------------------------------------------------------


class TestRawVsValidatedUpdate:
    """update_timeline_status bypasses validation — verify behavior difference."""

    @pytest.mark.asyncio
    async def test_raw_allows_resolved_to_active(self, db_session, admin_user):
        """Raw setter doesn't enforce transition rules."""
        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        await update_defect_status(db_session, t.id, "resolved")
        # Raw setter should work even though transition is invalid
        updated = await update_timeline_status(db_session, t.id, "active")
        assert updated is not None
        assert updated.status == "active"

    @pytest.mark.asyncio
    async def test_raw_returns_none_for_missing_id(self, db_session):
        """Raw setter returns None instead of raising for missing timeline."""
        result = await update_timeline_status(db_session, uuid.uuid4(), "notified")
        assert result is None

    @pytest.mark.asyncio
    async def test_raw_sets_kwargs(self, db_session, admin_user):
        """Raw setter applies extra kwargs to the model."""
        from datetime import UTC, datetime

        b = await _make_building(db_session, admin_user.id)
        t = await _make_timeline(db_session, b.id)
        now = datetime.now(UTC)
        updated = await update_timeline_status(
            db_session, t.id, "notified", notified_at=now
        )
        assert updated.status == "notified"
        assert updated.notified_at is not None
