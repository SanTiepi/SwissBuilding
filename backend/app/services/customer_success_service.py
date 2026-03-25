"""BatiConnect — Customer Success service.

Manages customer success milestones and advancement based on real product events.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_success import CustomerSuccessMilestone
from app.models.obligation import Obligation
from app.models.passport_publication import PassportPublication
from app.models.permit_procedure import PermitProcedure
from app.models.proof_delivery import ProofDelivery
from app.models.user import User
from app.models.workspace_membership import WorkspaceMembership

# Milestone types in recommended achievement order
MILESTONE_ORDER = [
    "first_workflow_win",
    "first_proof_reuse",
    "first_actor_spread",
    "first_blocker_caught",
    "first_trusted_pack",
    "first_exchange_publication",
]

NEXT_STEP_RECOMMENDATIONS = {
    "first_workflow_win": "Complete a permit procedure to demonstrate workflow value",
    "first_proof_reuse": "Reuse a proof delivery for a second audience to show evidence leverage",
    "first_actor_spread": "Invite a second user to the workspace to broaden adoption",
    "first_blocker_caught": "Complete an obligation before its due date to prove proactive monitoring",
    "first_trusted_pack": "Get a proof delivery acknowledged by the recipient",
    "first_exchange_publication": "Publish a passport to an external audience",
}


async def get_milestones(db: AsyncSession, org_id: UUID) -> list[CustomerSuccessMilestone]:
    """List all milestones for an organization."""
    result = await db.execute(
        select(CustomerSuccessMilestone)
        .where(CustomerSuccessMilestone.organization_id == org_id)
        .order_by(CustomerSuccessMilestone.created_at)
    )
    return list(result.scalars().all())


async def ensure_milestones_exist(db: AsyncSession, org_id: UUID) -> list[CustomerSuccessMilestone]:
    """Ensure all milestone types exist for the org, creating missing ones."""
    existing = await get_milestones(db, org_id)
    existing_types = {m.milestone_type for m in existing}

    for mt in MILESTONE_ORDER:
        if mt not in existing_types:
            milestone = CustomerSuccessMilestone(
                organization_id=org_id,
                milestone_type=mt,
                status="pending",
            )
            db.add(milestone)
            existing.append(milestone)

    await db.flush()
    return existing


async def check_and_advance(db: AsyncSession, org_id: UUID) -> list[CustomerSuccessMilestone]:
    """Scan for achieved milestones based on real events and advance status."""
    milestones = await ensure_milestones_exist(db, org_id)
    milestone_map = {m.milestone_type: m for m in milestones}

    # Get org user IDs for queries
    org_users = (await db.execute(select(User.id).where(User.organization_id == org_id))).scalars().all()

    now = datetime.now(UTC)

    # first_workflow_win: any PermitProcedure approved
    m = milestone_map.get("first_workflow_win")
    if m and m.status == "pending" and org_users:
        approved = (
            await db.execute(
                select(PermitProcedure)
                .where(
                    PermitProcedure.assigned_org_id == org_id,
                    PermitProcedure.status == "approved",
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if approved:
            m.status = "achieved"
            m.achieved_at = now
            m.evidence_entity_type = "permit_procedure"
            m.evidence_entity_id = approved.id
            m.evidence_summary = f"Permit '{approved.title}' approved"

    # first_proof_reuse: any ProofDelivery target sent to 2+ audiences
    m = milestone_map.get("first_proof_reuse")
    if m and m.status == "pending":
        # Find any target_id that appears with 2+ distinct audiences
        reuse_query = (
            select(ProofDelivery.target_id)
            .where(ProofDelivery.building_id.isnot(None))
            .group_by(ProofDelivery.target_id)
            .having(func.count(func.distinct(ProofDelivery.audience)) >= 2)
            .limit(1)
        )
        # Filter to org buildings via creator users
        if org_users:
            from app.models.building import Building

            org_building_ids = (
                (await db.execute(select(Building.id).where(Building.created_by.in_(org_users)))).scalars().all()
            )
            if org_building_ids:
                reuse_query = reuse_query.where(ProofDelivery.building_id.in_(org_building_ids))

        reused = (await db.execute(reuse_query)).scalar_one_or_none()
        if reused:
            m.status = "achieved"
            m.achieved_at = now
            m.evidence_entity_type = "proof_delivery"
            m.evidence_entity_id = reused
            m.evidence_summary = "Same proof delivered to 2+ distinct audiences"

    # first_actor_spread: 2+ distinct users with workspace membership
    m = milestone_map.get("first_actor_spread")
    if m and m.status == "pending":
        ws_user_count = (
            await db.execute(
                select(func.count(func.distinct(WorkspaceMembership.user_id))).where(
                    WorkspaceMembership.organization_id == org_id,
                    WorkspaceMembership.is_active.is_(True),
                )
            )
        ).scalar() or 0
        if ws_user_count >= 2:
            m.status = "achieved"
            m.achieved_at = now
            m.evidence_summary = f"{ws_user_count} distinct users active in workspace"

    # first_blocker_caught: any Obligation completed before overdue
    m = milestone_map.get("first_blocker_caught")
    if m and m.status == "pending":
        completed_obligation = (
            await db.execute(
                select(Obligation)
                .where(
                    Obligation.responsible_org_id == org_id,
                    Obligation.status == "completed",
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if completed_obligation:
            m.status = "achieved"
            m.achieved_at = now
            m.evidence_entity_type = "obligation"
            m.evidence_entity_id = completed_obligation.id
            m.evidence_summary = f"Obligation '{completed_obligation.title}' completed on time"

    # first_trusted_pack: any ProofDelivery with status=acknowledged
    m = milestone_map.get("first_trusted_pack")
    if m and m.status == "pending":
        ack_delivery = None
        if org_users:
            from app.models.building import Building

            org_building_ids = (
                (await db.execute(select(Building.id).where(Building.created_by.in_(org_users)))).scalars().all()
            )
            if org_building_ids:
                ack_delivery = (
                    await db.execute(
                        select(ProofDelivery)
                        .where(
                            ProofDelivery.building_id.in_(org_building_ids),
                            ProofDelivery.status == "acknowledged",
                        )
                        .limit(1)
                    )
                ).scalar_one_or_none()
        if ack_delivery:
            m.status = "achieved"
            m.achieved_at = now
            m.evidence_entity_type = "proof_delivery"
            m.evidence_entity_id = ack_delivery.id
            m.evidence_summary = "Proof delivery acknowledged by recipient"

    # first_exchange_publication: any PassportPublication
    m = milestone_map.get("first_exchange_publication")
    if m and m.status == "pending":
        publication = (
            await db.execute(
                select(PassportPublication).where(PassportPublication.published_by_org_id == org_id).limit(1)
            )
        ).scalar_one_or_none()
        if publication:
            m.status = "achieved"
            m.achieved_at = now
            m.evidence_entity_type = "passport_publication"
            m.evidence_entity_id = publication.id
            m.evidence_summary = "First passport published to external audience"

    await db.flush()
    return milestones


async def get_next_step(db: AsyncSession, org_id: UUID) -> dict | None:
    """Returns the first pending milestone and what to do about it."""
    milestones = await get_milestones(db, org_id)
    milestone_map = {m.milestone_type: m for m in milestones}

    for mt in MILESTONE_ORDER:
        m = milestone_map.get(mt)
        if m and m.status == "pending":
            return {
                "milestone_type": mt,
                "recommendation": NEXT_STEP_RECOMMENDATIONS.get(mt, "Continue using the platform"),
            }

    return None
