"""Service for generating structured building passport exports."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.schemas.passport_export import (
    BuildingPassportExport,
    PassportComparison,
    PassportComplianceSection,
    PassportIdentity,
    PassportInterventionSection,
    PassportPollutantSection,
    PassportValidation,
    PortfolioPassportSummary,
)
from app.services.building_data_loader import load_org_buildings

PASSPORT_VERSION = "1.0.0"
POLLUTANT_TYPES = ["asbestos", "pcb", "lead", "hap", "radon"]


async def generate_building_passport(
    building_id: UUID,
    db: AsyncSession,
    format_type: str = "json",
) -> BuildingPassportExport | None:
    """Generate a comprehensive building passport export."""
    result = await db.execute(
        select(Building)
        .options(
            selectinload(Building.diagnostics).selectinload(Diagnostic.samples),
            selectinload(Building.interventions),
            selectinload(Building.action_items),
        )
        .where(Building.id == building_id)
    )
    building = result.scalar_one_or_none()
    if building is None:
        return None

    identity = PassportIdentity(
        building_id=building.id,
        egid=building.egid,
        egrid=building.egrid,
        address=building.address,
        postal_code=building.postal_code,
        city=building.city,
        canton=building.canton,
        construction_year=building.construction_year,
        building_type=building.building_type,
    )

    # Build pollutant sections
    pollutant_sections = _build_pollutant_sections(building)

    # Intervention summary
    interventions: list[Intervention] = list(building.interventions)
    completed = [i for i in interventions if i.status == "completed"]
    planned = [i for i in interventions if i.status == "planned"]
    total_cost = sum(i.cost_chf or 0.0 for i in interventions)
    types_set = sorted({i.intervention_type for i in interventions})
    intervention_summary = PassportInterventionSection(
        intervention_count=len(interventions),
        completed_count=len(completed),
        planned_count=len(planned),
        total_estimated_cost=total_cost,
        intervention_types=types_set,
    )

    # Compliance section
    actions: list[ActionItem] = list(building.action_items)
    open_actions = [a for a in actions if a.status == "open"]
    critical_actions = [a for a in open_actions if a.priority == "critical"]
    deadlines = [a.due_date for a in open_actions if a.due_date is not None]
    next_deadline = min(deadlines) if deadlines else None

    if not actions:
        overall_status = "unknown"
    elif critical_actions:
        overall_status = "non_compliant"
    elif open_actions:
        overall_status = "partial"
    else:
        overall_status = "compliant"

    compliance = PassportComplianceSection(
        overall_status=overall_status,
        open_actions=len(open_actions),
        critical_actions=len(critical_actions),
        next_deadline=next_deadline,
        regulatory_framework=f"Swiss OTConst / Canton {building.canton}",
    )

    # Scores
    quality_score = _compute_quality_score(building, pollutant_sections)
    completeness_score = _compute_completeness_score(building)

    return BuildingPassportExport(
        passport_version=PASSPORT_VERSION,
        export_format=format_type,
        identity=identity,
        pollutant_sections=pollutant_sections,
        intervention_summary=intervention_summary,
        compliance=compliance,
        quality_score=round(quality_score, 2),
        completeness_score=round(completeness_score, 2),
        generated_at=datetime.now(UTC),
    )


def _build_pollutant_sections(building: Building) -> list[PassportPollutantSection]:
    """Build pollutant sections for all 5 pollutant types."""
    sections: list[PassportPollutantSection] = []
    diagnostics: list[Diagnostic] = list(building.diagnostics)

    for pollutant in POLLUTANT_TYPES:
        # Find diagnostics matching this pollutant type
        matching_diags = [d for d in diagnostics if d.diagnostic_type == pollutant]
        diagnosed = len(matching_diags) > 0

        # Collect all samples for matching diagnostics
        all_samples: list[Sample] = []
        for d in matching_diags:
            all_samples.extend(d.samples)

        sample_count = len(all_samples)
        exceeded_count = sum(1 for s in all_samples if s.threshold_exceeded)

        # Determine risk level from samples
        risk_levels = [s.risk_level for s in all_samples if s.risk_level]
        if risk_levels:
            priority = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
            risk_level = max(risk_levels, key=lambda r: priority.get(r, 0))
        else:
            risk_level = "unknown"

        # Last diagnostic date
        dates = [d.date_report for d in matching_diags if d.date_report is not None]
        last_date = max(dates) if dates else None

        # Compliance status
        if not diagnosed:
            compliance_status = "unknown"
        elif exceeded_count > 0:
            compliance_status = "non_compliant"
        elif sample_count > 0:
            compliance_status = "compliant"
        else:
            compliance_status = "pending"

        sections.append(
            PassportPollutantSection(
                pollutant_type=pollutant,
                diagnosed=diagnosed,
                sample_count=sample_count,
                exceeded_count=exceeded_count,
                risk_level=risk_level,
                last_diagnostic_date=last_date,
                compliance_status=compliance_status,
            )
        )

    return sections


def _compute_quality_score(
    building: Building,
    pollutant_sections: list[PassportPollutantSection],
) -> float:
    """Weighted quality score 0.0-1.0 based on data completeness."""
    score = 0.0
    total_weight = 0.0

    # Identity completeness (weight 0.3)
    identity_fields = [
        building.egid,
        building.egrid,
        building.construction_year,
    ]
    identity_filled = sum(1 for f in identity_fields if f is not None)
    score += 0.3 * (identity_filled / len(identity_fields))
    total_weight += 0.3

    # Pollutant coverage (weight 0.4)
    diagnosed_count = sum(1 for s in pollutant_sections if s.diagnosed)
    score += 0.4 * (diagnosed_count / len(POLLUTANT_TYPES))
    total_weight += 0.4

    # Intervention data (weight 0.15)
    has_interventions = len(list(building.interventions)) > 0
    score += 0.15 * (1.0 if has_interventions else 0.0)
    total_weight += 0.15

    # Action tracking (weight 0.15)
    has_actions = len(list(building.action_items)) > 0
    score += 0.15 * (1.0 if has_actions else 0.0)
    total_weight += 0.15

    return score / total_weight if total_weight > 0 else 0.0


def _compute_completeness_score(building: Building) -> float:
    """Completeness score based on fields present / total expected."""
    expected_fields = [
        building.address,
        building.postal_code,
        building.city,
        building.canton,
        building.egid,
        building.egrid,
        building.construction_year,
        building.building_type,
        building.surface_area_m2,
        building.floors_above,
    ]
    filled = sum(1 for f in expected_fields if f is not None)
    return filled / len(expected_fields)


async def validate_passport(
    building_id: UUID,
    db: AsyncSession,
) -> PassportValidation | None:
    """Validate passport readiness for a building."""
    result = await db.execute(
        select(Building)
        .options(
            selectinload(Building.diagnostics).selectinload(Diagnostic.samples),
            selectinload(Building.interventions),
        )
        .where(Building.id == building_id)
    )
    building = result.scalar_one_or_none()
    if building is None:
        return None

    missing_fields: list[str] = []
    warnings: list[str] = []

    # Required fields check
    if not building.address:
        missing_fields.append("address")
    if not building.canton:
        missing_fields.append("canton")
    if not building.egid:
        missing_fields.append("egid")
    if not building.diagnostics:
        missing_fields.append("at_least_one_diagnostic")

    # Warnings
    diagnostics: list[Diagnostic] = list(building.diagnostics)
    if diagnostics:
        for d in diagnostics:
            if d.date_report:
                age = (date.today() - d.date_report).days / 365.25
                if age > 5:
                    warnings.append(f"Diagnostic {d.diagnostic_type} is older than 5 years")

    # Check pollutant coverage
    diagnosed_types = {d.diagnostic_type for d in diagnostics}
    missing_pollutants = set(POLLUTANT_TYPES) - diagnosed_types
    if missing_pollutants:
        warnings.append(f"Missing pollutant coverage: {', '.join(sorted(missing_pollutants))}")

    # Check interventions
    if not building.interventions:
        warnings.append("No interventions recorded")

    # Completeness percentage
    completeness_fields = [
        building.address,
        building.postal_code,
        building.city,
        building.canton,
        building.egid,
        building.egrid,
        building.construction_year,
        building.building_type,
    ]
    filled = sum(1 for f in completeness_fields if f is not None)
    completeness_pct = (filled / len(completeness_fields)) * 100

    is_valid = len(missing_fields) == 0

    return PassportValidation(
        building_id=building_id,
        is_valid=is_valid,
        missing_fields=missing_fields,
        warnings=warnings,
        completeness_pct=round(completeness_pct, 1),
        generated_at=datetime.now(UTC),
    )


async def compare_passports(
    building_a_id: UUID,
    building_b_id: UUID,
    db: AsyncSession,
) -> PassportComparison | None:
    """Compare passports for two buildings."""
    passport_a = await generate_building_passport(building_a_id, db)
    passport_b = await generate_building_passport(building_b_id, db)

    if passport_a is None or passport_b is None:
        return None

    # Compare pollutant profiles
    matching_pollutants: list[str] = []
    differing_fields: list[str] = []

    for sec_a in passport_a.pollutant_sections:
        sec_b = next(
            (s for s in passport_b.pollutant_sections if s.pollutant_type == sec_a.pollutant_type),
            None,
        )
        if sec_b is None:
            continue
        if sec_a.compliance_status == sec_b.compliance_status:
            matching_pollutants.append(sec_a.pollutant_type)
        else:
            differing_fields.append(f"pollutant_{sec_a.pollutant_type}_compliance")

    # Compare identity fields
    if passport_a.identity.canton != passport_b.identity.canton:
        differing_fields.append("canton")
    if passport_a.identity.building_type != passport_b.identity.building_type:
        differing_fields.append("building_type")
    if passport_a.compliance.overall_status != passport_b.compliance.overall_status:
        differing_fields.append("overall_compliance_status")

    # Similarity score
    total_attributes = len(POLLUTANT_TYPES) + 3  # pollutants + canton + type + compliance
    matching_count = (
        len(matching_pollutants)
        + total_attributes
        - len(POLLUTANT_TYPES)
        - len([f for f in differing_fields if f in ("canton", "building_type", "overall_compliance_status")])
    )
    similarity_score = matching_count / total_attributes if total_attributes > 0 else 0.0

    # Recommendation
    if similarity_score > 0.8:
        recommendation = "Buildings have very similar profiles; shared remediation strategies may apply."
    elif similarity_score > 0.5:
        recommendation = "Buildings share some characteristics; partial strategy reuse possible."
    else:
        recommendation = "Buildings differ significantly; individual assessment recommended."

    return PassportComparison(
        building_a_id=building_a_id,
        building_b_id=building_b_id,
        similarity_score=round(similarity_score, 2),
        matching_pollutants=matching_pollutants,
        differing_fields=differing_fields,
        recommendation=recommendation,
    )


async def get_portfolio_passport_summary(
    org_id: UUID,
    db: AsyncSession,
) -> PortfolioPassportSummary | None:
    """Generate a portfolio-level passport summary for an organization."""
    # Get buildings belonging to org users
    all_buildings = await load_org_buildings(db, org_id)
    if not all_buildings:
        return PortfolioPassportSummary(
            organization_id=org_id,
            total_buildings=0,
            passports_complete=0,
            passports_incomplete=0,
            average_quality_score=0.0,
            average_completeness=0.0,
            buildings_needing_attention=[],
            generated_at=datetime.now(UTC),
        )

    buildings = [(b.id, b.address) for b in all_buildings]

    total = len(buildings)
    if total == 0:
        return PortfolioPassportSummary(
            organization_id=org_id,
            total_buildings=0,
            passports_complete=0,
            passports_incomplete=0,
            average_quality_score=0.0,
            average_completeness=0.0,
            buildings_needing_attention=[],
            generated_at=datetime.now(UTC),
        )

    complete = 0
    incomplete = 0
    quality_scores: list[float] = []
    completeness_scores: list[float] = []
    needing_attention: list[str] = []

    for building_id, address in buildings:
        passport = await generate_building_passport(building_id, db)
        if passport is None:
            incomplete += 1
            needing_attention.append(address)
            continue

        quality_scores.append(passport.quality_score)
        completeness_scores.append(passport.completeness_score)

        if passport.completeness_score >= 0.8:
            complete += 1
        else:
            incomplete += 1

        if passport.completeness_score < 0.6:
            needing_attention.append(address)

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
    avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.0

    return PortfolioPassportSummary(
        organization_id=org_id,
        total_buildings=total,
        passports_complete=complete,
        passports_incomplete=incomplete,
        average_quality_score=round(avg_quality, 2),
        average_completeness=round(avg_completeness, 2),
        buildings_needing_attention=needing_attention,
        generated_at=datetime.now(UTC),
    )
