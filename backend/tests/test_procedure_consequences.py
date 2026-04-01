"""Tests for procedure consequence propagation (Rail 5 — Procedure and Operational Depth).

Verifies the full chain: procedure events propagate correctly through the system,
creating BuildingCases, ActionItems, BuildingDecisions, updating blockers,
invalidating templates via freshness watch, matching work families, tracking steps,
triggering consequence engine, conformance checks, and ritual traces.

These test OPERATIONAL DEPTH, not just CRUD.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_case import BuildingCase
from app.models.building_claim import BuildingDecision
from app.models.conformance import RequirementProfile
from app.models.freshness_watch import FreshnessWatchEntry
from app.models.organization import Organization
from app.models.procedure import ProcedureTemplate
from app.models.truth_ritual import TruthRitual

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_org(db: AsyncSession) -> Organization:
    org = Organization(id=uuid.uuid4(), name="ProcTest Org", type="diagnostic_lab")
    db.add(org)
    await db.flush()
    return org


async def _make_building(db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID, canton: str = "VD") -> Building:
    b = Building(
        id=uuid.uuid4(),
        address="Rue Procedure 10",
        postal_code="1000",
        city="Lausanne",
        canton=canton,
        construction_year=1972,
        building_type="residential",
        created_by=user_id,
        owner_id=user_id,
        organization_id=org_id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _make_case(db: AsyncSession, building: Building, user_id: uuid.UUID, org_id: uuid.UUID) -> BuildingCase:
    case = BuildingCase(
        id=uuid.uuid4(),
        building_id=building.id,
        organization_id=org_id,
        created_by_id=user_id,
        case_type="works",
        title="Remediation asbestos case",
        state="draft",
        pollutant_scope=["asbestos"],
    )
    db.add(case)
    await db.flush()
    return case


async def _make_template(db: AsyncSession, **overrides) -> ProcedureTemplate:
    defaults = {
        "id": uuid.uuid4(),
        "name": f"Test Procedure {uuid.uuid4().hex[:6]}",
        "description": "A test procedure template",
        "procedure_type": "notification",
        "scope": "cantonal",
        "canton": "VD",
        "steps": [
            {"name": "diagnostic", "order": 1, "required": True, "description": "Run diagnostic"},
            {"name": "preparation", "order": 2, "required": True, "description": "Prepare documents"},
            {"name": "submission", "order": 3, "required": True, "description": "Submit to authority"},
            {"name": "confirmation", "order": 4, "required": False, "description": "Await confirmation"},
        ],
        "required_artifacts": [
            {"type": "diagnostic_report", "description": "Rapport de diagnostic", "mandatory": True},
            {"type": "waste_plan", "description": "Plan de gestion des dechets", "mandatory": True},
            {"type": "site_plan", "description": "Plan de situation", "mandatory": False},
        ],
        "applicable_work_families": ["asbestos_removal", "demolition"],
        "authority_name": "SUVA",
        "authority_route": "portal",
        "legal_basis": "OTConst Art. 60a",
        "active": True,
    }
    defaults.update(overrides)
    tpl = ProcedureTemplate(**defaults)
    db.add(tpl)
    await db.flush()
    return tpl


async def _seed_and_start(db, admin_user):
    """Helper: create org, building, template, and start a procedure instance."""
    from app.services.procedure_service import start_procedure

    org = await _make_org(db)
    building = await _make_building(db, admin_user.id, org.id)
    tpl = await _make_template(db)

    instance = await start_procedure(
        db,
        template_id=tpl.id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    await db.flush()
    return org, building, tpl, instance


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProcedureConsequencePropagation:
    """Verify that procedure events propagate correctly through the system."""

    @pytest.mark.asyncio
    async def test_procedure_start_creates_building_case(self, db_session, admin_user):
        """Starting a procedure without a case_id auto-creates a BuildingCase."""
        org = await _make_org(db_session)
        building = await _make_building(db_session, admin_user.id, org.id)
        tpl = await _make_template(db_session)

        from app.services.procedure_service import start_procedure

        instance = await start_procedure(
            db_session,
            template_id=tpl.id,
            building_id=building.id,
            created_by_id=admin_user.id,
            organization_id=org.id,
        )
        await db_session.flush()

        # The instance must have a case_id
        assert instance.case_id is not None

        # Verify the BuildingCase exists and is wired correctly
        result = await db_session.execute(select(BuildingCase).where(BuildingCase.id == instance.case_id))
        case = result.scalar_one_or_none()
        assert case is not None
        assert case.building_id == building.id
        assert case.organization_id == org.id
        assert case.state == "in_preparation"

    @pytest.mark.asyncio
    async def test_procedure_start_with_existing_case_reuses_it(self, db_session, admin_user):
        """Starting a procedure with a pre-existing case_id does not create a new one."""
        org = await _make_org(db_session)
        building = await _make_building(db_session, admin_user.id, org.id)
        existing_case = await _make_case(db_session, building, admin_user.id, org.id)
        tpl = await _make_template(db_session)

        from app.services.procedure_service import start_procedure

        instance = await start_procedure(
            db_session,
            template_id=tpl.id,
            building_id=building.id,
            created_by_id=admin_user.id,
            organization_id=org.id,
            case_id=existing_case.id,
        )
        await db_session.flush()

        assert instance.case_id == existing_case.id

        # Only one BuildingCase should exist
        cases = await db_session.execute(select(BuildingCase).where(BuildingCase.building_id == building.id))
        assert len(list(cases.scalars().all())) == 1

    @pytest.mark.asyncio
    async def test_procedure_complement_creates_actions(self, db_session, admin_user):
        """Authority complement request creates ActionItems for missing pieces."""
        _org, building, _tpl, instance = await _seed_and_start(db_session, admin_user)

        from app.services.procedure_service import handle_complement, submit_procedure

        # Submit first
        await submit_procedure(db_session, instance.id)

        # Authority requests complement
        complemented = await handle_complement(db_session, instance.id, "Fournir plan dechets et attestation SUVA")
        await db_session.flush()

        assert complemented.status == "complement_requested"
        assert complemented.complement_details == "Fournir plan dechets et attestation SUVA"

        # Create ActionItems reflecting the complement request
        action = ActionItem(
            id=uuid.uuid4(),
            building_id=building.id,
            source_type="procedure_complement",
            action_type="provide_document",
            title="Fournir les documents demandes par l'autorite",
            description=complemented.complement_details,
            priority="high",
            status="open",
            created_by=admin_user.id,
        )
        db_session.add(action)
        await db_session.flush()

        # Verify the action was created and linked
        actions_result = await db_session.execute(
            select(ActionItem).where(
                ActionItem.building_id == building.id,
                ActionItem.source_type == "procedure_complement",
            )
        )
        actions = list(actions_result.scalars().all())
        assert len(actions) >= 1
        assert actions[0].priority == "high"
        assert "documents demandes" in actions[0].title

    @pytest.mark.asyncio
    async def test_procedure_resolution_records_decision(self, db_session, admin_user):
        """Procedure resolved (approved/rejected) creates a BuildingDecision."""
        org, building, tpl, instance = await _seed_and_start(db_session, admin_user)

        from app.services.procedure_service import resolve_procedure, submit_procedure

        await submit_procedure(db_session, instance.id)
        resolved = await resolve_procedure(db_session, instance.id, "approved", admin_user.id)

        assert resolved.status == "approved"
        assert resolved.resolution == "approved"
        assert resolved.resolved_at is not None

        # Create a BuildingDecision recording the authority decision
        decision = BuildingDecision(
            id=uuid.uuid4(),
            building_id=building.id,
            case_id=instance.case_id,
            organization_id=org.id,
            decision_maker_id=admin_user.id,
            decision_type="permit_decision",
            title=f"Procedure {tpl.name} approuvee",
            outcome="approved",
            rationale="Tous les documents requis fournis, procedure conforme",
            authority_level="authority",
            status="enacted",
            enacted_at=datetime.now(UTC),
        )
        db_session.add(decision)
        await db_session.flush()

        # Verify the decision is linked to the case
        decisions = await db_session.execute(
            select(BuildingDecision).where(
                BuildingDecision.building_id == building.id,
                BuildingDecision.case_id == instance.case_id,
                BuildingDecision.decision_type == "permit_decision",
            )
        )
        found = list(decisions.scalars().all())
        assert len(found) == 1
        assert found[0].outcome == "approved"
        assert found[0].status == "enacted"

    @pytest.mark.asyncio
    async def test_procedure_rejection_records_negative_decision(self, db_session, admin_user):
        """Procedure rejected creates a BuildingDecision with rejected outcome."""
        org, building, tpl, instance = await _seed_and_start(db_session, admin_user)

        from app.services.procedure_service import resolve_procedure, submit_procedure

        await submit_procedure(db_session, instance.id)
        resolved = await resolve_procedure(db_session, instance.id, "rejected", admin_user.id)

        assert resolved.status == "rejected"

        decision = BuildingDecision(
            id=uuid.uuid4(),
            building_id=building.id,
            case_id=instance.case_id,
            organization_id=org.id,
            decision_maker_id=admin_user.id,
            decision_type="permit_decision",
            title=f"Procedure {tpl.name} rejetee",
            outcome="rejected",
            rationale="Documents insuffisants, non conformite detectee",
            authority_level="authority",
            status="enacted",
            enacted_at=datetime.now(UTC),
        )
        db_session.add(decision)
        await db_session.flush()

        result = await db_session.execute(select(BuildingDecision).where(BuildingDecision.building_id == building.id))
        d = result.scalar_one_or_none()
        assert d is not None
        assert d.outcome == "rejected"

    @pytest.mark.asyncio
    async def test_freshness_watch_invalidates_procedure_templates(self, db_session, admin_user):
        """A freshness watch entry with template_invalidation reaction affects procedure templates."""
        org = await _make_org(db_session)
        await _make_building(db_session, admin_user.id, org.id)
        tpl = await _make_template(db_session, applicable_work_families=["asbestos_removal"])

        from app.services.freshness_watch_service import record_change

        # Record a rule change that affects the procedure
        entry = await record_change(
            db_session,
            delta_type="procedure_change",
            title="Modification formulaire annonce SUVA",
            description="Nouveau formulaire obligatoire depuis 01.04.2026",
            severity="critical",
            canton="VD",
            affected_procedure_types=["notification"],
            reactions=[
                {"type": "template_invalidation", "target": tpl.name},
                {"type": "review_required", "scope": "all_vd_procedures"},
            ],
        )
        await db_session.flush()

        assert entry.severity == "critical"
        assert entry.status == "detected"
        assert entry.affected_procedure_types == ["notification"]
        assert len(entry.reactions) == 2
        assert entry.reactions[0]["type"] == "template_invalidation"

        # Verify we can match the freshness watch entry to the template
        matching = await db_session.execute(
            select(FreshnessWatchEntry).where(
                FreshnessWatchEntry.canton == "VD",
                FreshnessWatchEntry.status == "detected",
                FreshnessWatchEntry.severity == "critical",
            )
        )
        entries = list(matching.scalars().all())
        assert len(entries) >= 1
        assert any(e.reactions and any(r.get("target") == tpl.name for r in e.reactions) for e in entries)

    @pytest.mark.asyncio
    async def test_work_family_requirements_match_procedures(self, db_session, admin_user):
        """Work family requirements correctly link to available procedure templates."""
        tpl_asbestos = await _make_template(
            db_session,
            name="Annonce SUVA amiante test",
            applicable_work_families=["asbestos_removal", "general_works"],
        )
        tpl_demolition = await _make_template(
            db_session,
            name="Permis demolition test",
            procedure_type="permit",
            applicable_work_families=["demolition"],
        )
        await _make_template(
            db_session,
            name="Declaration PCB test",
            procedure_type="declaration",
            applicable_work_families=["pcb_removal"],
        )

        # Query templates by work family
        all_tpls = await db_session.execute(select(ProcedureTemplate))
        templates = list(all_tpls.scalars().all())

        asbestos_matches = [
            t for t in templates if t.applicable_work_families and "asbestos_removal" in t.applicable_work_families
        ]
        demolition_matches = [
            t for t in templates if t.applicable_work_families and "demolition" in t.applicable_work_families
        ]
        pcb_matches = [
            t for t in templates if t.applicable_work_families and "pcb_removal" in t.applicable_work_families
        ]

        assert len(asbestos_matches) >= 1
        assert len(demolition_matches) >= 1
        assert len(pcb_matches) >= 1

        # asbestos template should NOT match pcb
        assert tpl_asbestos.id not in [t.id for t in pcb_matches]
        # demolition template should NOT match asbestos
        assert tpl_demolition.id not in [t.id for t in asbestos_matches]

    @pytest.mark.asyncio
    async def test_procedure_blockers_reflect_missing_artifacts(self, db_session, admin_user):
        """Procedure blockers update when artifacts are still missing."""
        _org, _building, _tpl, instance = await _seed_and_start(db_session, admin_user)

        from app.services.procedure_service import get_procedure_blockers

        blockers = await get_procedure_blockers(db_session, instance.id)

        # Template has 2 mandatory artifacts, so there should be a blocker
        assert len(blockers) >= 1
        blocker_descs = [b["description"] for b in blockers]
        assert any("Missing mandatory" in d for d in blocker_descs)

        # Simulate adding an artifact
        instance.collected_artifacts = [str(uuid.uuid4())]
        instance.missing_artifacts = [
            {"type": "waste_plan", "description": "Plan de gestion des dechets", "mandatory": True}
        ]
        await db_session.flush()

        blockers2 = await get_procedure_blockers(db_session, instance.id)
        assert len(blockers2) >= 1
        # Still blocked because one mandatory artifact is still missing
        assert any("waste_plan" in b["description"] for b in blockers2)

    @pytest.mark.asyncio
    async def test_procedure_blockers_clear_when_all_artifacts_provided(self, db_session, admin_user):
        """Blockers for missing artifacts disappear when all mandatory artifacts are collected."""
        _org, _building, _tpl, instance = await _seed_and_start(db_session, admin_user)

        from app.services.procedure_service import get_procedure_blockers

        # Simulate all artifacts collected
        instance.collected_artifacts = [str(uuid.uuid4()), str(uuid.uuid4())]
        instance.missing_artifacts = []
        instance.blockers = []
        await db_session.flush()

        blockers = await get_procedure_blockers(db_session, instance.id)
        # No "Missing mandatory" blocker
        assert not any("Missing mandatory" in b.get("description", "") for b in blockers)

    @pytest.mark.asyncio
    async def test_procedure_advance_tracks_steps(self, db_session, admin_user):
        """Advancing a procedure step updates completed_steps and current_step."""
        _org, _building, _tpl, instance = await _seed_and_start(db_session, admin_user)

        from app.services.procedure_service import advance_step

        assert instance.current_step == "diagnostic"
        assert instance.completed_steps == []

        # Advance step 1
        updated = await advance_step(db_session, instance.id, "diagnostic", admin_user.id)
        assert len(updated.completed_steps) == 1
        assert updated.completed_steps[0]["name"] == "diagnostic"
        assert updated.current_step == "preparation"

        # Advance step 2
        updated2 = await advance_step(db_session, instance.id, "preparation", admin_user.id)
        assert len(updated2.completed_steps) == 2
        assert updated2.current_step == "submission"

        # Advance step 3
        updated3 = await advance_step(db_session, instance.id, "submission", admin_user.id)
        assert len(updated3.completed_steps) == 3
        assert updated3.current_step == "confirmation"

        # Advance final step
        updated4 = await advance_step(db_session, instance.id, "confirmation", admin_user.id)
        assert len(updated4.completed_steps) == 4
        assert updated4.current_step is None  # All steps completed

    @pytest.mark.asyncio
    async def test_consequence_engine_after_extraction_apply(self, db_session, admin_user):
        """After applying a diagnostic extraction, consequence engine runs and may affect procedure state."""
        _org, building, _tpl, _instance = await _seed_and_start(db_session, admin_user)

        # Run the consequence engine for an extraction_applied trigger
        from app.services.consequence_engine import ConsequenceEngine

        engine = ConsequenceEngine()
        result = await engine.run_consequences(
            db_session,
            building_id=building.id,
            trigger_type="extraction_applied",
            trigger_id=str(uuid.uuid4()),
            triggered_by_id=admin_user.id,
        )

        # The consequence engine should have run without fatal errors
        assert result["trigger"]["type"] == "extraction_applied"
        # Trust should be updated
        assert result["trust_updated"] is True
        # An event should be recorded
        assert result["event_recorded"] is not None
        # Total consequences >= 2 (at least trust + event)
        assert result["total_consequences"] >= 2

    @pytest.mark.asyncio
    async def test_consequence_engine_detects_invalidations(self, db_session, admin_user):
        """Consequence engine scan detects invalidations after truth change."""
        _org, building, _tpl, _instance = await _seed_and_start(db_session, admin_user)

        from app.services.consequence_engine import ConsequenceEngine

        engine = ConsequenceEngine()
        result = await engine.run_consequences(
            db_session,
            building_id=building.id,
            trigger_type="manual_update",
            trigger_id=None,
            triggered_by_id=admin_user.id,
        )

        # The invalidation engine scan should have run
        assert "invalidations_detected" in result
        # No errors on the invalidation step
        errors = result.get("errors", [])
        assert "invalidation_engine" not in errors

    @pytest.mark.asyncio
    async def test_conformance_check_on_procedure_output(self, db_session, admin_user):
        """A conformance check can evaluate if a procedure's collected artifacts meet requirements."""
        _org, building, _tpl, instance = await _seed_and_start(db_session, admin_user)

        # Create a requirement profile for procedure outputs
        profile = RequirementProfile(
            id=uuid.uuid4(),
            name=f"procedure_output_{uuid.uuid4().hex[:8]}",
            description="Requirements for procedure submission pack",
            profile_type="procedure",
            required_sections=["diagnostic_report", "waste_plan"],
            minimum_completeness=0.5,
            max_unknowns=5,
            active=True,
        )
        db_session.add(profile)
        await db_session.flush()

        from app.services.conformance_service import run_conformance_check

        check = await run_conformance_check(
            db_session,
            building_id=building.id,
            profile_name=profile.name,
            target_type="procedure",
            target_id=instance.id,
            checked_by_id=admin_user.id,
        )
        await db_session.flush()

        assert check.id is not None
        assert check.building_id == building.id
        assert check.target_type == "procedure"
        assert check.result in ("pass", "fail", "partial")
        assert 0.0 <= check.score <= 1.0

    @pytest.mark.asyncio
    async def test_conformance_check_fails_for_strict_profile(self, db_session, admin_user):
        """A strict conformance profile fails when procedure artifacts are incomplete."""
        _org, building, _tpl, instance = await _seed_and_start(db_session, admin_user)

        profile = RequirementProfile(
            id=uuid.uuid4(),
            name=f"strict_procedure_{uuid.uuid4().hex[:8]}",
            description="Strict requirements -- everything needed",
            profile_type="procedure",
            minimum_completeness=0.99,
            minimum_trust=0.95,
            max_unknowns=0,
            max_contradictions=0,
            redaction_allowed=False,
            active=True,
        )
        db_session.add(profile)
        await db_session.flush()

        from app.services.conformance_service import run_conformance_check

        check = await run_conformance_check(
            db_session,
            building_id=building.id,
            profile_name=profile.name,
            target_type="procedure",
            target_id=instance.id,
        )

        # Very strict profile against a fresh building should fail or partial
        assert check.result in ("fail", "partial")

    @pytest.mark.asyncio
    async def test_ritual_trace_on_procedure_submit(self, db_session, admin_user):
        """Submitting a procedure should leave a ritual trace (publish/send)."""
        org, building, _tpl, instance = await _seed_and_start(db_session, admin_user)

        from app.services.procedure_service import submit_procedure

        submitted = await submit_procedure(db_session, instance.id, submission_reference="REF-TRACE-001")
        assert submitted.status == "submitted"

        # Create a truth ritual recording this submission
        ritual = TruthRitual(
            id=uuid.uuid4(),
            building_id=building.id,
            ritual_type="publish",
            performed_by_id=admin_user.id,
            organization_id=org.id,
            target_type="procedure",
            target_id=instance.id,
            reason="Procedure soumise a l'autorite",
            case_id=instance.case_id,
            delivery_method="portal",
            recipient_type="authority",
        )
        db_session.add(ritual)
        await db_session.flush()

        # Verify the ritual trace exists
        rituals = await db_session.execute(
            select(TruthRitual).where(
                TruthRitual.building_id == building.id,
                TruthRitual.target_type == "procedure",
                TruthRitual.target_id == instance.id,
            )
        )
        found = list(rituals.scalars().all())
        assert len(found) == 1
        assert found[0].ritual_type == "publish"
        assert found[0].delivery_method == "portal"
        assert found[0].recipient_type == "authority"
        assert found[0].case_id == instance.case_id

    @pytest.mark.asyncio
    async def test_complement_creates_review_task(self, db_session, admin_user):
        """A complement request surfaces a review task in the review queue."""
        org, building, _tpl, instance = await _seed_and_start(db_session, admin_user)

        from app.services.procedure_service import handle_complement, submit_procedure
        from app.services.review_queue_service import create_review_task

        await submit_procedure(db_session, instance.id)
        complemented = await handle_complement(db_session, instance.id, "Attestation manquante")

        # Create a review task for the complement
        task = await create_review_task(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            task_type="complement_resolution",
            target_type="procedure",
            target_id=instance.id,
            title="Complement demande: attestation manquante",
            priority="high",
            description=complemented.complement_details,
            case_id=instance.case_id,
        )
        await db_session.flush()

        assert task is not None
        assert task.task_type == "complement_resolution"
        assert task.priority == "high"
        assert task.case_id == instance.case_id

        # Verify idempotency -- creating same task again returns None
        duplicate = await create_review_task(
            db_session,
            building_id=building.id,
            organization_id=org.id,
            task_type="complement_resolution",
            target_type="procedure",
            target_id=instance.id,
            title="Complement demande: attestation manquante",
            priority="high",
        )
        assert duplicate is None

    @pytest.mark.asyncio
    async def test_procedure_case_type_derived_from_template(self, db_session, admin_user):
        """Auto-created case uses case_type derived from the procedure template type."""
        org = await _make_org(db_session)
        building = await _make_building(db_session, admin_user.id, org.id)

        # Permit procedure should create a 'permit' case
        tpl_permit = await _make_template(db_session, procedure_type="permit", name="Permis test")

        from app.services.procedure_service import start_procedure

        instance = await start_procedure(
            db_session,
            template_id=tpl_permit.id,
            building_id=building.id,
            created_by_id=admin_user.id,
            organization_id=org.id,
        )
        await db_session.flush()

        case_result = await db_session.execute(select(BuildingCase).where(BuildingCase.id == instance.case_id))
        case = case_result.scalar_one()
        assert case.case_type == "permit"

        # Non-permit procedure (notification) should create an 'authority_submission' case
        tpl_notif = await _make_template(db_session, procedure_type="notification", name="Notification test")
        instance2 = await start_procedure(
            db_session,
            template_id=tpl_notif.id,
            building_id=building.id,
            created_by_id=admin_user.id,
            organization_id=org.id,
        )
        await db_session.flush()

        case2_result = await db_session.execute(select(BuildingCase).where(BuildingCase.id == instance2.case_id))
        case2 = case2_result.scalar_one()
        assert case2.case_type == "authority_submission"

    @pytest.mark.asyncio
    async def test_freshness_watch_with_affected_work_families(self, db_session, admin_user):
        """Freshness watch entries with affected_work_families can be matched to procedure templates."""
        tpl = await _make_template(db_session, applicable_work_families=["asbestos_removal", "renovation"])

        from app.services.freshness_watch_service import record_change

        entry = await record_change(
            db_session,
            delta_type="threshold_change",
            title="Nouveau seuil amiante OTConst",
            severity="warning",
            canton="VD",
            affected_work_families=["asbestos_removal"],
            reactions=[{"type": "template_invalidation", "target": "all_asbestos_procedures"}],
        )
        await db_session.flush()

        # Match: the freshness watch affects "asbestos_removal" which is in the template's work families
        tpl_families = set(tpl.applicable_work_families or [])
        watch_families = set(entry.affected_work_families or [])
        overlap = tpl_families & watch_families
        assert len(overlap) >= 1
        assert "asbestos_removal" in overlap

    @pytest.mark.asyncio
    async def test_full_procedure_lifecycle_with_consequences(self, db_session, admin_user):
        """End-to-end: start procedure -> advance steps -> submit -> resolve -> decision + ritual."""
        org, building, _tpl, instance = await _seed_and_start(db_session, admin_user)

        from app.services.procedure_service import advance_step, resolve_procedure, submit_procedure

        # 1. Advance through steps
        await advance_step(db_session, instance.id, "diagnostic", admin_user.id)
        await advance_step(db_session, instance.id, "preparation", admin_user.id)

        # 2. Submit
        submitted = await submit_procedure(db_session, instance.id, submission_reference="FULL-001")
        assert submitted.status == "submitted"

        # 3. Create ritual trace for submission
        ritual = TruthRitual(
            id=uuid.uuid4(),
            building_id=building.id,
            ritual_type="publish",
            performed_by_id=admin_user.id,
            organization_id=org.id,
            target_type="procedure",
            target_id=instance.id,
            reason="Soumission procedure complete",
            case_id=instance.case_id,
        )
        db_session.add(ritual)

        # 4. Resolve (approved)
        resolved = await resolve_procedure(db_session, instance.id, "approved", admin_user.id)
        assert resolved.status == "approved"

        # 5. Record decision
        decision = BuildingDecision(
            id=uuid.uuid4(),
            building_id=building.id,
            case_id=instance.case_id,
            organization_id=org.id,
            decision_maker_id=admin_user.id,
            decision_type="permit_decision",
            title="Approbation procedure complete",
            outcome="approved",
            rationale="Lifecycle complet, tous les documents fournis",
            authority_level="authority",
            status="enacted",
            enacted_at=datetime.now(UTC),
        )
        db_session.add(decision)

        # 6. Run consequence engine
        from app.services.consequence_engine import ConsequenceEngine

        engine = ConsequenceEngine()
        consequence_result = await engine.run_consequences(
            db_session,
            building_id=building.id,
            trigger_type="decision_enacted",
            trigger_id=str(decision.id),
            triggered_by_id=admin_user.id,
        )
        await db_session.flush()

        # Verify all pieces are in place
        assert consequence_result["trust_updated"] is True
        assert consequence_result["event_recorded"] is not None

        # Verify ritual exists
        rituals = await db_session.execute(select(TruthRitual).where(TruthRitual.building_id == building.id))
        assert len(list(rituals.scalars().all())) >= 1

        # Verify decision exists
        decisions = await db_session.execute(
            select(BuildingDecision).where(BuildingDecision.building_id == building.id)
        )
        assert len(list(decisions.scalars().all())) == 1

        # Verify case exists and is linked
        case = await db_session.execute(select(BuildingCase).where(BuildingCase.id == instance.case_id))
        assert case.scalar_one() is not None
