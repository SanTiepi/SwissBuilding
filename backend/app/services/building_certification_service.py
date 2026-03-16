"""
SwissBuildingOS - Building Certification Service

Evaluates building readiness for Swiss certification/label programs
(Minergie, CECB, SNBS, GEAK). Checks diagnostic completeness, document
availability, and pollutant clearance status.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ALL_POLLUTANTS
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.sample import Sample
from app.schemas.building_certification import (
    AvailableCertifications,
    CertificationDistributionItem,
    CertificationEligibility,
    CertificationReadiness,
    CertificationRoadmap,
    MissingRequirement,
    PortfolioCertificationStatus,
    RoadmapStep,
)
from app.services.building_data_loader import load_org_buildings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_CERTIFICATION_TYPES = {"minergie", "cecb", "snbs", "geak"}

_ALL_POLLUTANTS_SET: set[str] = set(ALL_POLLUTANTS)

CERTIFICATION_LABELS = {
    "minergie": "Minergie",
    "cecb": "CECB (Certificat Energetique Cantonal des Batiments)",
    "snbs": "SNBS (Standard Nachhaltiges Bauen Schweiz)",
    "geak": "GEAK (Gebaudeenergieausweis der Kantone)",
}

# Minimum requirements per certification type
# Each maps to a set of requirement check IDs
CERTIFICATION_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    "minergie": {
        "blocking": [
            "has_completed_diagnostic",
            "has_energy_assessment",
            "pollutants_cleared",
            "has_diagnostic_report",
        ],
        "recommended": [
            "all_pollutants_evaluated",
            "has_floor_plans",
            "has_lab_reports",
        ],
    },
    "cecb": {
        "blocking": [
            "has_completed_diagnostic",
            "has_energy_assessment",
            "has_diagnostic_report",
        ],
        "recommended": [
            "pollutants_cleared",
            "has_floor_plans",
            "all_pollutants_evaluated",
        ],
    },
    "snbs": {
        "blocking": [
            "has_completed_diagnostic",
            "pollutants_cleared",
            "all_pollutants_evaluated",
            "has_diagnostic_report",
            "has_lab_reports",
        ],
        "recommended": [
            "has_energy_assessment",
            "has_floor_plans",
        ],
    },
    "geak": {
        "blocking": [
            "has_completed_diagnostic",
            "has_energy_assessment",
            "has_diagnostic_report",
        ],
        "recommended": [
            "pollutants_cleared",
            "all_pollutants_evaluated",
            "has_floor_plans",
        ],
    },
}


# ---------------------------------------------------------------------------
# Internal data-fetching helpers
# ---------------------------------------------------------------------------


async def _fetch_building_data(
    db: AsyncSession,
    building_id: UUID,
) -> tuple[Building | None, list[Diagnostic], list[Sample], list[Document]]:
    """Load building plus related diagnostics, samples, and documents."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        return None, [], [], []

    diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(diag_result.scalars().all())

    samples: list[Sample] = []
    if diagnostics:
        diag_ids = [d.id for d in diagnostics]
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(doc_result.scalars().all())

    return building, diagnostics, samples, documents


# ---------------------------------------------------------------------------
# Requirement checks
# ---------------------------------------------------------------------------


def _check_requirements(
    diagnostics: list[Diagnostic],
    samples: list[Sample],
    documents: list[Document],
) -> dict[str, MissingRequirement | None]:
    """
    Run all possible requirement checks. Returns a dict mapping check_id
    to a MissingRequirement if the check fails, or None if it passes.
    """
    results: dict[str, MissingRequirement | None] = {}

    # 1. Has completed/validated diagnostic
    completed = [d for d in diagnostics if d.status in ("completed", "validated")]
    if completed:
        results["has_completed_diagnostic"] = None
    else:
        results["has_completed_diagnostic"] = MissingRequirement(
            id="has_completed_diagnostic",
            description="At least one completed or validated diagnostic is required",
            category="diagnostic",
            severity="blocking",
        )

    # 2. Has energy assessment (diagnostic_type contains 'energy' or type is cecb/minergie)
    energy_types = {"energy", "cecb", "minergie", "geak", "energy_audit"}
    has_energy = any((d.diagnostic_type or "").lower() in energy_types for d in diagnostics)
    if has_energy:
        results["has_energy_assessment"] = None
    else:
        results["has_energy_assessment"] = MissingRequirement(
            id="has_energy_assessment",
            description="An energy performance assessment is required",
            category="diagnostic",
            severity="blocking",
        )

    # 3. Pollutants cleared (no threshold-exceeded samples unresolved)
    positive_samples = [s for s in samples if s.threshold_exceeded]
    if not positive_samples:
        results["pollutants_cleared"] = None
    else:
        results["pollutants_cleared"] = MissingRequirement(
            id="pollutants_cleared",
            description=f"{len(positive_samples)} sample(s) with pollutant threshold exceeded",
            category="pollutant",
            severity="blocking",
        )

    # 4. All 5 pollutants evaluated
    evaluated = {(s.pollutant_type or "").lower() for s in samples} & _ALL_POLLUTANTS_SET
    if evaluated == _ALL_POLLUTANTS_SET:
        results["all_pollutants_evaluated"] = None
    else:
        missing = _ALL_POLLUTANTS_SET - evaluated
        results["all_pollutants_evaluated"] = MissingRequirement(
            id="all_pollutants_evaluated",
            description=f"Missing pollutant evaluations: {', '.join(sorted(missing))}",
            category="diagnostic",
            severity="recommended",
        )

    # 5. Has diagnostic report document
    report_types = {"diagnostic_report", "report"}
    has_report = any((d.document_type or "").lower() in report_types for d in documents)
    if has_report:
        results["has_diagnostic_report"] = None
    else:
        results["has_diagnostic_report"] = MissingRequirement(
            id="has_diagnostic_report",
            description="A diagnostic report document must be uploaded",
            category="document",
            severity="blocking",
        )

    # 6. Has floor plans
    has_plans = any((d.document_type or "").lower() in ("floor_plan", "plan") for d in documents)
    if has_plans:
        results["has_floor_plans"] = None
    else:
        results["has_floor_plans"] = MissingRequirement(
            id="has_floor_plans",
            description="Floor plans should be uploaded",
            category="document",
            severity="recommended",
        )

    # 7. Has lab reports
    has_lab = any((d.document_type or "").lower() in ("lab_report", "lab_analysis") for d in documents)
    if has_lab:
        results["has_lab_reports"] = None
    else:
        results["has_lab_reports"] = MissingRequirement(
            id="has_lab_reports",
            description="Lab analysis reports should be uploaded",
            category="document",
            severity="recommended",
        )

    return results


def _compute_readiness_score(
    check_results: dict[str, MissingRequirement | None],
    certification_type: str,
) -> int:
    """Compute a 0-100 readiness score based on check results and certification requirements."""
    reqs = CERTIFICATION_REQUIREMENTS.get(certification_type, {})
    blocking = reqs.get("blocking", [])
    recommended = reqs.get("recommended", [])

    if not blocking and not recommended:
        return 0

    # Blocking checks count for 70% of total, recommended for 30%
    blocking_weight = 70
    recommended_weight = 30

    blocking_passed = sum(1 for r in blocking if check_results.get(r) is None)
    blocking_total = len(blocking) if blocking else 1

    recommended_passed = sum(1 for r in recommended if check_results.get(r) is None)
    recommended_total = len(recommended) if recommended else 1

    score = int(
        (blocking_passed / blocking_total) * blocking_weight
        + (recommended_passed / recommended_total) * recommended_weight
    )
    return min(100, max(0, score))


def _estimate_effort(score: int) -> str:
    """Estimate completion effort from readiness score."""
    if score >= 80:
        return "low"
    if score >= 50:
        return "medium"
    return "high"


# ---------------------------------------------------------------------------
# FN1: evaluate_certification_readiness
# ---------------------------------------------------------------------------


async def evaluate_certification_readiness(
    building_id: UUID,
    certification_type: str,
    db: AsyncSession,
) -> CertificationReadiness:
    """
    Evaluate how ready a building is for a specific certification.

    Returns readiness score (0-100), missing requirements, and estimated effort.
    """
    if certification_type not in VALID_CERTIFICATION_TYPES:
        return CertificationReadiness(
            building_id=building_id,
            certification_type=certification_type,
            readiness_score=0,
            missing_requirements=[
                MissingRequirement(
                    id="invalid_type",
                    description=f"Unknown certification type: {certification_type}",
                    category="diagnostic",
                    severity="blocking",
                )
            ],
            estimated_completion_effort="high",
            evaluated_at=datetime.now(UTC),
        )

    building, diagnostics, samples, documents = await _fetch_building_data(db, building_id)
    if not building:
        return CertificationReadiness(
            building_id=building_id,
            certification_type=certification_type,
            readiness_score=0,
            missing_requirements=[
                MissingRequirement(
                    id="building_not_found",
                    description="Building not found",
                    category="diagnostic",
                    severity="blocking",
                )
            ],
            estimated_completion_effort="high",
            evaluated_at=datetime.now(UTC),
        )

    check_results = _check_requirements(diagnostics, samples, documents)
    score = _compute_readiness_score(check_results, certification_type)

    # Filter missing requirements to those relevant to this certification
    reqs = CERTIFICATION_REQUIREMENTS[certification_type]
    relevant_ids = set(reqs.get("blocking", [])) | set(reqs.get("recommended", []))
    missing = [req for check_id, req in check_results.items() if req is not None and check_id in relevant_ids]

    return CertificationReadiness(
        building_id=building_id,
        certification_type=certification_type,
        readiness_score=score,
        missing_requirements=missing,
        estimated_completion_effort=_estimate_effort(score),
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN2: get_available_certifications
# ---------------------------------------------------------------------------


async def get_available_certifications(
    building_id: UUID,
    db: AsyncSession,
) -> AvailableCertifications:
    """
    List all certifications a building could pursue with eligibility status.
    """
    building, diagnostics, samples, documents = await _fetch_building_data(db, building_id)

    certifications: list[CertificationEligibility] = []

    if not building:
        # Return all as ineligible
        for cert_type in sorted(VALID_CERTIFICATION_TYPES):
            certifications.append(
                CertificationEligibility(
                    certification_type=cert_type,
                    label=CERTIFICATION_LABELS[cert_type],
                    eligibility="ineligible",
                    readiness_percentage=0,
                    blockers=["Building not found"],
                )
            )
        return AvailableCertifications(
            building_id=building_id,
            certifications=certifications,
            evaluated_at=datetime.now(UTC),
        )

    check_results = _check_requirements(diagnostics, samples, documents)

    for cert_type in sorted(VALID_CERTIFICATION_TYPES):
        score = _compute_readiness_score(check_results, cert_type)
        reqs = CERTIFICATION_REQUIREMENTS[cert_type]
        blocking_ids = reqs.get("blocking", [])

        blockers = [check_results[bid].description for bid in blocking_ids if check_results.get(bid) is not None]

        if not blockers:
            eligibility = "eligible"
        elif score >= 50:
            eligibility = "partial"
        else:
            eligibility = "ineligible"

        certifications.append(
            CertificationEligibility(
                certification_type=cert_type,
                label=CERTIFICATION_LABELS[cert_type],
                eligibility=eligibility,
                readiness_percentage=score,
                blockers=blockers,
            )
        )

    return AvailableCertifications(
        building_id=building_id,
        certifications=certifications,
        evaluated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN3: generate_certification_roadmap
# ---------------------------------------------------------------------------

# Roadmap step templates per requirement check
_STEP_TEMPLATES: dict[str, dict] = {
    "has_completed_diagnostic": {
        "description": "Complete a building diagnostic assessment",
        "estimated_duration_days": 14,
        "dependencies": [],
        "priority": "critical",
    },
    "has_energy_assessment": {
        "description": "Conduct an energy performance assessment",
        "estimated_duration_days": 21,
        "dependencies": ["has_completed_diagnostic"],
        "priority": "critical",
    },
    "pollutants_cleared": {
        "description": "Remediate or clear identified pollutant issues",
        "estimated_duration_days": 60,
        "dependencies": ["has_completed_diagnostic"],
        "priority": "high",
    },
    "all_pollutants_evaluated": {
        "description": "Evaluate all 5 pollutant types (asbestos, PCB, lead, HAP, radon)",
        "estimated_duration_days": 14,
        "dependencies": ["has_completed_diagnostic"],
        "priority": "high",
    },
    "has_diagnostic_report": {
        "description": "Upload the diagnostic report document",
        "estimated_duration_days": 3,
        "dependencies": ["has_completed_diagnostic"],
        "priority": "critical",
    },
    "has_floor_plans": {
        "description": "Upload building floor plans",
        "estimated_duration_days": 7,
        "dependencies": [],
        "priority": "medium",
    },
    "has_lab_reports": {
        "description": "Upload laboratory analysis reports",
        "estimated_duration_days": 5,
        "dependencies": ["all_pollutants_evaluated"],
        "priority": "medium",
    },
}


async def generate_certification_roadmap(
    building_id: UUID,
    certification_type: str,
    db: AsyncSession,
) -> CertificationRoadmap:
    """
    Generate an ordered list of steps to achieve a specific certification.
    """
    if certification_type not in VALID_CERTIFICATION_TYPES:
        return CertificationRoadmap(
            building_id=building_id,
            certification_type=certification_type,
            steps=[],
            total_estimated_days=0,
            generated_at=datetime.now(UTC),
        )

    building, diagnostics, samples, documents = await _fetch_building_data(db, building_id)

    if not building:
        return CertificationRoadmap(
            building_id=building_id,
            certification_type=certification_type,
            steps=[
                RoadmapStep(
                    step_number=1,
                    description="Building not found — verify building exists",
                    estimated_duration_days=0,
                    dependencies=[],
                    priority="critical",
                )
            ],
            total_estimated_days=0,
            generated_at=datetime.now(UTC),
        )

    check_results = _check_requirements(diagnostics, samples, documents)
    reqs = CERTIFICATION_REQUIREMENTS[certification_type]
    all_req_ids = reqs.get("blocking", []) + reqs.get("recommended", [])

    # Build steps only for missing requirements
    steps: list[RoadmapStep] = []
    step_num = 0
    for req_id in all_req_ids:
        if check_results.get(req_id) is not None:
            template = _STEP_TEMPLATES.get(req_id)
            if template:
                step_num += 1
                steps.append(
                    RoadmapStep(
                        step_number=step_num,
                        description=template["description"],
                        estimated_duration_days=template["estimated_duration_days"],
                        dependencies=template["dependencies"],
                        priority=template["priority"],
                    )
                )

    total_days = sum(s.estimated_duration_days for s in steps)

    return CertificationRoadmap(
        building_id=building_id,
        certification_type=certification_type,
        steps=steps,
        total_estimated_days=total_days,
        generated_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# FN4: get_portfolio_certification_status
# ---------------------------------------------------------------------------


async def get_portfolio_certification_status(
    org_id: UUID,
    db: AsyncSession,
) -> PortfolioCertificationStatus:
    """
    Summarize certification status across all buildings belonging to an organization.
    """
    # Get buildings via users in the organization
    all_buildings = await load_org_buildings(db, org_id)
    buildings = [b for b in all_buildings if b.status == "active"]

    total = len(buildings)
    certified = 0
    in_progress = 0
    eligible = 0
    cert_counts: dict[str, int] = {}

    for building in buildings:
        avail = await get_available_certifications(building.id, db)
        building_best = "ineligible"
        for cert in avail.certifications:
            if cert.eligibility == "eligible":
                building_best = "eligible"
                cert_counts[cert.certification_type] = cert_counts.get(cert.certification_type, 0) + 1
            elif cert.eligibility == "partial" and building_best != "eligible":
                building_best = "partial"

        if building_best == "eligible":
            # If fully eligible for any, count as eligible
            eligible += 1
        elif building_best == "partial":
            in_progress += 1
        # "ineligible" buildings are just part of total

    distribution = [
        CertificationDistributionItem(certification_type=ct, count=cnt) for ct, cnt in sorted(cert_counts.items())
    ]

    return PortfolioCertificationStatus(
        organization_id=org_id,
        total_buildings=total,
        certified_count=certified,
        in_progress_count=in_progress,
        eligible_count=eligible,
        certification_distribution=distribution,
        evaluated_at=datetime.now(UTC),
    )
