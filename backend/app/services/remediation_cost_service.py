"""
SwissBuildingOS - Remediation Cost Estimation Service

Estimates remediation costs in CHF based on building diagnostics,
pollutant findings, and surface areas.  Uses simplified Swiss market
rates aligned with OTConst, CFST 6503, and OLED waste categories.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.remediation_cost import (
    BuildingCostComparison,
    CostFactors,
    PollutantCostBreakdown,
    RemediationCostEstimate,
)

# ---------------------------------------------------------------------------
# Cost constants (CHF, Swiss market rates - simplified)
# ---------------------------------------------------------------------------

# Asbestos removal by CFST 6503 work category
ASBESTOS_RATES: dict[str, float] = {
    "minor": 45.0,
    "medium": 120.0,
    "major": 280.0,
}

# PCB decontamination by material
PCB_RATES: dict[str, float] = {
    "joints": 150.0,
    "coatings": 200.0,
}
PCB_DEFAULT_RATE = 150.0

# Other pollutants
LEAD_RATE = 80.0  # CHF/m²
HAP_RATE = 100.0  # CHF/m²

# Radon
RADON_FIXED = 5000.0  # CHF fixed
RADON_VARIABLE = 15.0  # CHF/m² ventilation

# Waste disposal surcharge (fraction of remediation cost)
WASTE_SURCHARGES: dict[str, float] = {
    "type_b": 0.20,
    "type_e": 0.35,
    "special": 0.50,
}

# Safety setup
SAFETY_BASE = 3000.0  # CHF per intervention
SAFETY_PER_FLOOR = 500.0  # CHF per floor

# Lab analysis
LAB_COSTS: dict[str, float] = {
    "asbestos": 150.0,
    "pcb": 200.0,
    "lead": 120.0,
    "hap": 120.0,
    "radon": 120.0,
}

# Age factor threshold
_PRE_1991_FACTOR = 1.2

# Cost range spread (±30%)
_RANGE_SPREAD = 0.30

# Weeks per pollutant (rough estimate)
_WEEKS_PER_POLLUTANT = 3


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _age_factor(construction_year: int | None) -> float:
    if construction_year is not None and construction_year < 1991:
        return _PRE_1991_FACTOR
    return 1.0


def _floors_count(building: Building) -> int:
    above = building.floors_above or 0
    below = building.floors_below or 0
    return max(above + below, 1)


def _surface(building: Building) -> float:
    return building.surface_area_m2 or 0.0


def _unit_cost_for_pollutant(
    pollutant_type: str,
    work_category: str | None,
    material_category: str | None,
) -> float:
    if pollutant_type == "asbestos":
        return ASBESTOS_RATES.get(work_category or "minor", ASBESTOS_RATES["minor"])
    if pollutant_type == "pcb":
        if material_category and "joint" in material_category.lower():
            return PCB_RATES["joints"]
        if material_category and "coat" in material_category.lower():
            return PCB_RATES["coatings"]
        return PCB_DEFAULT_RATE
    if pollutant_type == "lead":
        return LEAD_RATE
    if pollutant_type == "hap":
        return HAP_RATE
    # radon handled separately
    return 0.0


def _dominant_waste_type(samples: list[Sample]) -> str | None:
    """Pick the most severe waste type among samples."""
    priority = {"special": 3, "type_e": 2, "type_b": 1}
    best: str | None = None
    best_p = 0
    for s in samples:
        wt = s.waste_disposal_type
        if wt and priority.get(wt, 0) > best_p:
            best = wt
            best_p = priority[wt]
    return best


def _dominant_work_category(samples: list[Sample]) -> str | None:
    priority = {"major": 3, "medium": 2, "minor": 1}
    best: str | None = None
    best_p = 0
    for s in samples:
        wc = s.cfst_work_category
        if wc and priority.get(wc, 0) > best_p:
            best = wc
            best_p = priority[wc]
    return best


async def _fetch_building(db: AsyncSession, building_id: UUID) -> Building:
    stmt = select(Building).where(Building.id == building_id)
    result = await db.execute(stmt)
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _fetch_samples_by_pollutant(db: AsyncSession, building_id: UUID) -> dict[str, list[Sample]]:
    """Return samples grouped by pollutant_type for completed diagnostics."""
    stmt = (
        select(Sample)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
        )
    )
    result = await db.execute(stmt)
    samples = result.scalars().all()
    grouped: dict[str, list[Sample]] = {}
    for s in samples:
        pt = s.pollutant_type
        if pt:
            grouped.setdefault(pt, []).append(s)
    return grouped


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def estimate_building_cost(db: AsyncSession, building_id: UUID) -> RemediationCostEstimate:
    """Full building remediation cost estimate with per-pollutant breakdown."""
    building = await _fetch_building(db, building_id)
    grouped = await _fetch_samples_by_pollutant(db, building_id)

    surface = _surface(building)
    age_f = _age_factor(building.construction_year)
    floors = _floors_count(building)

    breakdowns: list[PollutantCostBreakdown] = []
    total_remediation = 0.0
    total_waste = 0.0
    total_lab = 0.0
    pollutant_count = 0

    for pollutant_type, samples in grouped.items():
        pollutant_count += 1
        bd = _compute_pollutant_breakdown(pollutant_type, samples, surface, age_f)
        breakdowns.append(bd)
        total_remediation += bd.subtotal_chf
        total_waste += bd.waste_surcharge_chf
        total_lab += bd.lab_cost_chf

    # Safety cost: one setup per pollutant intervention
    safety = 0.0
    if pollutant_count > 0:
        safety = pollutant_count * (SAFETY_BASE + SAFETY_PER_FLOOR * floors)

    total_base = total_remediation + total_waste + total_lab + safety
    total_min = total_base * (1 - _RANGE_SPREAD)
    total_max = total_base * (1 + _RANGE_SPREAD)

    timeline_weeks = pollutant_count * _WEEKS_PER_POLLUTANT

    return RemediationCostEstimate(
        building_id=building_id,
        pollutant_breakdowns=breakdowns,
        total_min_chf=round(total_min, 2),
        total_max_chf=round(total_max, 2),
        waste_cost_chf=round(total_waste, 2),
        safety_cost_chf=round(safety, 2),
        lab_cost_chf=round(total_lab, 2),
        timeline_weeks_estimate=timeline_weeks,
        generated_at=datetime.now(UTC),
    )


def _compute_pollutant_breakdown(
    pollutant_type: str,
    samples: list[Sample],
    surface: float,
    age_factor: float,
) -> PollutantCostBreakdown:
    """Compute cost breakdown for a single pollutant type."""
    sample_count = len(samples)
    work_category = _dominant_work_category(samples)
    waste_type = _dominant_waste_type(samples)

    # Lab costs
    lab_unit = LAB_COSTS.get(pollutant_type, 120.0)
    lab_cost = lab_unit * sample_count

    if pollutant_type == "radon":
        # Radon: fixed + variable model
        unit_cost = RADON_VARIABLE
        subtotal = (RADON_FIXED + RADON_VARIABLE * surface) * age_factor
        affected_area = surface
    else:
        # Area-based: use building surface as affected area estimate
        material_cat = samples[0].material_category if samples else None
        unit_cost = _unit_cost_for_pollutant(pollutant_type, work_category, material_cat)
        affected_area = surface
        subtotal = unit_cost * affected_area * age_factor

    # Waste surcharge
    waste_surcharge = 0.0
    if waste_type and waste_type in WASTE_SURCHARGES:
        waste_surcharge = subtotal * WASTE_SURCHARGES[waste_type]

    return PollutantCostBreakdown(
        pollutant_type=pollutant_type,
        work_category=work_category,
        affected_area_m2=round(affected_area, 2),
        unit_cost_chf=round(unit_cost, 2),
        subtotal_chf=round(subtotal, 2),
        waste_surcharge_chf=round(waste_surcharge, 2),
        sample_count=sample_count,
        lab_cost_chf=round(lab_cost, 2),
    )


async def estimate_pollutant_cost(db: AsyncSession, building_id: UUID, pollutant_type: str) -> PollutantCostBreakdown:
    """Single pollutant detail for a building."""
    building = await _fetch_building(db, building_id)
    grouped = await _fetch_samples_by_pollutant(db, building_id)

    samples = grouped.get(pollutant_type, [])
    surface = _surface(building)
    age_f = _age_factor(building.construction_year)

    return _compute_pollutant_breakdown(pollutant_type, samples, surface, age_f)


async def compare_building_costs(db: AsyncSession, building_ids: list[UUID]) -> list[BuildingCostComparison]:
    """Compare up to 10 buildings by remediation cost."""
    if len(building_ids) > 10:
        raise ValueError("Cannot compare more than 10 buildings at once")

    results: list[tuple[UUID, str, float, float]] = []
    for bid in building_ids:
        building = await _fetch_building(db, bid)
        estimate = await estimate_building_cost(db, bid)
        total = (estimate.total_min_chf + estimate.total_max_chf) / 2
        surface = _surface(building)
        cost_m2 = total / surface if surface > 0 else 0.0

        # Identify primary cost driver
        driver: str | None = None
        if estimate.pollutant_breakdowns:
            top = max(estimate.pollutant_breakdowns, key=lambda b: b.subtotal_chf)
            driver = top.pollutant_type

        results.append((bid, building.address, total, cost_m2, driver))

    # Sort by total cost descending for ranking
    results.sort(key=lambda r: r[2], reverse=True)

    return [
        BuildingCostComparison(
            building_id=bid,
            address=addr,
            total_estimate_chf=round(total, 2),
            cost_per_m2=round(cpm2, 2),
            rank=i + 1,
            primary_cost_driver=driver,
        )
        for i, (bid, addr, total, cpm2, driver) in enumerate(results)
    ]


async def get_cost_factors(db: AsyncSession, building_id: UUID) -> CostFactors:
    """Explain what drives the cost for a building."""
    building = await _fetch_building(db, building_id)
    grouped = await _fetch_samples_by_pollutant(db, building_id)

    age_f = _age_factor(building.construction_year)
    floors = _floors_count(building)
    floors_f = 1.0 + (floors - 1) * 0.1  # 10% per additional floor
    surface = _surface(building)
    pollutant_count = len(grouped)

    urgency_flags: list[str] = []
    for pt, samples in grouped.items():
        for s in samples:
            if s.risk_level == "critical":
                flag = f"{pt}_critical"
                if flag not in urgency_flags:
                    urgency_flags.append(flag)
            if s.cfst_work_category == "major":
                flag = f"{pt}_major_works"
                if flag not in urgency_flags:
                    urgency_flags.append(flag)
            if s.waste_disposal_type == "special":
                flag = f"{pt}_special_waste"
                if flag not in urgency_flags:
                    urgency_flags.append(flag)

    return CostFactors(
        building_id=building_id,
        age_factor=round(age_f, 2),
        floors_factor=round(floors_f, 2),
        pollutant_count=pollutant_count,
        surface_area_m2=round(surface, 2),
        urgency_flags=urgency_flags,
    )
