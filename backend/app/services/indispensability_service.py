"""
BatiConnect - Indispensability Service

Quantifies the platform's value by measuring:
1. Fragmentation score — how scattered/unreliable data would be without BatiConnect
2. Defensibility score — how well decisions are documented and traceable
3. Counterfactual analysis — what the building state would look like without the platform

These metrics support the "indispensability" narrative: once you use BatiConnect,
going back to spreadsheets/emails is unthinkable.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_snapshot import BuildingSnapshot
from app.models.data_quality_issue import DataQualityIssue
from app.models.document import Document
from app.models.enrichment_run import BuildingEnrichmentRun

# ---------------------------------------------------------------------------
# 1. Fragmentation Score
# ---------------------------------------------------------------------------

_SYSTEMS_REPLACED = [
    "Tableurs Excel / Google Sheets",
    "E-mails avec pièces jointes",
    "Dossiers papier / classeurs",
    "Archives physiques dispersées",
    "Rapports PDF non indexés",
    "Bases de données Access / FileMaker",
]


async def compute_fragmentation_score(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Compute how fragmented data would be without the platform.

    Returns a score 0-100 where 100 = totally fragmented (no data unified).
    Lower score = more data consolidated in BatiConnect.
    """
    building = await db.get(Building, building_id)
    if not building:
        return {
            "fragmentation_score": 100.0,
            "sources_unified": 0,
            "documents_with_provenance": 0,
            "contradictions_detected": 0,
            "systems_replaced": [],
        }

    # Count enrichment sources unified
    enrichment_q = (
        select(func.count())
        .select_from(BuildingEnrichmentRun)
        .where(
            BuildingEnrichmentRun.building_id == building_id,
            BuildingEnrichmentRun.status == "completed",
        )
    )
    sources_unified = (await db.execute(enrichment_q)).scalar() or 0

    # Count documents with content hash (provenance tracked)
    docs_q = (
        select(func.count())
        .select_from(Document)
        .where(
            Document.building_id == building_id,
        )
    )
    documents_with_provenance = (await db.execute(docs_q)).scalar() or 0

    # Count data quality issues detected (contradictions the platform found)
    dq_q = (
        select(func.count())
        .select_from(DataQualityIssue)
        .where(
            DataQualityIssue.building_id == building_id,
        )
    )
    contradictions_detected = (await db.execute(dq_q)).scalar() or 0

    # Compute fragmentation score: starts at 100, reduced by consolidation evidence
    score = 100.0
    if sources_unified > 0:
        score -= min(30.0, sources_unified * 10.0)
    if documents_with_provenance > 0:
        score -= min(30.0, documents_with_provenance * 5.0)
    if contradictions_detected > 0:
        # Detecting contradictions = platform adding value
        score -= min(20.0, contradictions_detected * 5.0)
    if building.construction_year:
        score -= 10.0  # Basic metadata captured
    if building.canton:
        score -= 10.0  # Jurisdiction context captured

    score = max(0.0, min(100.0, score))

    # Determine which systems are replaced based on data presence
    systems = []
    if sources_unified > 0:
        systems.extend(_SYSTEMS_REPLACED[:3])
    if documents_with_provenance > 0:
        systems.extend([s for s in _SYSTEMS_REPLACED[3:] if s not in systems])

    return {
        "fragmentation_score": round(score, 1),
        "sources_unified": sources_unified,
        "documents_with_provenance": documents_with_provenance,
        "contradictions_detected": contradictions_detected,
        "systems_replaced": systems,
    }


# ---------------------------------------------------------------------------
# 2. Defensibility Score
# ---------------------------------------------------------------------------


async def compute_defensibility_score(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Compute how defensible the building's decision trail is.

    Returns a score 0-1 where 1 = fully defensible (all decisions tracked,
    evidence linked, timeline complete).
    """
    building = await db.get(Building, building_id)
    if not building:
        return {
            "defensibility_score": 0.0,
            "decisions_tracked": 0,
            "time_coverage_days": 0,
            "vulnerability_points": [
                "Aucune donnée disponible pour ce bâtiment",
            ],
        }

    # Count action items (decisions / recommendations tracked)
    actions_q = (
        select(func.count())
        .select_from(ActionItem)
        .where(
            ActionItem.building_id == building_id,
        )
    )
    decisions_tracked = (await db.execute(actions_q)).scalar() or 0

    # Time coverage from snapshots
    snap_q = select(
        func.min(BuildingSnapshot.captured_at),
        func.max(BuildingSnapshot.captured_at),
    ).where(BuildingSnapshot.building_id == building_id)
    snap_result = (await db.execute(snap_q)).first()
    first_snap, last_snap = snap_result if snap_result else (None, None)

    time_coverage_days = 0
    if first_snap and last_snap:
        delta = last_snap - first_snap
        time_coverage_days = max(0, delta.days)

    # Vulnerability assessment
    vulnerability_points: list[str] = []
    if decisions_tracked == 0:
        vulnerability_points.append("Aucune décision documentée dans la plateforme")
    if time_coverage_days == 0:
        vulnerability_points.append("Pas d'historique temporel des états du bâtiment")

    docs_q = (
        select(func.count())
        .select_from(Document)
        .where(
            Document.building_id == building_id,
        )
    )
    doc_count = (await db.execute(docs_q)).scalar() or 0
    if doc_count == 0:
        vulnerability_points.append("Aucun document probatoire archivé")

    # Compute score
    score = 0.0
    if decisions_tracked > 0:
        score += min(0.4, decisions_tracked * 0.1)
    if time_coverage_days > 0:
        score += min(0.3, time_coverage_days / 365.0 * 0.3)
    if doc_count > 0:
        score += min(0.3, doc_count * 0.05)

    score = max(0.0, min(1.0, score))

    return {
        "defensibility_score": round(score, 3),
        "decisions_tracked": decisions_tracked,
        "time_coverage_days": time_coverage_days,
        "vulnerability_points": vulnerability_points,
    }


# ---------------------------------------------------------------------------
# 3. Counterfactual Analysis
# ---------------------------------------------------------------------------


async def compute_counterfactual(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Compare 'with platform' vs 'without platform' state.

    Without the platform: trust=0, grade=unknown, no provenance, no timeline.
    With the platform: actual computed state.
    """
    from app.services.passport_service import get_passport_summary

    # Without platform — always the same bleak picture
    without_platform = {
        "trust": 0.0,
        "grade": "unknown",
        "completeness": 0.0,
        "evidence_chain": False,
        "regulatory_readiness": False,
    }

    # With platform — actual state
    passport = await get_passport_summary(db, building_id)
    if passport:
        with_platform = {
            "trust": passport.get("overall_trust", 0.0),
            "grade": passport.get("grade", "F"),
            "completeness": passport.get("completeness", 0.0),
            "evidence_chain": passport.get("evidence_count", 0) > 0,
            "regulatory_readiness": passport.get("grade", "F") in ("A", "B"),
        }
    else:
        with_platform = {
            "trust": 0.0,
            "grade": "F",
            "completeness": 0.0,
            "evidence_chain": False,
            "regulatory_readiness": False,
        }

    # Delta analysis
    delta: list[str] = []
    if with_platform["trust"] > without_platform["trust"]:
        delta.append(f"Confiance: {without_platform['trust']} → {with_platform['trust']}")
    if with_platform["grade"] != without_platform["grade"]:
        delta.append(f"Grade: {without_platform['grade']} → {with_platform['grade']}")
    if with_platform["evidence_chain"]:
        delta.append("Chaîne de preuves: absente → établie")
    if with_platform["regulatory_readiness"]:
        delta.append("Conformité réglementaire: inconnue → vérifiée")
    if not delta:
        delta.append("Aucune donnée consolidée — valeur à construire")

    # Cost of fragmentation estimate (qualitative)
    frag = await compute_fragmentation_score(db, building_id)
    cost_of_fragmentation = round(frag["fragmentation_score"] * 0.01, 2)  # 0-1 scale

    return {
        "without_platform": without_platform,
        "with_platform": with_platform,
        "delta": delta,
        "cost_of_fragmentation": cost_of_fragmentation,
    }


# ---------------------------------------------------------------------------
# 4. Full Indispensability Report
# ---------------------------------------------------------------------------


async def get_indispensability_report(
    db: AsyncSession,
    building_id: UUID,
) -> dict:
    """Full indispensability report combining all 3 dimensions."""
    fragmentation = await compute_fragmentation_score(db, building_id)
    defensibility = await compute_defensibility_score(db, building_id)
    counterfactual = await compute_counterfactual(db, building_id)

    # Generate headline
    frag_score = fragmentation["fragmentation_score"]
    def_score = defensibility["defensibility_score"]

    if frag_score > 70:
        headline = "Ce bâtiment souffre d'une fragmentation critique de ses données"
    elif def_score < 0.3:
        headline = "La traçabilité des décisions est insuffisante pour ce bâtiment"
    elif frag_score < 30 and def_score > 0.7:
        headline = "Ce bâtiment bénéficie d'une consolidation exemplaire"
    else:
        headline = "La plateforme apporte une valeur mesurable à la gestion de ce bâtiment"

    return {
        "headline": headline,
        "fragmentation": fragmentation,
        "defensibility": defensibility,
        "counterfactual": counterfactual,
    }


# ---------------------------------------------------------------------------
# 5. Portfolio Summary
# ---------------------------------------------------------------------------


async def get_portfolio_indispensability(
    db: AsyncSession,
    building_ids: list[UUID],
) -> dict:
    """Aggregate indispensability across a portfolio of buildings."""
    if not building_ids:
        return {
            "building_count": 0,
            "avg_fragmentation": 100.0,
            "avg_defensibility": 0.0,
            "total_documents": 0,
            "total_decisions": 0,
            "headline": "Aucun bâtiment dans le portefeuille",
        }

    total_frag = 0.0
    total_def = 0.0
    total_docs = 0
    total_decisions = 0

    for bid in building_ids:
        frag = await compute_fragmentation_score(db, bid)
        defen = await compute_defensibility_score(db, bid)
        total_frag += frag["fragmentation_score"]
        total_def += defen["defensibility_score"]
        total_docs += frag["documents_with_provenance"]
        total_decisions += defen["decisions_tracked"]

    n = len(building_ids)
    avg_frag = round(total_frag / n, 1)
    avg_def = round(total_def / n, 3)

    if avg_frag > 70:
        headline = f"Portefeuille à risque: fragmentation moyenne de {avg_frag}%"
    elif avg_def > 0.7:
        headline = f"Portefeuille bien documenté: défensibilité moyenne de {avg_def}"
    else:
        headline = f"Portefeuille en cours de consolidation ({n} bâtiments)"

    return {
        "building_count": n,
        "avg_fragmentation": avg_frag,
        "avg_defensibility": avg_def,
        "total_documents": total_docs,
        "total_decisions": total_decisions,
        "headline": headline,
    }
