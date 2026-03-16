"""Authority pack generation service.

Assembles authority-ready evidence packs with structured sections covering
building identity, diagnostics, samples, compliance, actions, risk, interventions,
and document inventory.
"""

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.evidence_pack import EvidencePack
from app.models.intervention import Intervention
from app.models.zone import Zone
from app.schemas.authority_pack import (
    AuthorityPackConfig,
    AuthorityPackListItem,
    AuthorityPackResult,
    AuthorityPackSection,
)
from app.services.eco_clause_template_service import generate_eco_clauses

ALL_SECTION_TYPES = [
    "building_identity",
    "diagnostic_summary",
    "sample_results",
    "compliance_status",
    "action_plan",
    "risk_assessment",
    "intervention_history",
    "document_inventory",
]

_SECTION_NAMES = {
    "building_identity": "Identite du batiment",
    "diagnostic_summary": "Synthese des diagnostics",
    "sample_results": "Resultats des echantillons",
    "compliance_status": "Statut de conformite",
    "action_plan": "Plan d'actions",
    "risk_assessment": "Evaluation des risques",
    "intervention_history": "Historique des interventions",
    "document_inventory": "Inventaire des documents",
}


async def _fetch_building(db: AsyncSession, building_id: uuid.UUID) -> Building | None:
    result = await db.execute(select(Building).where(Building.id == building_id))
    return result.scalar_one_or_none()


async def _build_building_identity(db: AsyncSession, building: Building) -> AuthorityPackSection:
    """Build the building identity section."""
    zones_result = await db.execute(select(Zone).where(Zone.building_id == building.id))
    zones = zones_result.scalars().all()

    items: list[dict] = [
        {
            "field": "address",
            "value": f"{building.address}, {building.postal_code} {building.city}",
        },
        {"field": "canton", "value": building.canton},
        {"field": "egid", "value": building.egid},
        {"field": "construction_year", "value": building.construction_year},
        {"field": "building_type", "value": building.building_type},
        {"field": "zones_count", "value": len(list(zones))},
    ]

    # Completeness: how many core identity fields are present
    expected = ["address", "canton", "egid", "construction_year"]
    present = sum(1 for f in expected if getattr(building, f, None) is not None and getattr(building, f, None) != "")
    completeness = present / len(expected) if expected else 1.0

    return AuthorityPackSection(
        section_name=_SECTION_NAMES["building_identity"],
        section_type="building_identity",
        items=items,
        completeness=completeness,
    )


async def _build_diagnostic_summary(db: AsyncSession, building_id: uuid.UUID) -> AuthorityPackSection:
    """Build the diagnostic summary section."""
    result = await db.execute(
        select(Diagnostic).where(Diagnostic.building_id == building_id).order_by(Diagnostic.created_at.desc())
    )
    diagnostics = result.scalars().all()

    items = [
        {
            "diagnostic_id": str(d.id),
            "type": d.diagnostic_type,
            "status": d.status,
            "date_inspection": str(d.date_inspection) if d.date_inspection else None,
            "laboratory": d.laboratory,
        }
        for d in diagnostics
    ]

    # At least 1 diagnostic expected
    completeness = min(1.0, len(items) / 1.0) if True else 0.0

    return AuthorityPackSection(
        section_name=_SECTION_NAMES["diagnostic_summary"],
        section_type="diagnostic_summary",
        items=items,
        completeness=completeness,
        notes=f"{len(items)} diagnostic(s) enregistre(s)" if items else "Aucun diagnostic",
    )


async def _build_sample_results(db: AsyncSession, building_id: uuid.UUID) -> AuthorityPackSection:
    """Build the sample results section."""
    result = await db.execute(
        select(Diagnostic).options(selectinload(Diagnostic.samples)).where(Diagnostic.building_id == building_id)
    )
    diagnostics = result.scalars().all()

    items = []
    for diag in diagnostics:
        for s in diag.samples:
            items.append(
                {
                    "sample_id": str(s.id),
                    "sample_number": s.sample_number,
                    "pollutant_type": s.pollutant_type,
                    "concentration": s.concentration,
                    "unit": s.unit,
                    "threshold_exceeded": s.threshold_exceeded,
                    "risk_level": s.risk_level,
                    "material_category": s.material_category,
                }
            )

    # At least 1 sample expected for a meaningful pack
    completeness = min(1.0, len(items) / 1.0) if True else 0.0

    return AuthorityPackSection(
        section_name=_SECTION_NAMES["sample_results"],
        section_type="sample_results",
        items=items,
        completeness=completeness,
    )


async def _build_compliance_status(db: AsyncSession, building_id: uuid.UUID) -> AuthorityPackSection:
    """Build the compliance status section."""
    result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id))
    artefacts = result.scalars().all()

    items = [
        {
            "artefact_id": str(a.id),
            "artefact_type": a.artefact_type,
            "title": a.title,
            "status": a.status,
            "authority_name": a.authority_name,
            "legal_basis": a.legal_basis,
        }
        for a in artefacts
    ]

    completeness = min(1.0, len(items) / 1.0) if True else 0.0

    return AuthorityPackSection(
        section_name=_SECTION_NAMES["compliance_status"],
        section_type="compliance_status",
        items=items,
        completeness=completeness,
    )


async def _build_action_plan(db: AsyncSession, building_id: uuid.UUID) -> AuthorityPackSection:
    """Build the action plan section."""
    result = await db.execute(
        select(ActionItem)
        .where(ActionItem.building_id == building_id)
        .order_by(ActionItem.priority.desc(), ActionItem.created_at.desc())
    )
    actions = result.scalars().all()

    items = [
        {
            "action_id": str(a.id),
            "title": a.title,
            "action_type": a.action_type,
            "priority": a.priority,
            "status": a.status,
            "due_date": str(a.due_date) if a.due_date else None,
        }
        for a in actions
    ]

    completeness = min(1.0, len(items) / 1.0) if True else 0.0

    return AuthorityPackSection(
        section_name=_SECTION_NAMES["action_plan"],
        section_type="action_plan",
        items=items,
        completeness=completeness,
    )


async def _build_risk_assessment(db: AsyncSession, building_id: uuid.UUID) -> AuthorityPackSection:
    """Build the risk assessment section."""
    result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    risk_score = result.scalar_one_or_none()

    items: list[dict] = []
    if risk_score:
        items.append(
            {
                "overall_risk_level": risk_score.overall_risk_level,
                "confidence": risk_score.confidence,
                "asbestos_probability": risk_score.asbestos_probability,
                "pcb_probability": risk_score.pcb_probability,
                "lead_probability": risk_score.lead_probability,
                "hap_probability": risk_score.hap_probability,
                "radon_probability": risk_score.radon_probability,
                "data_source": risk_score.data_source,
            }
        )

    completeness = 1.0 if items else 0.0

    return AuthorityPackSection(
        section_name=_SECTION_NAMES["risk_assessment"],
        section_type="risk_assessment",
        items=items,
        completeness=completeness,
    )


async def _build_intervention_history(db: AsyncSession, building_id: uuid.UUID) -> AuthorityPackSection:
    """Build the intervention history section."""
    result = await db.execute(
        select(Intervention)
        .where(Intervention.building_id == building_id)
        .order_by(Intervention.date_start.desc().nulls_last())
    )
    interventions = result.scalars().all()

    items = [
        {
            "intervention_id": str(i.id),
            "type": i.intervention_type,
            "title": i.title,
            "status": i.status,
            "date_start": str(i.date_start) if i.date_start else None,
            "date_end": str(i.date_end) if i.date_end else None,
            "contractor_name": i.contractor_name,
        }
        for i in interventions
    ]

    # Interventions are optional; completeness is 1.0 if any exist, 0.5 if none
    completeness = 1.0 if items else 0.5

    return AuthorityPackSection(
        section_name=_SECTION_NAMES["intervention_history"],
        section_type="intervention_history",
        items=items,
        completeness=completeness,
    )


async def _build_document_inventory(db: AsyncSession, building_id: uuid.UUID) -> AuthorityPackSection:
    """Build the document inventory section."""
    result = await db.execute(
        select(Document).where(Document.building_id == building_id).order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()

    items = [
        {
            "document_id": str(d.id),
            "file_name": d.file_name,
            "document_type": d.document_type,
            "mime_type": d.mime_type,
            "file_size_bytes": d.file_size_bytes,
        }
        for d in documents
    ]

    completeness = min(1.0, len(items) / 1.0) if True else 0.0

    return AuthorityPackSection(
        section_name=_SECTION_NAMES["document_inventory"],
        section_type="document_inventory",
        items=items,
        completeness=completeness,
    )


_SECTION_BUILDERS = {
    "building_identity": _build_building_identity,
    "diagnostic_summary": _build_diagnostic_summary,
    "sample_results": _build_sample_results,
    "compliance_status": _build_compliance_status,
    "action_plan": _build_action_plan,
    "risk_assessment": _build_risk_assessment,
    "intervention_history": _build_intervention_history,
    "document_inventory": _build_document_inventory,
}


async def generate_authority_pack(
    db: AsyncSession,
    building_id: uuid.UUID,
    config: AuthorityPackConfig,
    user_id: uuid.UUID,
) -> AuthorityPackResult:
    """Assemble a full authority pack for a building.

    Creates an EvidencePack record and returns structured results.
    """
    building = await _fetch_building(db, building_id)
    if not building:
        raise ValueError("Building not found")

    canton = config.canton or building.canton or "VD"
    section_types = config.include_sections or ALL_SECTION_TYPES

    # Validate requested section types
    warnings: list[str] = []
    valid_section_types = [s for s in section_types if s in _SECTION_BUILDERS]
    for s in section_types:
        if s not in _SECTION_BUILDERS:
            warnings.append(f"Unknown section type: {s}")

    # Build sections
    sections: list[AuthorityPackSection] = []
    for section_type in valid_section_types:
        builder = _SECTION_BUILDERS[section_type]
        if section_type == "building_identity":
            section = await builder(db, building)
        else:
            section = await builder(db, building_id)
        sections.append(section)

    # Compute overall completeness
    if sections:
        overall_completeness = sum(s.completeness for s in sections) / len(sections)
    else:
        overall_completeness = 0.0

    # Optionally include eco clauses (renovation context by default)
    eco_clause_summary: dict | None = None
    if config.include_sections is None or "eco_clauses" in (config.include_sections or []):
        try:
            eco_payload = await generate_eco_clauses(building_id, "renovation", db)
            eco_clause_summary = {
                "total_clauses": eco_payload.total_clauses,
                "detected_pollutants": eco_payload.detected_pollutants,
                "section_count": len(eco_payload.sections),
            }
        except ValueError:
            pass  # Building not found handled above; safe to skip

    generated_at = datetime.now(UTC)
    pack_id = uuid.uuid4()

    # Create EvidencePack record
    pack_record = EvidencePack(
        id=pack_id,
        building_id=building_id,
        pack_type="authority_pack",
        title=f"Authority Pack - {canton} - {building.address}",
        status="complete",
        created_by=user_id,
        assembled_at=generated_at,
        required_sections_json=[
            {"section_type": s.section_type, "label": s.section_name, "required": True, "included": True}
            for s in sections
        ],
        notes=json.dumps(
            {
                "canton": canton,
                "overall_completeness": overall_completeness,
                "total_sections": len(sections),
                "warnings": warnings,
                "language": config.language,
                "include_photos": config.include_photos,
                "sections": [
                    {
                        "section_type": s.section_type,
                        "section_name": s.section_name,
                        "completeness": s.completeness,
                        "item_count": len(s.items),
                    }
                    for s in sections
                ],
                "eco_clauses": eco_clause_summary,
            }
        ),
    )
    db.add(pack_record)
    await db.commit()

    return AuthorityPackResult(
        pack_id=pack_id,
        building_id=building_id,
        canton=canton,
        sections=sections,
        total_sections=len(sections),
        overall_completeness=overall_completeness,
        generated_at=generated_at,
        warnings=warnings,
    )


async def list_authority_packs(db: AsyncSession, building_id: uuid.UUID) -> list[AuthorityPackListItem]:
    """List previous authority packs for a building."""
    result = await db.execute(
        select(EvidencePack)
        .where(
            EvidencePack.building_id == building_id,
            EvidencePack.pack_type == "authority_pack",
        )
        .order_by(EvidencePack.created_at.desc())
    )
    packs = result.scalars().all()

    items: list[AuthorityPackListItem] = []
    for pack in packs:
        # Parse stored metadata to extract canton and completeness
        canton = "VD"
        overall_completeness = 0.0
        if pack.notes:
            try:
                meta = json.loads(pack.notes)
                canton = meta.get("canton", "VD")
                overall_completeness = meta.get("overall_completeness", 0.0)
            except (json.JSONDecodeError, TypeError):
                pass

        items.append(
            AuthorityPackListItem(
                pack_id=pack.id,
                building_id=pack.building_id,
                canton=canton,
                overall_completeness=overall_completeness,
                generated_at=pack.created_at,
                status=pack.status,
            )
        )

    return items


async def get_authority_pack(db: AsyncSession, pack_id: uuid.UUID) -> AuthorityPackResult | None:
    """Retrieve a previously generated authority pack by ID."""
    result = await db.execute(
        select(EvidencePack).where(
            EvidencePack.id == pack_id,
            EvidencePack.pack_type == "authority_pack",
        )
    )
    pack = result.scalar_one_or_none()
    if not pack:
        return None

    # Reconstruct result from stored metadata
    canton = "VD"
    overall_completeness = 0.0
    warnings: list[str] = []
    sections: list[AuthorityPackSection] = []

    if pack.notes:
        try:
            meta = json.loads(pack.notes)
            canton = meta.get("canton", "VD")
            overall_completeness = meta.get("overall_completeness", 0.0)
            warnings = meta.get("warnings", [])
            for s in meta.get("sections", []):
                sections.append(
                    AuthorityPackSection(
                        section_name=s.get("section_name", ""),
                        section_type=s.get("section_type", ""),
                        items=[],  # Items not stored in metadata for size reasons
                        completeness=s.get("completeness", 0.0),
                    )
                )
        except (json.JSONDecodeError, TypeError):
            pass

    return AuthorityPackResult(
        pack_id=pack.id,
        building_id=pack.building_id,
        canton=canton,
        sections=sections,
        total_sections=len(sections),
        overall_completeness=overall_completeness,
        generated_at=pack.created_at,
        warnings=warnings,
    )
