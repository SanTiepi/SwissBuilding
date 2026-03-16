"""
Tests for seed_demo_authority.py — Authority-Ready Demo Seed.

Uses the same conftest patterns (SQLite in-memory, session-scoped engine,
function-scoped cleanup).
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.building import Building
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.readiness_assessment import ReadinessAssessment
from app.models.sample import Sample
from app.models.user import User
from app.seeds.seed_demo_authority import seed_authority_demo


@pytest.fixture
async def seeded_building(db_session):
    """Create a minimal building + diagnostic + user for the authority demo seed."""
    user = User(
        id=uuid.uuid4(),
        email="seed-test@test.ch",
        password_hash="$2b$12$dummy",
        first_name="Seed",
        last_name="Tester",
        role="admin",
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.flush()

    building = Building(
        id=uuid.uuid4(),
        address="Rue du Demo 42",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1968,
        building_type="residential",
        created_by=user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.flush()

    diagnostic = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="asbestos",
        diagnostic_context="AvT",
        status="draft",
        diagnostician_id=user.id,
    )
    db_session.add(diagnostic)
    await db_session.commit()

    return {"building": building, "diagnostic": diagnostic, "user": user}


@pytest.mark.asyncio
async def test_seed_creates_samples_for_all_pollutants(db_session, seeded_building):
    """Seed creates samples for all 5 pollutants."""
    result = await seed_authority_demo(db_session)

    assert result["status"] == "completed"
    assert result["samples_count"] == 5

    # Verify all 5 pollutant types are present
    stmt = select(Sample).where(
        Sample.diagnostic_id == seeded_building["diagnostic"].id,
    )
    samples_result = await db_session.execute(stmt)
    samples = samples_result.scalars().all()

    pollutant_types = {s.pollutant_type for s in samples}
    assert pollutant_types == {"asbestos", "pcb", "lead", "hap", "radon"}

    # Check asbestos sample details
    asbestos = next(s for s in samples if s.pollutant_type == "asbestos")
    assert asbestos.threshold_exceeded is True
    assert asbestos.risk_level == "high"
    assert asbestos.cfst_work_category == "major"
    assert asbestos.waste_disposal_type == "special"
    assert asbestos.action_required == "Désamiantage complet"

    # Check PCB sample details
    pcb = next(s for s in samples if s.pollutant_type == "pcb")
    assert pcb.threshold_exceeded is True
    assert pcb.risk_level == "medium"
    assert pcb.waste_disposal_type == "type_e"

    # Check radon sample details
    radon = next(s for s in samples if s.pollutant_type == "radon")
    assert radon.threshold_exceeded is True
    assert radon.concentration == 450.0
    assert radon.unit == "Bq/m3"


@pytest.mark.asyncio
async def test_seed_creates_compliance_artefacts(db_session, seeded_building):
    """Seed creates SUVA notification and cantonal form artefacts."""
    await seed_authority_demo(db_session)

    building_id = seeded_building["building"].id
    stmt = select(ComplianceArtefact).where(
        ComplianceArtefact.building_id == building_id,
    )
    result = await db_session.execute(stmt)
    artefacts = result.scalars().all()

    assert len(artefacts) == 2

    types = {a.artefact_type for a in artefacts}
    assert types == {"suva_notification", "cantonal_notification"}

    for artefact in artefacts:
        assert artefact.status == "submitted"
        assert artefact.submitted_at is not None


@pytest.mark.asyncio
async def test_seed_creates_interventions(db_session, seeded_building):
    """Seed creates asbestos removal (completed) and PCB removal (in_progress)."""
    await seed_authority_demo(db_session)

    building_id = seeded_building["building"].id
    stmt = select(Intervention).where(
        Intervention.building_id == building_id,
    )
    result = await db_session.execute(stmt)
    interventions = result.scalars().all()

    assert len(interventions) == 2

    statuses = {i.status for i in interventions}
    assert statuses == {"completed", "in_progress"}

    types = {i.intervention_type for i in interventions}
    assert "asbestos_removal" in types
    assert "removal" in types


@pytest.mark.asyncio
async def test_seed_runs_readiness_evaluations(db_session, seeded_building):
    """Seed runs readiness evaluations for all 4 types."""
    await seed_authority_demo(db_session)

    building_id = seeded_building["building"].id
    stmt = select(ReadinessAssessment).where(
        ReadinessAssessment.building_id == building_id,
    )
    result = await db_session.execute(stmt)
    assessments = result.scalars().all()

    assert len(assessments) == 4

    readiness_types = {a.readiness_type for a in assessments}
    assert readiness_types == {"safe_to_start", "safe_to_tender", "safe_to_reopen", "safe_to_requalify"}

    for assessment in assessments:
        assert assessment.status is not None
        assert assessment.score is not None
        assert assessment.checks_json is not None


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session, seeded_building):
    """Running seed twice doesn't duplicate data."""
    result1 = await seed_authority_demo(db_session)
    assert result1["status"] == "completed"

    result2 = await seed_authority_demo(db_session)
    assert result2["status"] == "completed"

    # Verify no duplicates: samples
    diagnostic_id = seeded_building["diagnostic"].id
    stmt = select(func.count()).select_from(Sample).where(Sample.diagnostic_id == diagnostic_id)
    count_result = await db_session.execute(stmt)
    sample_count = count_result.scalar()
    assert sample_count == 5

    # Verify no duplicates: artefacts
    building_id = seeded_building["building"].id
    stmt = (
        select(func.count())
        .select_from(ComplianceArtefact)
        .where(
            ComplianceArtefact.building_id == building_id,
        )
    )
    count_result = await db_session.execute(stmt)
    artefact_count = count_result.scalar()
    assert artefact_count == 2

    # Verify no duplicates: interventions
    stmt = (
        select(func.count())
        .select_from(Intervention)
        .where(
            Intervention.building_id == building_id,
        )
    )
    count_result = await db_session.execute(stmt)
    intervention_count = count_result.scalar()
    assert intervention_count == 2

    # Verify no duplicates: documents
    stmt = (
        select(func.count())
        .select_from(Document)
        .where(
            Document.building_id == building_id,
        )
    )
    count_result = await db_session.execute(stmt)
    doc_count = count_result.scalar()
    assert doc_count == 3


@pytest.mark.asyncio
async def test_seed_creates_documents(db_session, seeded_building):
    """Seed creates 3 reference documents."""
    await seed_authority_demo(db_session)

    building_id = seeded_building["building"].id
    stmt = select(Document).where(Document.building_id == building_id)
    result = await db_session.execute(stmt)
    documents = result.scalars().all()

    assert len(documents) == 3

    doc_types = {d.document_type for d in documents}
    assert doc_types == {"diagnostic_report", "suva_notification", "waste_elimination_plan"}

    for doc in documents:
        assert doc.file_name is not None
        assert doc.file_path is not None
        assert doc.mime_type == "application/pdf"


@pytest.mark.asyncio
async def test_seed_updates_diagnostic_metadata(db_session, seeded_building):
    """Seed updates diagnostic to completed with SUVA notification metadata."""
    await seed_authority_demo(db_session)

    diagnostic_id = seeded_building["diagnostic"].id
    diagnostic = await db_session.get(Diagnostic, diagnostic_id)

    assert diagnostic.status == "completed"
    assert diagnostic.diagnostic_type == "full"
    assert diagnostic.suva_notification_required is True
    assert diagnostic.suva_notification_date == date(2025, 11, 15)
    assert diagnostic.canton_notification_date == date(2025, 11, 20)
    assert diagnostic.laboratory is not None
    assert diagnostic.methodology is not None


@pytest.mark.asyncio
async def test_seed_skips_when_no_building(db_session):
    """Seed returns skip status when no building with diagnostic exists."""
    result = await seed_authority_demo(db_session)
    assert result["status"] == "skipped"
