"""
SwissBuildingOS - Plan Overlay Service (Programme G)

Generates visual overlay data for technical plans:
- Pollutant zone overlay (confirmed/suspected/negative/unknown)
- Trust/confidence heatmap overlay (documentation quality per zone)
- Intervention overlay (completed/planned works on plan)
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.technical_plan import TechnicalPlan
from app.models.zone import Zone

# ---------------------------------------------------------------------------
# Pollutant status colours
# ---------------------------------------------------------------------------

_POLLUTANT_STATUS_COLORS: dict[str, str] = {
    "confirmed": "#FF0000",
    "suspected": "#FFA500",
    "negative": "#00FF00",
    "unknown": "#808080",
}

# ---------------------------------------------------------------------------
# Trust gradient (blue=good, red=gaps)
# ---------------------------------------------------------------------------


def _trust_color(score: float) -> str:
    """Return hex colour on a blue(100)->red(0) gradient."""
    # Clamp
    score = max(0.0, min(100.0, score))
    # Interpolate R(255->0) G(0) B(0->255) — simplified
    ratio = score / 100.0
    r = int(255 * (1 - ratio))
    b = int(255 * ratio)
    return f"#{r:02X}00{b:02X}"


# ---------------------------------------------------------------------------
# Intervention status colours
# ---------------------------------------------------------------------------

_INTERVENTION_STATUS_COLORS: dict[str, str] = {
    "completed": "#2E7D32",
    "in_progress": "#F9A825",
    "planned": "#1565C0",
    "cancelled": "#9E9E9E",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_pollutant_overlay(
    db: AsyncSession,
    plan_id: UUID,
) -> dict:
    """Generate pollutant zone overlay for a technical plan.

    Queries zones + samples linked to this plan's building.
    Returns zone polygons coloured by pollutant status, sample markers,
    and a legend with counts per status.
    """
    # Load plan to get building_id
    plan_result = await db.execute(select(TechnicalPlan).where(TechnicalPlan.id == plan_id))
    plan = plan_result.scalar_one_or_none()
    if plan is None:
        return {"zones": [], "samples": [], "legend": []}

    building_id = plan.building_id

    # Load zones for this building
    zone_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = list(zone_result.scalars().all())

    if not zones:
        return {"zones": [], "samples": [], "legend": []}

    # Load samples linked to diagnostics of this building via diagnostic
    from app.models.diagnostic import Diagnostic

    diag_result = await db.execute(select(Diagnostic.id).where(Diagnostic.building_id == building_id))
    diag_ids = [row[0] for row in diag_result.all()]

    samples: list[Sample] = []
    if diag_ids:
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    # Group samples by zone-ish association (floor matching)
    # Build zone overlay entries
    status_counts: dict[str, int] = defaultdict(int)
    zone_overlays: list[dict] = []

    # Determine pollutant status per zone based on samples in same floor
    zone_floor_map: dict[int | None, list[Zone]] = defaultdict(list)
    for z in zones:
        zone_floor_map[z.floor_number].append(z)

    # Map samples to floors
    samples_by_floor: dict[str | None, list[Sample]] = defaultdict(list)
    for s in samples:
        samples_by_floor[s.location_floor].append(s)

    for idx, z in enumerate(zones):
        # Try to find samples on same floor
        floor_key = str(z.floor_number) if z.floor_number is not None else None
        floor_samples = samples_by_floor.get(floor_key, [])

        # Determine status from samples
        has_positive = any(s.threshold_exceeded for s in floor_samples)
        has_negative = any(s.concentration is not None and not s.threshold_exceeded for s in floor_samples)
        has_suspected = any(
            s.risk_level in ("medium", "high", "critical") and not s.threshold_exceeded for s in floor_samples
        )

        if has_positive:
            status = "confirmed"
        elif has_suspected:
            status = "suspected"
        elif has_negative:
            status = "negative"
        else:
            status = "unknown"

        status_counts[status] += 1

        # Position zones in a grid layout on the plan
        row = idx // 3
        col = idx % 3
        zone_overlays.append(
            {
                "zone_id": str(z.id),
                "zone_type": z.zone_type,
                "x": round(0.1 + col * 0.3, 2),
                "y": round(0.1 + row * 0.3, 2),
                "width": 0.25,
                "height": 0.25,
                "pollutant_status": status,
                "color": _POLLUTANT_STATUS_COLORS[status],
                "label": z.name,
                "confidence": 0.9 if has_positive or has_negative else 0.5,
            }
        )

    # Build sample markers
    sample_overlays: list[dict] = []
    for idx, s in enumerate(samples):
        sample_overlays.append(
            {
                "sample_id": str(s.id),
                "x": round(0.05 + (idx % 10) * 0.09, 2),
                "y": round(0.05 + (idx // 10) * 0.09, 2),
                "result": "positive" if s.threshold_exceeded else "negative",
                "pollutant": s.pollutant_type,
                "concentration": s.concentration,
            }
        )

    # Build legend
    legend = [
        {"status": status, "color": _POLLUTANT_STATUS_COLORS[status], "count": count}
        for status, count in sorted(status_counts.items())
    ]

    return {"zones": zone_overlays, "samples": sample_overlays, "legend": legend}


async def generate_trust_overlay(
    db: AsyncSession,
    plan_id: UUID,
) -> dict:
    """Generate trust/confidence heatmap overlay for a technical plan.

    Zones with good documentation (diagnostics, samples, recent data) = blue.
    Zones with gaps (no diagnostics, no samples, stale data) = red.
    Returns per-zone trust scores and an overall trust score.
    """
    plan_result = await db.execute(select(TechnicalPlan).where(TechnicalPlan.id == plan_id))
    plan = plan_result.scalar_one_or_none()
    if plan is None:
        return {"zones": [], "overall_trust": 0.0}

    building_id = plan.building_id

    # Load zones
    zone_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = list(zone_result.scalars().all())

    if not zones:
        return {"zones": [], "overall_trust": 0.0}

    # Load diagnostics and samples for trust computation
    from app.models.diagnostic import Diagnostic

    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    diag_ids = [d.id for d in diagnostics]
    samples: list[Sample] = []
    if diag_ids:
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    # Load interventions
    intervention_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(intervention_result.scalars().all())

    # Compute trust per zone
    zone_overlays: list[dict] = []
    total_trust = 0.0

    # Samples by floor for matching
    samples_by_floor: dict[str | None, list[Sample]] = defaultdict(list)
    for s in samples:
        samples_by_floor[s.location_floor].append(s)

    for idx, z in enumerate(zones):
        trust_score = 0.0
        missing_info: list[str] = []

        # Base: has diagnostics? (+30)
        if diagnostics:
            trust_score += 30.0
        else:
            missing_info.append("no_diagnostics")

        # Samples on this floor? (+30)
        floor_key = str(z.floor_number) if z.floor_number is not None else None
        floor_samples = samples_by_floor.get(floor_key, [])
        if floor_samples:
            trust_score += 30.0
            # Lab results? (+10)
            if any(s.concentration is not None for s in floor_samples):
                trust_score += 10.0
            else:
                missing_info.append("no_lab_results")
        else:
            missing_info.append("no_samples")

        # Interventions touching this zone? (+15)
        zone_interventions = [
            i
            for i in interventions
            if i.zones_affected and isinstance(i.zones_affected, list) and str(z.id) in i.zones_affected
        ]
        if zone_interventions:
            trust_score += 15.0
        else:
            missing_info.append("no_interventions")

        # Surface area known? (+5)
        if z.surface_area_m2 is not None:
            trust_score += 5.0
        else:
            missing_info.append("no_surface_area")

        # Description present? (+5)
        if z.description:
            trust_score += 5.0
        else:
            missing_info.append("no_description")

        # Usage type set? (+5)
        if z.usage_type:
            trust_score += 5.0
        else:
            missing_info.append("no_usage_type")

        trust_score = min(100.0, trust_score)
        total_trust += trust_score

        row = idx // 3
        col = idx % 3
        zone_overlays.append(
            {
                "zone_id": str(z.id),
                "x": round(0.1 + col * 0.3, 2),
                "y": round(0.1 + row * 0.3, 2),
                "width": 0.25,
                "height": 0.25,
                "trust_score": round(trust_score, 1),
                "color": _trust_color(trust_score),
                "missing_info": missing_info,
            }
        )

    overall = round(total_trust / len(zones), 1) if zones else 0.0

    return {"zones": zone_overlays, "overall_trust": overall}


async def generate_intervention_overlay(
    db: AsyncSession,
    plan_id: UUID,
) -> dict:
    """Show completed/planned interventions on a technical plan.

    Returns intervention markers positioned on the plan, plus a coverage
    percentage indicating how many zones have at least one intervention.
    """
    plan_result = await db.execute(select(TechnicalPlan).where(TechnicalPlan.id == plan_id))
    plan = plan_result.scalar_one_or_none()
    if plan is None:
        return {"interventions": [], "coverage_pct": 0.0}

    building_id = plan.building_id

    # Load zones for coverage calculation
    zone_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    zones = list(zone_result.scalars().all())
    zone_ids_set = {str(z.id) for z in zones}

    # Load interventions
    intervention_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
    interventions = list(intervention_result.scalars().all())

    if not interventions:
        return {"interventions": [], "coverage_pct": 0.0}

    # Build intervention markers
    intervention_overlays: list[dict] = []
    covered_zones: set[str] = set()

    for idx, interv in enumerate(interventions):
        # Track which zones are covered
        affected = interv.zones_affected or []
        if isinstance(affected, list):
            for zid in affected:
                if str(zid) in zone_ids_set:
                    covered_zones.add(str(zid))

        color = _INTERVENTION_STATUS_COLORS.get(interv.status, "#9E9E9E")

        intervention_overlays.append(
            {
                "intervention_id": str(interv.id),
                "zone_id": affected[0] if affected else None,
                "x": round(0.1 + (idx % 5) * 0.18, 2),
                "y": round(0.1 + (idx // 5) * 0.18, 2),
                "type": interv.intervention_type,
                "status": interv.status,
                "date": str(interv.date_start) if interv.date_start else None,
                "color": color,
            }
        )

    coverage_pct = round((len(covered_zones) / len(zones)) * 100, 1) if zones else 0.0

    return {"interventions": intervention_overlays, "coverage_pct": coverage_pct}
