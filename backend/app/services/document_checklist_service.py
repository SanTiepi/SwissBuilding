"""Document checklist service (GED C) — missing documents detection.

For each building context, defines what documents are EXPECTED based on
construction year, pollutant risk, tenancy, etc., then compares with
what's PRESENT in the documents table.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.document import Document

# ---------------------------------------------------------------------------
# Requirement definitions
# ---------------------------------------------------------------------------

BASE_REQUIREMENTS: list[dict[str, Any]] = [
    {
        "type": "asbestos_report",
        "label_key": "doc_checklist.type_asbestos_report",
        "label_fallback": "Rapport amiante",
        "condition": "construction_year_lt_1990",
        "importance": "critical",
        "legal_basis": "OTConst Art. 60a",
        "recommendation_key": "doc_checklist.rec_asbestos",
        "recommendation_fallback": "Faire realiser un diagnostic amiante avant tous travaux",
    },
    {
        "type": "pcb_report",
        "label_key": "doc_checklist.type_pcb_report",
        "label_fallback": "Rapport PCB",
        "condition": "construction_year_1955_1975",
        "importance": "critical",
        "legal_basis": "ORRChim Annexe 2.15",
        "recommendation_key": "doc_checklist.rec_pcb",
        "recommendation_fallback": "Faire analyser les joints, condensateurs et peintures pour PCB",
    },
    {
        "type": "lead_report",
        "label_key": "doc_checklist.type_lead_report",
        "label_fallback": "Rapport plomb",
        "condition": "construction_year_lt_2006",
        "importance": "high",
        "legal_basis": "ORRChim Annexe 2.18",
        "recommendation_key": "doc_checklist.rec_lead",
        "recommendation_fallback": "Faire analyser les peintures et canalisations pour le plomb",
    },
    {
        "type": "hap_report",
        "label_key": "doc_checklist.type_hap_report",
        "label_fallback": "Rapport HAP",
        "condition": "construction_year_lt_1990",
        "importance": "high",
        "legal_basis": "OTConst Art. 82",
        "recommendation_key": "doc_checklist.rec_hap",
        "recommendation_fallback": "Faire analyser les enrobes, colles et etancheites pour HAP",
    },
    {
        "type": "radon_measurement",
        "label_key": "doc_checklist.type_radon",
        "label_fallback": "Mesure radon",
        "condition": "always",
        "importance": "medium",
        "legal_basis": "ORaP Art. 110",
        "recommendation_key": "doc_checklist.rec_radon",
        "recommendation_fallback": "Realiser une mesure du radon dans les locaux occupes au sous-sol ou rez",
    },
    {
        "type": "cecb_certificate",
        "label_key": "doc_checklist.type_cecb",
        "label_fallback": "Certificat CECB",
        "condition": "always",
        "importance": "medium",
        "legal_basis": "LEn cantonal",
        "recommendation_key": "doc_checklist.rec_cecb",
        "recommendation_fallback": "Obtenir un certificat energetique CECB/GEAK",
    },
    {
        "type": "building_permit",
        "label_key": "doc_checklist.type_building_permit",
        "label_fallback": "Permis de construire",
        "condition": "always",
        "importance": "low",
        "legal_basis": None,
        "recommendation_key": "doc_checklist.rec_building_permit",
        "recommendation_fallback": "Recuperer le permis de construire aupres de la commune",
    },
    {
        "type": "insurance_policy",
        "label_key": "doc_checklist.type_insurance",
        "label_fallback": "Police d'assurance batiment",
        "condition": "always",
        "importance": "high",
        "legal_basis": None,
        "recommendation_key": "doc_checklist.rec_insurance",
        "recommendation_fallback": "Verifier la police d'assurance batiment et son renouvellement",
    },
    {
        "type": "management_report",
        "label_key": "doc_checklist.type_management_report",
        "label_fallback": "Rapport de gestion",
        "condition": "has_tenants",
        "importance": "medium",
        "legal_basis": None,
        "recommendation_key": "doc_checklist.rec_management_report",
        "recommendation_fallback": "Obtenir le dernier rapport de gestion de la regie",
    },
    {
        "type": "fire_safety_report",
        "label_key": "doc_checklist.type_fire_safety",
        "label_fallback": "Rapport securite incendie",
        "condition": "always",
        "importance": "medium",
        "legal_basis": "AEAI",
        "recommendation_key": "doc_checklist.rec_fire_safety",
        "recommendation_fallback": "Faire realiser un controle de securite incendie",
    },
]


# ---------------------------------------------------------------------------
# Condition evaluators
# ---------------------------------------------------------------------------


def _evaluate_condition(condition: str, building: Building) -> bool:
    """Evaluate a requirement condition against building context."""
    year = building.construction_year

    if condition == "always":
        return True

    if condition == "construction_year_lt_1990":
        return year is not None and year < 1990

    if condition == "construction_year_1955_1975":
        return year is not None and 1955 <= year <= 1975

    if condition == "construction_year_lt_2006":
        return year is not None and year < 2006

    if condition == "has_tenants":
        # Heuristic: residential/commercial multi-tenant buildings
        btype = (building.building_type or "").lower()
        return any(kw in btype for kw in ("residential", "commercial", "mixed", "locatif", "immeuble"))

    return False


# ---------------------------------------------------------------------------
# Document type matching
# ---------------------------------------------------------------------------

# Map checklist types to possible document_type values in the DB
_TYPE_ALIASES: dict[str, set[str]] = {
    "asbestos_report": {"asbestos_report", "diagnostic_report", "amiante", "asbestos"},
    "pcb_report": {"pcb_report", "diagnostic_report", "pcb"},
    "lead_report": {"lead_report", "diagnostic_report", "lead", "plomb"},
    "hap_report": {"hap_report", "diagnostic_report", "hap"},
    "radon_measurement": {"radon_measurement", "radon", "radon_report"},
    "cecb_certificate": {"cecb_certificate", "cecb", "geak", "cece", "energy_certificate"},
    "building_permit": {"building_permit", "permit", "permis"},
    "insurance_policy": {"insurance_policy", "insurance", "assurance"},
    "management_report": {"management_report", "management", "gestion"},
    "fire_safety_report": {"fire_safety_report", "fire_safety", "incendie", "aeai"},
}


def _doc_matches_type(doc_type: str | None, req_type: str) -> bool:
    """Check if a document's type matches a requirement type."""
    if not doc_type:
        return False
    aliases = _TYPE_ALIASES.get(req_type, {req_type})
    return doc_type.lower() in aliases


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def evaluate_document_checklist(
    db: AsyncSession,
    building_id: UUID,
) -> dict[str, Any]:
    """Evaluate the document checklist for a building.

    Returns a structured result with required documents, their status,
    completion percentage, and critical missing items.
    """
    # Load building
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError(f"Building {building_id} not found")

    # Load all documents for this building
    doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
    documents = list(doc_result.scalars().all())

    items: list[dict[str, Any]] = []
    critical_missing: list[str] = []
    total_required = 0
    total_present = 0

    for req in BASE_REQUIREMENTS:
        applicable = _evaluate_condition(req["condition"], building)

        if not applicable:
            items.append(
                {
                    "document_type": req["type"],
                    "label": req["label_fallback"],
                    "importance": req["importance"],
                    "legal_basis": req.get("legal_basis"),
                    "status": "not_applicable",
                    "document_id": None,
                    "uploaded_at": None,
                    "recommendation": None,
                }
            )
            continue

        total_required += 1

        # Find matching document
        matching_doc = None
        for doc in documents:
            if _doc_matches_type(doc.document_type, req["type"]):
                matching_doc = doc
                break

        if matching_doc:
            total_present += 1
            items.append(
                {
                    "document_type": req["type"],
                    "label": req["label_fallback"],
                    "importance": req["importance"],
                    "legal_basis": req.get("legal_basis"),
                    "status": "present",
                    "document_id": str(matching_doc.id),
                    "uploaded_at": matching_doc.created_at.isoformat() if matching_doc.created_at else None,
                    "recommendation": None,
                }
            )
        else:
            status = "missing"
            items.append(
                {
                    "document_type": req["type"],
                    "label": req["label_fallback"],
                    "importance": req["importance"],
                    "legal_basis": req.get("legal_basis"),
                    "status": status,
                    "document_id": None,
                    "uploaded_at": None,
                    "recommendation": req["recommendation_fallback"],
                }
            )
            if req["importance"] == "critical":
                critical_missing.append(req["type"])

    completion_pct = round((total_present / total_required * 100) if total_required > 0 else 100.0, 1)

    return {
        "building_id": str(building_id),
        "total_required": total_required,
        "total_present": total_present,
        "completion_pct": completion_pct,
        "items": items,
        "critical_missing": critical_missing,
        "evaluated_at": datetime.now(UTC).isoformat(),
    }
