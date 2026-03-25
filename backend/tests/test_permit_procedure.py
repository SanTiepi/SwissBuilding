"""BatiConnect — Permit Procedure tests (service-layer + route-level)."""

import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.api.permit_procedures import router as permit_procedures_router
from app.main import app
from app.models.event import Event
from app.models.obligation import Obligation
from app.services.permit_procedure_service import (
    advance_step,
    approve_procedure,
    create_procedure,
    get_procedural_blockers,
    get_procedure_detail,
    get_procedures,
    reject_procedure,
    request_complement,
    respond_to_request,
    submit_procedure,
    withdraw_procedure,
)

# Register router for HTTP tests
app.include_router(permit_procedures_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Service-layer tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_procedure(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {
            "procedure_type": "construction_permit",
            "title": "Permis de construire - Rénovation toiture",
        },
    )
    assert proc.id is not None
    assert proc.status == "draft"
    assert proc.procedure_type == "construction_permit"


@pytest.mark.asyncio
async def test_create_procedure_creates_default_steps(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "suva_notification", "title": "Notification SUVA amiante"},
    )
    detail = await get_procedure_detail(db_session, proc.id)
    assert len(detail.steps) == 4
    types = [s.step_type for s in detail.steps]
    assert types == ["submission", "review", "decision", "acknowledgement"]
    assert detail.steps[0].status == "active"
    assert detail.steps[1].status == "pending"


@pytest.mark.asyncio
async def test_create_procedure_creates_timeline_event(db_session, sample_building):
    await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "demolition_permit", "title": "Démolition annexe"},
    )
    result = await db_session.execute(
        select(Event).where(
            Event.building_id == sample_building.id,
            Event.event_type == "permit_created",
        )
    )
    events = list(result.scalars().all())
    assert len(events) >= 1


@pytest.mark.asyncio
async def test_submit_procedure(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Test submit"},
    )
    submitted = await submit_procedure(db_session, proc.id)
    assert submitted.status == "submitted"
    assert submitted.submitted_at is not None


@pytest.mark.asyncio
async def test_submit_creates_obligation(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Test obligation"},
    )
    await submit_procedure(db_session, proc.id)
    result = await db_session.execute(
        select(Obligation).where(
            Obligation.building_id == sample_building.id,
            Obligation.obligation_type == "authority_submission",
            Obligation.linked_entity_id == proc.id,
        )
    )
    obligations = list(result.scalars().all())
    assert len(obligations) == 1


@pytest.mark.asyncio
async def test_submit_non_draft_raises(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Test non-draft"},
    )
    await submit_procedure(db_session, proc.id)
    with pytest.raises(ValueError, match="Cannot submit"):
        await submit_procedure(db_session, proc.id)


@pytest.mark.asyncio
async def test_advance_step(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Test advance"},
    )
    detail = await get_procedure_detail(db_session, proc.id)
    first_step = detail.steps[0]
    completed = await advance_step(db_session, proc.id, first_step.id)
    assert completed.status == "completed"
    assert completed.completed_at is not None

    # Next step should be active
    detail2 = await get_procedure_detail(db_session, proc.id)
    assert detail2.steps[1].status == "active"


@pytest.mark.asyncio
async def test_advance_step_already_completed_raises(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Test double advance"},
    )
    detail = await get_procedure_detail(db_session, proc.id)
    step = detail.steps[0]
    await advance_step(db_session, proc.id, step.id)
    with pytest.raises(ValueError, match="already completed"):
        await advance_step(db_session, proc.id, step.id)


@pytest.mark.asyncio
async def test_request_complement(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Test complement"},
    )
    await submit_procedure(db_session, proc.id)
    req = await request_complement(
        db_session,
        proc.id,
        {
            "request_type": "complement_request",
            "subject": "Documents manquants",
            "body": "Veuillez fournir le plan de sécurité.",
            "response_due_date": date(2026, 4, 15),
        },
    )
    assert req.status == "open"
    assert req.request_type == "complement_request"

    # Procedure should be complement_requested
    detail = await get_procedure_detail(db_session, proc.id)
    assert detail.status == "complement_requested"


@pytest.mark.asyncio
async def test_complement_creates_obligation_with_due_date(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Test complement obl"},
    )
    await submit_procedure(db_session, proc.id)
    await request_complement(
        db_session,
        proc.id,
        {
            "request_type": "complement_request",
            "subject": "Analyse complémentaire",
            "body": "Analyse PCB requise.",
            "response_due_date": date(2026, 5, 1),
        },
    )
    result = await db_session.execute(
        select(Obligation).where(
            Obligation.building_id == sample_building.id,
            Obligation.linked_entity_id == proc.id,
        )
    )
    obligations = list(result.scalars().all())
    # At least 2: one from submit, one from complement
    assert len(obligations) >= 2


@pytest.mark.asyncio
async def test_respond_to_request(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Test respond"},
    )
    req = await request_complement(
        db_session,
        proc.id,
        {
            "request_type": "information_request",
            "subject": "Info needed",
            "body": "Please clarify scope.",
        },
    )
    responded = await respond_to_request(db_session, req.id, "Here is the clarification.")
    assert responded.status == "responded"
    assert responded.response_body == "Here is the clarification."
    assert responded.responded_at is not None


@pytest.mark.asyncio
async def test_respond_not_found_raises(db_session):
    with pytest.raises(ValueError, match="not found"):
        await respond_to_request(db_session, uuid.uuid4(), "response")


@pytest.mark.asyncio
async def test_approve_procedure(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Test approve"},
    )
    approved = await approve_procedure(db_session, proc.id, reference_number="PC-2026-0042")
    assert approved.status == "approved"
    assert approved.approved_at is not None
    assert approved.reference_number == "PC-2026-0042"


@pytest.mark.asyncio
async def test_reject_procedure(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Test reject"},
    )
    rejected = await reject_procedure(db_session, proc.id, reason="Non conforme OTConst")
    assert rejected.status == "rejected"
    assert rejected.rejected_at is not None


@pytest.mark.asyncio
async def test_withdraw_procedure(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Test withdraw"},
    )
    withdrawn = await withdraw_procedure(db_session, proc.id)
    assert withdrawn.status == "withdrawn"


@pytest.mark.asyncio
async def test_get_procedures_list(db_session, sample_building):
    for i in range(3):
        await create_procedure(
            db_session,
            sample_building.id,
            {"procedure_type": "construction_permit", "title": f"Proc {i}"},
        )
    procs = await get_procedures(db_session, sample_building.id)
    assert len(procs) == 3


@pytest.mark.asyncio
async def test_get_procedure_detail_with_steps_and_requests(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Detail test"},
    )
    await request_complement(
        db_session,
        proc.id,
        {"request_type": "clarification", "subject": "Test", "body": "Details needed."},
    )
    # Verify steps via detail
    detail = await get_procedure_detail(db_session, proc.id)
    assert len(detail.steps) == 4
    # Verify authority request created via direct query
    from app.models.authority_request import AuthorityRequest

    result = await db_session.execute(select(AuthorityRequest).where(AuthorityRequest.procedure_id == proc.id))
    requests = list(result.scalars().all())
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_procedural_blockers(db_session, sample_building):
    proc1 = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Blocker 1"},
    )
    await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "suva_notification", "title": "Not blocking"},
    )
    await submit_procedure(db_session, proc1.id)
    # proc2 stays draft — not blocking
    blockers = await get_procedural_blockers(db_session, sample_building.id)
    assert len(blockers) == 1
    assert blockers[0]["status"] == "submitted"


@pytest.mark.asyncio
async def test_complement_requested_is_blocker(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Complement blocker"},
    )
    await submit_procedure(db_session, proc.id)
    await request_complement(
        db_session,
        proc.id,
        {"request_type": "complement_request", "subject": "Need docs", "body": "Plan de sécurité"},
    )
    blockers = await get_procedural_blockers(db_session, sample_building.id)
    assert any(b["status"] == "complement_requested" for b in blockers)


@pytest.mark.asyncio
async def test_approved_not_blocker(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Approved"},
    )
    await approve_procedure(db_session, proc.id)
    blockers = await get_procedural_blockers(db_session, sample_building.id)
    assert len(blockers) == 0


@pytest.mark.asyncio
async def test_full_workflow(db_session, sample_building):
    """Full workflow: create -> submit -> complement -> respond -> approve."""
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {
            "procedure_type": "construction_permit",
            "title": "Full workflow test",
            "authority_name": "Service des constructions VD",
        },
    )
    assert proc.status == "draft"

    # Submit
    proc = await submit_procedure(db_session, proc.id)
    assert proc.status == "submitted"

    # Advance first step (submission)
    detail = await get_procedure_detail(db_session, proc.id)
    submission_step = detail.steps[0]
    await advance_step(db_session, proc.id, submission_step.id)

    # Complement request
    req = await request_complement(
        db_session,
        proc.id,
        {
            "request_type": "complement_request",
            "subject": "Analyse PCB manquante",
            "body": "Veuillez fournir l'analyse PCB des joints.",
            "response_due_date": date(2026, 4, 30),
        },
    )
    detail = await get_procedure_detail(db_session, proc.id)
    assert detail.status == "complement_requested"

    # Respond
    await respond_to_request(db_session, req.id, "Analyse PCB ci-jointe.")

    # Advance review step
    detail = await get_procedure_detail(db_session, proc.id)
    review_step = next(s for s in detail.steps if s.step_type == "review")
    # Make it active first (since complement may not have changed step status)
    review_step.status = "active"
    await db_session.flush()
    await advance_step(db_session, proc.id, review_step.id)

    # Approve
    proc = await approve_procedure(db_session, proc.id, reference_number="PC-2026-1234")
    assert proc.status == "approved"
    assert proc.reference_number == "PC-2026-1234"


@pytest.mark.asyncio
async def test_provenance_fields(db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {
            "procedure_type": "cantonal_declaration",
            "title": "With provenance",
            "source_type": "manual",
            "confidence": "verified",
            "source_ref": "dossier-2026-001",
        },
    )
    assert proc.source_type == "manual"
    assert proc.confidence == "verified"
    assert proc.source_ref == "dossier-2026-001"


# ---------------------------------------------------------------------------
# Route-level tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_list_procedures(client, auth_headers, db_session, sample_building):
    await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "API list test"},
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/permit-procedures", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1


@pytest.mark.asyncio
async def test_api_create_procedure(client, auth_headers, sample_building):
    payload = {
        "procedure_type": "suva_notification",
        "title": "Notification SUVA API",
        "authority_name": "SUVA",
    }
    resp = await client.post(
        f"/api/v1/buildings/{sample_building.id}/permit-procedures",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["procedure_type"] == "suva_notification"
    assert body["status"] == "draft"
    assert len(body["steps"]) == 4


@pytest.mark.asyncio
async def test_api_get_procedure(client, auth_headers, db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "API get test"},
    )
    await db_session.commit()

    resp = await client.get(f"/api/v1/permit-procedures/{proc.id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "API get test"
    assert "steps" in body
    assert "authority_requests" in body


@pytest.mark.asyncio
async def test_api_submit_procedure(client, auth_headers, db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "API submit test"},
    )
    await db_session.commit()

    resp = await client.post(f"/api/v1/permit-procedures/{proc.id}/submit", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "submitted"


@pytest.mark.asyncio
async def test_api_approve_procedure(client, auth_headers, db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "API approve test"},
    )
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/permit-procedures/{proc.id}/approve?reference_number=REF-001",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["reference_number"] == "REF-001"


@pytest.mark.asyncio
async def test_api_reject_procedure(client, auth_headers, db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "API reject test"},
    )
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/permit-procedures/{proc.id}/reject?reason=Non%20conforme",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_api_procedure_not_found(client, auth_headers):
    fake = uuid.uuid4()
    resp = await client.get(f"/api/v1/permit-procedures/{fake}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_blockers(client, auth_headers, db_session, sample_building):
    proc = await create_procedure(
        db_session,
        sample_building.id,
        {"procedure_type": "construction_permit", "title": "Blocker API"},
    )
    await submit_procedure(db_session, proc.id)
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{sample_building.id}/procedural-blockers", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1


@pytest.mark.asyncio
async def test_api_unauthorized(client):
    fake = uuid.uuid4()
    resp = await client.get(f"/api/v1/buildings/{fake}/permit-procedures")
    assert resp.status_code in (401, 403)
