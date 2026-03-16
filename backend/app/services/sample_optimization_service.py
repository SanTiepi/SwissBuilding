"""
SwissBuildingOS - Sample Optimization Service

Recommends optimal sample locations, estimates costs, evaluates adequacy,
and provides portfolio-level sampling status.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.sample_optimization import (
    BuildingSamplingStatus,
    PollutantAdequacy,
    PollutantCostBreakdown,
    PortfolioSamplingStatus,
    RecommendedSample,
    SamplingAdequacyResult,
    SamplingCostEstimate,
    SamplingOptimizationResult,
    ZoneTypeCoverage,
)
from app.services.building_data_loader import load_org_buildings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COST_PER_SAMPLE: dict[str, float] = {
    "asbestos": 150.0,
    "pcb": 200.0,
    "lead": 150.0,
    "hap": 150.0,
    "radon": 100.0,
}

SAMPLE_METHOD: dict[str, str] = {
    "asbestos": "bulk",
    "pcb": "wipe",
    "lead": "bulk",
    "hap": "bulk",
    "radon": "radon_detector",
}

AIR_SAMPLE_POLLUTANTS = {"asbestos"}
AIR_SAMPLE_COST = 300.0

# Samples older than this are considered outdated
SAMPLE_MAX_AGE_YEARS = 3

# Minimum samples per pollutant for adequacy
MIN_SAMPLES_PER_POLLUTANT: dict[str, int] = {
    "asbestos": 3,
    "pcb": 2,
    "lead": 2,
    "hap": 1,
    "radon": 1,
}

LAB_TURNAROUND_DAYS = 10

POLLUTANT_YEAR_RULES: dict[str, tuple[int | None, int | None]] = {
    "asbestos": (None, 1990),
    "pcb": (1955, 1975),
    "lead": (None, 2006),
    "hap": (None, None),
    "radon": (None, None),
}

PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _applicable_pollutants(construction_year: int | None) -> list[str]:
    """Return pollutants applicable to a building based on construction year."""
    result = []
    for pollutant, (year_from, year_to) in POLLUTANT_YEAR_RULES.items():
        if construction_year is None:
            result.append(pollutant)
            continue
        if year_from is not None and construction_year < year_from:
            continue
        if year_to is not None and construction_year > year_to:
            continue
        result.append(pollutant)
    return result


def _is_sample_outdated(sample: Sample) -> bool:
    """Check if a sample is older than SAMPLE_MAX_AGE_YEARS."""
    if sample.created_at is None:
        return True
    now = datetime.now(UTC)
    created = sample.created_at
    if created.tzinfo is None:
        age_days = (now.replace(tzinfo=None) - created).days
    else:
        age_days = (now - created).days
    return age_days > SAMPLE_MAX_AGE_YEARS * 365


def _zone_risk_priority(zone: Zone, construction_year: int | None) -> str:
    """Assign priority based on zone type and building age."""
    high_risk_types = {"basement", "technical_room", "staircase"}
    if zone.zone_type in high_risk_types:
        return "high"
    if construction_year and construction_year < 1970:
        return "high"
    if construction_year and construction_year < 1990:
        return "medium"
    return "low"


async def _load_building_with_diagnostics(db: AsyncSession, building_id: UUID) -> Building | None:
    """Load building with diagnostics and their samples."""
    result = await db.execute(
        select(Building)
        .options(selectinload(Building.diagnostics).selectinload(Diagnostic.samples))
        .where(Building.id == building_id)
    )
    return result.scalar_one_or_none()


async def _load_zones(db: AsyncSession, building_id: UUID) -> list[Zone]:
    """Load all zones for a building."""
    result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    return list(result.scalars().all())


def _collect_all_samples(building: Building) -> list[Sample]:
    """Collect all samples across all diagnostics."""
    samples: list[Sample] = []
    for diag in building.diagnostics:
        samples.extend(diag.samples)
    return samples


def _zones_with_samples(zones: list[Zone], samples: list[Sample]) -> dict[str, set[str]]:
    """Map zone floor identifiers to sampled pollutant types."""
    # Build a lookup of location_floor -> set of pollutant_types sampled
    floor_pollutants: dict[str, set[str]] = {}
    for sample in samples:
        if not _is_sample_outdated(sample) and sample.location_floor:
            floor_pollutants.setdefault(sample.location_floor, set())
            if sample.pollutant_type:
                floor_pollutants[sample.location_floor].add(sample.pollutant_type)
    return floor_pollutants


# ---------------------------------------------------------------------------
# FN1: optimize_sampling_plan
# ---------------------------------------------------------------------------


async def optimize_sampling_plan(db: AsyncSession, building_id: UUID) -> SamplingOptimizationResult | None:
    """Recommend optimal sample locations: maximize coverage with minimum samples."""
    building = await _load_building_with_diagnostics(db, building_id)
    if building is None:
        return None

    zones = await _load_zones(db, building_id)
    all_samples = _collect_all_samples(building)
    applicable = _applicable_pollutants(building.construction_year)

    # Determine which zones have current samples for which pollutants
    floor_pollutants = _zones_with_samples(zones, all_samples)

    recommended: list[RecommendedSample] = []
    zones_already_sampled: set[UUID] = set()

    for zone in zones:
        zone_floor = str(zone.floor_number) if zone.floor_number is not None else zone.name
        sampled_pollutants = floor_pollutants.get(zone_floor, set())

        # Check for outdated samples in this zone
        zone_has_outdated = False
        for sample in all_samples:
            if sample.location_floor == zone_floor and _is_sample_outdated(sample):
                zone_has_outdated = True
                break

        missing_pollutants = [p for p in applicable if p not in sampled_pollutants]

        if not missing_pollutants and not zone_has_outdated:
            zones_already_sampled.add(zone.id)
            continue

        if sampled_pollutants and not missing_pollutants:
            zones_already_sampled.add(zone.id)

        priority = _zone_risk_priority(zone, building.construction_year)

        for pollutant in missing_pollutants:
            reason = "unsampled"
            if zone_has_outdated and pollutant in sampled_pollutants:
                reason = "outdated"

            cost = COST_PER_SAMPLE.get(pollutant, 150.0)
            method = SAMPLE_METHOD.get(pollutant, "bulk")

            recommended.append(
                RecommendedSample(
                    zone_id=zone.id,
                    zone_name=zone.name,
                    zone_type=zone.zone_type,
                    pollutant_type=pollutant,
                    sample_method=method,
                    priority=priority,
                    reason=reason,
                    estimated_cost_chf=cost,
                )
            )

    # Also check for zones with outdated samples that need refresh
    for zone in zones:
        zone_floor = str(zone.floor_number) if zone.floor_number is not None else zone.name
        for sample in all_samples:
            if (
                sample.location_floor == zone_floor
                and _is_sample_outdated(sample)
                and sample.pollutant_type
                and not any(r.zone_id == zone.id and r.pollutant_type == sample.pollutant_type for r in recommended)
            ):
                cost = COST_PER_SAMPLE.get(sample.pollutant_type, 150.0)
                method = SAMPLE_METHOD.get(sample.pollutant_type, "bulk")
                recommended.append(
                    RecommendedSample(
                        zone_id=zone.id,
                        zone_name=zone.name,
                        zone_type=zone.zone_type,
                        pollutant_type=sample.pollutant_type,
                        sample_method=method,
                        priority="medium",
                        reason="outdated",
                        estimated_cost_chf=cost,
                    )
                )

    # Sort: critical > high > medium > low
    recommended.sort(key=lambda r: PRIORITY_ORDER.get(r.priority, 3))

    total_cost = sum(r.estimated_cost_chf for r in recommended)
    total_zones = len(zones)
    zones_sampled = len(zones_already_sampled)
    coverage_before = (zones_sampled / total_zones) if total_zones > 0 else 0.0
    zones_needing = total_zones - zones_sampled
    coverage_after = 1.0 if recommended else coverage_before

    return SamplingOptimizationResult(
        building_id=building_id,
        total_zones=total_zones,
        zones_sampled=zones_sampled,
        zones_needing_samples=zones_needing,
        recommended_samples=recommended,
        total_estimated_cost_chf=round(total_cost, 2),
        coverage_before=round(coverage_before, 2),
        coverage_after=round(coverage_after, 2),
    )


# ---------------------------------------------------------------------------
# FN2: estimate_sampling_cost
# ---------------------------------------------------------------------------


async def estimate_sampling_cost(db: AsyncSession, building_id: UUID) -> SamplingCostEstimate | None:
    """Cost estimate for recommended sampling by pollutant type."""
    optimization = await optimize_sampling_plan(db, building_id)
    if optimization is None:
        return None

    # Group by pollutant
    pollutant_counts: dict[str, int] = {}
    for rec in optimization.recommended_samples:
        pollutant_counts[rec.pollutant_type] = pollutant_counts.get(rec.pollutant_type, 0) + 1

    breakdown: list[PollutantCostBreakdown] = []
    total_cost = 0.0
    total_samples = 0

    for pollutant, count in sorted(pollutant_counts.items()):
        cost_per = COST_PER_SAMPLE.get(pollutant, 150.0)
        subtotal = cost_per * count
        breakdown.append(
            PollutantCostBreakdown(
                pollutant_type=pollutant,
                sample_count=count,
                cost_per_sample_chf=cost_per,
                total_chf=round(subtotal, 2),
            )
        )
        total_cost += subtotal
        total_samples += count

    return SamplingCostEstimate(
        building_id=building_id,
        pollutant_breakdown=breakdown,
        total_samples=total_samples,
        total_cost_chf=round(total_cost, 2),
        lab_turnaround_days=LAB_TURNAROUND_DAYS,
    )


# ---------------------------------------------------------------------------
# FN3: evaluate_sampling_adequacy
# ---------------------------------------------------------------------------


async def evaluate_sampling_adequacy(db: AsyncSession, building_id: UUID) -> SamplingAdequacyResult | None:
    """Is current sampling sufficient? Statistical confidence, coverage, gaps."""
    building = await _load_building_with_diagnostics(db, building_id)
    if building is None:
        return None

    zones = await _load_zones(db, building_id)
    all_samples = _collect_all_samples(building)
    applicable = _applicable_pollutants(building.construction_year)

    # Current (non-outdated) samples
    current_samples = [s for s in all_samples if not _is_sample_outdated(s)]

    # --- Zone type coverage ---
    zone_type_map: dict[str, list[Zone]] = {}
    for zone in zones:
        zone_type_map.setdefault(zone.zone_type, []).append(zone)

    floor_pollutants = _zones_with_samples(zones, current_samples)

    zone_coverages: list[ZoneTypeCoverage] = []
    total_zone_count = 0
    total_sampled_count = 0

    for ztype, zone_list in sorted(zone_type_map.items()):
        sampled_count = 0
        for z in zone_list:
            zfloor = str(z.floor_number) if z.floor_number is not None else z.name
            if zfloor in floor_pollutants:
                sampled_count += 1
        pct = (sampled_count / len(zone_list) * 100) if zone_list else 0.0
        zone_coverages.append(
            ZoneTypeCoverage(
                zone_type=ztype,
                total_zones=len(zone_list),
                sampled_zones=sampled_count,
                coverage_pct=round(pct, 1),
            )
        )
        total_zone_count += len(zone_list)
        total_sampled_count += sampled_count

    overall_coverage = (total_sampled_count / total_zone_count * 100) if total_zone_count else 0.0

    # --- Pollutant adequacy ---
    pollutant_sample_counts: dict[str, int] = {}
    for s in current_samples:
        if s.pollutant_type:
            pollutant_sample_counts[s.pollutant_type] = pollutant_sample_counts.get(s.pollutant_type, 0) + 1

    pollutant_adequacies: list[PollutantAdequacy] = []
    all_adequate = True
    additional_needed = 0

    for pollutant in applicable:
        count = pollutant_sample_counts.get(pollutant, 0)
        min_req = MIN_SAMPLES_PER_POLLUTANT.get(pollutant, 1)
        adequate = count >= min_req
        if not adequate:
            all_adequate = False
            additional_needed += min_req - count
        pollutant_adequacies.append(
            PollutantAdequacy(
                pollutant_type=pollutant,
                samples_count=count,
                min_recommended=min_req,
                is_adequate=adequate,
            )
        )

    # Confidence: combine coverage and pollutant adequacy
    coverage_factor = min(overall_coverage / 100.0, 1.0)
    adequate_count = sum(1 for pa in pollutant_adequacies if pa.is_adequate)
    pollutant_factor = adequate_count / len(pollutant_adequacies) if pollutant_adequacies else 0.0
    confidence = round((coverage_factor * 0.5 + pollutant_factor * 0.5), 2)

    is_adequate = all_adequate and overall_coverage >= 80.0

    return SamplingAdequacyResult(
        building_id=building_id,
        is_adequate=is_adequate,
        confidence_level=confidence,
        overall_coverage_pct=round(overall_coverage, 1),
        zone_type_coverage=zone_coverages,
        pollutant_adequacy=pollutant_adequacies,
        recommended_additional_samples=additional_needed,
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_sampling_status
# ---------------------------------------------------------------------------


async def get_portfolio_sampling_status(db: AsyncSession, org_id: UUID) -> PortfolioSamplingStatus | None:
    """Org-level sampling status across all buildings."""
    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioSamplingStatus(
            organization_id=org_id,
            total_buildings=0,
            buildings_adequate=0,
            buildings_needing_resampling=0,
            total_estimated_cost_chf=0.0,
            priority_queue=[],
        )

    status_list: list[BuildingSamplingStatus] = []
    adequate_count = 0
    resampling_count = 0
    total_cost = 0.0

    for bld in buildings:
        adequacy = await evaluate_sampling_adequacy(db, bld.id)
        cost_est = await estimate_sampling_cost(db, bld.id)

        is_adequate = adequacy.is_adequate if adequacy else False
        coverage = adequacy.overall_coverage_pct if adequacy else 0.0
        est_cost = cost_est.total_cost_chf if cost_est else 0.0
        needs_resample = not is_adequate

        if is_adequate:
            adequate_count += 1
        if needs_resample:
            resampling_count += 1

        total_cost += est_cost

        # Priority based on coverage
        if coverage < 25:
            priority = "critical"
        elif coverage < 50:
            priority = "high"
        elif coverage < 80:
            priority = "medium"
        else:
            priority = "low"

        status_list.append(
            BuildingSamplingStatus(
                building_id=bld.id,
                address=bld.address,
                is_adequate=is_adequate,
                coverage_pct=coverage,
                needs_resampling=needs_resample,
                estimated_cost_chf=est_cost,
                priority=priority,
            )
        )

    # Sort by priority (critical first)
    status_list.sort(key=lambda s: PRIORITY_ORDER.get(s.priority, 3))

    return PortfolioSamplingStatus(
        organization_id=org_id,
        total_buildings=len(buildings),
        buildings_adequate=adequate_count,
        buildings_needing_resampling=resampling_count,
        total_estimated_cost_chf=round(total_cost, 2),
        priority_queue=status_list,
    )
