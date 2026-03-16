"""
SwissBuildingOS - Campaign Recommendation Service

Analyzes portfolio state and recommends the most impactful next campaigns
based on risk clusters, readiness gaps, documentation debt, and pollutant prevalence.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample


async def recommend_campaigns(
    db: AsyncSession,
    owner_id: UUID | None = None,
    limit: int = 5,
) -> list[dict]:
    """
    Analyze portfolio state and recommend the most impactful next campaigns.

    Returns a ranked list of campaign recommendations, each with:
      - campaign_type, title, description, priority
      - building_ids: list of target buildings
      - rationale: why this campaign is recommended
      - impact_score: 0.0-1.0 estimated impact
    """
    recommendations: list[dict] = []

    # Gather portfolio intelligence
    buildings = await _get_portfolio_buildings(db, owner_id)
    if not buildings:
        return []

    building_ids = [b.id for b in buildings]

    # Run all analyzers
    diag_rec = await _analyze_diagnostic_gaps(db, buildings)
    if diag_rec:
        recommendations.append(diag_rec)

    risk_rec = await _analyze_risk_clusters(db, building_ids)
    if risk_rec:
        recommendations.append(risk_rec)

    action_rec = await _analyze_open_actions(db, building_ids)
    if action_rec:
        recommendations.append(action_rec)

    doc_rec = await _analyze_documentation_debt(db, building_ids)
    if doc_rec:
        recommendations.append(doc_rec)

    pollutant_recs = await _analyze_pollutant_prevalence(db, building_ids)
    recommendations.extend(pollutant_recs)

    # Sort by impact_score descending, take top N
    recommendations.sort(key=lambda r: r.get("impact_score", 0), reverse=True)
    return recommendations[:limit]


# ---------------------------------------------------------------------------
# Portfolio query
# ---------------------------------------------------------------------------


async def _get_portfolio_buildings(
    db: AsyncSession,
    owner_id: UUID | None,
) -> list[Building]:
    """Get all buildings in the portfolio scope."""
    query = select(Building)
    if owner_id:
        query = query.where(Building.owner_id == owner_id)
    result = await db.execute(query)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Analyzers
# ---------------------------------------------------------------------------


async def _analyze_diagnostic_gaps(
    db: AsyncSession,
    buildings: list[Building],
) -> dict | None:
    """Find buildings that need diagnostics but don't have one."""
    # Buildings pre-1991 without a completed/validated diagnostic
    pre_1991 = [b for b in buildings if b.construction_year and b.construction_year < 1991]
    if not pre_1991:
        return None

    pre_1991_ids = [b.id for b in pre_1991]

    # Find which ones have completed diagnostics
    result = await db.execute(
        select(Diagnostic.building_id)
        .where(
            Diagnostic.building_id.in_(pre_1991_ids),
            Diagnostic.status.in_(["completed", "validated"]),
        )
        .distinct()
    )
    diagnosed_ids = set(result.scalars().all())

    undiagnosed = [b for b in pre_1991 if b.id not in diagnosed_ids]
    if not undiagnosed:
        return None

    return {
        "campaign_type": "diagnostic",
        "title": f"Diagnostic polluants — {len(undiagnosed)} bâtiments pré-1991",
        "description": (
            f"{len(undiagnosed)} bâtiments construits avant 1991 n'ont pas encore "
            f"de diagnostic polluants complété. Un diagnostic avant travaux (AvT) "
            f"est requis réglementairement."
        ),
        "priority": "high" if len(undiagnosed) > 5 else "medium",
        "building_ids": [str(b.id) for b in undiagnosed],
        "rationale": "regulatory_gap",
        "impact_score": min(0.95, 0.5 + len(undiagnosed) * 0.05),
    }


async def _analyze_risk_clusters(
    db: AsyncSession,
    building_ids: list[UUID],
) -> dict | None:
    """Find buildings with critical/high risk that need remediation campaigns."""
    result = await db.execute(
        select(BuildingRiskScore).where(
            BuildingRiskScore.building_id.in_(building_ids),
            BuildingRiskScore.overall_risk_level.in_(["critical", "high"]),
        )
    )
    high_risk = list(result.scalars().all())

    if not high_risk:
        return None

    critical_count = sum(1 for r in high_risk if r.overall_risk_level == "critical")

    return {
        "campaign_type": "remediation",
        "title": f"Assainissement prioritaire — {len(high_risk)} bâtiments à risque élevé",
        "description": (
            f"{len(high_risk)} bâtiments présentent un risque élevé ou critique "
            f"({critical_count} critiques). Une campagne d'assainissement coordonnée "
            f"permettrait de réduire l'exposition."
        ),
        "priority": "critical" if critical_count > 0 else "high",
        "building_ids": [str(r.building_id) for r in high_risk],
        "rationale": "risk_cluster",
        "impact_score": min(0.98, 0.6 + critical_count * 0.1),
    }


async def _analyze_open_actions(
    db: AsyncSession,
    building_ids: list[UUID],
) -> dict | None:
    """Find portfolios with many open high-priority actions needing coordination."""
    result = await db.execute(
        select(
            ActionItem.building_id,
            func.count(ActionItem.id).label("action_count"),
        )
        .where(
            ActionItem.building_id.in_(building_ids),
            ActionItem.status.in_(["open", "in_progress"]),
            ActionItem.priority.in_(["critical", "high"]),
        )
        .group_by(ActionItem.building_id)
    )
    rows = result.all()

    if not rows:
        return None

    total_actions = sum(r.action_count for r in rows)
    building_count = len(rows)

    if total_actions < 3:
        return None

    return {
        "campaign_type": "remediation",
        "title": f"Actions prioritaires — {total_actions} actions ouvertes sur {building_count} bâtiments",
        "description": (
            f"{total_actions} actions de priorité haute ou critique sont ouvertes "
            f"sur {building_count} bâtiments. Une campagne coordonnée optimiserait "
            f"les interventions et réduirait les coûts."
        ),
        "priority": "high",
        "building_ids": [str(r.building_id) for r in rows],
        "rationale": "action_backlog",
        "impact_score": min(0.85, 0.4 + total_actions * 0.03),
    }


async def _analyze_documentation_debt(
    db: AsyncSession,
    building_ids: list[UUID],
) -> dict | None:
    """Find buildings with diagnostics but missing documentation."""
    # Buildings that have diagnostics but no documents
    result = await db.execute(
        select(Diagnostic.building_id)
        .where(
            Diagnostic.building_id.in_(building_ids),
            Diagnostic.status.in_(["completed", "validated"]),
        )
        .distinct()
    )
    diagnosed_ids = set(result.scalars().all())

    if not diagnosed_ids:
        return None

    from app.models.document import Document

    result = await db.execute(
        select(Document.building_id).where(Document.building_id.in_(list(diagnosed_ids))).distinct()
    )
    documented_ids = set(result.scalars().all())

    undocumented = diagnosed_ids - documented_ids
    if not undocumented:
        return None

    return {
        "campaign_type": "documentation",
        "title": f"Mise à jour documentaire — {len(undocumented)} bâtiments sans rapport",
        "description": (
            f"{len(undocumented)} bâtiments ont un diagnostic complété mais aucun "
            f"document de rapport. Les dossiers restent incomplets sans documentation."
        ),
        "priority": "medium",
        "building_ids": [str(bid) for bid in undocumented],
        "rationale": "documentation_debt",
        "impact_score": min(0.70, 0.3 + len(undocumented) * 0.04),
    }


async def _analyze_pollutant_prevalence(
    db: AsyncSession,
    building_ids: list[UUID],
) -> list[dict]:
    """Find pollutants with high positive rates that need targeted campaigns."""
    result = await db.execute(
        select(
            Sample.pollutant_type,
            func.count(Sample.id).label("total"),
            func.sum(case((Sample.threshold_exceeded.is_(True), 1), else_=0)).label("positive"),
        )
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            Diagnostic.building_id.in_(building_ids),
            Sample.threshold_exceeded.isnot(None),
        )
        .group_by(Sample.pollutant_type)
    )
    rows = result.all()

    recommendations: list[dict] = []
    pollutant_labels = {
        "asbestos": "amiante",
        "pcb": "PCB",
        "lead": "plomb",
        "hap": "HAP",
        "radon": "radon",
    }

    for row in rows:
        positive = row.positive or 0
        total = row.total or 1
        rate = positive / total

        if rate < 0.3 or positive < 2:
            continue

        label = pollutant_labels.get(row.pollutant_type, row.pollutant_type)
        recommendations.append(
            {
                "campaign_type": "remediation",
                "title": f"Campagne {label} — taux de positivité {rate:.0%}",
                "description": (
                    f"{positive}/{total} échantillons de {label} sont positifs "
                    f"(taux {rate:.0%}). Une campagne ciblée de gestion du {label} "
                    f"pourrait être nécessaire."
                ),
                "priority": "high" if rate > 0.5 else "medium",
                "building_ids": [],  # Would need a subquery to find specific buildings
                "rationale": "pollutant_prevalence",
                "pollutant_type": row.pollutant_type,
                "impact_score": min(0.80, 0.3 + rate * 0.5),
            }
        )

    return recommendations
