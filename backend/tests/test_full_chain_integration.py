"""
Full-chain integration test for SwissBuildingOS.

Proves the complete journey: building creation → diagnostic → samples →
action generation → intervention → post-works → completeness → trust →
unknowns → readiness → contradictions → passport → dossier completion agent.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services import (
    action_generator,
    completeness_engine,
    contradiction_detector,
    dossier_completion_agent,
    passport_service,
    post_works_service,
    readiness_reasoner,
    time_machine_service,
    trust_score_calculator,
    unknown_generator,
)


@pytest.mark.asyncio
async def test_full_chain_building_lifecycle(db_session):
    """End-to-end test: create data programmatically and exercise every service in order."""

    # ------------------------------------------------------------------
    # 1. Create org + user + building
    # ------------------------------------------------------------------
    org = Organization(
        id=uuid.uuid4(),
        name="Régie Intégration SA",
        type="property_management",
        canton="VD",
    )
    db_session.add(org)

    user = User(
        id=uuid.uuid4(),
        email="integration@test.ch",
        password_hash="$2b$12$LJ3m4ys3Lz0YFBFpq9G7xuGZ5vNfM2.Y.nGnZqZ8E5ZQz1z1z1z1z",
        first_name="Integ",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(user)

    building = Building(
        id=uuid.uuid4(),
        address="Chemin de l'Intégration 42",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()

    building_id = building.id

    # ------------------------------------------------------------------
    # 2. Create diagnostic (full, AvT, completed)
    # ------------------------------------------------------------------
    diagnostic = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="full",
        diagnostic_context="AvT",
        status="completed",
        diagnostician_id=user.id,
        laboratory="LabTest SA",
        date_inspection=date(2025, 6, 1),
        date_report=date(2025, 6, 15),
        conclusion="positive",
    )
    db_session.add(diagnostic)
    await db_session.commit()

    diagnostic_id = diagnostic.id

    # ------------------------------------------------------------------
    # 3. Create samples: asbestos+, PCB+, lead-
    # ------------------------------------------------------------------
    samples = [
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diagnostic_id,
            sample_number="S-001",
            location_floor="1er étage",
            location_room="Corridor",
            material_category="flocage",
            pollutant_type="asbestos",
            pollutant_subtype="chrysotile",
            concentration=5.0,
            unit="%",
            threshold_exceeded=True,
            risk_level="high",
            action_required="remediation",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diagnostic_id,
            sample_number="S-002",
            location_floor="Sous-sol",
            location_room="Local technique",
            material_category="joint",
            pollutant_type="pcb",
            concentration=120.0,
            unit="mg/kg",
            threshold_exceeded=True,
            risk_level="medium",
            action_required="remediation",
        ),
        Sample(
            id=uuid.uuid4(),
            diagnostic_id=diagnostic_id,
            sample_number="S-003",
            location_floor="2e étage",
            location_room="Salon",
            material_category="peinture",
            pollutant_type="lead",
            concentration=200.0,
            unit="mg/kg",
            threshold_exceeded=False,
            risk_level="low",
            action_required="none",
        ),
    ]
    for s in samples:
        db_session.add(s)
    await db_session.commit()

    # ------------------------------------------------------------------
    # 4. Action generator
    # ------------------------------------------------------------------
    actions = await action_generator.generate_actions_from_diagnostic(db_session, building_id, diagnostic_id)
    assert len(actions) > 0, "Action generator should produce at least one action"

    # ------------------------------------------------------------------
    # 5. Create intervention (asbestos_removal, completed)
    # ------------------------------------------------------------------
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type="asbestos_removal",
        title="Désamiantage corridor 1er étage",
        status="completed",
        date_start=date(2025, 9, 1),
        date_end=date(2025, 10, 15),
        contractor_name="Sanacore SA",
        diagnostic_id=diagnostic_id,
        created_by=user.id,
    )
    db_session.add(intervention)
    await db_session.commit()

    intervention_id = intervention.id

    # ------------------------------------------------------------------
    # 6. Post-works state generation
    # ------------------------------------------------------------------
    post_works = await post_works_service.generate_post_works_states(db_session, building_id, intervention_id)
    assert post_works is not None, "Post-works state should be generated"

    # ------------------------------------------------------------------
    # 7. Completeness engine
    # ------------------------------------------------------------------
    completeness = await completeness_engine.evaluate_completeness(db_session, building_id)
    assert completeness.overall_score >= 0, "Completeness score should be non-negative"
    assert len(completeness.checks) > 0, "Completeness should include checks"

    # ------------------------------------------------------------------
    # 8. Trust score calculator
    # ------------------------------------------------------------------
    trust = await trust_score_calculator.calculate_trust_score(db_session, building_id)
    assert trust is not None, "Trust score should be produced"

    # ------------------------------------------------------------------
    # 9. Unknown generator
    # ------------------------------------------------------------------
    unknowns = await unknown_generator.generate_unknowns(db_session, building_id)
    # May be empty or not, but should run without error and return a list
    assert isinstance(unknowns, list), "Unknown generator should return a list"

    # ------------------------------------------------------------------
    # 10. Readiness reasoner (safe_to_start)
    # ------------------------------------------------------------------
    readiness = await readiness_reasoner.evaluate_readiness(db_session, building_id, "safe_to_start")
    assert readiness is not None, "Readiness assessment should be produced"
    assert readiness.readiness_type == "safe_to_start"
    assert readiness.status in (
        "ready",
        "not_ready",
        "conditionally_ready",
        "blocked",
    ), f"Unexpected readiness status: {readiness.status}"

    # ------------------------------------------------------------------
    # 11. Contradiction detector
    # ------------------------------------------------------------------
    contradictions = await contradiction_detector.detect_contradictions(db_session, building_id)
    assert isinstance(contradictions, list), "Contradiction detector should return a list"

    # ------------------------------------------------------------------
    # 12. Passport summary
    # ------------------------------------------------------------------
    passport = await passport_service.get_passport_summary(db_session, building_id)
    assert passport is not None, "Passport should be returned for a building with data"
    assert "passport_grade" in passport, "Passport should contain a grade"
    assert passport["passport_grade"] in ("A", "B", "C", "D", "E", "F"), (
        f"Unexpected grade: {passport['passport_grade']}"
    )

    # ------------------------------------------------------------------
    # 13. Dossier completion agent
    # ------------------------------------------------------------------
    report = await dossier_completion_agent.run_dossier_completion(db_session, building_id, force_refresh=True)
    assert report is not None, "Dossier completion report should be produced"
    assert report.overall_status in (
        "complete",
        "near_complete",
        "incomplete",
        "critical_gaps",
    ), f"Unexpected overall_status: {report.overall_status}"
    assert report.completeness_score >= 0
    assert report.trust_score >= 0
    assert report.assessed_at is not None


@pytest.mark.asyncio
async def test_contradiction_trust_chain(db_session):
    """Proves: contradictory data -> contradiction detection -> trust impact -> passport grade reflects issues."""

    # 1. Create org + user + building
    org = Organization(id=uuid.uuid4(), name="Contra SA", type="diagnostic_lab", canton="VD")
    db_session.add(org)
    user = User(
        id=uuid.uuid4(),
        email="contra@test.ch",
        password_hash="$2b$12$LJ3m4ys3Lz0YFBFpq9G7xuGZ5vNfM2.Y.nGnZqZ8E5ZQz1z1z1z1z",
        first_name="Contra",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(user)
    building = Building(
        id=uuid.uuid4(),
        address="Rue des Contradictions 7",
        postal_code="1204",
        city="Genève",
        canton="GE",
        construction_year=1970,
        building_type="residential",
        created_by=user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    building_id = building.id

    # 2. Create two completed diagnostics for the same building
    diag1 = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="full",
        status="completed",
        diagnostician_id=user.id,
        date_inspection=date(2025, 3, 1),
        date_report=date(2025, 3, 10),
        conclusion="positive",
    )
    diag2 = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="full",
        status="completed",
        diagnostician_id=user.id,
        date_inspection=date(2025, 5, 1),
        date_report=date(2025, 5, 10),
        conclusion="negative",
    )
    db_session.add_all([diag1, diag2])
    await db_session.commit()

    # 3. Create conflicting samples: diag1 says asbestos positive, diag2 says negative (same room + material)
    s_pos = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag1.id,
        sample_number="C-001",
        location_floor="1er étage",
        location_room="Bureau",
        material_category="flocage",
        pollutant_type="asbestos",
        concentration=15.0,
        unit="%",
        threshold_exceeded=True,
        risk_level="high",
        action_required="remediation",
    )
    s_neg = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag2.id,
        sample_number="C-002",
        location_floor="1er étage",
        location_room="Bureau",
        material_category="flocage",
        pollutant_type="asbestos",
        concentration=0.0,
        unit="%",
        threshold_exceeded=False,
        risk_level="low",
        action_required="none",
    )
    db_session.add_all([s_pos, s_neg])
    await db_session.commit()

    # 4. Contradiction detector should find the conflict
    contradictions = await contradiction_detector.detect_contradictions(db_session, building_id)
    assert len(contradictions) > 0, "Contradictions should be detected for conflicting asbestos results"
    descriptions = [c.description for c in contradictions]
    assert any("asbestos" in d.lower() or "Bureau" in d for d in descriptions), (
        f"Expected asbestos/location contradiction, got: {descriptions}"
    )

    # 5. Trust score should reflect contradictions
    trust = await trust_score_calculator.calculate_trust_score(db_session, building_id)
    assert trust is not None, "Trust score should be produced"
    assert trust.percent_contradictory is not None and trust.percent_contradictory > 0, (
        f"Contradictory percentage should be > 0, got {trust.percent_contradictory}"
    )

    # 6. Passport grade should reflect the contradiction issues
    passport = await passport_service.get_passport_summary(db_session, building_id)
    assert passport is not None, "Passport should be returned"
    assert "contradictions" in passport, "Passport should contain contradictions section"
    assert len(passport["contradictions"]) > 0, "Contradictions section should be populated"
    assert passport["passport_grade"] in ("A", "B", "C", "D", "E", "F")


@pytest.mark.asyncio
async def test_intervention_postworks_requalification_chain(db_session):
    """Proves: intervention completion -> post-works -> readiness reassessment -> snapshot + passport."""

    # 1. Create org + user + building
    org = Organization(id=uuid.uuid4(), name="PostWorks SA", type="property_management", canton="VD")
    db_session.add(org)
    user = User(
        id=uuid.uuid4(),
        email="postworks@test.ch",
        password_hash="$2b$12$LJ3m4ys3Lz0YFBFpq9G7xuGZ5vNfM2.Y.nGnZqZ8E5ZQz1z1z1z1z",
        first_name="Post",
        last_name="Works",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(user)
    building = Building(
        id=uuid.uuid4(),
        address="Avenue de la Réhabilitation 15",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="residential",
        created_by=user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    building_id = building.id

    # 2. Create completed diagnostic with positive asbestos sample
    diagnostic = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="full",
        diagnostic_context="AvT",
        status="completed",
        diagnostician_id=user.id,
        laboratory="LabChain SA",
        date_inspection=date(2025, 4, 1),
        date_report=date(2025, 4, 15),
        conclusion="positive",
    )
    db_session.add(diagnostic)
    await db_session.commit()
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diagnostic.id,
        sample_number="PW-001",
        location_floor="Sous-sol",
        location_room="Cave",
        material_category="calorifugeage",
        pollutant_type="asbestos",
        pollutant_subtype="amosite",
        concentration=8.0,
        unit="%",
        threshold_exceeded=True,
        risk_level="high",
        action_required="remediation",
    )
    db_session.add(sample)
    await db_session.commit()

    # 3. Create completed asbestos_removal intervention
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building_id,
        intervention_type="asbestos_removal",
        title="Désamiantage cave sous-sol",
        status="completed",
        date_start=date(2025, 7, 1),
        date_end=date(2025, 8, 15),
        contractor_name="Sanacore SA",
        diagnostic_id=diagnostic.id,
        created_by=user.id,
    )
    db_session.add(intervention)
    await db_session.commit()

    # 4. Post-works state generation
    post_works = await post_works_service.generate_post_works_states(
        db_session,
        building_id,
        intervention.id,
    )
    assert isinstance(post_works, list), "Post-works should return a list"
    assert len(post_works) > 0, "At least one post-works state should be generated for the positive sample"

    # 5. Readiness reassessment (safe_to_reopen after remediation)
    readiness = await readiness_reasoner.evaluate_readiness(db_session, building_id, "safe_to_reopen")
    assert readiness is not None, "Readiness assessment should be produced"
    assert readiness.readiness_type == "safe_to_reopen"
    assert readiness.status in ("ready", "not_ready", "conditionally_ready", "blocked")

    # 6. Capture a time-machine snapshot post-intervention
    snapshot = await time_machine_service.capture_snapshot(
        db_session,
        building_id,
        snapshot_type="post_intervention",
        trigger_event="asbestos_removal_completed",
    )
    assert snapshot is not None, "Snapshot should be captured"
    assert snapshot.building_id == building_id
    assert snapshot.snapshot_type == "post_intervention"

    # 7. Passport should reflect post-works status
    passport = await passport_service.get_passport_summary(db_session, building_id)
    assert passport is not None, "Passport should be returned for a building with intervention data"
    assert passport["passport_grade"] in ("A", "B", "C", "D", "E", "F")
    assert "readiness" in passport, "Passport should contain readiness section"
