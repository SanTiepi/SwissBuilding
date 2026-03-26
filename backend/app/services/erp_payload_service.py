"""ERP Payload service — stable, versioned JSON for ERP consumption.

Aggregates from existing services (safe_to_start, passport, decision_view,
obligations) into a deterministic, stable output shape that ERPs can rely on.

Pure read — never writes.
"""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.obligation import Obligation
from app.schemas.erp_payload import (
    ErpBlocker,
    ErpBuildingPayload,
    ErpNextAction,
    ErpObligation,
    ErpPortfolioPayload,
    ErpProofStatus,
    ErpSafeToStart,
)

logger = logging.getLogger(__name__)

# All 6 pollutants tracked by BatiConnect
_ALL_POLLUTANTS = ["asbestos", "pcb", "lead", "hap", "radon", "pfas"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _map_blocker_category(category: str) -> str:
    """Map decision-view blocker categories to ERP blocker types."""
    mapping = {
        "procedure_blocked": "procedure",
        "overdue_obligation": "obligation",
        "unresolved_unknown": "unknown",
    }
    return mapping.get(category, "unknown")


def _map_action_priority(priority: str) -> str:
    """Map safe-to-start priorities to ERP action priorities."""
    mapping = {
        "critical": "urgent",
        "high": "urgent",
        "medium": "recommended",
        "low": "optional",
    }
    return mapping.get(priority, "recommended")


def _infer_action_category(action_text: str) -> str:
    """Infer action category from action text."""
    text_lower = action_text.lower()
    if "diagnostic" in text_lower or "diagnostic" in text_lower:
        return "diagnostic"
    if "remediation" in text_lower or "remediat" in text_lower or "travaux" in text_lower:
        return "remediation"
    if "procedure" in text_lower or "autorit" in text_lower:
        return "procedure"
    return "proof"


def _map_obligation_status(status: str) -> str:
    """Map obligation status to ERP obligation status."""
    mapping = {
        "upcoming": "pending",
        "due_soon": "pending",
        "overdue": "overdue",
        "completed": "completed",
        "cancelled": "completed",
    }
    return mapping.get(status, "pending")


async def _build_proof_status(
    db: AsyncSession,
    building_id: UUID,
    passport: dict | None,
) -> ErpProofStatus:
    """Build proof status from passport data."""
    proof = ErpProofStatus()

    if not passport:
        return proof

    # Evidence coverage
    evidence = passport.get("evidence_coverage", {})
    total_diags = evidence.get("total_diagnostics", 0)
    if total_diags > 0:
        # Approximate diagnostic coverage as ratio of assessed pollutants
        pollutant_cov = passport.get("pollutant_coverage", {})
        assessed = [p for p in _ALL_POLLUTANTS if pollutant_cov.get(p, {}).get("status") == "assessed"]
        proof.pollutants_assessed = assessed
        proof.pollutants_missing = [p for p in _ALL_POLLUTANTS if p not in assessed]
        proof.diagnostic_coverage = len(assessed) / len(_ALL_POLLUTANTS) if _ALL_POLLUTANTS else 0.0

    # Last diagnostic date
    latest_diag = evidence.get("latest_diagnostic_date")
    if latest_diag:
        try:
            from datetime import date

            if isinstance(latest_diag, str):
                proof.last_diagnostic_date = date.fromisoformat(latest_diag[:10])
            elif isinstance(latest_diag, date):
                proof.last_diagnostic_date = latest_diag
        except (ValueError, TypeError):
            pass

    # Authority pack readiness — check if any audience pack for authority is generated
    try:
        from app.models.audience_pack import AudiencePack

        ap_result = await db.execute(
            select(AudiencePack)
            .where(
                AudiencePack.building_id == building_id,
                AudiencePack.pack_type == "authority",
                AudiencePack.status == "generated",
            )
            .limit(1)
        )
        proof.authority_pack_ready = ap_result.scalar_one_or_none() is not None
    except Exception:
        logger.debug("Could not check authority pack for %s", building_id, exc_info=True)

    return proof


async def _build_obligations(
    db: AsyncSession,
    building_id: UUID,
) -> list[ErpObligation]:
    """Fetch active obligations for a building."""
    result = await db.execute(
        select(Obligation).where(
            Obligation.building_id == building_id,
            Obligation.status.in_(["upcoming", "due_soon", "overdue", "completed"]),
        )
    )
    obligations: list[ErpObligation] = []
    for obl in result.scalars().all():
        obligations.append(
            ErpObligation(
                title=obl.title,
                due_date=obl.due_date,
                status=_map_obligation_status(obl.status),
                category=obl.obligation_type or "custom",
            )
        )
    return obligations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_erp_payload(
    db: AsyncSession,
    building_id: UUID,
) -> ErpBuildingPayload | None:
    """Produce a stable, versioned ERP payload for a single building.

    Aggregates from passport, safe-to-start, decision view, and obligations.
    Returns None if the building does not exist.
    """
    # 0. Verify building exists
    bld_result = await db.execute(select(Building).where(Building.id == building_id))
    building = bld_result.scalar_one_or_none()
    if building is None:
        return None

    now = datetime.now(UTC)

    # 1. Passport summary
    passport: dict | None = None
    passport_grade: str | None = None
    overall_trust: float | None = None
    overall_completeness: float | None = None
    try:
        from app.services.passport_service import get_passport_summary

        passport = await get_passport_summary(db, building_id)
        if passport:
            passport_grade = passport.get("passport_grade")
            overall_trust = passport.get("knowledge_state", {}).get("overall_trust")
            overall_completeness = passport.get("completeness", {}).get("overall")
    except Exception:
        logger.debug("Passport unavailable for ERP payload %s", building_id, exc_info=True)

    # 2. Safe-to-start
    erp_sts = ErpSafeToStart(status="memory_incomplete")
    try:
        from app.services.safe_to_start_service import compute_safe_to_start

        sts = await compute_safe_to_start(db, building_id)
        if sts:
            erp_sts = ErpSafeToStart(
                status=sts.status,
                conditions=sts.conditions,
                confidence=sts.confidence,
            )
    except Exception:
        logger.debug("Safe-to-start unavailable for ERP payload %s", building_id, exc_info=True)

    # 3. Blockers from decision view
    erp_blockers: list[ErpBlocker] = []
    erp_next_actions: list[ErpNextAction] = []
    try:
        from app.services.decision_view_service import get_building_decision_view

        dv = await get_building_decision_view(db, building_id)
        if dv:
            for b in dv.blockers:
                ref_id: UUID | None = None
                with contextlib.suppress(ValueError, TypeError):
                    ref_id = UUID(b.source_id) if b.source_id else None
                erp_blockers.append(
                    ErpBlocker(
                        type=_map_blocker_category(b.category),
                        title=b.title,
                        severity="critical" if b.category == "procedure_blocked" else "high",
                        reference_id=ref_id,
                    )
                )
    except Exception:
        logger.debug("Decision view unavailable for ERP payload %s", building_id, exc_info=True)

    # 4. Next actions from safe-to-start
    try:
        from app.services.safe_to_start_service import compute_safe_to_start as _sts

        sts2 = await _sts(db, building_id)
        if sts2:
            for a in sts2.next_actions[:5]:
                erp_next_actions.append(
                    ErpNextAction(
                        title=a.action,
                        priority=_map_action_priority(a.priority),
                        category=_infer_action_category(a.action),
                    )
                )
    except Exception:
        logger.debug("Next actions unavailable for ERP payload %s", building_id, exc_info=True)

    # 5. Proof status
    proof_status = await _build_proof_status(db, building_id, passport)

    # 6. Obligations
    obligations = await _build_obligations(db, building_id)

    return ErpBuildingPayload(
        generated_at=now,
        building_id=building_id,
        egid=building.egid,
        egrid=building.egrid,
        address=building.address,
        npa=building.postal_code,
        city=building.city,
        safe_to_start=erp_sts,
        blockers=erp_blockers,
        next_actions=erp_next_actions,
        proof_status=proof_status,
        obligations=obligations,
        passport_grade=passport_grade,
        trust_score=overall_trust,
        completeness=overall_completeness,
    )


async def get_erp_portfolio_payload(
    db: AsyncSession,
    org_id: UUID,
) -> ErpPortfolioPayload | None:
    """Produce a stable, versioned ERP payload for all buildings in an organization.

    Returns None if the organization has no buildings.
    """
    # Fetch all buildings for the org
    result = await db.execute(select(Building).where(Building.organization_id == org_id).order_by(Building.address))
    buildings = list(result.scalars().all())
    if not buildings:
        return None

    now = datetime.now(UTC)
    payloads: list[ErpBuildingPayload] = []
    critical_count = 0
    action_needed_count = 0

    for building in buildings:
        payload = await get_erp_payload(db, building.id)
        if payload:
            payloads.append(payload)
            if payload.safe_to_start.status == "critical_risk":
                critical_count += 1
            if payload.safe_to_start.status in ("critical_risk", "diagnostic_required", "proceed_with_conditions"):
                action_needed_count += 1

    return ErpPortfolioPayload(
        generated_at=now,
        org_id=org_id,
        building_count=len(payloads),
        critical_count=critical_count,
        action_needed_count=action_needed_count,
        buildings=payloads,
    )
