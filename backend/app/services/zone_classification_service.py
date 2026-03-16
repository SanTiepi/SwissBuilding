"""
SwissBuildingOS - Zone Classification Service

Classifies building zones by contamination status based on samples, materials,
diagnostics, interventions, and field observations. Provides hierarchy roll-up,
boundary zone identification, and transition history.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building_element import BuildingElement
from app.models.diagnostic import Diagnostic
from app.models.field_observation import FieldObservation
from app.models.intervention import Intervention
from app.models.material import Material
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.zone_classification import (
    CONTAMINATION_SEVERITY,
    BoundaryZone,
    BoundaryZoneResult,
    ContaminationStatus,
    FloorSummary,
    StatusTransition,
    ZoneClassification,
    ZoneClassificationResult,
    ZoneHierarchyNode,
    ZoneHierarchyResult,
    ZoneTransitionHistory,
    ZoneTransitionHistoryResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _worst_status(a: ContaminationStatus, b: ContaminationStatus) -> ContaminationStatus:
    """Return the more severe of two statuses."""
    if CONTAMINATION_SEVERITY[a] >= CONTAMINATION_SEVERITY[b]:
        return a
    return b


async def _get_zones(db: AsyncSession, building_id: UUID) -> list[Zone]:
    result = await db.execute(select(Zone).where(Zone.building_id == building_id).order_by(Zone.created_at))
    return list(result.scalars().all())


async def _get_zone_materials(db: AsyncSession, zone_id: UUID) -> list[Material]:
    """Get all materials in a zone through its building elements."""
    result = await db.execute(
        select(Material)
        .join(BuildingElement, Material.element_id == BuildingElement.id)
        .where(BuildingElement.zone_id == zone_id)
    )
    return list(result.scalars().all())


async def _get_zone_samples(db: AsyncSession, zone_id: UUID) -> list[Sample]:
    """Get samples linked to materials in a zone."""
    result = await db.execute(
        select(Sample)
        .join(Material, Sample.id == Material.sample_id)
        .join(BuildingElement, Material.element_id == BuildingElement.id)
        .where(BuildingElement.zone_id == zone_id)
    )
    return list(result.scalars().all())


async def _get_zone_interventions(db: AsyncSession, building_id: UUID, zone_id: UUID) -> list[Intervention]:
    """Get interventions that affect a given zone (stored as JSON array of zone IDs)."""
    result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building_id,
        )
    )
    interventions = result.scalars().all()
    zone_str = str(zone_id)
    return [i for i in interventions if i.zones_affected and zone_str in str(i.zones_affected)]


async def _get_zone_field_observations(db: AsyncSession, zone_id: UUID) -> list[FieldObservation]:
    result = await db.execute(select(FieldObservation).where(FieldObservation.zone_id == zone_id))
    return list(result.scalars().all())


def _classify_zone_status(
    materials: list[Material],
    samples: list[Sample],
    interventions: list[Intervention],
    observations: list[FieldObservation],
) -> tuple[ContaminationStatus, list[str], int, int]:
    """Determine contamination status for a single zone.

    Returns (status, pollutants_found, sample_count, threshold_exceeded_count).

    Logic:
    - If a completed remediation intervention covers this zone -> remediated
    - If an in_progress remediation exists -> under_monitoring
    - If any sample has threshold_exceeded with high risk -> confirmed_high
    - If any sample has threshold_exceeded -> confirmed_low
    - If materials are flagged but not confirmed -> suspected
    - If field observations mention contamination/pollution -> suspected
    - Otherwise -> clean
    """
    pollutants: set[str] = set()
    sample_count = len(samples)
    threshold_exceeded_count = sum(1 for s in samples if s.threshold_exceeded)

    # Collect pollutant types from materials and samples
    for m in materials:
        if m.contains_pollutant and m.pollutant_type:
            pollutants.add(m.pollutant_type)
    for s in samples:
        if s.pollutant_type:
            pollutants.add(s.pollutant_type)

    # Check remediation interventions
    remediation_interventions = [i for i in interventions if i.intervention_type == "remediation"]
    completed_remediation = any(i.status == "completed" for i in remediation_interventions)
    in_progress_remediation = any(i.status == "in_progress" for i in remediation_interventions)

    if completed_remediation and not any(s.threshold_exceeded for s in samples):
        return ContaminationStatus.remediated, sorted(pollutants), sample_count, threshold_exceeded_count

    if in_progress_remediation:
        return ContaminationStatus.under_monitoring, sorted(pollutants), sample_count, threshold_exceeded_count

    # Check samples for confirmed contamination
    high_risk_exceeded = any(s.threshold_exceeded and s.risk_level in ("high", "critical") for s in samples)
    any_exceeded = any(s.threshold_exceeded for s in samples)

    if high_risk_exceeded:
        return ContaminationStatus.confirmed_high, sorted(pollutants), sample_count, threshold_exceeded_count

    if any_exceeded:
        return ContaminationStatus.confirmed_low, sorted(pollutants), sample_count, threshold_exceeded_count

    # Check materials for suspected contamination
    suspected_materials = any(m.contains_pollutant and not m.pollutant_confirmed for m in materials)
    confirmed_materials = any(m.contains_pollutant and m.pollutant_confirmed for m in materials)

    if confirmed_materials:
        return ContaminationStatus.confirmed_low, sorted(pollutants), sample_count, threshold_exceeded_count

    if suspected_materials:
        return ContaminationStatus.suspected, sorted(pollutants), sample_count, threshold_exceeded_count

    # Check field observations for contamination hints
    contamination_obs = any(
        o.observation_type in ("contamination", "pollution", "pollutant") and o.severity in ("warning", "critical")
        for o in observations
    )
    if contamination_obs:
        return ContaminationStatus.suspected, sorted(pollutants), sample_count, threshold_exceeded_count

    return ContaminationStatus.clean, sorted(pollutants), sample_count, threshold_exceeded_count


# ---------------------------------------------------------------------------
# FN1 -classify_zones
# ---------------------------------------------------------------------------


async def classify_zones(db: AsyncSession, building_id: UUID) -> ZoneClassificationResult:
    """Auto-classify all zones in a building by contamination status."""
    zones = await _get_zones(db, building_id)
    classified: list[ZoneClassification] = []
    summary: dict[str, int] = {s.value: 0 for s in ContaminationStatus}

    for zone in zones:
        materials = await _get_zone_materials(db, zone.id)
        samples = await _get_zone_samples(db, zone.id)
        interventions = await _get_zone_interventions(db, building_id, zone.id)
        observations = await _get_zone_field_observations(db, zone.id)

        status, pollutants, sample_count, threshold_count = _classify_zone_status(
            materials, samples, interventions, observations
        )

        classified.append(
            ZoneClassification(
                zone_id=zone.id,
                zone_name=zone.name,
                zone_type=zone.zone_type,
                floor_number=zone.floor_number,
                contamination_status=status,
                pollutants_found=pollutants,
                sample_count=sample_count,
                threshold_exceeded_count=threshold_count,
            )
        )
        summary[status.value] += 1

    return ZoneClassificationResult(
        building_id=building_id,
        total_zones=len(zones),
        classified_zones=classified,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# FN2 -get_zone_hierarchy
# ---------------------------------------------------------------------------


async def get_zone_hierarchy(db: AsyncSession, building_id: UUID) -> ZoneHierarchyResult:
    """Build zone tree with contamination roll-up. Parent zones inherit worst child status."""
    zones = await _get_zones(db, building_id)
    classification_result = await classify_zones(db, building_id)

    # Build lookup: zone_id -> classification
    status_map: dict[UUID, ContaminationStatus] = {
        zc.zone_id: zc.contamination_status for zc in classification_result.classified_zones
    }

    # Build parent->children mapping
    children_map: dict[UUID | None, list[Zone]] = {}
    for zone in zones:
        children_map.setdefault(zone.parent_zone_id, []).append(zone)

    def _build_node(zone: Zone) -> ZoneHierarchyNode:
        own_status = status_map.get(zone.id, ContaminationStatus.clean)
        child_zones = children_map.get(zone.id, [])
        child_nodes = [_build_node(c) for c in child_zones]

        # Roll up: worst of own + all children
        rolled_up = own_status
        for child in child_nodes:
            rolled_up = _worst_status(rolled_up, child.rolled_up_status)

        return ZoneHierarchyNode(
            zone_id=zone.id,
            zone_name=zone.name,
            zone_type=zone.zone_type,
            floor_number=zone.floor_number,
            own_status=own_status,
            rolled_up_status=rolled_up,
            children=child_nodes,
        )

    # Root nodes = zones with no parent
    root_zones = children_map.get(None, [])
    tree = [_build_node(z) for z in root_zones]

    # Building-level status = worst across all zones
    building_status = ContaminationStatus.clean
    for zc in classification_result.classified_zones:
        building_status = _worst_status(building_status, zc.contamination_status)

    # Floor summaries
    floor_groups: dict[int | None, list[ContaminationStatus]] = {}
    for zc in classification_result.classified_zones:
        zone_obj = next((z for z in zones if z.id == zc.zone_id), None)
        if zone_obj:
            floor_groups.setdefault(zone_obj.floor_number, []).append(zc.contamination_status)

    floor_summaries = []
    for floor_num, statuses in sorted(floor_groups.items(), key=lambda x: (x[0] is None, x[0] or 0)):
        worst = ContaminationStatus.clean
        for s in statuses:
            worst = _worst_status(worst, s)
        floor_summaries.append(FloorSummary(floor_number=floor_num, worst_status=worst, zone_count=len(statuses)))

    return ZoneHierarchyResult(
        building_id=building_id,
        building_status=building_status,
        floor_summaries=floor_summaries,
        tree=tree,
    )


# ---------------------------------------------------------------------------
# FN3 -identify_boundary_zones
# ---------------------------------------------------------------------------


async def identify_boundary_zones(db: AsyncSession, building_id: UUID) -> BoundaryZoneResult:
    """Identify zones adjacent to contaminated zones that need protective measures.

    Adjacency heuristic: zones sharing the same parent or on the same/adjacent floor.
    """
    zones = await _get_zones(db, building_id)
    classification_result = await classify_zones(db, building_id)

    status_map: dict[UUID, ContaminationStatus] = {
        zc.zone_id: zc.contamination_status for zc in classification_result.classified_zones
    }

    contaminated_statuses = {
        ContaminationStatus.confirmed_low,
        ContaminationStatus.confirmed_high,
        ContaminationStatus.under_monitoring,
    }

    contaminated_zones = {
        zc.zone_id for zc in classification_result.classified_zones if zc.contamination_status in contaminated_statuses
    }

    if not contaminated_zones:
        return BoundaryZoneResult(building_id=building_id, boundary_zones=[], total_boundary_zones=0)

    # Build adjacency: same parent or adjacent floor
    zone_by_id = {z.id: z for z in zones}
    boundary_zones: list[BoundaryZone] = []

    for zone in zones:
        if zone.id in contaminated_zones:
            continue

        own_status = status_map.get(zone.id, ContaminationStatus.clean)
        adjacent_contaminated: list[UUID] = []

        for cz_id in contaminated_zones:
            cz = zone_by_id.get(cz_id)
            if not cz:
                continue

            is_adjacent = False
            # Same parent = siblings
            if zone.parent_zone_id is not None and zone.parent_zone_id == cz.parent_zone_id:
                is_adjacent = True
            # Same floor or adjacent floor
            if (
                zone.floor_number is not None
                and cz.floor_number is not None
                and abs(zone.floor_number - cz.floor_number) <= 1
            ):
                is_adjacent = True
            # Parent-child relationship
            if zone.id == cz.parent_zone_id or zone.parent_zone_id == cz.id:
                is_adjacent = True

            if is_adjacent:
                adjacent_contaminated.append(cz_id)

        if adjacent_contaminated:
            measures = _recommend_measures(own_status, adjacent_contaminated, status_map)
            boundary_zones.append(
                BoundaryZone(
                    zone_id=zone.id,
                    zone_name=zone.name,
                    zone_type=zone.zone_type,
                    floor_number=zone.floor_number,
                    own_status=own_status,
                    adjacent_contaminated_zones=adjacent_contaminated,
                    recommended_measures=measures,
                )
            )

    return BoundaryZoneResult(
        building_id=building_id,
        boundary_zones=boundary_zones,
        total_boundary_zones=len(boundary_zones),
    )


def _recommend_measures(
    own_status: ContaminationStatus,
    adjacent_ids: list[UUID],
    status_map: dict[UUID, ContaminationStatus],
) -> list[str]:
    """Recommend protective measures based on adjacent zone severity."""
    worst_adjacent = ContaminationStatus.clean
    for aid in adjacent_ids:
        worst_adjacent = _worst_status(worst_adjacent, status_map.get(aid, ContaminationStatus.clean))

    measures: list[str] = []

    if worst_adjacent == ContaminationStatus.confirmed_high:
        measures.extend(
            [
                "containment_barrier",
                "negative_pressure_zone",
                "decontamination_airlock",
                "air_quality_monitoring",
            ]
        )
    elif worst_adjacent == ContaminationStatus.confirmed_low:
        measures.extend(
            [
                "containment_barrier",
                "access_restriction",
                "air_quality_monitoring",
            ]
        )
    elif worst_adjacent == ContaminationStatus.under_monitoring:
        measures.extend(
            [
                "access_restriction",
                "periodic_sampling",
            ]
        )

    if own_status == ContaminationStatus.suspected:
        measures.append("priority_sampling")

    return measures


# ---------------------------------------------------------------------------
# FN4 -get_zone_transition_history
# ---------------------------------------------------------------------------


async def get_zone_transition_history(db: AsyncSession, building_id: UUID) -> ZoneTransitionHistoryResult:
    """Build contamination status transition timeline per zone.

    Reconstructs history from:
    - Diagnostic dates (first suspicion)
    - Sample creation dates (confirmation)
    - Intervention dates (remediation start/end)
    - Field observation dates (monitoring)
    """
    zones = await _get_zones(db, building_id)
    classification_result = await classify_zones(db, building_id)

    status_map: dict[UUID, ContaminationStatus] = {
        zc.zone_id: zc.contamination_status for zc in classification_result.classified_zones
    }

    zone_histories: list[ZoneTransitionHistory] = []

    for zone in zones:
        transitions: list[StatusTransition] = []

        materials = await _get_zone_materials(db, zone.id)
        samples = await _get_zone_samples(db, zone.id)
        interventions = await _get_zone_interventions(db, building_id, zone.id)
        await _get_zone_field_observations(db, zone.id)

        # Gather diagnostic IDs from samples to get diagnostic dates
        diag_ids = {s.diagnostic_id for s in samples}
        if diag_ids:
            await db.execute(select(Diagnostic).where(Diagnostic.id.in_(diag_ids)))

        # Transition: zone created as clean
        transitions.append(
            StatusTransition(
                from_status=None,
                to_status=ContaminationStatus.clean,
                timestamp=zone.created_at or datetime.now(UTC),
                reason="zone_created",
            )
        )

        # If any diagnostic with suspected materials
        suspected_materials = [m for m in materials if m.contains_pollutant and not m.pollutant_confirmed]
        if suspected_materials:
            earliest_mat = min(
                (m.created_at for m in suspected_materials if m.created_at),
                default=None,
            )
            if earliest_mat:
                transitions.append(
                    StatusTransition(
                        from_status=ContaminationStatus.clean,
                        to_status=ContaminationStatus.suspected,
                        timestamp=earliest_mat,
                        reason="material_flagged_as_suspected",
                    )
                )

        # If samples confirm contamination
        exceeded_samples = [s for s in samples if s.threshold_exceeded]
        if exceeded_samples:
            earliest_sample = min(
                (s.created_at for s in exceeded_samples if s.created_at),
                default=None,
            )
            if earliest_sample:
                high_risk = any(s.risk_level in ("high", "critical") for s in exceeded_samples)
                transitions.append(
                    StatusTransition(
                        from_status=ContaminationStatus.suspected,
                        to_status=ContaminationStatus.confirmed_high
                        if high_risk
                        else ContaminationStatus.confirmed_low,
                        timestamp=earliest_sample,
                        reason="sample_threshold_exceeded",
                    )
                )

        # Remediation transitions
        remediation_interventions = [i for i in interventions if i.intervention_type == "remediation"]
        for ri in sorted(remediation_interventions, key=lambda i: i.created_at or datetime.now(UTC)):
            if ri.status == "in_progress":
                ts = (
                    datetime.combine(ri.date_start, datetime.min.time()).replace(tzinfo=UTC)
                    if ri.date_start
                    else (ri.created_at or datetime.now(UTC))
                )
                transitions.append(
                    StatusTransition(
                        from_status=None,
                        to_status=ContaminationStatus.under_monitoring,
                        timestamp=ts,
                        reason="remediation_started",
                    )
                )
            elif ri.status == "completed":
                ts = (
                    datetime.combine(ri.date_end, datetime.min.time()).replace(tzinfo=UTC)
                    if ri.date_end
                    else (ri.created_at or datetime.now(UTC))
                )
                transitions.append(
                    StatusTransition(
                        from_status=ContaminationStatus.under_monitoring,
                        to_status=ContaminationStatus.remediated,
                        timestamp=ts,
                        reason="remediation_completed",
                    )
                )

        # Sort transitions by timestamp
        transitions.sort(key=lambda t: t.timestamp)

        current_status = status_map.get(zone.id, ContaminationStatus.clean)

        zone_histories.append(
            ZoneTransitionHistory(
                zone_id=zone.id,
                zone_name=zone.name,
                current_status=current_status,
                transitions=transitions,
            )
        )

    return ZoneTransitionHistoryResult(
        building_id=building_id,
        zone_histories=zone_histories,
    )
