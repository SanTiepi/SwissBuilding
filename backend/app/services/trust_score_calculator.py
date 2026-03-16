"""BuildingTrustScore calculation service.

Computes a trust score reflecting data reliability and completeness
for a building, based on proven/inferred/declared/obsolete/contradictory
classification of all data points.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_trust_score_v2 import BuildingTrustScore
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_link import EvidenceLink
from app.models.intervention import Intervention
from app.models.material import Material
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.zone import Zone

if TYPE_CHECKING:
    from uuid import UUID

# Trust weights per category
WEIGHT_PROVEN = 1.0
WEIGHT_INFERRED = 0.5
WEIGHT_DECLARED = 0.3
WEIGHT_OBSOLETE = 0.1
WEIGHT_CONTRADICTORY = 0.0

# Obsolescence threshold
OBSOLETE_YEARS = 5

# Trend detection threshold
TREND_THRESHOLD = 0.05


def _is_obsolete_date(d: date | datetime | None) -> bool:
    """Return True if a date is older than OBSOLETE_YEARS."""
    if d is None:
        return False
    if isinstance(d, datetime):
        d = d.date() if hasattr(d, "date") else d
    cutoff = date.today() - timedelta(days=OBSOLETE_YEARS * 365)
    return d < cutoff


async def calculate_trust_score(
    db: AsyncSession,
    building_id: UUID,
    assessed_by: str | None = None,
) -> BuildingTrustScore:
    """Calculate and persist a BuildingTrustScore for the given building.

    Classifies all building data points into trust categories
    (proven, inferred, declared, obsolete, contradictory),
    computes a weighted overall score, determines trend, and upserts.
    """
    # ── 1. Load building data ──────────────────────────────────────
    building = (await db.execute(select(Building).where(Building.id == building_id))).scalar_one_or_none()
    if building is None:
        msg = f"Building {building_id} not found"
        raise ValueError(msg)

    diagnostics = list(
        (await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))).scalars().all()
    )
    diag_ids = [d.id for d in diagnostics]

    samples: list[Sample] = []
    if diag_ids:
        samples = list((await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))).scalars().all())

    documents = list((await db.execute(select(Document).where(Document.building_id == building_id))).scalars().all())

    evidence_links = list(
        (
            await db.execute(
                select(EvidenceLink).where(
                    (EvidenceLink.source_type == "building") & (EvidenceLink.source_id == building_id)
                    | (EvidenceLink.target_type == "building") & (EvidenceLink.target_id == building_id)
                )
            )
        )
        .scalars()
        .all()
    )

    zones = list((await db.execute(select(Zone).where(Zone.building_id == building_id))).scalars().all())

    zone_ids = [z.id for z in zones]
    elements: list[BuildingElement] = []
    if zone_ids:
        elements = list(
            (await db.execute(select(BuildingElement).where(BuildingElement.zone_id.in_(zone_ids)))).scalars().all()
        )

    element_ids = [e.id for e in elements]
    materials: list[Material] = []
    if element_ids:
        materials = list(
            (await db.execute(select(Material).where(Material.element_id.in_(element_ids)))).scalars().all()
        )

    interventions = list(
        (await db.execute(select(Intervention).where(Intervention.building_id == building_id))).scalars().all()
    )

    plans = list(
        (await db.execute(select(TechnicalPlan).where(TechnicalPlan.building_id == building_id))).scalars().all()
    )

    actions = list((await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))).scalars().all())

    risk_score = (
        await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    ).scalar_one_or_none()

    # ── 2. Classify data points ────────────────────────────────────
    proven = 0
    inferred = 0
    declared = 0
    obsolete = 0
    contradictory = 0

    # Build set of obsolete diagnostic ids
    obsolete_diag_ids = set()
    for d in diagnostics:
        ref_date = d.date_inspection or (d.created_at.date() if isinstance(d.created_at, datetime) else d.created_at)
        if ref_date and _is_obsolete_date(ref_date):
            obsolete_diag_ids.add(d.id)

    # -- Diagnostics --
    for d in diagnostics:
        if d.id in obsolete_diag_ids:
            obsolete += 1
        elif d.status == "completed" or d.status == "validated":
            proven += 1
        else:
            declared += 1

    # -- Samples --
    # Track for contradiction detection: group by (location_room, pollutant_type)
    sample_groups: dict[tuple[str | None, str | None], list[Sample]] = defaultdict(list)
    for s in samples:
        sample_groups[(s.location_room, s.pollutant_type)].append(s)

    # Detect contradictions
    contradictory_sample_ids: set[uuid.UUID] = set()
    for _key, group in sample_groups.items():
        if len(group) >= 2:
            threshold_values = {s.threshold_exceeded for s in group if s.threshold_exceeded is not None}
            if len(threshold_values) > 1:
                for s in group:
                    contradictory_sample_ids.add(s.id)

    for s in samples:
        if s.id in contradictory_sample_ids:
            contradictory += 1
        elif s.diagnostic_id in obsolete_diag_ids:
            obsolete += 1
        elif s.concentration is not None and s.unit:
            proven += 1
        else:
            declared += 1

    # -- Documents --
    for d in documents:
        if d.document_type in ("lab_report", "official_report", "regulatory_notice"):
            proven += 1
        else:
            declared += 1

    # -- Evidence links (each link = a proven data point) --
    proven += len(evidence_links)

    # -- Zones --
    declared += len(zones)

    # -- Elements --
    declared += len(elements)

    # -- Materials --
    for m in materials:
        if m.sample_id is not None:
            proven += 1
        else:
            declared += 1

    # -- Interventions --
    for i in interventions:
        if i.status == "completed":
            proven += 1
        else:
            declared += 1

    # -- Technical plans --
    declared += len(plans)

    # -- Actions --
    declared += len(actions)

    # -- Risk score --
    if risk_score is not None:
        # Check if any evidence links reference this risk score
        has_evidence = any(
            (el.source_type == "risk_score" and el.source_id == risk_score.id)
            or (el.target_type == "risk_score" and el.target_id == risk_score.id)
            for el in evidence_links
        )
        if has_evidence:
            proven += 1
        else:
            inferred += 1

    # -- Building metadata (address, year, type = 3 declared points if no official source) --
    if building.source_dataset:
        proven += 3  # officially sourced building data
    else:
        declared += 3

    # ── 3. Compute overall score ───────────────────────────────────
    total = proven + inferred + declared + obsolete + contradictory
    if total == 0:
        overall_score = 0.0
    else:
        weighted_sum = (
            proven * WEIGHT_PROVEN
            + inferred * WEIGHT_INFERRED
            + declared * WEIGHT_DECLARED
            + obsolete * WEIGHT_OBSOLETE
            + contradictory * WEIGHT_CONTRADICTORY
        )
        overall_score = round(min(max(weighted_sum / total, 0.0), 1.0), 4)

    # Percentages
    pct_proven = round(proven / total, 4) if total else 0.0
    pct_inferred = round(inferred / total, 4) if total else 0.0
    pct_declared = round(declared / total, 4) if total else 0.0
    pct_obsolete = round(obsolete / total, 4) if total else 0.0
    pct_contradictory = round(contradictory / total, 4) if total else 0.0

    # ── 4. Determine trend ─────────────────────────────────────────
    latest_result = await db.execute(
        select(BuildingTrustScore)
        .where(BuildingTrustScore.building_id == building_id)
        .order_by(BuildingTrustScore.assessed_at.desc())
        .limit(1)
    )
    previous = latest_result.scalar_one_or_none()
    previous_score = previous.overall_score if previous else None

    if previous_score is not None:
        delta = overall_score - previous_score
        if delta > TREND_THRESHOLD:
            trend = "improving"
        elif delta < -TREND_THRESHOLD:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = None

    # ── 5. Persist new record ──────────────────────────────────────
    new_score = BuildingTrustScore(
        id=uuid.uuid4(),
        building_id=building_id,
        overall_score=overall_score,
        percent_proven=pct_proven,
        percent_inferred=pct_inferred,
        percent_declared=pct_declared,
        percent_obsolete=pct_obsolete,
        percent_contradictory=pct_contradictory,
        total_data_points=total,
        proven_count=proven,
        inferred_count=inferred,
        declared_count=declared,
        obsolete_count=obsolete,
        contradictory_count=contradictory,
        trend=trend,
        previous_score=previous_score,
        assessed_by=assessed_by,
        assessed_at=datetime.now(UTC),
    )
    db.add(new_score)
    await db.flush()
    return new_score
