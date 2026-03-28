"""Tests for the Decision Replay Layer (Bloc 8).

Tests the replayable snapshot model, basis validity checks, stale decision
detection, and API endpoints.
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.models.building import Building
from app.models.building_claim import BuildingClaim, BuildingDecision
from app.models.decision_replay import DecisionReplay
from app.models.organization import Organization
from app.models.user import User
from app.services.decision_replay_service import (
    _assess_replay_status,
    check_basis_validity,
    create_replay,
    get_decision_replays,
    get_replay_for_decision,
    get_stale_decisions,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_org(db):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="diagnostic_lab",
    )
    db.add(org)
    await db.flush()
    return org


async def _create_user(db, org_id=None):
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email=f"{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org_id,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_building(db, user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=user.id,
        status="active",
    )
    db.add(building)
    await db.flush()
    return building


async def _create_claim(db, building_id, org_id, user_id, **kwargs):
    defaults = {
        "building_id": building_id,
        "organization_id": org_id,
        "claimed_by_id": user_id,
        "claim_type": "pollutant_presence",
        "subject": "Amiante dans dalle",
        "assertion": "Presence confirmee par diagnostic",
        "basis_type": "diagnostic",
        "status": "asserted",
    }
    defaults.update(kwargs)
    claim = BuildingClaim(id=uuid.uuid4(), **defaults)
    db.add(claim)
    await db.flush()
    return claim


async def _create_decision(db, building_id, org_id, user_id, basis_claims=None, **kwargs):
    defaults = {
        "building_id": building_id,
        "organization_id": org_id,
        "decision_maker_id": user_id,
        "decision_type": "intervention_approval",
        "title": "Approuver intervention amiante",
        "outcome": "Intervention approuvee",
        "rationale": "Amiante confirme, intervention necessaire",
        "authority_level": "operator",
        "status": "enacted",
        "enacted_at": datetime.now(UTC),
        "basis_claims": basis_claims,
    }
    defaults.update(kwargs)
    decision = BuildingDecision(id=uuid.uuid4(), **defaults)
    db.add(decision)
    await db.flush()
    return decision


# ---------------------------------------------------------------------------
# Unit: _assess_replay_status
# ---------------------------------------------------------------------------


class TestAssessReplayStatus:
    def test_current_status_no_changes(self):
        status, valid, inv, summary = _assess_replay_status({}, [], False)
        assert status == "current"
        assert valid is True
        assert inv == []
        assert "aucun changement" in summary.lower()

    def test_partially_stale_few_changes(self):
        changes = [{"title": f"change {i}", "severity": "info"} for i in range(3)]
        status, valid, _inv, summary = _assess_replay_status({}, changes, False)
        assert status == "partially_stale"
        assert valid is True
        assert "3 changement" in summary

    def test_stale_many_changes(self):
        changes = [{"title": f"change {i}", "severity": "info"} for i in range(15)]
        status, valid, _inv, _summary = _assess_replay_status({}, changes, False)
        assert status == "stale"
        assert valid is False

    def test_invalidated_claims_changed(self):
        status, valid, inv, _summary = _assess_replay_status({}, [], True)
        assert status == "invalidated"
        assert valid is False
        assert len(inv) >= 1

    def test_invalidated_severe_changes(self):
        changes = [{"title": "Changement critique", "severity": "critical"}]
        status, valid, _inv, _summary = _assess_replay_status({}, changes, False)
        assert status == "invalidated"
        assert valid is False


# ---------------------------------------------------------------------------
# Service: create_replay
# ---------------------------------------------------------------------------


class TestCreateReplay:
    async def test_create_replay_basic(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org.id)
        building = await _create_building(db_session, user)
        decision = await _create_decision(db_session, building.id, org.id, user.id)
        await db_session.commit()

        replay = await create_replay(db_session, decision.id)
        await db_session.commit()

        assert replay.id is not None
        assert replay.building_id == building.id
        assert replay.decision_id == decision.id
        assert replay.basis_snapshot is not None
        assert replay.replay_status in ("current", "partially_stale", "stale", "invalidated")
        assert replay.replay_summary is not None

    async def test_create_replay_captures_decision_details(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org.id)
        building = await _create_building(db_session, user)
        decision = await _create_decision(db_session, building.id, org.id, user.id)
        await db_session.commit()

        replay = await create_replay(db_session, decision.id)
        await db_session.commit()

        snapshot = replay.basis_snapshot
        assert snapshot["decision_type"] == "intervention_approval"
        assert snapshot["outcome"] == "Intervention approuvee"
        assert snapshot["rationale"] == "Amiante confirme, intervention necessaire"

    async def test_create_replay_with_basis_claims(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org.id)
        building = await _create_building(db_session, user)
        claim = await _create_claim(db_session, building.id, org.id, user.id)
        decision = await _create_decision(
            db_session,
            building.id,
            org.id,
            user.id,
            basis_claims=[str(claim.id)],
        )
        await db_session.commit()

        replay = await create_replay(db_session, decision.id)
        await db_session.commit()

        snapshot = replay.basis_snapshot
        assert len(snapshot["claims_detail"]) == 1
        assert snapshot["claims_detail"][0]["id"] == str(claim.id)
        assert snapshot["claims_detail"][0]["status"] == "asserted"

    async def test_create_replay_not_found(self, db_session):
        with pytest.raises(ValueError, match="introuvable"):
            await create_replay(db_session, uuid.uuid4())

    async def test_create_replay_captures_trust_state(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org.id)
        building = await _create_building(db_session, user)
        decision = await _create_decision(db_session, building.id, org.id, user.id)
        await db_session.commit()

        replay = await create_replay(db_session, decision.id)
        await db_session.commit()

        assert replay.trust_state_at_decision is not None
        assert "overall_trust" in replay.trust_state_at_decision


# ---------------------------------------------------------------------------
# Service: get_decision_replays
# ---------------------------------------------------------------------------


class TestGetDecisionReplays:
    async def test_list_replays_for_building(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org.id)
        building = await _create_building(db_session, user)
        d1 = await _create_decision(db_session, building.id, org.id, user.id, title="Decision 1")
        d2 = await _create_decision(db_session, building.id, org.id, user.id, title="Decision 2")
        await db_session.commit()

        await create_replay(db_session, d1.id)
        await create_replay(db_session, d2.id)
        await db_session.commit()

        replays = await get_decision_replays(db_session, building.id)
        assert len(replays) == 2

    async def test_list_replays_empty(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org.id)
        building = await _create_building(db_session, user)
        await db_session.commit()

        replays = await get_decision_replays(db_session, building.id)
        assert replays == []


# ---------------------------------------------------------------------------
# Service: get_replay_for_decision
# ---------------------------------------------------------------------------


class TestGetReplayForDecision:
    async def test_get_latest_replay(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org.id)
        building = await _create_building(db_session, user)
        decision = await _create_decision(db_session, building.id, org.id, user.id)
        await db_session.commit()

        await create_replay(db_session, decision.id)
        await db_session.commit()

        replay = await get_replay_for_decision(db_session, decision.id)
        assert replay is not None
        assert replay.decision_id == decision.id

    async def test_get_replay_not_found(self, db_session):
        replay = await get_replay_for_decision(db_session, uuid.uuid4())
        assert replay is None


# ---------------------------------------------------------------------------
# Service: check_basis_validity
# ---------------------------------------------------------------------------


class TestCheckBasisValidity:
    async def test_check_validity_current(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org.id)
        building = await _create_building(db_session, user)
        decision = await _create_decision(db_session, building.id, org.id, user.id)
        await db_session.commit()

        replay = await create_replay(db_session, decision.id)
        await db_session.commit()

        result = await check_basis_validity(db_session, replay.id)
        await db_session.commit()

        assert result.replay_id == replay.id
        assert result.decision_id == decision.id
        assert isinstance(result.basis_still_valid, bool)
        assert result.replay_status in ("current", "partially_stale", "stale", "invalidated")
        assert isinstance(result.replay_summary, str)

    async def test_check_validity_not_found(self, db_session):
        with pytest.raises(ValueError, match="introuvable"):
            await check_basis_validity(db_session, uuid.uuid4())

    async def test_check_validity_detects_claim_change(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org.id)
        building = await _create_building(db_session, user)
        claim = await _create_claim(db_session, building.id, org.id, user.id)
        decision = await _create_decision(
            db_session,
            building.id,
            org.id,
            user.id,
            basis_claims=[str(claim.id)],
        )
        await db_session.commit()

        replay = await create_replay(db_session, decision.id)
        await db_session.commit()

        # Change the claim status
        claim.status = "superseded"
        await db_session.commit()

        result = await check_basis_validity(db_session, replay.id)
        await db_session.commit()

        # Should detect the claim change
        assert result.basis_still_valid is False
        assert result.replay_status == "invalidated"
        assert len(result.changes_detected) >= 1


# ---------------------------------------------------------------------------
# Service: get_stale_decisions
# ---------------------------------------------------------------------------


class TestGetStaleDecisions:
    async def test_get_stale_decisions_empty(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org.id)
        building = await _create_building(db_session, user)
        await db_session.commit()

        stale = await get_stale_decisions(db_session, building.id)
        assert stale == []

    async def test_get_stale_decisions_with_invalidated(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org.id)
        building = await _create_building(db_session, user)
        claim = await _create_claim(db_session, building.id, org.id, user.id)
        decision = await _create_decision(
            db_session,
            building.id,
            org.id,
            user.id,
            basis_claims=[str(claim.id)],
        )
        await db_session.commit()

        replay = await create_replay(db_session, decision.id)
        await db_session.commit()

        # Change claim to trigger invalidation
        claim.status = "contested"
        await db_session.commit()

        # Re-check validity to update replay status
        await check_basis_validity(db_session, replay.id)
        await db_session.commit()

        stale = await get_stale_decisions(db_session, building.id)
        assert len(stale) >= 1
        assert stale[0].decision_id == decision.id
        assert stale[0].replay_status == "invalidated"


# ---------------------------------------------------------------------------
# Model: DecisionReplay
# ---------------------------------------------------------------------------


class TestDecisionReplayModel:
    async def test_model_fields(self, db_session):
        org = await _create_org(db_session)
        user = await _create_user(db_session, org.id)
        building = await _create_building(db_session, user)
        decision = await _create_decision(db_session, building.id, org.id, user.id)
        await db_session.commit()

        now = datetime.now(UTC)
        replay = DecisionReplay(
            id=uuid.uuid4(),
            building_id=building.id,
            decision_id=decision.id,
            basis_snapshot={"test": True},
            trust_state_at_decision={"overall_trust": 0.75},
            completeness_at_decision=0.85,
            readiness_at_decision={"verdict": "clear"},
            changes_since=[{"title": "change"}],
            basis_still_valid=True,
            invalidated_by=None,
            replay_status="current",
            replay_summary="Base actuelle",
            replayed_at=now,
            created_at=now,
        )
        db_session.add(replay)
        await db_session.commit()
        await db_session.refresh(replay)

        assert replay.basis_snapshot == {"test": True}
        assert replay.completeness_at_decision == 0.85
        assert replay.replay_status == "current"
        assert replay.basis_still_valid is True


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


class TestDecisionReplayAPI:
    async def _create_decision_for_api(self, db_session, building, user, org):
        decision = await _create_decision(db_session, building.id, org.id, user.id)
        await db_session.commit()
        return decision

    async def _get_or_create_org(self, db_session, user):
        if user.organization_id:
            from sqlalchemy import select

            result = await db_session.execute(select(Organization).where(Organization.id == user.organization_id))
            org = result.scalar_one_or_none()
            if org:
                return org
        org = await _create_org(db_session)
        user.organization_id = org.id
        await db_session.commit()
        return org

    async def test_create_replay_api(self, client, auth_headers, sample_building, admin_user, db_session):
        org = await self._get_or_create_org(db_session, admin_user)
        decision = await self._create_decision_for_api(db_session, sample_building, admin_user, org)

        resp = await client.post(
            f"/api/v1/decisions/{decision.id}/replay",
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["decision_id"] == str(decision.id)
        assert data["replay_status"] in ("current", "partially_stale", "stale", "invalidated")

    async def test_get_replay_api(self, client, auth_headers, sample_building, admin_user, db_session):
        org = await self._get_or_create_org(db_session, admin_user)
        decision = await self._create_decision_for_api(db_session, sample_building, admin_user, org)

        # Create replay first
        await client.post(
            f"/api/v1/decisions/{decision.id}/replay",
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/decisions/{decision.id}/replay",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision_id"] == str(decision.id)
        assert "basis_snapshot" in data

    async def test_get_replay_not_found_api(self, client, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/decisions/{fake_id}/replay",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_list_replays_api(self, client, auth_headers, sample_building, admin_user, db_session):
        org = await self._get_or_create_org(db_session, admin_user)
        decision = await self._create_decision_for_api(db_session, sample_building, admin_user, org)

        await client.post(
            f"/api/v1/decisions/{decision.id}/replay",
            headers=auth_headers,
        )

        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/decision-replays",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == str(sample_building.id)
        assert data["total"] >= 1

    async def test_stale_decisions_api(self, client, auth_headers, sample_building):
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/stale-decisions",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_stale_decisions_404_building(self, client, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/buildings/{fake_id}/stale-decisions",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_list_replays_404_building(self, client, auth_headers):
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/buildings/{fake_id}/decision-replays",
            headers=auth_headers,
        )
        assert resp.status_code == 404
