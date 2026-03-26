"""BatiConnect — Indispensability API routes.

Endpoints that quantify the platform's value: fragmentation, defensibility,
counterfactual simulation, portfolio-level summary, and score explainability.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building import Building
from app.models.user import User
from app.schemas.indispensability import (
    BuildingIndispensabilitySummary,
    DefensibilityResult,
    FragmentationResult,
    IndispensabilityReport,
    PortfolioIndispensabilitySummary,
)
from app.schemas.score_explainability import ExplainedReport
from app.schemas.value_ledger import IndispensabilityExport, PortfolioIndispensabilityExport
from app.services.counterfactual_service import simulate_without_platform
from app.services.defensibility_service import compute_defensibility
from app.services.fragmentation_score_service import compute_fragmentation_score
from app.services.indispensability_export_service import (
    generate_indispensability_export,
    generate_portfolio_indispensability_export,
)

router = APIRouter()


@router.get("/buildings/{building_id}/indispensability", response_model=IndispensabilityReport)
async def get_indispensability_report(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Full indispensability report: fragmentation + defensibility + counterfactual."""
    from datetime import UTC, datetime

    fragmentation = await compute_fragmentation_score(db, building_id)
    if fragmentation is None:
        raise HTTPException(status_code=404, detail="Building not found")

    defensibility = await compute_defensibility(db, building_id)
    if defensibility is None:
        raise HTTPException(status_code=404, detail="Building not found")

    counterfactual = await simulate_without_platform(db, building_id)
    if counterfactual is None:
        raise HTTPException(status_code=404, detail="Building not found")

    # Compose compelling French headline
    headline = _compose_headline(fragmentation, defensibility)

    return IndispensabilityReport(
        building_id=building_id,
        generated_at=datetime.now(UTC),
        fragmentation=fragmentation,
        defensibility=defensibility,
        counterfactual=counterfactual,
        headline=headline,
    )


@router.get("/buildings/{building_id}/fragmentation", response_model=FragmentationResult)
async def get_fragmentation(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Fragmentation score: how scattered truth would be without BatiConnect."""
    result = await compute_fragmentation_score(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get("/buildings/{building_id}/defensibility", response_model=DefensibilityResult)
async def get_defensibility(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Defensibility assessment: how provable decisions are."""
    result = await compute_defensibility(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/organizations/{org_id}/indispensability-summary",
    response_model=PortfolioIndispensabilitySummary,
)
async def get_portfolio_indispensability(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Portfolio-level indispensability summary: avg scores, worst buildings."""
    # Load all buildings for the organization
    buildings_result = await db.execute(select(Building).where(Building.organization_id == org_id))
    buildings = list(buildings_result.scalars().all())

    if not buildings:
        raise HTTPException(status_code=404, detail="Organization not found or has no buildings")

    summaries: list[BuildingIndispensabilitySummary] = []

    for b in buildings:
        frag = await compute_fragmentation_score(db, b.id)
        defn = await compute_defensibility(db, b.id)

        frag_score = frag.fragmentation_score if frag else 0.0
        def_score = defn.without_us_scenario.defensibility_score if defn else 0.0

        summaries.append(
            BuildingIndispensabilitySummary(
                building_id=b.id,
                address=b.address,
                fragmentation_score=frag_score,
                defensibility_score=def_score,
            )
        )

    avg_frag = round(sum(s.fragmentation_score for s in summaries) / len(summaries), 1)
    avg_def = round(sum(s.defensibility_score for s in summaries) / len(summaries), 4)

    # Worst 5 by fragmentation (highest = most fragmented without us)
    worst_frag = sorted(summaries, key=lambda s: s.fragmentation_score, reverse=True)[:5]
    # Worst 5 by defensibility (lowest = least defensible)
    worst_def = sorted(summaries, key=lambda s: s.defensibility_score)[:5]

    return PortfolioIndispensabilitySummary(
        organization_id=org_id,
        buildings_count=len(summaries),
        avg_fragmentation_score=avg_frag,
        avg_defensibility_score=avg_def,
        worst_fragmentation=worst_frag,
        worst_defensibility=worst_def,
    )


# ---------------------------------------------------------------------------
# Headline composer
# ---------------------------------------------------------------------------


def _compose_headline(
    frag: FragmentationResult,
    defn: DefensibilityResult,
) -> str:
    """Compose a compelling French one-liner summary."""
    sources = frag.source_dispersion.sources_unified
    contradictions = frag.contradiction_value.contradictions_detected
    proof_chains = frag.proof_chain_integrity.proof_chains_count
    def_score = defn.without_us_scenario.defensibility_score
    snapshots = defn.temporal_defensibility.snapshots_count

    parts: list[str] = []

    if sources >= 4:
        parts.append(f"{sources} sources unifiées en une seule vérité")
    elif sources >= 2:
        parts.append(f"{sources} sources consolidées")

    if contradictions > 0:
        parts.append(f"{contradictions} contradiction(s) détectée(s)")

    if proof_chains > 0:
        parts.append(f"{proof_chains} preuve(s) chaînée(s)")

    if def_score > 0:
        parts.append(f"{def_score:.0%} de décisions défendables")

    if snapshots > 0:
        parts.append(f"mémoire sur {defn.temporal_defensibility.time_coverage_days}j")

    if parts:
        joined = ", ".join(parts)
        return f"BatiConnect pour ce bâtiment : {joined}."

    return (
        "BatiConnect est prêt à unifier les données de ce bâtiment. "
        "Chaque source importée renforce la vérité consolidée."
    )


# ---------------------------------------------------------------------------
# Indispensability export endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/indispensability-export",
    response_model=IndispensabilityExport,
)
async def get_building_indispensability_export(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Exportable indispensability report for a single building."""
    result = await generate_indispensability_export(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result


@router.get(
    "/organizations/{org_id}/indispensability-export",
    response_model=PortfolioIndispensabilityExport,
)
async def get_portfolio_indispensability_export(
    org_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Exportable indispensability report for a portfolio."""
    result = await generate_portfolio_indispensability_export(db, org_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Organization not found or has no buildings")
    return result


# ---------------------------------------------------------------------------
# Score Explainability
# ---------------------------------------------------------------------------


@router.get(
    "/buildings/{building_id}/score-explainability",
    response_model=ExplainedReport,
)
async def get_score_explainability(
    building_id: UUID,
    current_user: User = Depends(require_permission("buildings", "read")),
    db: AsyncSession = Depends(get_db),
):
    """Full explainability report: every metric traced to its source items."""
    from app.services.score_explainability_service import explain_building_scores

    result = await explain_building_scores(db, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Building not found")
    return result
