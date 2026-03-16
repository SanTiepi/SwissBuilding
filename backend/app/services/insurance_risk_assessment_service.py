"""
SwissBuildingOS - Insurance Risk Assessment Service

Evaluates insurance risk for buildings containing pollutants,
based on Swiss regulatory thresholds and construction history.

Business rules:
- Asbestos friable → uninsurable without removal plan
- PCB > 50 mg/kg → elevated minimum
- Radon > 1000 Bq/m³ → high risk
- Multiple pollutants → cumulative multiplier
- Pre-1991 building without diagnostic → elevated by default
- Post-remediation verified → return to standard tier
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.insurance_risk_assessment import (
    CoverageRestriction,
    InsuranceCompareResponse,
    InsuranceProfileComparison,
    InsuranceRiskAssessment,
    InsuranceRiskTier,
    LiabilityCategory,
    LiabilityExposure,
    PortfolioInsuranceSummary,
    RequiredMitigation,
    TierDistribution,
)

# ---------------------------------------------------------------------------
# Tier ordering for comparisons
# ---------------------------------------------------------------------------
_TIER_ORDER = {
    InsuranceRiskTier.standard: 0,
    InsuranceRiskTier.elevated: 1,
    InsuranceRiskTier.high: 2,
    InsuranceRiskTier.uninsurable: 3,
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _load_building_with_samples(
    db: AsyncSession, building_id: UUID
) -> tuple[Building | None, list[Sample], bool]:
    """Load building, its samples (via diagnostics), and whether remediation is done."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None, [], False

    # Load all samples from all diagnostics for this building
    stmt = (
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id)
    )
    samples_result = await db.execute(stmt)
    samples = list(samples_result.scalars().all())

    # Check for completed remediation interventions
    intervention_result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building_id,
            Intervention.intervention_type == "remediation",
            Intervention.status == "completed",
        )
    )
    has_remediation = intervention_result.scalars().first() is not None

    return building, samples, has_remediation


def _classify_pollutant_flags(samples: list[Sample]) -> dict[str, str]:
    """Build a dict of pollutant_type -> worst risk_level from samples."""
    flags: dict[str, str] = {}
    risk_order = {"unknown": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    for s in samples:
        if not s.pollutant_type:
            continue
        current = flags.get(s.pollutant_type)
        sample_risk = s.risk_level or "unknown"
        if current is None or risk_order.get(sample_risk, 0) > risk_order.get(current, 0):
            flags[s.pollutant_type] = sample_risk
    return flags


def _has_friable_asbestos(samples: list[Sample]) -> bool:
    """Check if any asbestos sample is friable."""
    return any(s.pollutant_type == "asbestos" and s.material_state == "friable" for s in samples)


def _has_high_pcb(samples: list[Sample]) -> bool:
    """Check if any PCB sample exceeds 50 mg/kg."""
    return any(s.pollutant_type == "pcb" and s.concentration is not None and s.concentration > 50 for s in samples)


def _has_high_radon(samples: list[Sample]) -> bool:
    """Check if any radon sample exceeds 1000 Bq/m³."""
    return any(s.pollutant_type == "radon" and s.concentration is not None and s.concentration > 1000 for s in samples)


def _count_pollutants_with_issues(samples: list[Sample]) -> int:
    """Count distinct pollutant types that have threshold exceeded or high/critical risk."""
    pollutants: set[str] = set()
    for s in samples:
        if not s.pollutant_type:
            continue
        if s.threshold_exceeded or s.risk_level in ("high", "critical"):
            pollutants.add(s.pollutant_type)
    return len(pollutants)


def _compute_tier_and_multiplier(
    building: Building,
    samples: list[Sample],
    has_remediation: bool,
    pollutant_flags: dict[str, str],
) -> tuple[InsuranceRiskTier, float]:
    """Determine risk tier and premium multiplier."""
    # Post-remediation verified → standard
    if has_remediation and not any(r in ("high", "critical") for r in pollutant_flags.values()):
        return InsuranceRiskTier.standard, 1.0

    # Uninsurable: friable asbestos without remediation
    if _has_friable_asbestos(samples) and not has_remediation:
        return InsuranceRiskTier.uninsurable, 3.0

    tier = InsuranceRiskTier.standard
    multiplier = 1.0

    # Pre-1991 without diagnostic → elevated by default
    has_diagnostic = len(samples) > 0
    if building.construction_year and building.construction_year < 1991 and not has_diagnostic:
        tier = InsuranceRiskTier.elevated
        multiplier = 1.5

    # PCB > 50 mg/kg → elevated minimum
    if _has_high_pcb(samples):
        if _TIER_ORDER.get(tier, 0) < _TIER_ORDER[InsuranceRiskTier.elevated]:
            tier = InsuranceRiskTier.elevated
        multiplier = max(multiplier, 1.8)

    # Radon > 1000 Bq/m³ → high risk
    if _has_high_radon(samples):
        if _TIER_ORDER.get(tier, 0) < _TIER_ORDER[InsuranceRiskTier.high]:
            tier = InsuranceRiskTier.high
        multiplier = max(multiplier, 2.2)

    # Multiple pollutants → cumulative multiplier
    problem_count = _count_pollutants_with_issues(samples)
    if problem_count >= 3:
        if _TIER_ORDER.get(tier, 0) < _TIER_ORDER[InsuranceRiskTier.high]:
            tier = InsuranceRiskTier.high
        multiplier = max(multiplier, 2.5)
    elif problem_count == 2:
        if _TIER_ORDER.get(tier, 0) < _TIER_ORDER[InsuranceRiskTier.elevated]:
            tier = InsuranceRiskTier.elevated
        multiplier = max(multiplier, 1.6)

    # High/critical individual pollutant findings
    for _pollutant, risk in pollutant_flags.items():
        if risk == "critical":
            if _TIER_ORDER.get(tier, 0) < _TIER_ORDER[InsuranceRiskTier.high]:
                tier = InsuranceRiskTier.high
            multiplier = max(multiplier, 2.3)
        elif risk == "high":
            if _TIER_ORDER.get(tier, 0) < _TIER_ORDER[InsuranceRiskTier.elevated]:
                tier = InsuranceRiskTier.elevated
            multiplier = max(multiplier, 1.7)

    # Cap multiplier
    multiplier = min(multiplier, 3.0)

    return tier, round(multiplier, 2)


def _build_coverage_restrictions(samples: list[Sample], tier: InsuranceRiskTier) -> list[CoverageRestriction]:
    """Generate coverage restrictions based on findings."""
    restrictions: list[CoverageRestriction] = []

    if tier == InsuranceRiskTier.uninsurable:
        restrictions.append(
            CoverageRestriction(
                restriction_type="coverage_denied",
                description="Coverage denied until friable asbestos remediation plan is approved and executed",
                pollutant="asbestos",
            )
        )

    if _has_high_pcb(samples):
        restrictions.append(
            CoverageRestriction(
                restriction_type="exclusion",
                description="Environmental contamination from PCB excluded until decontamination",
                pollutant="pcb",
            )
        )

    if _has_high_radon(samples):
        restrictions.append(
            CoverageRestriction(
                restriction_type="sublimit",
                description="Occupant health claims sublimited to CHF 500,000 pending radon mitigation",
                pollutant="radon",
            )
        )

    if _has_friable_asbestos(samples):
        restrictions.append(
            CoverageRestriction(
                restriction_type="exclusion",
                description="Worker exposure claims excluded for asbestos-related work",
                pollutant="asbestos",
            )
        )

    return restrictions


def _build_required_mitigations(
    samples: list[Sample],
    tier: InsuranceRiskTier,
    has_remediation: bool,
) -> list[RequiredMitigation]:
    """Generate required mitigations before coverage."""
    mitigations: list[RequiredMitigation] = []

    if _has_friable_asbestos(samples) and not has_remediation:
        mitigations.append(
            RequiredMitigation(
                action="Submit and execute friable asbestos removal plan (SUVA-compliant)",
                priority="immediate",
                pollutant="asbestos",
                estimated_cost_chf=50000.0,
            )
        )

    if _has_high_pcb(samples):
        mitigations.append(
            RequiredMitigation(
                action="PCB decontamination per ORRChim Annexe 2.15",
                priority="short_term",
                pollutant="pcb",
                estimated_cost_chf=30000.0,
            )
        )

    if _has_high_radon(samples):
        mitigations.append(
            RequiredMitigation(
                action="Radon mitigation system installation per ORaP Art. 110",
                priority="short_term",
                pollutant="radon",
                estimated_cost_chf=15000.0,
            )
        )

    # If no diagnostic for pre-1991 building
    if not samples and tier in (InsuranceRiskTier.elevated, InsuranceRiskTier.high):
        mitigations.append(
            RequiredMitigation(
                action="Complete pollutant diagnostic assessment",
                priority="immediate",
                pollutant=None,
                estimated_cost_chf=5000.0,
            )
        )

    return mitigations


def _build_summary(tier: InsuranceRiskTier, pollutant_flags: dict[str, str], has_diagnostic: bool) -> str:
    """Build a human-readable summary."""
    if tier == InsuranceRiskTier.uninsurable:
        return "Building is currently uninsurable due to friable asbestos. Remediation required before coverage."
    if tier == InsuranceRiskTier.high:
        pollutants = ", ".join(pollutant_flags.keys()) if pollutant_flags else "unknown pollutants"
        return (
            f"High insurance risk due to {pollutants}. Significant premium surcharge and coverage restrictions apply."
        )
    if tier == InsuranceRiskTier.elevated:
        if not has_diagnostic:
            return "Elevated risk: pre-1991 building without pollutant diagnostic. Assessment recommended."
        return "Elevated insurance risk. Moderate premium surcharge applies with some coverage restrictions."
    return "Standard insurance risk tier. No significant pollutant-related concerns."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def assess_building_insurance_risk(db: AsyncSession, building_id: UUID) -> InsuranceRiskAssessment:
    """Complete insurance risk assessment for a building."""
    building, samples, has_remediation = await _load_building_with_samples(db, building_id)
    if not building:
        raise ValueError(f"Building {building_id} not found")

    pollutant_flags = _classify_pollutant_flags(samples)
    tier, multiplier = _compute_tier_and_multiplier(building, samples, has_remediation, pollutant_flags)
    restrictions = _build_coverage_restrictions(samples, tier)
    mitigations = _build_required_mitigations(samples, tier, has_remediation)
    has_diagnostic = len(samples) > 0
    summary = _build_summary(tier, pollutant_flags, has_diagnostic)

    return InsuranceRiskAssessment(
        building_id=building_id,
        risk_tier=tier,
        premium_impact_multiplier=multiplier,
        pollutant_flags=pollutant_flags,
        coverage_restrictions=restrictions,
        required_mitigations=mitigations,
        has_diagnostic=has_diagnostic,
        building_year=building.construction_year,
        summary=summary,
    )


async def get_liability_exposure(db: AsyncSession, building_id: UUID) -> LiabilityExposure:
    """Analyze liability exposure across 4 categories."""
    building, samples, has_remediation = await _load_building_with_samples(db, building_id)
    if not building:
        raise ValueError(f"Building {building_id} not found")

    pollutant_flags = _classify_pollutant_flags(samples)
    categories: list[LiabilityCategory] = []

    # 1. Occupant health liability
    occupant_score = 0.0
    occupant_pollutants: list[str] = []
    occupant_justification_parts: list[str] = []

    if _has_friable_asbestos(samples):
        occupant_score = max(occupant_score, 0.95)
        occupant_pollutants.append("asbestos")
        occupant_justification_parts.append("Friable asbestos poses immediate inhalation risk to occupants")
    if _has_high_radon(samples):
        occupant_score = max(occupant_score, 0.8)
        occupant_pollutants.append("radon")
        occupant_justification_parts.append("Radon > 1000 Bq/m³ — chronic lung cancer risk")
    if "lead" in pollutant_flags and pollutant_flags["lead"] in ("high", "critical"):
        occupant_score = max(occupant_score, 0.6)
        occupant_pollutants.append("lead")
        occupant_justification_parts.append("Lead paint exposure risk, especially for children")

    if not occupant_justification_parts:
        occupant_justification_parts.append("No significant occupant health risks identified")
        occupant_score = 0.1 if not samples else 0.05

    categories.append(
        LiabilityCategory(
            category="occupant_health",
            score=round(occupant_score, 2),
            justification=". ".join(occupant_justification_parts),
            contributing_pollutants=occupant_pollutants,
        )
    )

    # 2. Worker safety liability
    worker_score = 0.0
    worker_pollutants: list[str] = []
    worker_justification_parts: list[str] = []

    for s in samples:
        if s.pollutant_type == "asbestos" and s.risk_level in ("high", "critical"):
            worker_score = max(worker_score, 0.9)
            if "asbestos" not in worker_pollutants:
                worker_pollutants.append("asbestos")
                worker_justification_parts.append(
                    "Asbestos exposure during renovation — CFST 6503 major works category"
                )
        if s.pollutant_type == "pcb" and s.threshold_exceeded:
            worker_score = max(worker_score, 0.7)
            if "pcb" not in worker_pollutants:
                worker_pollutants.append("pcb")
                worker_justification_parts.append("PCB joint sealant handling requires specialized protection")
        if s.pollutant_type == "hap" and s.risk_level in ("high", "critical"):
            worker_score = max(worker_score, 0.6)
            if "hap" not in worker_pollutants:
                worker_pollutants.append("hap")
                worker_justification_parts.append("HAP in flooring — dermal/inhalation exposure during removal")

    if not worker_justification_parts:
        worker_justification_parts.append("No significant worker safety risks identified")
        worker_score = 0.1 if not samples else 0.05

    categories.append(
        LiabilityCategory(
            category="worker_safety",
            score=round(worker_score, 2),
            justification=". ".join(worker_justification_parts),
            contributing_pollutants=worker_pollutants,
        )
    )

    # 3. Environmental contamination liability
    env_score = 0.0
    env_pollutants: list[str] = []
    env_justification_parts: list[str] = []

    if _has_high_pcb(samples):
        env_score = max(env_score, 0.85)
        env_pollutants.append("pcb")
        env_justification_parts.append("PCB contamination risk to soil and water during demolition/renovation")
    if "lead" in pollutant_flags and pollutant_flags["lead"] in ("high", "critical"):
        env_score = max(env_score, 0.5)
        env_pollutants.append("lead")
        env_justification_parts.append("Lead paint debris may contaminate surrounding soil")
    if "hap" in pollutant_flags and pollutant_flags["hap"] in ("high", "critical"):
        env_score = max(env_score, 0.5)
        env_pollutants.append("hap")
        env_justification_parts.append("HAP materials require controlled waste disposal per OLED")

    if not env_justification_parts:
        env_justification_parts.append("No significant environmental contamination risks identified")
        env_score = 0.1 if not samples else 0.05

    categories.append(
        LiabilityCategory(
            category="environmental_contamination",
            score=round(env_score, 2),
            justification=". ".join(env_justification_parts),
            contributing_pollutants=env_pollutants,
        )
    )

    # 4. Remediation cost liability
    remediation_score = 0.0
    remediation_pollutants: list[str] = []
    remediation_justification_parts: list[str] = []

    problem_count = _count_pollutants_with_issues(samples)
    if problem_count >= 3:
        remediation_score = 0.9
        remediation_justification_parts.append(
            f"{problem_count} pollutants requiring remediation — significant cumulative cost"
        )
    elif problem_count == 2:
        remediation_score = 0.65
        remediation_justification_parts.append("Two pollutants requiring remediation")
    elif problem_count == 1:
        remediation_score = 0.4
        remediation_justification_parts.append("Single pollutant requiring remediation")

    for s in samples:
        if (
            s.pollutant_type
            and (s.threshold_exceeded or s.risk_level in ("high", "critical"))
            and s.pollutant_type not in remediation_pollutants
        ):
            remediation_pollutants.append(s.pollutant_type)

    if not remediation_justification_parts:
        remediation_justification_parts.append("No significant remediation costs anticipated")
        remediation_score = 0.1 if not samples else 0.05

    if has_remediation:
        remediation_score = max(remediation_score * 0.3, 0.05)
        remediation_justification_parts.append("Post-remediation: residual cost liability reduced")

    categories.append(
        LiabilityCategory(
            category="remediation_cost",
            score=round(remediation_score, 2),
            justification=". ".join(remediation_justification_parts),
            contributing_pollutants=remediation_pollutants,
        )
    )

    # Overall
    scores = [c.score for c in categories]
    overall = round(max(scores) * 0.6 + (sum(scores) / len(scores)) * 0.4, 2) if scores else 0.0
    highest = max(categories, key=lambda c: c.score)

    summary_parts = [f"Overall liability score: {overall:.2f}/1.00"]
    if overall > 0.7:
        summary_parts.append("Significant liability exposure requiring immediate attention")
    elif overall > 0.4:
        summary_parts.append("Moderate liability exposure with specific risk areas")
    else:
        summary_parts.append("Low liability exposure")

    return LiabilityExposure(
        building_id=building_id,
        overall_liability_score=overall,
        categories=categories,
        highest_risk_category=highest.category,
        summary=". ".join(summary_parts),
    )


async def compare_insurance_profiles(db: AsyncSession, building_ids: list[UUID]) -> InsuranceCompareResponse:
    """Compare insurance profiles across multiple buildings."""
    profiles: list[InsuranceProfileComparison] = []

    for bid in building_ids:
        building, samples, has_remediation = await _load_building_with_samples(db, bid)
        if not building:
            continue

        pollutant_flags = _classify_pollutant_flags(samples)
        tier, multiplier = _compute_tier_and_multiplier(building, samples, has_remediation, pollutant_flags)

        # Find worst pollutant
        worst_pollutant: str | None = None
        risk_order = {"unknown": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        max_risk = -1
        for p, r in pollutant_flags.items():
            if risk_order.get(r, 0) > max_risk:
                max_risk = risk_order.get(r, 0)
                worst_pollutant = p

        # Recommended actions
        actions: list[str] = []
        if tier == InsuranceRiskTier.uninsurable:
            actions.append("Execute friable asbestos remediation plan immediately")
        if _has_high_pcb(samples):
            actions.append("Schedule PCB decontamination")
        if _has_high_radon(samples):
            actions.append("Install radon mitigation system")
        if not samples and building.construction_year and building.construction_year < 1991:
            actions.append("Conduct pollutant diagnostic assessment")
        if not actions:
            actions.append("Maintain current monitoring program")

        profiles.append(
            InsuranceProfileComparison(
                building_id=bid,
                address=building.address,
                risk_tier=tier,
                premium_impact_multiplier=multiplier,
                worst_pollutant=worst_pollutant,
                recommended_actions=actions,
            )
        )

    if not profiles:
        return InsuranceCompareResponse(
            profiles=[],
            best_tier=InsuranceRiskTier.standard,
            worst_tier=InsuranceRiskTier.standard,
        )

    best = min(profiles, key=lambda p: _TIER_ORDER[p.risk_tier])
    worst = max(profiles, key=lambda p: _TIER_ORDER[p.risk_tier])

    return InsuranceCompareResponse(
        profiles=profiles,
        best_tier=best.risk_tier,
        worst_tier=worst.risk_tier,
    )


async def get_portfolio_insurance_summary(db: AsyncSession, org_id: UUID) -> PortfolioInsuranceSummary:
    """Portfolio-level insurance summary for an organization."""
    from app.services.building_data_loader import load_org_buildings

    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioInsuranceSummary(
            organization_id=org_id,
            total_buildings=0,
            assessed_buildings=0,
            tier_distribution=TierDistribution(),
            average_premium_multiplier=1.0,
            total_premium_impact=0.0,
            buildings_requiring_immediate_action=0,
            trend_indicator="stable",
            summary="No buildings found for this organization.",
        )

    distribution = TierDistribution()
    multipliers: list[float] = []
    immediate_action_count = 0
    assessed = 0
    remediated_count = 0

    for building in buildings:
        _, samples, has_remediation = await _load_building_with_samples(db, building.id)
        pollutant_flags = _classify_pollutant_flags(samples)
        tier, multiplier = _compute_tier_and_multiplier(building, samples, has_remediation, pollutant_flags)

        if tier == InsuranceRiskTier.standard:
            distribution.standard += 1
        elif tier == InsuranceRiskTier.elevated:
            distribution.elevated += 1
        elif tier == InsuranceRiskTier.high:
            distribution.high += 1
        elif tier == InsuranceRiskTier.uninsurable:
            distribution.uninsurable += 1

        multipliers.append(multiplier)

        if tier in (InsuranceRiskTier.high, InsuranceRiskTier.uninsurable):
            immediate_action_count += 1

        if samples:
            assessed += 1

        if has_remediation:
            remediated_count += 1

    total = len(buildings)
    avg_multiplier = round(sum(multipliers) / len(multipliers), 2) if multipliers else 1.0
    total_impact = round(sum(m - 1.0 for m in multipliers), 2)

    # Trend indicator based on remediation vs problems
    problem_count = distribution.high + distribution.uninsurable
    if remediated_count > 0 and problem_count == 0:
        trend = "improving"
    elif problem_count > total * 0.3:
        trend = "worsening"
    else:
        trend = "stable"

    summary_parts = [f"{total} buildings in portfolio"]
    if distribution.uninsurable > 0:
        summary_parts.append(f"{distribution.uninsurable} uninsurable")
    if distribution.high > 0:
        summary_parts.append(f"{distribution.high} high risk")
    summary_parts.append(f"average premium multiplier: {avg_multiplier}x")

    return PortfolioInsuranceSummary(
        organization_id=org_id,
        total_buildings=total,
        assessed_buildings=assessed,
        tier_distribution=distribution,
        average_premium_multiplier=avg_multiplier,
        total_premium_impact=total_impact,
        buildings_requiring_immediate_action=immediate_action_count,
        trend_indicator=trend,
        summary=". ".join(summary_parts),
    )
