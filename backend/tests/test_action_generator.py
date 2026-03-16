"""Tests for automatic action generation from diagnostic results."""

import uuid
from datetime import date

from app.constants import (
    ACTION_PRIORITY_CRITICAL,
    ACTION_PRIORITY_HIGH,
    ACTION_PRIORITY_LOW,
    ACTION_PRIORITY_MEDIUM,
    ACTION_SOURCE_DIAGNOSTIC,
    ACTION_TYPE_DOCUMENTATION,
    ACTION_TYPE_INVESTIGATION,
    ACTION_TYPE_NOTIFICATION,
    ACTION_TYPE_PROCUREMENT,
    ACTION_TYPE_REMEDIATION,
)
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.action_generator import generate_actions_from_diagnostic

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _make_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "diagnostic_context": "AvT",
        "status": "completed",
        "date_inspection": date(2025, 1, 15),
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return d


async def _make_sample(db, diagnostic_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic_id,
        "sample_number": "S-1",
        "pollutant_type": "asbestos",
        "concentration": 5.0,
        "unit": "percent_weight",
        "threshold_exceeded": True,
    }
    defaults.update(kwargs)
    s = Sample(**defaults)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestActionGeneratorSamples:
    async def test_asbestos_generates_remediation_action(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(db_session, building.id, status="completed")
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            concentration=5.0,
            unit="percent_weight",
            threshold_exceeded=True,
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        assert len(actions) >= 1
        remediation = [a for a in actions if a.title == "action.auto.asbestos_remediation"]
        assert len(remediation) == 1
        assert remediation[0].priority == ACTION_PRIORITY_HIGH
        assert remediation[0].action_type == ACTION_TYPE_REMEDIATION
        assert remediation[0].source_type == ACTION_SOURCE_DIAGNOSTIC

    async def test_pcb_generates_decontamination_action(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(db_session, building.id, status="completed")
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="pcb",
            concentration=100.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        pcb_actions = [a for a in actions if a.title == "action.auto.pcb_decontamination"]
        assert len(pcb_actions) == 1
        assert pcb_actions[0].priority == ACTION_PRIORITY_HIGH

    async def test_lead_generates_investigation_action(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(db_session, building.id, status="completed")
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="lead",
            concentration=6000.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        lead_actions = [a for a in actions if a.title == "action.auto.lead_assessment"]
        assert len(lead_actions) == 1
        assert lead_actions[0].priority == ACTION_PRIORITY_MEDIUM
        assert lead_actions[0].action_type == ACTION_TYPE_INVESTIGATION

    async def test_hap_generates_remediation_action(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(db_session, building.id, status="completed")
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="hap",
            concentration=500.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        hap_actions = [a for a in actions if a.title == "action.auto.hap_remediation"]
        assert len(hap_actions) == 1
        assert hap_actions[0].priority == ACTION_PRIORITY_MEDIUM

    async def test_multiple_pollutants_generate_multiple_actions(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(db_session, building.id, status="completed")
        await _make_sample(
            db_session,
            diag.id,
            sample_number="S-1",
            pollutant_type="asbestos",
            concentration=5.0,
            unit="percent_weight",
            threshold_exceeded=True,
        )
        await _make_sample(
            db_session,
            diag.id,
            sample_number="S-2",
            pollutant_type="pcb",
            concentration=100.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        action_titles = {a.title for a in actions}
        assert "action.auto.asbestos_remediation" in action_titles
        assert "action.auto.pcb_decontamination" in action_titles

    async def test_no_actions_for_clean_diagnostic(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(db_session, building.id, status="completed")
        # Sample with no threshold exceeded
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            concentration=0.1,
            unit="percent_weight",
            threshold_exceeded=False,
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        # Only documentation action (missing report), no pollutant actions
        pollutant_actions = [
            a for a in actions if a.action_type in (ACTION_TYPE_REMEDIATION, ACTION_TYPE_INVESTIGATION)
        ]
        assert len(pollutant_actions) == 0


class TestActionGeneratorRadon:
    async def test_radon_300_generates_mitigation(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(db_session, building.id, status="completed")
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="radon",
            concentration=500.0,
            unit="bq_per_m3",
            threshold_exceeded=True,
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        radon_actions = [a for a in actions if a.title == "action.auto.radon_mitigation"]
        assert len(radon_actions) == 1
        assert radon_actions[0].priority == ACTION_PRIORITY_MEDIUM

    async def test_radon_1000_generates_urgent(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(db_session, building.id, status="completed")
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="radon",
            concentration=1500.0,
            unit="bq_per_m3",
            threshold_exceeded=True,
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        urgent_actions = [a for a in actions if a.title == "action.auto.radon_urgent"]
        assert len(urgent_actions) == 1
        assert urgent_actions[0].priority == ACTION_PRIORITY_CRITICAL

    async def test_radon_thresholds_differ(self, db_session, admin_user):
        """300 vs 1000 generate different priorities."""
        building = await _make_building(db_session, admin_user.id)

        # 500 Bq/m3 → medium priority
        diag1 = await _make_diagnostic(db_session, building.id, status="completed")
        await _make_sample(
            db_session,
            diag1.id,
            pollutant_type="radon",
            concentration=500.0,
            unit="bq_per_m3",
            threshold_exceeded=True,
        )
        actions1 = await generate_actions_from_diagnostic(db_session, building.id, diag1.id)
        radon1 = [a for a in actions1 if "radon" in a.title]
        assert radon1[0].priority == ACTION_PRIORITY_MEDIUM

        # 1500 Bq/m3 → critical priority
        diag2 = await _make_diagnostic(db_session, building.id, status="completed")
        await _make_sample(
            db_session,
            diag2.id,
            pollutant_type="radon",
            concentration=1500.0,
            unit="bq_per_m3",
            threshold_exceeded=True,
        )
        actions2 = await generate_actions_from_diagnostic(db_session, building.id, diag2.id)
        radon2 = [a for a in actions2 if "radon" in a.title]
        assert radon2[0].priority == ACTION_PRIORITY_CRITICAL


class TestActionGeneratorCompliance:
    async def test_suva_notification_action(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(
            db_session,
            building.id,
            status="completed",
            diagnostic_type="renovation",
            suva_notification_required=False,
            suva_notification_date=None,
        )
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            concentration=5.0,
            unit="percent_weight",
            threshold_exceeded=True,
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        suva_actions = [a for a in actions if a.title == "action.auto.suva_notification"]
        assert len(suva_actions) == 1
        assert suva_actions[0].priority == ACTION_PRIORITY_HIGH
        assert suva_actions[0].action_type == ACTION_TYPE_NOTIFICATION

    async def test_authority_notification_action(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(
            db_session,
            building.id,
            status="completed",
            diagnostic_type="renovation",
            suva_notification_required=False,
            canton_notification_date=None,
        )
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            concentration=5.0,
            unit="percent_weight",
            threshold_exceeded=True,
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        authority_actions = [a for a in actions if a.title == "action.auto.authority_notification"]
        assert len(authority_actions) == 1

    async def test_certified_contractor_for_major_work(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(
            db_session,
            building.id,
            status="completed",
            diagnostic_type="renovation",
        )
        # Friable asbestos → major work category
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            concentration=5.0,
            unit="percent_weight",
            threshold_exceeded=True,
            material_category="flocage",
            material_state="heavily_degraded",
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        contractor_actions = [a for a in actions if a.title == "action.auto.certified_contractor"]
        assert len(contractor_actions) == 1
        assert contractor_actions[0].priority == ACTION_PRIORITY_HIGH
        assert contractor_actions[0].action_type == ACTION_TYPE_PROCUREMENT


class TestActionGeneratorIdempotency:
    async def test_running_twice_no_duplicates(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(db_session, building.id, status="completed")
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            concentration=5.0,
            unit="percent_weight",
            threshold_exceeded=True,
        )

        actions1 = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        assert len(actions1) >= 1

        actions2 = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        assert len(actions2) == 0  # No new actions created

    async def test_idempotent_with_multiple_pollutants(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(db_session, building.id, status="completed")
        await _make_sample(
            db_session,
            diag.id,
            sample_number="S-1",
            pollutant_type="asbestos",
            concentration=5.0,
            unit="percent_weight",
            threshold_exceeded=True,
        )
        await _make_sample(
            db_session,
            diag.id,
            sample_number="S-2",
            pollutant_type="pcb",
            concentration=100.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
        )

        first_run = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        count_first = len(first_run)
        assert count_first >= 2

        second_run = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        assert len(second_run) == 0


class TestActionGeneratorEdgeCases:
    async def test_draft_diagnostic_generates_nothing(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(db_session, building.id, status="draft")
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            concentration=5.0,
            unit="percent_weight",
            threshold_exceeded=True,
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        assert len(actions) == 0

    async def test_nonexistent_diagnostic_returns_empty(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        actions = await generate_actions_from_diagnostic(db_session, building.id, uuid.uuid4())
        assert actions == []

    async def test_missing_report_generates_documentation_action(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(
            db_session,
            building.id,
            status="completed",
            report_file_path=None,
        )
        # No exceeded samples — only documentation action
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            concentration=0.1,
            unit="percent_weight",
            threshold_exceeded=False,
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        doc_actions = [a for a in actions if a.action_type == ACTION_TYPE_DOCUMENTATION]
        assert len(doc_actions) == 1
        assert doc_actions[0].priority == ACTION_PRIORITY_LOW

    async def test_validated_status_also_generates(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(db_session, building.id, status="validated")
        await _make_sample(
            db_session,
            diag.id,
            pollutant_type="asbestos",
            concentration=5.0,
            unit="percent_weight",
            threshold_exceeded=True,
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        assert len(actions) >= 1

    async def test_metadata_contains_sample_details(self, db_session, admin_user):
        building = await _make_building(db_session, admin_user.id)
        diag = await _make_diagnostic(db_session, building.id, status="completed")
        sample = await _make_sample(
            db_session,
            diag.id,
            pollutant_type="pcb",
            concentration=200.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            location_detail="Joint fenetre",
        )

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        pcb_actions = [a for a in actions if a.title == "action.auto.pcb_decontamination"]
        assert len(pcb_actions) == 1
        meta = pcb_actions[0].metadata_json
        assert meta["pollutant_type"] == "pcb"
        assert meta["concentration"] == 200.0
        assert meta["sample_id"] == str(sample.id)
