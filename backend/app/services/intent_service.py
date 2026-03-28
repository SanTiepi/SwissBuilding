"""
BatiConnect - Intent Service

Orchestrates the intent/question/decision-context/safe-to-x lifecycle.
Reuses readiness_reasoner (start/tender/reopen/requalify) and
transaction_readiness_service (sell/insure/finance/lease) — no duplication.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.building_intent import (
    INTENT_TYPES,
    QUESTION_TYPES,
    BuildingIntent,
    BuildingQuestion,
    DecisionContext,
    SafeToXState,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent → Question mapping
# ---------------------------------------------------------------------------

_INTENT_TO_QUESTIONS: dict[str, list[str]] = {
    "sell": ["safe_to_sell", "what_blocks", "what_missing"],
    "buy": ["safe_to_sell", "what_contradicts", "what_missing"],
    "renovate": ["safe_to_start", "safe_to_tender", "what_blocks"],
    "insure": ["safe_to_insure", "what_blocks"],
    "finance": ["safe_to_finance", "what_blocks", "what_missing"],
    "lease": ["safe_to_lease", "what_blocks"],
    "transfer": ["safe_to_transfer", "what_missing"],
    "demolish": ["safe_to_demolish", "what_blocks"],
    "assess": ["what_missing", "what_contradicts"],
    "comply": ["safe_to_start", "what_blocks", "what_expires"],
    "maintain": ["what_next", "what_expires"],
    "remediate": ["safe_to_start", "safe_to_tender", "safe_to_sell"],
    "other": [],
}

# Map question_types to the safe_to_type they represent
_QUESTION_TO_SAFE_TO: dict[str, str] = {
    "safe_to_start": "start",
    "safe_to_sell": "sell",
    "safe_to_insure": "insure",
    "safe_to_finance": "finance",
    "safe_to_lease": "lease",
    "safe_to_transfer": "transfer",
    "safe_to_demolish": "demolish",
    "safe_to_tender": "tender",
}

# Which safe_to types are handled by readiness_reasoner vs transaction_readiness
_READINESS_REASONER_TYPES = {"start", "tender", "reopen", "requalify"}
_TRANSACTION_READINESS_TYPES = {"sell", "insure", "finance", "lease"}

# Default verdict validity period
_DEFAULT_VALIDITY_HOURS = 24


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def create_intent(
    db: AsyncSession,
    building_id: UUID,
    intent_type: str,
    created_by_id: UUID,
    title: str,
    *,
    organization_id: UUID | None = None,
    description: str | None = None,
    target_date: datetime | None = None,
) -> BuildingIntent:
    """Create a new intent. Auto-generates relevant questions."""
    if intent_type not in INTENT_TYPES:
        raise ValueError(f"Unknown intent_type '{intent_type}'. Must be one of: {', '.join(INTENT_TYPES)}")

    # Verify building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        raise ValueError(f"Building {building_id} not found")

    intent = BuildingIntent(
        building_id=building_id,
        organization_id=organization_id,
        created_by_id=created_by_id,
        intent_type=intent_type,
        title=title,
        description=description,
        target_date=target_date,
        status="open",
    )
    db.add(intent)
    await db.flush()  # get intent.id

    # Auto-generate questions
    question_types = _INTENT_TO_QUESTIONS.get(intent_type, [])
    for qt in question_types:
        question_text = _default_question_text(qt)
        question = BuildingQuestion(
            intent_id=intent.id,
            building_id=building_id,
            asked_by_id=created_by_id,
            question_type=qt,
            question_text=question_text,
            status="pending",
        )
        db.add(question)

    await db.commit()
    await db.refresh(intent)
    return intent


async def ask_question(
    db: AsyncSession,
    building_id: UUID,
    question_type: str,
    asked_by_id: UUID,
    *,
    intent_id: UUID | None = None,
    question_text: str | None = None,
) -> BuildingQuestion:
    """Ask a question about a building. Uses default text if none provided."""
    if question_type not in QUESTION_TYPES:
        raise ValueError(f"Unknown question_type '{question_type}'. Must be one of: {', '.join(QUESTION_TYPES)}")

    # Verify building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    if result.scalar_one_or_none() is None:
        raise ValueError(f"Building {building_id} not found")

    text = question_text or _default_question_text(question_type)

    question = BuildingQuestion(
        intent_id=intent_id,
        building_id=building_id,
        asked_by_id=asked_by_id,
        question_type=question_type,
        question_text=text,
        status="pending",
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return question


async def evaluate_question(
    db: AsyncSession,
    question_id: UUID,
) -> BuildingQuestion:
    """Evaluate a question by assembling DecisionContext and computing SafeToXState.

    Uses existing readiness_reasoner and transaction_readiness_service.
    """
    result = await db.execute(
        select(BuildingQuestion)
        .options(selectinload(BuildingQuestion.decision_context), selectinload(BuildingQuestion.safe_to_x_state))
        .where(BuildingQuestion.id == question_id)
    )
    question = result.scalar_one_or_none()
    if question is None:
        raise ValueError(f"Question {question_id} not found")

    question.status = "evaluating"
    await db.flush()

    safe_to_type = _QUESTION_TO_SAFE_TO.get(question.question_type)

    if safe_to_type:
        # This is a safe_to_x question — evaluate with the appropriate engine
        verdict_data = await _evaluate_safe_to(db, question.building_id, safe_to_type)
    else:
        # Analytical question (what_blocks, what_missing, etc.)
        verdict_data = await _evaluate_analytical(db, question.building_id, question.question_type)

    now = datetime.now(UTC)

    # Upsert DecisionContext
    if question.decision_context:
        dc = question.decision_context
    else:
        dc = DecisionContext(
            question_id=question.id,
            building_id=question.building_id,
        )
        db.add(dc)

    dc.relevant_evidence_ids = verdict_data.get("evidence_ids", [])
    dc.applicable_rules = verdict_data.get("rules", [])
    dc.blockers = verdict_data.get("blockers", [])
    dc.conditions = verdict_data.get("conditions", [])
    dc.overall_confidence = verdict_data.get("confidence", 0.0)
    dc.data_freshness = verdict_data.get("freshness", "current")
    dc.contradiction_count = verdict_data.get("contradiction_count", 0)
    dc.coverage_assessment = verdict_data.get("coverage", "partial")
    dc.computed_at = now

    await db.flush()

    # Upsert SafeToXState (only for safe_to_x questions)
    if safe_to_type:
        if question.safe_to_x_state:
            stx = question.safe_to_x_state
        else:
            stx = SafeToXState(
                question_id=question.id,
                building_id=question.building_id,
                intent_id=question.intent_id,
                safe_to_type=safe_to_type,
            )
            db.add(stx)

        stx.verdict = verdict_data["verdict"]
        stx.verdict_summary = verdict_data["verdict_summary"]
        stx.decision_context_id = dc.id
        stx.blockers = verdict_data.get("blockers")
        stx.conditions = verdict_data.get("conditions")
        stx.evaluated_at = now
        stx.evaluated_by = "system"
        stx.rule_basis = verdict_data.get("rules")
        stx.confidence = verdict_data.get("confidence", 0.0)
        stx.valid_until = now + timedelta(hours=_DEFAULT_VALIDITY_HOURS)

    question.status = "answered"
    question.answered_at = now

    # Update parent intent status if all questions answered
    if question.intent_id:
        await _maybe_update_intent_status(db, question.intent_id)

    await db.commit()
    await db.refresh(question)
    return question


async def get_building_intents(
    db: AsyncSession,
    building_id: UUID,
    *,
    status: str | None = None,
) -> list[BuildingIntent]:
    """List all intents for a building."""
    query = select(BuildingIntent).where(BuildingIntent.building_id == building_id)
    if status:
        query = query.where(BuildingIntent.status == status)
    query = query.order_by(BuildingIntent.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_safe_to_x_summary(
    db: AsyncSession,
    building_id: UUID,
) -> dict[str, Any]:
    """Get all current SafeToX verdicts for a building.

    Combines:
    - readiness_reasoner for start/tender/reopen/requalify
    - transaction_readiness_service for sell/insure/finance/lease

    Returns a unified view of all SafeToX types.
    """
    from app.schemas.transaction_readiness import TransactionType
    from app.services.readiness_reasoner import READINESS_TYPES, evaluate_readiness
    from app.services.transaction_readiness_service import evaluate_transaction_readiness

    now = datetime.now(UTC)
    verdicts: list[dict[str, Any]] = []

    # Readiness reasoner types: safe_to_start, safe_to_tender, safe_to_reopen, safe_to_requalify
    for rtype in READINESS_TYPES:
        try:
            assessment = await evaluate_readiness(db, building_id, rtype)
            safe_to_type = rtype.replace("safe_to_", "")
            blockers_list = assessment.blockers_json or []
            conditions_list = assessment.conditions_json or []

            if assessment.status == "ready":
                verdict = "clear"
            elif assessment.status == "conditional":
                verdict = "conditional"
            elif assessment.status == "blocked":
                verdict = "blocked"
            else:
                verdict = "unknown"

            verdicts.append(
                {
                    "safe_to_type": safe_to_type,
                    "verdict": verdict,
                    "verdict_summary": f"{rtype}: {assessment.status} (score: {assessment.score:.0%})",
                    "blockers": blockers_list,
                    "conditions": conditions_list,
                    "confidence": assessment.score or 0.0,
                    "evaluated_at": (assessment.assessed_at.isoformat() if assessment.assessed_at else now.isoformat()),
                    "evaluated_by": "system",
                    "rule_basis": [
                        c.get("legal_basis") for c in (assessment.checks_json or []) if c.get("legal_basis")
                    ],
                }
            )
        except ValueError:
            logger.warning(f"Could not evaluate {rtype} for building {building_id}")

    # Transaction readiness types: sell, insure, finance, lease
    for ttype in TransactionType:
        try:
            tr = await evaluate_transaction_readiness(db, building_id, ttype)
            if tr.overall_status.value == "ready":
                verdict = "clear"
            elif tr.overall_status.value == "conditional":
                verdict = "conditional"
            else:
                verdict = "blocked"

            verdicts.append(
                {
                    "safe_to_type": ttype.value,
                    "verdict": verdict,
                    "verdict_summary": f"safe_to_{ttype.value}: {tr.overall_status.value} (score: {tr.score:.0%})",
                    "blockers": [{"message": b} for b in tr.blockers],
                    "conditions": [{"message": c} for c in tr.conditions],
                    "confidence": tr.score,
                    "evaluated_at": tr.evaluated_at.isoformat(),
                    "evaluated_by": "system",
                    "rule_basis": [],
                }
            )
        except Exception:
            logger.warning(f"Could not evaluate transaction readiness {ttype} for building {building_id}")

    return {
        "building_id": str(building_id),
        "verdicts": verdicts,
        "evaluated_at": now.isoformat(),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _evaluate_safe_to(
    db: AsyncSession,
    building_id: UUID,
    safe_to_type: str,
) -> dict[str, Any]:
    """Evaluate a safe_to_x question using the appropriate engine.

    After delegating to readiness_reasoner or transaction_readiness_service,
    merges unknowns ledger impact: open unknowns that block this safe_to_type
    become explicit blockers in the verdict.
    """
    from app.services.unknowns_ledger_service import get_coverage_map, get_unknowns_impact

    if safe_to_type in _READINESS_REASONER_TYPES:
        verdict_data = await _evaluate_via_readiness_reasoner(db, building_id, safe_to_type)
    elif safe_to_type in _TRANSACTION_READINESS_TYPES:
        verdict_data = await _evaluate_via_transaction_readiness(db, building_id, safe_to_type)
    else:
        # For types not yet wired (demolish, transfer), return unknown
        return {
            "verdict": "unknown",
            "verdict_summary": f"safe_to_{safe_to_type}: evaluation not yet implemented",
            "blockers": [],
            "conditions": [],
            "confidence": 0.0,
            "freshness": "current",
            "coverage": "insufficient",
            "rules": [],
            "evidence_ids": [],
            "contradiction_count": 0,
        }

    # --- Merge unknowns ledger impact ---
    unknowns_impact = await get_unknowns_impact(db, building_id)

    # Add unknowns that block this safe_to_type as explicit blockers
    blocked_count = unknowns_impact.get("blocked_safe_to_x", {}).get(safe_to_type, 0)
    if blocked_count > 0:
        blockers = verdict_data.get("blockers", [])
        # Add individual urgent entries as blockers (up to 5)
        for entry in unknowns_impact.get("most_urgent", []):
            entry_blocks = entry.blocks_safe_to_x or []
            if safe_to_type in entry_blocks:
                blockers.append(
                    {
                        "description": entry.subject,
                        "severity": entry.severity or "high",
                        "source": "unknowns_ledger",
                        "unknown_type": entry.unknown_type,
                    }
                )
        verdict_data["blockers"] = blockers

        # Downgrade verdict if unknowns introduce new blockers
        if verdict_data["verdict"] == "clear":
            verdict_data["verdict"] = "blocked"
            verdict_data["verdict_summary"] = f"safe_to_{safe_to_type}: blocked by {blocked_count} unknown(s)"

    # Update contradiction_count with critical unknowns count
    verdict_data["contradiction_count"] = verdict_data.get("contradiction_count", 0) + unknowns_impact.get(
        "critical_count", 0
    )

    # Update coverage_assessment based on unknowns coverage map
    coverage_map = await get_coverage_map(db, building_id)
    gap_count = len(coverage_map.get("gaps", []))
    covered_count = len(coverage_map.get("covered", []))
    total_zones = gap_count + covered_count + len(coverage_map.get("partial", []))

    if total_zones > 0:
        coverage_ratio = covered_count / total_zones
        if coverage_ratio >= 0.9 and gap_count == 0:
            spatial_coverage = "complete"
        elif coverage_ratio >= 0.5:
            spatial_coverage = "partial"
        else:
            spatial_coverage = "insufficient"

        # Take the worst of engine coverage and spatial coverage
        engine_coverage = verdict_data.get("coverage", "partial")
        coverage_rank = {"complete": 2, "partial": 1, "insufficient": 0}
        verdict_data["coverage"] = min(engine_coverage, spatial_coverage, key=lambda c: coverage_rank.get(c, 0))

    return verdict_data


async def _evaluate_via_readiness_reasoner(
    db: AsyncSession,
    building_id: UUID,
    safe_to_type: str,
) -> dict[str, Any]:
    """Delegate to readiness_reasoner for start/tender/reopen/requalify."""
    from app.services.readiness_reasoner import evaluate_readiness

    readiness_type = f"safe_to_{safe_to_type}"
    assessment = await evaluate_readiness(db, building_id, readiness_type)

    if assessment.status == "ready":
        verdict = "clear"
    elif assessment.status == "conditional":
        verdict = "conditional"
    elif assessment.status == "blocked":
        verdict = "blocked"
    else:
        verdict = "unknown"

    blockers = assessment.blockers_json or []
    conditions = assessment.conditions_json or []
    checks = assessment.checks_json or []

    rules = [c.get("legal_basis") for c in checks if c.get("legal_basis")]

    return {
        "verdict": verdict,
        "verdict_summary": f"safe_to_{safe_to_type}: {assessment.status} (score: {assessment.score:.0%})",
        "blockers": blockers,
        "conditions": conditions,
        "confidence": assessment.score or 0.0,
        "freshness": "current",
        "coverage": "complete" if assessment.score and assessment.score >= 0.8 else "partial",
        "rules": rules,
        "evidence_ids": [],
        "contradiction_count": 0,
    }


async def _evaluate_via_transaction_readiness(
    db: AsyncSession,
    building_id: UUID,
    safe_to_type: str,
) -> dict[str, Any]:
    """Delegate to transaction_readiness_service for sell/insure/finance/lease."""
    from app.schemas.transaction_readiness import TransactionType
    from app.services.transaction_readiness_service import evaluate_transaction_readiness

    ttype = TransactionType(safe_to_type)
    tr = await evaluate_transaction_readiness(db, building_id, ttype)

    if tr.overall_status.value == "ready":
        verdict = "clear"
    elif tr.overall_status.value == "conditional":
        verdict = "conditional"
    else:
        verdict = "blocked"

    return {
        "verdict": verdict,
        "verdict_summary": f"safe_to_{safe_to_type}: {tr.overall_status.value} (score: {tr.score:.0%})",
        "blockers": [
            {"description": b, "severity": "blocker", "resolution_path": r}
            for b, r in zip(tr.blockers, tr.recommendations[: len(tr.blockers)], strict=False)
        ],
        "conditions": [{"description": c, "status": "pending"} for c in tr.conditions],
        "confidence": tr.score,
        "freshness": "current",
        "coverage": "complete" if tr.score >= 0.8 else "partial",
        "rules": [],
        "evidence_ids": [],
        "contradiction_count": 0,
    }


async def _evaluate_analytical(
    db: AsyncSession,
    building_id: UUID,
    question_type: str,
) -> dict[str, Any]:
    """Evaluate analytical questions (what_blocks, what_missing, etc.)."""
    from app.services.passport_service import get_passport_summary

    passport = await get_passport_summary(db, building_id)

    if passport is None:
        return {
            "verdict": "unknown",
            "verdict_summary": "Cannot evaluate — building passport not available",
            "blockers": [],
            "conditions": [],
            "confidence": 0.0,
            "freshness": "stale",
            "coverage": "insufficient",
            "rules": [],
            "evidence_ids": [],
            "contradiction_count": 0,
        }

    blockers: list[dict] = []
    conditions: list[dict] = []

    if question_type == "what_blocks":
        # Collect all blockers from readiness
        for rtype, rdata in passport.get("readiness", {}).items():
            if rdata.get("blockers_count", 0) > 0:
                blockers.append(
                    {
                        "description": f"{rtype}: {rdata['blockers_count']} blocker(s)",
                        "severity": "blocker",
                        "resolution_path": f"Resolve blockers in {rtype} readiness",
                    }
                )

    elif question_type == "what_missing":
        blind = passport.get("blind_spots", {})
        if blind.get("total_open", 0) > 0:
            for utype, count in blind.get("by_type", {}).items():
                blockers.append(
                    {
                        "description": f"{utype}: {count} unknown(s)",
                        "severity": "warning",
                        "resolution_path": f"Investigate {utype} unknowns",
                    }
                )
        missing_pollutants = passport.get("pollutant_coverage", {}).get("missing", [])
        for p in missing_pollutants:
            blockers.append(
                {
                    "description": f"Missing pollutant evaluation: {p}",
                    "severity": "blocker",
                    "resolution_path": f"Commission {p} diagnostic",
                }
            )

    elif question_type == "what_contradicts":
        contras = passport.get("contradictions", {})
        if contras.get("unresolved", 0) > 0:
            for field, count in contras.get("by_type", {}).items():
                blockers.append(
                    {
                        "description": f"Contradiction on {field}: {count} issue(s)",
                        "severity": "warning",
                        "resolution_path": f"Review and resolve contradiction on {field}",
                    }
                )

    elif question_type == "what_changed":
        # Delegate to change signal data if available
        conditions.append(
            {
                "description": "Review change signals for recent modifications",
                "status": "pending",
            }
        )

    elif question_type == "what_expires":
        conditions.append(
            {
                "description": "Review diagnostic validity dates and regulatory deadlines",
                "status": "pending",
            }
        )

    elif question_type == "what_costs":
        conditions.append(
            {
                "description": "Review action items and intervention cost estimates",
                "status": "pending",
            }
        )

    elif question_type == "what_next":
        blind = passport.get("blind_spots", {})
        if blind.get("blocking", 0) > 0:
            blockers.append(
                {
                    "description": f"{blind['blocking']} blocking unknown(s) to resolve first",
                    "severity": "blocker",
                    "resolution_path": "Resolve blocking unknowns",
                }
            )
        readiness = passport.get("readiness", {})
        for rtype, rdata in readiness.items():
            if rdata.get("status") == "blocked":
                conditions.append(
                    {
                        "description": f"Unblock {rtype} readiness",
                        "status": "pending",
                    }
                )

    trust = passport.get("knowledge_state", {}).get("overall_trust", 0.0)
    contradictions = passport.get("contradictions", {}).get("unresolved", 0)
    completeness = passport.get("completeness", {}).get("overall_score", 0.0)

    if completeness >= 0.9:
        coverage = "complete"
    elif completeness >= 0.5:
        coverage = "partial"
    else:
        coverage = "insufficient"

    return {
        "verdict": "clear" if not blockers else "blocked",
        "verdict_summary": f"{question_type}: {len(blockers)} issue(s) found",
        "blockers": blockers,
        "conditions": conditions,
        "confidence": trust,
        "freshness": "current",
        "coverage": coverage,
        "rules": [],
        "evidence_ids": [],
        "contradiction_count": contradictions,
    }


async def _maybe_update_intent_status(db: AsyncSession, intent_id: UUID) -> None:
    """If all questions for an intent are answered, update intent status."""
    result = await db.execute(select(BuildingQuestion).where(BuildingQuestion.intent_id == intent_id))
    questions = list(result.scalars().all())
    if not questions:
        return

    all_answered = all(q.status == "answered" for q in questions)
    if all_answered:
        intent_result = await db.execute(select(BuildingIntent).where(BuildingIntent.id == intent_id))
        intent = intent_result.scalar_one_or_none()
        if intent and intent.status in ("open", "evaluating"):
            intent.status = "answered"


def _default_question_text(question_type: str) -> str:
    """Generate default human-readable question text."""
    texts = {
        "safe_to_start": "Is it safe to start renovation works on this building?",
        "safe_to_sell": "Is this building ready to be sold with adequate documentation?",
        "safe_to_insure": "Can this building be insured against pollutant liability?",
        "safe_to_finance": "Can this building secure financing?",
        "safe_to_lease": "Can this building be safely leased to occupants?",
        "safe_to_transfer": "Is this building ready for ownership transfer?",
        "safe_to_demolish": "Is it safe to demolish this building?",
        "safe_to_tender": "Can tender documents be prepared for this building?",
        "what_blocks": "What is currently blocking progress on this building?",
        "what_missing": "What information is missing about this building?",
        "what_contradicts": "What contradictions exist in this building's data?",
        "what_changed": "What has changed recently for this building?",
        "what_expires": "What is expiring or will expire soon for this building?",
        "what_costs": "What are the estimated costs for this building?",
        "what_next": "What should be done next for this building?",
        "custom": "Custom question about this building",
    }
    return texts.get(question_type, f"Question about this building ({question_type})")
