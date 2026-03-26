"""
BatiConnect — Score Explainability Service

Builds the full proof trail behind every metric in indispensability reports.
Every number becomes clickable and traceable to its source: documents,
contradictions, evidence links, enrichment sources, actions, custody events.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.data_quality_issue import DataQualityIssue
from app.models.document import Document
from app.models.enrichment_run import BuildingEnrichmentRun
from app.models.evidence_link import EvidenceLink
from app.models.source_snapshot import BuildingSourceSnapshot
from app.schemas.score_explainability import ExplainedReport, ExplainedScore, ScoreLineItem

# ---------------------------------------------------------------------------
# Cost heuristics (must match value_ledger_service.py)
# ---------------------------------------------------------------------------
_HOURS_PER_SOURCE = 2.0
_HOURS_PER_CONTRADICTION = 4.0
_HOURS_PER_PROOF_CHAIN = 1.0
_HOURS_PER_DOC_SECURED = 0.5
_HOURS_PER_DECISION_BACKED = 1.0
_RATE_CHF_PER_HOUR = 150.0

_METHODOLOGY_SUMMARY = (
    "Ce rapport détaille chaque élément concret qui compose les métriques "
    "d'indispensabilité de BatiConnect. Chaque ligne est liée à un objet "
    "réel du dossier (document, contradiction, lien d'évidence, source "
    "d'enrichissement, décision, événement de chaîne de custody). Les "
    "estimations horaires utilisent des heuristiques conservatrices basées "
    "sur le temps moyen de reconstitution manuelle. La valorisation "
    "financière applique un taux horaire de CHF 150.- pour un spécialiste "
    "immobilier."
)

# ---------------------------------------------------------------------------
# Source class mapping for enrichment sources
# ---------------------------------------------------------------------------
_SOURCE_CLASS_MAP: dict[str, str] = {
    "identity": "official",
    "regulatory": "official",
    "environment": "official",
    "energy": "official",
    "risk": "official",
    "transport": "derived",
    "social": "derived",
    "computed": "derived",
}


async def explain_building_scores(
    db: AsyncSession,
    building_id: UUID,
) -> ExplainedReport | None:
    """Build a full explainability report for a building.

    Returns None if the building does not exist.
    """
    building = await db.get(Building, building_id)
    if not building:
        return None

    scores: list[ExplainedScore] = []
    all_hour_items: list[tuple[ScoreLineItem, float]] = []

    # --- a) sources_unified ---
    sources_score, source_hour_items = await _explain_sources_unified(db, building_id)
    scores.append(sources_score)
    all_hour_items.extend(source_hour_items)

    # --- b) contradictions_resolved ---
    contra_score, contra_hour_items = await _explain_contradictions_resolved(db, building_id)
    scores.append(contra_score)
    all_hour_items.extend(contra_hour_items)

    # --- c) proof_chains_count ---
    proof_score, proof_hour_items = await _explain_proof_chains(db, building_id)
    scores.append(proof_score)
    all_hour_items.extend(proof_hour_items)

    # --- d) documents_with_provenance ---
    docs_score, docs_hour_items = await _explain_documents_with_provenance(db, building_id)
    scores.append(docs_score)
    all_hour_items.extend(docs_hour_items)

    # --- e) decisions_backed ---
    decisions_score, decisions_hour_items = await _explain_decisions_backed(db, building_id)
    scores.append(decisions_score)
    all_hour_items.extend(decisions_hour_items)

    # --- f) hours_saved ---
    hours_score = _explain_hours_saved(all_hour_items, building_id)
    scores.append(hours_score)

    # --- g) value_chf ---
    value_score = _explain_value_chf(all_hour_items, building_id)
    scores.append(value_score)

    total_line_items = sum(len(s.line_items) for s in scores)

    return ExplainedReport(
        building_id=building_id,
        generated_at=datetime.utcnow(),
        scores=scores,
        total_line_items=total_line_items,
        methodology_summary=_METHODOLOGY_SUMMARY,
    )


# ---------------------------------------------------------------------------
# a) Sources Unified
# ---------------------------------------------------------------------------


async def _explain_sources_unified(
    db: AsyncSession,
    building_id: UUID,
) -> tuple[ExplainedScore, list[tuple[ScoreLineItem, float]]]:
    """Each completed enrichment run + its source snapshots = 1 line item."""
    # Get enrichment runs
    runs_result = await db.execute(
        select(BuildingEnrichmentRun).where(
            and_(
                BuildingEnrichmentRun.building_id == building_id,
                BuildingEnrichmentRun.status == "completed",
            )
        )
    )
    runs = list(runs_result.scalars().all())

    # Get source snapshots for this building
    snapshots_result = await db.execute(
        select(BuildingSourceSnapshot).where(
            BuildingSourceSnapshot.building_id == building_id,
        )
    )
    snapshots = list(snapshots_result.scalars().all())

    line_items: list[ScoreLineItem] = []
    hour_items: list[tuple[ScoreLineItem, float]] = []

    for run in runs:
        item = ScoreLineItem(
            item_type="enrichment_source",
            item_id=run.id,
            label=f"Enrichissement #{len(line_items) + 1}",
            detail=(
                f"Exécution d'enrichissement avec {run.sources_succeeded} source(s) "
                f"réussie(s) sur {run.sources_attempted} tentée(s)"
            ),
            contribution=f"+{run.sources_succeeded} source(s) intégrée(s)",
            link=f"/buildings/{building_id}",
            source_class="official",
            timestamp=run.completed_at or run.created_at,
        )
        line_items.append(item)
        hour_items.append((item, _HOURS_PER_SOURCE))

    for snap in snapshots:
        source_class = _SOURCE_CLASS_MAP.get(snap.source_category, "derived")
        item = ScoreLineItem(
            item_type="enrichment_source",
            item_id=snap.id,
            label=f"Source: {snap.source_name}",
            detail=(
                f"Données de la source « {snap.source_name} » "
                f"(catégorie: {snap.source_category}, "
                f"confiance: {snap.confidence})"
            ),
            contribution="+1 source unifiée",
            link=f"/buildings/{building_id}",
            source_class=source_class,
            timestamp=snap.fetched_at,
        )
        line_items.append(item)
        hour_items.append((item, _HOURS_PER_SOURCE))

    return (
        ExplainedScore(
            metric_name="sources_unified",
            metric_label="Sources unifiées",
            value=float(len(line_items)),
            unit="sources",
            methodology=(
                "Chaque source externe intégrée au dossier est comptée comme "
                "une source unifiée. Inclut les exécutions d'enrichissement "
                "et les instantanés de sources individuelles."
            ),
            line_items=line_items,
            confidence="exact",
        ),
        hour_items,
    )


# ---------------------------------------------------------------------------
# b) Contradictions Resolved
# ---------------------------------------------------------------------------


async def _explain_contradictions_resolved(
    db: AsyncSession,
    building_id: UUID,
) -> tuple[ExplainedScore, list[tuple[ScoreLineItem, float]]]:
    """Each DataQualityIssue of type contradiction = 1 line item."""
    result = await db.execute(
        select(DataQualityIssue).where(
            and_(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.issue_type == "contradiction",
            )
        )
    )
    issues = list(result.scalars().all())

    line_items: list[ScoreLineItem] = []
    hour_items: list[tuple[ScoreLineItem, float]] = []

    for issue in issues:
        resolved_label = "résolue" if issue.status == "resolved" else "détectée"
        resolution_detail = ""
        if issue.resolution_notes:
            resolution_detail = f" Résolution: {issue.resolution_notes}"

        item = ScoreLineItem(
            item_type="contradiction",
            item_id=issue.id,
            label=f"Contradiction {resolved_label}: {issue.field_name or 'champ inconnu'}",
            detail=(f"{issue.description}{resolution_detail}"),
            contribution=f"+1 contradiction {resolved_label}",
            link=f"/buildings/{building_id}",
            source_class="documentary",
            timestamp=issue.resolved_at,
        )
        line_items.append(item)
        hour_items.append((item, _HOURS_PER_CONTRADICTION))

    return (
        ExplainedScore(
            metric_name="contradictions_resolved",
            metric_label="Contradictions détectées et résolues",
            value=float(len(line_items)),
            unit="contradictions",
            methodology=(
                "Contradictions détectées automatiquement entre sources et "
                "résolues par validation croisée. Chaque contradiction "
                "représente un risque d'erreur évité."
            ),
            line_items=line_items,
            confidence="exact",
        ),
        hour_items,
    )


# ---------------------------------------------------------------------------
# c) Proof Chains
# ---------------------------------------------------------------------------


async def _explain_proof_chains(
    db: AsyncSession,
    building_id: UUID,
) -> tuple[ExplainedScore, list[tuple[ScoreLineItem, float]]]:
    """EvidenceLink + CustodyEvent referencing this building = proof chains."""
    # Evidence links where building is source or target
    ev_result = await db.execute(
        select(EvidenceLink).where((EvidenceLink.source_id == building_id) | (EvidenceLink.target_id == building_id))
    )
    evidence_links = list(ev_result.scalars().all())

    # Custody events via document IDs for this building
    doc_ids_result = await db.execute(select(Document.id).where(Document.building_id == building_id))
    doc_ids = [r[0] for r in doc_ids_result.all()]

    # Evidence links referencing documents of this building
    if doc_ids:
        ev_doc_result = await db.execute(
            select(EvidenceLink).where(
                and_(
                    EvidenceLink.source_type == "document",
                    EvidenceLink.source_id.in_(doc_ids),
                )
            )
        )
        doc_evidence_links = list(ev_doc_result.scalars().all())
        # Deduplicate by ID
        seen_ids = {e.id for e in evidence_links}
        for el in doc_evidence_links:
            if el.id not in seen_ids:
                evidence_links.append(el)
                seen_ids.add(el.id)

    line_items: list[ScoreLineItem] = []
    hour_items: list[tuple[ScoreLineItem, float]] = []

    for el in evidence_links:
        item = ScoreLineItem(
            item_type="evidence_link",
            item_id=el.id,
            label=f"Lien d'évidence: {el.source_type} → {el.target_type}",
            detail=(
                f"Relation « {el.relationship} » entre "
                f"{el.source_type} et {el.target_type}" + (f". {el.explanation}" if el.explanation else "")
            ),
            contribution="+1 chaîne de preuve",
            link=f"/buildings/{building_id}",
            source_class="documentary",
            timestamp=el.created_at,
        )
        line_items.append(item)
        hour_items.append((item, _HOURS_PER_PROOF_CHAIN))

    return (
        ExplainedScore(
            metric_name="proof_chains_count",
            metric_label="Chaînes de preuve",
            value=float(len(line_items)),
            unit="chaînes",
            methodology=(
                "Liens d'évidence traçables entre documents, diagnostics "
                "et décisions. Chaque lien documente une relation de "
                "preuve entre deux éléments du dossier."
            ),
            line_items=line_items,
            confidence="exact",
        ),
        hour_items,
    )


# ---------------------------------------------------------------------------
# d) Documents with Provenance
# ---------------------------------------------------------------------------


async def _explain_documents_with_provenance(
    db: AsyncSession,
    building_id: UUID,
) -> tuple[ExplainedScore, list[tuple[ScoreLineItem, float]]]:
    """Documents where content_hash is not null = provenance verified."""
    result = await db.execute(
        select(Document).where(
            and_(
                Document.building_id == building_id,
                Document.content_hash.isnot(None),
            )
        )
    )
    documents = list(result.scalars().all())

    line_items: list[ScoreLineItem] = []
    hour_items: list[tuple[ScoreLineItem, float]] = []

    for doc in documents:
        item = ScoreLineItem(
            item_type="document",
            item_id=doc.id,
            label=f"Document: {doc.file_name}",
            detail=(
                f"Document de type « {doc.document_type or 'non classé'} » "
                f"avec empreinte SHA-256 vérifiable "
                f"({doc.content_hash[:12]}…)"
            ),
            contribution="+1 document avec provenance",
            link=f"/buildings/{building_id}/documents",
            source_class="documentary",
            timestamp=doc.created_at,
        )
        line_items.append(item)
        hour_items.append((item, _HOURS_PER_DOC_SECURED))

    return (
        ExplainedScore(
            metric_name="documents_with_provenance",
            metric_label="Documents avec provenance vérifiable",
            value=float(len(line_items)),
            unit="documents",
            methodology=(
                "Documents dont l'intégrité est vérifiable par empreinte "
                "SHA-256. Chaque document haché garantit qu'il n'a pas été "
                "modifié depuis son archivage."
            ),
            line_items=line_items,
            confidence="exact",
        ),
        hour_items,
    )


# ---------------------------------------------------------------------------
# e) Decisions Backed
# ---------------------------------------------------------------------------


async def _explain_decisions_backed(
    db: AsyncSession,
    building_id: UUID,
) -> tuple[ExplainedScore, list[tuple[ScoreLineItem, float]]]:
    """ActionItems that have at least one EvidenceLink = backed decisions."""
    actions_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = list(actions_result.scalars().all())

    line_items: list[ScoreLineItem] = []
    hour_items: list[tuple[ScoreLineItem, float]] = []

    for action in actions:
        # Check if this action has evidence links
        ev_count = (
            await db.execute(
                select(func.count())
                .select_from(EvidenceLink)
                .where((EvidenceLink.source_id == action.id) | (EvidenceLink.target_id == action.id))
            )
        ).scalar() or 0

        if ev_count > 0:
            item = ScoreLineItem(
                item_type="action",
                item_id=action.id,
                label=f"Décision: {action.title[:80]}",
                detail=(
                    f"Action de type « {action.action_type} » "
                    f"(priorité: {action.priority}, statut: {action.status}) "
                    f"appuyée par {ev_count} lien(s) d'évidence"
                ),
                contribution="+1 décision justifiée",
                link=f"/buildings/{building_id}",
                source_class="documentary",
                timestamp=action.created_at,
            )
            line_items.append(item)
            hour_items.append((item, _HOURS_PER_DECISION_BACKED))

    return (
        ExplainedScore(
            metric_name="decisions_backed",
            metric_label="Décisions justifiées par preuves",
            value=float(len(line_items)),
            unit="décisions",
            methodology=(
                "Décisions et actions dont la justification est traçable "
                "via au moins un lien d'évidence. Chaque décision justifiée "
                "réduit le risque de contestation."
            ),
            line_items=line_items,
            confidence="exact",
        ),
        hour_items,
    )


# ---------------------------------------------------------------------------
# f) Hours Saved
# ---------------------------------------------------------------------------


def _explain_hours_saved(
    all_hour_items: list[tuple[ScoreLineItem, float]],
    building_id: UUID,
) -> ExplainedScore:
    """Aggregate hour contributions from all metrics."""
    line_items: list[ScoreLineItem] = []
    total_hours = 0.0

    for original_item, hours in all_hour_items:
        item = ScoreLineItem(
            item_type=original_item.item_type,
            item_id=original_item.item_id,
            label=original_item.label,
            detail=original_item.detail,
            contribution=f"+{hours}h économisée(s)",
            link=original_item.link,
            source_class=original_item.source_class,
            timestamp=original_item.timestamp,
        )
        line_items.append(item)
        total_hours += hours

    return ExplainedScore(
        metric_name="hours_saved",
        metric_label="Heures économisées",
        value=round(total_hours, 1),
        unit="heures",
        methodology=(
            "Estimation basée sur le temps moyen de reconstitution manuelle: "
            "2h par source, 4h par contradiction, 1h par chaîne de preuve, "
            "0.5h par document, 1h par décision."
        ),
        line_items=line_items,
        confidence="estimated",
    )


# ---------------------------------------------------------------------------
# g) Value CHF
# ---------------------------------------------------------------------------


def _explain_value_chf(
    all_hour_items: list[tuple[ScoreLineItem, float]],
    building_id: UUID,
) -> ExplainedScore:
    """Monetize hour savings at CHF 150/h."""
    line_items: list[ScoreLineItem] = []
    total_chf = 0.0

    for original_item, hours in all_hour_items:
        chf = hours * _RATE_CHF_PER_HOUR
        item = ScoreLineItem(
            item_type=original_item.item_type,
            item_id=original_item.item_id,
            label=original_item.label,
            detail=original_item.detail,
            contribution=f"+CHF {chf:.0f}",
            link=original_item.link,
            source_class=original_item.source_class,
            timestamp=original_item.timestamp,
        )
        line_items.append(item)
        total_chf += chf

    return ExplainedScore(
        metric_name="value_chf",
        metric_label="Valeur estimée en CHF",
        value=round(total_chf, 2),
        unit="CHF",
        methodology=(
            "Valorisation au taux horaire moyen de CHF 150.- pour un "
            "spécialiste immobilier. Chaque heure économisée est convertie "
            "en valeur monétaire."
        ),
        line_items=line_items,
        confidence="heuristic",
    )
