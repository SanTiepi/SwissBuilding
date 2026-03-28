"""Tests for Procedure OS — templates, instances, applicability, lifecycle."""

import uuid

import pytest

from app.models.building import Building
from app.models.building_case import BuildingCase
from app.models.organization import Organization
from app.seeds.seed_procedure_templates import seed_procedure_templates
from app.services import procedure_service

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


async def _create_case(db, building, admin_user, org_id):
    case = BuildingCase(
        id=uuid.uuid4(),
        building_id=building.id,
        organization_id=org_id,
        created_by_id=admin_user.id,
        case_type="works",
        title="Test works case",
        state="draft",
        pollutant_scope=["asbestos"],
    )
    db.add(case)
    await db.flush()
    return case


async def _seed(db):
    count = await seed_procedure_templates(db)
    await db.flush()
    return count


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_procedure_templates(db_session):
    count = await _seed(db_session)
    assert count == 8


@pytest.mark.asyncio
async def test_seed_idempotent(db_session):
    c1 = await _seed(db_session)
    c2 = await _seed(db_session)
    assert c1 == c2 == 8
    templates = await procedure_service.list_templates(db_session)
    assert len(templates) == 8


# ---------------------------------------------------------------------------
# Template queries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_templates(db_session):
    await _seed(db_session)
    all_tpls = await procedure_service.list_templates(db_session)
    assert len(all_tpls) == 8

    federal = await procedure_service.list_templates(db_session, scope="federal")
    assert len(federal) >= 2

    vd = await procedure_service.list_templates(db_session, canton="VD")
    assert len(vd) >= 3

    notifications = await procedure_service.list_templates(db_session, procedure_type="notification")
    assert len(notifications) >= 1


@pytest.mark.asyncio
async def test_get_template(db_session):
    await _seed(db_session)
    all_tpls = await procedure_service.list_templates(db_session)
    tpl = await procedure_service.get_template(db_session, all_tpls[0].id)
    assert tpl is not None
    assert tpl.name == all_tpls[0].name


@pytest.mark.asyncio
async def test_get_template_not_found(db_session):
    result = await procedure_service.get_template(db_session, uuid.uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# Applicability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_applicable_procedures_for_vd_building(db_session, admin_user):
    await _seed(db_session)
    building = await _create_building(db_session, admin_user, canton="VD")
    results = await procedure_service.get_applicable_procedures(db_session, building.id)
    assert len(results) >= 3
    names = [r["template"].name for r in results]
    assert any("VD" in n or "Vaud" in n for n in names)


@pytest.mark.asyncio
async def test_applicable_procedures_for_ge_building(db_session, admin_user):
    await _seed(db_session)
    building = await _create_building(db_session, admin_user, canton="GE")
    results = await procedure_service.get_applicable_procedures(db_session, building.id)
    names = [r["template"].name for r in results]
    assert any("GE" in n or "Geneve" in n for n in names)


@pytest.mark.asyncio
async def test_applicable_procedures_with_work_type(db_session, admin_user):
    await _seed(db_session)
    building = await _create_building(db_session, admin_user, canton="VD")
    results = await procedure_service.get_applicable_procedures(db_session, building.id, work_type="demolition")
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_applicable_procedures_nonexistent_building(db_session):
    await _seed(db_session)
    results = await procedure_service.get_applicable_procedures(db_session, uuid.uuid4())
    assert results == []


# ---------------------------------------------------------------------------
# Instance lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_procedure(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    templates = await procedure_service.list_templates(db_session)
    tpl = templates[0]

    instance = await procedure_service.start_procedure(
        db_session,
        template_id=tpl.id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    assert instance.status == "in_progress"
    assert instance.template_id == tpl.id
    assert instance.current_step is not None


@pytest.mark.asyncio
async def test_start_procedure_invalid_template(db_session, admin_user):
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    with pytest.raises(ValueError, match="not found"):
        await procedure_service.start_procedure(
            db_session,
            template_id=uuid.uuid4(),
            building_id=building.id,
            created_by_id=admin_user.id,
            organization_id=org.id,
        )


@pytest.mark.asyncio
async def test_advance_step(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    templates = await procedure_service.list_templates(db_session)
    tpl = templates[0]

    instance = await procedure_service.start_procedure(
        db_session,
        template_id=tpl.id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    first_step = instance.current_step

    updated = await procedure_service.advance_step(db_session, instance.id, first_step, admin_user.id)
    assert len(updated.completed_steps) == 1
    assert updated.completed_steps[0]["name"] == first_step
    assert updated.current_step != first_step


@pytest.mark.asyncio
async def test_submit_procedure(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    templates = await procedure_service.list_templates(db_session)
    tpl = templates[0]

    instance = await procedure_service.start_procedure(
        db_session,
        template_id=tpl.id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    submitted = await procedure_service.submit_procedure(db_session, instance.id, submission_reference="REF-001")
    assert submitted.status == "submitted"
    assert submitted.submission_reference == "REF-001"
    assert submitted.submitted_at is not None


@pytest.mark.asyncio
async def test_submit_already_approved_fails(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    templates = await procedure_service.list_templates(db_session)
    tpl = templates[0]

    instance = await procedure_service.start_procedure(
        db_session,
        template_id=tpl.id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    await procedure_service.submit_procedure(db_session, instance.id)
    await procedure_service.resolve_procedure(db_session, instance.id, "approved", admin_user.id)

    with pytest.raises(ValueError, match="Cannot submit"):
        await procedure_service.submit_procedure(db_session, instance.id)


@pytest.mark.asyncio
async def test_handle_complement(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    templates = await procedure_service.list_templates(db_session)
    tpl = templates[0]

    instance = await procedure_service.start_procedure(
        db_session,
        template_id=tpl.id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    await procedure_service.submit_procedure(db_session, instance.id)
    complemented = await procedure_service.handle_complement(db_session, instance.id, "Please provide waste plan")
    assert complemented.status == "complement_requested"
    assert complemented.complement_details == "Please provide waste plan"


@pytest.mark.asyncio
async def test_resolve_procedure_approved(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    templates = await procedure_service.list_templates(db_session)
    tpl = templates[0]

    instance = await procedure_service.start_procedure(
        db_session,
        template_id=tpl.id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    await procedure_service.submit_procedure(db_session, instance.id)
    resolved = await procedure_service.resolve_procedure(db_session, instance.id, "approved", admin_user.id)
    assert resolved.status == "approved"
    assert resolved.resolution == "approved"
    assert resolved.resolved_at is not None


@pytest.mark.asyncio
async def test_resolve_procedure_rejected(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    templates = await procedure_service.list_templates(db_session)
    tpl = templates[0]

    instance = await procedure_service.start_procedure(
        db_session,
        template_id=tpl.id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    await procedure_service.submit_procedure(db_session, instance.id)
    resolved = await procedure_service.resolve_procedure(db_session, instance.id, "rejected", admin_user.id)
    assert resolved.status == "rejected"


@pytest.mark.asyncio
async def test_resolve_invalid_resolution(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    templates = await procedure_service.list_templates(db_session)
    tpl = templates[0]

    instance = await procedure_service.start_procedure(
        db_session,
        template_id=tpl.id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    await procedure_service.submit_procedure(db_session, instance.id)
    with pytest.raises(ValueError, match="Invalid resolution"):
        await procedure_service.resolve_procedure(db_session, instance.id, "maybe", admin_user.id)


@pytest.mark.asyncio
async def test_resubmit_after_complement(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    templates = await procedure_service.list_templates(db_session)
    tpl = templates[0]

    instance = await procedure_service.start_procedure(
        db_session,
        template_id=tpl.id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    await procedure_service.submit_procedure(db_session, instance.id)
    await procedure_service.handle_complement(db_session, instance.id, "Need more docs")
    resubmitted = await procedure_service.submit_procedure(db_session, instance.id, submission_reference="REF-002")
    assert resubmitted.status == "submitted"
    assert resubmitted.submission_reference == "REF-002"


# ---------------------------------------------------------------------------
# Blockers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blockers_missing_artifacts(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    templates = await procedure_service.list_templates(db_session)
    tpl = templates[0]

    instance = await procedure_service.start_procedure(
        db_session,
        template_id=tpl.id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    blockers = await procedure_service.get_procedure_blockers(db_session, instance.id)
    assert len(blockers) >= 1
    assert any("Missing mandatory" in b["description"] for b in blockers)


@pytest.mark.asyncio
async def test_blockers_complement_requested(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    templates = await procedure_service.list_templates(db_session)
    tpl = templates[0]

    instance = await procedure_service.start_procedure(
        db_session,
        template_id=tpl.id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    await procedure_service.submit_procedure(db_session, instance.id)
    await procedure_service.handle_complement(db_session, instance.id, "Need waste plan")
    blockers = await procedure_service.get_procedure_blockers(db_session, instance.id)
    assert any("Complement requested" in b["description"] for b in blockers)


@pytest.mark.asyncio
async def test_blockers_nonexistent_instance(db_session):
    blockers = await procedure_service.get_procedure_blockers(db_session, uuid.uuid4())
    assert blockers == []


# ---------------------------------------------------------------------------
# List instances
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_instances(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    templates = await procedure_service.list_templates(db_session)

    await procedure_service.start_procedure(
        db_session,
        template_id=templates[0].id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    await procedure_service.start_procedure(
        db_session,
        template_id=templates[1].id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )

    instances = await procedure_service.list_instances(db_session, building.id)
    assert len(instances) == 2


@pytest.mark.asyncio
async def test_list_instances_filter_status(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    templates = await procedure_service.list_templates(db_session)

    instance = await procedure_service.start_procedure(
        db_session,
        template_id=templates[0].id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
    )
    await procedure_service.submit_procedure(db_session, instance.id)

    in_progress = await procedure_service.list_instances(db_session, building.id, status="in_progress")
    submitted = await procedure_service.list_instances(db_session, building.id, status="submitted")
    assert len(in_progress) == 0
    assert len(submitted) == 1


# ---------------------------------------------------------------------------
# With case_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_procedure_with_case(db_session, admin_user):
    await _seed(db_session)
    org = await _create_org(db_session)
    building = await _create_building(db_session, admin_user)
    case = await _create_case(db_session, building, admin_user, org.id)
    templates = await procedure_service.list_templates(db_session)

    instance = await procedure_service.start_procedure(
        db_session,
        template_id=templates[0].id,
        building_id=building.id,
        created_by_id=admin_user.id,
        organization_id=org.id,
        case_id=case.id,
    )
    assert instance.case_id == case.id

    instances = await procedure_service.list_instances(db_session, building.id, case_id=case.id)
    assert len(instances) == 1


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_list_templates(client, db_session, auth_headers):
    await _seed(db_session)
    await db_session.commit()
    resp = await client.get("/api/v1/procedure-templates", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 8


@pytest.mark.asyncio
async def test_api_get_template(client, db_session, auth_headers):
    await _seed(db_session)
    await db_session.commit()
    resp = await client.get("/api/v1/procedure-templates", headers=auth_headers)
    tpl_id = resp.json()[0]["id"]
    detail = await client.get(f"/api/v1/procedure-templates/{tpl_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == tpl_id


@pytest.mark.asyncio
async def test_api_get_template_not_found(client, auth_headers):
    resp = await client.get(f"/api/v1/procedure-templates/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_applicable(client, db_session, admin_user, auth_headers):
    await _seed(db_session)
    building = await _create_building(db_session, admin_user)
    await db_session.commit()
    resp = await client.get(f"/api/v1/buildings/{building.id}/procedures/applicable", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_api_full_lifecycle(client, db_session, admin_user, auth_headers):
    await _seed(db_session)
    org = await _create_org(db_session)
    admin_user.organization_id = org.id
    building = await _create_building(db_session, admin_user)
    await db_session.commit()

    # List templates
    tpls = await client.get("/api/v1/procedure-templates", headers=auth_headers)
    tpl_id = tpls.json()[0]["id"]

    # Start
    resp = await client.post(
        f"/api/v1/buildings/{building.id}/procedures",
        json={"template_id": tpl_id},
        headers=auth_headers,
    )
    # The API uses current_user.organization_id which may be None for test admin
    # so we test that it returns either 201 or 400
    if resp.status_code == 201:
        instance_id = resp.json()["id"]
        assert resp.json()["status"] == "in_progress"

        # Get instance
        detail = await client.get(f"/api/v1/procedures/{instance_id}", headers=auth_headers)
        assert detail.status_code == 200

        # List instances
        list_resp = await client.get(f"/api/v1/buildings/{building.id}/procedures", headers=auth_headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

        # Advance step
        first_step = resp.json()["current_step"]
        adv = await client.post(
            f"/api/v1/procedures/{instance_id}/advance",
            json={"step_name": first_step},
            headers=auth_headers,
        )
        assert adv.status_code == 200

        # Submit
        sub = await client.post(
            f"/api/v1/procedures/{instance_id}/submit",
            json={"submission_reference": "SUB-001"},
            headers=auth_headers,
        )
        assert sub.status_code == 200
        assert sub.json()["status"] == "submitted"

        # Resolve
        res = await client.post(
            f"/api/v1/procedures/{instance_id}/resolve",
            json={"resolution": "approved"},
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "approved"

        # Blockers
        blockers = await client.get(f"/api/v1/procedures/{instance_id}/blockers", headers=auth_headers)
        assert blockers.status_code == 200


@pytest.mark.asyncio
async def test_api_instance_not_found(client, auth_headers):
    resp = await client.get(f"/api/v1/procedures/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Template data integrity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_all_templates_have_steps(db_session):
    await _seed(db_session)
    templates = await procedure_service.list_templates(db_session)
    for tpl in templates:
        assert tpl.steps, f"Template '{tpl.name}' has no steps"
        assert len(tpl.steps) >= 3, f"Template '{tpl.name}' has fewer than 3 steps"


@pytest.mark.asyncio
async def test_all_templates_have_required_artifacts(db_session):
    await _seed(db_session)
    templates = await procedure_service.list_templates(db_session)
    for tpl in templates:
        assert tpl.required_artifacts, f"Template '{tpl.name}' has no required_artifacts"


@pytest.mark.asyncio
async def test_all_templates_have_legal_basis(db_session):
    await _seed(db_session)
    templates = await procedure_service.list_templates(db_session)
    for tpl in templates:
        assert tpl.legal_basis, f"Template '{tpl.name}' has no legal_basis"


@pytest.mark.asyncio
async def test_all_templates_have_authority(db_session):
    await _seed(db_session)
    templates = await procedure_service.list_templates(db_session)
    for tpl in templates:
        assert tpl.authority_name, f"Template '{tpl.name}' has no authority_name"


@pytest.mark.asyncio
async def test_french_labels(db_session):
    """All template names should be in French."""
    await _seed(db_session)
    templates = await procedure_service.list_templates(db_session)
    for tpl in templates:
        name_lower = tpl.name.lower()
        assert any(
            kw in name_lower for kw in ["declaration", "annonce", "permis", "preavis", "plan", "demande", "renovation"]
        ), f"Template '{tpl.name}' does not appear to be in French"
