"""BatiConnect — Remediation Intelligence API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.growth_stack import AIExtractionRead, ExtractionInput
from app.schemas.intelligence_stack import (
    AIPatternStats,
    AIRulePatternRead,
    FlywheelTrendPoint,
    ModuleLearningOverview,
    PassportNarrativeResponse,
    QuoteComparisonInsight,
    ReadinessAdvisorResponse,
    RemediationBenchmarkSnapshot,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Extractions
# ---------------------------------------------------------------------------


@router.post(
    "/extractions/quote",
    response_model=AIExtractionRead,
    status_code=201,
    tags=["Remediation Intelligence"],
)
async def extract_quote(
    body: ExtractionInput,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Extract structured data from a remediation quote via AI provider."""
    from app.services.ai_extraction_service import extract_quote_data

    log, _draft = await extract_quote_data(
        db,
        text=body.text,
        source_filename=body.source_filename,
        source_document_id=body.source_document_id,
    )
    await db.commit()
    await db.refresh(log)
    return log


@router.post(
    "/extractions/completion",
    response_model=AIExtractionRead,
    status_code=201,
    tags=["Remediation Intelligence"],
)
async def extract_completion(
    body: ExtractionInput,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Extract structured data from a completion report via AI provider."""
    from app.services.ai_extraction_service import extract_completion_data

    log, _draft = await extract_completion_data(
        db,
        text=body.text,
        source_filename=body.source_filename,
        source_document_id=body.source_document_id,
    )
    await db.commit()
    await db.refresh(log)
    return log


@router.post(
    "/extractions/certificate",
    response_model=AIExtractionRead,
    status_code=201,
    tags=["Remediation Intelligence"],
)
async def extract_certificate(
    body: ExtractionInput,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Extract structured data from a certificate/clearance document via AI provider."""
    from app.services.ai_extraction_service import extract_certificate_data

    log, _draft = await extract_certificate_data(
        db,
        input_text=body.text or body.source_filename or "",
        source_doc_id=body.source_document_id,
    )
    await db.commit()
    await db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# AI Patterns
# ---------------------------------------------------------------------------


@router.get(
    "/ai-patterns",
    response_model=list[AIRulePatternRead],
    tags=["Remediation Intelligence"],
)
async def list_patterns(
    pattern_type: str | None = Query(None),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """List active AI rule patterns."""
    from app.services.pattern_learning_service import get_patterns

    return await get_patterns(db, pattern_type_filter=pattern_type)


@router.get(
    "/ai-patterns/stats",
    response_model=AIPatternStats,
    tags=["Remediation Intelligence"],
)
async def pattern_stats(
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get AI pattern statistics."""
    from app.services.pattern_learning_service import get_pattern_stats

    stats = await get_pattern_stats(db)
    return AIPatternStats(**stats)


# ---------------------------------------------------------------------------
# Readiness Advisor
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/readiness-advisor",
    response_model=ReadinessAdvisorResponse,
    tags=["Remediation Intelligence"],
)
async def readiness_advisor(
    building_id: UUID,
    current_user: User = Depends(require_permission("readiness", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get readiness advisor suggestions for a building. Read-only."""
    from datetime import UTC, datetime

    from app.services.readiness_advisor_service import get_suggestions

    suggestions = await get_suggestions(db, building_id)
    return ReadinessAdvisorResponse(
        building_id=building_id,
        suggestions=suggestions,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Passport Narrative
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/passport-narrative",
    response_model=PassportNarrativeResponse,
    tags=["Remediation Intelligence"],
)
async def passport_narrative(
    building_id: UUID,
    audience: str = Query("owner", pattern="^(owner|authority|contractor)$"),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get structured passport narrative for a building."""
    from app.services.passport_narrative_service import generate_narrative

    return await generate_narrative(db, building_id, audience)


# ---------------------------------------------------------------------------
# Quote Comparison Insights
# ---------------------------------------------------------------------------


@router.get(
    "/marketplace/requests/{request_id}/comparison-insights",
    response_model=QuoteComparisonInsight,
    tags=["Remediation Intelligence"],
)
async def comparison_insights(
    request_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get quote comparison insights for a marketplace request. No ranking."""
    from app.services.quote_intelligence_service import get_comparison_insights

    return await get_comparison_insights(db, request_id)


# ---------------------------------------------------------------------------
# Remediation Benchmark
# ---------------------------------------------------------------------------


@router.get(
    "/organizations/{org_id}/remediation-benchmark",
    response_model=RemediationBenchmarkSnapshot,
    tags=["Remediation Intelligence"],
)
async def remediation_benchmark(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get remediation benchmark for an organization."""
    from app.services.remediation_intelligence_service import get_benchmark

    return await get_benchmark(db, org_id)


# ---------------------------------------------------------------------------
# Flywheel Trends
# ---------------------------------------------------------------------------


@router.get(
    "/organizations/{org_id}/flywheel-trends",
    response_model=list[FlywheelTrendPoint],
    tags=["Remediation Intelligence"],
)
async def flywheel_trends(
    org_id: UUID,
    days: int = Query(90, ge=7, le=365),
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Get flywheel trend time series for an organization."""
    from app.services.remediation_intelligence_service import get_flywheel_trends

    return await get_flywheel_trends(db, org_id, days)


# ---------------------------------------------------------------------------
# Module Learning Overview (admin)
# ---------------------------------------------------------------------------


@router.get(
    "/admin/module-learning-overview",
    response_model=ModuleLearningOverview,
    tags=["Remediation Intelligence"],
)
async def module_learning_overview(
    current_user: User = Depends(require_permission("audit_logs", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: module learning overview."""
    from app.services.remediation_intelligence_service import get_learning_overview

    return await get_learning_overview(db)
