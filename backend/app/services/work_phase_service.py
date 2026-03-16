"""Work Phase Service.

Plans detailed work phases for Swiss renovation projects following CFST 6503
work categories and OTConst/ORRChim/OLED/ORaP regulatory requirements.

Each positive pollutant finding generates a structured sequence of work phases:
preparation → containment → removal → decontamination → restoration → verification.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.schemas.work_phase import (
    CfstCategoryCount,
    PhaseRequirements,
    PhaseTimeline,
    PortfolioWorkOverview,
    TimelinePhase,
    WorkPhase,
    WorkPhasePlan,
)
from app.services.building_data_loader import load_org_buildings

# ---------------------------------------------------------------------------
# Phase type definitions and durations (days)
# ---------------------------------------------------------------------------

_PHASE_TYPES = (
    "preparation",
    "containment",
    "removal",
    "decontamination",
    "restoration",
    "verification",
)

# Base durations per phase type (days), scaled by CFST category
_BASE_DURATIONS: dict[str, dict[str, int]] = {
    "minor": {
        "preparation": 1,
        "containment": 1,
        "removal": 2,
        "decontamination": 1,
        "restoration": 2,
        "verification": 1,
    },
    "medium": {
        "preparation": 3,
        "containment": 2,
        "removal": 5,
        "decontamination": 3,
        "restoration": 4,
        "verification": 2,
    },
    "major": {
        "preparation": 5,
        "containment": 5,
        "removal": 10,
        "decontamination": 5,
        "restoration": 7,
        "verification": 3,
    },
}

# Equipment per phase type
_EQUIPMENT: dict[str, list[str]] = {
    "preparation": ["warning_signs", "barriers", "personal_protective_equipment"],
    "containment": ["polyethylene_sheeting", "negative_air_units", "hepa_filters", "airlocks"],
    "removal": ["wet_removal_tools", "hepa_vacuum", "sealed_waste_bags", "respiratory_protection"],
    "decontamination": ["hepa_vacuum", "damp_wiping_supplies", "encapsulant_sprayer"],
    "restoration": ["construction_materials", "finishing_tools"],
    "verification": ["air_monitoring_equipment", "pcm_cassettes", "calibrated_pumps"],
}

# Safety measures per phase type
_SAFETY_MEASURES: dict[str, list[str]] = {
    "preparation": ["site_access_restriction", "worker_medical_clearance", "safety_briefing"],
    "containment": ["negative_pressure_enclosure", "decontamination_unit", "air_monitoring_start"],
    "removal": ["wet_methods", "respiratory_protection_ffp3", "disposable_coveralls", "continuous_air_monitoring"],
    "decontamination": ["surface_cleaning", "hepa_vacuuming", "visual_inspection"],
    "restoration": ["clearance_before_restoration", "material_compatibility_check"],
    "verification": ["air_clearance_testing", "visual_reinspection", "clearance_certificate"],
}

# Regulatory references per pollutant
_REGULATORY_REFS: dict[str, list[str]] = {
    "asbestos": ["OTConst Art. 60a", "OTConst Art. 82-86", "CFST 6503", "SUVA 2891"],
    "pcb": ["ORRChim Annexe 2.15", "OLED Annexe 5"],
    "lead": ["ORRChim Annexe 2.18", "OSEC eau potable"],
    "hap": ["OLED dechet special"],
    "radon": ["ORaP Art. 110"],
}

# Personnel requirements per pollutant
_PERSONNEL: dict[str, list[str]] = {
    "asbestos": ["certified_asbestos_removal_specialist", "suva_approved_supervisor", "occupational_hygienist"],
    "pcb": ["pcb_remediation_specialist", "environmental_engineer"],
    "lead": ["lead_abatement_worker", "industrial_hygienist"],
    "hap": ["hap_remediation_specialist", "environmental_engineer"],
    "radon": ["radon_mitigation_specialist", "building_physicist"],
}

# Permits needed per pollutant
_PERMITS: dict[str, list[str]] = {
    "asbestos": ["suva_notification", "cantonal_waste_plan", "air_monitoring_plan"],
    "pcb": ["cantonal_waste_plan", "environmental_impact_declaration"],
    "lead": ["cantonal_waste_plan"],
    "hap": ["cantonal_waste_plan", "special_waste_declaration"],
    "radon": ["cantonal_building_permit_amendment"],
}


def _phase_id(building_id: uuid.UUID, suffix: str) -> str:
    raw = f"{building_id}:wp:{suffix}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _determine_cfst_category(sample: Sample) -> str:
    """Determine CFST 6503 work category from sample data."""
    state = (sample.material_state or "good").lower().strip()
    cat = (sample.material_category or "").lower()

    # Friable / heavily degraded → major
    friable_keywords = {"friable", "flocage", "spray", "calorifuge"}
    if state in ("friable", "heavily_degraded", "tres_degrade") or any(kw in cat for kw in friable_keywords):
        return "major"

    # Degraded → medium
    if state in ("degraded", "degrade", "mauvais"):
        return "medium"

    # Good/intact with high concentration → medium
    if sample.concentration and sample.threshold_exceeded:
        return "medium"

    return "minor"


async def _get_building(db: AsyncSession, building_id: uuid.UUID) -> Building | None:
    result = await db.execute(select(Building).where(Building.id == building_id))
    return result.scalar_one_or_none()


async def _get_positive_samples(db: AsyncSession, building_id: uuid.UUID) -> list[Sample]:
    """Get samples with threshold exceeded (positive pollutant findings)."""
    result = await db.execute(
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            Diagnostic.building_id == building_id,
            Sample.threshold_exceeded.is_(True),
        )
    )
    return list(result.scalars().all())


async def _get_org_building_ids(db: AsyncSession, org_id: uuid.UUID) -> list[uuid.UUID]:
    """Get building IDs belonging to an organization (via user.organization_id)."""
    buildings = await load_org_buildings(db, org_id)
    return [b.id for b in buildings]


# ---------------------------------------------------------------------------
# FN1: plan_work_phases
# ---------------------------------------------------------------------------


async def plan_work_phases(db: AsyncSession, building_id: uuid.UUID) -> WorkPhasePlan:
    """Return ordered work phases for a building renovation."""
    building = await _get_building(db, building_id)
    if not building:
        return WorkPhasePlan(
            building_id=building_id,
            phases=[],
            total_phases=0,
            generated_at=datetime.now(UTC),
        )

    samples = await _get_positive_samples(db, building_id)
    if not samples:
        return WorkPhasePlan(
            building_id=building_id,
            phases=[],
            total_phases=0,
            generated_at=datetime.now(UTC),
        )

    phases: list[WorkPhase] = []
    order = 0

    # Group samples by pollutant, pick worst CFST category per pollutant
    pollutant_categories: dict[str, str] = {}
    category_priority = {"major": 3, "medium": 2, "minor": 1}

    for s in samples:
        pt = s.pollutant_type
        if not pt:
            continue
        cat = _determine_cfst_category(s)
        existing = pollutant_categories.get(pt)
        if existing is None or category_priority.get(cat, 0) > category_priority.get(existing, 0):
            pollutant_categories[pt] = cat

    # Sort pollutants: asbestos first, then by severity
    pollutant_order = {"asbestos": 1, "pcb": 2, "lead": 3, "hap": 4, "radon": 5}
    sorted_pollutants = sorted(
        pollutant_categories.keys(),
        key=lambda p: pollutant_order.get(p, 99),
    )

    for pollutant in sorted_pollutants:
        cfst_cat = pollutant_categories[pollutant]
        durations = _BASE_DURATIONS[cfst_cat]
        prev_phase_id: str | None = None

        for phase_type in _PHASE_TYPES:
            pid = _phase_id(building_id, f"{pollutant}-{phase_type}")
            deps = [prev_phase_id] if prev_phase_id else []

            phases.append(
                WorkPhase(
                    phase_id=pid,
                    phase_name=f"{pollutant.capitalize()} - {phase_type.replace('_', ' ').title()}",
                    phase_type=phase_type,
                    duration_days=durations[phase_type],
                    dependencies=deps,
                    cfst_category=cfst_cat,
                    required_equipment=_EQUIPMENT.get(phase_type, []),
                    safety_measures=_SAFETY_MEASURES.get(phase_type, []),
                    pollutant=pollutant,
                    order=order,
                )
            )
            prev_phase_id = pid
            order += 1

    return WorkPhasePlan(
        building_id=building_id,
        phases=phases,
        total_phases=len(phases),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: estimate_phase_timeline
# ---------------------------------------------------------------------------


async def estimate_phase_timeline(db: AsyncSession, building_id: uuid.UUID) -> PhaseTimeline:
    """Return Gantt-style timeline with start/end dates and critical path."""
    plan = await plan_work_phases(db, building_id)
    now = datetime.now(UTC)

    # Earliest feasible start: next business day
    start_date = (now + timedelta(days=1)).date()
    if start_date.weekday() >= 5:  # Saturday/Sunday
        start_date += timedelta(days=(7 - start_date.weekday()))

    if not plan.phases:
        return PhaseTimeline(
            building_id=building_id,
            total_duration_days=0,
            start_date=start_date,
            end_date=start_date,
            phases=[],
            critical_path=[],
            parallel_possible=[],
            generated_at=now,
        )

    # Compute start/end for each phase based on dependencies
    phase_end_day: dict[str, int] = {}
    timeline_phases: list[TimelinePhase] = []

    for phase in plan.phases:
        if phase.dependencies:
            phase_start_day = max(phase_end_day.get(d, 0) for d in phase.dependencies)
        else:
            phase_start_day = 0

        end_day = phase_start_day + phase.duration_days
        phase_end_day[phase.phase_id] = end_day

        phase_start = start_date + timedelta(days=phase_start_day)
        phase_end = start_date + timedelta(days=end_day)

        timeline_phases.append(
            TimelinePhase(
                phase_id=phase.phase_id,
                phase_name=phase.phase_name,
                phase_type=phase.phase_type,
                start_date=phase_start,
                end_date=phase_end,
                duration_days=phase.duration_days,
                is_critical_path=False,
                parallel_possible=False,
            )
        )

    total_duration = max(phase_end_day.values()) if phase_end_day else 0
    end_date = start_date + timedelta(days=total_duration)

    # Critical path: walk backwards from longest-ending phases
    critical_ids = _compute_critical_path(plan.phases, phase_end_day, total_duration)

    # Parallel possible: phases that share the same start day but different pollutants
    parallel_ids = _find_parallel_possible(plan.phases, phase_end_day)

    for tp in timeline_phases:
        tp.is_critical_path = tp.phase_id in critical_ids
        tp.parallel_possible = tp.phase_id in parallel_ids

    return PhaseTimeline(
        building_id=building_id,
        total_duration_days=total_duration,
        start_date=start_date,
        end_date=end_date,
        phases=timeline_phases,
        critical_path=critical_ids,
        parallel_possible=parallel_ids,
        generated_at=now,
    )


def _compute_critical_path(
    phases: list[WorkPhase],
    end_map: dict[str, int],
    total_duration: int,
) -> list[str]:
    """Identify phases on the critical path (longest dependency chain)."""
    if not phases:
        return []

    phase_map = {p.phase_id: p for p in phases}
    end_phases = [p for p in phases if end_map.get(p.phase_id, 0) == total_duration]

    visited: set[str] = set()
    critical: list[str] = []
    stack = [p.phase_id for p in end_phases]

    while stack:
        pid = stack.pop()
        if pid in visited:
            continue
        visited.add(pid)
        critical.append(pid)
        phase = phase_map.get(pid)
        if phase:
            for dep in phase.dependencies:
                stack.append(dep)

    # Return in chronological order
    start_map: dict[str, int] = {}
    for p in phases:
        s = 0
        if p.dependencies:
            s = max(end_map.get(d, 0) for d in p.dependencies)
        start_map[p.phase_id] = s

    critical.sort(key=lambda x: start_map.get(x, 0))
    return critical


def _find_parallel_possible(
    phases: list[WorkPhase],
    end_map: dict[str, int],
) -> list[str]:
    """Find phases that could theoretically run in parallel (different pollutants, same phase_type)."""
    # Group by phase_type
    by_type: dict[str, list[WorkPhase]] = {}
    for p in phases:
        by_type.setdefault(p.phase_type, []).append(p)

    parallel: set[str] = set()
    for _phase_type, group in by_type.items():
        if len(group) > 1:
            # Different pollutants doing the same phase type can run in parallel
            pollutants = {p.pollutant for p in group}
            if len(pollutants) > 1:
                for p in group:
                    parallel.add(p.phase_id)

    return list(parallel)


# ---------------------------------------------------------------------------
# FN3: get_phase_requirements
# ---------------------------------------------------------------------------


async def get_phase_requirements(
    db: AsyncSession,
    building_id: uuid.UUID,
    phase_type: str,
) -> PhaseRequirements:
    """Return detailed requirements for a specific phase type at a building."""
    samples = await _get_positive_samples(db, building_id)

    pollutants_found = {s.pollutant_type for s in samples if s.pollutant_type}

    # Aggregate regulatory references
    reg_refs: list[str] = []
    personnel: list[str] = []
    permits: list[str] = []

    for pollutant in sorted(pollutants_found):
        reg_refs.extend(_REGULATORY_REFS.get(pollutant, []))
        personnel.extend(_PERSONNEL.get(pollutant, []))
        permits.extend(_PERMITS.get(pollutant, []))

    # Deduplicate while preserving order
    reg_refs = list(dict.fromkeys(reg_refs))
    personnel = list(dict.fromkeys(personnel))
    permits = list(dict.fromkeys(permits))

    # Waste management plan
    waste_plan: str | None = None
    if phase_type == "removal" and pollutants_found:
        waste_plan = f"OLED-compliant waste elimination plan required for: {', '.join(sorted(pollutants_found))}"
    elif phase_type == "decontamination" and pollutants_found:
        waste_plan = "Decontamination waste must follow OLED special waste disposal procedures"

    # Air monitoring required for containment, removal, decontamination, verification
    air_monitoring = phase_type in ("containment", "removal", "decontamination", "verification")

    # For asbestos specifically, air monitoring is always required
    if "asbestos" in pollutants_found:
        air_monitoring = True

    return PhaseRequirements(
        building_id=building_id,
        phase_type=phase_type,
        regulatory_references=reg_refs,
        qualified_personnel=personnel,
        permits_needed=permits,
        waste_management_plan=waste_plan,
        air_monitoring_required=air_monitoring,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_work_overview
# ---------------------------------------------------------------------------


async def get_portfolio_work_overview(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> PortfolioWorkOverview:
    """Return organization-wide work overview."""
    # Verify org exists
    org_result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = org_result.scalar_one_or_none()
    if not org:
        return PortfolioWorkOverview(
            organization_id=org_id,
            buildings_with_planned_work=0,
            total_phases_pending=0,
            estimated_total_duration_days=0,
            buildings_by_cfst_category=[],
            generated_at=datetime.now(UTC),
        )

    building_ids = await _get_org_building_ids(db, org_id)

    buildings_with_work = 0
    total_phases = 0
    total_duration = 0
    category_counts: dict[str, int] = {"minor": 0, "medium": 0, "major": 0}

    for bid in building_ids:
        plan = await plan_work_phases(db, bid)
        if plan.total_phases > 0:
            buildings_with_work += 1
            total_phases += plan.total_phases

            # Duration: sum of all phase durations (sequential worst case)
            total_duration += sum(p.duration_days for p in plan.phases)

            # Track the worst CFST category for this building
            worst_cat = "minor"
            cat_priority = {"minor": 1, "medium": 2, "major": 3}
            for p in plan.phases:
                if cat_priority.get(p.cfst_category, 0) > cat_priority.get(worst_cat, 0):
                    worst_cat = p.cfst_category
            category_counts[worst_cat] = category_counts.get(worst_cat, 0) + 1

    return PortfolioWorkOverview(
        organization_id=org_id,
        buildings_with_planned_work=buildings_with_work,
        total_phases_pending=total_phases,
        estimated_total_duration_days=total_duration,
        buildings_by_cfst_category=[
            CfstCategoryCount(category=cat, count=count) for cat, count in sorted(category_counts.items()) if count > 0
        ],
        generated_at=datetime.now(UTC),
    )
