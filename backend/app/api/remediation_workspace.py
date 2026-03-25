"""BatiConnect — Remediation Growth Stack API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.growth_stack import (
    AIExtractionRead,
    CompanyEligibilitySummary,
    CompanyWorkspaceSummary,
    CompletionClosureSummary,
    ExtractionCorrection,
    ExtractionInput,
    ExtractionRejection,
    FlywheelMetrics,
    OperatorRemediationQueue,
    QuoteComparisonMatrix,
    SubscriptionChangeRead,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Company workspace
# ---------------------------------------------------------------------------


@router.get(
    "/marketplace/companies/{profile_id}/workspace",
    response_model=CompanyWorkspaceSummary,
)
async def get_company_workspace_endpoint(
    profile_id: UUID,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.remediation_workspace_service import get_company_workspace

    ws = await get_company_workspace(db, profile_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Company profile not found")
    return ws


# ---------------------------------------------------------------------------
# Operator queue
# ---------------------------------------------------------------------------


@router.get(
    "/marketplace/operator/queue",
    response_model=OperatorRemediationQueue,
)
async def get_operator_queue_endpoint(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.remediation_workspace_service import get_operator_queue

    return await get_operator_queue(db, current_user.id, current_user.organization_id)


# ---------------------------------------------------------------------------
# Quote comparison matrix
# ---------------------------------------------------------------------------


@router.get(
    "/marketplace/requests/{request_id}/comparison-matrix",
    response_model=QuoteComparisonMatrix,
)
async def get_comparison_matrix_endpoint(
    request_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.remediation_workspace_service import get_quote_comparison_matrix

    return await get_quote_comparison_matrix(db, request_id)


# ---------------------------------------------------------------------------
# Completion closure summary
# ---------------------------------------------------------------------------


@router.get(
    "/marketplace/completions/{completion_id}/closure-summary",
    response_model=CompletionClosureSummary,
)
async def get_closure_summary_endpoint(
    completion_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.remediation_workspace_service import get_completion_closure_summary

    summary = await get_completion_closure_summary(db, completion_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Completion confirmation not found")
    return summary


# ---------------------------------------------------------------------------
# Subscription history
# ---------------------------------------------------------------------------


@router.get(
    "/marketplace/subscriptions/{subscription_id}/history",
    response_model=list[SubscriptionChangeRead],
)
async def get_subscription_history_endpoint(
    subscription_id: UUID,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select

    from app.models.subscription_change import SubscriptionChange

    result = await db.execute(
        select(SubscriptionChange)
        .where(SubscriptionChange.subscription_id == subscription_id)
        .order_by(SubscriptionChange.created_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Eligibility summary
# ---------------------------------------------------------------------------


@router.get(
    "/marketplace/companies/{profile_id}/eligibility-summary",
    response_model=CompanyEligibilitySummary,
)
async def get_eligibility_summary_endpoint(
    profile_id: UUID,
    current_user: User = Depends(require_permission("organizations", "read")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.marketplace_service import get_eligibility_summary

    result = await get_eligibility_summary(db, profile_id)
    return result


# ---------------------------------------------------------------------------
# AI Extraction endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/marketplace/extractions/quote",
    response_model=AIExtractionRead,
    status_code=201,
)
async def extract_quote_endpoint(
    payload: ExtractionInput,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.ai_extraction_service import extract_quote_data

    log, _draft = await extract_quote_data(
        db,
        text=payload.text,
        source_filename=payload.source_filename,
        source_document_id=payload.source_document_id,
    )
    await db.commit()
    return log


@router.post(
    "/marketplace/extractions/completion",
    response_model=AIExtractionRead,
    status_code=201,
)
async def extract_completion_endpoint(
    payload: ExtractionInput,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.ai_extraction_service import extract_completion_data

    log, _draft = await extract_completion_data(
        db,
        text=payload.text,
        source_filename=payload.source_filename,
        source_document_id=payload.source_document_id,
    )
    await db.commit()
    return log


@router.post(
    "/marketplace/extractions/{log_id}/confirm",
    response_model=AIExtractionRead,
)
async def confirm_extraction_endpoint(
    log_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.ai_extraction_service import confirm_extraction

    try:
        log = await confirm_extraction(db, log_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    await db.commit()
    return log


@router.post(
    "/marketplace/extractions/{log_id}/correct",
    response_model=AIExtractionRead,
)
async def correct_extraction_endpoint(
    log_id: UUID,
    payload: ExtractionCorrection,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.ai_extraction_service import correct_extraction

    try:
        log = await correct_extraction(db, log_id, payload.corrected_data, current_user.id, payload.notes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    await db.commit()
    return log


@router.post(
    "/marketplace/extractions/{log_id}/reject",
    response_model=AIExtractionRead,
)
async def reject_extraction_endpoint(
    log_id: UUID,
    payload: ExtractionRejection,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.ai_extraction_service import reject_extraction

    try:
        log = await reject_extraction(db, log_id, current_user.id, payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    await db.commit()
    return log


# ---------------------------------------------------------------------------
# Flywheel metrics (admin only)
# ---------------------------------------------------------------------------


@router.get(
    "/admin/remediation/flywheel-metrics",
    response_model=FlywheelMetrics,
)
async def get_flywheel_metrics_endpoint(
    current_user: User = Depends(require_permission("audit_logs", "read")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.flywheel_metrics_service import get_module_metrics

    return await get_module_metrics(db)
