"""Tests for the decision view service and API endpoint."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact_version import ArtifactVersion
from app.models.audience_pack import AudiencePack
from app.models.building import Building
from app.models.custody_event import CustodyEvent
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.obligation import Obligation
from app.models.permit_procedure import PermitProcedure
from app.models.proof_delivery import ProofDelivery
from app.models.unknown_issue import UnknownIssue
from app.models.user import User
from app.services.decision_view_service import get_building_decision_view


@pytest.fixture
async def decision_building(db_session: AsyncSession, admin_user: User):
    """Create a building for decision view tests."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue de Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decision_view_nonexistent_building(db_session: AsyncSession):
    """Returns None for a non-existent building."""
    result = await get_building_decision_view(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_decision_view_empty_building(db_session: AsyncSession, decision_building: Building):
    """Returns default values for a building with no related data."""
    result = await get_building_decision_view(db_session, decision_building.id)
    assert result is not None
    assert result.building_id == decision_building.id
    assert result.passport_grade == "F"
    assert result.blockers == []
    assert result.conditions == []
    assert result.clear_items == []
    assert len(result.audience_readiness) == 4
    assert result.proof_chain == []
    assert result.roi.time_saved_hours == 0.0


@pytest.mark.asyncio
async def test_decision_view_blocked_procedure(db_session: AsyncSession, decision_building: Building, admin_user: User):
    """Blocked procedure appears as a blocker."""
    proc = PermitProcedure(
        id=uuid.uuid4(),
        building_id=decision_building.id,
        procedure_type="suva_notification",
        title="SUVA blocked",
        status="complement_requested",
        authority_name="SUVA",
    )
    db_session.add(proc)
    await db_session.commit()

    result = await get_building_decision_view(db_session, decision_building.id)
    assert len(result.blockers) == 1
    assert result.blockers[0].category == "procedure_blocked"
    assert "SUVA blocked" in result.blockers[0].title


@pytest.mark.asyncio
async def test_decision_view_approved_procedure_is_clear(
    db_session: AsyncSession, decision_building: Building, admin_user: User
):
    """Approved procedure appears as clear item."""
    proc = PermitProcedure(
        id=uuid.uuid4(),
        building_id=decision_building.id,
        procedure_type="construction_permit",
        title="Permit approved",
        status="approved",
        approved_at=datetime.now(UTC),
    )
    db_session.add(proc)
    await db_session.commit()

    result = await get_building_decision_view(db_session, decision_building.id)
    assert len(result.clear_items) >= 1
    assert any(c.category == "procedure_approved" for c in result.clear_items)


@pytest.mark.asyncio
async def test_decision_view_overdue_obligation(db_session: AsyncSession, decision_building: Building):
    """Overdue obligation appears as a blocker."""
    obl = Obligation(
        id=uuid.uuid4(),
        building_id=decision_building.id,
        title="Overdue inspection",
        obligation_type="regulatory_inspection",
        due_date=date.today() - timedelta(days=10),
        status="overdue",
        priority="high",
    )
    db_session.add(obl)
    await db_session.commit()

    result = await get_building_decision_view(db_session, decision_building.id)
    assert len(result.blockers) == 1
    assert result.blockers[0].category == "overdue_obligation"


@pytest.mark.asyncio
async def test_decision_view_completed_obligation_is_clear(db_session: AsyncSession, decision_building: Building):
    """Completed obligation appears as clear item."""
    obl = Obligation(
        id=uuid.uuid4(),
        building_id=decision_building.id,
        title="Done inspection",
        obligation_type="regulatory_inspection",
        due_date=date.today() - timedelta(days=5),
        status="completed",
        priority="medium",
        completed_at=datetime.now(UTC),
    )
    db_session.add(obl)
    await db_session.commit()

    result = await get_building_decision_view(db_session, decision_building.id)
    assert any(c.category == "obligation_completed" for c in result.clear_items)


@pytest.mark.asyncio
async def test_decision_view_blocking_unknown(db_session: AsyncSession, decision_building: Building):
    """Blocking unknown issue appears as a blocker."""
    unk = UnknownIssue(
        id=uuid.uuid4(),
        building_id=decision_building.id,
        title="Missing radon data",
        unknown_type="missing_diagnostic",
        status="open",
        blocks_readiness=True,
    )
    db_session.add(unk)
    await db_session.commit()

    result = await get_building_decision_view(db_session, decision_building.id)
    assert len(result.blockers) == 1
    assert result.blockers[0].category == "unresolved_unknown"


@pytest.mark.asyncio
async def test_decision_view_nonblocking_unknown_is_condition(db_session: AsyncSession, decision_building: Building):
    """Non-blocking unknown appears as a condition."""
    unk = UnknownIssue(
        id=uuid.uuid4(),
        building_id=decision_building.id,
        title="Missing HAP data",
        unknown_type="missing_diagnostic",
        status="open",
        blocks_readiness=False,
    )
    db_session.add(unk)
    await db_session.commit()

    result = await get_building_decision_view(db_session, decision_building.id)
    assert len(result.conditions) >= 1
    assert any(c.category == "incomplete_coverage" for c in result.conditions)


@pytest.mark.asyncio
async def test_decision_view_audience_pack(db_session: AsyncSession, decision_building: Building, admin_user: User):
    """Audience pack is reflected in audience readiness."""
    pack = AudiencePack(
        id=uuid.uuid4(),
        building_id=decision_building.id,
        pack_type="insurer",
        pack_version=1,
        status="ready",
        generated_by_user_id=admin_user.id,
        sections={"building_identity": {}, "diagnostics": {}},
        unknowns_summary=[{"type": "test"}],
        contradictions_summary=[],
        residual_risk_summary=[{"risk": "low"}],
        trust_refs=[{"ref": 1}],
        proof_refs=[{"doc": 1}, {"doc": 2}],
        content_hash="abc123",
        generated_at=datetime.now(UTC),
    )
    db_session.add(pack)
    await db_session.commit()

    result = await get_building_decision_view(db_session, decision_building.id)
    insurer_ar = next(ar for ar in result.audience_readiness if ar.audience == "insurer")
    assert insurer_ar.has_pack is True
    assert insurer_ar.latest_pack_version == 1
    assert insurer_ar.unknowns_count == 1
    assert insurer_ar.residual_risks_count == 1
    assert insurer_ar.proof_refs_count == 2


@pytest.mark.asyncio
async def test_decision_view_proof_chain_diagnostic_pub(db_session: AsyncSession, decision_building: Building):
    """Diagnostic publication appears in proof chain."""
    pub = DiagnosticReportPublication(
        id=uuid.uuid4(),
        building_id=decision_building.id,
        source_system="batiscan",
        source_mission_id="TEST-001",
        match_state="auto_matched",
        match_key_type="egid",
        mission_type="asbestos_full",
        payload_hash="abc123def456",
        published_at=datetime.now(UTC),
    )
    db_session.add(pub)
    await db_session.commit()

    result = await get_building_decision_view(db_session, decision_building.id)
    assert any(p.entity_type == "diagnostic_publication" for p in result.proof_chain)


@pytest.mark.asyncio
async def test_decision_view_custody_posture(db_session: AsyncSession, decision_building: Building, admin_user: User):
    """Custody posture counts artifact versions and events."""
    av = ArtifactVersion(
        id=uuid.uuid4(),
        artifact_type="audience_pack",
        artifact_id=uuid.uuid4(),
        version_number=1,
        status="current",
        created_by_user_id=admin_user.id,
        created_at=datetime.now(UTC),
    )
    db_session.add(av)
    await db_session.flush()

    ce = CustodyEvent(
        id=uuid.uuid4(),
        artifact_version_id=av.id,
        event_type="created",
        actor_type="system",
        occurred_at=datetime.now(UTC),
    )
    db_session.add(ce)
    await db_session.commit()

    result = await get_building_decision_view(db_session, decision_building.id)
    assert result.custody_posture.total_artifact_versions >= 1
    assert result.custody_posture.total_custody_events >= 1


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decision_view_schema_serialization(db_session: AsyncSession, decision_building: Building):
    """DecisionView schema serializes correctly."""
    result = await get_building_decision_view(db_session, decision_building.id)
    assert result is not None
    data = result.model_dump()
    assert "building_id" in data
    assert "passport_grade" in data
    assert "blockers" in data
    assert "audience_readiness" in data
    assert len(data["audience_readiness"]) == 4
    assert "proof_chain" in data
    assert "roi" in data
    assert "custody_posture" in data


@pytest.mark.asyncio
async def test_decision_view_proof_chain_delivery(db_session: AsyncSession, decision_building: Building):
    """Proof delivery appears in proof chain."""
    pd = ProofDelivery(
        id=uuid.uuid4(),
        building_id=decision_building.id,
        target_type="authority_pack",
        target_id=uuid.uuid4(),
        audience="authority",
        delivery_method="email",
        status="acknowledged",
        sent_at=datetime.now(UTC),
        content_hash="testhash123",
    )
    db_session.add(pd)
    await db_session.commit()

    result = await get_building_decision_view(db_session, decision_building.id)
    auth_proofs = [p for p in result.proof_chain if p.entity_type == "proof_delivery"]
    assert len(auth_proofs) >= 1
    assert auth_proofs[0].status == "acknowledged"
