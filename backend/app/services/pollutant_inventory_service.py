"""Pollutant Inventory Service — consolidated pollutant views for buildings and portfolios."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.pollutant_inventory import (
    BuildingPollutantHotspots,
    BuildingPollutantInventory,
    BuildingPollutantStats,
    BuildingPollutantSummary,
    PollutantHotspot,
    PollutantInventoryItem,
    PollutantTypeSummary,
    PortfolioPollutantOverview,
)

RISK_LEVEL_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}


def _worst_risk(levels: list[str | None]) -> str | None:
    """Return the worst (highest severity) risk level from a list."""
    filtered = [r for r in levels if r]
    if not filtered:
        return None
    return max(filtered, key=lambda r: RISK_LEVEL_ORDER.get(r, 0))


def _sample_status(sample: Sample) -> str:
    """Derive a pollutant status from a sample's fields."""
    if sample.pollutant_type is None:
        return "cleared"
    if sample.threshold_exceeded:
        return "confirmed"
    if sample.concentration is not None and sample.concentration > 0:
        return "suspected"
    return "suspected"


def _location_key(sample: Sample) -> str:
    """Build a location key from floor/room/detail for grouping."""
    parts = [
        sample.location_floor or "unknown_floor",
        sample.location_room or "unknown_room",
    ]
    if sample.location_detail:
        parts.append(sample.location_detail)
    return " / ".join(parts)


async def _get_building_samples(db: AsyncSession, building_id: uuid.UUID) -> list[tuple[Sample, Diagnostic]]:
    """Fetch all samples for a building, joined with their diagnostics."""
    stmt = (
        select(Sample, Diagnostic)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
        .order_by(Sample.created_at)
    )
    result = await db.execute(stmt)
    return list(result.all())


def _build_inventory_item(
    sample: Sample, diagnostic: Diagnostic, zone_name: str | None = None, zone_type: str | None = None
) -> PollutantInventoryItem:
    """Convert a sample + diagnostic into an inventory item."""
    return PollutantInventoryItem(
        sample_id=sample.id,
        diagnostic_id=diagnostic.id,
        pollutant_type=sample.pollutant_type or "unknown",
        pollutant_subtype=sample.pollutant_subtype,
        status=_sample_status(sample),
        concentration=sample.concentration,
        unit=sample.unit,
        threshold_exceeded=sample.threshold_exceeded or False,
        risk_level=sample.risk_level,
        location_floor=sample.location_floor,
        location_room=sample.location_room,
        location_detail=sample.location_detail,
        material_category=sample.material_category,
        material_description=sample.material_description,
        zone_name=zone_name,
        zone_type=zone_type,
        diagnostic_date=diagnostic.date_report or diagnostic.date_inspection,
        diagnostic_status=diagnostic.status,
    )


async def get_building_pollutant_inventory(db: AsyncSession, building_id: uuid.UUID) -> BuildingPollutantInventory:
    """Return a complete pollutant inventory for a building.

    Aggregates samples from all diagnostics, enriched with location and zone info.
    """
    rows = await _get_building_samples(db, building_id)

    items: list[PollutantInventoryItem] = []
    pollutant_types: set[str] = set()

    for sample, diagnostic in rows:
        item = _build_inventory_item(sample, diagnostic)
        items.append(item)
        if sample.pollutant_type:
            pollutant_types.add(sample.pollutant_type)

    return BuildingPollutantInventory(
        building_id=building_id,
        total_findings=len(items),
        items=items,
        pollutant_types_found=sorted(pollutant_types),
        generated_at=datetime.now(UTC),
    )


async def get_pollutant_summary(db: AsyncSession, building_id: uuid.UUID) -> BuildingPollutantSummary:
    """Return a per-pollutant-type summary for a building."""
    rows = await _get_building_samples(db, building_id)

    # Group by pollutant_type
    groups: dict[str, list[tuple[Sample, Diagnostic]]] = {}
    for sample, diagnostic in rows:
        pt = sample.pollutant_type or "unknown"
        groups.setdefault(pt, []).append((sample, diagnostic))

    summaries: list[PollutantTypeSummary] = []
    for pt, group_rows in sorted(groups.items()):
        statuses = [_sample_status(s) for s, _ in group_rows]
        risk_levels = [s.risk_level for s, _ in group_rows]
        concentrations = [s.concentration for s, _ in group_rows if s.concentration is not None]
        diag_dates = [d.date_report or d.date_inspection for _, d in group_rows if d.date_report or d.date_inspection]
        zones: set[str] = set()
        for s, _ in group_rows:
            loc = _location_key(s)
            zones.add(loc)

        units = [s.unit for s, _ in group_rows if s.unit]

        summaries.append(
            PollutantTypeSummary(
                pollutant_type=pt,
                count=len(group_rows),
                confirmed_count=statuses.count("confirmed"),
                suspected_count=statuses.count("suspected"),
                cleared_count=statuses.count("cleared"),
                worst_risk_level=_worst_risk(risk_levels),
                zones_affected=sorted(zones),
                latest_diagnostic_date=max(diag_dates) if diag_dates else None,
                max_concentration=max(concentrations) if concentrations else None,
                unit=units[0] if units else None,
            )
        )

    return BuildingPollutantSummary(
        building_id=building_id,
        summaries=summaries,
        total_pollutant_types=len(summaries),
        generated_at=datetime.now(UTC),
    )


async def get_portfolio_pollutant_overview(db: AsyncSession, org_id: uuid.UUID) -> PortfolioPollutantOverview:
    """Return pollutant distribution across all buildings owned by members of an organization."""
    from app.services.building_data_loader import load_org_buildings

    # Get all buildings created by org members
    all_buildings = await load_org_buildings(db, org_id)

    # Reload with eager-loaded diagnostics/samples
    if not all_buildings:
        buildings: list[Building] = []
    else:
        building_ids = [b.id for b in all_buildings]
        stmt = (
            select(Building)
            .where(Building.id.in_(building_ids))
            .options(selectinload(Building.diagnostics).selectinload(Diagnostic.samples))
        )
        result = await db.execute(stmt)
        buildings = list(result.scalars().all())

    pollutant_distribution: dict[str, int] = {}
    risk_distribution: dict[str, int] = {}
    building_stats: list[BuildingPollutantStats] = []
    buildings_with_pollutants = 0

    for building in buildings:
        b_pollutant_types: set[str] = set()
        b_findings = 0
        b_confirmed = 0
        b_risk_levels: list[str | None] = []

        for diag in building.diagnostics:
            for sample in diag.samples:
                if sample.pollutant_type:
                    b_pollutant_types.add(sample.pollutant_type)
                    b_findings += 1
                    pollutant_distribution[sample.pollutant_type] = (
                        pollutant_distribution.get(sample.pollutant_type, 0) + 1
                    )
                    if sample.risk_level:
                        risk_distribution[sample.risk_level] = risk_distribution.get(sample.risk_level, 0) + 1
                        b_risk_levels.append(sample.risk_level)
                    if sample.threshold_exceeded:
                        b_confirmed += 1

        if b_pollutant_types:
            buildings_with_pollutants += 1

        building_stats.append(
            BuildingPollutantStats(
                building_id=building.id,
                address=building.address,
                city=building.city,
                pollutant_types=sorted(b_pollutant_types),
                total_findings=b_findings,
                confirmed_count=b_confirmed,
                worst_risk_level=_worst_risk(b_risk_levels),
            )
        )

    return PortfolioPollutantOverview(
        organization_id=org_id,
        total_buildings=len(buildings),
        buildings_with_pollutants=buildings_with_pollutants,
        pollutant_distribution=pollutant_distribution,
        risk_distribution=risk_distribution,
        buildings=building_stats,
        generated_at=datetime.now(UTC),
    )


async def get_pollutant_hotspots(db: AsyncSession, building_id: uuid.UUID) -> BuildingPollutantHotspots:
    """Identify zones with high concentration or multiple pollutants, ranked by risk."""
    rows = await _get_building_samples(db, building_id)

    # Group by location key
    location_groups: dict[str, list[tuple[Sample, Diagnostic]]] = {}
    for sample, diagnostic in rows:
        if not sample.pollutant_type:
            continue
        key = _location_key(sample)
        location_groups.setdefault(key, []).append((sample, diagnostic))

    hotspots: list[PollutantHotspot] = []

    for loc_key, group_rows in location_groups.items():
        pollutant_types = list({s.pollutant_type for s, _ in group_rows if s.pollutant_type})
        risk_levels = [s.risk_level for s, _ in group_rows]
        concentrations = [s.concentration for s, _ in group_rows if s.concentration is not None]
        worst_risk = _worst_risk(risk_levels)

        # Compute a risk score for ranking:
        # - multi-pollutant factor (number of distinct pollutants)
        # - risk severity factor
        # - concentration factor (normalized, capped at 1.0)
        risk_severity = RISK_LEVEL_ORDER.get(worst_risk, 0) if worst_risk else 0
        multi_pollutant_factor = len(pollutant_types)
        max_conc = max(concentrations) if concentrations else 0
        # Simple composite score
        risk_score = round(risk_severity * 2.0 + multi_pollutant_factor * 1.5 + min(max_conc / 1000.0, 2.0), 2)

        # Extract zone info from the first sample
        first_sample = group_rows[0][0]

        hotspots.append(
            PollutantHotspot(
                zone_name=first_sample.location_room,
                zone_type=None,
                location_key=loc_key,
                pollutant_types=sorted(pollutant_types),
                pollutant_count=len(pollutant_types),
                max_concentration=max(concentrations) if concentrations else None,
                worst_risk_level=worst_risk,
                findings_count=len(group_rows),
                risk_score=risk_score,
            )
        )

    # Sort by risk_score descending
    hotspots.sort(key=lambda h: h.risk_score, reverse=True)

    return BuildingPollutantHotspots(
        building_id=building_id,
        hotspots=hotspots,
        generated_at=datetime.now(UTC),
    )
