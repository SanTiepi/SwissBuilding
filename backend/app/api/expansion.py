"""BatiConnect — Expansion signals, fit evaluation, and customer success API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.expansion_signal import (
    AccountExpansionTrigger,
    ExpansionOpportunity,
)
from app.models.organization import Organization
from app.models.user import User
from app.schemas.expansion import (
    AccountExpansionTriggerRead,
    CustomerSuccessMilestoneRead,
    CustomerSuccessReport,
    ExpansionOpportunityAction,
    ExpansionOpportunityRead,
    NextStepInfo,
)
from app.schemas.fit_evaluation import FitResult
from app.services.customer_success_service import check_and_advance, get_milestones, get_next_step
from app.services.fit_evaluation_service import evaluate_fit

router = APIRouter()


async def _get_org_or_404(db: AsyncSession, org_id: UUID) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get(
    "/organizations/{org_id}/expansion-triggers",
    response_model=list[AccountExpansionTriggerRead],
)
async def list_expansion_triggers(
    org_id: UUID,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_org_or_404(db, org_id)
    result = await db.execute(
        select(AccountExpansionTrigger)
        .where(AccountExpansionTrigger.organization_id == org_id)
        .order_by(AccountExpansionTrigger.detected_at.desc())
    )
    return result.scalars().all()


@router.get(
    "/organizations/{org_id}/expansion-opportunities",
    response_model=list[ExpansionOpportunityRead],
)
async def list_expansion_opportunities(
    org_id: UUID,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_org_or_404(db, org_id)
    result = await db.execute(
        select(ExpansionOpportunity)
        .where(ExpansionOpportunity.organization_id == org_id)
        .order_by(ExpansionOpportunity.detected_at.desc())
    )
    return result.scalars().all()


@router.post(
    "/expansion-opportunities/{opp_id}/act",
    response_model=ExpansionOpportunityRead,
)
async def act_on_opportunity(
    opp_id: UUID,
    payload: ExpansionOpportunityAction,
    current_user: User = Depends(require_permission("organizations", "update")),
    db: AsyncSession = Depends(get_db),
):
    from datetime import UTC, datetime

    result = await db.execute(select(ExpansionOpportunity).where(ExpansionOpportunity.id == opp_id))
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Expansion opportunity not found")
    if opp.status not in ("detected", "qualified"):
        raise HTTPException(status_code=400, detail=f"Cannot act on opportunity with status '{opp.status}'")

    opp.status = "acted"
    opp.acted_at = datetime.now(UTC)
    if payload.notes:
        opp.notes = payload.notes
    await db.commit()
    await db.refresh(opp)
    return opp


@router.post(
    "/expansion-opportunities/{opp_id}/dismiss",
    response_model=ExpansionOpportunityRead,
)
async def dismiss_opportunity(
    opp_id: UUID,
    payload: ExpansionOpportunityAction,
    current_user: User = Depends(require_permission("organizations", "update")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ExpansionOpportunity).where(ExpansionOpportunity.id == opp_id))
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Expansion opportunity not found")
    if opp.status not in ("detected", "qualified"):
        raise HTTPException(status_code=400, detail=f"Cannot dismiss opportunity with status '{opp.status}'")

    opp.status = "dismissed"
    if payload.notes:
        opp.notes = payload.notes
    await db.commit()
    await db.refresh(opp)
    return opp


@router.get(
    "/organizations/{org_id}/fit-evaluation",
    response_model=FitResult,
)
async def get_fit_evaluation(
    org_id: UUID,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_org_or_404(db, org_id)
    return await evaluate_fit(db, org_id)


@router.get(
    "/organizations/{org_id}/customer-success",
    response_model=CustomerSuccessReport,
)
async def get_customer_success(
    org_id: UUID,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    await _get_org_or_404(db, org_id)
    # Advance milestones, then return report
    await check_and_advance(db, org_id)
    await db.commit()

    # Re-fetch to get clean state
    all_milestones = await get_milestones(db, org_id)
    next_step_data = await get_next_step(db, org_id)

    next_step = None
    if next_step_data:
        next_step = NextStepInfo(**next_step_data)

    return CustomerSuccessReport(
        organization_id=org_id,
        milestones=[CustomerSuccessMilestoneRead.model_validate(m) for m in all_milestones],
        next_step=next_step,
    )
