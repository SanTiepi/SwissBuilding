"""Authority pack generation service.

Assembles authority-ready evidence packs with structured sections covering
building identity, diagnostics, samples, compliance, actions, risk, interventions,
document inventory, passport summary, readiness verdict, pollutant inventory,
completeness report, contradictions, and explicit caveats.

This is the KEY deliverable for the pilot: a generable, downloadable pack that
contains everything needed for an authority submission.
"""

import hashlib
import json
import logging
import os
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
    AuthorityPackArtifactMetadata,
    AuthorityPackArtifactResult,
    AuthorityPackConfig,
    AuthorityPackListItem,
    AuthorityPackResult,
    AuthorityPackSection,
)
from app.services.eco_clause_template_service import generate_eco_clauses

logger = logging.getLogger(__name__)

AUTHORITY_PACK_VERSION = "2.0.0"

ALL_SECTION_TYPES = [
    "building_identity",
    "passport_summary",
    "completeness_report",
    "readiness_verdict",
    "diagnostic_summary",
    "sample_results",
    "pollutant_inventory",
    "compliance_status",
    "action_plan",
    "risk_assessment",
    "intervention_history",
    "document_inventory",
    "contradictions",
    "caveats",
]

_SECTION_NAMES = {
    "building_identity": "Identite du batiment",
    "passport_summary": "Resume du passeport batiment",
    "completeness_report": "Rapport de completude du dossier",
    "readiness_verdict": "Verdict de readiness reglementaire",
    "diagnostic_summary": "Synthese des diagnostics",
    "sample_results": "Resultats des echantillons",
    "pollutant_inventory": "Inventaire des polluants",
    "compliance_status": "Statut de conformite",
    "action_plan": "Plan d'actions",
    "risk_assessment": "Evaluation des risques",
    "intervention_history": "Historique des interventions",
    "document_inventory": "Inventaire des documents",
    "contradictions": "Contradictions detectees",
    "caveats": "Reserves et limites",
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


async def _build_passport_summary(db: AsyncSession, building_id: uuid.UUID) -> AuthorityPackSection:
    """Build the passport summary section from passport_service."""
    items: list[dict] = []
    completeness = 0.0
    notes = None
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
        if passport:
            items.append(
                {
                    "passport_grade": passport.get("passport_grade", "F"),
                    "overall_trust": passport.get("knowledge_state", {}).get("overall_trust", 0.0),
                    "total_data_points": passport.get("knowledge_state", {}).get("total_data_points", 0),
                    "diagnostics_count": passport.get("evidence_coverage", {}).get("diagnostics_count", 0),
                    "documents_count": passport.get("evidence_coverage", {}).get("documents_count", 0),
                    "pollutant_coverage_ratio": passport.get("pollutant_coverage", {}).get("coverage_ratio", 0.0),
                    "blind_spots_total": passport.get("blind_spots", {}).get("total_open", 0),
                    "contradictions_unresolved": passport.get("contradictions", {}).get("unresolved", 0),
                    "assessed_at": passport.get("assessed_at"),
                    "source": "passport_service",
                }
            )
            grade = passport.get("passport_grade", "F")
            completeness = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4}.get(grade, 0.2)
            notes = f"Grade passeport: {grade}"
    except Exception as e:
        logger.warning("Failed to build passport summary for %s: %s", building_id, e)
        notes = "Impossible de generer le resume du passeport"

    return AuthorityPackSection(
        section_name="Resume du passeport batiment",
        section_type="passport_summary",
        items=items,
        completeness=completeness,
        notes=notes,
    )


async def _build_completeness_report(db: AsyncSession, building_id: uuid.UUID) -> AuthorityPackSection:
    """Build the completeness report section from completeness_engine."""
    items: list[dict] = []
    completeness = 0.0
    notes = None
    try:
        from app.services.completeness_engine import evaluate_completeness

        result = await evaluate_completeness(db, building_id)
        checks_data = []
        for c in result.checks:
            checks_data.append(
                {
                    "id": c.id,
                    "category": c.category,
                    "status": c.status,
                    "weight": c.weight,
                    "details": c.details,
                }
            )
        items.append(
            {
                "overall_score": result.overall_score,
                "ready_to_proceed": result.ready_to_proceed,
                "workflow_stage": result.workflow_stage,
                "missing_items": result.missing_items,
                "checks": checks_data,
                "source": "completeness_engine",
            }
        )
        completeness = result.overall_score
        notes = (
            f"Score: {round(result.overall_score * 100)}% — "
            f"{'Pret a proceder' if result.ready_to_proceed else f'{len(result.missing_items)} element(s) manquant(s)'}"
        )
    except Exception as e:
        logger.warning("Failed to build completeness report for %s: %s", building_id, e)
        notes = "Impossible d'evaluer la completude"

    return AuthorityPackSection(
        section_name="Rapport de completude du dossier",
        section_type="completeness_report",
        items=items,
        completeness=completeness,
        notes=notes,
    )


async def _build_readiness_verdict(db: AsyncSession, building_id: uuid.UUID) -> AuthorityPackSection:
    """Build the readiness verdict section from readiness_reasoner."""
    items: list[dict] = []
    completeness = 0.0
    notes = None
    try:
        from app.services.readiness_reasoner import READINESS_TYPES, evaluate_readiness

        for rtype in READINESS_TYPES:
            try:
                assessment = await evaluate_readiness(db, building_id, rtype)
                blockers = [b.get("message", str(b)) for b in (assessment.blockers_json or [])]
                conditions = [c.get("message", str(c)) for c in (assessment.conditions_json or [])]
                items.append(
                    {
                        "readiness_type": rtype,
                        "status": assessment.status,
                        "score": assessment.score or 0.0,
                        "blockers": blockers,
                        "conditions": conditions,
                        "assessed_at": assessment.assessed_at.isoformat() if assessment.assessed_at else None,
                        "source": "readiness_reasoner",
                    }
                )
            except ValueError:
                items.append(
                    {
                        "readiness_type": rtype,
                        "status": "error",
                        "score": 0.0,
                        "blockers": [],
                        "conditions": [],
                        "source": "readiness_reasoner",
                    }
                )

        if items:
            avg_score = sum(i["score"] for i in items) / len(items)
            completeness = avg_score
            ready_count = sum(1 for i in items if i["status"] == "ready")
            blocked_count = sum(1 for i in items if i["status"] == "blocked")
            notes = f"{ready_count}/{len(items)} pret(s), {blocked_count} bloque(s)"
    except Exception as e:
        logger.warning("Failed to build readiness verdict for %s: %s", building_id, e)
        notes = "Impossible d'evaluer la readiness"

    return AuthorityPackSection(
        section_name="Verdict de readiness reglementaire",
        section_type="readiness_verdict",
        items=items,
        completeness=completeness,
        notes=notes,
    )


async def _build_pollutant_inventory(db: AsyncSession, building_id: uuid.UUID) -> AuthorityPackSection:
    """Build per-pollutant status inventory."""
    from app.constants import ALL_POLLUTANTS

    result = await db.execute(
        select(Diagnostic).options(selectinload(Diagnostic.samples)).where(Diagnostic.building_id == building_id)
    )
    diagnostics = result.scalars().all()

    # Aggregate per pollutant
    pollutant_data: dict[str, dict] = {}
    for p in ALL_POLLUTANTS:
        pollutant_data[p] = {
            "pollutant": p,
            "status": "unknown",
            "diagnostic_count": 0,
            "sample_count": 0,
            "positive_count": 0,
            "latest_diagnostic_date": None,
            "max_risk_level": None,
            "actions_pending": 0,
        }

    for diag in diagnostics:
        dtype = (diag.diagnostic_type or "").lower()
        if dtype in pollutant_data:
            pd = pollutant_data[dtype]
            pd["diagnostic_count"] += 1
            date_str = str(diag.date_inspection) if diag.date_inspection else None
            if date_str and (pd["latest_diagnostic_date"] is None or date_str > pd["latest_diagnostic_date"]):
                pd["latest_diagnostic_date"] = date_str

        for s in diag.samples:
            stype = (s.pollutant_type or "").lower()
            if stype in pollutant_data:
                pd = pollutant_data[stype]
                pd["sample_count"] += 1
                if s.threshold_exceeded:
                    pd["positive_count"] += 1
                    pd["status"] = "present"
                elif pd["status"] == "unknown":
                    pd["status"] = "absent"
                # Track max risk level
                risk_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
                current_max = risk_order.get(pd["max_risk_level"] or "", 0)
                sample_risk = risk_order.get((s.risk_level or "").lower(), 0)
                if sample_risk > current_max:
                    pd["max_risk_level"] = s.risk_level

    # Count pending actions per pollutant
    action_result = await db.execute(
        select(ActionItem).where(ActionItem.building_id == building_id, ActionItem.status == "open")
    )
    open_actions = action_result.scalars().all()
    for a in open_actions:
        atype = (a.action_type or "").lower()
        for p in ALL_POLLUTANTS:
            if p in atype:
                pollutant_data[p]["actions_pending"] += 1
                break

    items = list(pollutant_data.values())

    covered = sum(1 for i in items if i["status"] != "unknown")
    completeness = covered / len(items) if items else 0.0
    present_count = sum(1 for i in items if i["status"] == "present")
    notes = f"{covered}/{len(items)} polluant(s) evalue(s), {present_count} present(s)"

    return AuthorityPackSection(
        section_name="Inventaire des polluants",
        section_type="pollutant_inventory",
        items=items,
        completeness=completeness,
        notes=notes,
    )


async def _build_contradictions(db: AsyncSession, building_id: uuid.UUID) -> AuthorityPackSection:
    """Build contradictions section."""
    items: list[dict] = []
    completeness = 1.0
    notes = None
    try:
        from app.models.data_quality_issue import DataQualityIssue

        result = await db.execute(
            select(DataQualityIssue).where(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.issue_type == "contradiction",
            )
        )
        contradictions = result.scalars().all()

        for c in contradictions:
            items.append(
                {
                    "field": c.field_name,
                    "description": c.description,
                    "status": c.status,
                    "severity": c.severity,
                    "source": "contradiction_detector",
                }
            )

        unresolved = sum(1 for c in contradictions if c.status != "resolved")
        if unresolved > 0:
            completeness = max(0.0, 1.0 - (unresolved * 0.2))
            notes = f"{unresolved} contradiction(s) non resolue(s) sur {len(contradictions)}"
        elif contradictions:
            notes = f"{len(contradictions)} contradiction(s) — toutes resolues"
        else:
            notes = "Aucune contradiction detectee"
    except Exception as e:
        logger.warning("Failed to build contradictions for %s: %s", building_id, e)
        notes = "Impossible de verifier les contradictions"

    return AuthorityPackSection(
        section_name="Contradictions detectees",
        section_type="contradictions",
        items=items,
        completeness=completeness,
        notes=notes,
    )


async def _build_caveats(
    sections: list[AuthorityPackSection], building: Building, db: AsyncSession | None = None
) -> AuthorityPackSection:
    """Build explicit caveats listing what is NOT covered or NOT verified.

    Includes first-class Caveat records from the database when db is provided.
    """
    caveats: list[dict] = []

    # 1. First-class caveats from the database (Commitment & Caveat graph)
    if db is not None:
        try:
            from app.services.commitment_service import get_caveats_for_pack

            db_caveats = await get_caveats_for_pack(db, building.id, "authority")
            for c in db_caveats:
                caveats.append(
                    {
                        "caveat_type": c.caveat_type,
                        "message": f"{c.subject}: {c.description}" if c.description else c.subject,
                        "severity": c.severity,
                        "source": "commitment_graph",
                        "caveat_id": str(c.id),
                    }
                )
        except Exception:
            logger.warning("Failed to load first-class caveats for building %s", building.id)

    # Always present caveat: this is not a legal compliance guarantee
    caveats.append(
        {
            "caveat_type": "liability",
            "message": (
                "Ce pack ne constitue pas une garantie de conformite legale. "
                "Il s'agit d'un outil d'aide a la decision base sur les donnees disponibles."
            ),
            "severity": "info",
        }
    )

    # Check for low-completeness sections
    for s in sections:
        if s.completeness < 0.5 and s.section_type not in ("caveats",):
            caveats.append(
                {
                    "caveat_type": "incomplete_section",
                    "message": f"Section '{s.section_name}' incomplete ({round(s.completeness * 100)}%)",
                    "severity": "warning",
                    "section_type": s.section_type,
                }
            )

    # Check building age
    if building.construction_year and building.construction_year < 1990:
        caveats.append(
            {
                "caveat_type": "building_age",
                "message": (
                    f"Batiment construit en {building.construction_year} — verifier la couverture amiante, PCB et plomb"
                ),
                "severity": "info",
            }
        )

    # Check missing EGID
    if not building.egid:
        caveats.append(
            {
                "caveat_type": "missing_identity",
                "message": "EGID manquant — identification officielle incomplete",
                "severity": "warning",
            }
        )

    # PFAS caveat — regulatory framework still provisional
    caveats.append(
        {
            "caveat_type": "regulatory",
            "message": (
                "Le cadre reglementaire PFAS est encore provisoire (OSEC/OFEV). "
                "Les seuils et obligations peuvent evoluer."
            ),
            "severity": "info",
        }
    )

    # No PDF generation caveat
    caveats.append(
        {
            "caveat_type": "format",
            "message": "Le pack est genere au format JSON. La generation PDF est prevue dans une version ulterieure.",
            "severity": "info",
        }
    )

    # Completeness is 1.0 because caveats are always complete (they are what they are)
    return AuthorityPackSection(
        section_name="Reserves et limites",
        section_type="caveats",
        items=caveats,
        completeness=1.0,
        notes=f"{len(caveats)} reserve(s) identifiee(s)",
    )


# ---------------------------------------------------------------------------
# Financial field redaction
# ---------------------------------------------------------------------------

_REDACTED_PLACEHOLDER = "[confidentiel]"
_REDACTED_COST_MESSAGE = "[Montants masques a la demande du proprietaire]"

_FINANCIAL_FIELD_NAMES = frozenset(
    {
        "total_amount_chf",
        "cost",
        "amount",
        "price",
        "amount_chf",
        "claimed_amount_chf",
        "approved_amount_chf",
        "paid_amount_chf",
        "insured_value_chf",
        "premium_annual_chf",
    }
)


def _redact_authority_item(item: dict) -> dict:
    """Return a copy of *item* with financial fields replaced by placeholders."""
    redacted = {}
    for key, value in item.items():
        if key in _FINANCIAL_FIELD_NAMES:
            redacted[key] = _REDACTED_PLACEHOLDER
        else:
            redacted[key] = value
    return redacted


def _redact_authority_section(section: AuthorityPackSection) -> AuthorityPackSection:
    """Return a redacted copy of a section, masking financial data."""
    redacted_items = [_redact_authority_item(item) for item in section.items]
    return AuthorityPackSection(
        section_name=section.section_name,
        section_type=section.section_type,
        items=redacted_items,
        completeness=section.completeness,
        notes=section.notes,
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
    "passport_summary": _build_passport_summary,
    "completeness_report": _build_completeness_report,
    "readiness_verdict": _build_readiness_verdict,
    "pollutant_inventory": _build_pollutant_inventory,
    "contradictions": _build_contradictions,
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

    # Build sections (excluding caveats — built after all others)
    sections: list[AuthorityPackSection] = []
    for section_type in valid_section_types:
        if section_type == "caveats":
            continue  # built after all others
        builder = _SECTION_BUILDERS[section_type]
        if section_type == "building_identity":
            section = await builder(db, building)
        else:
            section = await builder(db, building_id)
        sections.append(section)

    # Build caveats section (always included, references other sections + first-class caveats)
    if "caveats" in valid_section_types or config.include_sections is None:
        caveats_section = await _build_caveats(sections, building, db=db)
        sections.append(caveats_section)

    # Compute overall completeness (exclude caveats from calculation)
    scorable = [s for s in sections if s.section_type != "caveats"]
    if scorable:
        overall_completeness = sum(s.completeness for s in scorable) / len(scorable)
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

    # Apply financial redaction to exported view if requested
    output_sections = sections
    if config.redact_financials:
        output_sections = [_redact_authority_section(s) for s in sections]

    generated_at = datetime.now(UTC)
    pack_id = uuid.uuid4()

    # Count caveats for metadata
    caveats_section_data = next((s for s in sections if s.section_type == "caveats"), None)
    caveats_count = len(caveats_section_data.items) if caveats_section_data else 0

    # Build metadata dict
    metadata_inner = {
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
        "caveats_count": caveats_count,
        "pack_version": AUTHORITY_PACK_VERSION,
        "generated_by": str(user_id),
        "generation_date": generated_at.isoformat(),
        "financials_redacted": config.redact_financials,
    }

    # Compute SHA-256 hash of the pack content for traceability
    content_for_hash = json.dumps(metadata_inner, sort_keys=True, default=str)
    content_hash = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()
    metadata_inner["sha256_hash"] = content_hash

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
        notes=json.dumps(metadata_inner),
    )
    db.add(pack_record)
    await db.commit()

    return AuthorityPackResult(
        pack_id=pack_id,
        building_id=building_id,
        canton=canton,
        sections=output_sections,
        total_sections=len(output_sections),
        overall_completeness=overall_completeness,
        generated_at=generated_at,
        warnings=warnings,
        caveats_count=caveats_count,
        pack_version=AUTHORITY_PACK_VERSION,
        sha256_hash=content_hash,
        financials_redacted=config.redact_financials,
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

    caveats_count = 0
    pack_version = "1.0.0"
    sha256_hash = None
    if pack.notes:
        try:
            meta = json.loads(pack.notes)
            caveats_count = meta.get("caveats_count", 0)
            pack_version = meta.get("pack_version", "1.0.0")
            sha256_hash = meta.get("sha256_hash")
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
        caveats_count=caveats_count,
        pack_version=pack_version,
        sha256_hash=sha256_hash,
    )


async def generate_pack_artifact(
    db: AsyncSession,
    building_id: uuid.UUID,
    config: AuthorityPackConfig,
    user_id: uuid.UUID,
    output_dir: str | None = None,
) -> AuthorityPackArtifactResult:
    """Generate the authority pack AND write it as a real JSON artifact file.

    Returns an AuthorityPackArtifactResult containing:
      - pack_data: the full AuthorityPackResult
      - artifact_path: path to the written JSON file
      - sha256: SHA-256 hash of the artifact file content
      - metadata: generation metadata (building_id, timestamps, version, etc.)
    """
    # Generate the pack using the existing function
    pack = await generate_authority_pack(db, building_id, config, user_id)

    # Determine output directory
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "artifacts", "packs")
    os.makedirs(output_dir, exist_ok=True)

    # Build the filename with building ID and timestamp
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    filename = f"authority-pack-{building_id}-{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    # Serialize the full pack to JSON
    pack_dict = pack.model_dump(mode="json")
    content = json.dumps(pack_dict, indent=2, default=str, ensure_ascii=False)
    sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

    # Write the artifact file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(
        "Authority pack artifact written: %s (sha256=%s, building=%s)",
        filepath,
        sha256[:16],
        building_id,
    )

    generated_at = datetime.now(UTC).isoformat()

    return AuthorityPackArtifactResult(
        pack_data=pack,
        artifact_path=filepath,
        sha256=sha256,
        metadata=AuthorityPackArtifactMetadata(
            building_id=str(building_id),
            generated_at=generated_at,
            generated_by=str(user_id),
            version=pack.pack_version,
            financials_redacted=config.redact_financials,
        ),
    )
