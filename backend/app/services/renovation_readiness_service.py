"""BatiConnect — Renovation Readiness Orchestrator.

Wires existing services into a single flow:
from a building + work type, assess what is ready / missing / subsidized
and optionally generate a readiness pack.

This is an ORCHESTRATOR — it calls existing services, it does NOT
duplicate their logic.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import WORK_FAMILIES
from app.services.commitment_service import get_building_caveats
from app.services.completeness_engine import evaluate_completeness
from app.services.pack_builder import generate_pack
from app.services.passport_service import get_passport_summary
from app.services.procedure_service import get_applicable_procedures
from app.services.readiness_reasoner import evaluate_readiness
from app.services.subsidy_source_service import SubsidySourceService
from app.services.unknowns_ledger_service import get_ledger

logger = logging.getLogger(__name__)

# Work types that map to pollutant-specific work families
_POLLUTANT_WORK_TYPES = {
    "asbestos_removal",
    "pcb_removal",
    "lead_removal",
    "hap_removal",
    "radon_mitigation",
    "pfas_remediation",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_readiness_verdict(assessment: Any) -> dict:
    """Extract readiness verdict from a ReadinessAssessment ORM object."""
    blockers = []
    conditions = []
    if assessment.blockers_json:
        blockers = [b.get("message", str(b)) for b in assessment.blockers_json]
    if assessment.conditions_json:
        conditions = [c.get("message", str(c)) for c in assessment.conditions_json]
    return {
        "verdict": assessment.status or "unknown",
        "score": round(assessment.score or 0.0, 2),
        "blockers": blockers,
        "conditions": conditions,
    }


def _derive_next_actions(
    completeness_result: Any,
    readiness_start: dict,
    readiness_tender: dict,
    unknowns: list,
    work_family: dict | None,
) -> list[dict]:
    """Generate prioritized next actions from the assessment data."""
    actions: list[dict] = []

    # 1. High-priority: readiness blockers
    for blocker in readiness_start.get("blockers", [])[:3]:
        actions.append({"title": blocker, "priority": "high", "source": "readiness"})

    # 2. Medium-priority: missing completeness items
    if completeness_result:
        for check in getattr(completeness_result, "checks", []):
            if getattr(check, "status", None) == "missing" and len(actions) < 7:
                label = getattr(check, "details", None) or getattr(check, "label_key", "")
                actions.append({"title": label, "priority": "medium", "source": "completeness"})

    # 3. Medium-priority: critical unknowns
    for entry in unknowns:
        if getattr(entry, "severity", None) in ("critical", "high") and len(actions) < 7:
            actions.append(
                {
                    "title": getattr(entry, "subject", "Unknown gap"),
                    "priority": "medium",
                    "source": "unknowns",
                }
            )

    # 4. Low-priority: missing proof from work family
    if work_family:
        for proof in work_family.get("proof_required", [])[:2]:
            if len(actions) < 8:
                actions.append(
                    {
                        "title": f"Fournir: {proof}",
                        "priority": "low",
                        "source": "work_family",
                    }
                )

    return actions[:8]


def _compute_pack_blockers(
    readiness_start: dict,
    completeness_result: Any,
) -> list[str]:
    """Determine what prevents pack generation."""
    blockers: list[str] = []

    # Pack cannot be generated if not safe to start
    if readiness_start.get("verdict") not in ("ready", "conditionally_ready"):
        for b in readiness_start.get("blockers", [])[:3]:
            blockers.append(b)

    # Pack requires minimum completeness
    if completeness_result:
        score = getattr(completeness_result, "score", 0.0)
        if score < 0.5:
            blockers.append(f"Completude insuffisante ({round(score * 100)}%)")

    return blockers


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def assess_readiness(
    db: AsyncSession,
    building_id: UUID,
    work_type: str,
    org_id: UUID | None = None,
) -> dict[str, Any]:
    """Full renovation readiness assessment for a building + work type.

    Orchestrates existing services into a unified response.
    Returns a dict with all assessment sections.
    """
    # Validate work type
    work_family = WORK_FAMILIES.get(work_type)
    if work_family is None:
        return {
            "building_id": str(building_id),
            "work_type": work_type,
            "error": "unknown_work_type",
            "detail": f"Work type '{work_type}' not found in WORK_FAMILIES",
        }

    work_type_label = work_family.get("label_fr", work_type)

    # --- 1. Passport summary (optional, won't fail the assessment) ---
    passport = None
    try:
        passport = await get_passport_summary(db, building_id)
    except Exception:
        logger.warning("Passport summary failed for building %s", building_id)

    if passport is None:
        return {
            "building_id": str(building_id),
            "work_type": work_type,
            "error": "building_not_found",
            "detail": "Building does not exist or has no data",
        }

    # --- 2. Completeness ---
    completeness_result = None
    try:
        completeness_result = await evaluate_completeness(db, building_id, "avt")
    except Exception:
        logger.warning("Completeness evaluation failed for building %s", building_id)

    completeness_section: dict[str, Any] = {"score_pct": 0, "documented": [], "missing": []}
    if completeness_result:
        completeness_section["score_pct"] = round(getattr(completeness_result, "score", 0.0) * 100)
        for check in getattr(completeness_result, "checks", []):
            entry = {
                "id": getattr(check, "id", ""),
                "label": getattr(check, "label_key", ""),
                "status": getattr(check, "status", "unknown"),
                "details": getattr(check, "details", ""),
            }
            if getattr(check, "status", "") == "complete":
                completeness_section["documented"].append(entry)
            elif getattr(check, "status", "") in ("missing", "partial"):
                completeness_section["missing"].append(entry)

    # --- 3. Readiness verdict (safe_to_start + safe_to_tender) ---
    readiness_start_data: dict = {"verdict": "unknown", "blockers": [], "conditions": []}
    readiness_tender_data: dict = {"verdict": "unknown", "blockers": [], "conditions": []}
    try:
        start_assessment = await evaluate_readiness(db, building_id, "safe_to_start")
        readiness_start_data = _format_readiness_verdict(start_assessment)
    except Exception:
        logger.warning("safe_to_start evaluation failed for building %s", building_id)

    try:
        tender_assessment = await evaluate_readiness(db, building_id, "safe_to_tender")
        readiness_tender_data = _format_readiness_verdict(tender_assessment)
    except Exception:
        logger.warning("safe_to_tender evaluation failed for building %s", building_id)

    # Overall verdict
    if readiness_start_data["verdict"] == "ready" and readiness_tender_data["verdict"] == "ready":
        overall_verdict = "ready"
    elif readiness_start_data["verdict"] in ("ready", "conditionally_ready"):
        overall_verdict = "partially_ready"
    else:
        overall_verdict = "not_ready"

    # --- 4. Applicable procedures ---
    procedures_section: dict[str, Any] = {"applicable": [], "forms_needed": []}
    try:
        applicable = await get_applicable_procedures(db, building_id, work_type=work_type)
        for item in applicable:
            tpl = item.get("template")
            if tpl:
                procedures_section["applicable"].append(
                    {
                        "name": getattr(tpl, "name", ""),
                        "type": getattr(tpl, "procedure_type", ""),
                        "authority": getattr(tpl, "canton", "") or "federal",
                        "steps_count": len(getattr(tpl, "steps_json", []) or []),
                    }
                )
        # Add forms from work family
        for proc_name in work_family.get("procedure_names", []):
            procedures_section["forms_needed"].append(proc_name)
    except Exception:
        logger.warning("Procedures lookup failed for building %s", building_id)

    # --- 5. Subsidy eligibility ---
    subsidies_section: dict[str, Any] = {"eligible": [], "total_potential_chf": 0}
    try:
        eligibility = await SubsidySourceService.get_subsidy_eligibility(db, building_id, work_type)
        for program in eligibility.get("programs", []):
            subsidies_section["eligible"].append(
                {
                    "name": program.get("name", ""),
                    "category": program.get("category", ""),
                    "max_amount": program.get("max_chf") or program.get("max_chf_m2", 0),
                    "conditions": program.get("conditions", ""),
                }
            )
        subsidies_section["total_potential_chf"] = eligibility.get("max_amount", 0)
    except Exception:
        logger.warning("Subsidy eligibility failed for building %s", building_id)

    # --- 6. Unknowns ---
    unknowns_section: dict[str, Any] = {"count": 0, "critical": [], "blocking_safe_to_x": []}
    unknown_entries: list = []
    try:
        unknown_entries = await get_ledger(db, building_id, status="open")
        unknowns_section["count"] = len(unknown_entries)
        for entry in unknown_entries:
            severity = getattr(entry, "severity", "low")
            item = {
                "subject": getattr(entry, "subject", ""),
                "type": getattr(entry, "unknown_type", ""),
                "severity": severity,
            }
            if severity in ("critical", "high"):
                unknowns_section["critical"].append(item)
            blocks = getattr(entry, "blocks_safe_to_x", None)
            if blocks:
                unknowns_section["blocking_safe_to_x"].append(item)
    except Exception:
        logger.warning("Unknowns ledger failed for building %s", building_id)

    # --- 7. Caveats ---
    caveats_list: list[dict] = []
    try:
        caveats = await get_building_caveats(db, building_id, active_only=True)
        for c in caveats:
            caveats_list.append(
                {
                    "title": getattr(c, "title", ""),
                    "severity": getattr(c, "severity", "info"),
                    "description": getattr(c, "description", ""),
                }
            )
    except Exception:
        logger.warning("Caveats lookup failed for building %s", building_id)

    # --- 8. Next actions ---
    next_actions = _derive_next_actions(
        completeness_result,
        readiness_start_data,
        readiness_tender_data,
        unknown_entries,
        work_family,
    )

    # --- 9. Pack readiness ---
    pack_blockers = _compute_pack_blockers(readiness_start_data, completeness_result)

    return {
        "building_id": str(building_id),
        "work_type": work_type,
        "work_type_label": work_type_label,
        "readiness": {
            "verdict": overall_verdict,
            "safe_to_start": readiness_start_data,
            "safe_to_tender": readiness_tender_data,
        },
        "completeness": completeness_section,
        "procedures": procedures_section,
        "subsidies": subsidies_section,
        "unknowns": unknowns_section,
        "caveats": caveats_list,
        "next_actions": next_actions,
        "pack_ready": len(pack_blockers) == 0,
        "pack_blockers": pack_blockers,
        "passport_grade": passport.get("passport_grade", "F") if passport else "F",
        "assessed_at": datetime.now(UTC).isoformat(),
    }


async def generate_readiness_pack(
    db: AsyncSession,
    building_id: UUID,
    work_type: str,
    org_id: UUID | None = None,
    created_by_id: UUID | None = None,
) -> dict[str, Any]:
    """Generate a renovation readiness pack if assessment allows it.

    Uses pack_builder with authority pack type + conformance check.
    Returns the pack + conformance result.
    """
    # First assess readiness
    assessment = await assess_readiness(db, building_id, work_type, org_id)

    if assessment.get("error"):
        return assessment

    if not assessment.get("pack_ready"):
        return {
            "building_id": str(building_id),
            "work_type": work_type,
            "error": "pack_not_ready",
            "pack_blockers": assessment.get("pack_blockers", []),
        }

    # Generate pack using pack_builder
    try:
        pack_result = await generate_pack(
            db,
            building_id,
            "authority",
            org_id=org_id,
            created_by_id=created_by_id,
        )
        return {
            "building_id": str(building_id),
            "work_type": work_type,
            "work_type_label": assessment.get("work_type_label", work_type),
            "pack": {
                "pack_id": str(pack_result.pack_id),
                "version": pack_result.version,
                "sections_count": len(pack_result.sections),
                "generated_at": pack_result.generated_at,
            },
            "assessment_summary": {
                "verdict": assessment["readiness"]["verdict"],
                "completeness_pct": assessment["completeness"]["score_pct"],
                "passport_grade": assessment.get("passport_grade", "F"),
            },
        }
    except Exception as exc:
        logger.error("Pack generation failed for building %s: %s", building_id, exc)
        return {
            "building_id": str(building_id),
            "work_type": work_type,
            "error": "pack_generation_failed",
            "detail": str(exc),
        }


async def list_renovation_options(
    db: AsyncSession,
    building_id: UUID,
) -> list[dict[str, Any]]:
    """List available renovation types with quick readiness indicator for each.

    Returns a lightweight list without full assessment (fast).
    """
    # Get passport to confirm building exists
    passport = await get_passport_summary(db, building_id)
    if passport is None:
        return []

    options: list[dict[str, Any]] = []
    for name, defn in WORK_FAMILIES.items():
        options.append(
            {
                "work_type": name,
                "label_fr": defn.get("label_fr", name),
                "pollutant": defn.get("pollutant"),
                "regulatory_basis": defn.get("regulatory_basis", ""),
                "authorities": defn.get("authorities", []),
            }
        )

    return options
