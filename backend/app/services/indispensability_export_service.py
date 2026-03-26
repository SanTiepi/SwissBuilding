"""
BatiConnect — Indispensability Export Service

Generates structured export reports combining fragmentation, defensibility,
counterfactual, and value ledger data into French narratives.

Two scopes:
- Building-level: single building deep-dive
- Portfolio-level: org-wide aggregation
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.organization import Organization
from app.schemas.value_ledger import (
    IndispensabilityExport,
    IndispensabilitySection,
    PortfolioIndispensabilityExport,
)
from app.services.indispensability_service import (
    compute_counterfactual,
    compute_defensibility_score,
    compute_fragmentation_score,
)
from app.services.value_ledger_service import get_value_ledger

logger = logging.getLogger(__name__)


async def generate_indispensability_export(
    db: AsyncSession,
    building_id: UUID,
    org_id: UUID | None = None,
) -> IndispensabilityExport | None:
    """Generate a full indispensability export for a single building.

    If org_id is not provided, it is inferred from the building.
    """
    building = await db.get(Building, building_id)
    if not building:
        return None

    if org_id is None:
        org_id = building.organization_id

    address = building.address or "Adresse inconnue"

    fragmentation = await compute_fragmentation_score(db, building_id)
    defensibility = await compute_defensibility_score(db, building_id)
    counterfactual = await compute_counterfactual(db, building_id)
    ledger = await get_value_ledger(db, org_id)

    frag_score = fragmentation["fragmentation_score"]
    def_score = defensibility["defensibility_score"]
    hours_saved = ledger.hours_saved_estimate if ledger else 0.0
    value_chf = ledger.value_chf_estimate if ledger else 0.0

    executive_summary = (
        f"Ce rapport démontre la valeur apportée par SwissBuilding pour le bâtiment "
        f"situé au {address}. La fragmentation des données est évaluée à {frag_score}%, "
        f"la défensibilité des décisions à {def_score:.0%}. "
        f"La valeur cumulée estimée est de {value_chf} CHF."
    )

    recommendation = (
        f"SwissBuilding est indispensable pour maintenir la traçabilité et la conformité "
        f"réglementaire de ce bâtiment. Le retour à des outils fragmentés engendrerait "
        f"une perte estimée à {hours_saved} heures de travail consolidé."
    )

    return IndispensabilityExport(
        title=f"Rapport d'indispensabilité — {address}",
        generated_at=datetime.now(UTC),
        generated_by="SwissBuilding",
        executive_summary=executive_summary,
        fragmentation_section=IndispensabilitySection(
            title="Fragmentation des données",
            narrative=(
                f"Score de fragmentation: {frag_score}%. "
                f"{fragmentation['sources_unified']} sources unifiées, "
                f"{fragmentation['documents_with_provenance']} documents avec provenance."
            ),
            metrics={
                "fragmentation_score": frag_score,
                "sources_unified": fragmentation["sources_unified"],
                "documents_with_provenance": fragmentation["documents_with_provenance"],
                "contradictions_detected": fragmentation["contradictions_detected"],
            },
        ),
        defensibility_section=IndispensabilitySection(
            title="Défensibilité décisionnelle",
            narrative=(
                f"Score de défensibilité: {def_score}. "
                f"{defensibility['decisions_tracked']} décisions tracées sur "
                f"{defensibility['time_coverage_days']} jours."
            ),
            metrics={
                "defensibility_score": def_score,
                "decisions_tracked": defensibility["decisions_tracked"],
                "time_coverage_days": defensibility["time_coverage_days"],
            },
        ),
        counterfactual_section=IndispensabilitySection(
            title="Analyse contrefactuelle",
            narrative=(
                f"Sans la plateforme: confiance {counterfactual['without_platform']['trust']}, "
                f"grade {counterfactual['without_platform']['grade']}. "
                f"Avec la plateforme: confiance {counterfactual['with_platform']['trust']}, "
                f"grade {counterfactual['with_platform']['grade']}."
            ),
            metrics={
                "cost_of_fragmentation": counterfactual["cost_of_fragmentation"],
            },
        ),
        value_ledger_section=IndispensabilitySection(
            title="Registre de valeur cumulée",
            narrative=f"Valeur estimée: {value_chf} CHF ({hours_saved} heures économisées).",
            metrics={
                "hours_saved_estimate": hours_saved,
                "value_chf_estimate": value_chf,
                "days_active": ledger.days_active if ledger else 0,
            },
        ),
        recommendation=recommendation,
    )


async def generate_portfolio_indispensability_export(
    db: AsyncSession,
    org_id: UUID,
    building_ids: list[UUID] | None = None,
) -> PortfolioIndispensabilityExport | None:
    """Build an aggregated indispensability export for a portfolio.

    If building_ids is not provided, all buildings for the org are used.
    """
    org = await db.get(Organization, org_id)
    if not org:
        return None

    org_name = org.name or "Organisation"

    # If no building_ids provided, get all buildings for the org
    if building_ids is None:
        from sqlalchemy import select as sa_select

        result = await db.execute(sa_select(Building.id).where(Building.organization_id == org_id))
        building_ids = [r[0] for r in result.all()]

    if not building_ids:
        return None

    all_frag = []
    all_def = []
    total_docs = 0
    for bid in building_ids:
        f = await compute_fragmentation_score(db, bid)
        d = await compute_defensibility_score(db, bid)
        all_frag.append(f)
        all_def.append(d)
        total_docs += f["documents_with_provenance"]

    n = len(building_ids)
    avg_frag = round(sum(f["fragmentation_score"] for f in all_frag) / n, 1)
    avg_def = round(sum(d["defensibility_score"] for d in all_def) / n, 3)

    ledger = await get_value_ledger(db, org_id)
    hours_saved = ledger.hours_saved_estimate if ledger else 0.0
    value_chf = ledger.value_chf_estimate if ledger else 0.0

    executive_summary = (
        f"Ce rapport couvre {n} bâtiments du portefeuille {org_name}. "
        f"La fragmentation moyenne est de {avg_frag}%, "
        f"la défensibilité moyenne de {avg_def:.0%}. "
        f"SwissBuilding a sécurisé {total_docs} documents au total."
    )

    recommendation = (
        f"SwissBuilding est essentiel pour la gestion consolidée de ce portefeuille "
        f"de {n} bâtiments. La valeur cumulée estimée est de {value_chf} CHF."
    )

    total_cost = 0.0
    for bid in building_ids:
        cf = await compute_counterfactual(db, bid)
        total_cost += cf["cost_of_fragmentation"]

    return PortfolioIndispensabilityExport(
        title=f"Rapport d'indispensabilité — Portefeuille {org_name}",
        generated_at=datetime.now(UTC),
        generated_by="SwissBuilding",
        executive_summary=executive_summary,
        buildings_count=n,
        fragmentation_section=IndispensabilitySection(
            title="Fragmentation des données",
            narrative=f"Fragmentation moyenne: {avg_frag}% sur {n} bâtiments.",
            metrics={"avg_fragmentation": avg_frag},
        ),
        defensibility_section=IndispensabilitySection(
            title="Défensibilité décisionnelle",
            narrative=f"Défensibilité moyenne: {avg_def} sur {n} bâtiments.",
            metrics={"avg_defensibility": avg_def},
        ),
        counterfactual_section=IndispensabilitySection(
            title="Analyse contrefactuelle",
            narrative=f"Coût total de fragmentation estimé: {total_cost}.",
            metrics={"total_cost_of_fragmentation": total_cost},
        ),
        value_ledger_section=IndispensabilitySection(
            title="Registre de valeur cumulée",
            narrative=f"Valeur estimée: {value_chf} CHF ({hours_saved} heures économisées).",
            metrics={
                "hours_saved_estimate": hours_saved,
                "value_chf_estimate": value_chf,
            },
        ),
        recommendation=recommendation,
    )


# Aliases for backward compatibility
build_indispensability_export = generate_indispensability_export
build_portfolio_indispensability_export = generate_portfolio_indispensability_export
