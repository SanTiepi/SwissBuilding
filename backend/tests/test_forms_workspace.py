"""Tests for the Forms Workspace (Boucle 5 — regulatory execution layer)."""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.seeds.seed_form_templates import seed_form_templates
from app.services.forms_service import (
    acknowledge_form,
    get_applicable_forms,
    get_form_instance,
    handle_complement,
    list_form_instances,
    prefill_form,
    submit_form,
    update_form,
)


async def _create_building(db, admin_user, canton="VD"):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton=canton,
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        owner_id=admin_user.id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _create_diagnostic_with_asbestos(db, admin_user, building):
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building.id,
        diagnostic_type="avant_travaux",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db.add(diag)
    await db.flush()
    sample = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        pollutant_type="asbestos",
        location_detail="Faux plafond",
        material_category="flocage",
        concentration=2.5,
        unit="percent_weight",
        threshold_exceeded=True,
        risk_level="high",
        action_required="remove_planned",
        waste_disposal_type="special",
    )
    db.add(sample)
    await db.flush()
    return diag, sample


async def _seed_templates(db):
    count = await seed_form_templates(db)
    await db.flush()
    return count


# ---------------------------------------------------------------------------
# Seed templates
# ---------------------------------------------------------------------------


class TestSeedFormTemplates:
    async def test_seed_creates_templates(self, db_session):
        count = await _seed_templates(db_session)
        assert count == 4

    async def test_seed_is_idempotent(self, db_session):
        c1 = await _seed_templates(db_session)
        c2 = await _seed_templates(db_session)
        assert c1 == 4
        assert c2 == 0


# ---------------------------------------------------------------------------
# Applicability
# ---------------------------------------------------------------------------


class TestGetApplicableForms:
    async def test_suva_applicable_with_positive_asbestos(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _create_diagnostic_with_asbestos(db_session, admin_user, building)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id)
        form_types = [item["template"].form_type for item in applicable]
        assert "suva_notification" in form_types

    async def test_waste_plan_applicable_with_positive_samples(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _create_diagnostic_with_asbestos(db_session, admin_user, building)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id)
        form_types = [item["template"].form_type for item in applicable]
        assert "waste_plan" in form_types

    async def test_cantonal_declaration_applicable_for_vd(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user, canton="VD")
        await _create_diagnostic_with_asbestos(db_session, admin_user, building)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id)
        form_types = [item["template"].form_type for item in applicable]
        assert "cantonal_declaration" in form_types

    async def test_no_forms_for_clean_building(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _seed_templates(db_session)

        # No diagnostics/samples → no positive pollutants → no forms
        applicable = await get_applicable_forms(db_session, building.id)
        assert len(applicable) == 0

    async def test_building_not_found_raises(self, db_session):
        await _seed_templates(db_session)
        with pytest.raises(ValueError, match="not found"):
            await get_applicable_forms(db_session, uuid.uuid4())

    async def test_work_permit_applicable_with_intervention_type(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id, intervention_type="renovation")
        form_types = [item["template"].form_type for item in applicable]
        assert "work_permit" in form_types


# ---------------------------------------------------------------------------
# Pre-fill
# ---------------------------------------------------------------------------


class TestPrefillForm:
    async def test_prefill_populates_building_fields(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _create_diagnostic_with_asbestos(db_session, admin_user, building)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id)
        suva = next(a for a in applicable if a["template"].form_type == "suva_notification")

        instance = await prefill_form(
            db_session,
            suva["template"].id,
            building.id,
            admin_user.id,
        )
        assert instance.status in ("prefilled", "reviewed")
        assert instance.building_id == building.id
        assert instance.field_values is not None
        assert "building_address" in instance.field_values
        assert instance.field_values["building_address"]["value"] == "Rue Test 1"
        assert instance.field_values["building_address"]["confidence"] == "high"
        assert instance.prefill_confidence is not None
        assert 0.0 <= instance.prefill_confidence <= 1.0

    async def test_prefill_marks_missing_fields(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _create_diagnostic_with_asbestos(db_session, admin_user, building)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id)
        suva = next(a for a in applicable if a["template"].form_type == "suva_notification")

        instance = await prefill_form(
            db_session,
            suva["template"].id,
            building.id,
            admin_user.id,
        )
        # Owner and manual fields should be in missing_fields
        assert instance.missing_fields is not None
        assert len(instance.missing_fields) > 0

    async def test_prefill_template_not_found(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        with pytest.raises(ValueError, match=r"FormTemplate.*not found"):
            await prefill_form(db_session, uuid.uuid4(), building.id, admin_user.id)


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


class TestUpdateForm:
    async def test_update_field_values(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _create_diagnostic_with_asbestos(db_session, admin_user, building)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id)
        suva = next(a for a in applicable if a["template"].form_type == "suva_notification")
        instance = await prefill_form(
            db_session,
            suva["template"].id,
            building.id,
            admin_user.id,
        )

        updated = await update_form(
            db_session,
            instance.id,
            field_values={"owner": {"value": "M. Dupont"}},
        )
        assert updated.field_values["owner"]["value"] == "M. Dupont"
        assert updated.field_values["owner"]["manual_override"] is True
        assert updated.status == "reviewed"

    async def test_cannot_update_submitted_form(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _create_diagnostic_with_asbestos(db_session, admin_user, building)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id)
        suva = next(a for a in applicable if a["template"].form_type == "suva_notification")
        instance = await prefill_form(
            db_session,
            suva["template"].id,
            building.id,
            admin_user.id,
        )
        await submit_form(db_session, instance.id)

        with pytest.raises(ValueError, match="Cannot update"):
            await update_form(db_session, instance.id, field_values={"owner": {"value": "test"}})


# ---------------------------------------------------------------------------
# Submit / Complement / Acknowledge lifecycle
# ---------------------------------------------------------------------------


class TestFormLifecycle:
    async def test_submit_form(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _create_diagnostic_with_asbestos(db_session, admin_user, building)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id)
        suva = next(a for a in applicable if a["template"].form_type == "suva_notification")
        instance = await prefill_form(
            db_session,
            suva["template"].id,
            building.id,
            admin_user.id,
        )

        submitted = await submit_form(db_session, instance.id, submission_reference="REF-2026-001")
        assert submitted.status == "submitted"
        assert submitted.submitted_at is not None
        assert submitted.submission_reference == "REF-2026-001"

    async def test_complement_request(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _create_diagnostic_with_asbestos(db_session, admin_user, building)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id)
        suva = next(a for a in applicable if a["template"].form_type == "suva_notification")
        instance = await prefill_form(
            db_session,
            suva["template"].id,
            building.id,
            admin_user.id,
        )
        await submit_form(db_session, instance.id)

        complemented = await handle_complement(db_session, instance.id, "Missing contractor certificate")
        assert complemented.status == "complement_requested"
        assert complemented.complement_details == "Missing contractor certificate"

    async def test_acknowledge_form(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _create_diagnostic_with_asbestos(db_session, admin_user, building)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id)
        suva = next(a for a in applicable if a["template"].form_type == "suva_notification")
        instance = await prefill_form(
            db_session,
            suva["template"].id,
            building.id,
            admin_user.id,
        )
        await submit_form(db_session, instance.id)

        acknowledged = await acknowledge_form(db_session, instance.id)
        assert acknowledged.status == "acknowledged"
        assert acknowledged.acknowledged_at is not None

    async def test_cannot_submit_acknowledged_form(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _create_diagnostic_with_asbestos(db_session, admin_user, building)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id)
        suva = next(a for a in applicable if a["template"].form_type == "suva_notification")
        instance = await prefill_form(
            db_session,
            suva["template"].id,
            building.id,
            admin_user.id,
        )
        await submit_form(db_session, instance.id)
        await acknowledge_form(db_session, instance.id)

        with pytest.raises(ValueError, match="Cannot submit"):
            await submit_form(db_session, instance.id)


# ---------------------------------------------------------------------------
# List / Get
# ---------------------------------------------------------------------------


class TestListGetForms:
    async def test_list_form_instances(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _create_diagnostic_with_asbestos(db_session, admin_user, building)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id)
        for a in applicable[:2]:
            await prefill_form(db_session, a["template"].id, building.id, admin_user.id)

        instances = await list_form_instances(db_session, building.id)
        assert len(instances) == 2

    async def test_get_form_instance(self, db_session, admin_user):
        building = await _create_building(db_session, admin_user)
        await _create_diagnostic_with_asbestos(db_session, admin_user, building)
        await _seed_templates(db_session)

        applicable = await get_applicable_forms(db_session, building.id)
        instance = await prefill_form(
            db_session,
            applicable[0]["template"].id,
            building.id,
            admin_user.id,
        )

        fetched = await get_form_instance(db_session, instance.id)
        assert fetched is not None
        assert fetched.id == instance.id

    async def test_get_nonexistent_returns_none(self, db_session):
        fetched = await get_form_instance(db_session, uuid.uuid4())
        assert fetched is None
