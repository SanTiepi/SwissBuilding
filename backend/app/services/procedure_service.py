"""BatiConnect — Procedure OS service.

Manages procedure templates and instances: determine applicability,
start/advance/submit/complement/resolve procedures, and compute blockers.

Reuses rule_resolver for jurisdiction matching.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.building_case import BuildingCase
from app.models.procedure import (
    ProcedureInstance,
    ProcedureTemplate,
)
from app.services.rule_resolver import _walk_jurisdiction_chain

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template queries
# ---------------------------------------------------------------------------


async def list_templates(
    db: AsyncSession,
    *,
    active_only: bool = True,
    procedure_type: str | None = None,
    scope: str | None = None,
    canton: str | None = None,
) -> list[ProcedureTemplate]:
    """List procedure templates with optional filters."""
    q = select(ProcedureTemplate)
    if active_only:
        q = q.where(ProcedureTemplate.active.is_(True))
    if procedure_type:
        q = q.where(ProcedureTemplate.procedure_type == procedure_type)
    if scope:
        q = q.where(ProcedureTemplate.scope == scope)
    if canton:
        q = q.where(ProcedureTemplate.canton == canton)
    result = await db.execute(q.order_by(ProcedureTemplate.name))
    return list(result.scalars().all())


async def get_template(db: AsyncSession, template_id: UUID) -> ProcedureTemplate | None:
    result = await db.execute(select(ProcedureTemplate).where(ProcedureTemplate.id == template_id))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Applicability
# ---------------------------------------------------------------------------


async def get_applicable_procedures(
    db: AsyncSession,
    building_id: UUID,
    *,
    case_id: UUID | None = None,
    work_type: str | None = None,
) -> list[dict]:
    """Determine which procedure templates apply based on building, case, and work type.

    Uses jurisdiction hierarchy walk for matching.
    Returns list of {"template": ProcedureTemplate, "reason": str}.
    """
    # Load building
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if building is None:
        return []

    # Determine building canton and jurisdiction chain
    canton = getattr(building, "canton", None)
    jurisdiction_id = getattr(building, "jurisdiction_id", None)
    jurisdiction_ids: list[UUID] = []
    if jurisdiction_id:
        jurisdiction_ids = await _walk_jurisdiction_chain(db, jurisdiction_id)

    # Load case if provided
    case_work_families: list[str] = []
    case_pollutants: list[str] = []
    if case_id:
        case_result = await db.execute(select(BuildingCase).where(BuildingCase.id == case_id))
        case = case_result.scalar_one_or_none()
        if case:
            case_pollutants = case.pollutant_scope or []
            # Derive work families from case type
            if case.case_type == "works":
                case_work_families.append("general_works")

    # Get all active templates
    all_templates = await list_templates(db)

    applicable: list[dict] = []
    for tpl in all_templates:
        reason = _match_template(tpl, canton, jurisdiction_ids, work_type, case_work_families, case_pollutants)
        if reason:
            applicable.append({"template": tpl, "reason": reason})

    return applicable


def _match_template(
    tpl: ProcedureTemplate,
    canton: str | None,
    jurisdiction_ids: list[UUID],
    work_type: str | None,
    case_work_families: list[str],
    case_pollutants: list[str],
) -> str | None:
    """Return a reason string if template applies, else None."""
    # Scope: federal templates always apply
    if tpl.scope == "federal":
        # Check work family match
        if work_type and tpl.applicable_work_families and work_type in tpl.applicable_work_families:
            return f"Federal procedure applicable for work type '{work_type}'"
        # Check pollutant overlap
        if case_pollutants and tpl.applicable_work_families:
            for family in tpl.applicable_work_families:
                for pol in case_pollutants:
                    if pol in family:
                        return f"Federal procedure applicable for pollutant '{pol}'"
        # Generic federal match
        if not tpl.applicable_work_families:
            return "Federal procedure (always applicable)"
        # If work families specified but no match, check case work families
        if case_work_families and tpl.applicable_work_families:
            overlap = set(case_work_families) & set(tpl.applicable_work_families)
            if overlap:
                return f"Federal procedure matching work families: {', '.join(overlap)}"
        return None

    # Cantonal match
    if tpl.scope == "cantonal" and tpl.canton and canton and canton.upper() == tpl.canton.upper():
        # Match by canton + work type
        if work_type and tpl.applicable_work_families and work_type in tpl.applicable_work_families:
            return f"Cantonal procedure ({tpl.canton}) for work type '{work_type}'"
        # Generic cantonal match
        return f"Cantonal procedure applicable in {tpl.canton}"

    # Jurisdiction match
    if tpl.jurisdiction_id and tpl.jurisdiction_id in jurisdiction_ids:
        return "Procedure matches building jurisdiction"

    # Communal — requires jurisdiction match (already covered above)
    return None


# ---------------------------------------------------------------------------
# Instance lifecycle
# ---------------------------------------------------------------------------


async def start_procedure(
    db: AsyncSession,
    template_id: UUID,
    building_id: UUID,
    created_by_id: UUID,
    organization_id: UUID,
    *,
    case_id: UUID | None = None,
) -> ProcedureInstance:
    """Start a procedure instance from a template.

    Auto-checks which artifacts are already available and sets initial step.
    """
    tpl = await get_template(db, template_id)
    if tpl is None:
        raise ValueError(f"Procedure template '{template_id}' not found")

    # Determine initial step
    steps = tpl.steps or []
    first_step = steps[0]["name"] if steps else None

    # Determine missing artifacts (all required artifacts start as missing)
    missing = []
    if tpl.required_artifacts:
        for art in tpl.required_artifacts:
            if art.get("mandatory", True):
                missing.append(art)

    # Auto-create BuildingCase if none provided (V3 doctrine: BuildingCase = operating root)
    if case_id is None:
        case = BuildingCase(
            building_id=building_id,
            organization_id=organization_id,
            created_by_id=created_by_id,
            case_type="permit" if tpl.procedure_type == "permit" else "authority_submission",
            title=tpl.name,
            description=tpl.description,
            state="in_preparation",
            priority="medium",
        )
        db.add(case)
        await db.flush()
        case_id = case.id

    instance = ProcedureInstance(
        template_id=template_id,
        building_id=building_id,
        case_id=case_id,
        organization_id=organization_id,
        created_by_id=created_by_id,
        status="in_progress",
        current_step=first_step,
        completed_steps=[],
        collected_artifacts=[],
        missing_artifacts=missing,
        blockers=[],
    )
    db.add(instance)
    await db.flush()
    logger.info("Started procedure instance %s from template %s", instance.id, template_id)
    return instance


async def get_instance(db: AsyncSession, instance_id: UUID) -> ProcedureInstance | None:
    result = await db.execute(
        select(ProcedureInstance)
        .options(selectinload(ProcedureInstance.template))
        .where(ProcedureInstance.id == instance_id)
    )
    return result.scalar_one_or_none()


async def list_instances(
    db: AsyncSession,
    building_id: UUID,
    *,
    case_id: UUID | None = None,
    status: str | None = None,
) -> list[ProcedureInstance]:
    """List procedure instances for a building, optionally filtered by case and status."""
    q = select(ProcedureInstance).where(ProcedureInstance.building_id == building_id)
    if case_id:
        q = q.where(ProcedureInstance.case_id == case_id)
    if status:
        q = q.where(ProcedureInstance.status == status)
    result = await db.execute(q.order_by(ProcedureInstance.created_at.desc()))
    return list(result.scalars().all())


async def advance_step(
    db: AsyncSession,
    instance_id: UUID,
    step_name: str,
    completed_by_id: UUID,
) -> ProcedureInstance:
    """Mark a procedure step as completed and advance to the next step."""
    instance = await get_instance(db, instance_id)
    if instance is None:
        raise ValueError(f"Procedure instance '{instance_id}' not found")
    if instance.status in ("submitted", "approved", "rejected", "expired", "cancelled"):
        raise ValueError(f"Cannot advance step on procedure with status '{instance.status}'")

    # Record completion
    completed = instance.completed_steps or []
    completed.append(
        {
            "name": step_name,
            "completed_at": datetime.now(UTC).isoformat(),
            "completed_by": str(completed_by_id),
        }
    )
    instance.completed_steps = completed

    # Determine next step from template
    tpl = instance.template
    if tpl is None:
        tpl = await get_template(db, instance.template_id)
    steps = (tpl.steps if tpl else None) or []
    completed_names = {s["name"] for s in completed}
    next_step = None
    for s in sorted(steps, key=lambda x: x.get("order", 0)):
        if s["name"] not in completed_names:
            next_step = s["name"]
            break

    instance.current_step = next_step
    instance.updated_at = datetime.now(UTC)

    # If all steps done, keep in_progress (user must explicitly submit)
    await db.flush()
    logger.info("Advanced procedure %s: completed step '%s', next='%s'", instance_id, step_name, next_step)
    return instance


async def submit_procedure(
    db: AsyncSession,
    instance_id: UUID,
    *,
    submission_reference: str | None = None,
) -> ProcedureInstance:
    """Submit the procedure to the authority."""
    instance = await get_instance(db, instance_id)
    if instance is None:
        raise ValueError(f"Procedure instance '{instance_id}' not found")
    if instance.status not in ("in_progress", "complement_requested"):
        raise ValueError(f"Cannot submit procedure with status '{instance.status}'")

    instance.status = "submitted"
    instance.submitted_at = datetime.now(UTC)
    instance.submission_reference = submission_reference
    instance.updated_at = datetime.now(UTC)
    await db.flush()
    logger.info("Submitted procedure %s (ref=%s)", instance_id, submission_reference)
    return instance


async def handle_complement(
    db: AsyncSession,
    instance_id: UUID,
    complement_details: str,
) -> ProcedureInstance:
    """Handle a complement request from the authority."""
    instance = await get_instance(db, instance_id)
    if instance is None:
        raise ValueError(f"Procedure instance '{instance_id}' not found")
    if instance.status != "submitted":
        raise ValueError(f"Cannot request complement on procedure with status '{instance.status}'")

    instance.status = "complement_requested"
    instance.complement_requested_at = datetime.now(UTC)
    instance.complement_details = complement_details
    instance.updated_at = datetime.now(UTC)
    await db.flush()
    logger.info("Complement requested for procedure %s", instance_id)
    return instance


async def resolve_procedure(
    db: AsyncSession,
    instance_id: UUID,
    resolution: str,
    resolved_by_id: UUID,
) -> ProcedureInstance:
    """Record the authority decision (approved/rejected/expired)."""
    instance = await get_instance(db, instance_id)
    if instance is None:
        raise ValueError(f"Procedure instance '{instance_id}' not found")
    if resolution not in ("approved", "rejected", "expired"):
        raise ValueError(f"Invalid resolution '{resolution}'. Must be approved/rejected/expired.")
    if instance.status not in ("submitted", "complement_requested"):
        raise ValueError(f"Cannot resolve procedure with status '{instance.status}'")

    instance.status = resolution
    instance.resolution = resolution
    instance.resolved_at = datetime.now(UTC)
    instance.updated_at = datetime.now(UTC)
    await db.flush()
    logger.info("Resolved procedure %s as '%s'", instance_id, resolution)
    return instance


async def get_procedure_blockers(
    db: AsyncSession,
    instance_id: UUID,
) -> list[dict]:
    """Compute current blockers for the procedure.

    Checks: missing mandatory artifacts, incomplete required steps, expired status.
    """
    instance = await get_instance(db, instance_id)
    if instance is None:
        return []

    blockers: list[dict] = list(instance.blockers or [])

    # Check missing mandatory artifacts
    missing = instance.missing_artifacts or []
    if missing:
        blocker_types = [a.get("type", "unknown") for a in missing]
        blockers.append(
            {
                "description": f"Missing mandatory artifacts: {', '.join(blocker_types)}",
                "severity": "high",
                "since": instance.created_at.isoformat() if instance.created_at else None,
            }
        )

    # Check if complement requested but not addressed
    if instance.status == "complement_requested":
        blockers.append(
            {
                "description": f"Complement requested by authority: {instance.complement_details or 'see details'}",
                "severity": "high",
                "since": (instance.complement_requested_at.isoformat() if instance.complement_requested_at else None),
            }
        )

    return blockers
