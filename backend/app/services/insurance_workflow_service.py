"""Insurance-Ready Dossier Workflow -- assess, show risks/incidents/caveats, generate pack.

Pure orchestrator: consumes existing services to produce a unified insurance
readiness assessment.  No new DB models.  Follows the T1 transaction_workflow_service
pattern: derive state from existing data, never store lifecycle.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.data_quality_issue import DataQualityIssue
from app.models.diagnostic import Diagnostic
from app.models.incident import IncidentEpisode
from app.models.sample import Sample
from app.models.unknowns_ledger import UnknownEntry

logger = logging.getLogger(__name__)

# Verdict levels (derived, never stored)
VERDICTS = ("not_insurable", "conditional", "insurable")

# Risk rating levels
_RISK_RATINGS = ("low", "moderate", "elevated", "high")

# Pollutant statuses
_POLLUTANT_STATUSES = ("clear", "traces", "present", "unknown")

# All pollutants tracked
_ALL_POLLUTANTS = {"asbestos", "pcb", "lead", "hap", "radon", "pfas"}

# Pollutants relevant for insurance (core)
_INSURANCE_POLLUTANTS = {"asbestos", "pcb", "lead"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _get_safe_to_insure(db: AsyncSession, building_id: UUID) -> dict:
    """Get safe_to_insure evaluation from transaction_readiness_service."""
    try:
        from app.schemas.transaction_readiness import TransactionType
        from app.services.transaction_readiness_service import evaluate_transaction_readiness

        result = await evaluate_transaction_readiness(db, building_id, TransactionType.insure)
        return {
            "verdict": result.overall_status.value if result.overall_status else "unknown",
            "blockers": result.blockers,
            "conditions": result.conditions,
        }
    except Exception:
        logger.warning("Failed to evaluate safe_to_insure for %s", building_id)
        return {"verdict": "unknown", "blockers": [], "conditions": []}


async def _get_risk_profile(db: AsyncSession, building_id: UUID) -> dict:
    """Get incident risk profile from incident_service."""
    try:
        from app.services.incident_service import get_incident_risk_profile

        profile = await get_incident_risk_profile(db, building_id)
        return {
            "overall_rating": profile.get("most_common_cause", "low"),
            "incident_count": profile.get("total_incidents", 0),
            "unresolved_incidents": profile.get("unresolved_count", 0),
            "recurring_patterns": profile.get("recurring_count", 0),
            "total_claim_cost_chf": profile.get("total_repair_cost_chf", 0.0),
        }
    except Exception:
        logger.warning("Failed to get risk profile for %s", building_id)
        return {
            "overall_rating": "unknown",
            "incident_count": 0,
            "unresolved_incidents": 0,
            "recurring_patterns": 0,
            "total_claim_cost_chf": 0.0,
        }


async def _get_insurer_incident_summary(db: AsyncSession, building_id: UUID) -> dict:
    """Get insurer-formatted incident summary."""
    try:
        from app.services.incident_service import get_insurer_incident_summary

        return await get_insurer_incident_summary(db, building_id)
    except Exception:
        logger.warning("Failed to get insurer incident summary for %s", building_id)
        return {
            "total_incidents": 0,
            "claims_filed": 0,
            "unresolved_incidents": 0,
            "recurring_risks": 0,
            "total_damage_cost_chf": 0.0,
            "risk_rating": "low",
        }


async def _get_completeness(db: AsyncSession, building_id: UUID) -> dict:
    try:
        from app.services.completeness_engine import evaluate_completeness

        result = await evaluate_completeness(db, building_id)
        documented = [c.label_key for c in result.checks if c.status == "complete"]
        missing = result.missing_items
        return {
            "score_pct": round(result.overall_score * 100, 1),
            "documented": documented,
            "missing": missing,
        }
    except Exception:
        logger.warning("Failed to get completeness for %s", building_id)
        return {"score_pct": 0.0, "documented": [], "missing": []}


async def _get_pollutant_status(db: AsyncSession, building_id: UUID) -> dict:
    """Derive per-pollutant status for insurance assessment."""
    result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(result.scalars().all())

    completed = [d for d in diagnostics if d.status in ("completed", "validated")]
    diag_ids = [d.id for d in completed]

    samples: list[Sample] = []
    if diag_ids:
        sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
        samples = list(sample_result.scalars().all())

    # Per-pollutant status
    pollutant_map: dict[str, str] = {}
    for pollutant in ("asbestos", "pcb", "lead"):
        p_samples = [s for s in samples if (s.pollutant_type or "").lower() == pollutant]
        if not p_samples:
            pollutant_map[pollutant] = "unknown"
        elif any(s.threshold_exceeded for s in p_samples):
            pollutant_map[pollutant] = "present"
        elif any((s.concentration or 0) > 0 for s in p_samples):
            pollutant_map[pollutant] = "traces"
        else:
            pollutant_map[pollutant] = "clear"

    # Radon special case (no traces concept)
    radon_samples = [s for s in samples if (s.pollutant_type or "").lower() == "radon"]
    if not radon_samples:
        pollutant_map["radon"] = "unknown"
    elif any(s.threshold_exceeded for s in radon_samples):
        pollutant_map["radon"] = "elevated"
    else:
        pollutant_map["radon"] = "clear"

    # Overall status
    statuses = list(pollutant_map.values())
    if "present" in statuses:
        overall = "at_risk"
    elif "unknown" in statuses or "elevated" in statuses or "traces" in statuses:
        overall = "partial_risk"
    else:
        overall = "clear"

    return {
        "asbestos": pollutant_map.get("asbestos", "unknown"),
        "pcb": pollutant_map.get("pcb", "unknown"),
        "lead": pollutant_map.get("lead", "unknown"),
        "radon": pollutant_map.get("radon", "unknown"),
        "overall": overall,
    }


async def _get_contradictions(db: AsyncSession, building_id: UUID) -> dict:
    result = await db.execute(
        select(DataQualityIssue).where(
            and_(
                DataQualityIssue.building_id == building_id,
                DataQualityIssue.issue_type == "contradiction",
                DataQualityIssue.status != "resolved",
            )
        )
    )
    issues = list(result.scalars().all())
    items = [
        {
            "description": i.description or "Contradiction detectee",
            "severity": i.severity or "medium",
        }
        for i in issues
    ]
    return {"count": len(items), "items": items}


async def _get_unknowns(db: AsyncSession, building_id: UUID) -> dict:
    result = await db.execute(
        select(UnknownEntry).where(
            and_(
                UnknownEntry.building_id == building_id,
                UnknownEntry.status.in_(["open", "investigating"]),
            )
        )
    )
    entries = list(result.scalars().all())
    critical = [e.subject for e in entries if e.severity == "critical"]
    blocking = [e.subject for e in entries if e.blocks_safe_to_x and "insure" in (e.blocks_safe_to_x or [])]
    return {
        "count": len(entries),
        "critical": critical[:5],
        "blocking_insurance": blocking[:5],
    }


async def _get_caveats(db: AsyncSession, building_id: UUID) -> dict:
    """Get caveats structured for insurer audience."""
    try:
        from app.services.commitment_service import get_building_caveats, get_caveats_for_pack

        # Pack-specific caveats (insurer)
        pack_caveats = await get_caveats_for_pack(db, building_id, "insurer")
        all_caveats = await get_building_caveats(db, building_id, active_only=True)

        insurer_exclusions = [
            {
                "type": c.caveat_type,
                "subject": c.subject,
                "severity": c.severity,
            }
            for c in all_caveats
            if c.caveat_type in ("insurer_exclusion", "contractor_exclusion")
        ]

        coverage_gaps = [
            {
                "type": c.caveat_type,
                "subject": c.subject,
                "severity": c.severity,
            }
            for c in all_caveats
            if c.caveat_type == "coverage_gap"
        ]

        implied_conditions = [
            {
                "type": c.caveat_type,
                "subject": c.subject,
                "severity": c.severity,
            }
            for c in all_caveats
            if c.caveat_type in ("authority_condition", "scope_limitation", "temporal_limitation")
        ]

        return {
            "count": len(pack_caveats),
            "insurer_exclusions": insurer_exclusions,
            "coverage_gaps": coverage_gaps,
            "implied_conditions": implied_conditions,
        }
    except Exception:
        logger.warning("Failed to get caveats for %s", building_id)
        return {
            "count": 0,
            "insurer_exclusions": [],
            "coverage_gaps": [],
            "implied_conditions": [],
        }


async def _get_incidents(db: AsyncSession, building_id: UUID) -> dict:
    """Get incident data structured for insurance assessment."""
    all_q = select(IncidentEpisode).where(IncidentEpisode.building_id == building_id)
    all_incidents = list((await db.execute(all_q)).scalars().all())

    unresolved = [
        {
            "title": i.title,
            "type": i.incident_type,
            "severity": i.severity,
            "discovered_at": i.discovered_at.isoformat() if i.discovered_at else None,
        }
        for i in all_incidents
        if i.status not in ("resolved",)
    ]

    recurring = [
        {
            "title": i.title,
            "type": i.incident_type,
            "severity": i.severity,
        }
        for i in all_incidents
        if i.recurring
    ]

    # Recent: last 12 months
    now = datetime.now(UTC)
    recent = []
    for i in all_incidents:
        if not i.discovered_at:
            continue
        discovered = i.discovered_at
        # Normalize timezone awareness for comparison
        if discovered.tzinfo is None:
            discovered = discovered.replace(tzinfo=UTC)
        if (now - discovered).days <= 365:
            recent.append(
                {
                    "title": i.title,
                    "type": i.incident_type,
                    "severity": i.severity,
                    "discovered_at": i.discovered_at.isoformat() if i.discovered_at else None,
                    "resolved": i.status == "resolved",
                }
            )

    return {
        "total": len(all_incidents),
        "unresolved": unresolved,
        "recurring": recurring,
        "recent": recent,
    }


async def _get_passport(db: AsyncSession, building_id: UUID) -> dict | None:
    try:
        from app.services.passport_service import get_passport_summary

        return await get_passport_summary(db, building_id)
    except Exception:
        logger.warning("Failed to get passport for %s", building_id)
        return None


async def _get_trust(db: AsyncSession, building_id: UUID) -> dict:
    try:
        from app.models.building_trust_score_v2 import BuildingTrustScore

        result = await db.execute(
            select(BuildingTrustScore)
            .where(BuildingTrustScore.building_id == building_id)
            .order_by(BuildingTrustScore.assessed_at.desc())
            .limit(1)
        )
        trust = result.scalar_one_or_none()
        if trust:
            return {"score_pct": round((trust.overall_score or 0.0) * 100, 1)}
    except Exception:
        logger.warning("Failed to get trust for %s", building_id)
    return {"score_pct": 0.0}


def _derive_risk_rating(
    insurer_summary: dict,
    incidents: dict,
    pollutant_status: dict,
    unknowns: dict,
) -> str:
    """Derive overall risk rating from multiple signals."""
    # Start from insurer summary rating if available
    base_rating = insurer_summary.get("risk_rating", "low")

    # Escalate based on pollutant status
    if pollutant_status["overall"] == "at_risk" and base_rating in ("low", "moderate"):
        base_rating = "elevated"

    # Escalate based on unknowns
    if len(unknowns.get("blocking_insurance", [])) >= 2 and base_rating in ("low", "moderate"):
        base_rating = "elevated"

    # Escalate based on unresolved incidents
    if len(incidents.get("unresolved", [])) >= 3:
        base_rating = "high"

    return base_rating


def _derive_verdict(
    safe_to_insure: dict,
    risk_rating: str,
    incidents: dict,
    pollutant_status: dict,
    unknowns: dict,
    contradictions: dict,
) -> tuple[str, str]:
    """Derive insurance verdict and summary.

    Returns: (verdict, verdict_summary)

    Only hard signals block insurability (high risk rating, active pollutant
    exceedance). Safe-to-insure blockers are treated as conditions since they
    are advisory checks that may not have enough data to evaluate.
    """
    blockers: list[str] = []
    conditions: list[str] = []

    # High risk rating blocks
    if risk_rating == "high":
        blockers.append("Profil de risque eleve")

    # Active pollutant presence blocks
    if pollutant_status["overall"] == "at_risk":
        blockers.append("Polluant actif depasse les seuils reglementaires")

    # Safe-to-insure blockers are conditions (advisory, not hard-blocking)
    for b in safe_to_insure.get("blockers", []):
        conditions.append(b)

    # Conditions from safe_to_insure
    for c in safe_to_insure.get("conditions", []):
        conditions.append(c)

    if incidents.get("unresolved"):
        conditions.append(f"{len(incidents['unresolved'])} incident(s) non resolu(s)")

    if incidents.get("recurring"):
        conditions.append(f"{len(incidents['recurring'])} schema(s) recurrent(s)")

    if pollutant_status["overall"] == "partial_risk":
        conditions.append("Couverture polluants partielle ou traces detectees")

    if unknowns.get("blocking_insurance"):
        conditions.append(f"{len(unknowns['blocking_insurance'])} inconnu(s) bloquant l'assurance")

    if contradictions["count"] > 0:
        conditions.append(f"{contradictions['count']} contradiction(s) non resolue(s)")

    if blockers:
        summary = f"Non assurable: {'; '.join(blockers)}"
        return "not_insurable", summary
    if conditions:
        count = len(conditions)
        summary = f"Assurable sous {count} condition{'s' if count > 1 else ''}"
        return "conditional", summary
    return "insurable", "Le batiment est assurable sans reserve"


def _derive_next_actions(
    safe_to_insure: dict,
    incidents: dict,
    pollutant_status: dict,
    unknowns: dict,
    contradictions: dict,
    completeness: dict,
) -> list[dict]:
    """Derive next actions from gaps."""
    actions: list[dict] = []

    # Blockers first
    for blocker in safe_to_insure.get("blockers", []):
        actions.append(
            {
                "title": f"Resoudre: {blocker}",
                "priority": "high",
                "action_type": "fix_blocker",
            }
        )

    # Unresolved incidents
    for inc in incidents.get("unresolved", [])[:3]:
        actions.append(
            {
                "title": f"Resoudre incident: {inc['title']}",
                "priority": "high",
                "action_type": "incident",
            }
        )

    # Unknown pollutants
    for pollutant, status in pollutant_status.items():
        if pollutant == "overall":
            continue
        if status == "unknown":
            actions.append(
                {
                    "title": f"Effectuer diagnostic {pollutant}",
                    "priority": "medium",
                    "action_type": "diagnostic",
                }
            )

    # Unknowns blocking insurance
    for item in unknowns.get("blocking_insurance", []):
        if not any(item in a["title"] for a in actions):
            actions.append(
                {
                    "title": f"Resoudre: {item}",
                    "priority": "medium",
                    "action_type": "fix_blocker",
                }
            )

    # Contradictions
    if contradictions["count"] > 0:
        actions.append(
            {
                "title": f"Resoudre {contradictions['count']} contradiction(s)",
                "priority": "medium",
                "action_type": "data_quality",
            }
        )

    # Missing docs
    for item in completeness.get("missing", [])[:3]:
        actions.append(
            {
                "title": f"Obtenir: {item}",
                "priority": "low",
                "action_type": "documentation",
            }
        )

    return actions[:10]


def _derive_pack_readiness(verdict: str, completeness: dict) -> tuple[bool, list[str]]:
    """Check whether an insurer pack can be generated."""
    pack_blockers: list[str] = []
    if verdict == "not_insurable":
        pack_blockers.append("Le batiment n'est pas assurable (verdict: not_insurable)")
    if completeness["score_pct"] < 30.0:
        pack_blockers.append("Completude du dossier trop faible pour generer un pack")
    return len(pack_blockers) == 0, pack_blockers


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class InsuranceWorkflowService:
    """Orchestrates the full insurance readiness assessment lifecycle."""

    async def assess_insurance_readiness(
        self,
        db: AsyncSession,
        building_id: UUID,
    ) -> dict:
        """Full insurance readiness assessment.

        Returns a comprehensive dict covering all dimensions needed
        to decide whether a building can be insured, and what gaps remain.
        """
        building = await _get_building(db, building_id)

        # 1. Safe-to-insure evaluation (from transaction_readiness_service)
        safe_to_insure = await _get_safe_to_insure(db, building_id)

        # 2. Insurer incident summary
        insurer_summary_raw = await _get_insurer_incident_summary(db, building_id)

        # 3. Data gathering
        completeness = await _get_completeness(db, building_id)
        pollutant_status = await _get_pollutant_status(db, building_id)
        contradictions = await _get_contradictions(db, building_id)
        unknowns = await _get_unknowns(db, building_id)
        caveats = await _get_caveats(db, building_id)
        incidents = await _get_incidents(db, building_id)
        passport = await _get_passport(db, building_id)
        trust = await _get_trust(db, building_id)

        # 4. Risk profile
        risk_profile = {
            "overall_rating": insurer_summary_raw.get("risk_rating", "low"),
            "incident_count": insurer_summary_raw.get("total_incidents", 0),
            "unresolved_incidents": insurer_summary_raw.get("unresolved_incidents", 0),
            "recurring_patterns": insurer_summary_raw.get("recurring_risks", 0),
            "total_claim_cost_chf": insurer_summary_raw.get("total_damage_cost_chf", 0.0),
        }

        # 5. Derive overall risk rating
        overall_risk = _derive_risk_rating(insurer_summary_raw, incidents, pollutant_status, unknowns)
        risk_profile["overall_rating"] = overall_risk

        # 6. Derive verdict
        verdict, verdict_summary = _derive_verdict(
            safe_to_insure, overall_risk, incidents, pollutant_status, unknowns, contradictions
        )

        # 7. Insurer-facing summary
        grade = passport.get("passport_grade", "F") if passport else "F"

        key_risks = []
        if pollutant_status["overall"] in ("at_risk", "partial_risk"):
            key_risks.append(f"Statut polluants: {pollutant_status['overall']}")
        for inc in incidents.get("unresolved", [])[:2]:
            key_risks.append(f"Incident non resolu: {inc['title']}")
        if unknowns.get("blocking_insurance"):
            key_risks.append(f"{len(unknowns['blocking_insurance'])} inconnu(s) bloquant")

        key_strengths = []
        if trust["score_pct"] >= 60.0:
            key_strengths.append(f"Score de confiance: {trust['score_pct']}%")
        if completeness["score_pct"] >= 80.0:
            key_strengths.append("Dossier bien documente")
        if pollutant_status["overall"] == "clear":
            key_strengths.append("Polluants sous les seuils reglementaires")
        if not incidents.get("unresolved"):
            key_strengths.append("Aucun incident non resolu")

        recommended_inspections = []
        for p, s in pollutant_status.items():
            if p != "overall" and s == "unknown":
                recommended_inspections.append(f"Diagnostic {p}")
        if incidents.get("recurring"):
            recommended_inspections.append("Inspection technique recurrence sinistres")

        insurer_summary = {
            "building_grade": grade,
            "year": building.construction_year,
            "address": building.address,
            "risk_rating": overall_risk,
            "key_risks": key_risks[:5],
            "key_strengths": key_strengths[:5],
            "recommended_inspections": recommended_inspections[:5],
        }

        # 8. Next actions
        next_actions = _derive_next_actions(
            safe_to_insure, incidents, pollutant_status, unknowns, contradictions, completeness
        )

        # 9. Pack readiness
        pack_ready, pack_blockers = _derive_pack_readiness(verdict, completeness)

        return {
            "building_id": str(building_id),
            "verdict": verdict,
            "verdict_summary": verdict_summary,
            "safe_to_insure": safe_to_insure,
            "risk_profile": risk_profile,
            "completeness": completeness,
            "pollutant_status": pollutant_status,
            "contradictions": contradictions,
            "unknowns": unknowns,
            "caveats": caveats,
            "incidents": incidents,
            "insurer_summary": insurer_summary,
            "next_actions": next_actions,
            "pack_ready": pack_ready,
            "pack_blockers": pack_blockers,
            "assessed_at": datetime.now(UTC).isoformat(),
        }

    async def generate_insurer_pack(
        self,
        db: AsyncSession,
        building_id: UUID,
        created_by_id: UUID,
        org_id: UUID | None = None,
        redact_financials: bool = True,
    ) -> dict:
        """Generate insurer-facing pack using pack_builder with 'insurer' type.

        Runs conformance. Returns pack + conformance result.
        Blocks when verdict == not_insurable.
        """
        # Check readiness first
        assessment = await self.assess_insurance_readiness(db, building_id)
        if assessment["verdict"] == "not_insurable":
            raise ValueError(
                "Impossible de generer le pack: le batiment n'est pas assurable. "
                f"Blocages: {'; '.join(assessment['pack_blockers'])}"
            )

        from app.services.pack_builder_service import generate_pack

        pack_result = await generate_pack(
            db,
            building_id,
            pack_type="insurer",
            org_id=org_id,
            created_by_id=created_by_id,
            redact_financials=redact_financials,
        )

        return {
            "pack_id": str(pack_result.pack_id),
            "overall_completeness": pack_result.overall_completeness,
            "total_sections": pack_result.total_sections,
            "sha256_hash": pack_result.sha256_hash,
            "financials_redacted": redact_financials,
            "assessment": assessment,
        }

    async def get_insurer_summary(
        self,
        db: AsyncSession,
        building_id: UUID,
    ) -> dict:
        """Insurer-facing summary: risk profile, incidents, caveats, grade.

        A PROJECTION of existing data, not new truth.
        """
        building = await _get_building(db, building_id)
        passport = await _get_passport(db, building_id)
        incidents = await _get_incidents(db, building_id)
        caveats = await _get_caveats(db, building_id)
        pollutant_status = await _get_pollutant_status(db, building_id)
        insurer_summary_raw = await _get_insurer_incident_summary(db, building_id)
        trust = await _get_trust(db, building_id)
        completeness = await _get_completeness(db, building_id)

        grade = passport.get("passport_grade", "F") if passport else "F"
        risk_rating = insurer_summary_raw.get("risk_rating", "low")

        key_facts = []
        if building.construction_year:
            key_facts.append(f"Construction: {building.construction_year}")
        if building.renovation_year:
            key_facts.append(f"Renovation: {building.renovation_year}")
        if building.canton:
            key_facts.append(f"Canton: {building.canton}")
        key_facts.append(f"Completude: {completeness['score_pct']}%")

        key_risks = []
        if pollutant_status["overall"] in ("at_risk", "partial_risk"):
            key_risks.append(f"Statut polluants: {pollutant_status['overall']}")
        for inc in incidents.get("unresolved", [])[:2]:
            key_risks.append(f"Incident non resolu: {inc['title']}")
        if incidents.get("recurring"):
            key_risks.append(f"{len(incidents['recurring'])} schema(s) recurrent(s)")

        key_strengths = []
        if trust["score_pct"] >= 60.0:
            key_strengths.append(f"Score de confiance: {trust['score_pct']}%")
        if completeness["score_pct"] >= 80.0:
            key_strengths.append("Dossier bien documente")
        if pollutant_status["overall"] == "clear":
            key_strengths.append("Polluants sous les seuils")
        if not incidents.get("unresolved"):
            key_strengths.append("Aucun incident non resolu")

        return {
            "building_id": str(building_id),
            "building_grade": grade,
            "year": building.construction_year,
            "address": building.address,
            "city": building.city,
            "canton": building.canton,
            "risk_rating": risk_rating,
            "pollutant_status": pollutant_status,
            "incidents_total": incidents["total"],
            "incidents_unresolved": len(incidents["unresolved"]),
            "incidents_recurring": len(incidents["recurring"]),
            "caveats_count": caveats["count"],
            "insurer_exclusions": caveats["insurer_exclusions"],
            "coverage_gaps": caveats["coverage_gaps"],
            "key_facts": key_facts,
            "key_risks": key_risks[:5],
            "key_strengths": key_strengths[:5],
            "trust_score_pct": trust["score_pct"],
            "completeness_pct": completeness["score_pct"],
            "generated_at": datetime.now(UTC).isoformat(),
        }
