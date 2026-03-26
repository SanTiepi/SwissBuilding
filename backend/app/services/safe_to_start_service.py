"""Safe-to-start decision service — defensible go/no-go for a building.

Reuses decision_view_service, passport_service, and readiness_reasoner to
produce a single, clear status with blockers, conditions, and next actions.

Pure read — never writes.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.post_works_link import PostWorksLink
from app.schemas.safe_to_start import SafeToStartAction, SafeToStartResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Explanation templates (French)
# ---------------------------------------------------------------------------

_EXPLANATIONS_FR: dict[str, str] = {
    "ready_to_proceed": (
        "Le batiment dispose de toutes les preuves necessaires et aucun bloquant n'est identifie — "
        "les travaux peuvent demarrer."
    ),
    "proceed_with_conditions": (
        "Le batiment peut avancer sous reserve de conditions mineures — aucun bloquant critique."
    ),
    "diagnostic_required": (
        "Un diagnostic manquant ou incomplet empeche l'evaluation — un diagnostic est requis avant de demarrer."
    ),
    "critical_risk": ("Des bloquants critiques sont identifies — les travaux ne doivent pas demarrer en l'etat."),
    "memory_incomplete": ("Les donnees disponibles sont insuffisantes pour produire une evaluation fiable."),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def compute_safe_to_start(
    db: AsyncSession,
    building_id: UUID,
) -> SafeToStartResult | None:
    """Compute a defensible go/no-go status for a building.

    Reuses decision_view_service, passport_service, readiness logic.
    Returns None if building does not exist.
    """
    # 0. Verify building exists
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if building is None:
        return None

    blockers: list[str] = []
    conditions: list[str] = []
    next_actions: list[SafeToStartAction] = []
    reusable_proof: list[str] = []
    confidence = "low"
    post_works_impact: dict = {}

    # 1. Passport summary (trust + completeness + grade)
    passport: dict | None = None
    overall_trust = 0.0
    overall_completeness = 0.0
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
        if passport:
            overall_trust = passport.get("knowledge_state", {}).get("overall_trust", 0.0)
            overall_completeness = passport.get("completeness", {}).get("overall", 0.0)
    except Exception:
        logger.debug("Passport unavailable for safe-to-start %s", building_id, exc_info=True)

    # 2. Decision view (blockers + conditions + proof chain)
    decision_view = None
    try:
        from app.services.decision_view_service import get_building_decision_view

        decision_view = await get_building_decision_view(db, building_id)
    except Exception:
        logger.debug("Decision view unavailable for safe-to-start %s", building_id, exc_info=True)

    if decision_view is not None:
        for b in getattr(decision_view, "blockers", []):
            blockers.append(b.title)
        for c in getattr(decision_view, "conditions", []):
            conditions.append(c.title)
        # Reusable proof from proof chain
        for item in getattr(decision_view, "proof_chain", []):
            if getattr(item, "status", "") in ("published", "delivered", "generated"):
                reusable_proof.append(f"{item.entity_type}: {item.entity_id}")

    # 3. Check diagnostics exist
    diag_result = await db.execute(
        select(Diagnostic).where(
            Diagnostic.building_id == building_id,
            Diagnostic.status.in_(["completed", "validated"]),
        )
    )
    diagnostics = list(diag_result.scalars().all())
    has_diagnostics = len(diagnostics) > 0

    if not has_diagnostics:
        # Check if there are ANY diagnostics at all
        any_diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
        any_diags = list(any_diag_result.scalars().all())
        if any_diags:
            # Diagnostics exist but not completed
            blockers.append("Diagnostics en cours — resultats non disponibles")
            next_actions.append(
                SafeToStartAction(
                    action="Finaliser les diagnostics en cours",
                    priority="critical",
                    who="Diagnostiqueur certifie",
                )
            )
        else:
            next_actions.append(
                SafeToStartAction(
                    action="Commander un diagnostic polluants complet",
                    priority="critical",
                    who="Diagnostiqueur certifie",
                )
            )

    # 4. Readiness checks (blind spots + contradictions from passport)
    if passport:
        blind_spots = passport.get("blind_spots", {})
        if blind_spots.get("total_open", 0) > 0:
            blocking_spots = blind_spots.get("blocking", 0)
            if blocking_spots > 0:
                blockers.append(f"{blocking_spots} zone(s) aveugle(s) bloquante(s)")
            else:
                conditions.append(f"{blind_spots['total_open']} zone(s) aveugle(s) non-bloquante(s)")

        contradictions = passport.get("contradictions", {})
        if contradictions.get("unresolved", 0) > 0:
            blockers.append(f"{contradictions['unresolved']} contradiction(s) non resolue(s)")

        # Evidence coverage → reusable proof
        evidence = passport.get("evidence_coverage", {})
        if evidence.get("total_diagnostics", 0) > 0:
            reusable_proof.append(f"{evidence['total_diagnostics']} diagnostic(s) disponible(s)")
        if evidence.get("total_documents", 0) > 0:
            reusable_proof.append(f"{evidence['total_documents']} document(s) disponible(s)")

    # 5. Post-works residual memory
    post_works_impact = await _evaluate_post_works(db, building_id, blockers, conditions)

    # 6. Derive confidence
    if overall_completeness >= 0.8 and overall_trust >= 0.6:
        confidence = "high"
    elif overall_completeness >= 0.5 or overall_trust >= 0.3:
        confidence = "medium"
    else:
        confidence = "low"

    # 7. Determine status
    status = _determine_status(
        blockers=blockers,
        conditions=conditions,
        has_diagnostics=has_diagnostics,
        overall_completeness=overall_completeness,
        overall_trust=overall_trust,
        passport=passport,
    )

    # 8. Add generic next actions from blockers
    for b_text in blockers:
        if not any(a.action == f"Resoudre: {b_text}" for a in next_actions):
            next_actions.append(
                SafeToStartAction(
                    action=f"Resoudre: {b_text}",
                    priority="high",
                )
            )

    explanation_fr = _EXPLANATIONS_FR.get(status, "Statut inconnu.")

    return SafeToStartResult(
        building_id=building_id,
        status=status,
        blockers=blockers,
        conditions=conditions,
        next_actions=next_actions[:10],  # cap at 10
        reusable_proof=reusable_proof,
        confidence=confidence,
        explanation_fr=explanation_fr,
        post_works_impact=post_works_impact,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _determine_status(
    *,
    blockers: list[str],
    conditions: list[str],
    has_diagnostics: bool,
    overall_completeness: float,
    overall_trust: float,
    passport: dict | None,
) -> str:
    """Derive the go/no-go status from collected signals."""
    # No data at all
    if passport is None and not has_diagnostics and overall_completeness == 0.0:
        return "memory_incomplete"

    # Missing diagnostics
    if not has_diagnostics:
        return "diagnostic_required"

    # Active blockers
    if blockers:
        return "critical_risk"

    # Conditions but no blockers
    if conditions:
        return "proceed_with_conditions"

    # Everything clear
    return "ready_to_proceed"


async def _evaluate_post_works(
    db: AsyncSession,
    building_id: UUID,
    blockers: list[str],
    conditions: list[str],
) -> dict:
    """Check post-works links for residual memory and feed into blockers/conditions."""
    impact: dict = {}

    # Find post-works links via interventions for this building
    pw_result = await db.execute(
        select(PostWorksLink)
        .join(Intervention, PostWorksLink.intervention_id == Intervention.id)
        .where(Intervention.building_id == building_id)
    )
    post_works = list(pw_result.scalars().all())

    if not post_works:
        # Check if there are completed remediation interventions without post-works
        remediation_result = await db.execute(
            select(Intervention).where(
                Intervention.building_id == building_id,
                Intervention.intervention_type == "remediation",
                Intervention.status == "completed",
            )
        )
        remediations = list(remediation_result.scalars().all())
        if remediations:
            conditions.append("Travaux de remediation effectues mais verite post-travaux non verifiee")
            impact["missing_post_works_truth"] = True
            impact["remediation_count"] = len(remediations)
        return impact

    finalized = [pw for pw in post_works if pw.status == "finalized"]
    pending = [pw for pw in post_works if pw.status != "finalized"]

    if pending:
        conditions.append(f"{len(pending)} verification(s) post-travaux en attente")
        impact["pending_verifications"] = len(pending)

    for pw in finalized:
        # Residual risks → conditions
        residual_risks = pw.residual_risks or []
        for rr in residual_risks:
            if isinstance(rr, dict):
                risk_desc = rr.get("description", rr.get("material_type", "risque residuel"))
                conditions.append(f"Risque residuel: {risk_desc}")

        # Grade delta → warning if negative
        grade_delta = pw.grade_delta or {}
        if isinstance(grade_delta, dict):
            before = grade_delta.get("before_grade", "")
            after = grade_delta.get("after_grade", "")
            if before and after and before < after:
                # Grade worsened (A < B in string order means improvement)
                conditions.append(f"Degradation du grade post-travaux: {before} → {after}")
                impact["grade_worsened"] = True
            elif before and after and after < before:
                # Grade improved
                impact["grade_improved"] = True
                impact["grade_before"] = before
                impact["grade_after"] = after

    impact["finalized_count"] = len(finalized)
    return impact
