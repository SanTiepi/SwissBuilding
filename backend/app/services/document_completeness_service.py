"""Document completeness assessment service.

Evaluates which document types are present vs required for a building,
checks document currency (expiry), and provides portfolio-level summaries.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.schemas.document_completeness import (
    BuildingDocumentGap,
    DocumentCompletenessResult,
    DocumentCurrencyFlag,
    DocumentCurrencyResult,
    DocumentTypeStatus,
    MissingDocumentDetail,
    PortfolioDocumentStatus,
)
from app.services.building_data_loader import load_org_buildings

# ---------------------------------------------------------------------------
# Required document types for a complete building dossier
# ---------------------------------------------------------------------------

REQUIRED_DOCUMENT_TYPES = [
    "diagnostic_report",
    "lab_certificates",
    "building_plans",
    "waste_plan",
    "remediation_plan",
    "compliance_declarations",
    "photo_documentation",
    "contractor_authorizations",
]

# Validity periods in years per document type
VALIDITY_YEARS: dict[str, int] = {
    "diagnostic_report": 5,
    "lab_certificates": 3,
    "building_plans": 0,  # no expiry, checked differently
    "compliance_declarations": 2,
}

# Who should provide each document type
DOCUMENT_PROVIDERS: dict[str, str] = {
    "diagnostic_report": "Diagnostician (SUVA-recognized laboratory)",
    "lab_certificates": "Accredited laboratory",
    "building_plans": "Building owner or architect",
    "waste_plan": "Diagnostician or environmental engineer",
    "remediation_plan": "Remediation specialist (SUVA-recognized)",
    "compliance_declarations": "Building owner or property manager",
    "photo_documentation": "Diagnostician or site inspector",
    "contractor_authorizations": "Contractor (SUVA-approved)",
}

# Why each document type is needed
DOCUMENT_REASONS: dict[str, str] = {
    "diagnostic_report": "Required for pollutant assessment per OTConst Art. 60a",
    "lab_certificates": "Laboratory proof of sample analysis results",
    "building_plans": "Needed to locate pollutant zones and plan remediation",
    "waste_plan": "OLED compliance for waste disposal classification",
    "remediation_plan": "CFST 6503 requires documented remediation approach",
    "compliance_declarations": "Regulatory proof of compliance status",
    "photo_documentation": "Visual evidence of building condition and findings",
    "contractor_authorizations": "SUVA authorization proof for remediation contractors",
}

# Urgency ranking per document type
DOCUMENT_URGENCY: dict[str, str] = {
    "diagnostic_report": "critical",
    "lab_certificates": "critical",
    "building_plans": "high",
    "waste_plan": "high",
    "remediation_plan": "high",
    "compliance_declarations": "medium",
    "photo_documentation": "medium",
    "contractor_authorizations": "low",
}

# Template availability
TEMPLATE_AVAILABLE: dict[str, bool] = {
    "diagnostic_report": False,
    "lab_certificates": False,
    "building_plans": False,
    "waste_plan": True,
    "remediation_plan": True,
    "compliance_declarations": True,
    "photo_documentation": False,
    "contractor_authorizations": True,
}

# Mapping from document_type field values to our required types
_TYPE_ALIASES: dict[str, str] = {
    "diagnostic_report": "diagnostic_report",
    "lab_result": "lab_certificates",
    "lab_certificates": "lab_certificates",
    "lab_certificate": "lab_certificates",
    "building_plans": "building_plans",
    "building_plan": "building_plans",
    "technical_plan": "building_plans",
    "plan": "building_plans",
    "waste_plan": "waste_plan",
    "remediation_plan": "remediation_plan",
    "compliance_declarations": "compliance_declarations",
    "compliance_declaration": "compliance_declarations",
    "compliance_certificate": "compliance_declarations",
    "photo_documentation": "photo_documentation",
    "photo": "photo_documentation",
    "contractor_authorizations": "contractor_authorizations",
    "contractor_authorization": "contractor_authorizations",
}


def _normalize_document_type(doc_type: str | None) -> str | None:
    """Map a document's type field to the canonical required type."""
    if not doc_type:
        return None
    return _TYPE_ALIASES.get(doc_type.lower().strip())


async def _get_building_documents(db: AsyncSession, building_id: UUID) -> list[Document]:
    """Fetch all documents for a building."""
    result = await db.execute(select(Document).where(Document.building_id == building_id))
    return list(result.scalars().all())


def _compute_age_years(created_at: datetime | None) -> float:
    """Compute age in years from a datetime."""
    if not created_at:
        return 0.0
    now = datetime.now(UTC)
    # Handle naive datetimes from SQLite
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    delta = now - created_at
    return delta.days / 365.25


async def assess_document_completeness(
    db: AsyncSession,
    building_id: UUID,
) -> DocumentCompletenessResult:
    """Assess which required document types are present, missing, or outdated.

    Returns a score 0-100 reflecting overall document completeness.
    """
    docs = await _get_building_documents(db, building_id)

    # Group documents by normalized type
    docs_by_type: dict[str, list[Document]] = {}
    for doc in docs:
        normalized = _normalize_document_type(doc.document_type)
        if normalized:
            docs_by_type.setdefault(normalized, []).append(doc)

    types: list[DocumentTypeStatus] = []
    present_count = 0
    missing_count = 0
    outdated_count = 0

    for req_type in REQUIRED_DOCUMENT_TYPES:
        matching = docs_by_type.get(req_type, [])
        if not matching:
            types.append(
                DocumentTypeStatus(
                    document_type=req_type,
                    status="missing",
                )
            )
            missing_count += 1
        else:
            # Pick the most recent document
            latest = max(matching, key=lambda d: d.created_at or datetime.min)
            max_years = VALIDITY_YEARS.get(req_type, 0)
            age = _compute_age_years(latest.created_at)

            if max_years > 0 and age > max_years:
                status = "outdated"
                outdated_count += 1
            else:
                status = "present"
                present_count += 1

            types.append(
                DocumentTypeStatus(
                    document_type=req_type,
                    status=status,
                    document_id=latest.id,
                    uploaded_at=str(latest.created_at) if latest.created_at else None,
                )
            )

    total_required = len(REQUIRED_DOCUMENT_TYPES)
    score = (present_count / total_required) * 100.0 if total_required > 0 else 0.0

    return DocumentCompletenessResult(
        building_id=building_id,
        score=round(score, 1),
        total_required=total_required,
        present=present_count,
        missing=missing_count,
        outdated=outdated_count,
        types=types,
    )


async def get_missing_documents(
    db: AsyncSession,
    building_id: UUID,
) -> list[MissingDocumentDetail]:
    """Return a prioritized list of missing documents with context."""
    completeness = await assess_document_completeness(db, building_id)

    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    missing: list[MissingDocumentDetail] = []

    for t in completeness.types:
        if t.status in ("missing", "outdated"):
            missing.append(
                MissingDocumentDetail(
                    document_type=t.document_type,
                    reason=DOCUMENT_REASONS.get(t.document_type, "Required for complete dossier"),
                    provider=DOCUMENT_PROVIDERS.get(t.document_type, "Building owner"),
                    urgency=DOCUMENT_URGENCY.get(t.document_type, "medium"),
                    template_available=TEMPLATE_AVAILABLE.get(t.document_type, False),
                )
            )

    # Sort by urgency
    missing.sort(key=lambda m: urgency_order.get(m.urgency, 99))
    return missing


async def validate_document_currency(
    db: AsyncSession,
    building_id: UUID,
) -> DocumentCurrencyResult:
    """Check whether existing documents are still valid (not expired)."""
    docs = await _get_building_documents(db, building_id)

    flags: list[DocumentCurrencyFlag] = []

    for doc in docs:
        normalized = _normalize_document_type(doc.document_type)
        if not normalized:
            continue

        max_years = VALIDITY_YEARS.get(normalized, 0)
        if max_years <= 0:
            continue

        age = _compute_age_years(doc.created_at)
        is_expired = age > max_years

        # Compute expiry date
        expires_at = None
        if doc.created_at:
            created = doc.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            expires_at = str(created.replace(year=created.year + max_years))

        flags.append(
            DocumentCurrencyFlag(
                document_id=doc.id,
                document_type=normalized,
                filename=doc.file_name or "",
                uploaded_at=str(doc.created_at) if doc.created_at else "",
                max_validity_years=max_years,
                age_years=round(age, 2),
                is_expired=is_expired,
                expires_at=expires_at,
            )
        )

    valid_count = sum(1 for f in flags if not f.is_expired)
    expired_count = sum(1 for f in flags if f.is_expired)

    return DocumentCurrencyResult(
        building_id=building_id,
        total_checked=len(flags),
        valid=valid_count,
        expired=expired_count,
        flags=flags,
    )


async def get_portfolio_document_status(
    db: AsyncSession,
    org_id: UUID,
) -> PortfolioDocumentStatus:
    """Organization-level document completeness overview."""
    # Find buildings belonging to org members
    buildings = await load_org_buildings(db, org_id)

    if not buildings:
        return PortfolioDocumentStatus(
            organization_id=org_id,
            total_buildings=0,
            average_score=0.0,
            most_commonly_missing=None,
            buildings_with_critical_gaps=[],
            estimated_documents_to_full=0,
        )

    scores: list[float] = []
    missing_type_counts: dict[str, int] = {}
    critical_gaps: list[BuildingDocumentGap] = []
    total_missing = 0

    for building in buildings:
        completeness = await assess_document_completeness(db, building.id)
        scores.append(completeness.score)

        building_critical: list[str] = []
        for t in completeness.types:
            if t.status in ("missing", "outdated"):
                missing_type_counts[t.document_type] = missing_type_counts.get(t.document_type, 0) + 1
                total_missing += 1
                urgency = DOCUMENT_URGENCY.get(t.document_type, "medium")
                if urgency in ("critical", "high"):
                    building_critical.append(t.document_type)

        if building_critical:
            critical_gaps.append(
                BuildingDocumentGap(
                    building_id=building.id,
                    address=building.address or "",
                    score=completeness.score,
                    missing_count=completeness.missing + completeness.outdated,
                    critical_missing=building_critical,
                )
            )

    avg_score = sum(scores) / len(scores) if scores else 0.0

    most_common = None
    if missing_type_counts:
        most_common = max(missing_type_counts, key=lambda k: missing_type_counts[k])

    # Sort critical gaps by score ascending (worst first)
    critical_gaps.sort(key=lambda g: g.score)

    return PortfolioDocumentStatus(
        organization_id=org_id,
        total_buildings=len(buildings),
        average_score=round(avg_score, 1),
        most_commonly_missing=most_common,
        buildings_with_critical_gaps=critical_gaps,
        estimated_documents_to_full=total_missing,
    )
