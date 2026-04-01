"""Transaction-Ready Dossier Workflow -- assess, show gaps, generate pack, track.

Pure orchestrator: consumes existing services to produce a unified transaction
readiness assessment.  No new DB models.  Follows the G1 dossier_workflow_service
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
from app.models.ownership_record import OwnershipRecord
from app.models.sample import Sample
from app.models.unknowns_ledger import UnknownEntry

logger = logging.getLogger(__name__)

# Verdict levels (derived, never stored)
VERDICTS = ("not_ready", "conditional", "ready")

# Trust thresholds
_TRUST_LEVELS = [
    (0.8, "strong"),
    (0.6, "adequate"),
    (0.4, "review"),
]

# Pollutant status thresholds
_ALL_POLLUTANTS = {"asbestos", "pcb", "lead", "hap", "radon", "pfas"}

# Critical pollutants that block sale if missing
_CRITICAL_POLLUTANTS_FOR_SALE = {"asbestos", "pcb", "lead"}


def _trust_level(score_pct: float) -> str:
    """Map trust percentage to level string."""
    score = score_pct / 100.0
    for threshold, level in _TRUST_LEVELS:
        if score >= threshold:
            return level
    return "weak"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _get_passport(db: AsyncSession, building_id: UUID) -> dict | None:
    try:
        from app.services.passport_service import get_passport_summary

        return await get_passport_summary(db, building_id)
    except Exception:
        logger.warning("Failed to get passport for building %s", building_id)
        return None


async def _get_completeness(db: AsyncSession, building_id: UUID) -> dict:
    try:
        from app.services.completeness_engine import evaluate_completeness

        result = await evaluate_completeness(db, building_id)
        documented = [c.label_key for c in result.checks if c.status == "complete"]
        missing = result.missing_items
        # Critical missing: items that block transaction (pollutant-related)
        critical_keywords = ("amiante", "asbestos", "pcb", "plomb", "lead", "diagnostic")
        critical_missing = [m for m in missing if any(k in m.lower() for k in critical_keywords)]
        return {
            "score_pct": round(result.overall_score * 100, 1),
            "documented": documented,
            "missing": missing,
            "critical_missing": critical_missing,
        }
    except Exception:
        logger.warning("Failed to get completeness for building %s", building_id)
        return {
            "score_pct": 0.0,
            "documented": [],
            "missing": [],
            "critical_missing": [],
        }


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
            pct = round((trust.overall_score or 0.0) * 100, 1)
            return {"score_pct": pct, "level": _trust_level(pct)}
    except Exception:
        logger.warning("Failed to get trust for building %s", building_id)
    return {"score_pct": 0.0, "level": "weak"}


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
    blocking = [e.subject for e in entries if e.blocks_safe_to_x and "sell" in (e.blocks_safe_to_x or [])]
    return {
        "count": len(entries),
        "critical": critical[:5],
        "blocking_transaction": blocking[:5],
    }


async def _get_caveats(db: AsyncSession, building_id: UUID) -> dict:
    try:
        from app.services.commitment_service import get_building_caveats

        caveats = await get_building_caveats(db, building_id, active_only=True)
        items = [
            {
                "type": c.caveat_type,
                "subject": c.subject,
                "severity": c.severity,
                "applies_to": c.applies_to_audiences or [],
            }
            for c in caveats
        ]
        seller_caveats = [
            i
            for i in items
            if "seller" in (i.get("applies_to") or [])
            or i["type"] in ("seller_caveat", "scope_limitation", "data_quality_warning")
        ]
        buyer_risks = [
            i
            for i in items
            if "buyer" in (i.get("applies_to") or [])
            or i["type"] in ("coverage_gap", "unverified_claim", "temporal_limitation")
        ]
        return {
            "count": len(items),
            "items": items,
            "seller_caveats": seller_caveats,
            "buyer_risks": buyer_risks,
        }
    except Exception:
        logger.warning("Failed to get caveats for building %s", building_id)
        return {"count": 0, "items": [], "seller_caveats": [], "buyer_risks": []}


async def _get_incidents(db: AsyncSession, building_id: UUID) -> dict:
    try:
        from app.services.incident_service import get_incident_risk_profile

        profile = await get_incident_risk_profile(db, building_id)
        unresolved = profile.get("unresolved_count", 0)
        recurring = profile.get("recurring_count", 0)
        total = profile.get("total_incidents", 0)

        # Derive risk rating
        if total == 0:
            risk_rating = "low"
        elif unresolved >= 3 or recurring >= 2:
            risk_rating = "high"
        elif unresolved >= 1 or recurring >= 1:
            risk_rating = "elevated" if total >= 3 else "moderate"
        else:
            risk_rating = "low"

        return {
            "unresolved_count": unresolved,
            "recurring_count": recurring,
            "risk_rating": risk_rating,
        }
    except Exception:
        logger.warning("Failed to get incidents for building %s", building_id)
        return {"unresolved_count": 0, "recurring_count": 0, "risk_rating": "low"}


async def _get_ownership(db: AsyncSession, building_id: UUID) -> dict:
    result = await db.execute(
        select(OwnershipRecord).where(
            and_(
                OwnershipRecord.building_id == building_id,
                OwnershipRecord.status == "active",
            )
        )
    )
    records = list(result.scalars().all())
    documented = len(records) > 0
    # Best-effort name from contact
    current_owner = None
    if records:
        try:
            from app.models.contact import Contact

            first_record = records[0]
            if first_record.owner_type == "contact":
                contact_result = await db.execute(select(Contact).where(Contact.id == first_record.owner_id))
                contact = contact_result.scalar_one_or_none()
                if contact:
                    current_owner = (contact.name or "").strip() or None
        except Exception:
            pass
    return {"documented": documented, "current_owner": current_owner}


async def _get_pollutant_status(db: AsyncSession, building_id: UUID) -> str:
    """Derive pollutant status: clear / partial / at_risk."""
    result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
    diagnostics = list(result.scalars().all())
    if not diagnostics:
        return "at_risk"

    completed = [d for d in diagnostics if d.status in ("completed", "validated")]
    if not completed:
        return "at_risk"

    diag_ids = [d.id for d in completed]
    sample_result = await db.execute(select(Sample).where(Sample.diagnostic_id.in_(diag_ids)))
    samples = list(sample_result.scalars().all())

    has_exceeded = any(s.threshold_exceeded for s in samples)
    covered_pollutants = {(s.pollutant_type or "").lower() for s in samples}
    missing_critical = _CRITICAL_POLLUTANTS_FOR_SALE - covered_pollutants

    if has_exceeded:
        return "at_risk"
    if missing_critical:
        return "partial"
    return "clear"


def _derive_verdict(
    completeness: dict,
    trust: dict,
    contradictions: dict,
    unknowns: dict,
    incidents: dict,
    ownership: dict,
) -> tuple[str, str]:
    """Derive verdict and summary from assessment components.

    Returns: (verdict, verdict_summary)
    """
    blockers: list[str] = []
    conditions: list[str] = []

    # Critical missing docs block
    if completeness["critical_missing"]:
        blockers.append(f"{len(completeness['critical_missing'])} document(s) critique(s) manquant(s)")

    # Very low completeness blocks
    if completeness["score_pct"] < 50.0:
        blockers.append("Completude du dossier insuffisante (<50%)")

    # Critical unknowns block
    if unknowns["blocking_transaction"]:
        blockers.append(f"{len(unknowns['blocking_transaction'])} inconnu(s) bloquant la transaction")

    # Ownership not documented blocks
    if not ownership["documented"]:
        blockers.append("Propriete non documentee")

    # Conditions (non-blocking)
    if contradictions["count"] > 0:
        conditions.append(f"{contradictions['count']} contradiction(s) non resolue(s)")

    if trust["score_pct"] < 60.0:
        conditions.append("Score de confiance faible")

    if incidents["risk_rating"] in ("elevated", "high"):
        conditions.append("Profil d'incidents eleve")

    if completeness["score_pct"] < 70.0 and not any("Completude" in b for b in blockers):
        conditions.append("Completude du dossier a ameliorer")

    if blockers:
        summary = f"Le dossier n'est pas pret: {'; '.join(blockers)}"
        return "not_ready", summary
    if conditions:
        count = len(conditions)
        summary = f"Le dossier est pret sous {count} condition{'s' if count > 1 else ''}"
        return "conditional", summary
    return "ready", "Le dossier est pret pour la transaction"


def _derive_next_actions(
    completeness: dict,
    trust: dict,
    contradictions: dict,
    unknowns: dict,
    incidents: dict,
    ownership: dict,
) -> list[dict]:
    """Derive next actions from gaps."""
    actions: list[dict] = []

    for item in completeness.get("critical_missing", []):
        actions.append(
            {
                "title": f"Obtenir: {item}",
                "priority": "high",
                "action_type": "documentation",
            }
        )

    if not ownership["documented"]:
        actions.append(
            {
                "title": "Documenter la propriete de l'immeuble",
                "priority": "high",
                "action_type": "documentation",
            }
        )

    for item in unknowns.get("blocking_transaction", []):
        if not any(item in a["title"] for a in actions):
            actions.append(
                {
                    "title": f"Resoudre: {item}",
                    "priority": "high",
                    "action_type": "fix_blocker",
                }
            )

    if contradictions["count"] > 0:
        actions.append(
            {
                "title": f"Resoudre {contradictions['count']} contradiction(s)",
                "priority": "medium",
                "action_type": "data_quality",
            }
        )

    if trust["score_pct"] < 60.0:
        actions.append(
            {
                "title": "Ameliorer le score de confiance des donnees",
                "priority": "medium",
                "action_type": "data_quality",
            }
        )

    if incidents["unresolved_count"] > 0:
        actions.append(
            {
                "title": f"Traiter {incidents['unresolved_count']} incident(s) non resolu(s)",
                "priority": "medium",
                "action_type": "incident",
            }
        )

    return actions[:10]


def _derive_pack_readiness(verdict: str, completeness: dict, trust: dict) -> tuple[bool, list[str]]:
    """Check whether a transaction pack can be generated."""
    pack_blockers: list[str] = []
    if verdict == "not_ready":
        pack_blockers.append("Le dossier n'est pas pret (verdict: not_ready)")
    if completeness["score_pct"] < 50.0:
        pack_blockers.append("Completude du dossier trop faible pour generer un pack")
    return len(pack_blockers) == 0, pack_blockers


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class TransactionWorkflowService:
    """Orchestrates the full transaction-readiness lifecycle."""

    async def assess_transaction_readiness(
        self,
        db: AsyncSession,
        building_id: UUID,
    ) -> dict:
        """Full transaction readiness assessment.

        Returns a comprehensive dict covering all dimensions needed
        to decide whether a building can be sold, and what gaps remain.
        """
        building = await _get_building(db, building_id)

        # 1. Safe-to-sell evaluation (from existing transaction_readiness_service)
        safe_to_sell_data: dict = {"verdict": "unknown", "blockers": [], "conditions": []}
        try:
            from app.schemas.transaction_readiness import TransactionType
            from app.services.transaction_readiness_service import evaluate_transaction_readiness

            sell_result = await evaluate_transaction_readiness(db, building_id, TransactionType.sell)
            safe_to_sell_data = {
                "verdict": sell_result.overall_status.value if sell_result.overall_status else "unknown",
                "blockers": sell_result.blockers,
                "conditions": sell_result.conditions,
            }
        except Exception:
            logger.warning("Failed to evaluate safe_to_sell for %s", building_id)

        # 2-8. Parallel data gathering
        completeness = await _get_completeness(db, building_id)
        trust = await _get_trust(db, building_id)
        contradictions = await _get_contradictions(db, building_id)
        unknowns = await _get_unknowns(db, building_id)
        caveats = await _get_caveats(db, building_id)
        incidents = await _get_incidents(db, building_id)
        ownership = await _get_ownership(db, building_id)
        passport = await _get_passport(db, building_id)

        # 9. Derive verdict
        verdict, verdict_summary = _derive_verdict(completeness, trust, contradictions, unknowns, incidents, ownership)

        # 10. Buyer summary
        pollutant_status = await _get_pollutant_status(db, building_id)
        grade = passport.get("passport_grade", "F") if passport else "F"

        key_facts = []
        if building.construction_year:
            key_facts.append(f"Construction: {building.construction_year}")
        if building.renovation_year:
            key_facts.append(f"Renovation: {building.renovation_year}")
        if building.canton:
            key_facts.append(f"Canton: {building.canton}")
        key_facts.append(f"Completude: {completeness['score_pct']}%")

        key_risks = []
        for item in unknowns.get("critical", []):
            key_risks.append(item)
        for item in contradictions.get("items", [])[:2]:
            key_risks.append(item["description"])
        if incidents["risk_rating"] in ("elevated", "high"):
            key_risks.append(f"Profil d'incidents: {incidents['risk_rating']}")

        key_strengths = []
        if trust["level"] in ("strong", "adequate"):
            key_strengths.append(f"Confiance: {trust['level']}")
        if completeness["score_pct"] >= 80.0:
            key_strengths.append("Dossier bien documente")
        if pollutant_status == "clear":
            key_strengths.append("Aucun polluant depasse les seuils")
        if ownership["documented"]:
            key_strengths.append("Propriete documentee")

        buyer_summary = {
            "building_grade": grade,
            "year": building.construction_year,
            "address": building.address,
            "pollutant_status": pollutant_status,
            "key_facts": key_facts,
            "key_risks": key_risks[:5],
            "key_strengths": key_strengths[:5],
        }

        # 11. Next actions
        next_actions = _derive_next_actions(completeness, trust, contradictions, unknowns, incidents, ownership)

        # 12. Pack readiness
        pack_ready, pack_blockers = _derive_pack_readiness(verdict, completeness, trust)

        return {
            "building_id": str(building_id),
            "verdict": verdict,
            "verdict_summary": verdict_summary,
            "safe_to_sell": safe_to_sell_data,
            "completeness": completeness,
            "trust": trust,
            "contradictions": contradictions,
            "unknowns": unknowns,
            "caveats": caveats,
            "incidents": incidents,
            "ownership": ownership,
            "buyer_summary": buyer_summary,
            "next_actions": next_actions,
            "pack_ready": pack_ready,
            "pack_blockers": pack_blockers,
            "assessed_at": datetime.now(UTC).isoformat(),
        }

    async def generate_transaction_pack(
        self,
        db: AsyncSession,
        building_id: UUID,
        created_by_id: UUID,
        org_id: UUID | None = None,
        redact_financials: bool = True,
    ) -> dict:
        """Generate a transfer/due-diligence pack.

        Uses pack_builder with 'transfer' type + financial redaction.
        Runs conformance check.  Blocks when verdict == not_ready.
        """
        # Check readiness first
        assessment = await self.assess_transaction_readiness(db, building_id)
        if assessment["verdict"] == "not_ready":
            raise ValueError(
                "Impossible de generer le pack: le dossier n'est pas pret. "
                f"Blocages: {'; '.join(assessment['pack_blockers'])}"
            )

        from app.services.pack_builder_service import generate_pack

        pack_result = await generate_pack(
            db,
            building_id,
            pack_type="transfer",
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

    async def get_buyer_summary(
        self,
        db: AsyncSession,
        building_id: UUID,
    ) -> dict:
        """Buyer/advisor-facing summary: key facts, risks, strengths, grade, caveats.

        This is what a buyer sees before deciding to proceed.
        A PROJECTION of existing data, not new truth.
        """
        building = await _get_building(db, building_id)
        passport = await _get_passport(db, building_id)
        completeness = await _get_completeness(db, building_id)
        trust = await _get_trust(db, building_id)
        caveats = await _get_caveats(db, building_id)
        incidents = await _get_incidents(db, building_id)
        unknowns = await _get_unknowns(db, building_id)
        pollutant_status = await _get_pollutant_status(db, building_id)

        grade = passport.get("passport_grade", "F") if passport else "F"

        key_facts = []
        if building.construction_year:
            key_facts.append(f"Construction: {building.construction_year}")
        if building.renovation_year:
            key_facts.append(f"Renovation: {building.renovation_year}")
        if building.canton:
            key_facts.append(f"Canton: {building.canton}")
        if building.building_type:
            key_facts.append(f"Type: {building.building_type}")
        key_facts.append(f"Completude: {completeness['score_pct']}%")

        key_risks = []
        if pollutant_status == "at_risk":
            key_risks.append("Statut polluants a risque")
        elif pollutant_status == "partial":
            key_risks.append("Couverture polluants partielle")
        for item in unknowns.get("critical", [])[:3]:
            key_risks.append(item)
        if incidents["risk_rating"] in ("elevated", "high"):
            key_risks.append(f"Profil d'incidents: {incidents['risk_rating']}")
        for caveat in caveats.get("buyer_risks", [])[:2]:
            key_risks.append(caveat.get("subject", ""))

        key_strengths = []
        if trust["level"] in ("strong", "adequate"):
            key_strengths.append(f"Score de confiance: {trust['level']}")
        if completeness["score_pct"] >= 80.0:
            key_strengths.append("Dossier bien documente")
        if pollutant_status == "clear":
            key_strengths.append("Polluants sous les seuils reglementaires")
        if incidents["risk_rating"] == "low":
            key_strengths.append("Historique d'incidents faible")

        return {
            "building_id": str(building_id),
            "building_grade": grade,
            "year": building.construction_year,
            "address": building.address,
            "city": building.city,
            "canton": building.canton,
            "pollutant_status": pollutant_status,
            "key_facts": key_facts,
            "key_risks": key_risks[:5],
            "key_strengths": key_strengths[:5],
            "caveats_count": caveats["count"],
            "buyer_risks": caveats.get("buyer_risks", []),
            "trust_level": trust["level"],
            "completeness_pct": completeness["score_pct"],
            "generated_at": datetime.now(UTC).isoformat(),
        }
