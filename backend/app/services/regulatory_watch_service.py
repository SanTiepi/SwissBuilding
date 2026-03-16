"""
SwissBuildingOS - Regulatory Watch Service

Monitors active Swiss regulations, assesses their impact on buildings,
simulates threshold changes, and computes portfolio-wide regulatory exposure.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.compliance_engine import SWISS_THRESHOLDS

# ---------------------------------------------------------------------------
# Cost estimation constants (CHF per incident, rough Swiss market rates)
# ---------------------------------------------------------------------------

_REMEDIATION_COST_PER_POLLUTANT: dict[str, float] = {
    "asbestos": 25_000.0,
    "pcb": 18_000.0,
    "lead": 12_000.0,
    "hap": 15_000.0,
    "radon": 8_000.0,
}

_DEFAULT_REMEDIATION_COST = 15_000.0

# ---------------------------------------------------------------------------
# Domain mapping — links pollutant/regulation to a business domain
# ---------------------------------------------------------------------------

_DOMAIN_FOR_POLLUTANT: dict[str, str] = {
    "asbestos": "asbestos",
    "pcb": "pcb",
    "lead": "lead",
    "hap": "hap",
    "radon": "radon",
}

# ---------------------------------------------------------------------------
# Regulation registry — static Swiss-federal regulation catalogue
# ---------------------------------------------------------------------------

_REGULATION_REGISTRY: list[dict] = [
    {
        "regulation_name": "Asbestos material content limit",
        "reference": "OTConst Art.60a",
        "domain": "asbestos",
        "effective_date": date(2005, 1, 1),
        "thresholds": {"material_content": 1.0, "unit": "percent_weight"},
        "enforcement_level": "strict",
        "cantons": None,  # all cantons
    },
    {
        "regulation_name": "Asbestos air fiber count (indoor)",
        "reference": "VLT air interieur",
        "domain": "asbestos",
        "effective_date": date(2005, 1, 1),
        "thresholds": {"air_fiber_count": 1000, "unit": "fibers_per_m3"},
        "enforcement_level": "strict",
        "cantons": None,
    },
    {
        "regulation_name": "Asbestos workplace exposure limit",
        "reference": "CFST 6503",
        "domain": "asbestos",
        "effective_date": date(2005, 1, 1),
        "thresholds": {"air_work_limit": 10000, "unit": "fibers_per_m3"},
        "enforcement_level": "strict",
        "cantons": None,
    },
    {
        "regulation_name": "PCB material content limit",
        "reference": "ORRChim Annexe 2.15",
        "domain": "pcb",
        "effective_date": date(2005, 3, 1),
        "thresholds": {"material_content": 50, "unit": "mg_per_kg"},
        "enforcement_level": "strict",
        "cantons": None,
    },
    {
        "regulation_name": "PCB indoor air recommendation",
        "reference": "Recommandation OFSP",
        "domain": "pcb",
        "effective_date": date(2012, 1, 1),
        "thresholds": {"air_indoor": 6000, "unit": "ng_per_m3"},
        "enforcement_level": "advisory",
        "cantons": None,
    },
    {
        "regulation_name": "Lead paint content limit",
        "reference": "ORRChim Annexe 2.18",
        "domain": "lead",
        "effective_date": date(2005, 3, 1),
        "thresholds": {"paint_content": 5000, "unit": "mg_per_kg"},
        "enforcement_level": "strict",
        "cantons": None,
    },
    {
        "regulation_name": "HAP material content limit",
        "reference": "OLED dechet special",
        "domain": "hap",
        "effective_date": date(2016, 1, 1),
        "thresholds": {"material_content": 200, "unit": "mg_per_kg"},
        "enforcement_level": "moderate",
        "cantons": None,
    },
    {
        "regulation_name": "Radon reference value",
        "reference": "ORaP Art.110",
        "domain": "radon",
        "effective_date": date(2018, 1, 1),
        "thresholds": {"reference_value": 300, "unit": "bq_per_m3"},
        "enforcement_level": "moderate",
        "cantons": None,
    },
    {
        "regulation_name": "Radon mandatory action level",
        "reference": "ORaP Art.110",
        "domain": "radon",
        "effective_date": date(2018, 1, 1),
        "thresholds": {"mandatory_action": 1000, "unit": "bq_per_m3"},
        "enforcement_level": "strict",
        "cantons": None,
    },
]


def _remediation_cost(pollutant: str) -> float:
    return _REMEDIATION_COST_PER_POLLUTANT.get(pollutant.lower(), _DEFAULT_REMEDIATION_COST)


# ---------------------------------------------------------------------------
# FN1: get_active_regulations
# ---------------------------------------------------------------------------


async def get_active_regulations(
    canton: str,
    db: AsyncSession,
) -> list[dict]:
    """Return active regulations applicable to a canton.

    All federal regulations apply to every canton.  Canton-specific regs
    would be filtered via the ``cantons`` list on each registry entry.
    """
    canton_upper = canton.upper()
    results: list[dict] = []

    for reg in _REGULATION_REGISTRY:
        # If cantons is None → applies to all; otherwise filter
        if reg["cantons"] is not None and canton_upper not in reg["cantons"]:
            continue
        results.append(
            {
                "regulation_name": reg["regulation_name"],
                "reference": reg["reference"],
                "domain": reg["domain"],
                "effective_date": reg["effective_date"],
                "thresholds": reg["thresholds"],
                "enforcement_level": reg["enforcement_level"],
            }
        )

    return results


# ---------------------------------------------------------------------------
# FN2: assess_regulatory_impact
# ---------------------------------------------------------------------------


async def assess_regulatory_impact(
    building_id: UUID,
    db: AsyncSession,
) -> dict:
    """Assess the impact of current regulations on a building.

    Loads all samples for the building and checks each against
    SWISS_THRESHOLDS.  Returns applicable regulations, compliance gaps,
    overall exposure level, and estimated compliance cost.
    """
    # Verify building exists
    building_result = await db.execute(select(Building).where(Building.id == building_id))
    building = building_result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    canton = (building.canton or "").upper()

    # Load samples
    stmt = (
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
        .where(Sample.concentration.is_not(None))
        .where(Sample.pollutant_type.is_not(None))
    )
    result = await db.execute(stmt)
    samples = list(result.scalars().all())

    # Group by pollutant → max concentration
    pollutant_max: dict[str, float] = {}
    for s in samples:
        p = s.pollutant_type.lower()
        if p not in pollutant_max or s.concentration > pollutant_max[p]:
            pollutant_max[p] = s.concentration

    # Get active regulations for this canton
    active_regs = await get_active_regulations(canton, db)

    applicable_regulations: list[str] = []
    compliance_gaps: list[dict] = []
    total_cost = 0.0

    seen_regs: set[str] = set()
    for reg in active_regs:
        domain = reg["domain"]
        if domain not in pollutant_max:
            continue
        reg_ref = reg["reference"]
        if reg_ref not in seen_regs:
            seen_regs.add(reg_ref)
            applicable_regulations.append(reg_ref)

        # Check each threshold key in the regulation
        for _threshold_key, threshold_value in reg["thresholds"].items():
            if _threshold_key == "unit":
                continue
            max_conc = pollutant_max[domain]
            if max_conc >= threshold_value:
                compliance_gaps.append(
                    {
                        "regulation": reg_ref,
                        "gap_description": (
                            f"{domain} concentration {max_conc} exceeds "
                            f"threshold {threshold_value} ({reg['regulation_name']})"
                        ),
                        "remediation_required": reg["enforcement_level"] == "strict",
                    }
                )
                total_cost += _remediation_cost(domain)

    # Overall exposure
    gap_count = len(compliance_gaps)
    if gap_count == 0:
        overall_exposure = "low"
    elif gap_count <= 2:
        overall_exposure = "medium"
    else:
        overall_exposure = "high"

    return {
        "building_id": building_id,
        "applicable_regulations": applicable_regulations,
        "compliance_gaps": compliance_gaps,
        "overall_exposure": overall_exposure,
        "estimated_compliance_cost": round(total_cost, 2),
    }


# ---------------------------------------------------------------------------
# FN3: simulate_threshold_change
# ---------------------------------------------------------------------------


async def simulate_threshold_change(
    building_id: UUID,
    pollutant_type: str,
    new_threshold: float,
    db: AsyncSession,
) -> dict:
    """What-if analysis: simulate changing a threshold for a pollutant.

    For the given building, checks current compliance status vs. a
    hypothetical new threshold and reports affected samples.
    """
    # Verify building exists
    building_result = await db.execute(select(Building).where(Building.id == building_id))
    building = building_result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    pollutant_lower = pollutant_type.lower()

    # Load samples for this building + pollutant
    stmt = (
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
        .where(Sample.pollutant_type == pollutant_lower)
        .where(Sample.concentration.is_not(None))
    )
    result = await db.execute(stmt)
    samples = list(result.scalars().all())

    # Determine current threshold (first match from SWISS_THRESHOLDS)
    entries = SWISS_THRESHOLDS.get(pollutant_lower, {})
    current_threshold: float | None = None
    for _mtype, entry in entries.items():
        current_threshold = entry["threshold"]
        break  # use first measurement type as primary

    if current_threshold is None:
        current_threshold = 0.0

    # Evaluate compliance
    currently_compliant = all(s.concentration < current_threshold for s in samples) if samples else True
    would_be_compliant = all(s.concentration < new_threshold for s in samples) if samples else True

    affected_samples: list[dict] = []
    for s in samples:
        # Sample is "affected" if it crosses the new threshold differently
        exceeds_current = s.concentration >= current_threshold
        exceeds_new = s.concentration >= new_threshold
        if exceeds_current != exceeds_new or exceeds_new:
            affected_samples.append(
                {
                    "sample_id": s.id,
                    "current_value": s.concentration,
                    "new_threshold": new_threshold,
                }
            )

    additional_remediation_needed = currently_compliant and not would_be_compliant
    cost_delta = (
        _remediation_cost(pollutant_lower) * len([s for s in affected_samples if s["current_value"] >= new_threshold])
        if not would_be_compliant
        else 0.0
    )

    return {
        "building_id": building_id,
        "pollutant_type": pollutant_lower,
        "currently_compliant": currently_compliant,
        "would_be_compliant": would_be_compliant,
        "affected_samples": affected_samples,
        "additional_remediation_needed": additional_remediation_needed,
        "cost_delta": round(cost_delta, 2),
    }


# ---------------------------------------------------------------------------
# FN4: get_portfolio_regulatory_exposure
# ---------------------------------------------------------------------------


async def get_portfolio_regulatory_exposure(
    org_id: UUID,
    db: AsyncSession,
) -> dict:
    """Compute org-wide regulatory exposure.

    Iterates over all buildings belonging to users in the organization,
    computes compliance gaps, and aggregates results.
    """
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    regulations_tracked = len(_REGULATION_REGISTRY)
    buildings_with_gaps = 0
    total_cost = 0.0
    domain_stats: dict[str, dict] = {}  # domain -> {buildings_affected, total_cost}
    most_impacted: list[dict] = []

    for building in buildings:
        try:
            impact = await assess_regulatory_impact(building.id, db)
        except ValueError:
            continue

        gap_count = len(impact["compliance_gaps"])
        building_cost = impact["estimated_compliance_cost"]

        if gap_count > 0:
            buildings_with_gaps += 1
            total_cost += building_cost
            most_impacted.append(
                {
                    "building_id": building.id,
                    "address": building.address,
                    "canton": building.canton,
                    "gap_count": gap_count,
                    "estimated_cost": building_cost,
                }
            )

            # Track domain stats from gaps
            seen_domains: set[str] = set()
            for gap in impact["compliance_gaps"]:
                # Extract domain from gap_description
                desc = gap["gap_description"]
                for domain in _DOMAIN_FOR_POLLUTANT.values():
                    if domain in desc.lower():
                        if domain not in seen_domains:
                            seen_domains.add(domain)
                            if domain not in domain_stats:
                                domain_stats[domain] = {"buildings_affected": 0, "total_cost": 0.0}
                            domain_stats[domain]["buildings_affected"] += 1
                        domain_stats[domain]["total_cost"] += _remediation_cost(domain)

    # Sort most impacted by gap_count desc
    most_impacted.sort(key=lambda b: b["gap_count"], reverse=True)

    exposure_by_domain = [
        {
            "domain": domain,
            "buildings_affected": stats["buildings_affected"],
            "total_cost": round(stats["total_cost"], 2),
        }
        for domain, stats in sorted(domain_stats.items())
    ]

    return {
        "org_id": org_id,
        "regulations_tracked": regulations_tracked,
        "buildings_with_gaps": buildings_with_gaps,
        "total_compliance_cost": round(total_cost, 2),
        "exposure_by_domain": exposure_by_domain,
        "most_impacted_buildings": most_impacted,
    }
