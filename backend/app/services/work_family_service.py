"""BatiConnect — Work-Family Trade Matrix service.

Maps every major corps de metier to its procedure context, authorities,
proof requirements, contractor categories, and safe-to-x implications.

The matrix lives in constants.py (WORK_FAMILIES). This service provides
lookup, requirement resolution for a BuildingCase, and coverage analysis
for a building.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import WORK_FAMILIES
from app.models.building import Building
from app.models.building_case import BuildingCase
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.procedure import ProcedureInstance, ProcedureTemplate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Static lookups
# ---------------------------------------------------------------------------


async def get_work_family(name: str) -> dict | None:
    """Get a single work family definition by name. Returns None if unknown."""
    family = WORK_FAMILIES.get(name)
    if family is None:
        return None
    return {"name": name, **family}


async def get_all_families() -> list[dict]:
    """List all work families with their full definitions."""
    return [{"name": name, **defn} for name, defn in WORK_FAMILIES.items()]


# ---------------------------------------------------------------------------
# Requirement resolution for a BuildingCase
# ---------------------------------------------------------------------------


async def get_requirements_for_case(db: AsyncSession, case_id: UUID) -> dict[str, Any]:
    """Given a BuildingCase, determine all work-family requirements.

    Returns:
        {
            "case_id": ...,
            "case_type": ...,
            "work_families": [
                {
                    "name": ...,
                    "label_fr": ...,
                    "applicable_procedures": [...],
                    "required_proof": [...],
                    "authorities_to_notify": [...],
                    "safe_to_x_implications": [...],
                    "contractor_requirements": [...],
                    "regulatory_basis": ...,
                }
            ],
            "aggregate": {
                "all_procedures": [...],
                "all_proof": [...],
                "all_authorities": [...],
                "all_safe_to_x": [...],
            }
        }
    """
    # Load case
    result = await db.execute(select(BuildingCase).where(BuildingCase.id == case_id))
    case = result.scalar_one_or_none()
    if case is None:
        return {"case_id": str(case_id), "error": "Case not found"}

    # Determine relevant work families from case type + pollutant scope
    relevant_families = _resolve_families_for_case(case)

    # Load matching procedure templates
    tpl_result = await db.execute(select(ProcedureTemplate).where(ProcedureTemplate.active.is_(True)))
    all_templates = list(tpl_result.scalars().all())

    families_output: list[dict] = []
    agg_procedures: set[str] = set()
    agg_proof: set[str] = set()
    agg_authorities: set[str] = set()
    agg_safe_to_x: set[str] = set()

    for family_name in relevant_families:
        defn = WORK_FAMILIES.get(family_name)
        if defn is None:
            continue

        # Match procedure templates that list this work family
        matching_templates = [
            t.name for t in all_templates if t.applicable_work_families and family_name in t.applicable_work_families
        ]

        proof = defn.get("proof_required", [])
        authorities = defn.get("authorities", [])
        safe_implications = defn.get("safe_to_x_implications", [])
        contractors = defn.get("contractor_categories", [])
        regulatory = defn.get("regulatory_basis", "")

        families_output.append(
            {
                "name": family_name,
                "label_fr": defn.get("label_fr", family_name),
                "applicable_procedures": matching_templates,
                "required_proof": proof,
                "authorities_to_notify": authorities,
                "safe_to_x_implications": safe_implications,
                "contractor_requirements": contractors,
                "regulatory_basis": regulatory,
            }
        )

        agg_procedures.update(matching_templates)
        agg_proof.update(proof)
        agg_authorities.update(authorities)
        agg_safe_to_x.update(safe_implications)

    return {
        "case_id": str(case_id),
        "case_type": case.case_type,
        "building_id": str(case.building_id),
        "work_families": families_output,
        "aggregate": {
            "all_procedures": sorted(agg_procedures),
            "all_proof": sorted(agg_proof),
            "all_authorities": sorted(agg_authorities),
            "all_safe_to_x": sorted(agg_safe_to_x),
        },
    }


def _resolve_families_for_case(case: BuildingCase) -> list[str]:
    """Derive which work families are relevant for a given case.

    Uses case_type and pollutant_scope to match families.
    """
    families: list[str] = []

    # Pollutant-based families
    pollutant_map = {
        "asbestos": "asbestos_removal",
        "pcb": "pcb_removal",
        "lead": "lead_removal",
        "hap": "hap_removal",
        "radon": "radon_mitigation",
        "pfas": "pfas_remediation",
    }
    for pol in case.pollutant_scope or []:
        fam = pollutant_map.get(pol)
        if fam:
            families.append(fam)

    # Case type mapping
    case_type_map: dict[str, list[str]] = {
        "works": ["renovation"],
        "permit": ["renovation"],
        "authority_submission": ["renovation"],
        "tender": ["renovation"],
        "insurance_claim": ["insurance_claim"],
        "incident": ["insurance_claim", "maintenance"],
        "maintenance": ["maintenance"],
        "funding": ["subsidy_funding", "energy_renovation"],
        "transaction": ["transaction_transfer"],
        "due_diligence": ["transaction_transfer"],
        "transfer": ["transaction_transfer"],
        "handoff": ["transaction_transfer"],
        "control": ["maintenance"],
    }
    for fam in case_type_map.get(case.case_type, []):
        if fam not in families:
            families.append(fam)

    return families


# ---------------------------------------------------------------------------
# Coverage analysis for a building
# ---------------------------------------------------------------------------


async def get_coverage_for_building(
    db: AsyncSession,
    building_id: UUID,
) -> dict[str, Any]:
    """For each work family, show what the building already has vs what's missing.

    Returns:
        {
            "building_id": ...,
            "families": {
                "<family_name>": {
                    "label_fr": ...,
                    "procedures_ready": [...],
                    "procedures_missing": [...],
                    "proof_available": [...],
                    "proof_missing": [...],
                    "safe_to_x_status": {...},
                    "coverage_pct": ...,
                }
            },
            "summary": {
                "total_families": ...,
                "families_fully_covered": ...,
                "families_partial": ...,
                "families_uncovered": ...,
                "overall_coverage_pct": ...,
            }
        }
    """
    # Verify building exists
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if building is None:
        return {"building_id": str(building_id), "error": "Building not found"}

    # Load building's existing evidence
    existing_evidence = await _collect_building_evidence(db, building_id)

    # Load procedure instances for this building
    proc_result = await db.execute(select(ProcedureInstance).where(ProcedureInstance.building_id == building_id))
    proc_instances = list(proc_result.scalars().all())

    # Load all active templates
    tpl_result = await db.execute(select(ProcedureTemplate).where(ProcedureTemplate.active.is_(True)))
    all_templates = list(tpl_result.scalars().all())

    families_coverage: dict[str, dict] = {}
    total_covered = 0
    total_partial = 0
    total_uncovered = 0

    for family_name, defn in WORK_FAMILIES.items():
        # Determine which procedures apply
        matching_templates = [
            t for t in all_templates if t.applicable_work_families and family_name in t.applicable_work_families
        ]

        # Check which procedure templates have active/completed instances
        procedures_ready: list[str] = []
        procedures_missing: list[str] = []
        for tpl in matching_templates:
            has_instance = any(
                pi.template_id == tpl.id and pi.status in ("approved", "submitted", "in_progress", "completed")
                for pi in proc_instances
            )
            if has_instance:
                procedures_ready.append(tpl.name)
            else:
                procedures_missing.append(tpl.name)

        # Check proof availability
        required_proof = defn.get("proof_required", [])
        proof_available: list[str] = []
        proof_missing: list[str] = []
        for proof_item in required_proof:
            if _proof_is_available(proof_item, existing_evidence, defn.get("pollutant")):
                proof_available.append(proof_item)
            else:
                proof_missing.append(proof_item)

        # Safe-to-x status
        safe_implications = defn.get("safe_to_x_implications", [])
        safe_status: dict[str, str] = {}
        for stx in safe_implications:
            if not proof_missing and not procedures_missing:
                safe_status[stx] = "ready"
            elif proof_available or procedures_ready:
                safe_status[stx] = "partial"
            else:
                safe_status[stx] = "not_ready"

        # Coverage calculation
        total_items = len(required_proof) + len(matching_templates)
        covered_items = len(proof_available) + len(procedures_ready)
        coverage_pct = round((covered_items / total_items * 100) if total_items > 0 else 100, 1)

        if coverage_pct >= 100:
            total_covered += 1
        elif coverage_pct > 0:
            total_partial += 1
        else:
            total_uncovered += 1

        families_coverage[family_name] = {
            "label_fr": defn.get("label_fr", family_name),
            "procedures_ready": procedures_ready,
            "procedures_missing": procedures_missing,
            "proof_available": proof_available,
            "proof_missing": proof_missing,
            "safe_to_x_status": safe_status,
            "coverage_pct": coverage_pct,
        }

    total_families = len(WORK_FAMILIES)
    overall_pct = round((total_covered / total_families * 100) if total_families > 0 else 0, 1)

    return {
        "building_id": str(building_id),
        "families": families_coverage,
        "summary": {
            "total_families": total_families,
            "families_fully_covered": total_covered,
            "families_partial": total_partial,
            "families_uncovered": total_uncovered,
            "overall_coverage_pct": overall_pct,
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _collect_building_evidence(
    db: AsyncSession,
    building_id: UUID,
) -> dict[str, Any]:
    """Collect existing diagnostics, documents, and interventions for coverage matching."""
    # Diagnostics — types present
    diag_result = await db.execute(
        select(Diagnostic.diagnostic_type).where(Diagnostic.building_id == building_id).distinct()
    )
    diagnostic_types = {row[0] for row in diag_result.all() if row[0]}

    # Documents — types present
    doc_result = await db.execute(select(Document.document_type).where(Document.building_id == building_id).distinct())
    document_types = {row[0] for row in doc_result.all() if row[0]}

    # Interventions — types present
    interv_result = await db.execute(
        select(Intervention.intervention_type).where(Intervention.building_id == building_id).distinct()
    )
    intervention_types = {row[0] for row in interv_result.all() if row[0]}

    # Diagnostic count per pollutant
    diag_count_result = await db.execute(
        select(Diagnostic.diagnostic_type, func.count(Diagnostic.id))
        .where(Diagnostic.building_id == building_id)
        .group_by(Diagnostic.diagnostic_type)
    )
    diagnostic_counts = {row[0]: row[1] for row in diag_count_result.all() if row[0]}

    return {
        "diagnostic_types": diagnostic_types,
        "document_types": document_types,
        "intervention_types": intervention_types,
        "diagnostic_counts": diagnostic_counts,
    }


# Map of proof item keys to what building evidence satisfies them
_PROOF_EVIDENCE_MAP: dict[str, dict[str, set[str]]] = {
    # Pollutant diagnostics
    "diagnostic_amiante": {"diagnostic_types": {"asbestos", "full"}},
    "diagnostic_pcb": {"diagnostic_types": {"pcb", "full"}},
    "diagnostic_plomb": {"diagnostic_types": {"lead", "full"}},
    "diagnostic_hap": {"diagnostic_types": {"hap", "full"}},
    "diagnostic_pfas": {"diagnostic_types": {"pfas", "full"}},
    "diagnostic_polluants": {"diagnostic_types": {"asbestos", "pcb", "lead", "hap", "full"}},
    "diagnostic_polluants_complet": {"diagnostic_types": {"full"}},
    "mesure_radon_long_terme": {"diagnostic_types": {"radon"}},
    # Documents
    "plans_architecte": {"document_types": {"plan", "building_plan", "technical_plan"}},
    "plans_facade_toiture": {"document_types": {"plan", "building_plan", "technical_plan"}},
    "plans_techniques_cvs": {"document_types": {"plan", "technical_plan"}},
    "plans_sanitaires": {"document_types": {"plan", "technical_plan"}},
    "plans_interieurs": {"document_types": {"plan", "building_plan"}},
    "plans_amenagement_exterieur": {"document_types": {"plan"}},
    "plans_etancheite": {"document_types": {"plan", "technical_plan"}},
    "plans_accessibilite": {"document_types": {"plan"}},
    "plans_evacuation": {"document_types": {"plan"}},
    "schema_electrique": {"document_types": {"plan", "technical_plan"}},
    "rapport_expertise": {"document_types": {"report", "expertise"}},
    "rapport_energetique": {"document_types": {"report", "energy_report"}},
    "bilan_energetique": {"document_types": {"report", "energy_report"}},
    "cecb": {"document_types": {"cecb", "energy_certificate"}},
    "cecb_avant": {"document_types": {"cecb", "energy_certificate"}},
    "cecb_ou_audit_energetique": {"document_types": {"cecb", "energy_certificate", "report"}},
    "police_assurance": {"document_types": {"insurance", "contract"}},
    "assurance_batiment": {"document_types": {"insurance", "contract"}},
    "extrait_registre_foncier": {"document_types": {"registry", "legal"}},
    "etat_locatif": {"document_types": {"financial", "lease"}},
    "contrats_maintenance": {"document_types": {"contract"}},
    "carnet_entretien": {"document_types": {"maintenance", "logbook"}},
    "concept_protection_incendie": {"document_types": {"report", "fire_safety"}},
    # Interventions
    "rapport_assainissement": {"intervention_types": {"decontamination", "renovation"}},
    "mesure_controle_post_travaux": {"intervention_types": {"inspection", "diagnostic"}},
    "suivi_post_remediation": {"intervention_types": {"inspection"}},
}


def _proof_is_available(
    proof_item: str,
    evidence: dict[str, Any],
    pollutant: str | None,
) -> bool:
    """Check if a proof item is satisfied by existing building evidence."""
    mapping = _PROOF_EVIDENCE_MAP.get(proof_item)
    if mapping is None:
        # No mapping — cannot automatically verify, assume missing
        return False

    for evidence_category, required_values in mapping.items():
        existing_values = evidence.get(evidence_category, set())
        if existing_values & required_values:
            return True

    return False
