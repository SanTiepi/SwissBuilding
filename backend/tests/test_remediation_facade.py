"""Tests for the Remediation Domain Facade."""

from __future__ import annotations

import uuid

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.intervention import Intervention
from app.models.post_works_state import PostWorksState
from app.services.remediation_facade import get_remediation_summary

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


# ── Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nonexistent_building(db_session, admin_user):
    """Returns None for a building that does not exist."""
    result = await get_remediation_summary(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_empty_building(db_session, admin_user):
    """Returns zero counts for a building with no actions or interventions."""
    b = await _create_building(db_session, admin_user)
    result = await get_remediation_summary(db_session, b.id)

    assert result is not None
    assert result["actions"]["total"] == 0
    assert result["actions"]["open"] == 0
    assert result["interventions"]["total"] == 0
    assert result["post_works_states_count"] == 0
    assert result["has_completed_remediation"] is False


@pytest.mark.asyncio
async def test_building_with_actions_and_interventions(db_session, admin_user):
    """Returns correct counts when actions and interventions exist."""
    b = await _create_building(db_session, admin_user)

    # Create actions
    for status, priority in [("open", "high"), ("open", "critical"), ("completed", "medium")]:
        db_session.add(
            ActionItem(
                id=uuid.uuid4(),
                building_id=b.id,
                source_type="diagnostic",
                action_type="remediation",
                title=f"Action {status}",
                priority=priority,
                status=status,
            )
        )

    # Create interventions
    db_session.add(
        Intervention(
            id=uuid.uuid4(),
            building_id=b.id,
            intervention_type="asbestos_removal",
            title="Remove asbestos",
            status="completed",
        )
    )
    db_session.add(
        Intervention(
            id=uuid.uuid4(),
            building_id=b.id,
            intervention_type="encapsulation",
            title="Encapsulate PCB",
            status="planned",
        )
    )
    await db_session.flush()

    result = await get_remediation_summary(db_session, b.id)

    assert result["actions"]["total"] == 3
    assert result["actions"]["open"] == 2
    assert result["actions"]["done"] == 1
    assert result["actions"]["by_priority"]["high"] == 1
    assert result["actions"]["by_priority"]["critical"] == 1
    assert result["interventions"]["total"] == 2
    assert result["interventions"]["by_status"]["completed"] == 1
    assert result["interventions"]["by_status"]["planned"] == 1
    # No post-works states yet, so has_completed_remediation is False
    assert result["has_completed_remediation"] is False


@pytest.mark.asyncio
async def test_has_completed_remediation_flag(db_session, admin_user):
    """has_completed_remediation is True when completed intervention + post-works state exist."""
    b = await _create_building(db_session, admin_user)

    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=b.id,
        intervention_type="asbestos_removal",
        title="Remove asbestos",
        status="completed",
    )
    db_session.add(intervention)

    pws = PostWorksState(
        id=uuid.uuid4(),
        building_id=b.id,
        intervention_id=intervention.id,
        state_type="removed",
        pollutant_type="asbestos",
        title="Removed asbestos",
    )
    db_session.add(pws)
    await db_session.flush()

    result = await get_remediation_summary(db_session, b.id)

    assert result["has_completed_remediation"] is True
    assert result["post_works_states_count"] == 1
