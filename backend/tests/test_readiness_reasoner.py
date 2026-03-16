"""Tests for the Readiness Reasoner service."""

import uuid
from datetime import date, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.readiness import PreworkTrigger, ReadinessAssessmentRead, _derive_prework_triggers
from app.services.readiness_reasoner import (
    READINESS_TYPES,
    evaluate_all_readiness,
    evaluate_readiness,
    generate_prework_triggers,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_building(db_session, admin_user, *, construction_year=1965, **kwargs):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        **kwargs,
    )
    db_session.add(building)
    return building


def _make_diagnostic(db_session, building, *, status="completed", context="AvT", **kwargs):
    defaults = {
        "date_inspection": date(2024, 1, 15),
    }
    defaults.update(kwargs)
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="full",
        diagnostic_context=context,
        status=status,
        **defaults,
    )
    db_session.add(diag)
    return diag


def _make_sample(
    db_session,
    diag,
    *,
    pollutant_type="asbestos",
    concentration=5.0,
    unit="percent_weight",
    **kwargs,
):
    defaults = {
        "risk_level": "high",
        "threshold_exceeded": True,
        "cfst_work_category": "medium",
        "action_required": "remove_planned",
        "waste_disposal_type": "type_e",
    }
    defaults.update(kwargs)
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number=f"S-{uuid.uuid4().hex[:6]}",
        pollutant_type=pollutant_type,
        concentration=concentration,
        unit=unit,
        **defaults,
    )
    db_session.add(sample)
    return sample


def _make_document(db_session, building, *, document_type="diagnostic_report", **kwargs):
    doc = Document(
        id=uuid.uuid4(),
        building_id=building.id,
        file_path=f"/docs/{uuid.uuid4().hex}.pdf",
        file_name="report.pdf",
        document_type=document_type,
        **kwargs,
    )
    db_session.add(doc)
    return doc


def _make_action(db_session, building, *, priority="medium", status="open", **kwargs):
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Test action",
        priority=priority,
        status=status,
        **kwargs,
    )
    db_session.add(action)
    return action


def _make_intervention(db_session, building, *, intervention_type="removal", status="completed", **kwargs):
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=building.id,
        intervention_type=intervention_type,
        title="Test intervention",
        status=status,
        **kwargs,
    )
    db_session.add(intervention)
    return intervention


def _make_zone(db_session, building, *, zone_type="floor", name="Ground floor", **kwargs):
    zone = Zone(
        id=uuid.uuid4(),
        building_id=building.id,
        zone_type=zone_type,
        name=name,
        **kwargs,
    )
    db_session.add(zone)
    return zone


async def _create_full_building_data(db_session, admin_user):
    """Create a building with all data needed for safe_to_start: ready."""
    building = _make_building(db_session, admin_user)
    diag = _make_diagnostic(
        db_session,
        building,
        suva_notification_required=True,
        suva_notification_date=date(2024, 2, 1),
    )
    # All 5 pollutants
    _make_sample(db_session, diag, pollutant_type="asbestos")
    _make_sample(
        db_session,
        diag,
        pollutant_type="pcb",
        concentration=100.0,
        unit="mg_per_kg",
        threshold_exceeded=False,
        risk_level="low",
        cfst_work_category=None,
        action_required="none",
    )
    _make_sample(
        db_session,
        diag,
        pollutant_type="lead",
        concentration=200.0,
        unit="mg_per_kg",
        threshold_exceeded=False,
        risk_level="low",
        cfst_work_category=None,
        action_required="none",
    )
    _make_sample(
        db_session,
        diag,
        pollutant_type="hap",
        concentration=50.0,
        unit="mg_per_kg",
        threshold_exceeded=False,
        risk_level="low",
        cfst_work_category=None,
        action_required="none",
    )
    _make_sample(
        db_session,
        diag,
        pollutant_type="radon",
        concentration=100.0,
        unit="bq_per_m3",
        threshold_exceeded=False,
        risk_level="low",
        cfst_work_category=None,
        action_required="none",
    )
    _make_document(db_session, building, document_type="diagnostic_report")
    await db_session.commit()
    return building, diag


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSafeToStart:
    """Tests for safe_to_start readiness type."""

    async def test_ready_with_complete_data(self, db_session, admin_user):
        """Building with all requirements met should be ready."""
        building, _ = await _create_full_building_data(db_session, admin_user)

        result = await evaluate_readiness(db_session, building.id, "safe_to_start")

        assert result.status == "ready"
        assert result.score == 1.0
        assert result.readiness_type == "safe_to_start"
        assert result.building_id == building.id
        assert result.blockers_json == []
        assert len(result.checks_json) >= 7

    async def test_blocked_missing_diagnostic(self, db_session, admin_user):
        """Building with no diagnostic should be blocked."""
        building = _make_building(db_session, admin_user)
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_start")

        assert result.status == "blocked"
        assert result.score < 1.0
        assert len(result.blockers_json) > 0
        blocker_messages = [b["message"] for b in result.blockers_json]
        assert any("diagnostic" in m.lower() for m in blocker_messages)

    async def test_blocked_open_critical_actions(self, db_session, admin_user):
        """Building with open critical actions should be blocked."""
        building, _ = await _create_full_building_data(db_session, admin_user)
        _make_action(db_session, building, priority="critical", status="open")
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_start")

        assert result.status == "blocked"
        blocker_messages = [b["message"] for b in result.blockers_json]
        assert any("critical" in m.lower() for m in blocker_messages)

    async def test_blocked_missing_pollutant(self, db_session, admin_user):
        """Building with missing pollutant evaluation should be blocked."""
        building = _make_building(db_session, admin_user)
        diag = _make_diagnostic(db_session, building)
        # Only asbestos, missing 4 others
        _make_sample(
            db_session,
            diag,
            pollutant_type="asbestos",
            threshold_exceeded=False,
            risk_level="low",
            cfst_work_category=None,
            action_required="none",
        )
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_start")

        assert result.status == "blocked"
        blocker_messages = [b["message"] for b in result.blockers_json]
        assert any("pollutant" in m.lower() for m in blocker_messages)

    async def test_blocked_missing_suva_notification(self, db_session, admin_user):
        """Positive asbestos without SUVA notification should be blocked."""
        building = _make_building(db_session, admin_user)
        diag = _make_diagnostic(
            db_session,
            building,
            suva_notification_required=True,
            suva_notification_date=None,  # Not notified
        )
        for pt in ("asbestos", "pcb", "lead", "hap", "radon"):
            _make_sample(
                db_session,
                diag,
                pollutant_type=pt,
                threshold_exceeded=(pt == "asbestos"),
                risk_level="high" if pt == "asbestos" else "low",
                cfst_work_category="medium" if pt == "asbestos" else None,
                action_required="remove_planned" if pt == "asbestos" else "none",
            )
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_start")

        assert result.status == "blocked"
        blocker_messages = [b["message"] for b in result.blockers_json]
        assert any("suva" in m.lower() for m in blocker_messages)

    async def test_conditional_without_report(self, db_session, admin_user):
        """Building ready except for diagnostic report should be conditional."""
        building = _make_building(db_session, admin_user)
        diag = _make_diagnostic(db_session, building)
        # All pollutants, none positive
        for pt in ("asbestos", "pcb", "lead", "hap", "radon"):
            _make_sample(
                db_session,
                diag,
                pollutant_type=pt,
                threshold_exceeded=False,
                risk_level="low",
                cfst_work_category=None,
                action_required="none",
            )
        # No document uploaded
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_start")

        assert result.status == "conditional"
        assert len(result.conditions_json) > 0

    async def test_upsert_idempotent(self, db_session, admin_user):
        """Evaluating twice for same building+type should update, not duplicate."""
        building, _ = await _create_full_building_data(db_session, admin_user)

        result1 = await evaluate_readiness(db_session, building.id, "safe_to_start")
        result2 = await evaluate_readiness(db_session, building.id, "safe_to_start")

        assert result1.id == result2.id  # Same record updated


@pytest.mark.asyncio
class TestSafeToTender:
    """Tests for safe_to_tender readiness type."""

    async def test_ready_with_complete_data(self, db_session, admin_user):
        """Building with report, actions, and zones should be ready."""
        building = _make_building(db_session, admin_user)
        _make_document(db_session, building, document_type="diagnostic_report")
        _make_action(db_session, building, priority="medium", status="open")
        _make_zone(db_session, building)
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_tender")

        assert result.status == "ready"
        assert result.score == 1.0

    async def test_blocked_missing_report(self, db_session, admin_user):
        """Building without diagnostic report should be blocked for tender."""
        building = _make_building(db_session, admin_user)
        _make_action(db_session, building, priority="medium", status="open")
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_tender")

        assert result.status == "blocked"
        blocker_messages = [b["message"] for b in result.blockers_json]
        assert any("report" in m.lower() for m in blocker_messages)


@pytest.mark.asyncio
class TestSafeToReopen:
    """Tests for safe_to_reopen readiness type."""

    async def test_blocked_incomplete_interventions(self, db_session, admin_user):
        """Building with planned interventions should be blocked for reopen."""
        building = _make_building(db_session, admin_user)
        _make_intervention(db_session, building, status="planned")
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_reopen")

        assert result.status == "blocked"
        blocker_messages = [b["message"] for b in result.blockers_json]
        assert any("intervention" in m.lower() for m in blocker_messages)

    async def test_ready_all_interventions_completed(self, db_session, admin_user):
        """Building with all interventions completed and no critical risk should be ready."""
        building = _make_building(db_session, admin_user)
        _make_intervention(db_session, building, intervention_type="encapsulation", status="completed")
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_reopen")

        # Should be conditional (missing post-works inspection) or ready
        assert result.status in ("ready", "conditional")
        assert len(result.blockers_json) == 0

    async def test_blocked_missing_air_clearance(self, db_session, admin_user):
        """Asbestos removal without air clearance should be blocked."""
        building = _make_building(db_session, admin_user)
        _make_intervention(
            db_session,
            building,
            intervention_type="asbestos_removal",
            status="completed",
        )
        # No air clearance document
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_reopen")

        assert result.status == "blocked"
        blocker_messages = [b["message"] for b in result.blockers_json]
        assert any("clearance" in m.lower() for m in blocker_messages)


@pytest.mark.asyncio
class TestSafeToRequalify:
    """Tests for safe_to_requalify readiness type."""

    async def test_old_diagnostic_triggers_condition(self, db_session, admin_user):
        """Diagnostic older than validity period should trigger requalification."""
        building = _make_building(db_session, admin_user)
        old_date = date.today() - timedelta(days=6 * 365)
        _make_diagnostic(db_session, building, date_inspection=old_date)
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_requalify")

        assert result.status == "conditional"
        assert len(result.conditions_json) > 0
        condition_messages = [c["message"] for c in result.conditions_json]
        assert any("requalification" in m.lower() for m in condition_messages)

    async def test_recent_diagnostic_is_fine(self, db_session, admin_user):
        """Recent diagnostic should not trigger requalification."""
        building = _make_building(db_session, admin_user)
        recent_date = date.today() - timedelta(days=365)
        _make_diagnostic(db_session, building, date_inspection=recent_date)
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_requalify")

        assert result.status == "ready"

    async def test_building_modifications_trigger_condition(self, db_session, admin_user):
        """Significant building modifications should trigger requalification."""
        building = _make_building(db_session, admin_user)
        recent_date = date.today() - timedelta(days=365)
        _make_diagnostic(db_session, building, date_inspection=recent_date)
        _make_intervention(
            db_session,
            building,
            intervention_type="renovation",
            status="completed",
        )
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_requalify")

        assert result.status == "conditional"
        condition_messages = [c["message"] for c in result.conditions_json]
        assert any("modification" in m.lower() for m in condition_messages)


@pytest.mark.asyncio
class TestEvaluateAll:
    """Tests for evaluate_all_readiness."""

    async def test_returns_all_four_types(self, db_session, admin_user):
        """evaluate_all_readiness should return assessments for all 4 types."""
        building = _make_building(db_session, admin_user)
        await db_session.commit()

        results = await evaluate_all_readiness(db_session, building.id)

        assert len(results) == 4
        types_returned = {r.readiness_type for r in results}
        assert types_returned == set(READINESS_TYPES)

    async def test_assessed_by_propagated(self, db_session, admin_user):
        """assessed_by_id should be set on all assessments."""
        building = _make_building(db_session, admin_user)
        await db_session.commit()

        results = await evaluate_all_readiness(db_session, building.id, assessed_by_id=admin_user.id)

        for r in results:
            assert r.assessed_by == admin_user.id


@pytest.mark.asyncio
class TestEdgeCases:
    """Edge case tests."""

    async def test_unknown_readiness_type_raises(self, db_session, admin_user):
        """Unknown readiness_type should raise ValueError."""
        building = _make_building(db_session, admin_user)
        await db_session.commit()

        with pytest.raises(ValueError, match="Unknown readiness_type"):
            await evaluate_readiness(db_session, building.id, "safe_to_fly")

    async def test_nonexistent_building_raises(self, db_session):
        """Non-existent building should raise ValueError."""
        fake_id = uuid.uuid4()

        with pytest.raises(ValueError, match="not found"):
            await evaluate_readiness(db_session, fake_id, "safe_to_start")

    async def test_score_computation(self, db_session, admin_user):
        """Score should be between 0 and 1 and reflect check results."""
        building = _make_building(db_session, admin_user)
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_start")

        assert 0.0 <= result.score <= 1.0
        # With no data, most checks fail so score should be low
        assert result.score < 0.5


@pytest.mark.asyncio
class TestPreworkTriggers:
    """Tests for prework trigger derivation from readiness checks."""

    async def test_triggers_generated_for_missing_pollutants(self, db_session, admin_user):
        """Missing pollutant evaluations should generate per-pollutant prework triggers."""
        building = _make_building(db_session, admin_user)
        diag = _make_diagnostic(db_session, building)
        # Only asbestos — missing pcb, lead, hap, radon
        _make_sample(
            db_session,
            diag,
            pollutant_type="asbestos",
            threshold_exceeded=False,
            risk_level="low",
            cfst_work_category=None,
            action_required="none",
        )
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_start")
        read = ReadinessAssessmentRead.model_validate(result)

        assert len(read.prework_triggers) > 0
        trigger_types = {t.trigger_type for t in read.prework_triggers}
        # Should have triggers for the 4 missing pollutants
        assert "pcb_check" in trigger_types
        assert "lead_check" in trigger_types
        assert "hap_check" in trigger_types
        assert "radon_check" in trigger_types

    async def test_no_triggers_when_all_pass(self, db_session, admin_user):
        """Building with all checks passing should have empty prework triggers."""
        building, _ = await _create_full_building_data(db_session, admin_user)

        result = await evaluate_readiness(db_session, building.id, "safe_to_start")
        read = ReadinessAssessmentRead.model_validate(result)

        assert read.prework_triggers == []

    async def test_triggers_for_suva_notification(self, db_session, admin_user):
        """Missing SUVA notification for asbestos should generate amiante_check trigger."""
        building = _make_building(db_session, admin_user)
        diag = _make_diagnostic(
            db_session,
            building,
            suva_notification_required=True,
            suva_notification_date=None,
        )
        for pt in ("asbestos", "pcb", "lead", "hap", "radon"):
            _make_sample(
                db_session,
                diag,
                pollutant_type=pt,
                threshold_exceeded=(pt == "asbestos"),
                risk_level="high" if pt == "asbestos" else "low",
                cfst_work_category="medium" if pt == "asbestos" else None,
                action_required="remove_planned" if pt == "asbestos" else "none",
            )
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_start")
        read = ReadinessAssessmentRead.model_validate(result)

        trigger_types = {t.trigger_type for t in read.prework_triggers}
        assert "amiante_check" in trigger_types
        # Verify source_check reference
        amiante_triggers = [t for t in read.prework_triggers if t.trigger_type == "amiante_check"]
        assert any(t.source_check == "suva_notification" for t in amiante_triggers)

    async def test_backward_compatibility_old_responses_still_valid(self, db_session, admin_user):
        """ReadinessAssessmentRead should still work with all existing fields."""
        building, _ = await _create_full_building_data(db_session, admin_user)
        result = await evaluate_readiness(db_session, building.id, "safe_to_start")

        read = ReadinessAssessmentRead.model_validate(result)

        # All original fields still present and correct
        assert read.id == result.id
        assert read.building_id == result.building_id
        assert read.readiness_type == "safe_to_start"
        assert read.status == "ready"
        assert read.score == 1.0
        assert isinstance(read.checks_json, list)
        assert isinstance(read.blockers_json, list)
        assert isinstance(read.conditions_json, list)
        # New field has correct default
        assert isinstance(read.prework_triggers, list)

    async def test_triggers_have_correct_schema(self, db_session, admin_user):
        """Each prework trigger should have all required fields with valid values."""
        building = _make_building(db_session, admin_user)
        # No diagnostic at all → multiple failures
        await db_session.commit()

        result = await evaluate_readiness(db_session, building.id, "safe_to_start")
        read = ReadinessAssessmentRead.model_validate(result)

        for trigger in read.prework_triggers:
            assert isinstance(trigger, PreworkTrigger)
            assert trigger.trigger_type in (
                "amiante_check",
                "pcb_check",
                "lead_check",
                "hap_check",
                "radon_check",
            )
            assert trigger.urgency in ("low", "medium", "high")
            assert len(trigger.reason) > 0
            assert len(trigger.source_check) > 0


# ---------------------------------------------------------------------------
# Standalone prework trigger unit tests (sync — no DB needed)
# ---------------------------------------------------------------------------


def test_generate_prework_triggers_service_function():
    """Service-level generate_prework_triggers should match schema derivation."""
    checks = [
        {
            "id": "all_pollutants_evaluated",
            "label": "All pollutants evaluated",
            "status": "fail",
            "detail": "Missing: pcb, lead",
            "required": True,
        },
    ]
    triggers = generate_prework_triggers(checks)
    assert len(triggers) >= 2
    types = {t["trigger_type"] for t in triggers}
    assert "pcb_check" in types
    assert "lead_check" in types


def test_derive_prework_triggers_empty_checks():
    """Empty or None checks should produce no triggers."""
    assert _derive_prework_triggers(None) == []
    assert _derive_prework_triggers([]) == []


def test_derive_prework_triggers_all_passing():
    """All-passing checks should produce no triggers."""
    checks = [
        {"id": "completed_diagnostic", "status": "pass", "required": True},
        {"id": "all_pollutants_evaluated", "status": "pass", "required": True},
    ]
    assert _derive_prework_triggers(checks) == []
