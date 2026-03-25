"""Tests for ControlTower v2 — Action Aggregation Service."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.authority_request import AuthorityRequest
from app.models.building import Building
from app.models.contract import Contract
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.document_inbox import DocumentInboxItem
from app.models.intake_request import IntakeRequest
from app.models.lease import Lease
from app.models.obligation import Obligation
from app.models.organization import Organization
from app.models.permit_procedure import PermitProcedure
from app.models.permit_step import PermitStep
from app.models.user import User
from app.services.action_aggregation_service import get_action_feed, get_feed_summary

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TODAY = date.today()


async def _make_building(db: AsyncSession, *, city: str = "Lausanne", address: str = "Rue Test 1") -> Building:
    user = await _make_user(db)
    b = Building(
        id=uuid.uuid4(),
        address=address,
        city=city,
        canton="VD",
        postal_code="1000",
        building_type="residential",
        created_by=user.id,
    )
    db.add(b)
    await db.flush()
    return b


async def _make_org(db: AsyncSession) -> Organization:
    org = Organization(id=uuid.uuid4(), name="TestOrg", type="property_management")
    db.add(org)
    await db.flush()
    return org


async def _make_user(db: AsyncSession) -> User:
    u = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash="fakehash",
        first_name="Test",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
    )
    db.add(u)
    await db.flush()
    return u


# ---------------------------------------------------------------------------
# Tests — Obligation collection
# ---------------------------------------------------------------------------


async def test_overdue_obligation_priority_2(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    db_session.add(
        Obligation(
            id=uuid.uuid4(),
            building_id=b.id,
            title="Overdue SUVA",
            obligation_type="authority_submission",
            due_date=_TODAY - timedelta(days=5),
            status="overdue",
            priority="high",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.total == 1
    assert feed.items[0].priority == 2
    assert feed.items[0].source_type == "obligation"
    assert feed.items[0].priority_label == "overdue_obligation"


async def test_due_soon_obligation_priority_4(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    db_session.add(
        Obligation(
            id=uuid.uuid4(),
            building_id=b.id,
            title="Due soon followup",
            obligation_type="diagnostic_followup",
            due_date=_TODAY + timedelta(days=10),
            status="due_soon",
            priority="medium",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.total == 1
    assert feed.items[0].priority == 4
    assert feed.items[0].priority_label == "upcoming_deadline"


async def test_completed_obligation_excluded(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    db_session.add(
        Obligation(
            id=uuid.uuid4(),
            building_id=b.id,
            title="Done",
            obligation_type="maintenance",
            due_date=_TODAY - timedelta(days=30),
            status="completed",
            priority="low",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.total == 0


# ---------------------------------------------------------------------------
# Tests — Permit blockers
# ---------------------------------------------------------------------------


async def test_complement_requested_procedure_priority_0(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    db_session.add(
        PermitProcedure(
            id=uuid.uuid4(),
            building_id=b.id,
            procedure_type="construction_permit",
            title="Blocked permit",
            status="complement_requested",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.total == 1
    assert feed.items[0].priority == 0
    assert feed.items[0].priority_label == "procedural_blocker"


async def test_blocked_step_priority_0(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    proc_id = uuid.uuid4()
    db_session.add(
        PermitProcedure(
            id=proc_id,
            building_id=b.id,
            procedure_type="suva_notification",
            title="SUVA proc",
            status="under_review",
        )
    )
    await db_session.flush()
    db_session.add(
        PermitStep(
            id=uuid.uuid4(),
            procedure_id=proc_id,
            step_type="review",
            title="Blocked step",
            status="blocked",
            step_order=1,
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.total == 1
    assert feed.items[0].priority == 0


# ---------------------------------------------------------------------------
# Tests — Authority requests
# ---------------------------------------------------------------------------


async def test_overdue_authority_request_priority_1(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    proc_id = uuid.uuid4()
    db_session.add(
        PermitProcedure(
            id=proc_id,
            building_id=b.id,
            procedure_type="construction_permit",
            title="Permit",
            status="under_review",
        )
    )
    await db_session.flush()
    db_session.add(
        AuthorityRequest(
            id=uuid.uuid4(),
            procedure_id=proc_id,
            request_type="complement_request",
            subject="Missing docs",
            body="Please provide plan",
            response_due_date=_TODAY - timedelta(days=3),
            status="overdue",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert any(it.priority == 1 and it.source_type == "authority_request" for it in feed.items)


async def test_future_authority_request_excluded(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    proc_id = uuid.uuid4()
    db_session.add(
        PermitProcedure(
            id=proc_id,
            building_id=b.id,
            procedure_type="construction_permit",
            title="Permit",
            status="under_review",
        )
    )
    await db_session.flush()
    db_session.add(
        AuthorityRequest(
            id=uuid.uuid4(),
            procedure_id=proc_id,
            request_type="information_request",
            subject="Info",
            body="Info needed",
            response_due_date=_TODAY + timedelta(days=30),
            status="open",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert not any(it.source_type == "authority_request" for it in feed.items)


# ---------------------------------------------------------------------------
# Tests — Inbox
# ---------------------------------------------------------------------------


async def test_pending_inbox_priority_3(db_session: AsyncSession):
    u = await _make_user(db_session)
    db_session.add(
        DocumentInboxItem(
            id=uuid.uuid4(),
            filename="rapport.pdf",
            file_url="/uploads/rapport.pdf",
            status="pending",
            source="upload",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.total == 1
    assert feed.items[0].priority == 3
    assert feed.items[0].source_type == "inbox"


# ---------------------------------------------------------------------------
# Tests — Publications
# ---------------------------------------------------------------------------


async def test_unmatched_publication_priority_3(db_session: AsyncSession):
    u = await _make_user(db_session)
    db_session.add(
        DiagnosticReportPublication(
            id=uuid.uuid4(),
            source_mission_id="MISSION-001",
            match_state="unmatched",
            match_key_type="none",
            mission_type="asbestos_full",
            payload_hash="abc123def456",
            published_at=_TODAY,
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.total == 1
    assert feed.items[0].source_type == "publication"


# ---------------------------------------------------------------------------
# Tests — Intake
# ---------------------------------------------------------------------------


async def test_new_intake_priority_3(db_session: AsyncSession):
    u = await _make_user(db_session)
    db_session.add(
        IntakeRequest(
            id=uuid.uuid4(),
            requester_name="Jean Dupont",
            requester_email="jean@test.ch",
            building_address="Rue Test 5",
            request_type="asbestos_diagnostic",
            status="new",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.total == 1
    assert feed.items[0].source_type == "intake"


# ---------------------------------------------------------------------------
# Tests — Lease / Contract renewals
# ---------------------------------------------------------------------------


async def test_lease_ending_soon_priority_4(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    db_session.add(
        Lease(
            id=uuid.uuid4(),
            building_id=b.id,
            lease_type="residential",
            reference_code=f"L-{uuid.uuid4().hex[:6]}",
            tenant_type="contact",
            tenant_id=uuid.uuid4(),
            date_start=_TODAY - timedelta(days=365),
            date_end=_TODAY + timedelta(days=30),
            status="active",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.total == 1
    assert feed.items[0].source_type == "lease"
    assert feed.items[0].priority == 4


async def test_contract_ending_soon_priority_4(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    db_session.add(
        Contract(
            id=uuid.uuid4(),
            building_id=b.id,
            contract_type="maintenance",
            reference_code=f"C-{uuid.uuid4().hex[:6]}",
            title="Elevator maintenance",
            counterparty_type="organization",
            counterparty_id=uuid.uuid4(),
            date_start=_TODAY - timedelta(days=365),
            date_end=_TODAY + timedelta(days=45),
            status="active",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.total == 1
    assert feed.items[0].source_type == "contract"
    assert feed.items[0].priority == 4


async def test_far_future_lease_excluded(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    db_session.add(
        Lease(
            id=uuid.uuid4(),
            building_id=b.id,
            lease_type="commercial",
            reference_code=f"L-{uuid.uuid4().hex[:6]}",
            tenant_type="contact",
            tenant_id=uuid.uuid4(),
            date_start=_TODAY - timedelta(days=100),
            date_end=_TODAY + timedelta(days=200),
            status="active",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.total == 0


# ---------------------------------------------------------------------------
# Tests — Priority ordering
# ---------------------------------------------------------------------------


async def test_priority_ordering(db_session: AsyncSession):
    """Items are sorted P0 first, then P1, P2, ... P4."""
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    # P2 — overdue obligation
    db_session.add(
        Obligation(
            id=uuid.uuid4(),
            building_id=b.id,
            title="Overdue",
            obligation_type="authority_submission",
            due_date=_TODAY - timedelta(days=5),
            status="overdue",
            priority="high",
        )
    )
    # P0 — blocked procedure
    db_session.add(
        PermitProcedure(
            id=uuid.uuid4(),
            building_id=b.id,
            procedure_type="construction_permit",
            title="Blocked",
            status="complement_requested",
        )
    )
    # P4 — due soon
    db_session.add(
        Obligation(
            id=uuid.uuid4(),
            building_id=b.id,
            title="Due soon",
            obligation_type="diagnostic_followup",
            due_date=_TODAY + timedelta(days=10),
            status="due_soon",
            priority="medium",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.total == 3
    priorities = [it.priority for it in feed.items]
    assert priorities == sorted(priorities)
    assert priorities[0] == 0
    assert priorities[-1] == 4


# ---------------------------------------------------------------------------
# Tests — Filtering
# ---------------------------------------------------------------------------


async def test_filter_by_building_id(db_session: AsyncSession):
    b1 = await _make_building(db_session, address="Rue A")
    b2 = await _make_building(db_session, address="Rue B")
    u = await _make_user(db_session)
    db_session.add(
        Obligation(
            id=uuid.uuid4(),
            building_id=b1.id,
            title="B1",
            obligation_type="maintenance",
            due_date=_TODAY - timedelta(days=1),
            status="overdue",
            priority="high",
        )
    )
    db_session.add(
        Obligation(
            id=uuid.uuid4(),
            building_id=b2.id,
            title="B2",
            obligation_type="maintenance",
            due_date=_TODAY - timedelta(days=1),
            status="overdue",
            priority="high",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id, building_id=b1.id)
    assert feed.total == 1
    assert feed.items[0].building_id == b1.id


async def test_filter_by_source_type(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    db_session.add(
        Obligation(
            id=uuid.uuid4(),
            building_id=b.id,
            title="Ob",
            obligation_type="maintenance",
            due_date=_TODAY - timedelta(days=1),
            status="overdue",
            priority="high",
        )
    )
    db_session.add(
        IntakeRequest(
            id=uuid.uuid4(),
            requester_name="X",
            requester_email="x@test.ch",
            building_address="Y",
            request_type="other",
            status="new",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id, source_type="obligation")
    assert feed.total == 1
    assert all(it.source_type == "obligation" for it in feed.items)


async def test_filter_by_priority(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    db_session.add(
        Obligation(
            id=uuid.uuid4(),
            building_id=b.id,
            title="Overdue",
            obligation_type="maintenance",
            due_date=_TODAY - timedelta(days=1),
            status="overdue",
            priority="high",
        )
    )
    db_session.add(
        Obligation(
            id=uuid.uuid4(),
            building_id=b.id,
            title="Soon",
            obligation_type="maintenance",
            due_date=_TODAY + timedelta(days=5),
            status="due_soon",
            priority="low",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id, priority_min=4, priority_max=4)
    assert all(it.priority == 4 for it in feed.items)


async def test_pagination(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    for i in range(5):
        db_session.add(
            Obligation(
                id=uuid.uuid4(),
                building_id=b.id,
                title=f"Ob-{i}",
                obligation_type="maintenance",
                due_date=_TODAY - timedelta(days=i + 1),
                status="overdue",
                priority="high",
            )
        )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id, limit=2, offset=0)
    assert feed.total == 5
    assert len(feed.items) == 2
    feed2 = await get_action_feed(db_session, u.id, limit=2, offset=2)
    assert len(feed2.items) == 2


# ---------------------------------------------------------------------------
# Tests — Summary
# ---------------------------------------------------------------------------


async def test_summary_counts(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    db_session.add(
        Obligation(
            id=uuid.uuid4(),
            building_id=b.id,
            title="Overdue",
            obligation_type="maintenance",
            due_date=_TODAY - timedelta(days=1),
            status="overdue",
            priority="high",
        )
    )
    db_session.add(
        PermitProcedure(
            id=uuid.uuid4(),
            building_id=b.id,
            procedure_type="construction_permit",
            title="Blocked",
            status="complement_requested",
        )
    )
    await db_session.flush()
    summary = await get_feed_summary(db_session, u.id)
    assert summary.total == 2
    assert summary.by_priority.get(0, 0) == 1
    assert summary.by_priority.get(2, 0) == 1
    assert summary.by_source_type.get("obligation", 0) == 1
    assert summary.by_source_type.get("procedure", 0) == 1


# ---------------------------------------------------------------------------
# Tests — Empty state
# ---------------------------------------------------------------------------


async def test_empty_feed(db_session: AsyncSession):
    u = await _make_user(db_session)
    feed = await get_action_feed(db_session, u.id)
    assert feed.total == 0
    assert feed.items == []


async def test_empty_summary(db_session: AsyncSession):
    u = await _make_user(db_session)
    summary = await get_feed_summary(db_session, u.id)
    assert summary.total == 0
    assert summary.by_priority == {}
    assert summary.by_source_type == {}


# ---------------------------------------------------------------------------
# Tests — Address enrichment
# ---------------------------------------------------------------------------


async def test_building_address_enriched(db_session: AsyncSession):
    b = await _make_building(db_session, address="Avenue de Cour 15")
    u = await _make_user(db_session)
    db_session.add(
        Obligation(
            id=uuid.uuid4(),
            building_id=b.id,
            title="Test",
            obligation_type="maintenance",
            due_date=_TODAY - timedelta(days=1),
            status="overdue",
            priority="high",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.items[0].building_address == "Avenue de Cour 15"


# ---------------------------------------------------------------------------
# Tests — Composite ID format
# ---------------------------------------------------------------------------


async def test_composite_id_format(db_session: AsyncSession):
    b = await _make_building(db_session)
    u = await _make_user(db_session)
    ob_id = uuid.uuid4()
    db_session.add(
        Obligation(
            id=ob_id,
            building_id=b.id,
            title="Test",
            obligation_type="maintenance",
            due_date=_TODAY - timedelta(days=1),
            status="overdue",
            priority="high",
        )
    )
    await db_session.flush()
    feed = await get_action_feed(db_session, u.id)
    assert feed.items[0].id == f"obligation:{ob_id}"
