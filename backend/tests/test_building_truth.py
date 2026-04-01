import uuid

import pytest

from app.models.building import Building
from app.models.organization import Organization
from app.schemas.building_truth import BuildingClaimCreate, BuildingDecisionCreate
from app.services.truth_service import (
    contest_claim,
    create_claim,
    enact_decision,
    get_claim_history,
    get_truth_state,
    list_claims,
    list_decisions,
    record_decision,
    reverse_decision,
    supersede_claim,
    verify_claim,
    withdraw_claim,
)


async def _create_org(db):
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="diagnostic_lab",
    )
    db.add(org)
    await db.flush()
    return org


async def _create_building(db, admin_user, org):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        organization_id=org.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


# ── Claim tests ──


class TestCreateClaim:
    async def test_create_claim(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        data = BuildingClaimCreate(
            claim_type="pollutant_presence",
            subject="asbestos in zone 3",
            assertion="present based on lab analysis",
            basis_type="diagnostic",
            basis_ids=["abc-123"],
            confidence=0.95,
        )
        claim = await create_claim(db_session, building.id, data, admin_user.id, org.id)
        assert claim.claim_type == "pollutant_presence"
        assert claim.subject == "asbestos in zone 3"
        assert claim.status == "asserted"
        assert claim.confidence == 0.95
        assert claim.building_id == building.id
        assert claim.claimed_by_id == admin_user.id


class TestVerifyClaim:
    async def test_verify_claim(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        data = BuildingClaimCreate(
            claim_type="pollutant_absence",
            subject="lead in facade",
            assertion="absent per lab results",
            basis_type="diagnostic",
        )
        claim = await create_claim(db_session, building.id, data, admin_user.id, org.id)
        verified = await verify_claim(db_session, claim.id, admin_user.id)
        assert verified.status == "verified"
        assert verified.verified_by_id == admin_user.id
        assert verified.verified_at is not None

    async def test_verify_already_superseded_fails(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        data = BuildingClaimCreate(
            claim_type="pollutant_presence",
            subject="pcb",
            assertion="present",
            basis_type="observation",
        )
        claim = await create_claim(db_session, building.id, data, admin_user.id, org.id)
        claim.status = "superseded"
        await db_session.flush()
        with pytest.raises(ValueError, match="Cannot verify"):
            await verify_claim(db_session, claim.id, admin_user.id)


class TestContestClaim:
    async def test_contest_claim(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        data = BuildingClaimCreate(
            claim_type="condition_assessment",
            subject="roof integrity",
            assertion="good condition",
            basis_type="observation",
        )
        claim = await create_claim(db_session, building.id, data, admin_user.id, org.id)
        contested = await contest_claim(db_session, claim.id, admin_user.id, "Visual damage observed")
        assert contested.status == "contested"
        assert contested.contestation_reason == "Visual damage observed"

    async def test_contest_withdrawn_fails(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        data = BuildingClaimCreate(
            claim_type="pollutant_presence",
            subject="radon",
            assertion="elevated",
            basis_type="diagnostic",
        )
        claim = await create_claim(db_session, building.id, data, admin_user.id, org.id)
        claim.status = "withdrawn"
        await db_session.flush()
        with pytest.raises(ValueError, match="Cannot contest"):
            await contest_claim(db_session, claim.id, admin_user.id, "reason")


class TestSupersedeClaim:
    async def test_supersede_claim(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        data1 = BuildingClaimCreate(
            claim_type="pollutant_presence",
            subject="asbestos in zone 1",
            assertion="present",
            basis_type="observation",
        )
        old = await create_claim(db_session, building.id, data1, admin_user.id, org.id)
        data2 = BuildingClaimCreate(
            claim_type="pollutant_absence",
            subject="asbestos in zone 1",
            assertion="absent after remediation",
            basis_type="diagnostic",
        )
        new = await create_claim(db_session, building.id, data2, admin_user.id, org.id)
        result = await supersede_claim(db_session, old.id, new.id)
        assert result.status == "superseded"
        assert result.superseded_by_id == new.id


class TestWithdrawClaim:
    async def test_withdraw_claim(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        data = BuildingClaimCreate(
            claim_type="other",
            subject="test",
            assertion="test assertion",
            basis_type="inference",
        )
        claim = await create_claim(db_session, building.id, data, admin_user.id, org.id)
        withdrawn = await withdraw_claim(db_session, claim.id)
        assert withdrawn.status == "withdrawn"


class TestListClaims:
    async def test_list_claims(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        for i in range(3):
            data = BuildingClaimCreate(
                claim_type="pollutant_presence",
                subject=f"substance {i}",
                assertion=f"found substance {i}",
                basis_type="diagnostic",
            )
            await create_claim(db_session, building.id, data, admin_user.id, org.id)
        items, total = await list_claims(db_session, building.id)
        assert total == 3
        assert len(items) == 3

    async def test_list_claims_filtered(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        data1 = BuildingClaimCreate(
            claim_type="pollutant_presence",
            subject="asbestos",
            assertion="present",
            basis_type="diagnostic",
        )
        await create_claim(db_session, building.id, data1, admin_user.id, org.id)
        data2 = BuildingClaimCreate(
            claim_type="condition_assessment",
            subject="roof",
            assertion="damaged",
            basis_type="observation",
        )
        await create_claim(db_session, building.id, data2, admin_user.id, org.id)
        _items, total = await list_claims(db_session, building.id, claim_type="pollutant_presence")
        assert total == 1


# ── Decision tests ──


class TestRecordDecision:
    async def test_record_decision(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        data = BuildingDecisionCreate(
            decision_type="readiness_override",
            title="Override readiness for building sale",
            outcome="approved",
            rationale="All critical pollutants remediated, remaining items are low-risk.",
            authority_level="director",
        )
        decision = await record_decision(db_session, building.id, data, admin_user.id, org.id)
        assert decision.decision_type == "readiness_override"
        assert decision.status == "pending"
        assert decision.outcome == "approved"
        assert decision.authority_level == "director"
        assert decision.reversible is True


class TestEnactDecision:
    async def test_enact_decision(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        data = BuildingDecisionCreate(
            decision_type="intervention_approval",
            title="Approve asbestos removal",
            outcome="approved",
            rationale="Budget available, contractor vetted.",
        )
        decision = await record_decision(db_session, building.id, data, admin_user.id, org.id)
        enacted = await enact_decision(db_session, decision.id)
        assert enacted.status == "enacted"
        assert enacted.enacted_at is not None


class TestReverseDecision:
    async def test_reverse_decision(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        data = BuildingDecisionCreate(
            decision_type="risk_acceptance",
            title="Accept low radon risk",
            outcome="accepted",
            rationale="Below threshold.",
        )
        decision = await record_decision(db_session, building.id, data, admin_user.id, org.id)
        decision.status = "enacted"
        await db_session.flush()
        reversed_dec = await reverse_decision(
            db_session, decision.id, admin_user.id, "New measurements show higher levels"
        )
        assert reversed_dec.status == "reversed"
        assert reversed_dec.reversal_reason == "New measurements show higher levels"

    async def test_reverse_irreversible_fails(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        data = BuildingDecisionCreate(
            decision_type="permit_decision",
            title="Permit granted",
            outcome="granted",
            rationale="All conditions met.",
            reversible=False,
        )
        decision = await record_decision(db_session, building.id, data, admin_user.id, org.id)
        with pytest.raises(ValueError, match="irreversible"):
            await reverse_decision(db_session, decision.id, admin_user.id, "changed mind")


class TestListDecisions:
    async def test_list_decisions(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        for i in range(2):
            data = BuildingDecisionCreate(
                decision_type="scope_change",
                title=f"Scope change {i}",
                outcome=f"changed {i}",
                rationale=f"Reason {i}",
            )
            await record_decision(db_session, building.id, data, admin_user.id, org.id)
        _items, total = await list_decisions(db_session, building.id)
        assert total == 2


# ── Truth state tests ──


class TestGetTruthState:
    async def test_truth_state(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        # Create a mix of claims
        data1 = BuildingClaimCreate(
            claim_type="pollutant_presence",
            subject="asbestos",
            assertion="present",
            basis_type="diagnostic",
        )
        claim1 = await create_claim(db_session, building.id, data1, admin_user.id, org.id)
        data2 = BuildingClaimCreate(
            claim_type="pollutant_absence",
            subject="lead",
            assertion="absent",
            basis_type="diagnostic",
        )
        await create_claim(db_session, building.id, data2, admin_user.id, org.id)
        await contest_claim(db_session, claim1.id, admin_user.id, "Needs lab confirmation")

        # Create a decision
        dec_data = BuildingDecisionCreate(
            decision_type="claim_resolution",
            title="Resolve asbestos claim",
            outcome="verified after lab confirmation",
            rationale="Lab results confirm presence.",
        )
        await record_decision(db_session, building.id, dec_data, admin_user.id, org.id)

        state = await get_truth_state(db_session, building.id)
        assert len(state["active_claims"]) == 1  # only the "absent" one
        assert len(state["contested_claims"]) == 1
        assert len(state["recent_decisions"]) == 1
        assert "claims_by_status" in state["summary"]


class TestGetClaimHistory:
    async def test_claim_history_by_subject(self, db_session, admin_user):
        org = await _create_org(db_session)
        building = await _create_building(db_session, admin_user, org)
        for subject in ["asbestos in zone 1", "lead in facade", "asbestos in zone 2"]:
            data = BuildingClaimCreate(
                claim_type="pollutant_presence",
                subject=subject,
                assertion="found",
                basis_type="diagnostic",
            )
            await create_claim(db_session, building.id, data, admin_user.id, org.id)
        history = await get_claim_history(db_session, building.id, subject="asbestos")
        assert len(history) == 2
