"""BatiConnect — Expansion signals, fit evaluation, and customer success tests."""

import uuid
from datetime import UTC, date, datetime

import pytest

from app.api.expansion import router as expansion_router
from app.main import app
from app.models.building import Building
from app.models.customer_success import CustomerSuccessMilestone
from app.models.expansion_signal import (
    AccountExpansionTrigger,
    DistributionLoopSignal,
    ExpansionOpportunity,
)
from app.models.obligation import Obligation
from app.models.organization import Organization
from app.models.permit_procedure import PermitProcedure
from app.models.user import User
from app.models.workspace_membership import WorkspaceMembership
from app.services.customer_success_service import check_and_advance, get_milestones, get_next_step
from app.services.fit_evaluation_service import evaluate_fit

# Register expansion router for HTTP tests (not yet in router.py hub file)
app.include_router(expansion_router, prefix="/api/v1")


# ---- Helpers ----


async def _create_org(db, name="Test Org"):
    org = Organization(
        id=uuid.uuid4(),
        name=name,
        type="property_management",
    )
    db.add(org)
    await db.flush()
    await db.refresh(org)
    return org


async def _create_user_in_org(db, org, email="user@test.ch", role="admin"):
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role=role,
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _create_building_by_user(db, user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=user.id,
        status="active",
    )
    db.add(building)
    await db.flush()
    await db.refresh(building)
    return building


# =====================================================================
# Model tests — AccountExpansionTrigger
# =====================================================================


@pytest.mark.asyncio
async def test_create_expansion_trigger(db_session):
    org = await _create_org(db_session)
    trigger = AccountExpansionTrigger(
        id=uuid.uuid4(),
        organization_id=org.id,
        trigger_type="second_actor_active",
        evidence_summary="Second user logged in",
        detected_at=datetime.now(UTC),
    )
    db_session.add(trigger)
    await db_session.flush()
    assert trigger.id is not None
    assert trigger.trigger_type == "second_actor_active"


@pytest.mark.asyncio
async def test_create_expansion_trigger_with_source(db_session):
    org = await _create_org(db_session)
    source_id = uuid.uuid4()
    trigger = AccountExpansionTrigger(
        id=uuid.uuid4(),
        organization_id=org.id,
        trigger_type="pack_consulted",
        source_entity_type="evidence_pack",
        source_entity_id=source_id,
        evidence_summary="Pack consulted 3 times",
        detected_at=datetime.now(UTC),
    )
    db_session.add(trigger)
    await db_session.flush()
    assert trigger.source_entity_type == "evidence_pack"
    assert trigger.source_entity_id == source_id


# =====================================================================
# Model tests — DistributionLoopSignal
# =====================================================================


@pytest.mark.asyncio
async def test_create_distribution_signal(db_session, sample_building):
    org = await _create_org(db_session)
    signal = DistributionLoopSignal(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        organization_id=org.id,
        signal_type="pack_shared",
        audience_type="authority",
    )
    db_session.add(signal)
    await db_session.flush()
    assert signal.signal_type == "pack_shared"
    assert signal.audience_type == "authority"


@pytest.mark.asyncio
async def test_distribution_signal_nullable_org(db_session, sample_building):
    signal = DistributionLoopSignal(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        organization_id=None,
        signal_type="embed_viewed",
    )
    db_session.add(signal)
    await db_session.flush()
    assert signal.organization_id is None


# =====================================================================
# Model tests — ExpansionOpportunity
# =====================================================================


@pytest.mark.asyncio
async def test_create_expansion_opportunity(db_session):
    org = await _create_org(db_session)
    opp = ExpansionOpportunity(
        id=uuid.uuid4(),
        organization_id=org.id,
        opportunity_type="add_building",
        status="detected",
        recommended_action="Add remaining portfolio buildings",
        evidence=[{"signal_type": "second_actor_active", "entity": "user", "date": "2026-03-25"}],
        priority="high",
        detected_at=datetime.now(UTC),
    )
    db_session.add(opp)
    await db_session.flush()
    assert opp.status == "detected"
    assert opp.priority == "high"
    assert len(opp.evidence) == 1


@pytest.mark.asyncio
async def test_expansion_opportunity_status_transitions(db_session):
    org = await _create_org(db_session)
    opp = ExpansionOpportunity(
        id=uuid.uuid4(),
        organization_id=org.id,
        opportunity_type="add_actor",
        status="detected",
        recommended_action="Invite architect to workspace",
        priority="medium",
        detected_at=datetime.now(UTC),
    )
    db_session.add(opp)
    await db_session.flush()

    # Transition to acted
    opp.status = "acted"
    opp.acted_at = datetime.now(UTC)
    await db_session.flush()
    assert opp.status == "acted"
    assert opp.acted_at is not None


# =====================================================================
# Model tests — CustomerSuccessMilestone
# =====================================================================


@pytest.mark.asyncio
async def test_create_milestone_pending(db_session):
    org = await _create_org(db_session)
    milestone = CustomerSuccessMilestone(
        id=uuid.uuid4(),
        organization_id=org.id,
        milestone_type="first_workflow_win",
        status="pending",
    )
    db_session.add(milestone)
    await db_session.flush()
    assert milestone.status == "pending"
    assert milestone.achieved_at is None


@pytest.mark.asyncio
async def test_create_milestone_achieved(db_session):
    org = await _create_org(db_session)
    now = datetime.now(UTC)
    milestone = CustomerSuccessMilestone(
        id=uuid.uuid4(),
        organization_id=org.id,
        milestone_type="first_workflow_win",
        status="achieved",
        achieved_at=now,
        evidence_entity_type="permit_procedure",
        evidence_entity_id=uuid.uuid4(),
        evidence_summary="Permit approved",
    )
    db_session.add(milestone)
    await db_session.flush()
    assert milestone.status == "achieved"
    assert milestone.evidence_summary == "Permit approved"


@pytest.mark.asyncio
async def test_create_milestone_blocked(db_session):
    org = await _create_org(db_session)
    milestone = CustomerSuccessMilestone(
        id=uuid.uuid4(),
        organization_id=org.id,
        milestone_type="first_exchange_publication",
        status="blocked",
        blocker_description="No exchange contract configured",
    )
    db_session.add(milestone)
    await db_session.flush()
    assert milestone.status == "blocked"
    assert milestone.blocker_description is not None


# =====================================================================
# Fit Evaluation Service
# =====================================================================


@pytest.mark.asyncio
async def test_fit_evaluation_no_buildings(db_session):
    org = await _create_org(db_session)
    await _create_user_in_org(db_session, org)
    result = await evaluate_fit(db_session, org.id)
    assert result.verdict in ("pilot_slice", "walk_away")
    assert any("No building anchor" in r for r in result.reasons)


@pytest.mark.asyncio
async def test_fit_evaluation_good_fit(db_session):
    org = await _create_org(db_session)
    user1 = await _create_user_in_org(db_session, org, email="u1@test.ch")
    user2 = await _create_user_in_org(db_session, org, email="u2@test.ch")
    b1 = await _create_building_by_user(db_session, user1)
    await _create_building_by_user(db_session, user2)

    # Add workspace membership for proof need
    ws = WorkspaceMembership(
        id=uuid.uuid4(),
        building_id=b1.id,
        organization_id=org.id,
        user_id=user1.id,
        role="manager",
        granted_by_user_id=user1.id,
        is_active=True,
    )
    db_session.add(ws)
    await db_session.flush()

    result = await evaluate_fit(db_session, org.id)
    assert result.verdict == "good_fit"
    assert len(result.evidence) == 4


@pytest.mark.asyncio
async def test_fit_evaluation_pilot_slice(db_session):
    org = await _create_org(db_session)
    user = await _create_user_in_org(db_session, org)
    await _create_building_by_user(db_session, user)
    # Single user, single building, no workspace — pilot_slice
    result = await evaluate_fit(db_session, org.id)
    assert result.verdict == "pilot_slice"


@pytest.mark.asyncio
async def test_fit_evaluation_evidence_grounded(db_session):
    org = await _create_org(db_session)
    user = await _create_user_in_org(db_session, org)
    await _create_building_by_user(db_session, user)
    result = await evaluate_fit(db_session, org.id)
    # All evidence entries have check/result/detail
    for ev in result.evidence:
        assert ev.check
        assert ev.detail
        assert isinstance(ev.result, bool)


# =====================================================================
# Customer Success Service
# =====================================================================


@pytest.mark.asyncio
async def test_get_milestones_empty(db_session):
    org = await _create_org(db_session)
    milestones = await get_milestones(db_session, org.id)
    assert milestones == []


@pytest.mark.asyncio
async def test_check_and_advance_creates_milestones(db_session):
    org = await _create_org(db_session)
    milestones = await check_and_advance(db_session, org.id)
    assert len(milestones) == 6  # All 6 milestone types


@pytest.mark.asyncio
async def test_check_and_advance_workflow_win(db_session):
    org = await _create_org(db_session)
    user = await _create_user_in_org(db_session, org)
    building = await _create_building_by_user(db_session, user)

    # Create approved permit
    permit = PermitProcedure(
        id=uuid.uuid4(),
        building_id=building.id,
        procedure_type="construction_permit",
        title="Test Permit",
        status="approved",
        assigned_org_id=org.id,
    )
    db_session.add(permit)
    await db_session.flush()

    milestones = await check_and_advance(db_session, org.id)
    ww = next(m for m in milestones if m.milestone_type == "first_workflow_win")
    assert ww.status == "achieved"
    assert ww.evidence_entity_type == "permit_procedure"


@pytest.mark.asyncio
async def test_check_and_advance_actor_spread(db_session):
    org = await _create_org(db_session)
    user1 = await _create_user_in_org(db_session, org, email="a@test.ch")
    user2 = await _create_user_in_org(db_session, org, email="b@test.ch")
    building = await _create_building_by_user(db_session, user1)

    # Two workspace memberships with distinct users
    for u in [user1, user2]:
        ws = WorkspaceMembership(
            id=uuid.uuid4(),
            building_id=building.id,
            organization_id=org.id,
            user_id=u.id,
            role="manager",
            granted_by_user_id=user1.id,
            is_active=True,
        )
        db_session.add(ws)
    await db_session.flush()

    milestones = await check_and_advance(db_session, org.id)
    spread = next(m for m in milestones if m.milestone_type == "first_actor_spread")
    assert spread.status == "achieved"


@pytest.mark.asyncio
async def test_check_and_advance_blocker_caught(db_session):
    org = await _create_org(db_session)
    user = await _create_user_in_org(db_session, org)
    building = await _create_building_by_user(db_session, user)

    obligation = Obligation(
        id=uuid.uuid4(),
        building_id=building.id,
        title="Annual inspection",
        obligation_type="regulatory_inspection",
        due_date=date(2026, 6, 1),
        status="completed",
        responsible_org_id=org.id,
        completed_at=datetime.now(UTC),
    )
    db_session.add(obligation)
    await db_session.flush()

    milestones = await check_and_advance(db_session, org.id)
    blocker = next(m for m in milestones if m.milestone_type == "first_blocker_caught")
    assert blocker.status == "achieved"
    assert blocker.evidence_entity_type == "obligation"


@pytest.mark.asyncio
async def test_get_next_step_returns_first_pending(db_session):
    org = await _create_org(db_session)
    # Create one achieved, rest will be created as pending
    m = CustomerSuccessMilestone(
        id=uuid.uuid4(),
        organization_id=org.id,
        milestone_type="first_workflow_win",
        status="achieved",
        achieved_at=datetime.now(UTC),
    )
    db_session.add(m)
    await db_session.flush()

    # Advance to create remaining
    await check_and_advance(db_session, org.id)
    step = await get_next_step(db_session, org.id)
    assert step is not None
    assert step["milestone_type"] == "first_proof_reuse"


@pytest.mark.asyncio
async def test_get_next_step_none_when_all_achieved(db_session):
    org = await _create_org(db_session)
    from app.services.customer_success_service import MILESTONE_ORDER

    for mt in MILESTONE_ORDER:
        m = CustomerSuccessMilestone(
            id=uuid.uuid4(),
            organization_id=org.id,
            milestone_type=mt,
            status="achieved",
            achieved_at=datetime.now(UTC),
        )
        db_session.add(m)
    await db_session.flush()

    step = await get_next_step(db_session, org.id)
    assert step is None


# =====================================================================
# API route tests
# =====================================================================


@pytest.mark.asyncio
async def test_api_expansion_triggers(client, auth_headers, db_session, admin_user):
    org = await _create_org(db_session)
    trigger = AccountExpansionTrigger(
        id=uuid.uuid4(),
        organization_id=org.id,
        trigger_type="second_building_active",
        evidence_summary="Second building activated",
        detected_at=datetime.now(UTC),
    )
    db_session.add(trigger)
    await db_session.commit()

    resp = await client.get(f"/api/v1/organizations/{org.id}/expansion-triggers", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["trigger_type"] == "second_building_active"


@pytest.mark.asyncio
async def test_api_expansion_opportunities(client, auth_headers, db_session, admin_user):
    org = await _create_org(db_session)
    opp = ExpansionOpportunity(
        id=uuid.uuid4(),
        organization_id=org.id,
        opportunity_type="extend_audience",
        status="detected",
        recommended_action="Share pack with insurer",
        priority="medium",
        detected_at=datetime.now(UTC),
    )
    db_session.add(opp)
    await db_session.commit()

    resp = await client.get(f"/api/v1/organizations/{org.id}/expansion-opportunities", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["opportunity_type"] == "extend_audience"


@pytest.mark.asyncio
async def test_api_act_on_opportunity(client, auth_headers, db_session, admin_user):
    org = await _create_org(db_session)
    opp = ExpansionOpportunity(
        id=uuid.uuid4(),
        organization_id=org.id,
        opportunity_type="add_actor",
        status="detected",
        recommended_action="Invite diagnostician",
        priority="high",
        detected_at=datetime.now(UTC),
    )
    db_session.add(opp)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/expansion-opportunities/{opp.id}/act",
        json={"notes": "Invited Jean"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "acted"
    assert data["notes"] == "Invited Jean"


@pytest.mark.asyncio
async def test_api_dismiss_opportunity(client, auth_headers, db_session, admin_user):
    org = await _create_org(db_session)
    opp = ExpansionOpportunity(
        id=uuid.uuid4(),
        organization_id=org.id,
        opportunity_type="deepen_proof",
        status="qualified",
        recommended_action="Add more evidence",
        priority="low",
        detected_at=datetime.now(UTC),
    )
    db_session.add(opp)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/expansion-opportunities/{opp.id}/dismiss",
        json={"notes": "Not relevant now"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"


@pytest.mark.asyncio
async def test_api_act_on_already_acted(client, auth_headers, db_session, admin_user):
    org = await _create_org(db_session)
    opp = ExpansionOpportunity(
        id=uuid.uuid4(),
        organization_id=org.id,
        opportunity_type="add_building",
        status="acted",
        recommended_action="Already acted",
        priority="medium",
        detected_at=datetime.now(UTC),
        acted_at=datetime.now(UTC),
    )
    db_session.add(opp)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/expansion-opportunities/{opp.id}/act",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_fit_evaluation(client, auth_headers, db_session, admin_user):
    org = await _create_org(db_session)
    resp = await client.get(f"/api/v1/organizations/{org.id}/fit-evaluation", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] in ("good_fit", "pilot_slice", "walk_away")
    assert len(data["evidence"]) == 4
    assert all("check" in e for e in data["evidence"])


@pytest.mark.asyncio
async def test_api_customer_success(client, auth_headers, db_session, admin_user):
    org = await _create_org(db_session)
    resp = await client.get(f"/api/v1/organizations/{org.id}/customer-success", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_id"] == str(org.id)
    assert len(data["milestones"]) == 6
    assert data["next_step"] is not None
    assert data["next_step"]["milestone_type"] == "first_workflow_win"


@pytest.mark.asyncio
async def test_api_triggers_404_unknown_org(client, auth_headers):
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/organizations/{fake_id}/expansion-triggers", headers=auth_headers)
    assert resp.status_code == 404
