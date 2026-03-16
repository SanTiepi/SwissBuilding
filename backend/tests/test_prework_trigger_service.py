"""Tests for the prework trigger service — persistent lifecycle + escalation."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.prework_trigger import PreworkTrigger
from app.services.prework_trigger_service import (
    acknowledge_trigger,
    escalate_triggers,
    get_portfolio_trigger_summary,
    list_triggers,
    resolve_trigger,
    sync_triggers,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BUILDING_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


@pytest_asyncio.fixture
async def building(db_session: AsyncSession):
    b = Building(
        id=BUILDING_ID,
        address="Test Prework",
        city="Lausanne",
        canton="VD",
        postal_code="1000",
    )
    db_session.add(b)
    await db_session.flush()
    return b


def _make_checks(
    *,
    completed_diagnostic: str = "pass",
    all_pollutants: str = "pass",
    all_pollutants_detail: str = "All 5 pollutant types covered",
    positive_samples: str = "not_applicable",
    suva: str = "not_applicable",
    cfst: str = "not_applicable",
    waste: str = "not_applicable",
    critical_actions: str = "pass",
    report: str = "pass",
    cantonal: str = "not_applicable",
) -> list[dict]:
    """Build a checks_json list for testing."""
    return [
        {
            "id": "completed_diagnostic",
            "label": "Completed diagnostic",
            "status": completed_diagnostic,
            "required": True,
        },
        {
            "id": "all_pollutants_evaluated",
            "label": "All pollutants",
            "status": all_pollutants,
            "detail": all_pollutants_detail,
            "required": True,
        },
        {
            "id": "positive_samples_classified",
            "label": "Positive samples",
            "status": positive_samples,
            "required": True,
        },
        {"id": "suva_notification", "label": "SUVA", "status": suva, "required": True},
        {"id": "cfst_work_category", "label": "CFST", "status": cfst, "required": True},
        {"id": "waste_classified", "label": "Waste", "status": waste, "required": True},
        {"id": "no_critical_actions", "label": "Critical actions", "status": critical_actions, "required": True},
        {"id": "diagnostic_report", "label": "Report", "status": report, "required": False},
        {"id": "cantonal_form", "label": "Canton", "status": cantonal, "required": False},
    ]


# ---------------------------------------------------------------------------
# sync_triggers
# ---------------------------------------------------------------------------


class TestSyncTriggers:
    """Test idempotent sync from readiness checks."""

    async def test_no_triggers_when_all_pass(self, db_session: AsyncSession, building):
        checks = _make_checks()
        result = await sync_triggers(db_session, BUILDING_ID, None, checks)
        assert result["created"] == []
        assert result["resolved"] == []

    async def test_creates_trigger_for_missing_pollutant(self, db_session: AsyncSession, building):
        checks = _make_checks(
            all_pollutants="fail",
            all_pollutants_detail="Missing: pcb, lead",
        )
        result = await sync_triggers(db_session, BUILDING_ID, None, checks)
        created_types = {t.trigger_type for t in result["created"]}
        assert "amiante_check" in created_types  # from all_pollutants_evaluated direct map
        assert "pcb_check" in created_types
        assert "lead_check" in created_types

    async def test_idempotent_no_duplicates(self, db_session: AsyncSession, building):
        checks = _make_checks(all_pollutants="fail", all_pollutants_detail="Missing: pcb")
        await sync_triggers(db_session, BUILDING_ID, None, checks)
        await db_session.commit()

        # Sync again — should not create duplicates
        result2 = await sync_triggers(db_session, BUILDING_ID, None, checks)
        assert result2["created"] == []

    async def test_auto_resolves_when_check_passes(self, db_session: AsyncSession, building):
        # First: create trigger
        checks_fail = _make_checks(all_pollutants="fail", all_pollutants_detail="Missing: pcb")
        await sync_triggers(db_session, BUILDING_ID, None, checks_fail)
        await db_session.commit()

        # Now: all pass
        checks_pass = _make_checks()
        result = await sync_triggers(db_session, BUILDING_ID, None, checks_pass)
        assert len(result["resolved"]) > 0
        for t in result["resolved"]:
            assert t.status == "resolved"
            assert t.resolved_reason == "Source check now passes"

    async def test_updates_reason_on_change(self, db_session: AsyncSession, building):
        checks1 = _make_checks(all_pollutants="fail", all_pollutants_detail="Missing: pcb")
        await sync_triggers(db_session, BUILDING_ID, None, checks1)
        await db_session.commit()

        checks2 = _make_checks(all_pollutants="fail", all_pollutants_detail="Missing: pcb, lead")
        result = await sync_triggers(db_session, BUILDING_ID, None, checks2)
        # pcb_check was updated, lead_check was created
        assert len(result["created"]) >= 1  # lead_check

    async def test_creates_amiante_from_suva_fail(self, db_session: AsyncSession, building):
        checks = _make_checks(suva="fail")
        result = await sync_triggers(db_session, BUILDING_ID, None, checks)
        created_types = {t.trigger_type for t in result["created"]}
        assert "amiante_check" in created_types

    async def test_legal_basis_populated(self, db_session: AsyncSession, building):
        checks = _make_checks(all_pollutants="fail", all_pollutants_detail="Missing: radon")
        result = await sync_triggers(db_session, BUILDING_ID, None, checks)
        radon = [t for t in result["created"] if t.trigger_type == "radon_check"]
        assert radon
        assert radon[0].legal_basis == "ORaP Art. 110"


# ---------------------------------------------------------------------------
# Escalation
# ---------------------------------------------------------------------------


class TestEscalation:
    """Test deterministic escalation based on age x urgency."""

    async def test_fresh_trigger_no_escalation(self, db_session: AsyncSession, building):
        trigger = PreworkTrigger(
            building_id=BUILDING_ID,
            trigger_type="amiante_check",
            reason="test",
            source_check="all_pollutants_evaluated",
            urgency="high",
            status="pending",
            created_at=datetime.now(UTC),
        )
        db_session.add(trigger)
        await db_session.flush()

        result = await escalate_triggers(db_session, BUILDING_ID)
        assert len(result) == 0  # no change

    async def test_high_urgency_7_day_escalation(self, db_session: AsyncSession, building):
        trigger = PreworkTrigger(
            building_id=BUILDING_ID,
            trigger_type="amiante_check",
            reason="test",
            source_check="all_pollutants_evaluated",
            urgency="high",
            status="pending",
            created_at=datetime.now(UTC) - timedelta(days=8),
        )
        db_session.add(trigger)
        await db_session.flush()

        result = await escalate_triggers(db_session, BUILDING_ID)
        assert len(result) == 1
        assert result[0].escalation_level == 0.5

    async def test_high_urgency_30_day_critical(self, db_session: AsyncSession, building):
        trigger = PreworkTrigger(
            building_id=BUILDING_ID,
            trigger_type="pcb_check",
            reason="test",
            source_check="all_pollutants_evaluated",
            urgency="high",
            status="pending",
            created_at=datetime.now(UTC) - timedelta(days=31),
        )
        db_session.add(trigger)
        await db_session.flush()

        result = await escalate_triggers(db_session, BUILDING_ID)
        assert len(result) == 1
        assert result[0].escalation_level == 2.0

    async def test_resolved_trigger_not_escalated(self, db_session: AsyncSession, building):
        trigger = PreworkTrigger(
            building_id=BUILDING_ID,
            trigger_type="lead_check",
            reason="test",
            source_check="all_pollutants_evaluated",
            urgency="high",
            status="resolved",
            created_at=datetime.now(UTC) - timedelta(days=60),
        )
        db_session.add(trigger)
        await db_session.flush()

        result = await escalate_triggers(db_session, BUILDING_ID)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Acknowledge / Resolve
# ---------------------------------------------------------------------------


class TestLifecycle:
    """Test trigger lifecycle transitions."""

    async def test_acknowledge_pending(self, db_session: AsyncSession, building):
        trigger = PreworkTrigger(
            building_id=BUILDING_ID,
            trigger_type="amiante_check",
            reason="test",
            source_check="test",
            urgency="high",
            status="pending",
        )
        db_session.add(trigger)
        await db_session.flush()

        result = await acknowledge_trigger(db_session, trigger.id, USER_ID)
        assert result is not None
        assert result.status == "acknowledged"
        assert result.acknowledged_by == USER_ID

    async def test_acknowledge_non_pending_returns_none(self, db_session: AsyncSession, building):
        trigger = PreworkTrigger(
            building_id=BUILDING_ID,
            trigger_type="pcb_check",
            reason="test",
            source_check="test",
            urgency="high",
            status="resolved",
        )
        db_session.add(trigger)
        await db_session.flush()

        result = await acknowledge_trigger(db_session, trigger.id, USER_ID)
        assert result is None

    async def test_resolve_trigger(self, db_session: AsyncSession, building):
        trigger = PreworkTrigger(
            building_id=BUILDING_ID,
            trigger_type="amiante_check",
            reason="test",
            source_check="test",
            urgency="high",
            status="acknowledged",
        )
        db_session.add(trigger)
        await db_session.flush()

        result = await resolve_trigger(db_session, trigger.id, status="resolved", reason="Diagnostic completed")
        assert result is not None
        assert result.status == "resolved"
        assert result.resolved_reason == "Diagnostic completed"

    async def test_dismiss_trigger(self, db_session: AsyncSession, building):
        trigger = PreworkTrigger(
            building_id=BUILDING_ID,
            trigger_type="hap_check",
            reason="test",
            source_check="test",
            urgency="medium",
            status="pending",
        )
        db_session.add(trigger)
        await db_session.flush()

        result = await resolve_trigger(db_session, trigger.id, status="dismissed", reason="Not applicable")
        assert result is not None
        assert result.status == "dismissed"

    async def test_resolve_already_resolved_returns_none(self, db_session: AsyncSession, building):
        trigger = PreworkTrigger(
            building_id=BUILDING_ID,
            trigger_type="radon_check",
            reason="test",
            source_check="test",
            urgency="low",
            status="resolved",
        )
        db_session.add(trigger)
        await db_session.flush()

        result = await resolve_trigger(db_session, trigger.id)
        assert result is None


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


class TestListTriggers:
    """Test listing triggers with filters."""

    async def test_list_active_only(self, db_session: AsyncSession, building):
        for i, status in enumerate(["pending", "acknowledged", "resolved", "dismissed"]):
            db_session.add(
                PreworkTrigger(
                    building_id=BUILDING_ID,
                    trigger_type=f"type_{i}",
                    reason="test",
                    source_check="test",
                    urgency="high",
                    status=status,
                )
            )
        await db_session.flush()

        active = await list_triggers(db_session, BUILDING_ID)
        assert len(active) == 2  # pending + acknowledged

    async def test_list_with_resolved(self, db_session: AsyncSession, building):
        for i, status in enumerate(["pending", "resolved"]):
            db_session.add(
                PreworkTrigger(
                    building_id=BUILDING_ID,
                    trigger_type=f"type_{i}",
                    reason="test",
                    source_check="test",
                    urgency="high",
                    status=status,
                )
            )
        await db_session.flush()

        all_triggers = await list_triggers(db_session, BUILDING_ID, include_resolved=True)
        assert len(all_triggers) == 2


# ---------------------------------------------------------------------------
# Portfolio summary
# ---------------------------------------------------------------------------


class TestPortfolioSummary:
    """Test cross-building aggregation."""

    async def test_portfolio_summary(self, db_session: AsyncSession, building):
        b2_id = uuid.uuid4()
        db_session.add(Building(id=b2_id, address="B2", city="Genève", canton="GE", postal_code="1200"))
        await db_session.flush()

        db_session.add(
            PreworkTrigger(
                building_id=BUILDING_ID,
                trigger_type="amiante_check",
                reason="t",
                source_check="s",
                urgency="high",
                status="pending",
                escalation_level=2.5,
            )
        )
        db_session.add(
            PreworkTrigger(
                building_id=BUILDING_ID,
                trigger_type="pcb_check",
                reason="t",
                source_check="s",
                urgency="medium",
                status="pending",
            )
        )
        db_session.add(
            PreworkTrigger(
                building_id=b2_id,
                trigger_type="radon_check",
                reason="t",
                source_check="s",
                urgency="high",
                status="acknowledged",
            )
        )
        db_session.add(
            PreworkTrigger(
                building_id=b2_id,
                trigger_type="lead_check",
                reason="t",
                source_check="s",
                urgency="low",
                status="resolved",
            )
        )
        await db_session.flush()

        summary = await get_portfolio_trigger_summary(db_session, [BUILDING_ID, b2_id])
        assert summary["total_active"] == 3  # excludes resolved
        assert summary["buildings_affected"] == 2
        assert summary["critical_escalations"] == 1  # the 2.5 one
        assert summary["by_type"]["amiante_check"] == 1
        assert summary["by_urgency"]["high"] == 2

    async def test_empty_portfolio(self, db_session: AsyncSession):
        summary = await get_portfolio_trigger_summary(db_session, [])
        assert summary["total_active"] == 0
