"""
SwissBuildingOS - Spatial Risk Mapping Service

Zone-by-zone spatial risk analysis: composite risk scores, floor profiles,
contamination propagation via zone adjacency, and coverage gap detection.
"""

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.spatial_risk_mapping import (
    AreaStatus,
    BuildingRiskMap,
    ColorTier,
    CoverageGap,
    FloorCoverageStatus,
    FloorRiskProfile,
    FloorZoneDetail,
    GapPriority,
    PollutantDistribution,
    PropagationEdge,
    RiskPropagationAnalysis,
    SpatialCoverageGaps,
    ZonePropagatedRisk,
    ZoneRiskOverlay,
)

# ---------------------------------------------------------------------------
# Risk level weights for composite scoring
# ---------------------------------------------------------------------------
_RISK_LEVEL_WEIGHT = {
    "critical": 1.0,
    "high": 0.75,
    "medium": 0.5,
    "low": 0.25,
    "unknown": 0.3,
}

# Propagation dampening factor: neighbor risk is reduced by this factor
_PROPAGATION_FACTOR = 0.4

# Habitable zones get higher gap priority
_HABITABLE_ZONE_TYPES = {"floor", "room", "staircase"}


def _score_to_color_tier(score: float) -> ColorTier:
    """Map a 0-1 risk score to a color tier."""
    if score >= 0.75:
        return ColorTier.red
    if score >= 0.5:
        return ColorTier.orange
    if score >= 0.25:
        return ColorTier.yellow
    return ColorTier.green


def _risk_level_to_score(risk_level: str | None) -> float:
    """Convert a sample risk_level string to a numeric score."""
    if not risk_level:
        return 0.0
    return _RISK_LEVEL_WEIGHT.get(risk_level.lower(), 0.0)


def _area_status_from_score(score: float, has_samples: bool) -> AreaStatus:
    """Determine area status from risk score and sampling state."""
    if not has_samples:
        return AreaStatus.unknown
    if score >= 0.5:
        return AreaStatus.restricted
    return AreaStatus.safe


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


async def _load_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _load_zones(db: AsyncSession, building_id: UUID) -> list[Zone]:
    result = await db.execute(
        select(Zone)
        .where(Zone.building_id == building_id)
        .options(selectinload(Zone.elements).selectinload(BuildingElement.materials))
        .options(selectinload(Zone.children))
    )
    return list(result.scalars().unique().all())


async def _load_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    return list(result.scalars().all())


async def _load_diagnostics(db: AsyncSession, building_id: UUID) -> list[Diagnostic]:
    result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Zone-sample matching
# ---------------------------------------------------------------------------


def _match_samples_to_zones(
    zones: list[Zone],
    samples: list[Sample],
) -> dict[UUID, list[Sample]]:
    """Match samples to zones by location_floor / zone name."""
    zone_samples: dict[UUID, list[Sample]] = defaultdict(list)

    for sample in samples:
        matched = False
        if sample.location_floor:
            for zone in zones:
                if zone.name and sample.location_floor.lower() in zone.name.lower():
                    zone_samples[zone.id].append(sample)
                    matched = True
                    break
        if not matched and zones:
            zone_samples[zones[0].id].append(sample)

    return dict(zone_samples)


def _get_zone_pollutants_from_materials(zone: Zone) -> list[str]:
    """Extract pollutant types from zone materials."""
    pollutants: list[str] = []
    for element in zone.elements:
        for material in element.materials:
            if material.contains_pollutant and material.pollutant_type and material.pollutant_type not in pollutants:
                pollutants.append(material.pollutant_type)
    return pollutants


def _compute_zone_risk_score(
    zone: Zone,
    zone_sample_list: list[Sample],
) -> tuple[float, str | None, list[str]]:
    """
    Compute composite risk score for a zone from samples + materials.
    Returns (score, dominant_pollutant, pollutant_types).
    """
    scores: list[float] = []
    pollutant_scores: dict[str, float] = {}

    # From samples
    for sample in zone_sample_list:
        s = _risk_level_to_score(sample.risk_level)
        # Threshold exceeded bumps score
        if sample.threshold_exceeded:
            s = max(s, 0.75)
        scores.append(s)
        if sample.pollutant_type:
            pollutant_scores[sample.pollutant_type] = max(pollutant_scores.get(sample.pollutant_type, 0.0), s)

    # From materials
    material_pollutants = _get_zone_pollutants_from_materials(zone)
    for pt in material_pollutants:
        mat_score = 0.5  # confirmed pollutant in material = medium baseline
        scores.append(mat_score)
        pollutant_scores[pt] = max(pollutant_scores.get(pt, 0.0), mat_score)

    if not scores:
        return 0.0, None, []

    composite = max(scores)
    all_pollutants = list(pollutant_scores.keys())
    dominant = max(pollutant_scores, key=pollutant_scores.get) if pollutant_scores else None
    return composite, dominant, all_pollutants


# ---------------------------------------------------------------------------
# FN1: Building Risk Map
# ---------------------------------------------------------------------------


async def get_building_risk_map(
    db: AsyncSession,
    building_id: UUID,
) -> BuildingRiskMap:
    """Zone-by-zone risk overlay for a building."""
    await _load_building(db, building_id)
    zones = await _load_zones(db, building_id)
    samples = await _load_samples(db, building_id)
    zone_samples = _match_samples_to_zones(zones, samples)

    overlays: list[ZoneRiskOverlay] = []
    risk_scores: list[float] = []
    zones_at_risk = 0

    for zone in zones:
        z_samples = zone_samples.get(zone.id, [])
        score, dominant, pollutant_types = _compute_zone_risk_score(zone, z_samples)
        color = _score_to_color_tier(score)

        if score >= 0.5:
            zones_at_risk += 1
        risk_scores.append(score)

        overlays.append(
            ZoneRiskOverlay(
                zone_id=zone.id,
                zone_name=zone.name,
                zone_type=zone.zone_type,
                floor_number=zone.floor_number,
                composite_risk_score=score,
                color_tier=color,
                dominant_pollutant=dominant,
                sample_density=len(z_samples),
                pollutant_types=pollutant_types,
            )
        )

    overall = max(risk_scores) if risk_scores else 0.0

    return BuildingRiskMap(
        building_id=building_id,
        zones=overlays,
        total_zones=len(zones),
        zones_at_risk=zones_at_risk,
        overall_risk_score=overall,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: Floor Risk Profile
# ---------------------------------------------------------------------------


async def get_floor_risk_profile(
    db: AsyncSession,
    building_id: UUID,
    floor: int,
) -> FloorRiskProfile:
    """Single floor detail: zones, pollutant distribution, safe vs restricted areas."""
    await _load_building(db, building_id)
    all_zones = await _load_zones(db, building_id)
    samples = await _load_samples(db, building_id)
    zone_samples = _match_samples_to_zones(all_zones, samples)

    floor_zones = [z for z in all_zones if z.floor_number == floor]
    zone_details: list[FloorZoneDetail] = []
    pollutant_agg: dict[str, dict] = {}
    safe_count = 0
    restricted_count = 0
    unknown_count = 0
    sampled_count = 0

    for zone in floor_zones:
        z_samples = zone_samples.get(zone.id, [])
        score, _, pollutant_types = _compute_zone_risk_score(zone, z_samples)
        color = _score_to_color_tier(score)
        has_samples = len(z_samples) > 0
        status = _area_status_from_score(score, has_samples)

        if status == AreaStatus.safe:
            safe_count += 1
        elif status == AreaStatus.restricted:
            restricted_count += 1
        else:
            unknown_count += 1

        if has_samples:
            sampled_count += 1

        # Aggregate pollutant distribution
        for sample in z_samples:
            if sample.pollutant_type:
                pt = sample.pollutant_type
                if pt not in pollutant_agg:
                    pollutant_agg[pt] = {
                        "zone_ids": set(),
                        "sample_count": 0,
                        "max_concentration": None,
                        "unit": None,
                    }
                pollutant_agg[pt]["zone_ids"].add(zone.id)
                pollutant_agg[pt]["sample_count"] += 1
                if sample.concentration is not None:
                    current_max = pollutant_agg[pt]["max_concentration"]
                    if current_max is None or sample.concentration > current_max:
                        pollutant_agg[pt]["max_concentration"] = sample.concentration
                        pollutant_agg[pt]["unit"] = sample.unit

        zone_details.append(
            FloorZoneDetail(
                zone_id=zone.id,
                zone_name=zone.name,
                zone_type=zone.zone_type,
                area_status=status,
                risk_score=score,
                color_tier=color,
                pollutants=pollutant_types,
                sample_count=len(z_samples),
            )
        )

    distributions = [
        PollutantDistribution(
            pollutant_type=pt,
            zone_count=len(data["zone_ids"]),
            sample_count=data["sample_count"],
            max_concentration=data["max_concentration"],
            unit=data["unit"],
        )
        for pt, data in pollutant_agg.items()
    ]

    total = len(floor_zones)
    coverage = (sampled_count / total * 100.0) if total > 0 else 0.0

    return FloorRiskProfile(
        building_id=building_id,
        floor_number=floor,
        zones=zone_details,
        pollutant_distribution=distributions,
        safe_zones=safe_count,
        restricted_zones=restricted_count,
        unknown_zones=unknown_count,
        coverage_percentage=coverage,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: Risk Propagation Analysis
# ---------------------------------------------------------------------------


def _build_adjacency(zones: list[Zone]) -> dict[UUID, list[UUID]]:
    """Build adjacency map from parent_zone_id relationships (bidirectional)."""
    adj: dict[UUID, list[UUID]] = defaultdict(list)
    for zone in zones:
        if zone.parent_zone_id:
            adj[zone.id].append(zone.parent_zone_id)
            adj[zone.parent_zone_id].append(zone.id)
    return dict(adj)


async def get_risk_propagation_analysis(
    db: AsyncSession,
    building_id: UUID,
) -> RiskPropagationAnalysis:
    """Adjacent zone contamination risk via parent_zone_id adjacency."""
    await _load_building(db, building_id)
    zones = await _load_zones(db, building_id)
    samples = await _load_samples(db, building_id)
    zone_samples = _match_samples_to_zones(zones, samples)

    # Compute own risk per zone
    zone_own_risk: dict[UUID, float] = {}
    zone_dominant: dict[UUID, str | None] = {}
    zone_by_id: dict[UUID, Zone] = {}

    for zone in zones:
        zone_by_id[zone.id] = zone
        z_samples = zone_samples.get(zone.id, [])
        score, dominant, _ = _compute_zone_risk_score(zone, z_samples)
        zone_own_risk[zone.id] = score
        zone_dominant[zone.id] = dominant

    adjacency = _build_adjacency(zones)

    edges: list[PropagationEdge] = []
    zone_propagated: dict[UUID, float] = defaultdict(float)
    zone_contributors: dict[UUID, list[str]] = defaultdict(list)

    for zone in zones:
        neighbors = adjacency.get(zone.id, [])
        for neighbor_id in neighbors:
            if neighbor_id not in zone_by_id:
                continue
            neighbor_risk = zone_own_risk.get(neighbor_id, 0.0)
            if neighbor_risk > 0.0:
                propagated = neighbor_risk * _PROPAGATION_FACTOR
                zone_propagated[zone.id] = max(zone_propagated[zone.id], propagated)
                zone_contributors[zone.id].append(zone_by_id[neighbor_id].name)
                edges.append(
                    PropagationEdge(
                        source_zone_id=neighbor_id,
                        source_zone_name=zone_by_id[neighbor_id].name,
                        target_zone_id=zone.id,
                        target_zone_name=zone.name,
                        source_risk_score=neighbor_risk,
                        propagated_risk_score=propagated,
                        dominant_pollutant=zone_dominant.get(neighbor_id),
                        relationship="parent_child",
                    )
                )

    zone_results: list[ZonePropagatedRisk] = []
    elevated_count = 0

    for zone in zones:
        own = zone_own_risk.get(zone.id, 0.0)
        propagated = zone_propagated.get(zone.id, 0.0)
        combined = min(1.0, max(own, propagated))
        color = _score_to_color_tier(combined)

        if propagated > own:
            elevated_count += 1

        zone_results.append(
            ZonePropagatedRisk(
                zone_id=zone.id,
                zone_name=zone.name,
                zone_type=zone.zone_type,
                own_risk_score=own,
                propagated_risk_score=propagated,
                combined_risk_score=combined,
                color_tier=color,
                contributing_zones=zone_contributors.get(zone.id, []),
            )
        )

    return RiskPropagationAnalysis(
        building_id=building_id,
        zones=zone_results,
        edges=edges,
        total_zones=len(zones),
        zones_with_elevated_risk=elevated_count,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: Spatial Coverage Gaps
# ---------------------------------------------------------------------------


async def get_spatial_coverage_gaps(
    db: AsyncSession,
    building_id: UUID,
) -> SpatialCoverageGaps:
    """Zones without samples, floors without diagnostics, areas needing investigation."""
    await _load_building(db, building_id)
    zones = await _load_zones(db, building_id)
    samples = await _load_samples(db, building_id)
    diagnostics = await _load_diagnostics(db, building_id)
    zone_samples = _match_samples_to_zones(zones, samples)

    gaps: list[CoverageGap] = []
    sampled_zone_ids: set[UUID] = set()

    # Identify zones with and without samples
    for zone in zones:
        z_samples = zone_samples.get(zone.id, [])
        if z_samples:
            sampled_zone_ids.add(zone.id)
        else:
            # Zone without samples = coverage gap
            is_habitable = zone.zone_type in _HABITABLE_ZONE_TYPES
            priority = GapPriority.high if is_habitable else GapPriority.medium
            gaps.append(
                CoverageGap(
                    zone_id=zone.id,
                    zone_name=zone.name,
                    zone_type=zone.zone_type,
                    floor_number=zone.floor_number,
                    gap_type="unsampled_zone",
                    priority=priority,
                    reason=f"Zone '{zone.name}' has no samples",
                )
            )

    # Check floor coverage
    floors: dict[int, list[Zone]] = defaultdict(list)
    for zone in zones:
        if zone.floor_number is not None:
            floors[zone.floor_number].append(zone)

    # Check which floors have diagnostics (via samples on that floor)
    floor_has_diagnostic: set[int] = set()
    for sample in samples:
        if sample.location_floor:
            try:
                fl = int(sample.location_floor)
                floor_has_diagnostic.add(fl)
            except ValueError:
                pass
    # Also check from diagnostic records
    for _d in diagnostics:
        # diagnostics cover the building, but we track floors with any sample
        pass

    floor_statuses: list[FloorCoverageStatus] = []
    for fl_num in sorted(floors.keys()):
        fl_zones = floors[fl_num]
        fl_sampled = sum(1 for z in fl_zones if z.id in sampled_zone_ids)
        total = len(fl_zones)
        coverage = (fl_sampled / total * 100.0) if total > 0 else 0.0
        has_diag = fl_num in floor_has_diagnostic or len(diagnostics) > 0

        floor_statuses.append(
            FloorCoverageStatus(
                floor_number=fl_num,
                total_zones=total,
                sampled_zones=fl_sampled,
                has_diagnostic=has_diag,
                coverage_percentage=coverage,
            )
        )

        if coverage == 0.0 and total > 0:
            gaps.append(
                CoverageGap(
                    zone_id=None,
                    zone_name=None,
                    zone_type=None,
                    floor_number=fl_num,
                    gap_type="unsampled_floor",
                    priority=GapPriority.critical,
                    reason=f"Floor {fl_num} has {total} zones but no samples",
                )
            )

    # Check for zones with old/no diagnostics (building has no diagnostics at all)
    if not diagnostics and zones:
        gaps.append(
            CoverageGap(
                zone_id=None,
                zone_name=None,
                zone_type=None,
                floor_number=None,
                gap_type="no_diagnostics",
                priority=GapPriority.critical,
                reason="Building has no diagnostics at all",
            )
        )

    # Sort gaps by priority
    priority_order = {
        GapPriority.critical: 0,
        GapPriority.high: 1,
        GapPriority.medium: 2,
        GapPriority.low: 3,
    }
    gaps.sort(key=lambda g: priority_order[g.priority])

    total_zones = len(zones)
    sampled_count = len(sampled_zone_ids)
    overall_coverage = (sampled_count / total_zones * 100.0) if total_zones > 0 else 0.0

    return SpatialCoverageGaps(
        building_id=building_id,
        gaps=gaps,
        floor_coverage=floor_statuses,
        total_zones=total_zones,
        sampled_zones=sampled_count,
        unsampled_zones=total_zones - sampled_count,
        overall_coverage_percentage=overall_coverage,
        evaluated_at=datetime.now(UTC),
    )
