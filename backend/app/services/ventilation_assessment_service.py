"""Ventilation Assessment Service.

Evaluates ventilation requirements for buildings based on pollutant presence:
- Radon zones need forced ventilation (ORaP Art. 110: 300/1000 Bq/m3)
- Asbestos zones need negative pressure during works
- PCB zones need air monitoring
- Generates air quality monitoring plans for remediation

References:
- ORaP Art. 110: radon reference 300 Bq/m3, limit 1000 Bq/m3
- CFST 6503: work categories for asbestos
- OTConst Art. 60a, 82-86: asbestos handling
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.ventilation_assessment import (
    AirQualityMonitoringPlan,
    BuildingVentilationStatus,
    MonitoringPoint,
    PortfolioVentilationStatus,
    RadonMitigationRecommendation,
    RadonVentilationEvaluation,
    VentilationAssessment,
    VentilationRequirement,
)
from app.services.building_data_loader import load_org_buildings

# ORaP Art. 110 thresholds
RADON_REFERENCE_BQ_M3 = 300.0
RADON_LIMIT_BQ_M3 = 1000.0

# Ventilation specs per pollutant
_VENTILATION_SPECS: dict[str, dict] = {
    "radon": {
        "ventilation_type": "forced",
        "air_changes_per_hour": 0.5,
        "filtration": None,
        "monitoring_frequency": "monthly",
        "rationale": "ORaP Art. 110 — radon above reference level requires forced ventilation",
    },
    "radon_high": {
        "ventilation_type": "forced",
        "air_changes_per_hour": 1.0,
        "filtration": None,
        "monitoring_frequency": "weekly",
        "rationale": "ORaP Art. 110 — radon above limit requires enhanced forced ventilation",
    },
    "asbestos": {
        "ventilation_type": "negative_pressure",
        "air_changes_per_hour": 6.0,
        "filtration": "HEPA",
        "monitoring_frequency": "continuous",
        "rationale": "OTConst Art. 82-86 — asbestos remediation requires negative pressure with HEPA filtration",
    },
    "pcb": {
        "ventilation_type": "forced",
        "air_changes_per_hour": 2.0,
        "filtration": "activated_carbon",
        "monitoring_frequency": "daily",
        "rationale": "ORRChim Annexe 2.15 — PCB above threshold requires air monitoring and forced ventilation",
    },
    "lead": {
        "ventilation_type": "forced",
        "air_changes_per_hour": 1.0,
        "filtration": "HEPA",
        "monitoring_frequency": "daily",
        "rationale": "ORRChim Annexe 2.18 — lead dust control during works requires HEPA filtration",
    },
    "hap": {
        "ventilation_type": "forced",
        "air_changes_per_hour": 3.0,
        "filtration": "activated_carbon",
        "monitoring_frequency": "daily",
        "rationale": "HAP remediation requires forced ventilation with activated carbon filtration",
    },
}

# Radon mitigation methods and their characteristics
_RADON_MITIGATION: dict[str, dict] = {
    "sub_slab_depressurization": {
        "expected_reduction_pct": 80.0,
        "cost_chf": 8000.0,
        "priority_threshold": RADON_LIMIT_BQ_M3,
    },
    "forced_ventilation": {
        "expected_reduction_pct": 50.0,
        "cost_chf": 3500.0,
        "priority_threshold": RADON_REFERENCE_BQ_M3,
    },
    "sealing": {
        "expected_reduction_pct": 30.0,
        "cost_chf": 2000.0,
        "priority_threshold": RADON_REFERENCE_BQ_M3,
    },
}


def _sample_location(s: Sample) -> str:
    """Build a human-readable location string from sample fields."""
    parts = [p for p in [s.location_floor, s.location_room, s.location_detail] if p]
    return " / ".join(parts) if parts else "Unknown location"


def _radon_priority(concentration: float) -> str:
    """Determine radon mitigation priority from concentration."""
    if concentration >= RADON_LIMIT_BQ_M3:
        return "critical"
    if concentration >= 600:
        return "high"
    if concentration >= RADON_REFERENCE_BQ_M3:
        return "medium"
    return "low"


def _select_radon_mitigation(concentration: float) -> str:
    """Select best mitigation method based on radon level."""
    if concentration >= RADON_LIMIT_BQ_M3:
        return "sub_slab_depressurization"
    if concentration >= 600:
        return "combined"
    return "forced_ventilation"


async def _get_pollutant_samples(
    db: AsyncSession,
    building_id: uuid.UUID,
    pollutant_type: str,
    *,
    threshold_exceeded: bool = False,
) -> list[Sample]:
    """Fetch samples of a given pollutant type from completed diagnostics."""
    query = (
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
            Sample.pollutant_type == pollutant_type,
        )
    )
    if threshold_exceeded:
        query = query.where(Sample.threshold_exceeded.is_(True))

    result = await db.execute(query)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# FN1: assess_ventilation_needs
# ---------------------------------------------------------------------------


async def assess_ventilation_needs(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> VentilationAssessment:
    """Per-zone ventilation requirements based on detected pollutants.

    Radon zones need forced ventilation, asbestos zones need negative pressure
    during works, PCB zones need air monitoring with forced ventilation.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return VentilationAssessment(
            building_id=building_id,
            requirements=[],
            total_zones_assessed=0,
            zones_needing_upgrade=0,
            generated_at=datetime.now(UTC),
        )

    requirements: list[VentilationRequirement] = []

    for pollutant in ["radon", "asbestos", "pcb", "lead", "hap"]:
        if pollutant == "radon":
            samples = await _get_pollutant_samples(db, building_id, pollutant, threshold_exceeded=True)
        else:
            samples = await _get_pollutant_samples(db, building_id, pollutant, threshold_exceeded=True)

        for s in samples:
            location = _sample_location(s)
            # Radon high vs standard
            if pollutant == "radon" and s.concentration and s.concentration >= RADON_LIMIT_BQ_M3:
                spec = _VENTILATION_SPECS["radon_high"]
            elif pollutant == "radon":
                spec = _VENTILATION_SPECS["radon"]
            else:
                spec = _VENTILATION_SPECS[pollutant]

            requirements.append(
                VentilationRequirement(
                    zone_id=None,
                    zone_name=location,
                    pollutant_type=pollutant,
                    ventilation_type=spec["ventilation_type"],
                    air_changes_per_hour=spec["air_changes_per_hour"],
                    filtration=spec["filtration"],
                    monitoring_frequency=spec["monitoring_frequency"],
                    rationale=spec["rationale"],
                )
            )

    # Count zones from building zones table
    zone_result = await db.execute(select(func.count()).select_from(Zone).where(Zone.building_id == building_id))
    total_zones = zone_result.scalar() or 0
    # If no zones defined, count based on unique sample locations
    if total_zones == 0:
        total_zones = max(len({r.zone_name for r in requirements}), 0)

    return VentilationAssessment(
        building_id=building_id,
        requirements=requirements,
        total_zones_assessed=total_zones,
        zones_needing_upgrade=len(requirements),
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: evaluate_radon_ventilation
# ---------------------------------------------------------------------------


async def evaluate_radon_ventilation(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> RadonVentilationEvaluation:
    """Radon-specific evaluation: current levels, ventilation adequacy,
    recommended mitigation, cost estimates, expected reduction.

    Thresholds per ORaP Art. 110:
    - Reference: 300 Bq/m3
    - Limit: 1000 Bq/m3
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return RadonVentilationEvaluation(
            building_id=building_id,
            total_zones_measured=0,
            zones_above_reference=0,
            zones_above_limit=0,
            recommendations=[],
            total_estimated_cost_chf=0.0,
            generated_at=datetime.now(UTC),
        )

    # Get all radon samples (not just threshold exceeded)
    all_radon = await _get_pollutant_samples(db, building_id, "radon")
    exceeded = [s for s in all_radon if s.threshold_exceeded]

    zones_above_ref = 0
    zones_above_limit = 0
    recommendations: list[RadonMitigationRecommendation] = []
    total_cost = 0.0

    for s in exceeded:
        concentration = s.concentration or 0.0
        if concentration >= RADON_LIMIT_BQ_M3:
            zones_above_limit += 1
            zones_above_ref += 1
        elif concentration >= RADON_REFERENCE_BQ_M3:
            zones_above_ref += 1

        method = _select_radon_mitigation(concentration)
        priority = _radon_priority(concentration)

        if method == "combined":
            # Combined approach: sub-slab + sealing
            reduction = 90.0
            cost = 10000.0
        else:
            spec = _RADON_MITIGATION[method]
            reduction = spec["expected_reduction_pct"]
            cost = spec["cost_chf"]

        total_cost += cost

        threshold = RADON_LIMIT_BQ_M3 if concentration >= RADON_LIMIT_BQ_M3 else RADON_REFERENCE_BQ_M3

        recommendations.append(
            RadonMitigationRecommendation(
                zone_name=_sample_location(s),
                current_level_bq_m3=concentration,
                threshold_bq_m3=threshold,
                mitigation_method=method,
                expected_reduction_pct=reduction,
                estimated_cost_chf=cost,
                priority=priority,
            )
        )

    return RadonVentilationEvaluation(
        building_id=building_id,
        total_zones_measured=len(all_radon),
        zones_above_reference=zones_above_ref,
        zones_above_limit=zones_above_limit,
        recommendations=recommendations,
        total_estimated_cost_chf=total_cost,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: get_air_quality_monitoring_plan
# ---------------------------------------------------------------------------

# Monitoring specs per pollutant
_MONITORING_SPECS: dict[str, list[dict]] = {
    "asbestos": [
        {
            "parameter": "fiber_count",
            "frequency": "continuous",
            "threshold_value": 0.01,
            "threshold_unit": "fibers/ml",
            "alarm_trigger": 0.05,
            "documentation_required": "Real-time fiber counter log + daily report",
        },
    ],
    "radon": [
        {
            "parameter": "radon_level",
            "frequency": "hourly",
            "threshold_value": 300.0,
            "threshold_unit": "Bq/m3",
            "alarm_trigger": 1000.0,
            "documentation_required": "Continuous radon monitor data + weekly summary",
        },
    ],
    "pcb": [
        {
            "parameter": "pcb_concentration",
            "frequency": "daily",
            "threshold_value": 50.0,
            "threshold_unit": "mg/kg",
            "alarm_trigger": 100.0,
            "documentation_required": "Air sample analysis report per sampling point",
        },
    ],
    "lead": [
        {
            "parameter": "lead_dust",
            "frequency": "daily",
            "threshold_value": 0.05,
            "threshold_unit": "mg/m3",
            "alarm_trigger": 0.15,
            "documentation_required": "Air sample analysis + wipe test results",
        },
    ],
    "hap": [
        {
            "parameter": "voc_level",
            "frequency": "daily",
            "threshold_value": 0.5,
            "threshold_unit": "mg/m3",
            "alarm_trigger": 2.0,
            "documentation_required": "VOC monitoring report + sample analysis",
        },
    ],
}


async def get_air_quality_monitoring_plan(
    db: AsyncSession,
    building_id: uuid.UUID,
) -> AirQualityMonitoringPlan:
    """Generate monitoring requirements during and after remediation.

    Includes measurement points, frequency, thresholds, alarm triggers,
    and documentation requirements per pollutant type found.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return AirQualityMonitoringPlan(
            building_id=building_id,
            monitoring_points=[],
            total_points=0,
            during_works=False,
            post_remediation=False,
            estimated_duration_days=0,
            generated_at=datetime.now(UTC),
        )

    points: list[MonitoringPoint] = []
    has_works_pollutants = False
    has_post_pollutants = False
    max_duration = 0

    for pollutant in ["asbestos", "radon", "pcb", "lead", "hap"]:
        samples = await _get_pollutant_samples(db, building_id, pollutant, threshold_exceeded=True)
        if not samples:
            continue

        specs = _MONITORING_SPECS.get(pollutant, [])

        for s in samples:
            location = _sample_location(s)
            for spec in specs:
                points.append(
                    MonitoringPoint(
                        location=location,
                        parameter=spec["parameter"],
                        frequency=spec["frequency"],
                        threshold_value=spec["threshold_value"],
                        threshold_unit=spec["threshold_unit"],
                        alarm_trigger=spec["alarm_trigger"],
                        documentation_required=spec["documentation_required"],
                    )
                )

        # Asbestos, PCB, lead, HAP require during-works monitoring
        if pollutant in ("asbestos", "pcb", "lead", "hap"):
            has_works_pollutants = True
            max_duration = max(max_duration, 30)  # 30 days minimum during works

        # Radon requires post-remediation monitoring
        if pollutant == "radon":
            has_post_pollutants = True
            max_duration = max(max_duration, 90)  # 90 days post-ventilation install

        # Post-remediation for asbestos clearance
        if pollutant == "asbestos":
            has_post_pollutants = True
            max_duration = max(max_duration, 14)  # 14 days clearance monitoring

    return AirQualityMonitoringPlan(
        building_id=building_id,
        monitoring_points=points,
        total_points=len(points),
        during_works=has_works_pollutants,
        post_remediation=has_post_pollutants,
        estimated_duration_days=max_duration,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_ventilation_status
# ---------------------------------------------------------------------------


async def get_portfolio_ventilation_status(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> PortfolioVentilationStatus:
    """Org-level ventilation status: buildings needing upgrades, radon
    mitigation priority list, total cost, ORaP Art. 110 compliance."""
    all_buildings = await load_org_buildings(db, org_id)
    # Post-filter: only active buildings
    buildings = [b for b in all_buildings if getattr(b, "status", None) == "active"]

    building_statuses: list[BuildingVentilationStatus] = []
    total_cost = 0.0
    buildings_needing_upgrade = 0
    orap_compliant_count = 0

    for b in buildings:
        assessment = await assess_ventilation_needs(db, b.id)
        radon_eval = await evaluate_radon_ventilation(db, b.id)

        needs_upgrade = assessment.zones_needing_upgrade > 0
        if needs_upgrade:
            buildings_needing_upgrade += 1

        # ORaP compliance: no zones above limit (1000 Bq/m3) without mitigation
        orap_compliant = radon_eval.zones_above_limit == 0
        if orap_compliant:
            orap_compliant_count += 1

        # Determine radon priority
        if radon_eval.zones_above_limit > 0:
            radon_priority = "critical"
        elif radon_eval.zones_above_reference > 0:
            radon_priority = "high"
        elif radon_eval.total_zones_measured > 0:
            radon_priority = "low"
        else:
            radon_priority = "none"

        building_cost = radon_eval.total_estimated_cost_chf
        total_cost += building_cost

        building_statuses.append(
            BuildingVentilationStatus(
                building_id=b.id,
                address=b.address,
                needs_ventilation_upgrade=needs_upgrade,
                radon_priority=radon_priority,
                zones_requiring_action=assessment.zones_needing_upgrade,
                estimated_cost_chf=building_cost,
                orap_compliant=orap_compliant,
            )
        )

    # Sort by priority: critical first
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 4}
    building_statuses.sort(key=lambda s: priority_order.get(s.radon_priority, 4))

    orap_rate = orap_compliant_count / len(buildings) if buildings else 1.0

    return PortfolioVentilationStatus(
        organization_id=org_id,
        total_buildings=len(buildings),
        buildings_needing_upgrade=buildings_needing_upgrade,
        radon_mitigation_priority_list=building_statuses,
        total_estimated_cost_chf=total_cost,
        orap_compliance_rate=round(orap_rate, 2),
        generated_at=datetime.now(UTC),
    )
