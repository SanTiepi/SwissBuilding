"""Finance/Lender-Ready Dossier Workflow -- assess, show collateral gaps, generate lender pack.

Pure orchestrator: consumes existing services to produce a unified finance
readiness assessment.  No new DB models.  Follows the I1 insurance_workflow_service
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
from app.models.incident import IncidentEpisode
from app.models.unknowns_ledger import UnknownEntry

logger = logging.getLogger(__name__)

# Verdict levels (derived, never stored)
VERDICTS = ("not_financeable", "conditional", "financeable")

# Collateral confidence levels
_COLLATERAL_LEVELS = ("strong", "adequate", "weak", "insufficient")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _get_safe_to_finance(db: AsyncSession, building_id: UUID) -> dict:
    """Get safe_to_finance evaluation from transaction_readiness_service."""
    try:
        from app.schemas.transaction_readiness import TransactionType
        from app.services.transaction_readiness_service import evaluate_transaction_readiness

        result = await evaluate_transaction_readiness(db, building_id, TransactionType.finance)
        return {
            "verdict": result.overall_status.value if result.overall_status else "unknown",
            "blockers": result.blockers,
            "conditions": result.conditions,
        }
    except Exception:
        logger.warning("Failed to evaluate safe_to_finance for %s", building_id)
        return {"verdict": "unknown", "blockers": [], "conditions": []}


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
            score = round((trust.overall_score or 0.0) * 100, 1)
            level = (
                "strong" if score >= 75 else "adequate" if score >= 50 else "weak" if score >= 30 else "insufficient"
            )
            return {"score_pct": score, "level": level}
    except Exception:
        logger.warning("Failed to get trust for %s", building_id)
    return {"score_pct": 0.0, "level": "insufficient"}


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
    blocking = [e.subject for e in entries if e.blocks_safe_to_x and "finance" in (e.blocks_safe_to_x or [])]
    return {
        "count": len(entries),
        "critical": critical[:5],
        "blocking_finance": blocking[:5],
    }


async def _get_caveats(db: AsyncSession, building_id: UUID) -> dict:
    """Get caveats structured for lender audience."""
    try:
        from app.services.commitment_service import get_building_caveats, get_caveats_for_pack

        pack_caveats = await get_caveats_for_pack(db, building_id, "lender")
        all_caveats = await get_building_caveats(db, building_id, active_only=True)

        lender_conditions = [
            {
                "type": c.caveat_type,
                "subject": c.subject,
                "severity": c.severity,
            }
            for c in all_caveats
            if c.caveat_type in ("authority_condition", "scope_limitation", "temporal_limitation")
        ]

        collateral_risks = [
            {
                "type": c.caveat_type,
                "subject": c.subject,
                "severity": c.severity,
            }
            for c in all_caveats
            if c.caveat_type in ("insurer_exclusion", "contractor_exclusion", "coverage_gap")
        ]

        documentation_gaps = [
            {
                "type": c.caveat_type,
                "subject": c.subject,
                "severity": c.severity,
            }
            for c in all_caveats
            if c.caveat_type == "documentation_gap"
        ]

        return {
            "count": len(pack_caveats),
            "lender_conditions": lender_conditions,
            "collateral_risks": collateral_risks,
            "documentation_gaps": documentation_gaps,
        }
    except Exception:
        logger.warning("Failed to get caveats for %s", building_id)
        return {
            "count": 0,
            "lender_conditions": [],
            "collateral_risks": [],
            "documentation_gaps": [],
        }


async def _get_incidents(db: AsyncSession, building_id: UUID) -> dict:
    """Get incident data for finance assessment."""
    all_q = select(IncidentEpisode).where(IncidentEpisode.building_id == building_id)
    all_incidents = list((await db.execute(all_q)).scalars().all())

    unresolved = [i for i in all_incidents if i.status not in ("resolved",)]
    recurring = [i for i in all_incidents if i.recurring]

    # Risk rating from incident profile
    risk_rating = "low"
    if len(unresolved) >= 3:
        risk_rating = "high"
    elif len(unresolved) >= 1 or len(recurring) >= 1:
        risk_rating = "moderate"

    return {
        "unresolved_count": len(unresolved),
        "recurring_count": len(recurring),
        "risk_rating": risk_rating,
    }


async def _get_passport(db: AsyncSession, building_id: UUID) -> dict | None:
    try:
        from app.services.passport_service import get_passport_summary

        return await get_passport_summary(db, building_id)
    except Exception:
        logger.warning("Failed to get passport for %s", building_id)
        return None


def _derive_collateral_confidence(
    trust: dict,
    completeness: dict,
    contradictions: dict,
    incidents: dict,
) -> dict:
    """Derive collateral confidence from multiple signals."""
    factors: list[dict] = []

    # Trust factor
    trust_pct = trust["score_pct"]
    if trust_pct >= 75:
        factors.append({"name": "Score de confiance", "status": "strong", "impact": "positive"})
    elif trust_pct >= 50:
        factors.append({"name": "Score de confiance", "status": "adequate", "impact": "neutral"})
    else:
        factors.append({"name": "Score de confiance", "status": "weak", "impact": "negative"})

    # Completeness factor
    comp_pct = completeness["score_pct"]
    if comp_pct >= 80:
        factors.append({"name": "Completude du dossier", "status": "strong", "impact": "positive"})
    elif comp_pct >= 50:
        factors.append({"name": "Completude du dossier", "status": "adequate", "impact": "neutral"})
    else:
        factors.append({"name": "Completude du dossier", "status": "weak", "impact": "negative"})

    # Contradiction factor
    contra_count = contradictions["count"]
    if contra_count == 0:
        factors.append({"name": "Coherence des donnees", "status": "strong", "impact": "positive"})
    elif contra_count <= 2:
        factors.append({"name": "Coherence des donnees", "status": "adequate", "impact": "neutral"})
    else:
        factors.append({"name": "Coherence des donnees", "status": "weak", "impact": "negative"})

    # Incident factor
    inc_risk = incidents["risk_rating"]
    if inc_risk == "low":
        factors.append({"name": "Historique sinistres", "status": "strong", "impact": "positive"})
    elif inc_risk == "moderate":
        factors.append({"name": "Historique sinistres", "status": "adequate", "impact": "neutral"})
    else:
        factors.append({"name": "Historique sinistres", "status": "weak", "impact": "negative"})

    # Compute composite score (weighted average)
    status_scores = {"strong": 100, "adequate": 65, "weak": 35, "insufficient": 0}
    weights = [0.35, 0.25, 0.20, 0.20]  # trust, completeness, contradictions, incidents
    total = sum(status_scores.get(f["status"], 0) * w for f, w in zip(factors, weights, strict=True))
    score_pct = round(total, 1)

    if score_pct >= 75:
        level = "strong"
    elif score_pct >= 50:
        level = "adequate"
    elif score_pct >= 30:
        level = "weak"
    else:
        level = "insufficient"

    return {
        "score_pct": score_pct,
        "level": level,
        "factors": factors,
    }


def _derive_verdict(
    safe_to_finance: dict,
    trust: dict,
    unknowns: dict,
    contradictions: dict,
    incidents: dict,
    completeness: dict,
) -> tuple[str, str]:
    """Derive finance verdict and summary.

    Returns: (verdict, verdict_summary)

    not_financeable: no ownership docs OR critical unknowns blocking finance OR trust < 30%
    conditional: contradictions, moderate unknowns, incidents, incomplete completeness
    financeable: ownership clear, trust adequate+, no critical blockers
    """
    blockers: list[str] = []
    conditions: list[str] = []

    # Critical unknowns blocking finance -- hard blocker
    if unknowns.get("blocking_finance"):
        blockers.append(f"{len(unknowns['blocking_finance'])} inconnu(s) critique(s) bloquant le financement")

    # Safe-to-finance blockers are treated as conditions (advisory, not hard-blocking)
    for b in safe_to_finance.get("blockers", []):
        conditions.append(b)

    # Trust below 30% is a condition (not hard-blocking; may simply lack data)
    if trust["score_pct"] < 30.0:
        conditions.append("Score de confiance insuffisant (<30%)")

    # Conditions from safe_to_finance
    for c in safe_to_finance.get("conditions", []):
        conditions.append(c)

    if contradictions["count"] > 0:
        conditions.append(f"{contradictions['count']} contradiction(s) non resolue(s)")

    if unknowns["count"] > 0 and not unknowns.get("blocking_finance"):
        conditions.append(f"{unknowns['count']} inconnu(s) en attente")

    if incidents["unresolved_count"] > 0:
        conditions.append(f"{incidents['unresolved_count']} incident(s) non resolu(s)")

    if completeness["score_pct"] < 60.0:
        conditions.append("Completude du dossier insuffisante pour un financement")

    if blockers:
        summary = f"Non financable: {'; '.join(blockers)}"
        return "not_financeable", summary
    if conditions:
        count = len(conditions)
        summary = f"Financable sous {count} condition{'s' if count > 1 else ''}"
        return "conditional", summary
    return "financeable", "Le batiment est financable sans reserve"


def _derive_next_actions(
    safe_to_finance: dict,
    unknowns: dict,
    contradictions: dict,
    incidents: dict,
    completeness: dict,
    collateral: dict,
) -> list[dict]:
    """Derive next actions from gaps."""
    actions: list[dict] = []

    # Blockers first
    for blocker in safe_to_finance.get("blockers", []):
        actions.append(
            {
                "title": f"Resoudre: {blocker}",
                "priority": "high",
                "action_type": "fix_blocker",
            }
        )

    # Unknowns blocking finance
    for item in unknowns.get("blocking_finance", []):
        if not any(item in a["title"] for a in actions):
            actions.append(
                {
                    "title": f"Resoudre: {item}",
                    "priority": "high",
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

    # Unresolved incidents
    if incidents["unresolved_count"] > 0:
        actions.append(
            {
                "title": f"Cloturer {incidents['unresolved_count']} incident(s) non resolu(s)",
                "priority": "medium",
                "action_type": "incident",
            }
        )

    # Weak collateral factors
    for factor in collateral.get("factors", []):
        if factor["impact"] == "negative" and factor["status"] == "weak":
            actions.append(
                {
                    "title": f"Ameliorer: {factor['name']}",
                    "priority": "medium",
                    "action_type": "improvement",
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
    """Check whether a lender pack can be generated."""
    pack_blockers: list[str] = []
    if verdict == "not_financeable":
        pack_blockers.append("Le batiment n'est pas financable (verdict: not_financeable)")
    if completeness["score_pct"] < 30.0:
        pack_blockers.append("Completude du dossier trop faible pour generer un pack")
    return len(pack_blockers) == 0, pack_blockers


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class FinanceWorkflowService:
    """Orchestrates the full finance/lender readiness assessment lifecycle."""

    async def assess_finance_readiness(
        self,
        db: AsyncSession,
        building_id: UUID,
    ) -> dict:
        """Full finance readiness assessment.

        Returns a comprehensive dict covering all dimensions needed
        to decide whether a building can be financed, and what gaps remain.
        """
        building = await _get_building(db, building_id)

        # 1. Safe-to-finance evaluation
        safe_to_finance = await _get_safe_to_finance(db, building_id)

        # 2. Data gathering
        completeness = await _get_completeness(db, building_id)
        trust = await _get_trust(db, building_id)
        contradictions = await _get_contradictions(db, building_id)
        unknowns = await _get_unknowns(db, building_id)
        caveats = await _get_caveats(db, building_id)
        incidents = await _get_incidents(db, building_id)
        passport = await _get_passport(db, building_id)

        # 3. Collateral confidence
        collateral = _derive_collateral_confidence(trust, completeness, contradictions, incidents)

        # 4. Derive verdict
        verdict, verdict_summary = _derive_verdict(
            safe_to_finance, trust, unknowns, contradictions, incidents, completeness
        )

        # 5. Lender-facing summary
        grade = passport.get("passport_grade", "F") if passport else "F"

        key_risks: list[str] = []
        if collateral["level"] in ("weak", "insufficient"):
            key_risks.append(f"Confiance collatérale: {collateral['level']}")
        if incidents["unresolved_count"] > 0:
            key_risks.append(f"{incidents['unresolved_count']} incident(s) non resolu(s)")
        if unknowns.get("blocking_finance"):
            key_risks.append(f"{len(unknowns['blocking_finance'])} inconnu(s) bloquant")
        if contradictions["count"] > 0:
            key_risks.append(f"{contradictions['count']} contradiction(s)")

        key_strengths: list[str] = []
        if trust["score_pct"] >= 60.0:
            key_strengths.append(f"Score de confiance: {trust['score_pct']}%")
        if completeness["score_pct"] >= 80.0:
            key_strengths.append("Dossier bien documente")
        if incidents["unresolved_count"] == 0:
            key_strengths.append("Aucun incident non resolu")
        if contradictions["count"] == 0:
            key_strengths.append("Aucune contradiction")

        recommended_due_diligence: list[str] = []
        if trust["score_pct"] < 60.0:
            recommended_due_diligence.append("Verification independante du score de confiance")
        if completeness["score_pct"] < 70.0:
            recommended_due_diligence.append("Audit documentaire complementaire")
        if incidents["unresolved_count"] > 0:
            recommended_due_diligence.append("Examen des incidents non resolus")
        if contradictions["count"] > 0:
            recommended_due_diligence.append("Resolution des contradictions avant engagement")

        lender_summary = {
            "building_grade": grade,
            "year": building.construction_year,
            "address": building.address,
            "collateral_rating": collateral["level"],
            "key_risks": key_risks[:5],
            "key_strengths": key_strengths[:5],
            "recommended_due_diligence": recommended_due_diligence[:5],
        }

        # 6. Next actions
        next_actions = _derive_next_actions(
            safe_to_finance, unknowns, contradictions, incidents, completeness, collateral
        )

        # 7. Pack readiness
        pack_ready, pack_blockers = _derive_pack_readiness(verdict, completeness)

        return {
            "building_id": str(building_id),
            "verdict": verdict,
            "verdict_summary": verdict_summary,
            "safe_to_finance": safe_to_finance,
            "collateral_confidence": collateral,
            "completeness": completeness,
            "trust": trust,
            "contradictions": contradictions,
            "unknowns": unknowns,
            "caveats": caveats,
            "incidents": incidents,
            "lender_summary": lender_summary,
            "next_actions": next_actions,
            "pack_ready": pack_ready,
            "pack_blockers": pack_blockers,
            "assessed_at": datetime.now(UTC).isoformat(),
        }

    async def generate_lender_pack(
        self,
        db: AsyncSession,
        building_id: UUID,
        created_by_id: UUID,
        org_id: UUID | None = None,
        redact_financials: bool = False,
    ) -> dict:
        """Generate lender-facing pack using pack_builder with 'owner' type as base.

        Runs conformance. Returns pack + conformance result.
        Blocks when verdict == not_financeable.
        Note: redact_financials=False by default for lender (they NEED financial info).
        """
        assessment = await self.assess_finance_readiness(db, building_id)
        if assessment["verdict"] == "not_financeable":
            raise ValueError(
                "Impossible de generer le pack: le batiment n'est pas financable. "
                f"Blocages: {'; '.join(assessment['pack_blockers'])}"
            )

        from app.services.pack_builder_service import generate_pack

        pack_result = await generate_pack(
            db,
            building_id,
            pack_type="owner",
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

    async def get_lender_summary(
        self,
        db: AsyncSession,
        building_id: UUID,
    ) -> dict:
        """Lender-facing summary: collateral confidence, incidents, caveats, grade.

        A PROJECTION of existing data, not new truth.
        """
        building = await _get_building(db, building_id)
        passport = await _get_passport(db, building_id)
        trust = await _get_trust(db, building_id)
        completeness = await _get_completeness(db, building_id)
        contradictions = await _get_contradictions(db, building_id)
        incidents = await _get_incidents(db, building_id)
        caveats = await _get_caveats(db, building_id)
        collateral = _derive_collateral_confidence(trust, completeness, contradictions, incidents)

        grade = passport.get("passport_grade", "F") if passport else "F"

        key_facts: list[str] = []
        if building.construction_year:
            key_facts.append(f"Construction: {building.construction_year}")
        if building.renovation_year:
            key_facts.append(f"Renovation: {building.renovation_year}")
        if building.canton:
            key_facts.append(f"Canton: {building.canton}")
        key_facts.append(f"Completude: {completeness['score_pct']}%")

        key_risks: list[str] = []
        if collateral["level"] in ("weak", "insufficient"):
            key_risks.append(f"Confiance collatérale: {collateral['level']}")
        if incidents["unresolved_count"] > 0:
            key_risks.append(f"{incidents['unresolved_count']} incident(s) non resolu(s)")
        if contradictions["count"] > 0:
            key_risks.append(f"{contradictions['count']} contradiction(s)")

        key_strengths: list[str] = []
        if trust["score_pct"] >= 60.0:
            key_strengths.append(f"Score de confiance: {trust['score_pct']}%")
        if completeness["score_pct"] >= 80.0:
            key_strengths.append("Dossier bien documente")
        if incidents["unresolved_count"] == 0:
            key_strengths.append("Aucun incident non resolu")

        return {
            "building_id": str(building_id),
            "building_grade": grade,
            "year": building.construction_year,
            "address": building.address,
            "city": building.city,
            "canton": building.canton,
            "collateral_confidence": collateral,
            "incidents_unresolved": incidents["unresolved_count"],
            "incidents_recurring": incidents["recurring_count"],
            "caveats_count": caveats["count"],
            "lender_conditions": caveats["lender_conditions"],
            "collateral_risks": caveats["collateral_risks"],
            "documentation_gaps": caveats["documentation_gaps"],
            "key_facts": key_facts,
            "key_risks": key_risks[:5],
            "key_strengths": key_strengths[:5],
            "trust_score_pct": trust["score_pct"],
            "completeness_pct": completeness["score_pct"],
            "generated_at": datetime.now(UTC).isoformat(),
        }
