"""
SwissBuildingOS - Building Age Analysis Service

Era-based pollutant probability classification and risk profiling driven by
Swiss construction history:
- Pre-1950: lead paint high
- 1950-1975: asbestos + PCB peak
- 1975-1991: asbestos declining, PCB window
- Post-1991: generally safe (ban era)
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.zone import Zone
from app.schemas.building_age_analysis import (
    AgeBasedRiskProfile,
    EraBucket,
    EraClassification,
    EraHotspot,
    EraHotspotReport,
    PollutantProbability,
    PortfolioAgeDistribution,
    PriorityBuilding,
    RiskModifier,
)

# ---------------------------------------------------------------------------
# Era definitions
# ---------------------------------------------------------------------------

_ERAS = {
    "pre_1950": {"label": "Pre-1950 (lead era)", "priority": "high"},
    "1950_1975": {"label": "1950-1975 (asbestos + PCB peak)", "priority": "critical"},
    "1975_1991": {"label": "1975-1991 (declining asbestos, PCB window)", "priority": "high"},
    "post_1991": {"label": "Post-1991 (ban era)", "priority": "low"},
    "unknown": {"label": "Unknown construction date", "priority": "medium"},
}

_ERA_POLLUTANTS: dict[str, list[dict]] = {
    "pre_1950": [
        {
            "pollutant": "lead",
            "probability": "high",
            "typical_materials": ["interior paint", "exterior paint", "window putty"],
            "notes": "Lead-based paints widespread before regulation",
        },
        {
            "pollutant": "asbestos",
            "probability": "low",
            "typical_materials": ["pipe insulation (rare)"],
            "notes": "Asbestos use not yet widespread",
        },
        {
            "pollutant": "hap",
            "probability": "medium",
            "typical_materials": ["tar-based waterproofing", "coal tar coatings"],
            "notes": "PAH in older waterproofing and coatings",
        },
        {
            "pollutant": "pcb",
            "probability": "negligible",
            "typical_materials": [],
            "notes": "PCB production not yet started",
        },
        {
            "pollutant": "radon",
            "probability": "medium",
            "typical_materials": ["foundation", "basement walls"],
            "notes": "Older buildings often lack radon barriers",
        },
    ],
    "1950_1975": [
        {
            "pollutant": "asbestos",
            "probability": "high",
            "typical_materials": [
                "pipe insulation",
                "floor tiles (vinyl-amiante)",
                "roof corrugated sheets",
                "fire protection panels",
                "facade panels (Eternit)",
                "flocking/flocage",
            ],
            "notes": "Peak asbestos usage period in Swiss construction",
        },
        {
            "pollutant": "pcb",
            "probability": "high",
            "typical_materials": [
                "window joint sealants",
                "expansion joint fillers",
                "facade sealants",
                "elastic caulking",
            ],
            "notes": "PCB-based sealants standard in this era (>50 mg/kg threshold per ORRChim)",
        },
        {
            "pollutant": "lead",
            "probability": "medium",
            "typical_materials": ["older paint layers", "water pipes"],
            "notes": "Lead paint phasing out but still present in repaints over older layers",
        },
        {
            "pollutant": "hap",
            "probability": "medium",
            "typical_materials": ["bituminous waterproofing", "parquet adhesives"],
            "notes": "PAH in adhesives and waterproofing",
        },
        {
            "pollutant": "radon",
            "probability": "medium",
            "typical_materials": ["foundation", "basement"],
            "notes": "Variable protection depending on construction method",
        },
    ],
    "1975_1991": [
        {
            "pollutant": "asbestos",
            "probability": "medium",
            "typical_materials": [
                "floor tiles",
                "facade panels (Eternit)",
                "pipe insulation (declining)",
                "roof elements",
            ],
            "notes": "Asbestos use declining but not yet banned (Swiss ban 1990)",
        },
        {
            "pollutant": "pcb",
            "probability": "medium",
            "typical_materials": ["joint sealants", "elastic fillers"],
            "notes": "PCB production stopped 1980 but existing stock used until ~1986",
        },
        {
            "pollutant": "lead",
            "probability": "low",
            "typical_materials": ["occasional paint layers"],
            "notes": "Lead paint largely phased out",
        },
        {
            "pollutant": "hap",
            "probability": "low",
            "typical_materials": ["older adhesives"],
            "notes": "PAH-containing products declining",
        },
        {
            "pollutant": "radon",
            "probability": "low",
            "typical_materials": ["foundation"],
            "notes": "Better construction standards but pre-radon-norm (SIA 180)",
        },
    ],
    "post_1991": [
        {
            "pollutant": "asbestos",
            "probability": "negligible",
            "typical_materials": [],
            "notes": "Asbestos banned in Switzerland since 1990",
        },
        {
            "pollutant": "pcb",
            "probability": "negligible",
            "typical_materials": [],
            "notes": "PCB-free sealants standard",
        },
        {
            "pollutant": "lead",
            "probability": "negligible",
            "typical_materials": [],
            "notes": "Lead-free paints mandatory",
        },
        {
            "pollutant": "hap",
            "probability": "negligible",
            "typical_materials": [],
            "notes": "PAH-free products standard",
        },
        {
            "pollutant": "radon",
            "probability": "low",
            "typical_materials": ["foundation"],
            "notes": "Modern radon protection per SIA 180 but depends on geology",
        },
    ],
    "unknown": [
        {
            "pollutant": "asbestos",
            "probability": "medium",
            "typical_materials": ["various"],
            "notes": "Unknown era — diagnostic needed to assess",
        },
        {
            "pollutant": "pcb",
            "probability": "medium",
            "typical_materials": ["various"],
            "notes": "Unknown era — diagnostic needed",
        },
        {
            "pollutant": "lead",
            "probability": "medium",
            "typical_materials": ["various"],
            "notes": "Unknown era — diagnostic needed",
        },
        {
            "pollutant": "hap",
            "probability": "medium",
            "typical_materials": ["various"],
            "notes": "Unknown era — diagnostic needed",
        },
        {
            "pollutant": "radon",
            "probability": "medium",
            "typical_materials": ["various"],
            "notes": "Unknown era — diagnostic needed",
        },
    ],
}

_ERA_HOTSPOTS: dict[str, list[dict]] = {
    "pre_1950": [
        {
            "zone_type": "room",
            "element_type": "wall",
            "pollutant": "lead",
            "probability": "high",
            "description": "Interior walls — lead-based paint layers",
        },
        {
            "zone_type": "facade",
            "element_type": "coating",
            "pollutant": "lead",
            "probability": "high",
            "description": "Exterior coatings — lead paint on facades",
        },
        {
            "zone_type": "basement",
            "element_type": "structural",
            "pollutant": "radon",
            "probability": "medium",
            "description": "Basement — no radon barrier in older construction",
        },
        {
            "zone_type": "roof",
            "element_type": "coating",
            "pollutant": "hap",
            "probability": "medium",
            "description": "Roof waterproofing — tar-based products",
        },
    ],
    "1950_1975": [
        {
            "zone_type": "technical_room",
            "element_type": "pipe",
            "pollutant": "asbestos",
            "probability": "high",
            "description": "Pipe insulation — asbestos lagging on heating/water pipes",
        },
        {
            "zone_type": "room",
            "element_type": "floor",
            "pollutant": "asbestos",
            "probability": "high",
            "description": "Floor tiles — vinyl-amiante tiles (cushion vinyl)",
        },
        {
            "zone_type": "facade",
            "element_type": "window",
            "pollutant": "pcb",
            "probability": "high",
            "description": "Window joints — PCB-based elastic sealants",
        },
        {
            "zone_type": "facade",
            "element_type": "wall",
            "pollutant": "asbestos",
            "probability": "high",
            "description": "Facade panels — Eternit fibre-cement cladding",
        },
        {
            "zone_type": "staircase",
            "element_type": "ceiling",
            "pollutant": "asbestos",
            "probability": "medium",
            "description": "Ceiling flocage — sprayed asbestos fire protection",
        },
        {
            "zone_type": "room",
            "element_type": "floor",
            "pollutant": "hap",
            "probability": "medium",
            "description": "Parquet adhesive — PAH-containing black glue",
        },
    ],
    "1975_1991": [
        {
            "zone_type": "room",
            "element_type": "floor",
            "pollutant": "asbestos",
            "probability": "medium",
            "description": "Floor tiles — late-era vinyl-amiante still possible",
        },
        {
            "zone_type": "facade",
            "element_type": "wall",
            "pollutant": "asbestos",
            "probability": "medium",
            "description": "Facade panels — Eternit still used until ban",
        },
        {
            "zone_type": "facade",
            "element_type": "window",
            "pollutant": "pcb",
            "probability": "medium",
            "description": "Window sealants — PCB stock used until ~1986",
        },
        {
            "zone_type": "roof",
            "element_type": "structural",
            "pollutant": "asbestos",
            "probability": "low",
            "description": "Roof elements — declining use of asbestos sheets",
        },
    ],
    "post_1991": [
        {
            "zone_type": "basement",
            "element_type": "structural",
            "pollutant": "radon",
            "probability": "low",
            "description": "Foundation — modern protection but geology-dependent",
        },
    ],
    "unknown": [
        {
            "zone_type": "room",
            "element_type": "wall",
            "pollutant": "asbestos",
            "probability": "medium",
            "description": "Unknown era — investigate all common hotspots",
        },
        {
            "zone_type": "facade",
            "element_type": "window",
            "pollutant": "pcb",
            "probability": "medium",
            "description": "Unknown era — check window joints for PCB sealants",
        },
        {
            "zone_type": "room",
            "element_type": "wall",
            "pollutant": "lead",
            "probability": "medium",
            "description": "Unknown era — test paint layers for lead",
        },
    ],
}

_ERA_SUMMARIES: dict[str, str] = {
    "pre_1950": (
        "Pre-1950 building: high lead paint probability, moderate PAH/radon risk. "
        "Priority diagnostic for lead paint on interior/exterior surfaces."
    ),
    "1950_1975": (
        "1950-1975 building: peak asbestos and PCB era. High probability of asbestos in "
        "insulation, floor tiles, facade panels. PCB in window/expansion joint sealants. "
        "Full pollutant diagnostic strongly recommended before any renovation."
    ),
    "1975_1991": (
        "1975-1991 building: asbestos use declining but not yet banned (Swiss ban 1990). "
        "PCB sealants possible until ~1986. Targeted diagnostic recommended."
    ),
    "post_1991": (
        "Post-1991 building: built after Swiss asbestos ban. Generally low pollutant risk. "
        "Radon check may still be relevant depending on geology."
    ),
    "unknown": (
        "Construction date unknown: cannot classify era risk. Comprehensive diagnostic "
        "recommended to establish pollutant baseline."
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classify_era(construction_year: int | None) -> str:
    if construction_year is None:
        return "unknown"
    if construction_year < 1950:
        return "pre_1950"
    if construction_year <= 1975:
        return "1950_1975"
    if construction_year <= 1991:
        return "1975_1991"
    return "post_1991"


def _priority_rank(priority: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(priority, 0)


# ---------------------------------------------------------------------------
# FN1: analyze_construction_era
# ---------------------------------------------------------------------------


async def analyze_construction_era(db: AsyncSession, building_id: UUID) -> EraClassification:
    """Era classification and pollutant probability based on construction year."""
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    era = _classify_era(building.construction_year)
    era_info = _ERAS[era]
    pollutants = [PollutantProbability(**p) for p in _ERA_POLLUTANTS[era]]

    return EraClassification(
        building_id=building_id,
        construction_year=building.construction_year,
        era=era,
        era_label=era_info["label"],
        pollutant_probabilities=pollutants,
        diagnostic_priority=era_info["priority"],
        summary=_ERA_SUMMARIES[era],
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: get_age_based_risk_profile
# ---------------------------------------------------------------------------


async def get_age_based_risk_profile(db: AsyncSession, building_id: UUID) -> AgeBasedRiskProfile:
    """Construction year drives baseline risk with modifiers from diagnostics and interventions."""
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    era = _classify_era(building.construction_year)

    # Baseline risk from era
    baseline_risk = {
        "pre_1950": "elevated",
        "1950_1975": "elevated",
        "1975_1991": "moderate",
        "post_1991": "low",
        "unknown": "elevated",
    }[era]

    # Count diagnostics
    diag_stmt = select(func.count()).select_from(Diagnostic).where(Diagnostic.building_id == building_id)
    diag_result = await db.execute(diag_stmt)
    diagnostic_count = diag_result.scalar() or 0

    completed_stmt = (
        select(func.count())
        .select_from(Diagnostic)
        .where(Diagnostic.building_id == building_id, Diagnostic.status.in_(["completed", "validated"]))
    )
    completed_result = await db.execute(completed_stmt)
    completed_diagnostic_count = completed_result.scalar() or 0

    has_diagnostics = diagnostic_count > 0

    # Count interventions (renovation history)
    intervention_stmt = select(func.count()).select_from(Intervention).where(Intervention.building_id == building_id)
    intervention_result = await db.execute(intervention_stmt)
    intervention_count = intervention_result.scalar() or 0

    # Build risk modifiers
    modifiers: list[RiskModifier] = []

    if not has_diagnostics and era in ("pre_1950", "1950_1975", "1975_1991", "unknown"):
        modifiers.append(
            RiskModifier(
                factor="no_diagnostic",
                impact="increases",
                description="No pollutant diagnostic on record — unknown contamination status",
            )
        )

    if has_diagnostics and completed_diagnostic_count > 0:
        modifiers.append(
            RiskModifier(
                factor="diagnostic_coverage",
                impact="decreases",
                description=f"{completed_diagnostic_count} completed diagnostic(s) provide contamination data",
            )
        )

    if intervention_count > 0:
        modifiers.append(
            RiskModifier(
                factor="intervention_history",
                impact="increases",
                description=(
                    f"{intervention_count} intervention(s) on record — "
                    "renovation may have disturbed pollutant-containing materials"
                ),
            )
        )

    if building.renovation_year and building.renovation_year < 1991:
        modifiers.append(
            RiskModifier(
                factor="pre_ban_renovation",
                impact="increases",
                description=f"Renovation in {building.renovation_year} (before asbestos ban) may have introduced new pollutant materials",
            )
        )

    if building.renovation_year and building.renovation_year >= 1991 and has_diagnostics:
        modifiers.append(
            RiskModifier(
                factor="post_ban_renovation_with_diag",
                impact="decreases",
                description=f"Post-ban renovation ({building.renovation_year}) with diagnostic coverage reduces residual risk",
            )
        )

    # Compute overall risk
    overall_risk = baseline_risk
    increase_count = sum(1 for m in modifiers if m.impact == "increases")
    decrease_count = sum(1 for m in modifiers if m.impact == "decreases")

    if (decrease_count > increase_count and baseline_risk == "elevated") or (
        increase_count > decrease_count and baseline_risk == "low"
    ):
        overall_risk = "moderate"
    elif increase_count > decrease_count and baseline_risk == "moderate":
        overall_risk = "elevated"

    # Recommendation
    if overall_risk == "elevated":
        recommendation = "Full pollutant diagnostic strongly recommended before any renovation works."
    elif overall_risk == "moderate":
        recommendation = "Targeted diagnostic recommended to clarify remaining risk areas."
    else:
        recommendation = "Low risk profile. Routine radon check may still be advisable."

    return AgeBasedRiskProfile(
        building_id=building_id,
        construction_year=building.construction_year,
        era=era,
        baseline_risk=baseline_risk,
        has_diagnostics=has_diagnostics,
        diagnostic_count=diagnostic_count,
        completed_diagnostic_count=completed_diagnostic_count,
        risk_modifiers=modifiers,
        overall_risk=overall_risk,
        recommendation=recommendation,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: identify_era_specific_hotspots
# ---------------------------------------------------------------------------


async def identify_era_specific_hotspots(db: AsyncSession, building_id: UUID) -> EraHotspotReport:
    """Typical pollutant locations by era, mapped to actual building zones."""
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    era = _classify_era(building.construction_year)

    # Load building zones for matching
    zone_stmt = select(Zone).where(Zone.building_id == building_id)
    zone_result = await db.execute(zone_stmt)
    zones = zone_result.scalars().all()
    zone_by_type: dict[str, list] = {}
    for z in zones:
        zone_by_type.setdefault(z.zone_type, []).append(z)

    hotspot_defs = _ERA_HOTSPOTS.get(era, [])
    hotspots: list[EraHotspot] = []
    matched_zone_ids: set[UUID] = set()

    for hdef in hotspot_defs:
        matched_zone = None
        matching_zones = zone_by_type.get(hdef["zone_type"], [])
        if matching_zones:
            matched_zone = matching_zones[0]
            matched_zone_ids.add(matched_zone.id)

        hotspots.append(
            EraHotspot(
                zone_type=hdef["zone_type"],
                element_type=hdef["element_type"],
                pollutant=hdef["pollutant"],
                probability=hdef["probability"],
                description=hdef["description"],
                matched_zone_id=matched_zone.id if matched_zone else None,
                matched_zone_name=matched_zone.name if matched_zone else None,
            )
        )

    return EraHotspotReport(
        building_id=building_id,
        construction_year=building.construction_year,
        era=era,
        hotspots=hotspots,
        total_matched_zones=len(matched_zone_ids),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_age_distribution
# ---------------------------------------------------------------------------


async def get_portfolio_age_distribution(db: AsyncSession, org_id: UUID) -> PortfolioAgeDistribution:
    """Org-level age distribution: building count per era, diagnostic coverage, priority list."""
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioAgeDistribution(
            organization_id=org_id,
            total_buildings=0,
            era_buckets=[],
            priority_buildings=[],
            generated_at=datetime.now(UTC),
        )

    # Classify each building
    era_buildings: dict[str, list] = {}
    for b in buildings:
        era = _classify_era(b.construction_year)
        era_buildings.setdefault(era, []).append(b)

    # Count diagnostics per building
    building_ids = [b.id for b in buildings]
    diag_count_stmt = (
        select(Diagnostic.building_id, func.count().label("cnt"))
        .where(Diagnostic.building_id.in_(building_ids))
        .group_by(Diagnostic.building_id)
    )
    diag_result = await db.execute(diag_count_stmt)
    diag_counts: dict[UUID, int] = {row[0]: row[1] for row in diag_result.all()}

    # Build era buckets
    buckets: list[EraBucket] = []
    era_order = ["pre_1950", "1950_1975", "1975_1991", "post_1991", "unknown"]
    for era_key in era_order:
        era_bldgs = era_buildings.get(era_key, [])
        if not era_bldgs:
            continue
        diagnosed = sum(1 for b in era_bldgs if diag_counts.get(b.id, 0) > 0)
        buckets.append(
            EraBucket(
                era=era_key,
                era_label=_ERAS[era_key]["label"],
                building_count=len(era_bldgs),
                diagnosed_count=diagnosed,
                undiagnosed_count=len(era_bldgs) - diagnosed,
                avg_diagnostic_priority=_ERAS[era_key]["priority"],
            )
        )

    # Priority buildings: old + undiagnosed, sorted by era priority descending
    priority_buildings: list[PriorityBuilding] = []
    for b in buildings:
        era = _classify_era(b.construction_year)
        dc = diag_counts.get(b.id, 0)
        if dc == 0 and era in ("pre_1950", "1950_1975", "1975_1991", "unknown"):
            priority_buildings.append(
                PriorityBuilding(
                    building_id=b.id,
                    address=b.address,
                    construction_year=b.construction_year,
                    era=era,
                    diagnostic_count=0,
                )
            )

    # Sort by priority (critical first)
    priority_buildings.sort(key=lambda p: _priority_rank(_ERAS[p.era]["priority"]), reverse=True)

    return PortfolioAgeDistribution(
        organization_id=org_id,
        total_buildings=len(buildings),
        era_buckets=buckets,
        priority_buildings=priority_buildings,
        generated_at=datetime.now(UTC),
    )
