"""Handoff pack generation service.

Generates structured handoff packs for three transition points:
1. Diagnostician → Property manager (findings, risk, actions, costs, regulations, timeline)
2. Property manager → Contractor (scope, pollutants, safety, access, materials, disposal, docs)
3. Property manager → Authority (compliance, reports, remediation, waste, parties, timeline)
Also validates completeness of required data for each handoff type.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.action_item import ActionItem
from app.models.assignment import Assignment
from app.models.building import Building
from app.models.building_element import BuildingElement
from app.models.building_risk_score import BuildingRiskScore
from app.models.compliance_artefact import ComplianceArtefact
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.material import Material
from app.models.sample import Sample
from app.models.zone import Zone
from app.schemas.handoff_pack import (
    AuthorityHandoffResult,
    ContractorHandoffResult,
    DiagnosticHandoffResult,
    HandoffSection,
    HandoffValidationResult,
    HandoffValidationWarning,
)

# ---------------------------------------------------------------------------
# Swiss regulatory reference constants
# ---------------------------------------------------------------------------
_REGULATORY_REFS = {
    "asbestos": "OTConst Art. 60a, 82-86; CFST 6503",
    "pcb": "ORRChim Annexe 2.15 (>50 mg/kg)",
    "lead": "ORRChim Annexe 2.18 (>5000 mg/kg)",
    "hap": "OPair / LPE",
    "radon": "ORaP Art. 110 (300/1000 Bq/m3)",
}

_WASTE_CATEGORIES = {
    "asbestos": "type_e / special",
    "pcb": "special",
    "lead": "type_b / special",
    "hap": "special",
    "radon": "N/A",
}

_CFST_LABELS = {
    "minor": "Travaux mineurs (cat. minor)",
    "medium": "Travaux moyens (cat. medium)",
    "major": "Travaux majeurs (cat. major)",
}


async def _fetch_building(db: AsyncSession, building_id: uuid.UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise ValueError("Building not found")
    return building


async def _fetch_diagnostics_with_samples(db: AsyncSession, building_id: uuid.UUID) -> list[Diagnostic]:
    result = await db.execute(
        select(Diagnostic)
        .options(selectinload(Diagnostic.samples))
        .where(Diagnostic.building_id == building_id)
        .order_by(Diagnostic.created_at.desc())
    )
    return list(result.scalars().all())


async def _fetch_actions(db: AsyncSession, building_id: uuid.UUID) -> list[ActionItem]:
    result = await db.execute(
        select(ActionItem)
        .where(ActionItem.building_id == building_id)
        .order_by(ActionItem.priority.desc(), ActionItem.created_at.desc())
    )
    return list(result.scalars().all())


async def _fetch_risk_score(db: AsyncSession, building_id: uuid.UUID) -> BuildingRiskScore | None:
    result = await db.execute(select(BuildingRiskScore).where(BuildingRiskScore.building_id == building_id))
    return result.scalar_one_or_none()


async def _fetch_interventions(db: AsyncSession, building_id: uuid.UUID) -> list[Intervention]:
    result = await db.execute(
        select(Intervention)
        .where(Intervention.building_id == building_id)
        .order_by(Intervention.date_start.desc().nulls_last())
    )
    return list(result.scalars().all())


async def _fetch_documents(db: AsyncSession, building_id: uuid.UUID) -> list[Document]:
    result = await db.execute(
        select(Document).where(Document.building_id == building_id).order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def _fetch_zones(db: AsyncSession, building_id: uuid.UUID) -> list[Zone]:
    result = await db.execute(select(Zone).where(Zone.building_id == building_id))
    return list(result.scalars().all())


async def _fetch_materials(db: AsyncSession, building_id: uuid.UUID) -> list[Material]:
    result = await db.execute(
        select(Material)
        .join(BuildingElement, Material.element_id == BuildingElement.id)
        .join(Zone, BuildingElement.zone_id == Zone.id)
        .where(Zone.building_id == building_id)
    )
    return list(result.scalars().all())


async def _fetch_compliance_artefacts(db: AsyncSession, building_id: uuid.UUID) -> list[ComplianceArtefact]:
    result = await db.execute(select(ComplianceArtefact).where(ComplianceArtefact.building_id == building_id))
    return list(result.scalars().all())


async def _fetch_assignments(db: AsyncSession, building_id: uuid.UUID) -> list[Assignment]:
    result = await db.execute(
        select(Assignment).where(
            Assignment.target_type == "building",
            Assignment.target_id == building_id,
        )
    )
    return list(result.scalars().all())


def _all_samples(diagnostics: list[Diagnostic]) -> list[Sample]:
    samples: list[Sample] = []
    for d in diagnostics:
        samples.extend(d.samples)
    return samples


# ===================================================================
# FN1: Diagnostic handoff (diagnostician → property manager)
# ===================================================================


async def generate_diagnostic_handoff(db: AsyncSession, building_id: uuid.UUID) -> DiagnosticHandoffResult:
    """Generate handoff pack for diagnostician → property manager transition.

    Structured for a non-technical audience: plain-language findings,
    risk levels, recommended actions, cost estimates, regulatory obligations,
    and a suggested timeline.
    """
    await _fetch_building(db, building_id)  # validate exists
    diagnostics = await _fetch_diagnostics_with_samples(db, building_id)
    actions = await _fetch_actions(db, building_id)
    risk_score = await _fetch_risk_score(db, building_id)
    interventions = await _fetch_interventions(db, building_id)

    samples = _all_samples(diagnostics)
    warnings: list[str] = []

    # -- Findings summary --
    findings_items: list[dict] = []
    for d in diagnostics:
        positive_samples = [s for s in d.samples if s.threshold_exceeded]
        findings_items.append(
            {
                "diagnostic_type": d.diagnostic_type,
                "status": d.status,
                "date_inspection": str(d.date_inspection) if d.date_inspection else None,
                "conclusion": d.conclusion,
                "summary": d.summary,
                "total_samples": len(d.samples),
                "positive_samples": len(positive_samples),
            }
        )
    if not diagnostics:
        warnings.append("Aucun diagnostic enregistre")
    findings_completeness = min(1.0, len(findings_items))
    findings = HandoffSection(
        section_name="Synthese des constats",
        section_type="findings_summary",
        items=findings_items,
        completeness=findings_completeness,
    )

    # -- Risk levels --
    risk_items: list[dict] = []
    if risk_score:
        risk_items.append(
            {
                "overall_risk_level": risk_score.overall_risk_level,
                "confidence": risk_score.confidence,
                "asbestos_probability": risk_score.asbestos_probability,
                "pcb_probability": risk_score.pcb_probability,
                "lead_probability": risk_score.lead_probability,
                "hap_probability": risk_score.hap_probability,
                "radon_probability": risk_score.radon_probability,
            }
        )
    # Add per-sample risk
    for s in samples:
        if s.threshold_exceeded:
            risk_items.append(
                {
                    "type": "sample_risk",
                    "pollutant_type": s.pollutant_type,
                    "risk_level": s.risk_level,
                    "concentration": s.concentration,
                    "unit": s.unit,
                    "location": f"{s.location_floor or ''} / {s.location_room or ''}".strip(" /"),
                }
            )
    risk_completeness = 1.0 if risk_score else (0.5 if risk_items else 0.0)
    risk_section = HandoffSection(
        section_name="Niveaux de risque",
        section_type="risk_levels",
        items=risk_items,
        completeness=risk_completeness,
    )

    # -- Recommended actions --
    action_items: list[dict] = [
        {
            "title": a.title,
            "action_type": a.action_type,
            "priority": a.priority,
            "status": a.status,
            "description": a.description,
            "due_date": str(a.due_date) if a.due_date else None,
        }
        for a in actions
    ]
    actions_completeness = min(1.0, len(action_items)) if samples else 0.5
    actions_section = HandoffSection(
        section_name="Actions recommandees",
        section_type="recommended_actions",
        items=action_items,
        completeness=actions_completeness,
    )

    # -- Cost estimates --
    cost_items: list[dict] = []
    for i in interventions:
        if i.cost_chf is not None:
            cost_items.append(
                {
                    "intervention_type": i.intervention_type,
                    "title": i.title,
                    "cost_chf": i.cost_chf,
                    "status": i.status,
                }
            )
    # Also extract from action metadata if present
    for a in actions:
        if a.metadata_json and isinstance(a.metadata_json, dict):
            est = a.metadata_json.get("estimated_cost_chf")
            if est is not None:
                cost_items.append(
                    {
                        "source": "action_estimate",
                        "title": a.title,
                        "cost_chf": est,
                    }
                )
    cost_completeness = min(1.0, len(cost_items)) if cost_items else 0.0
    cost_section = HandoffSection(
        section_name="Estimations de couts",
        section_type="cost_estimates",
        items=cost_items,
        completeness=cost_completeness,
        notes="Les estimations sont indicatives et doivent etre confirmees par un entrepreneur."
        if cost_items
        else None,
    )

    # -- Regulatory obligations --
    pollutant_types_found = {s.pollutant_type for s in samples if s.threshold_exceeded and s.pollutant_type}
    reg_items: list[dict] = []
    for pt in sorted(pollutant_types_found):
        reg_items.append(
            {
                "pollutant_type": pt,
                "regulation": _REGULATORY_REFS.get(pt, "Voir reglementation cantonale"),
                "waste_category": _WASTE_CATEGORIES.get(pt, "A determiner"),
            }
        )
    # SUVA notifications
    for d in diagnostics:
        if d.suva_notification_required:
            reg_items.append(
                {
                    "type": "suva_notification",
                    "diagnostic_type": d.diagnostic_type,
                    "required": True,
                    "notification_date": str(d.suva_notification_date) if d.suva_notification_date else None,
                }
            )
    reg_completeness = 1.0 if reg_items else (0.5 if not pollutant_types_found else 0.0)
    reg_section = HandoffSection(
        section_name="Obligations reglementaires",
        section_type="regulatory_obligations",
        items=reg_items,
        completeness=reg_completeness,
    )

    # -- Timeline --
    timeline_items: list[dict] = []
    for a in actions:
        if a.due_date:
            timeline_items.append(
                {
                    "type": "action_deadline",
                    "title": a.title,
                    "due_date": str(a.due_date),
                    "priority": a.priority,
                    "status": a.status,
                }
            )
    for i in interventions:
        if i.date_start or i.date_end:
            timeline_items.append(
                {
                    "type": "intervention",
                    "title": i.title,
                    "date_start": str(i.date_start) if i.date_start else None,
                    "date_end": str(i.date_end) if i.date_end else None,
                    "status": i.status,
                }
            )
    timeline_completeness = min(1.0, len(timeline_items)) if timeline_items else 0.0
    timeline_section = HandoffSection(
        section_name="Calendrier",
        section_type="timeline",
        items=timeline_items,
        completeness=timeline_completeness,
    )

    sections = [findings, risk_section, actions_section, cost_section, reg_section, timeline_section]
    overall = sum(s.completeness for s in sections) / len(sections) if sections else 0.0

    return DiagnosticHandoffResult(
        building_id=building_id,
        generated_at=datetime.now(UTC),
        findings_summary=findings,
        risk_levels=risk_section,
        recommended_actions=actions_section,
        cost_estimates=cost_section,
        regulatory_obligations=reg_section,
        timeline=timeline_section,
        overall_completeness=overall,
        warnings=warnings,
    )


# ===================================================================
# FN2: Contractor handoff (property manager → contractor)
# ===================================================================


async def generate_contractor_handoff(db: AsyncSession, building_id: uuid.UUID) -> ContractorHandoffResult:
    """Generate handoff pack for property manager → contractor transition.

    Structured for technical execution: work scope, pollutant map, safety
    requirements, access constraints, material quantities, disposal
    requirements, and reference documents.
    """
    building = await _fetch_building(db, building_id)
    diagnostics = await _fetch_diagnostics_with_samples(db, building_id)
    actions = await _fetch_actions(db, building_id)
    zones = await _fetch_zones(db, building_id)
    materials = await _fetch_materials(db, building_id)
    documents = await _fetch_documents(db, building_id)
    interventions = await _fetch_interventions(db, building_id)

    samples = _all_samples(diagnostics)
    warnings: list[str] = []

    # -- Work scope --
    scope_items: list[dict] = []
    for a in actions:
        if a.status in ("open", "in_progress"):
            scope_items.append(
                {
                    "title": a.title,
                    "action_type": a.action_type,
                    "priority": a.priority,
                    "description": a.description,
                    "due_date": str(a.due_date) if a.due_date else None,
                }
            )
    for i in interventions:
        if i.status in ("planned", "in_progress"):
            scope_items.append(
                {
                    "type": "planned_intervention",
                    "title": i.title,
                    "intervention_type": i.intervention_type,
                    "description": i.description,
                    "date_start": str(i.date_start) if i.date_start else None,
                    "date_end": str(i.date_end) if i.date_end else None,
                }
            )
    if not scope_items:
        warnings.append("Aucun travail planifie")
    scope_completeness = min(1.0, len(scope_items)) if scope_items else 0.0
    work_scope = HandoffSection(
        section_name="Perimetre des travaux",
        section_type="work_scope",
        items=scope_items,
        completeness=scope_completeness,
    )

    # -- Pollutant map --
    pollutant_items: list[dict] = []
    for s in samples:
        if s.threshold_exceeded:
            pollutant_items.append(
                {
                    "sample_number": s.sample_number,
                    "pollutant_type": s.pollutant_type,
                    "concentration": s.concentration,
                    "unit": s.unit,
                    "risk_level": s.risk_level,
                    "cfst_work_category": s.cfst_work_category,
                    "location_floor": s.location_floor,
                    "location_room": s.location_room,
                    "location_detail": s.location_detail,
                    "material_category": s.material_category,
                    "material_description": s.material_description,
                    "material_state": s.material_state,
                }
            )
    pollutant_completeness = min(1.0, len(pollutant_items)) if pollutant_items else 0.0
    pollutant_section = HandoffSection(
        section_name="Cartographie des polluants",
        section_type="pollutant_map",
        items=pollutant_items,
        completeness=pollutant_completeness,
    )

    # -- Safety requirements --
    safety_items: list[dict] = []
    cfst_categories = {s.cfst_work_category for s in samples if s.cfst_work_category}
    for cat in sorted(cfst_categories):
        safety_items.append(
            {
                "cfst_category": cat,
                "label": _CFST_LABELS.get(cat, cat),
                "regulation": "CFST 6503",
            }
        )
    # SUVA requirements
    suva_required = any(d.suva_notification_required for d in diagnostics)
    if suva_required:
        safety_items.append(
            {
                "type": "suva_notification",
                "required": True,
                "description": "Notification SUVA obligatoire avant travaux",
            }
        )
    safety_completeness = min(1.0, len(safety_items)) if safety_items else 0.5
    safety_section = HandoffSection(
        section_name="Exigences de securite",
        section_type="safety_requirements",
        items=safety_items,
        completeness=safety_completeness,
    )

    # -- Access constraints --
    access_items: list[dict] = []
    for z in zones:
        access_items.append(
            {
                "zone_id": str(z.id),
                "zone_type": z.zone_type,
                "name": z.name,
                "floor_number": z.floor_number,
            }
        )
    access_items.append(
        {
            "type": "building_info",
            "address": f"{building.address}, {building.postal_code} {building.city}",
            "floors_above": building.floors_above,
            "floors_below": building.floors_below,
            "surface_area_m2": building.surface_area_m2,
        }
    )
    access_completeness = 1.0 if zones else 0.5
    access_section = HandoffSection(
        section_name="Contraintes d'acces",
        section_type="access_constraints",
        items=access_items,
        completeness=access_completeness,
    )

    # -- Material quantities --
    material_items: list[dict] = []
    for m in materials:
        if m.contains_pollutant:
            material_items.append(
                {
                    "material_type": m.material_type,
                    "name": m.name,
                    "pollutant_type": m.pollutant_type,
                    "pollutant_confirmed": m.pollutant_confirmed,
                    "installation_year": m.installation_year,
                }
            )
    mat_completeness = min(1.0, len(material_items)) if material_items else 0.0
    material_section = HandoffSection(
        section_name="Quantites de materiaux",
        section_type="material_quantities",
        items=material_items,
        completeness=mat_completeness,
    )

    # -- Disposal requirements --
    disposal_items: list[dict] = []
    pollutant_types_found = {s.pollutant_type for s in samples if s.threshold_exceeded and s.pollutant_type}
    for pt in sorted(pollutant_types_found):
        matching_samples = [s for s in samples if s.pollutant_type == pt and s.threshold_exceeded]
        disposal_items.append(
            {
                "pollutant_type": pt,
                "waste_category": _WASTE_CATEGORIES.get(pt, "A determiner"),
                "sample_count": len(matching_samples),
                "waste_disposal_types": list(
                    {s.waste_disposal_type for s in matching_samples if s.waste_disposal_type}
                ),
                "regulation": _REGULATORY_REFS.get(pt, ""),
            }
        )
    disposal_completeness = min(1.0, len(disposal_items)) if disposal_items else 0.0
    disposal_section = HandoffSection(
        section_name="Exigences d'elimination",
        section_type="disposal_requirements",
        items=disposal_items,
        completeness=disposal_completeness,
    )

    # -- Reference documents --
    doc_items: list[dict] = [
        {
            "document_id": str(d.id),
            "file_name": d.file_name,
            "document_type": d.document_type,
            "description": d.description,
        }
        for d in documents
    ]
    doc_completeness = min(1.0, len(doc_items)) if doc_items else 0.0
    doc_section = HandoffSection(
        section_name="Documents de reference",
        section_type="reference_documents",
        items=doc_items,
        completeness=doc_completeness,
    )

    sections = [
        work_scope,
        pollutant_section,
        safety_section,
        access_section,
        material_section,
        disposal_section,
        doc_section,
    ]
    overall = sum(s.completeness for s in sections) / len(sections)

    return ContractorHandoffResult(
        building_id=building_id,
        generated_at=datetime.now(UTC),
        work_scope=work_scope,
        pollutant_map=pollutant_section,
        safety_requirements=safety_section,
        access_constraints=access_section,
        material_quantities=material_section,
        disposal_requirements=disposal_section,
        reference_documents=doc_section,
        overall_completeness=overall,
        warnings=warnings,
    )


# ===================================================================
# FN3: Authority handoff (property manager → authority)
# ===================================================================


async def generate_authority_handoff(db: AsyncSession, building_id: uuid.UUID) -> AuthorityHandoffResult:
    """Generate handoff pack for property manager → authority transition.

    Structured for regulatory review: compliance status per regulation,
    diagnostic reports summary, remediation plan, waste management plan,
    responsible parties, and timeline commitments.
    """
    building = await _fetch_building(db, building_id)
    diagnostics = await _fetch_diagnostics_with_samples(db, building_id)
    actions = await _fetch_actions(db, building_id)
    interventions = await _fetch_interventions(db, building_id)
    artefacts = await _fetch_compliance_artefacts(db, building_id)
    assignments = await _fetch_assignments(db, building_id)

    samples = _all_samples(diagnostics)
    warnings: list[str] = []

    # -- Compliance status --
    compliance_items: list[dict] = []
    for a in artefacts:
        compliance_items.append(
            {
                "artefact_type": a.artefact_type,
                "title": a.title,
                "status": a.status,
                "authority_name": a.authority_name,
                "legal_basis": a.legal_basis,
            }
        )
    # Add per-pollutant regulatory status from samples
    pollutant_types = {s.pollutant_type for s in samples if s.pollutant_type}
    for pt in sorted(pollutant_types):
        exceeded = any(s.threshold_exceeded for s in samples if s.pollutant_type == pt)
        compliance_items.append(
            {
                "type": "pollutant_regulation",
                "pollutant_type": pt,
                "regulation": _REGULATORY_REFS.get(pt, ""),
                "threshold_exceeded": exceeded,
                "status": "non_conforme" if exceeded else "conforme",
            }
        )
    compliance_completeness = min(1.0, len(compliance_items)) if compliance_items else 0.0
    compliance_section = HandoffSection(
        section_name="Statut de conformite",
        section_type="compliance_status",
        items=compliance_items,
        completeness=compliance_completeness,
    )

    # -- Diagnostic reports summary --
    report_items: list[dict] = []
    for d in diagnostics:
        positive = [s for s in d.samples if s.threshold_exceeded]
        report_items.append(
            {
                "diagnostic_id": str(d.id),
                "diagnostic_type": d.diagnostic_type,
                "status": d.status,
                "date_inspection": str(d.date_inspection) if d.date_inspection else None,
                "date_report": str(d.date_report) if d.date_report else None,
                "laboratory": d.laboratory,
                "laboratory_report_number": d.laboratory_report_number,
                "total_samples": len(d.samples),
                "positive_samples": len(positive),
                "conclusion": d.conclusion,
            }
        )
    if not diagnostics:
        warnings.append("Aucun rapport de diagnostic")
    report_completeness = min(1.0, len(report_items)) if report_items else 0.0
    report_section = HandoffSection(
        section_name="Rapports de diagnostic",
        section_type="diagnostic_reports",
        items=report_items,
        completeness=report_completeness,
    )

    # -- Remediation plan --
    remediation_items: list[dict] = []
    for i in interventions:
        remediation_items.append(
            {
                "intervention_id": str(i.id),
                "intervention_type": i.intervention_type,
                "title": i.title,
                "status": i.status,
                "date_start": str(i.date_start) if i.date_start else None,
                "date_end": str(i.date_end) if i.date_end else None,
                "contractor_name": i.contractor_name,
                "cost_chf": i.cost_chf,
            }
        )
    for a in actions:
        if a.action_type in ("remediation", "removal", "encapsulation", "monitoring"):
            remediation_items.append(
                {
                    "type": "planned_action",
                    "title": a.title,
                    "action_type": a.action_type,
                    "priority": a.priority,
                    "status": a.status,
                    "due_date": str(a.due_date) if a.due_date else None,
                }
            )
    remediation_completeness = min(1.0, len(remediation_items)) if remediation_items else 0.0
    remediation_section = HandoffSection(
        section_name="Plan d'assainissement",
        section_type="remediation_plan",
        items=remediation_items,
        completeness=remediation_completeness,
    )

    # -- Waste management --
    waste_items: list[dict] = []
    pollutant_types_found = {s.pollutant_type for s in samples if s.threshold_exceeded and s.pollutant_type}
    for pt in sorted(pollutant_types_found):
        matching = [s for s in samples if s.pollutant_type == pt and s.threshold_exceeded]
        disposal_types = list({s.waste_disposal_type for s in matching if s.waste_disposal_type})
        waste_items.append(
            {
                "pollutant_type": pt,
                "waste_category": _WASTE_CATEGORIES.get(pt, "A determiner"),
                "sample_count": len(matching),
                "disposal_types": disposal_types,
                "regulation": "OLED",
            }
        )
    waste_completeness = min(1.0, len(waste_items)) if waste_items else 0.0
    waste_section = HandoffSection(
        section_name="Plan de gestion des dechets",
        section_type="waste_management",
        items=waste_items,
        completeness=waste_completeness,
    )

    # -- Responsible parties --
    party_items: list[dict] = []
    for a in assignments:
        party_items.append(
            {
                "assignment_id": str(a.id),
                "role": a.role,
                "user_id": str(a.user_id),
            }
        )
    # Add building owner if set
    if building.owner_id:
        party_items.append(
            {
                "type": "building_owner",
                "user_id": str(building.owner_id),
            }
        )
    party_completeness = min(1.0, len(party_items)) if party_items else 0.0
    if not party_items:
        warnings.append("Aucune partie responsable identifiee")
    party_section = HandoffSection(
        section_name="Parties responsables",
        section_type="responsible_parties",
        items=party_items,
        completeness=party_completeness,
    )

    # -- Timeline commitments --
    timeline_items: list[dict] = []
    for a in actions:
        if a.due_date:
            timeline_items.append(
                {
                    "type": "action",
                    "title": a.title,
                    "due_date": str(a.due_date),
                    "status": a.status,
                    "priority": a.priority,
                }
            )
    for i in interventions:
        if i.date_start or i.date_end:
            timeline_items.append(
                {
                    "type": "intervention",
                    "title": i.title,
                    "date_start": str(i.date_start) if i.date_start else None,
                    "date_end": str(i.date_end) if i.date_end else None,
                    "status": i.status,
                }
            )
    # SUVA notification deadlines
    for d in diagnostics:
        if d.suva_notification_required and d.suva_notification_date:
            timeline_items.append(
                {
                    "type": "suva_notification",
                    "diagnostic_type": d.diagnostic_type,
                    "date": str(d.suva_notification_date),
                }
            )
    timeline_completeness = min(1.0, len(timeline_items)) if timeline_items else 0.0
    timeline_section = HandoffSection(
        section_name="Engagements de calendrier",
        section_type="timeline_commitments",
        items=timeline_items,
        completeness=timeline_completeness,
    )

    sections = [
        compliance_section,
        report_section,
        remediation_section,
        waste_section,
        party_section,
        timeline_section,
    ]
    overall = sum(s.completeness for s in sections) / len(sections)

    return AuthorityHandoffResult(
        building_id=building_id,
        generated_at=datetime.now(UTC),
        compliance_status=compliance_section,
        diagnostic_reports=report_section,
        remediation_plan=remediation_section,
        waste_management=waste_section,
        responsible_parties=party_section,
        timeline_commitments=timeline_section,
        overall_completeness=overall,
        warnings=warnings,
    )


# ===================================================================
# FN4: Validate handoff completeness
# ===================================================================

# Required checks per handoff type
_DIAGNOSTIC_CHECKS = [
    ("diagnostics", "Au moins un diagnostic"),
    ("samples", "Au moins un echantillon"),
    ("risk_score", "Score de risque calcule"),
    ("actions", "Actions recommandees"),
    ("diagnostic_completed", "Diagnostic en statut completed ou validated"),
]

_CONTRACTOR_CHECKS = [
    ("diagnostics", "Au moins un diagnostic"),
    ("samples_positive", "Echantillons positifs identifies"),
    ("actions_open", "Travaux planifies"),
    ("zones", "Zones definies"),
    ("documents", "Documents de reference"),
    ("safety_category", "Categorie de securite CFST"),
]

_AUTHORITY_CHECKS = [
    ("diagnostics", "Au moins un diagnostic"),
    ("compliance_artefacts", "Artefacts de conformite"),
    ("responsible_parties", "Parties responsables"),
    ("diagnostic_completed", "Diagnostic en statut completed ou validated"),
    ("waste_plan", "Plan de gestion des dechets"),
]


async def validate_handoff_completeness(
    db: AsyncSession,
    building_id: uuid.UUID,
    handoff_type: str,
) -> HandoffValidationResult:
    """Validate whether all required data exists for a given handoff type.

    Returns readiness score 0-100, missing fields, incomplete sections,
    and quality warnings.
    """
    # Validate handoff_type
    valid_types = ("diagnostic", "contractor", "authority")
    if handoff_type not in valid_types:
        raise ValueError(f"Invalid handoff_type: {handoff_type}. Must be one of {valid_types}")

    await _fetch_building(db, building_id)

    diagnostics = await _fetch_diagnostics_with_samples(db, building_id)
    samples = _all_samples(diagnostics)
    actions = await _fetch_actions(db, building_id)
    risk_score = await _fetch_risk_score(db, building_id)
    zones = await _fetch_zones(db, building_id)
    documents = await _fetch_documents(db, building_id)
    artefacts = await _fetch_compliance_artefacts(db, building_id)
    assignments = await _fetch_assignments(db, building_id)

    missing_fields: list[str] = []
    incomplete_sections: list[str] = []
    quality_warnings: list[HandoffValidationWarning] = []

    positive_samples = [s for s in samples if s.threshold_exceeded]
    completed_diags = [d for d in diagnostics if d.status in ("completed", "validated")]

    # Determine checks based on type
    if handoff_type == "diagnostic":
        checks = _DIAGNOSTIC_CHECKS
    elif handoff_type == "contractor":
        checks = _CONTRACTOR_CHECKS
    else:
        checks = _AUTHORITY_CHECKS

    passed = 0
    total = len(checks)

    for check_id, label in checks:
        if check_id == "diagnostics":
            if diagnostics:
                passed += 1
            else:
                missing_fields.append("diagnostics")
                incomplete_sections.append(label)
        elif check_id == "samples":
            if samples:
                passed += 1
            else:
                missing_fields.append("samples")
                incomplete_sections.append(label)
        elif check_id == "samples_positive":
            if positive_samples:
                passed += 1
            else:
                missing_fields.append("positive_samples")
                incomplete_sections.append(label)
        elif check_id == "risk_score":
            if risk_score:
                passed += 1
            else:
                missing_fields.append("risk_score")
                incomplete_sections.append(label)
        elif check_id == "actions":
            if actions:
                passed += 1
            else:
                missing_fields.append("actions")
                incomplete_sections.append(label)
        elif check_id == "actions_open":
            if any(a.status in ("open", "in_progress") for a in actions):
                passed += 1
            else:
                missing_fields.append("open_actions")
                incomplete_sections.append(label)
        elif check_id == "zones":
            if zones:
                passed += 1
            else:
                missing_fields.append("zones")
                incomplete_sections.append(label)
        elif check_id == "documents":
            if documents:
                passed += 1
            else:
                missing_fields.append("documents")
                incomplete_sections.append(label)
        elif check_id == "diagnostic_completed":
            if completed_diags:
                passed += 1
            else:
                missing_fields.append("completed_diagnostic")
                incomplete_sections.append(label)
        elif check_id == "compliance_artefacts":
            if artefacts:
                passed += 1
            else:
                missing_fields.append("compliance_artefacts")
                incomplete_sections.append(label)
        elif check_id == "responsible_parties":
            if assignments:
                passed += 1
            else:
                missing_fields.append("responsible_parties")
                incomplete_sections.append(label)
        elif check_id == "safety_category":
            if any(s.cfst_work_category for s in samples):
                passed += 1
            else:
                missing_fields.append("cfst_work_category")
                incomplete_sections.append(label)
        elif check_id == "waste_plan":
            if positive_samples and all(s.waste_disposal_type for s in positive_samples):
                passed += 1
            else:
                missing_fields.append("waste_disposal_types")
                incomplete_sections.append(label)

    # Quality warnings
    draft_diags = [d for d in diagnostics if d.status == "draft"]
    if draft_diags:
        quality_warnings.append(
            HandoffValidationWarning(
                field="diagnostic_status",
                message=f"{len(draft_diags)} diagnostic(s) encore en brouillon",
                severity="warning",
            )
        )

    samples_no_risk = [s for s in samples if not s.risk_level]
    if samples_no_risk:
        quality_warnings.append(
            HandoffValidationWarning(
                field="sample_risk_level",
                message=f"{len(samples_no_risk)} echantillon(s) sans niveau de risque",
                severity="warning",
            )
        )

    if handoff_type == "contractor" and not any(s.cfst_work_category for s in samples):
        quality_warnings.append(
            HandoffValidationWarning(
                field="cfst_work_category",
                message="Aucune categorie de travaux CFST definie",
                severity="error",
            )
        )

    if handoff_type == "authority":
        suva_missing = [d for d in diagnostics if d.suva_notification_required and not d.suva_notification_date]
        if suva_missing:
            quality_warnings.append(
                HandoffValidationWarning(
                    field="suva_notification_date",
                    message=f"{len(suva_missing)} notification(s) SUVA requise(s) sans date",
                    severity="error",
                )
            )

    readiness_score = round((passed / total) * 100) if total > 0 else 0

    return HandoffValidationResult(
        building_id=building_id,
        handoff_type=handoff_type,
        readiness_score=readiness_score,
        missing_fields=missing_fields,
        incomplete_sections=incomplete_sections,
        quality_warnings=quality_warnings,
        is_ready=readiness_score >= 80,
    )
