"""
SwissBuildingOS - Plan Heatmap Service

Generates proof-overlay heatmap data for a technical plan by aggregating
trust, unknowns, contradictions, and annotations.  Supports temporal decay,
sample-linked confidence, zone statistics, date-snapshot, and coverage-gap
detection.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_quality_issue import DataQualityIssue
from app.models.plan_annotation import PlanAnnotation
from app.models.sample import Sample
from app.models.unknown_issue import UnknownIssue
from app.models.zone import Zone
from app.schemas.plan_heatmap import (
    CoverageGap,
    CoverageGapReport,
    HeatmapPoint,
    PlanHeatmap,
    ZoneHeatmapStats,
)

# Mapping from annotation_type to (heatmap_category, intensity)
_ANNOTATION_TYPE_MAP: dict[str, tuple[str, float]] = {
    "hazard_zone": ("hazard", 0.9),
    "sample_location": ("sample", 0.7),
    "observation": ("trust", 0.5),
    "marker": ("trust", 0.3),
    "zone_reference": ("trust", 0.4),
    "measurement_point": ("sample", 0.6),
}

# Temporal decay thresholds (days)
_DECAY_THRESHOLD_2Y_DAYS = 365 * 2
_DECAY_THRESHOLD_5Y_DAYS = 365 * 5

# Confidence weights for sample-linked points
_CONFIDENCE_BASE_LAB = 0.9  # sample has lab concentration
_CONFIDENCE_BASE_VISUAL = 0.5  # sample without lab results
_CONFIDENCE_AGE_PENALTY_2Y = 0.15  # deducted if sample >2y old
_CONFIDENCE_AGE_PENALTY_5Y = 0.30  # deducted if sample >5y old


def _compute_decay_factor(created_at: datetime | None, now: datetime) -> float:
    """Return temporal decay factor based on annotation age."""
    if created_at is None:
        return 1.0
    # Ensure both are offset-aware or offset-naive for comparison
    if created_at.tzinfo is None and now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    elif created_at.tzinfo is not None and now.tzinfo is None:
        created_at = created_at.replace(tzinfo=None)
    age = now - created_at
    if age > timedelta(days=_DECAY_THRESHOLD_5Y_DAYS):
        return 0.25
    if age > timedelta(days=_DECAY_THRESHOLD_2Y_DAYS):
        return 0.5
    return 1.0


def _compute_confidence(
    sample: Sample | None,
    now: datetime,
) -> float | None:
    """Compute confidence for a sample-linked annotation point."""
    if sample is None:
        return None
    # Base confidence depends on whether lab results exist
    base = _CONFIDENCE_BASE_LAB if sample.concentration is not None else _CONFIDENCE_BASE_VISUAL
    # Age penalty
    created = sample.created_at
    if created is not None:
        if created.tzinfo is None and now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        elif created.tzinfo is not None and now.tzinfo is None:
            created = created.replace(tzinfo=None)
        age = now - created
        if age > timedelta(days=_DECAY_THRESHOLD_5Y_DAYS):
            base -= _CONFIDENCE_AGE_PENALTY_5Y
        elif age > timedelta(days=_DECAY_THRESHOLD_2Y_DAYS):
            base -= _CONFIDENCE_AGE_PENALTY_2Y
    return round(max(0.0, base), 2)


async def generate_plan_heatmap(
    db: AsyncSession,
    plan_id: UUID,
    building_id: UUID,
    *,
    reference_date: datetime | None = None,
) -> PlanHeatmap:
    """Generate heatmap data for a technical plan.

    Collects all PlanAnnotations, maps them to heatmap categories,
    enriches with unknown/contradiction data, applies temporal decay,
    and adds sample-linked confidence.

    Args:
        reference_date: If provided, decay is computed relative to this date.
                        Defaults to utcnow().
    """
    now = reference_date or datetime.now(UTC)

    # Load annotations for this plan
    result = await db.execute(
        select(PlanAnnotation).where(
            PlanAnnotation.plan_id == plan_id,
            PlanAnnotation.building_id == building_id,
        )
    )
    annotations = list(result.scalars().all())

    points: list[HeatmapPoint] = []
    summary: dict[str, int] = defaultdict(int)

    # Collect zone_ids and sample_ids for batch lookups
    zone_ids: set[UUID] = set()
    sample_ids: set[UUID] = set()
    for ann in annotations:
        if ann.zone_id is not None:
            zone_ids.add(ann.zone_id)
        if ann.sample_id is not None:
            sample_ids.add(ann.sample_id)

    # Load unknown issues for linked zones
    zones_with_unknowns: set[UUID] = set()
    if zone_ids:
        unknown_result = await db.execute(
            select(UnknownIssue.entity_id).where(
                UnknownIssue.building_id == building_id,
                UnknownIssue.entity_type == "zone",
                UnknownIssue.entity_id.in_(zone_ids),
                UnknownIssue.status == "open",
            )
        )
        zones_with_unknowns = {row[0] for row in unknown_result.all()}

    # Load contradictions for linked samples
    samples_with_contradictions: set[UUID] = set()
    if sample_ids:
        contradiction_result = await db.execute(
            select(DataQualityIssue.entity_id).where(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.entity_type == "sample",
                DataQualityIssue.entity_id.in_(sample_ids),
                DataQualityIssue.issue_type == "contradiction",
                DataQualityIssue.status == "open",
            )
        )
        samples_with_contradictions = {row[0] for row in contradiction_result.all()}

    # Batch-load sample objects for confidence calculation
    samples_by_id: dict[UUID, Sample] = {}
    if sample_ids:
        sample_result = await db.execute(select(Sample).where(Sample.id.in_(sample_ids)))
        samples_by_id = {s.id: s for s in sample_result.scalars().all()}

    # Process each annotation
    for ann in annotations:
        category, base_intensity = _ANNOTATION_TYPE_MAP.get(ann.annotation_type, ("trust", 0.3))

        decay = _compute_decay_factor(ann.created_at, now)
        intensity = round(base_intensity * decay, 4)

        # Confidence from linked sample
        sample_obj = samples_by_id.get(ann.sample_id) if ann.sample_id else None
        confidence = _compute_confidence(sample_obj, now)

        point = HeatmapPoint(
            x=ann.x,
            y=ann.y,
            intensity=intensity,
            category=category,
            label=ann.label,
            annotation_id=str(ann.id),
            zone_id=str(ann.zone_id) if ann.zone_id else None,
            decay_factor=decay,
            confidence=confidence,
        )
        points.append(point)
        summary[category] += 1

        # Add unknown point for zones with open unknowns
        if ann.zone_id is not None and ann.zone_id in zones_with_unknowns:
            unknown_point = HeatmapPoint(
                x=ann.x,
                y=ann.y,
                intensity=0.8,
                category="unknown",
                label=f"Unknown issue in zone ({ann.label})",
                annotation_id=str(ann.id),
                zone_id=str(ann.zone_id),
                decay_factor=decay,
            )
            points.append(unknown_point)
            summary["unknown"] += 1

        # Add contradiction point for samples with contradictions
        if ann.sample_id is not None and ann.sample_id in samples_with_contradictions:
            contradiction_point = HeatmapPoint(
                x=ann.x,
                y=ann.y,
                intensity=0.85,
                category="contradiction",
                label=f"Contradiction on sample ({ann.label})",
                annotation_id=str(ann.id),
                zone_id=str(ann.zone_id) if ann.zone_id else None,
                decay_factor=decay,
            )
            points.append(contradiction_point)
            summary["contradiction"] += 1

    # Coverage score: simple heuristic based on annotation count
    annotation_count = len(annotations)
    coverage_score = min(1.0, annotation_count / 10.0)

    return PlanHeatmap(
        plan_id=str(plan_id),
        building_id=str(building_id),
        total_points=len(points),
        coverage_score=round(coverage_score, 2),
        points=points,
        summary=dict(summary),
    )


async def get_zone_heatmap_stats(
    db: AsyncSession,
    building_id: UUID,
) -> list[ZoneHeatmapStats]:
    """Return per-zone aggregated proof density, average intensity, coverage gaps.

    Considers all annotations across all plans for the building.
    """
    now = datetime.now(UTC)

    # Load all zones for this building
    zone_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = {z.id: z for z in zone_result.scalars().all()}

    if not zones:
        return []

    # Load all annotations that reference zones in this building
    ann_result = await db.execute(
        select(PlanAnnotation).where(
            PlanAnnotation.building_id == building_id,
            PlanAnnotation.zone_id.isnot(None),
        )
    )
    annotations = list(ann_result.scalars().all())

    # Group annotations by zone
    zone_annotations: dict[UUID, list[PlanAnnotation]] = defaultdict(list)
    for ann in annotations:
        if ann.zone_id in zones:
            zone_annotations[ann.zone_id].append(ann)

    stats: list[ZoneHeatmapStats] = []
    for zone_id, zone in zones.items():
        anns = zone_annotations.get(zone_id, [])
        point_count = len(anns)

        if point_count > 0:
            total_intensity = 0.0
            for ann in anns:
                _, base_intensity = _ANNOTATION_TYPE_MAP.get(ann.annotation_type, ("trust", 0.3))
                decay = _compute_decay_factor(ann.created_at, now)
                total_intensity += base_intensity * decay
            avg_intensity = round(total_intensity / point_count, 4)
        else:
            avg_intensity = 0.0

        coverage = min(1.0, point_count / 5.0)

        stats.append(
            ZoneHeatmapStats(
                zone_id=str(zone_id),
                zone_name=zone.name,
                point_count=point_count,
                avg_intensity=avg_intensity,
                coverage_score=round(coverage, 2),
            )
        )

    return stats


async def get_heatmap_at_date(
    db: AsyncSession,
    plan_id: UUID,
    building_id: UUID,
    target_date: date,
) -> PlanHeatmap:
    """Generate a heatmap snapshot as it would have been at *target_date*.

    Only annotations created on or before target_date are included.
    Decay is computed relative to target_date.
    """
    # Convert date to datetime for comparisons
    target_dt = datetime(target_date.year, target_date.month, target_date.day)

    # Load annotations created on or before target_date
    result = await db.execute(
        select(PlanAnnotation).where(
            PlanAnnotation.plan_id == plan_id,
            PlanAnnotation.building_id == building_id,
            PlanAnnotation.created_at <= target_dt,
        )
    )
    annotations = list(result.scalars().all())

    points: list[HeatmapPoint] = []
    summary: dict[str, int] = defaultdict(int)

    # Collect sample_ids for confidence
    sample_ids: set[UUID] = set()
    for ann in annotations:
        if ann.sample_id is not None:
            sample_ids.add(ann.sample_id)

    samples_by_id: dict[UUID, Sample] = {}
    if sample_ids:
        sample_result = await db.execute(select(Sample).where(Sample.id.in_(sample_ids)))
        samples_by_id = {s.id: s for s in sample_result.scalars().all()}

    for ann in annotations:
        category, base_intensity = _ANNOTATION_TYPE_MAP.get(ann.annotation_type, ("trust", 0.3))
        decay = _compute_decay_factor(ann.created_at, target_dt)
        intensity = round(base_intensity * decay, 4)

        sample_obj = samples_by_id.get(ann.sample_id) if ann.sample_id else None
        confidence = _compute_confidence(sample_obj, target_dt)

        point = HeatmapPoint(
            x=ann.x,
            y=ann.y,
            intensity=intensity,
            category=category,
            label=ann.label,
            annotation_id=str(ann.id),
            zone_id=str(ann.zone_id) if ann.zone_id else None,
            decay_factor=decay,
            confidence=confidence,
        )
        points.append(point)
        summary[category] += 1

    annotation_count = len(annotations)
    coverage_score = min(1.0, annotation_count / 10.0)

    return PlanHeatmap(
        plan_id=str(plan_id),
        building_id=str(building_id),
        total_points=len(points),
        coverage_score=round(coverage_score, 2),
        points=points,
        summary=dict(summary),
    )


async def detect_coverage_gaps(
    db: AsyncSession,
    plan_id: UUID,
    building_id: UUID,
) -> CoverageGapReport:
    """Identify zones referenced by the plan but without annotations, or with
    stale / low-density annotations.

    Gap types:
        - "no_annotations": zone exists for this building but has zero
          annotations on this plan
        - "low_density": zone has fewer than 2 annotations on this plan
        - "stale_data": all annotations for the zone on this plan are >2 years old
    """
    now = datetime.now(UTC)

    # All zones for this building
    zone_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = {z.id: z for z in zone_result.scalars().all()}

    if not zones:
        return CoverageGapReport(
            plan_id=str(plan_id),
            building_id=str(building_id),
            gaps=[],
            overall_coverage=1.0,
        )

    # All annotations for this plan that reference a zone
    ann_result = await db.execute(
        select(PlanAnnotation).where(
            PlanAnnotation.plan_id == plan_id,
            PlanAnnotation.building_id == building_id,
        )
    )
    annotations = list(ann_result.scalars().all())

    # Group by zone_id (only those in the building's zone set)
    zone_annotations: dict[UUID, list[PlanAnnotation]] = defaultdict(list)
    for ann in annotations:
        if ann.zone_id is not None and ann.zone_id in zones:
            zone_annotations[ann.zone_id].append(ann)

    gaps: list[CoverageGap] = []
    covered_zones = 0

    for zone_id, zone in zones.items():
        anns = zone_annotations.get(zone_id, [])

        if len(anns) == 0:
            gaps.append(
                CoverageGap(
                    zone_id=str(zone_id),
                    zone_name=zone.name,
                    gap_type="no_annotations",
                    description=f"Zone '{zone.name}' has no annotations on this plan.",
                )
            )
            continue

        # Check stale: all annotations older than 2 years
        all_stale = all(_compute_decay_factor(a.created_at, now) < 1.0 for a in anns)
        if all_stale:
            gaps.append(
                CoverageGap(
                    zone_id=str(zone_id),
                    zone_name=zone.name,
                    gap_type="stale_data",
                    description=f"All annotations for zone '{zone.name}' are older than 2 years.",
                )
            )
        elif len(anns) < 2:
            gaps.append(
                CoverageGap(
                    zone_id=str(zone_id),
                    zone_name=zone.name,
                    gap_type="low_density",
                    description=f"Zone '{zone.name}' has only {len(anns)} annotation(s) on this plan.",
                )
            )
            covered_zones += 1
        else:
            covered_zones += 1

    total_zones = len(zones)
    overall_coverage = round(covered_zones / total_zones, 2) if total_zones > 0 else 1.0

    return CoverageGapReport(
        plan_id=str(plan_id),
        building_id=str(building_id),
        gaps=gaps,
        overall_coverage=overall_coverage,
    )
