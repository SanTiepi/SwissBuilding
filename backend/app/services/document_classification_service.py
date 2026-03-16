"""Auto-classify building documents by analyzing metadata and context."""

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.schemas.document_classification import (
    ClassificationSummary,
    DocumentClassification,
    MissingDocumentSuggestion,
)

VALID_CATEGORIES = {
    "diagnostic_report",
    "lab_result",
    "remediation_plan",
    "compliance_certificate",
    "insurance_doc",
    "legal_doc",
    "photo",
    "technical_plan",
    "invoice",
    "other",
}

ALL_POLLUTANTS = {"asbestos", "pcb", "lead", "hap", "radon"}

# Filename patterns → category (checked in order, first match wins)
_FILENAME_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(rapport|report|diagnostic)", re.IGNORECASE), "diagnostic_report"),
    (re.compile(r"(analyse|labo|laboratory|lab_result)", re.IGNORECASE), "lab_result"),
    (re.compile(r"(remediation|assainissement|decontamination)", re.IGNORECASE), "remediation_plan"),
    (re.compile(r"(compliance|conformit|certificat)", re.IGNORECASE), "compliance_certificate"),
    (re.compile(r"(assurance|insurance)", re.IGNORECASE), "insurance_doc"),
    (re.compile(r"(juridique|legal|contrat|contract)", re.IGNORECASE), "legal_doc"),
    (re.compile(r"(photo|img|image)", re.IGNORECASE), "photo"),
    (re.compile(r"(plan|drawing|schema)", re.IGNORECASE), "technical_plan"),
    (re.compile(r"(facture|invoice|rechnung)", re.IGNORECASE), "invoice"),
]

# Pollutant keyword patterns in filenames
_POLLUTANT_KEYWORDS: dict[str, re.Pattern[str]] = {
    "asbestos": re.compile(r"(amiante|asbestos|asbest)", re.IGNORECASE),
    "pcb": re.compile(r"(pcb|polychlorobiphenyl)", re.IGNORECASE),
    "lead": re.compile(r"(plomb|lead|blei)", re.IGNORECASE),
    "hap": re.compile(r"(hap|pah|hydrocarbure)", re.IGNORECASE),
    "radon": re.compile(r"(radon)", re.IGNORECASE),
}

# document_type field → category mapping
_DOCTYPE_MAP: dict[str, str] = {
    "diagnostic_report": "diagnostic_report",
    "lab_result": "lab_result",
    "remediation_plan": "remediation_plan",
    "compliance_certificate": "compliance_certificate",
    "insurance": "insurance_doc",
    "insurance_doc": "insurance_doc",
    "legal": "legal_doc",
    "legal_doc": "legal_doc",
    "photo": "photo",
    "technical_plan": "technical_plan",
    "plan": "technical_plan",
    "invoice": "invoice",
}

# file_type / mime_type → category fallback
_FILETYPE_MAP: dict[str, str] = {
    "application/pdf": "diagnostic_report",
    "pdf": "diagnostic_report",
    "image/jpeg": "photo",
    "image/png": "photo",
    "jpg": "photo",
    "jpeg": "photo",
    "png": "photo",
    "application/dxf": "technical_plan",
    "application/dwg": "technical_plan",
    "dwg": "technical_plan",
    "dxf": "technical_plan",
}


def _extract_pollutant_tags_from_filename(filename: str) -> list[str]:
    """Extract pollutant tags from filename keywords."""
    tags = []
    for pollutant, pattern in _POLLUTANT_KEYWORDS.items():
        if pattern.search(filename):
            tags.append(pollutant)
    return sorted(tags)


def _classify_single(
    doc: Document,
    diagnostic_pollutants: set[str],
) -> DocumentClassification:
    """Classify a single document based on metadata and context."""
    filename = doc.file_name or ""
    document_type = doc.document_type or ""
    mime_type = doc.mime_type or ""

    category = "other"
    confidence = 0.5

    # Priority 1: explicit document_type field
    if document_type and document_type.lower() in _DOCTYPE_MAP:
        category = _DOCTYPE_MAP[document_type.lower()]
        confidence = 0.9
    else:
        # Priority 2: filename pattern matching
        for pattern, cat in _FILENAME_PATTERNS:
            if pattern.search(filename):
                category = cat
                confidence = 0.7
                break
        else:
            # Priority 3: file_type / mime_type fallback
            mime_lower = mime_type.lower()
            if mime_lower in _FILETYPE_MAP:
                category = _FILETYPE_MAP[mime_lower]
                confidence = 0.5
            else:
                # Try extension from filename
                ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                if ext in _FILETYPE_MAP:
                    category = _FILETYPE_MAP[ext]
                    confidence = 0.5

    # Extract pollutant tags from filename
    pollutant_tags = _extract_pollutant_tags_from_filename(filename)

    # Merge pollutant tags from linked diagnostics
    for p in sorted(diagnostic_pollutants):
        if p not in pollutant_tags:
            pollutant_tags.append(p)
    pollutant_tags = sorted(set(pollutant_tags))

    # Build suggested tags
    suggested_tags = [category]
    if pollutant_tags:
        suggested_tags.extend(pollutant_tags)
    if mime_type:
        suggested_tags.append(mime_type.split("/")[-1] if "/" in mime_type else mime_type)
    suggested_tags = sorted(set(suggested_tags))

    return DocumentClassification(
        document_id=doc.id,
        filename=filename,
        document_category=category,
        pollutant_tags=pollutant_tags,
        confidence=confidence,
        suggested_tags=suggested_tags,
    )


async def _get_building_diagnostic_pollutants(db: AsyncSession, building_id: UUID) -> set[str]:
    """Get the set of pollutant types from diagnostics linked to a building."""
    result = await db.execute(select(Diagnostic.diagnostic_type).where(Diagnostic.building_id == building_id))
    types = {row[0] for row in result.all() if row[0]}
    # Normalize: diagnostic_type values match ALL_POLLUTANTS names
    return types & ALL_POLLUTANTS


async def classify_document(db: AsyncSession, document_id: UUID) -> DocumentClassification:
    """Classify a single document by its ID."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    pollutants = await _get_building_diagnostic_pollutants(db, doc.building_id)
    return _classify_single(doc, pollutants)


async def classify_building_documents(db: AsyncSession, building_id: UUID) -> list[DocumentClassification]:
    """Classify all documents for a building."""
    result = await db.execute(select(Document).where(Document.building_id == building_id))
    docs = result.scalars().all()

    pollutants = await _get_building_diagnostic_pollutants(db, building_id)
    return [_classify_single(doc, pollutants) for doc in docs]


async def get_classification_summary(db: AsyncSession, building_id: UUID) -> ClassificationSummary:
    """Aggregate classification results for a building."""
    classifications = await classify_building_documents(db, building_id)

    category_counts: dict[str, int] = {}
    found_pollutants: set[str] = set()

    for c in classifications:
        category_counts[c.document_category] = category_counts.get(c.document_category, 0) + 1
        found_pollutants.update(c.pollutant_tags)

    # Determine which pollutants the building deals with
    building_pollutants = await _get_building_diagnostic_pollutants(db, building_id)

    # Pollutant coverage: True if at least one document references it
    pollutant_coverage = {p: p in found_pollutants for p in sorted(building_pollutants or ALL_POLLUTANTS)}

    # Coverage gaps: essential categories that are missing
    essential_categories = {
        "diagnostic_report",
        "lab_result",
        "remediation_plan",
        "compliance_certificate",
    }
    coverage_gaps = sorted(essential_categories - set(category_counts.keys()))

    return ClassificationSummary(
        building_id=building_id,
        total_documents=len(classifications),
        category_counts=category_counts,
        pollutant_coverage=pollutant_coverage,
        coverage_gaps=coverage_gaps,
    )


async def suggest_missing_documents(db: AsyncSession, building_id: UUID) -> list[MissingDocumentSuggestion]:
    """Based on diagnostics and pollutants found, suggest missing documents."""
    classifications = await classify_building_documents(db, building_id)
    building_pollutants = await _get_building_diagnostic_pollutants(db, building_id)

    suggestions: list[MissingDocumentSuggestion] = []

    # Index: which categories exist per pollutant
    category_pollutant_pairs: set[tuple[str, str]] = set()
    categories_present: set[str] = set()
    for c in classifications:
        categories_present.add(c.document_category)
        for p in c.pollutant_tags:
            category_pollutant_pairs.add((c.document_category, p))

    # For each pollutant, check essential documents
    essential_per_pollutant = [
        ("diagnostic_report", "high", "No diagnostic report for {pollutant} found"),
        ("lab_result", "high", "No laboratory analysis for {pollutant} found"),
        ("remediation_plan", "medium", "No remediation plan for {pollutant} found"),
        ("compliance_certificate", "low", "No compliance certificate for {pollutant} found"),
    ]

    for pollutant in sorted(building_pollutants):
        for cat, priority, reason_tpl in essential_per_pollutant:
            if (cat, pollutant) not in category_pollutant_pairs:
                suggestions.append(
                    MissingDocumentSuggestion(
                        category=cat,
                        pollutant=pollutant,
                        reason=reason_tpl.format(pollutant=pollutant),
                        priority=priority,
                    )
                )

    # General suggestions (not pollutant-specific)
    if "insurance_doc" not in categories_present and building_pollutants:
        suggestions.append(
            MissingDocumentSuggestion(
                category="insurance_doc",
                pollutant=None,
                reason="No insurance document found for building with pollutant diagnostics",
                priority="low",
            )
        )

    return suggestions
