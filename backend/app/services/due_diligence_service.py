"""
SwissBuildingOS - Due Diligence Service

Generates buyer/investor due diligence reports for buildings with pollutant
exposure.  Covers risk assessment, remediation cost estimation, property value
impact, compliance state, and side-by-side acquisition comparison.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.due_diligence import (
    AcquisitionCompareResponse,
    AcquisitionTarget,
    ComplianceState,
    DueDiligenceRecommendation,
    DueDiligenceReport,
    PollutantDepreciation,
    PollutantStatus,
    PropertyValueImpact,
    PropertyValueImpactSummary,
    RemediationCostSummary,
    RiskFlag,
    RiskImpact,
    RiskProbability,
    TransactionRisk,
    TransactionRiskAssessment,
)
from app.services.compliance_engine import get_cantonal_requirements

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

POLLUTANT_DEPRECIATION_PCT: dict[str, float] = {
    "asbestos": 8.0,
    "pcb": 5.0,
    "radon": 3.0,
    "lead": 4.0,
    "hap": 2.0,
}

CUMULATIVE_CAP_PCT = 25.0

# Rough remediation CHF/m² rates (simplified, reused from remediation_cost_service)
_REMEDIATION_RATES: dict[str, float] = {
    "asbestos": 120.0,
    "pcb": 150.0,
    "lead": 80.0,
    "hap": 100.0,
    "radon": 15.0,
}

_RADON_FIXED = 5000.0
_POST_REMEDIATION_RECOVERY_FRACTION = 0.60  # recover 60% of depreciation after works


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


async def _fetch_diagnostics(db: AsyncSession, building_id: UUID) -> list[Diagnostic]:
    stmt = select(Diagnostic).where(Diagnostic.building_id == building_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _fetch_samples(db: AsyncSession, building_id: UUID) -> list[Sample]:
    stmt = (
        select(Sample)
        .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
        .where(Diagnostic.building_id == building_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _group_samples_by_pollutant(samples: list[Sample]) -> dict[str, list[Sample]]:
    grouped: dict[str, list[Sample]] = {}
    for s in samples:
        pt = (s.pollutant_type or "").lower()
        if pt:
            grouped.setdefault(pt, []).append(s)
    return grouped


def _pollutant_statuses(grouped: dict[str, list[Sample]]) -> list[PollutantStatus]:
    statuses: list[PollutantStatus] = []
    for pollutant in POLLUTANT_DEPRECIATION_PCT:
        samples = grouped.get(pollutant, [])
        exceeded = any(s.threshold_exceeded for s in samples)
        worst_risk = "unknown"
        if samples:
            risk_priority = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            worst = max(samples, key=lambda s: risk_priority.get(s.risk_level or "low", 0))
            worst_risk = worst.risk_level or "low"
        statuses.append(
            PollutantStatus(
                pollutant=pollutant,
                detected=len(samples) > 0,
                risk_level=worst_risk if samples else "unknown",
                sample_count=len(samples),
                threshold_exceeded=exceeded,
            )
        )
    return statuses


def _compliance_state(
    building: Building,
    diagnostics: list[Diagnostic],
    samples: list[Sample],
) -> ComplianceState:
    canton = (building.canton or "VD").upper()
    cantonal_reqs = get_cantonal_requirements(canton)
    year = building.construction_year
    diag_required = year is not None and year < cantonal_reqs.get("diagnostic_required_before_year", 1991)
    diag_completed = any(d.status in ("completed", "validated") for d in diagnostics)
    suva_required = any(s.pollutant_type == "asbestos" and s.threshold_exceeded for s in samples)

    return ComplianceState(
        diagnostic_required=diag_required,
        diagnostic_completed=diag_completed,
        waste_plan_required=cantonal_reqs.get("requires_waste_elimination_plan", True),
        suva_notification_required=suva_required,
        canton=canton,
        authority_name=cantonal_reqs.get("authority_name", ""),
    )


def _remediation_cost_summary(
    building: Building,
    grouped: dict[str, list[Sample]],
) -> RemediationCostSummary:
    surface = building.surface_area_m2 or 0.0
    total = 0.0
    driver: str | None = None
    driver_cost = 0.0

    for pollutant, samples in grouped.items():
        if not any(s.threshold_exceeded for s in samples):
            continue
        rate = _REMEDIATION_RATES.get(pollutant, 100.0)
        if pollutant == "radon":
            cost = _RADON_FIXED + rate * surface
        else:
            cost = rate * surface
        if cost > driver_cost:
            driver_cost = cost
            driver = pollutant
        total += cost

    total_min = total * 0.7
    total_max = total * 1.3

    return RemediationCostSummary(
        total_min_chf=round(total_min, 2),
        total_max_chf=round(total_max, 2),
        pollutant_count=len(grouped),
        primary_cost_driver=driver,
    )


def _risk_flags(
    building: Building,
    diagnostics: list[Diagnostic],
    samples: list[Sample],
    compliance: ComplianceState,
) -> list[RiskFlag]:
    flags: list[RiskFlag] = []

    # No diagnostic on pre-1991 building
    if compliance.diagnostic_required and not compliance.diagnostic_completed:
        flags.append(
            RiskFlag(
                flag="missing_diagnostic",
                severity="high",
                description="Pre-1991 building without completed pollutant diagnostic",
            )
        )

    # Critical pollutants detected
    for s in samples:
        if s.risk_level == "critical":
            flags.append(
                RiskFlag(
                    flag=f"critical_{s.pollutant_type}",
                    severity="critical",
                    description=f"Critical {s.pollutant_type} level detected",
                )
            )
            break  # one flag is enough

    # Multiple pollutants
    pollutants_found = {s.pollutant_type for s in samples if s.threshold_exceeded}
    if len(pollutants_found) >= 3:
        flags.append(
            RiskFlag(
                flag="multi_pollutant",
                severity="high",
                description=f"{len(pollutants_found)} pollutants exceed thresholds",
            )
        )

    # SUVA notification pending
    if compliance.suva_notification_required:
        flags.append(
            RiskFlag(
                flag="suva_notification",
                severity="medium",
                description="SUVA notification required due to asbestos findings",
            )
        )

    # Old building without renovation
    year = building.construction_year
    if year is not None and year < 1960 and building.renovation_year is None:
        flags.append(
            RiskFlag(
                flag="unrenovated_old_building",
                severity="medium",
                description="Pre-1960 building with no recorded renovation",
            )
        )

    return flags


def _compute_depreciations(
    grouped: dict[str, list[Sample]],
) -> tuple[list[PollutantDepreciation], float, float]:
    depreciations: list[PollutantDepreciation] = []
    raw_total = 0.0

    for pollutant, base_pct in POLLUTANT_DEPRECIATION_PCT.items():
        samples = grouped.get(pollutant, [])
        detected = any(s.threshold_exceeded for s in samples)
        applied = base_pct if detected else 0.0
        raw_total += applied
        depreciations.append(
            PollutantDepreciation(
                pollutant=pollutant,
                detected=detected,
                base_depreciation_pct=base_pct,
                applied_depreciation_pct=applied,
            )
        )

    capped = min(raw_total, CUMULATIVE_CAP_PCT)
    recovery = round(capped * _POST_REMEDIATION_RECOVERY_FRACTION, 2)
    return depreciations, capped, recovery


def _recommendation(
    risk_flags: list[RiskFlag],
    capped_depreciation: float,
    compliance: ComplianceState,
) -> tuple[DueDiligenceRecommendation, str]:
    critical_count = sum(1 for f in risk_flags if f.severity == "critical")
    high_count = sum(1 for f in risk_flags if f.severity == "high")

    if critical_count >= 2 or capped_depreciation >= 20.0:
        return DueDiligenceRecommendation.avoid, (
            "Multiple critical risk factors and/or severe value depreciation. "
            "Transaction not recommended without major risk mitigation."
        )
    if critical_count >= 1 or capped_depreciation >= 15.0:
        return DueDiligenceRecommendation.defer, (
            "Significant pollutant risks identified. Defer acquisition until "
            "remediation is completed or costs are fully negotiated."
        )
    if high_count >= 1 or capped_depreciation >= 5.0:
        return DueDiligenceRecommendation.proceed_with_conditions, (
            "Pollutant risks present but manageable. Proceed with price "
            "adjustment reflecting remediation costs and depreciation."
        )
    return DueDiligenceRecommendation.proceed, (
        "No significant pollutant risks identified. Building is suitable for acquisition."
    )


# ---------------------------------------------------------------------------
# Public API — FN1: generate_due_diligence_report
# ---------------------------------------------------------------------------


async def generate_due_diligence_report(
    db: AsyncSession,
    building_id: UUID,
) -> DueDiligenceReport:
    """
    Generate a comprehensive buyer/investor due diligence report for a building.
    """
    building = await _fetch_building(db, building_id)
    diagnostics = await _fetch_diagnostics(db, building_id)
    samples = await _fetch_samples(db, building_id)
    grouped = _group_samples_by_pollutant(samples)

    statuses = _pollutant_statuses(grouped)
    compliance = _compliance_state(building, diagnostics, samples)
    cost_summary = _remediation_cost_summary(building, grouped)
    flags = _risk_flags(building, diagnostics, samples, compliance)
    _depreciations, capped_dep, recovery = _compute_depreciations(grouped)
    net_impact = round(capped_dep - recovery, 2)
    rec, rationale = _recommendation(flags, capped_dep, compliance)

    return DueDiligenceReport(
        building_id=building.id,
        address=building.address,
        city=building.city,
        canton=building.canton,
        construction_year=building.construction_year,
        building_type=building.building_type,
        surface_area_m2=building.surface_area_m2,
        pollutant_statuses=statuses,
        compliance_state=compliance,
        remediation_cost=cost_summary,
        risk_flags=flags,
        value_impact=PropertyValueImpactSummary(
            total_depreciation_pct=capped_dep,
            post_remediation_recovery_pct=recovery,
            net_impact_pct=net_impact,
        ),
        recommendation=rec,
        recommendation_rationale=rationale,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Public API — FN2: assess_transaction_risks
# ---------------------------------------------------------------------------


def _probability_from_count(count: int, threshold: int) -> RiskProbability:
    if count >= threshold * 2:
        return RiskProbability.very_high
    if count >= threshold:
        return RiskProbability.high
    if count >= 1:
        return RiskProbability.medium
    return RiskProbability.low


def _impact_from_severity(severity_flags: list[str]) -> RiskImpact:
    if "critical" in severity_flags:
        return RiskImpact.severe
    if "high" in severity_flags:
        return RiskImpact.significant
    if "medium" in severity_flags:
        return RiskImpact.moderate
    return RiskImpact.negligible


_RISK_SCORE_MAP = {
    RiskProbability.low: 0.1,
    RiskProbability.medium: 0.3,
    RiskProbability.high: 0.6,
    RiskProbability.very_high: 0.9,
}

_IMPACT_SCORE_MAP = {
    RiskImpact.negligible: 0.1,
    RiskImpact.moderate: 0.3,
    RiskImpact.significant: 0.6,
    RiskImpact.severe: 0.9,
}


async def assess_transaction_risks(
    db: AsyncSession,
    building_id: UUID,
) -> TransactionRiskAssessment:
    """
    Assess categorized transaction risks: regulatory, financial, legal, reputational.
    """
    building = await _fetch_building(db, building_id)
    diagnostics = await _fetch_diagnostics(db, building_id)
    samples = await _fetch_samples(db, building_id)
    grouped = _group_samples_by_pollutant(samples)

    exceeded_pollutants = [p for p, ss in grouped.items() if any(s.threshold_exceeded for s in ss)]
    critical_samples = [s for s in samples if s.risk_level == "critical"]
    compliance = _compliance_state(building, diagnostics, samples)

    risks: list[TransactionRisk] = []

    # 1. Regulatory risk
    reg_severity: list[str] = []
    if compliance.diagnostic_required and not compliance.diagnostic_completed:
        reg_severity.append("high")
    if exceeded_pollutants:
        reg_severity.append("medium")
    if critical_samples:
        reg_severity.append("critical")

    reg_prob = _probability_from_count(len(exceeded_pollutants), 2)
    reg_impact = _impact_from_severity(reg_severity)

    risks.append(
        TransactionRisk(
            category="regulatory",
            title="Non-compliance penalties",
            description=(
                "Risk of fines and mandatory remediation orders from cantonal "
                f"authorities ({compliance.authority_name}) for non-compliant pollutant levels."
            ),
            probability=reg_prob,
            impact=reg_impact,
            mitigation="Complete pollutant diagnostics and submit waste elimination plan before acquisition.",
            contributing_pollutants=exceeded_pollutants,
        )
    )

    # 2. Financial risk
    surface = building.surface_area_m2 or 0.0
    total_cost = sum(
        (_REMEDIATION_RATES.get(p, 100.0) * surface) + (_RADON_FIXED if p == "radon" else 0.0)
        for p in exceeded_pollutants
    )
    fin_prob = (
        RiskProbability.high
        if total_cost > 50_000
        else (RiskProbability.medium if total_cost > 10_000 else RiskProbability.low)
    )
    fin_impact = (
        RiskImpact.severe
        if total_cost > 100_000
        else (
            RiskImpact.significant
            if total_cost > 30_000
            else RiskImpact.moderate
            if total_cost > 0
            else RiskImpact.negligible
        )
    )

    risks.append(
        TransactionRisk(
            category="financial",
            title="Remediation costs",
            description=f"Estimated remediation cost: CHF {total_cost:,.0f}. Costs may escalate if additional contamination is discovered.",
            probability=fin_prob,
            impact=fin_impact,
            mitigation="Negotiate price reduction or escrow for remediation. Obtain detailed cost estimate.",
            contributing_pollutants=exceeded_pollutants,
        )
    )

    # 3. Legal risk
    legal_severity: list[str] = []
    if compliance.suva_notification_required:
        legal_severity.append("high")
    if len(exceeded_pollutants) >= 2:
        legal_severity.append("medium")
    legal_prob = _probability_from_count(len(exceeded_pollutants), 2)
    legal_impact = _impact_from_severity(legal_severity)

    risks.append(
        TransactionRisk(
            category="legal",
            title="Liability transfer",
            description="Buyer assumes liability for existing pollutant contamination upon acquisition. Seller disclosure obligations may be incomplete.",
            probability=legal_prob,
            impact=legal_impact,
            mitigation="Require seller to provide complete diagnostic history. Include indemnification clauses in purchase agreement.",
            contributing_pollutants=exceeded_pollutants,
        )
    )

    # 4. Reputational risk
    rep_severity: list[str] = []
    if "asbestos" in exceeded_pollutants:
        rep_severity.append("high")
    if critical_samples:
        rep_severity.append("critical")
    rep_prob = _probability_from_count(len(critical_samples), 1)
    rep_impact = _impact_from_severity(rep_severity)

    risks.append(
        TransactionRisk(
            category="reputational",
            title="Occupant health exposure",
            description="Risk of negative publicity and tenant complaints if pollutant exposure is revealed post-acquisition.",
            probability=rep_prob,
            impact=rep_impact,
            mitigation="Communicate remediation plan proactively. Engage independent health assessment.",
            contributing_pollutants=exceeded_pollutants,
        )
    )

    # Overall risk score (weighted average of probability x impact)
    scores = []
    for r in risks:
        p = _RISK_SCORE_MAP.get(r.probability, 0.1)
        i = _IMPACT_SCORE_MAP.get(r.impact, 0.1)
        scores.append(p * i)
    overall = round(sum(scores) / len(scores), 2) if scores else 0.0

    highest_cat = max(risks, key=lambda r: _RISK_SCORE_MAP.get(r.probability, 0) * _IMPACT_SCORE_MAP.get(r.impact, 0))

    return TransactionRiskAssessment(
        building_id=building.id,
        overall_risk_score=overall,
        risks=risks,
        highest_risk_category=highest_cat.category,
        summary=f"Transaction risk assessment for {building.address}: overall score {overall:.2f}/1.00. Highest risk: {highest_cat.category}.",
    )


# ---------------------------------------------------------------------------
# Public API — FN3: estimate_property_value_impact
# ---------------------------------------------------------------------------


async def estimate_property_value_impact(
    db: AsyncSession,
    building_id: UUID,
) -> PropertyValueImpact:
    """
    Estimate pollutant-driven property value adjustment.

    Base depreciation per pollutant: asbestos -8%, PCB -5%, radon -3%, lead -4%, HAP -2%.
    Cumulative cap: -25%. Post-remediation recovery: 60% of depreciation.
    """
    building = await _fetch_building(db, building_id)
    samples = await _fetch_samples(db, building_id)
    grouped = _group_samples_by_pollutant(samples)

    depreciations, capped, recovery = _compute_depreciations(grouped)
    net = round(capped - recovery, 2)

    pollutants_detected = [d.pollutant for d in depreciations if d.detected]
    if not pollutants_detected:
        summary = f"No pollutant thresholds exceeded for {building.address}. No value depreciation."
    else:
        summary = (
            f"Property value impact for {building.address}: "
            f"-{capped}% depreciation (capped), +{recovery}% post-remediation recovery, "
            f"net impact -{net}%. Pollutants: {', '.join(pollutants_detected)}."
        )

    return PropertyValueImpact(
        building_id=building.id,
        pollutant_depreciations=depreciations,
        raw_cumulative_pct=round(sum(d.applied_depreciation_pct for d in depreciations), 2),
        capped_depreciation_pct=capped,
        post_remediation_recovery_pct=recovery,
        net_impact_pct=net,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Public API — FN4: compare_acquisition_targets
# ---------------------------------------------------------------------------


async def compare_acquisition_targets(
    db: AsyncSession,
    building_ids: list[UUID],
) -> AcquisitionCompareResponse:
    """
    Side-by-side comparison of buildings for acquisition decisions.
    Ranked by attractiveness (lower risk score + lower cost + lower depreciation = better).
    """
    if len(building_ids) > 10:
        raise ValueError("Cannot compare more than 10 buildings at once")

    targets: list[AcquisitionTarget] = []

    for bid in building_ids:
        building = await _fetch_building(db, bid)
        samples = await _fetch_samples(db, bid)
        grouped = _group_samples_by_pollutant(samples)
        diagnostics = await _fetch_diagnostics(db, bid)

        # Risk score
        risk_assessment = await assess_transaction_risks(db, bid)
        risk_score = risk_assessment.overall_risk_score

        # Remediation cost
        cost_summary = _remediation_cost_summary(building, grouped)
        avg_cost = (cost_summary.total_min_chf + cost_summary.total_max_chf) / 2

        # Value impact
        _deps, capped_dep, recovery = _compute_depreciations(grouped)
        net_impact = round(capped_dep - recovery, 2)

        # Recommendation
        compliance = _compliance_state(building, diagnostics, samples)
        flags = _risk_flags(building, diagnostics, samples, compliance)
        rec, _ = _recommendation(flags, capped_dep, compliance)

        targets.append(
            AcquisitionTarget(
                building_id=bid,
                address=building.address,
                risk_score=risk_score,
                remediation_cost_chf=round(avg_cost, 2),
                value_impact_pct=net_impact,
                recommendation=rec,
                rank=0,  # set after sorting
            )
        )

    # Rank by attractiveness: lower composite score = better
    # Composite: risk_score (0-1) + normalized cost + normalized depreciation
    max_cost = max((t.remediation_cost_chf for t in targets), default=1.0) or 1.0
    max_dep = max((abs(t.value_impact_pct) for t in targets), default=1.0) or 1.0

    def _composite(t: AcquisitionTarget) -> float:
        return t.risk_score + (t.remediation_cost_chf / max_cost) + (abs(t.value_impact_pct) / max_dep)

    targets.sort(key=_composite)
    for i, t in enumerate(targets):
        t.rank = i + 1

    best_id = targets[0].building_id if targets else None
    worst_id = targets[-1].building_id if targets else None

    return AcquisitionCompareResponse(
        targets=targets,
        best_target=best_id,
        worst_target=worst_id,
    )
