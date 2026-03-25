"""BatiConnect — Permit Procedure operations service."""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.authority_request import AuthorityRequest
from app.models.event import Event
from app.models.obligation import Obligation
from app.models.permit_procedure import PermitProcedure
from app.models.permit_step import PermitStep

# Default steps created for each procedure type
_DEFAULT_STEPS = [
    {"step_type": "submission", "title": "Submission", "step_order": 0},
    {"step_type": "review", "title": "Authority review", "step_order": 1},
    {"step_type": "decision", "title": "Decision", "step_order": 2},
    {"step_type": "acknowledgement", "title": "Acknowledgement", "step_order": 3},
]


def _create_timeline_event(building_id: UUID, event_type: str, title: str, description: str | None = None) -> Event:
    """Create an Event instance for timeline tracking."""
    return Event(
        building_id=building_id,
        event_type=event_type,
        date=date.today(),
        title=title,
        description=description,
    )


async def create_procedure(db: AsyncSession, building_id: UUID, data: dict) -> PermitProcedure:
    """Create a permit procedure with default steps (submission -> review -> decision -> acknowledgement)."""
    procedure = PermitProcedure(building_id=building_id, status="draft", **data)
    db.add(procedure)
    await db.flush()

    # Create default steps; first step is active
    for i, step_def in enumerate(_DEFAULT_STEPS):
        step = PermitStep(
            procedure_id=procedure.id,
            status="active" if i == 0 else "pending",
            **step_def,
        )
        db.add(step)

    # Timeline event
    evt = _create_timeline_event(building_id, "permit_created", f"Permit procedure created: {procedure.title}")
    db.add(evt)

    await db.flush()
    await db.refresh(procedure)
    return procedure


async def submit_procedure(db: AsyncSession, procedure_id: UUID) -> PermitProcedure:
    """Transition procedure from draft to submitted. Creates an Obligation for authority submission."""
    procedure = await get_procedure_detail(db, procedure_id)
    if not procedure:
        raise ValueError("Procedure not found")
    if procedure.status != "draft":
        raise ValueError(f"Cannot submit procedure in status '{procedure.status}'")

    procedure.status = "submitted"
    procedure.submitted_at = datetime.now(tz=UTC)

    # Create obligation for tracking
    obligation = Obligation(
        building_id=procedure.building_id,
        title=f"Authority submission: {procedure.title}",
        obligation_type="authority_submission",
        due_date=date.today(),
        status="upcoming",
        priority="high",
        linked_entity_type="permit_procedure",
        linked_entity_id=procedure.id,
    )
    db.add(obligation)

    evt = _create_timeline_event(
        procedure.building_id, "permit_submitted", f"Permit procedure submitted: {procedure.title}"
    )
    db.add(evt)

    await db.flush()
    await db.refresh(procedure)
    return procedure


async def advance_step(db: AsyncSession, procedure_id: UUID, step_id: UUID) -> PermitStep:
    """Complete the given step and activate the next one in order."""
    procedure = await get_procedure_detail(db, procedure_id)
    if not procedure:
        raise ValueError("Procedure not found")

    # Find the target step
    target_step = None
    for s in procedure.steps:
        if s.id == step_id:
            target_step = s
            break
    if not target_step:
        raise ValueError("Step not found in this procedure")
    if target_step.status == "completed":
        raise ValueError("Step already completed")

    target_step.status = "completed"
    target_step.completed_at = datetime.now(tz=UTC)

    # Activate the next pending step
    for s in procedure.steps:
        if s.step_order > target_step.step_order and s.status == "pending":
            s.status = "active"
            break

    # If decision step completed, move procedure to under_review
    if target_step.step_type == "submission" and procedure.status == "submitted":
        procedure.status = "under_review"

    evt = _create_timeline_event(
        procedure.building_id,
        "permit_step_completed",
        f"Step completed: {target_step.title}",
        f"Procedure: {procedure.title}",
    )
    db.add(evt)

    await db.flush()
    await db.refresh(target_step)
    return target_step


async def request_complement(db: AsyncSession, procedure_id: UUID, data: dict) -> AuthorityRequest:
    """Create a complement/information request. Sets procedure status to complement_requested."""
    procedure = await get_procedure_detail(db, procedure_id)
    if not procedure:
        raise ValueError("Procedure not found")

    procedure.status = "complement_requested"

    request = AuthorityRequest(procedure_id=procedure_id, status="open", **data)
    db.add(request)
    await db.flush()

    # Create obligation with due date if provided
    if data.get("response_due_date"):
        obligation = Obligation(
            building_id=procedure.building_id,
            title=f"Complement response due: {data.get('subject', procedure.title)}",
            obligation_type="authority_submission",
            due_date=data["response_due_date"],
            status="upcoming",
            priority="high",
            linked_entity_type="permit_procedure",
            linked_entity_id=procedure.id,
        )
        db.add(obligation)

    evt = _create_timeline_event(
        procedure.building_id,
        "permit_complement_requested",
        f"Complement requested: {data.get('subject', '')}",
        data.get("body"),
    )
    db.add(evt)

    await db.flush()
    await db.refresh(request)
    return request


async def respond_to_request(db: AsyncSession, request_id: UUID, response_body: str) -> AuthorityRequest:
    """Mark an authority request as responded."""
    result = await db.execute(select(AuthorityRequest).where(AuthorityRequest.id == request_id))
    request = result.scalar_one_or_none()
    if not request:
        raise ValueError("Authority request not found")

    request.status = "responded"
    request.response_body = response_body
    request.responded_at = datetime.now(tz=UTC)

    # Load procedure for timeline event
    proc_result = await db.execute(select(PermitProcedure).where(PermitProcedure.id == request.procedure_id))
    procedure = proc_result.scalar_one_or_none()
    if procedure:
        evt = _create_timeline_event(
            procedure.building_id,
            "permit_complement_responded",
            f"Complement responded: {request.subject}",
        )
        db.add(evt)

    await db.flush()
    await db.refresh(request)
    return request


async def approve_procedure(
    db: AsyncSession, procedure_id: UUID, reference_number: str | None = None
) -> PermitProcedure:
    """Approve a permit procedure."""
    procedure = await get_procedure_detail(db, procedure_id)
    if not procedure:
        raise ValueError("Procedure not found")

    procedure.status = "approved"
    procedure.approved_at = datetime.now(tz=UTC)
    if reference_number:
        procedure.reference_number = reference_number

    evt = _create_timeline_event(procedure.building_id, "permit_approved", f"Permit approved: {procedure.title}")
    db.add(evt)

    await db.flush()
    await db.refresh(procedure)
    return procedure


async def reject_procedure(db: AsyncSession, procedure_id: UUID, reason: str | None = None) -> PermitProcedure:
    """Reject a permit procedure."""
    procedure = await get_procedure_detail(db, procedure_id)
    if not procedure:
        raise ValueError("Procedure not found")

    procedure.status = "rejected"
    procedure.rejected_at = datetime.now(tz=UTC)

    evt = _create_timeline_event(
        procedure.building_id,
        "permit_rejected",
        f"Permit rejected: {procedure.title}",
        reason,
    )
    db.add(evt)

    await db.flush()
    await db.refresh(procedure)
    return procedure


async def withdraw_procedure(db: AsyncSession, procedure_id: UUID) -> PermitProcedure:
    """Withdraw a permit procedure."""
    procedure = await get_procedure_detail(db, procedure_id)
    if not procedure:
        raise ValueError("Procedure not found")

    procedure.status = "withdrawn"

    evt = _create_timeline_event(procedure.building_id, "permit_withdrawn", f"Permit withdrawn: {procedure.title}")
    db.add(evt)

    await db.flush()
    await db.refresh(procedure)
    return procedure


async def get_procedures(db: AsyncSession, building_id: UUID) -> list[PermitProcedure]:
    """List all permit procedures for a building with steps eager-loaded."""
    result = await db.execute(
        select(PermitProcedure)
        .where(PermitProcedure.building_id == building_id)
        .options(selectinload(PermitProcedure.steps))
        .order_by(PermitProcedure.created_at.desc())
    )
    return list(result.scalars().all())


async def get_procedure_detail(db: AsyncSession, procedure_id: UUID) -> PermitProcedure | None:
    """Get a single procedure with steps and authority requests."""
    result = await db.execute(
        select(PermitProcedure)
        .where(PermitProcedure.id == procedure_id)
        .options(
            selectinload(PermitProcedure.steps),
            selectinload(PermitProcedure.authority_requests),
        )
    )
    return result.scalar_one_or_none()


async def get_procedural_blockers(db: AsyncSession, building_id: UUID) -> list[dict]:
    """Return procedures that are blocking activities (complement_requested, under_review, submitted)."""
    blocking_statuses = {"submitted", "under_review", "complement_requested"}
    procedures = await get_procedures(db, building_id)
    blockers = []
    for proc in procedures:
        if proc.status in blocking_statuses:
            reason_map = {
                "submitted": "Awaiting authority review",
                "under_review": "Under authority review",
                "complement_requested": "Complement requested by authority",
            }
            blockers.append(
                {
                    "procedure_id": proc.id,
                    "procedure_type": proc.procedure_type,
                    "title": proc.title,
                    "status": proc.status,
                    "blocker_reason": reason_map.get(proc.status, "Pending"),
                }
            )
    return blockers
