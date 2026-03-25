"""BatiConnect — Fit evaluation service.

Evaluates whether an organization is a good fit for BatiConnect
based on observable product signals, not opaque scores.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.lease import Lease
from app.models.user import User
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.fit_evaluation import FitEvidence, FitResult


async def evaluate_fit(db: AsyncSession, org_id: UUID) -> FitResult:
    """Evaluate organization fit based on real workflow signals.

    Checks:
    1. Canonical building anchor — does the org manage at least one building?
    2. Real procedure/proof need — are there diagnostics or leases?
    3. Recurring habit potential — are there multiple users or buildings?
    4. ERP-replacement risk — too many financial/lease records suggest ERP overlap
    """
    evidence: list[FitEvidence] = []
    reasons: list[str] = []
    negative_count = 0

    # 1. Canonical building anchor: org has buildings via user ownership
    org_users = (await db.execute(select(User.id).where(User.organization_id == org_id))).scalars().all()

    building_count = 0
    if org_users:
        building_count = (
            await db.execute(select(func.count()).select_from(Building).where(Building.created_by.in_(org_users)))
        ).scalar() or 0

    has_buildings = building_count > 0
    evidence.append(
        FitEvidence(
            check="canonical_building_anchor",
            result=has_buildings,
            detail=f"Organization has {building_count} building(s) created by its members",
        )
    )
    if not has_buildings:
        reasons.append("No building anchor — org has no buildings yet")
        negative_count += 1

    # 2. Real procedure/proof need: diagnostics on org buildings, or workspace memberships
    diag_count = 0
    if org_users and building_count > 0:
        org_building_ids = (
            (await db.execute(select(Building.id).where(Building.created_by.in_(org_users)))).scalars().all()
        )
        if org_building_ids:
            diag_count = (
                await db.execute(
                    select(func.count()).select_from(Diagnostic).where(Diagnostic.building_id.in_(org_building_ids))
                )
            ).scalar() or 0

    ws_count = (
        await db.execute(
            select(func.count())
            .select_from(WorkspaceMembership)
            .where(WorkspaceMembership.organization_id == org_id, WorkspaceMembership.is_active.is_(True))
        )
    ).scalar() or 0

    has_proof_need = diag_count > 0 or ws_count > 0
    evidence.append(
        FitEvidence(
            check="real_procedure_proof_need",
            result=has_proof_need,
            detail=f"{diag_count} diagnostic(s), {ws_count} active workspace membership(s)",
        )
    )
    if not has_proof_need:
        reasons.append("No proof/procedure need detected — no diagnostics or workspace activity")
        negative_count += 1

    # 3. Recurring habit potential: multiple users or multiple buildings
    user_count = len(org_users)
    has_habit_potential = user_count >= 2 or building_count >= 2
    evidence.append(
        FitEvidence(
            check="recurring_habit_potential",
            result=has_habit_potential,
            detail=f"{user_count} user(s), {building_count} building(s) — multi-use potential {'yes' if has_habit_potential else 'no'}",
        )
    )
    if not has_habit_potential:
        reasons.append("Limited habit potential — single user, single building")
        negative_count += 1

    # 4. ERP-replacement risk: too many leases suggests they already have an ERP
    lease_count = 0
    if has_buildings:
        building_ids = (await db.execute(select(Building.id).where(Building.created_by.in_(org_users)))).scalars().all()
        if building_ids:
            lease_count = (
                await db.execute(select(func.count()).select_from(Lease).where(Lease.building_id.in_(building_ids)))
            ).scalar() or 0

    erp_risk = lease_count > 50
    evidence.append(
        FitEvidence(
            check="erp_replacement_risk",
            result=not erp_risk,
            detail=f"{lease_count} lease(s) — {'high ERP overlap risk' if erp_risk else 'overlay-safe'}",
        )
    )
    if erp_risk:
        reasons.append("ERP-replacement risk — high lease volume suggests existing ERP; position as overlay")
        negative_count += 1

    # Verdict
    if negative_count == 0:
        verdict = "good_fit"
        if not reasons:
            reasons.append("All fit checks passed — strong adoption candidate")
    elif negative_count <= 2:
        verdict = "pilot_slice"
        reasons.insert(0, "Partial fit — consider a pilot scope to validate value")
    else:
        verdict = "walk_away"
        reasons.insert(0, "Poor fit — most adoption signals are absent")

    return FitResult(
        organization_id=org_id,
        verdict=verdict,
        reasons=reasons,
        evidence=evidence,
    )
