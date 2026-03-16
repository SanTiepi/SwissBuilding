"""
SwissBuildingOS - Evidence Domain Facade

Read-only composition point for evidence-related queries: diagnostics,
samples, documents, and evidence links for a building. Thin wrapper over
existing models -- no new business logic.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.sample import Sample

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_evidence_summary(
    db: AsyncSession,
    building_id: UUID,
) -> dict | None:
    """Aggregate evidence state for a building.

    Returns None if the building does not exist.

    Returns a dict with:
      - building_id
      - diagnostics_count (total + by status)
      - samples_count (total, positive, negative, by pollutant)
      - documents_count
      - evidence_links_count
      - coverage_ratio (fraction of 5 pollutants with at least one sample)
    """
    # ── 0. Verify building exists ─────────────────────────────────
    result = await db.execute(select(Building).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        return None

    # ── 1. Diagnostics ────────────────────────────────────────────
    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())
    diagnostics_total = len(diagnostics)

    by_status: dict[str, int] = defaultdict(int)
    for d in diagnostics:
        by_status[d.status or "unknown"] += 1

    # ── 2. Samples (via diagnostics) ──────────────────────────────
    samples: list[Sample] = []
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    positive_count = 0
    negative_count = 0
    by_pollutant: dict[str, dict[str, int]] = defaultdict(lambda: {"positive": 0, "negative": 0, "total": 0})

    for s in samples:
        pollutant = (s.pollutant_type or "unknown").lower()
        by_pollutant[pollutant]["total"] += 1
        if s.threshold_exceeded:
            positive_count += 1
            by_pollutant[pollutant]["positive"] += 1
        else:
            negative_count += 1
            by_pollutant[pollutant]["negative"] += 1

    # ── 3. Documents ──────────────────────────────────────────────
    doc_count_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.building_id == building_id)
    )
    documents_count = doc_count_result.scalar() or 0

    # ── 4. Evidence links ─────────────────────────────────────────
    # Evidence links reference buildings indirectly (source/target), so we
    # count links where the building_id appears as either source or target
    # with source_type/target_type = "building".
    link_count_result = await db.execute(
        select(func.count())
        .select_from(EvidenceLink)
        .where(
            ((EvidenceLink.source_type == "building") & (EvidenceLink.source_id == building_id))
            | ((EvidenceLink.target_type == "building") & (EvidenceLink.target_id == building_id))
        )
    )
    evidence_links_count = link_count_result.scalar() or 0

    # ── 5. Coverage ratio ─────────────────────────────────────────
    all_pollutants = {"asbestos", "pcb", "lead", "hap", "radon"}
    covered = {p for p in by_pollutant if p in all_pollutants}
    coverage_ratio = round(len(covered) / len(all_pollutants), 4) if all_pollutants else 0.0

    return {
        "building_id": str(building_id),
        "diagnostics_count": diagnostics_total,
        "diagnostics_by_status": dict(by_status),
        "samples_count": len(samples),
        "samples_positive": positive_count,
        "samples_negative": negative_count,
        "samples_by_pollutant": {k: dict(v) for k, v in by_pollutant.items()},
        "documents_count": documents_count,
        "evidence_links_count": evidence_links_count,
        "coverage_ratio": coverage_ratio,
    }
