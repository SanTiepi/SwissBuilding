"""Tests for the canonical cycle seed."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact_version import ArtifactVersion
from app.models.audience_pack import AudiencePack
from app.models.award_confirmation import AwardConfirmation
from app.models.building import Building
from app.models.client_request import ClientRequest
from app.models.completion_confirmation import CompletionConfirmation
from app.models.custody_event import CustodyEvent
from app.models.demo_scenario import DemoRunbookStep, DemoScenario
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.obligation import Obligation
from app.models.permit_procedure import PermitProcedure
from app.models.permit_step import PermitStep
from app.models.pilot_scorecard import PilotMetric, PilotScorecard
from app.models.post_works_link import PostWorksLink
from app.models.proof_delivery import ProofDelivery
from app.models.quote import Quote
from app.seeds.seed_canonical_cycle import seed_canonical_cycle


@pytest.mark.asyncio
async def test_canonical_cycle_creates_building(db_session: AsyncSession):
    """Seed creates the Lausanne building."""
    summary = await seed_canonical_cycle(db_session)
    result = await db_session.execute(select(Building).where(Building.city == "Lausanne", Building.egid == 999001))
    building = result.scalar_one_or_none()
    assert building is not None
    assert building.address == "Rue du Grand-Pont 12"
    assert str(building.id) == summary["building_id"]


@pytest.mark.asyncio
async def test_canonical_cycle_diagnostic_publication(db_session: AsyncSession):
    """Seed creates a diagnostic publication with structured summary."""
    await seed_canonical_cycle(db_session)
    result = await db_session.execute(
        select(DiagnosticReportPublication).where(DiagnosticReportPublication.mission_type == "asbestos_full")
    )
    pub = result.scalar_one_or_none()
    assert pub is not None
    assert pub.match_state == "auto_matched"
    assert pub.structured_summary is not None
    assert pub.structured_summary["pollutant"] == "asbestos"


@pytest.mark.asyncio
async def test_canonical_cycle_permit_procedure(db_session: AsyncSession):
    """Seed creates an approved permit procedure with 4 completed steps."""
    await seed_canonical_cycle(db_session)
    result = await db_session.execute(select(PermitProcedure).where(PermitProcedure.status == "approved"))
    proc = result.scalar_one_or_none()
    assert proc is not None
    assert proc.procedure_type == "suva_notification"

    steps_result = await db_session.execute(select(PermitStep).where(PermitStep.procedure_id == proc.id))
    steps = steps_result.scalars().all()
    assert len(steps) == 4
    assert all(s.status == "completed" for s in steps)


@pytest.mark.asyncio
async def test_canonical_cycle_rfq_chain(db_session: AsyncSession):
    """Seed creates RFQ chain: request → quote → award → completion."""
    await seed_canonical_cycle(db_session)

    cr = (await db_session.execute(select(ClientRequest).where(ClientRequest.status == "awarded"))).scalar_one_or_none()
    assert cr is not None

    q = (await db_session.execute(select(Quote).where(Quote.status == "awarded"))).scalar_one_or_none()
    assert q is not None
    assert q.client_request_id == cr.id

    award = (
        await db_session.execute(select(AwardConfirmation).where(AwardConfirmation.quote_id == q.id))
    ).scalar_one_or_none()
    assert award is not None

    cc = (
        await db_session.execute(
            select(CompletionConfirmation).where(CompletionConfirmation.status == "fully_confirmed")
        )
    ).scalar_one_or_none()
    assert cc is not None
    assert cc.award_confirmation_id == award.id


@pytest.mark.asyncio
async def test_canonical_cycle_post_works(db_session: AsyncSession):
    """Seed creates a finalized post-works link with grade delta."""
    await seed_canonical_cycle(db_session)
    result = await db_session.execute(select(PostWorksLink).where(PostWorksLink.status == "finalized"))
    pw = result.scalar_one_or_none()
    assert pw is not None
    assert pw.grade_delta is not None
    assert pw.grade_delta["before"] == "D"
    assert pw.grade_delta["after"] == "B"


@pytest.mark.asyncio
async def test_canonical_cycle_proof_deliveries(db_session: AsyncSession):
    """Seed creates 2 proof deliveries (authority + insurer)."""
    await seed_canonical_cycle(db_session)
    result = await db_session.execute(select(ProofDelivery))
    deliveries = result.scalars().all()
    audiences = {d.audience for d in deliveries}
    assert "authority" in audiences
    assert "insurer" in audiences
    auth_delivery = next(d for d in deliveries if d.audience == "authority")
    assert auth_delivery.status == "acknowledged"


@pytest.mark.asyncio
async def test_canonical_cycle_audience_packs(db_session: AsyncSession):
    """Seed creates 2 audience packs (insurer + authority)."""
    await seed_canonical_cycle(db_session)
    result = await db_session.execute(select(AudiencePack))
    packs = result.scalars().all()
    pack_types = {p.pack_type for p in packs}
    assert "insurer" in pack_types
    assert "authority" in pack_types


@pytest.mark.asyncio
async def test_canonical_cycle_artifact_versions_and_custody(db_session: AsyncSession):
    """Seed creates 2 artifact versions and 4 custody events."""
    await seed_canonical_cycle(db_session)

    av_result = await db_session.execute(select(ArtifactVersion))
    avs = av_result.scalars().all()
    assert len(avs) == 2
    assert all(av.status == "current" for av in avs)

    ce_result = await db_session.execute(select(CustodyEvent))
    ces = ce_result.scalars().all()
    assert len(ces) == 4


@pytest.mark.asyncio
async def test_canonical_cycle_obligations(db_session: AsyncSession):
    """Seed creates 2 obligations (1 completed, 1 upcoming)."""
    await seed_canonical_cycle(db_session)
    result = await db_session.execute(select(Obligation))
    obls = result.scalars().all()
    statuses = {o.status for o in obls}
    assert "completed" in statuses
    assert "upcoming" in statuses


@pytest.mark.asyncio
async def test_canonical_cycle_demo_scenario(db_session: AsyncSession):
    """Seed creates demo scenario with 5 runbook steps."""
    await seed_canonical_cycle(db_session)
    result = await db_session.execute(select(DemoScenario).where(DemoScenario.scenario_code == "canonical_cycle"))
    scenario = result.scalar_one_or_none()
    assert scenario is not None

    steps_result = await db_session.execute(select(DemoRunbookStep).where(DemoRunbookStep.scenario_id == scenario.id))
    steps = steps_result.scalars().all()
    assert len(steps) == 5


@pytest.mark.asyncio
async def test_canonical_cycle_pilot_scorecard(db_session: AsyncSession):
    """Seed creates pilot scorecard with 4 metrics."""
    await seed_canonical_cycle(db_session)
    result = await db_session.execute(select(PilotScorecard).where(PilotScorecard.pilot_code == "canonical_cycle_vd"))
    scorecard = result.scalar_one_or_none()
    assert scorecard is not None
    assert scorecard.status == "active"

    metrics_result = await db_session.execute(select(PilotMetric).where(PilotMetric.scorecard_id == scorecard.id))
    metrics = metrics_result.scalars().all()
    assert len(metrics) == 4


@pytest.mark.asyncio
async def test_canonical_cycle_idempotent(db_session: AsyncSession):
    """Running seed twice is safe (idempotent)."""
    await seed_canonical_cycle(db_session)
    await seed_canonical_cycle(db_session)  # should not raise

    result = await db_session.execute(select(Building).where(Building.egid == 999001))
    buildings = result.scalars().all()
    assert len(buildings) == 1
