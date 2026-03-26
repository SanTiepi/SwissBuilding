"""
BatiConnect — Fragmentation Score Service

Measures how fragmented a building's truth would be WITHOUT BatiConnect's
unification layer. High score = the building desperately needs the platform.

This is sales ammunition: every number tells a story about what breaks
when you remove the single source of truth.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_snapshot import BuildingSnapshot
from app.models.compliance_artefact import ComplianceArtefact
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.intervention import Intervention
from app.schemas.indispensability import (
    ContradictionValue,
    FragmentationResult,
    KnowledgeConsolidation,
    ProofChainIntegrity,
    SourceDispersion,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System mapping — what external systems each source would otherwise live in
# ---------------------------------------------------------------------------

_SOURCE_SYSTEM_MAP: dict[str, str] = {
    "diagnostic": "email diagnostiqueur",
    "document": "classeur papier",
    "enrichment": "portail cantonal",
    "publication": "email diagnostiqueur",
    "import": "Excel gérance",
    "manual": "Excel gérance",
    "cadastre": "cadastre",
    "vd-public-rcb": "portail cantonal",
    "registre_foncier": "registre foncier",
    "intervention": "classeur papier",
    "compliance": "dossier autorité",
    "snapshot": "aucun (mémoire perdue)",
}

# Enrichment fields on Building that come from external sources
_ENRICHMENT_FIELDS = [
    "egrid",
    "egid",
    "official_id",
    "parcel_number",
    "municipality_ofs",
    "latitude",
    "longitude",
    "construction_year",
    "renovation_year",
    "floors_above",
    "floors_below",
    "surface_area_m2",
    "volume_m3",
]

# Fields typically entered manually
_MANUAL_FIELDS = [
    "address",
    "postal_code",
    "city",
    "canton",
    "building_type",
    "status",
]

# Fragmentation score weights (sum = 1.0)
_W_SOURCES = 0.25
_W_CONTRADICTIONS = 0.30
_W_PROOF_CHAINS = 0.25
_W_ENRICHMENT = 0.20


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def compute_fragmentation_score(
    db: AsyncSession,
    building_id: UUID,
) -> FragmentationResult | None:
    """Compute how fragmented a building's truth would be without BatiConnect.

    Returns None if building does not exist.
    """
    # ── 0. Verify building ────────────────────────────────────────
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    # ── 1. Source dispersion ──────────────────────────────────────
    source_dispersion = await _compute_source_dispersion(db, building_id, building)

    # ── 2. Contradiction resolution value ─────────────────────────
    contradiction_value = await _compute_contradiction_value(db, building_id)

    # ── 3. Proof chain integrity ──────────────────────────────────
    proof_chain = await _compute_proof_chain_integrity(db, building_id)

    # ── 4. Knowledge consolidation ────────────────────────────────
    knowledge = _compute_knowledge_consolidation(building)

    # ── 5. Fragmentation score ────────────────────────────────────
    score = _compute_score(source_dispersion, contradiction_value, proof_chain, knowledge)

    return FragmentationResult(
        building_id=building_id,
        source_dispersion=source_dispersion,
        contradiction_value=contradiction_value,
        proof_chain_integrity=proof_chain,
        knowledge_consolidation=knowledge,
        fragmentation_score=round(score, 1),
    )


# ---------------------------------------------------------------------------
# Source dispersion
# ---------------------------------------------------------------------------


async def _compute_source_dispersion(
    db: AsyncSession,
    building_id: UUID,
    building: Building,
) -> SourceDispersion:
    """Count distinct source origins and map them to replaced systems."""
    sources: set[str] = set()
    systems: set[str] = set()

    # Diagnostics
    diag_count = (
        await db.execute(select(func.count()).select_from(Diagnostic).where(Diagnostic.building_id == building_id))
    ).scalar() or 0
    if diag_count > 0:
        sources.add("diagnostic")
        systems.add(_SOURCE_SYSTEM_MAP["diagnostic"])

    # Documents
    doc_count = (
        await db.execute(select(func.count()).select_from(Document).where(Document.building_id == building_id))
    ).scalar() or 0
    if doc_count > 0:
        sources.add("document")
        systems.add(_SOURCE_SYSTEM_MAP["document"])

    # Diagnostic publications (imported from Batiscan)
    pub_count = (
        await db.execute(
            select(func.count())
            .select_from(DiagnosticReportPublication)
            .where(DiagnosticReportPublication.building_id == building_id)
        )
    ).scalar() or 0
    if pub_count > 0:
        sources.add("publication")
        systems.add(_SOURCE_SYSTEM_MAP["publication"])

    # Enrichment from public datasets
    if building.source_dataset:
        sources.add("enrichment")
        mapped = _SOURCE_SYSTEM_MAP.get(building.source_dataset, "portail cantonal")
        systems.add(mapped)

    # Source metadata (additional enrichment)
    if building.source_metadata_json:
        sources.add("enrichment_metadata")
        systems.add("portail cantonal")

    # Interventions
    intervention_count = (
        await db.execute(select(func.count()).select_from(Intervention).where(Intervention.building_id == building_id))
    ).scalar() or 0
    if intervention_count > 0:
        sources.add("intervention")
        systems.add(_SOURCE_SYSTEM_MAP["intervention"])

    # Compliance artefacts
    artefact_count = (
        await db.execute(
            select(func.count()).select_from(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id)
        )
    ).scalar() or 0
    if artefact_count > 0:
        sources.add("compliance")
        systems.add(_SOURCE_SYSTEM_MAP["compliance"])

    # Snapshots (temporal memory)
    snapshot_count = (
        await db.execute(
            select(func.count()).select_from(BuildingSnapshot).where(BuildingSnapshot.building_id == building_id)
        )
    ).scalar() or 0
    if snapshot_count > 0:
        sources.add("snapshot")
        systems.add(_SOURCE_SYSTEM_MAP["snapshot"])

    # Manual data always counts (the building itself was created)
    sources.add("manual")
    systems.add(_SOURCE_SYSTEM_MAP["manual"])

    return SourceDispersion(
        sources_unified=len(sources),
        systems_replaced=sorted(systems),
    )


# ---------------------------------------------------------------------------
# Contradiction value
# ---------------------------------------------------------------------------


async def _compute_contradiction_value(
    db: AsyncSession,
    building_id: UUID,
) -> ContradictionValue:
    """Count contradictions detected and resolved by the platform."""
    result = await db.execute(
        select(DataQualityIssue).where(
            and_(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.issue_type == "contradiction",
            )
        )
    )
    contradictions = list(result.scalars().all())

    detected = len(contradictions)
    resolved = sum(1 for c in contradictions if c.status == "resolved")
    unresolved = detected - resolved

    if unresolved > 0:
        silent_risk = (
            f"{unresolved} contradiction(s) non résolue(s) resteraient invisibles sans la plateforme. "
            "Chaque contradiction non détectée peut entraîner une décision basée sur des données "
            "erronées — risque de non-conformité réglementaire, surcoûts de chantier, ou mise en danger des occupants."
        )
    elif detected > 0:
        silent_risk = (
            f"Les {detected} contradiction(s) détectée(s) ont toutes été résolues grâce à BatiConnect. "
            "Sans la plateforme, ces incohérences seraient restées enfouies dans des classeurs séparés, "
            "invisibles jusqu'au jour de l'inspection ou du sinistre."
        )
    else:
        silent_risk = (
            "Aucune contradiction détectée pour le moment. La surveillance continue de BatiConnect "
            "garantit que toute incohérence future sera immédiatement signalée — "
            "un filet de sécurité qui n'existe pas avec des outils fragmentés."
        )

    return ContradictionValue(
        contradictions_detected=detected,
        contradictions_resolved=resolved,
        silent_risk=silent_risk,
    )


# ---------------------------------------------------------------------------
# Proof chain integrity
# ---------------------------------------------------------------------------


async def _compute_proof_chain_integrity(
    db: AsyncSession,
    building_id: UUID,
) -> ProofChainIntegrity:
    """Count evidence links and documents with/without provenance."""
    # For building-specific: count evidence links for this building's diagnostics/documents
    diag_ids_result = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    diag_ids = [r[0] for r in diag_ids_result.all()]

    doc_ids_result = await db.execute(select(Document.id).where(Document.building_id == building_id))
    doc_ids = [r[0] for r in doc_ids_result.all()]

    entity_ids = set(diag_ids + doc_ids)
    entity_ids.add(building_id)

    # Count evidence links that reference any of our entities
    if entity_ids:
        proof_chains = 0
        for eid in entity_ids:
            link_count = (
                await db.execute(
                    select(func.count())
                    .select_from(EvidenceLink)
                    .where((EvidenceLink.source_id == eid) | (EvidenceLink.target_id == eid))
                )
            ).scalar() or 0
            proof_chains += link_count
    else:
        proof_chains = 0

    # Documents with provenance = those with content_hash (integrity tracked)
    docs_with_prov = (
        await db.execute(
            select(func.count())
            .select_from(Document)
            .where(
                and_(
                    Document.building_id == building_id,
                    Document.content_hash.isnot(None),
                )
            )
        )
    ).scalar() or 0

    docs_total = (
        await db.execute(select(func.count()).select_from(Document).where(Document.building_id == building_id))
    ).scalar() or 0

    return ProofChainIntegrity(
        proof_chains_count=proof_chains,
        documents_with_provenance=docs_with_prov,
        documents_without_provenance=docs_total - docs_with_prov,
    )


# ---------------------------------------------------------------------------
# Knowledge consolidation
# ---------------------------------------------------------------------------


def _compute_knowledge_consolidation(building: Building) -> KnowledgeConsolidation:
    """Measure field population from enrichment vs manual entry."""
    enrichment_count = 0
    manual_count = 0
    cross_source = 0

    has_metadata = bool(building.source_metadata_json)
    has_source_dataset = bool(building.source_dataset)

    for field in _ENRICHMENT_FIELDS:
        val = getattr(building, field, None)
        if val is not None:
            enrichment_count += 1
            # If both enrichment and manual data exist, it's cross-source validated
            if has_metadata or has_source_dataset:
                cross_source += 1

    for field in _MANUAL_FIELDS:
        val = getattr(building, field, None)
        if val is not None:
            manual_count += 1

    return KnowledgeConsolidation(
        enrichment_fields_count=enrichment_count,
        manual_fields_count=manual_count,
        cross_source_fields=cross_source,
    )


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------


def _compute_score(
    source: SourceDispersion,
    contradiction: ContradictionValue,
    proof: ProofChainIntegrity,
    knowledge: KnowledgeConsolidation,
) -> float:
    """Compute fragmentation score 0-100 (100 = completely fragmented without us).

    Higher score = more value provided by BatiConnect.
    """
    # Source dispersion: more sources unified = higher fragmentation without us
    # Cap at 8 sources for normalization
    source_score = min(source.sources_unified / 8.0, 1.0) * 100

    # Contradiction value: detected contradictions prove the platform catches
    # things that would otherwise go unnoticed
    if contradiction.contradictions_detected > 0:
        contradiction_score = 100.0  # any contradiction detected = max value
    else:
        contradiction_score = 30.0  # surveillance value even with no contradictions

    # Proof chains: more chains = more would be lost without us
    chain_total = proof.proof_chains_count + proof.documents_with_provenance
    chain_score = min(chain_total / 20.0, 1.0) * 100

    # Knowledge consolidation: more enriched fields = more aggregation value
    total_fields = knowledge.enrichment_fields_count + knowledge.manual_fields_count
    if total_fields > 0:
        enrichment_ratio = knowledge.enrichment_fields_count / total_fields
        knowledge_score = enrichment_ratio * 100
    else:
        knowledge_score = 0.0

    return (
        _W_SOURCES * source_score
        + _W_CONTRADICTIONS * contradiction_score
        + _W_PROOF_CHAINS * chain_score
        + _W_ENRICHMENT * knowledge_score
    )
