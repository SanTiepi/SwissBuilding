"""
SwissBuildingOS - Compliance Gap Analysis Service

Identifies non-compliance items per pollutant and regulation, generates
remediation roadmaps, estimates compliance costs, and provides portfolio-level
gap analysis.  Uses Swiss regulatory thresholds from compliance_engine.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.compliance_gap import (
    ComplianceCostEstimate,
    ComplianceGapItem,
    ComplianceGapReport,
    ComplianceRoadmap,
    CostRange,
    GapTypeCount,
    LaborMaterialsDisposal,
    PollutantCostBreakdown,
    PortfolioBuildingGap,
    PortfolioComplianceGaps,
    RegulationCostBreakdown,
    RoadmapStep,
)
from app.services.compliance_engine import SWISS_THRESHOLDS

# ---------------------------------------------------------------------------
# Regulation metadata
# ---------------------------------------------------------------------------

_REGULATION_MAP: dict[str, dict[str, str]] = {
    "asbestos_material": {
        "ref": "OTConst Art. 82",
        "name": "OTConst - Asbestos in materials",
        "required": "< 1.0% weight",
        "remediation": "Professional asbestos removal per CFST 6503",
    },
    "asbestos_air": {
        "ref": "CFST 6503",
        "name": "CFST - Asbestos air fiber count",
        "required": "< 1000 fibers/m3",
        "remediation": "Air decontamination and source removal",
    },
    "pcb_material": {
        "ref": "ORRChim Annexe 2.15",
        "name": "ORRChim - PCB in materials",
        "required": "< 50 mg/kg",
        "remediation": "PCB decontamination and material replacement",
    },
    "pcb_air": {
        "ref": "OFSP Recommendation",
        "name": "OFSP - PCB indoor air",
        "required": "< 6000 ng/m3",
        "remediation": "Source removal and ventilation improvement",
    },
    "lead_paint": {
        "ref": "ORRChim Annexe 2.18",
        "name": "ORRChim - Lead in paint",
        "required": "< 5000 mg/kg",
        "remediation": "Lead paint removal or encapsulation",
    },
    "lead_water": {
        "ref": "OSEC",
        "name": "OSEC - Lead in drinking water",
        "required": "< 10 ug/l",
        "remediation": "Pipe replacement",
    },
    "hap_material": {
        "ref": "OLED",
        "name": "OLED - HAP in materials",
        "required": "< 200 mg/kg",
        "remediation": "HAP material removal as special waste",
    },
    "radon_reference": {
        "ref": "ORaP Art. 110",
        "name": "ORaP - Radon reference value",
        "required": "< 300 Bq/m3",
        "remediation": "Radon mitigation (sealing, ventilation)",
    },
    "radon_mandatory": {
        "ref": "ORaP Art. 110",
        "name": "ORaP - Radon mandatory action",
        "required": "< 1000 Bq/m3",
        "remediation": "Urgent radon mitigation required",
    },
}

# Maps (pollutant, threshold_key) -> regulation key
_THRESHOLD_TO_REGULATION: dict[tuple[str, str], str] = {
    ("asbestos", "material_content"): "asbestos_material",
    ("asbestos", "air_fiber_count"): "asbestos_air",
    ("pcb", "material_content"): "pcb_material",
    ("pcb", "air_indoor"): "pcb_air",
    ("lead", "paint_content"): "lead_paint",
    ("lead", "water"): "lead_water",
    ("hap", "material_content"): "hap_material",
    ("radon", "reference_value"): "radon_reference",
    ("radon", "mandatory_action"): "radon_mandatory",
}

# Unit normalization for matching
_UNIT_NORM: dict[str, str] = {
    "percent_weight": "percent_weight",
    "%": "percent_weight",
    "fibers_per_m3": "fibers_per_m3",
    "f/m3": "fibers_per_m3",
    "mg_per_kg": "mg_per_kg",
    "mg/kg": "mg_per_kg",
    "ng_per_m3": "ng_per_m3",
    "ng/m3": "ng_per_m3",
    "ug_per_l": "ug_per_l",
    "ug/l": "ug_per_l",
    "bq_per_m3": "bq_per_m3",
    "bq/m3": "bq_per_m3",
}

# Cost rates per regulation (CHF per affected unit)
_COST_RATES: dict[str, float] = {
    "asbestos_material": 180.0,
    "asbestos_air": 220.0,
    "pcb_material": 160.0,
    "pcb_air": 140.0,
    "lead_paint": 90.0,
    "lead_water": 200.0,
    "hap_material": 110.0,
    "radon_reference": 8000.0,
    "radon_mandatory": 15000.0,
}

# Cost split ratios
_LABOR_RATIO = 0.50
_MATERIALS_RATIO = 0.30
_DISPOSAL_RATIO = 0.20

# Range spread
_RANGE_LOW = 0.70
_RANGE_HIGH = 1.40

# Timeline estimates (weeks per regulation gap)
_WEEKS_PER_GAP: dict[str, int] = {
    "asbestos_material": 4,
    "asbestos_air": 3,
    "pcb_material": 4,
    "pcb_air": 2,
    "lead_paint": 3,
    "lead_water": 5,
    "hap_material": 3,
    "radon_reference": 4,
    "radon_mandatory": 2,
}

# Responsible parties
_RESPONSIBLE: dict[str, str] = {
    "asbestos_material": "Certified asbestos contractor (SUVA-recognized)",
    "asbestos_air": "Certified asbestos contractor (SUVA-recognized)",
    "pcb_material": "Specialized decontamination firm",
    "pcb_air": "Environmental remediation firm",
    "lead_paint": "Certified lead remediation contractor",
    "lead_water": "Licensed plumber",
    "hap_material": "Specialized decontamination firm",
    "radon_reference": "Radon mitigation specialist",
    "radon_mandatory": "Radon mitigation specialist (urgent)",
}

# Severity ordering
_SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _norm_unit(unit: str) -> str:
    return _UNIT_NORM.get(unit.lower().strip(), unit.lower().strip())


def _severity_from_ratio(ratio: float) -> str:
    if ratio >= 3.0:
        return "critical"
    if ratio >= 1.5:
        return "high"
    if ratio >= 1.0:
        return "medium"
    return "low"


def _worst_severity(a: str, b: str) -> str:
    return a if _SEVERITY_ORDER.get(a, 0) >= _SEVERITY_ORDER.get(b, 0) else b


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _fetch_building(db: AsyncSession, building_id: UUID) -> Building:
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _fetch_exceeded_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    """Return samples with threshold_exceeded from completed/validated diagnostics."""
    stmt = (
        select(Sample)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
            Sample.threshold_exceeded.is_(True),
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _fetch_all_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    """Return all samples from completed/validated diagnostics."""
    stmt = (
        select(Sample)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _match_regulation(pollutant: str, unit: str) -> str | None:
    """Find the regulation key matching a pollutant + unit pair."""
    p = pollutant.lower().strip()
    norm = _norm_unit(unit)
    entries = SWISS_THRESHOLDS.get(p, {})
    for threshold_key, entry in entries.items():
        if _norm_unit(entry["unit"]) == norm:
            return _THRESHOLD_TO_REGULATION.get((p, threshold_key))
    return None


def _build_gaps(samples: list[Sample]) -> list[ComplianceGapItem]:
    """Aggregate exceeded samples into gap items, one per regulation."""
    # Group by regulation key
    reg_groups: dict[str, list[Sample]] = {}
    for s in samples:
        if not s.pollutant_type or not s.unit:
            continue
        reg_key = _match_regulation(s.pollutant_type, s.unit)
        if reg_key:
            reg_groups.setdefault(reg_key, []).append(s)

    gaps: list[ComplianceGapItem] = []
    for reg_key, reg_samples in reg_groups.items():
        meta = _REGULATION_MAP.get(reg_key)
        if not meta:
            continue

        # Worst concentration determines severity
        worst_ratio = 0.0
        worst_concentration: float | None = None
        worst_unit = ""
        p = reg_samples[0].pollutant_type.lower() if reg_samples[0].pollutant_type else ""

        for s in reg_samples:
            if s.concentration is not None and s.unit:
                norm = _norm_unit(s.unit)
                entries = SWISS_THRESHOLDS.get(p, {})
                for entry in entries.values():
                    if _norm_unit(entry["unit"]) == norm and entry["threshold"] > 0:
                        ratio = s.concentration / entry["threshold"]
                        if ratio > worst_ratio:
                            worst_ratio = ratio
                            worst_concentration = s.concentration
                            worst_unit = s.unit

        severity = _severity_from_ratio(worst_ratio)
        current_desc = f"{worst_concentration} {worst_unit}" if worst_concentration is not None else "exceeded"

        gaps.append(
            ComplianceGapItem(
                pollutant_type=p,
                regulation_ref=meta["ref"],
                regulation_name=meta["name"],
                current_state=current_desc,
                required_state=meta["required"],
                severity=severity,
                remediation_path=meta["remediation"],
                sample_count=len(reg_samples),
            )
        )

    # Sort by severity descending
    gaps.sort(key=lambda g: _SEVERITY_ORDER.get(g.severity, 0), reverse=True)
    return gaps


def _compliant_regulations(samples: list[Sample], gaps: list[ComplianceGapItem]) -> list[str]:
    """Return regulation refs that have been checked but are compliant."""
    gap_refs = {g.regulation_ref for g in gaps}
    # Determine which pollutants were tested
    tested_pollutants: set[str] = set()
    for s in samples:
        if s.pollutant_type:
            tested_pollutants.add(s.pollutant_type.lower())

    compliant: list[str] = []
    for (p, _), reg_key in _THRESHOLD_TO_REGULATION.items():
        if p in tested_pollutants:
            meta = _REGULATION_MAP.get(reg_key)
            if meta and meta["ref"] not in gap_refs and meta["ref"] not in compliant:
                compliant.append(meta["ref"])
    return compliant


# ---------------------------------------------------------------------------
# FN1: identify_compliance_gaps
# ---------------------------------------------------------------------------


async def identify_compliance_gaps(db: AsyncSession, building_id: UUID) -> ComplianceGapReport:
    """Identify all non-compliance items for a building, per pollutant and regulation."""
    await _fetch_building(db, building_id)
    exceeded = await _fetch_exceeded_samples(db, building_id)
    all_samples = await _fetch_all_samples(db, building_id)

    gaps = _build_gaps(exceeded)
    compliant = _compliant_regulations(all_samples, gaps)

    return ComplianceGapReport(
        building_id=building_id,
        total_gaps=len(gaps),
        gaps=gaps,
        compliant_regulations=compliant,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: generate_compliance_roadmap
# ---------------------------------------------------------------------------


def _gaps_to_roadmap_steps(gaps: list[ComplianceGapItem]) -> list[RoadmapStep]:
    """Convert gap items into ordered roadmap steps with dependencies."""
    # Order: critical first, then high, medium, low
    steps: list[RoadmapStep] = []
    # Group by pollutant for dependency chains
    pollutant_steps: dict[str, list[int]] = {}

    for step_num, gap in enumerate(gaps, start=1):
        reg_key = _reg_key_from_ref(gap.pollutant_type, gap.regulation_ref)

        # Dependencies: air measurements depend on material removal for same pollutant
        deps: list[int] = []
        if "air" in (reg_key or ""):
            # Air gap depends on material gap for same pollutant
            for prev_step_num in pollutant_steps.get(gap.pollutant_type, []):
                deps.append(prev_step_num)

        weeks = _WEEKS_PER_GAP.get(reg_key or "", 3)
        responsible = _RESPONSIBLE.get(reg_key or "", "Qualified contractor")
        cost = _COST_RATES.get(reg_key or "", 100.0)

        step = RoadmapStep(
            step_number=step_num,
            title=f"Resolve {gap.regulation_name}",
            description=f"Current: {gap.current_state}. Required: {gap.required_state}. Action: {gap.remediation_path}",
            pollutant_type=gap.pollutant_type,
            regulation_ref=gap.regulation_ref,
            dependencies=deps,
            estimated_weeks=weeks,
            responsible_party=responsible,
            estimated_cost_chf=cost,
            is_critical_path=gap.severity in ("critical", "high"),
        )
        steps.append(step)
        pollutant_steps.setdefault(gap.pollutant_type, []).append(step_num)

    return steps


def _reg_key_from_ref(pollutant: str, ref: str) -> str | None:
    """Reverse-lookup regulation key from pollutant + ref."""
    for (p, _), reg_key in _THRESHOLD_TO_REGULATION.items():
        meta = _REGULATION_MAP.get(reg_key)
        if meta and p == pollutant.lower() and meta["ref"] == ref:
            return reg_key
    return None


async def generate_compliance_roadmap(db: AsyncSession, building_id: UUID) -> ComplianceRoadmap:
    """Generate ordered compliance roadmap with dependencies and critical path."""
    report = await identify_compliance_gaps(db, building_id)
    steps = _gaps_to_roadmap_steps(report.gaps)

    # Total weeks: sum of critical path steps (simplified: sequential critical, parallel non-critical)
    critical_weeks = sum(s.estimated_weeks for s in steps if s.is_critical_path)
    total_weeks = max(critical_weeks, sum(s.estimated_weeks for s in steps) if steps else 0)

    return ComplianceRoadmap(
        building_id=building_id,
        steps=steps,
        total_weeks=total_weeks,
        critical_path_weeks=critical_weeks,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: estimate_compliance_cost
# ---------------------------------------------------------------------------


def _make_range(base: float) -> CostRange:
    return CostRange(
        min_chf=round(base * _RANGE_LOW, 2),
        expected_chf=round(base, 2),
        max_chf=round(base * _RANGE_HIGH, 2),
    )


async def estimate_compliance_cost(db: AsyncSession, building_id: UUID) -> ComplianceCostEstimate:
    """Estimate total cost to reach full compliance with per-regulation and per-pollutant breakdown."""
    report = await identify_compliance_gaps(db, building_id)

    by_regulation: list[RegulationCostBreakdown] = []
    by_pollutant_map: dict[str, float] = {}

    total_base = 0.0

    for gap in report.gaps:
        reg_key = _reg_key_from_ref(gap.pollutant_type, gap.regulation_ref)
        base_cost = _COST_RATES.get(reg_key or "", 100.0) * gap.sample_count
        # Scale by severity
        severity_mult = {"critical": 2.0, "high": 1.5, "medium": 1.0, "low": 0.8}
        base_cost *= severity_mult.get(gap.severity, 1.0)

        by_regulation.append(
            RegulationCostBreakdown(
                regulation_ref=gap.regulation_ref,
                regulation_name=gap.regulation_name,
                cost=_make_range(base_cost),
            )
        )

        by_pollutant_map[gap.pollutant_type] = by_pollutant_map.get(gap.pollutant_type, 0.0) + base_cost
        total_base += base_cost

    by_pollutant = [
        PollutantCostBreakdown(pollutant_type=pt, cost=_make_range(cost))
        for pt, cost in sorted(by_pollutant_map.items(), key=lambda x: x[1], reverse=True)
    ]

    labor_base = total_base * _LABOR_RATIO
    materials_base = total_base * _MATERIALS_RATIO
    disposal_base = total_base * _DISPOSAL_RATIO

    return ComplianceCostEstimate(
        building_id=building_id,
        total=_make_range(total_base),
        by_regulation=by_regulation,
        by_pollutant=by_pollutant,
        by_category=LaborMaterialsDisposal(
            labor_chf=_make_range(labor_base),
            materials_chf=_make_range(materials_base),
            disposal_chf=_make_range(disposal_base),
        ),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_compliance_gaps
# ---------------------------------------------------------------------------


async def get_portfolio_compliance_gaps(db: AsyncSession, org_id: UUID) -> PortfolioComplianceGaps:
    """Organization-level compliance gap summary."""
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    total_buildings = len(buildings)
    buildings_with_gaps = 0
    total_gap_count = 0
    total_cost = 0.0
    gap_type_counts: dict[str, dict[str, int]] = {}  # ref -> {name, count}
    building_gaps: list[PortfolioBuildingGap] = []

    for building in buildings:
        exceeded = await _fetch_exceeded_samples(db, building.id)
        gaps = _build_gaps(exceeded)

        if gaps:
            buildings_with_gaps += 1

        gap_count = len(gaps)
        total_gap_count += gap_count

        # Estimate cost for this building
        building_cost = 0.0
        worst_sev = "low"
        for gap in gaps:
            reg_key = _reg_key_from_ref(gap.pollutant_type, gap.regulation_ref)
            base = _COST_RATES.get(reg_key or "", 100.0) * gap.sample_count
            severity_mult = {"critical": 2.0, "high": 1.5, "medium": 1.0, "low": 0.8}
            base *= severity_mult.get(gap.severity, 1.0)
            building_cost += base
            worst_sev = _worst_severity(worst_sev, gap.severity)

            # Track gap type counts
            ref = gap.regulation_ref
            if ref not in gap_type_counts:
                gap_type_counts[ref] = {"name": gap.regulation_name, "count": 0}
            gap_type_counts[ref]["count"] += 1

        total_cost += building_cost

        building_gaps.append(
            PortfolioBuildingGap(
                building_id=building.id,
                address=building.address,
                gap_count=gap_count,
                estimated_cost_chf=round(building_cost, 2),
                worst_severity=worst_sev,
            )
        )

    # Sort buildings by gap count descending, take top 10
    building_gaps.sort(key=lambda b: b.gap_count, reverse=True)
    furthest = building_gaps[:10]

    # Most common gap types, sorted by count
    most_common = sorted(
        [
            GapTypeCount(regulation_ref=ref, regulation_name=info["name"], count=info["count"])
            for ref, info in gap_type_counts.items()
        ],
        key=lambda g: g.count,
        reverse=True,
    )

    return PortfolioComplianceGaps(
        organization_id=org_id,
        total_buildings=total_buildings,
        buildings_with_gaps=buildings_with_gaps,
        total_gap_count=total_gap_count,
        estimated_total_cost_chf=round(total_cost, 2),
        most_common_gaps=most_common,
        furthest_from_compliance=furthest,
        generated_at=datetime.now(UTC),
    )
