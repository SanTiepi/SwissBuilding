"""BatiConnect -- Consequence Engine.

Orchestrates automatic consequences when building truth changes.
Called after any apply/update that modifies canonical building data.

Each step is idempotent (underlying generators handle dedup/auto-resolve).
Each step is isolated: if one fails, the rest continue.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consequence_run import ConsequenceRun
from app.models.evidence_pack import EvidencePack
from app.models.passport_envelope import BuildingPassportEnvelope

logger = logging.getLogger(__name__)

# Trigger types accepted by the engine
TRIGGER_TYPES = frozenset(
    {
        "extraction_applied",
        "document_uploaded",
        "claim_created",
        "decision_enacted",
        "intervention_completed",
        "observation_recorded",
        "manual_update",
    }
)


class ConsequenceEngine:
    """Orchestrates automatic consequences when building truth changes."""

    async def run_consequences(
        self,
        db: AsyncSession,
        building_id: UUID,
        trigger_type: str,
        trigger_id: str | None = None,
        triggered_by_id: UUID | None = None,
    ) -> dict:
        """Run the full consequence chain for a building after a truth change.

        Steps (in order):
        1. contradiction_detector -- detect new contradictions
        2. unknown_generator -- detect new gaps
        3. action_generator -- generate actions from findings (diagnostics)
        4. readiness_action_generator -- convert blocked readiness to actions
        5. trust_score_calculator -- recompute trust
        6. Record a BuildingEvent -- log what triggered the chain
        7. change_tracker detect_signals -- detect patterns
        8. Check pack staleness -- flag published packs that may be stale
        9. Check passport staleness -- flag if passport needs new version

        Returns a result dict summarizing what happened.
        """
        started_at = datetime.now(UTC)
        result: dict = {
            "trigger": {"type": trigger_type, "id": trigger_id},
            "contradictions_found": 0,
            "unknowns_detected": 0,
            "actions_generated": 0,
            "readiness_actions": 0,
            "trust_updated": False,
            "event_recorded": None,
            "signals_detected": 0,
            "stale_packs": 0,
            "stale_passport": False,
            "invalidations_detected": 0,
            "total_consequences": 0,
            "errors": [],
        }

        # 1. Contradiction detection
        try:
            from app.services.contradiction_detector import detect_contradictions

            issues = await detect_contradictions(db, building_id)
            result["contradictions_found"] = len(issues)

            # Auto-create review tasks for new contradictions
            if issues:
                try:
                    from app.models.building import Building
                    from app.services.review_queue_service import auto_create_from_contradiction

                    bld_result = await db.execute(select(Building).where(Building.id == building_id))
                    bld = bld_result.scalar_one_or_none()
                    org_id = bld.organization_id if bld else None
                    if org_id:
                        for issue in issues:
                            issue_id = getattr(issue, "id", None)
                            if issue_id:
                                await auto_create_from_contradiction(
                                    db,
                                    building_id=building_id,
                                    organization_id=org_id,
                                    contradiction_id=issue_id,
                                    contradiction_detail=getattr(issue, "description", "Contradiction detectee"),
                                )
                except Exception:
                    logger.exception("consequence_engine: review_queue contradiction tasks failed for %s", building_id)
        except Exception:
            logger.exception("consequence_engine: contradiction_detector failed for %s", building_id)
            result["errors"].append("contradiction_detector")

        # 2. Unknown generation
        try:
            from app.services.unknown_generator import generate_unknowns

            unknowns = await generate_unknowns(db, building_id)
            result["unknowns_detected"] = len(unknowns)
        except Exception:
            logger.exception("consequence_engine: unknown_generator failed for %s", building_id)
            result["errors"].append("unknown_generator")

        # 2b. Unknowns Ledger scan (first-class ledger entries)
        try:
            from app.services.unknowns_ledger_service import scan_building

            ledger_result = await scan_building(db, building_id)
            result["ledger_entries_created"] = ledger_result.get("created", 0)
            result["ledger_entries_resolved"] = ledger_result.get("resolved", 0)
        except Exception:
            logger.exception("consequence_engine: unknowns_ledger scan failed for %s", building_id)
            result["errors"].append("unknowns_ledger")

        # 3. Action generation (from all completed diagnostics)
        try:
            from app.models.diagnostic import Diagnostic
            from app.services.action_generator import generate_actions_from_diagnostic

            diag_result = await db.execute(
                select(Diagnostic).where(
                    Diagnostic.building_id == building_id,
                    Diagnostic.status.in_(["completed", "validated"]),
                )
            )
            diagnostics = list(diag_result.scalars().all())
            total_actions = 0
            for diag in diagnostics:
                actions = await generate_actions_from_diagnostic(db, building_id, diag.id)
                total_actions += len(actions)
            result["actions_generated"] = total_actions
        except Exception:
            logger.exception("consequence_engine: action_generator failed for %s", building_id)
            result["errors"].append("action_generator")

        # 4. Readiness action generation
        try:
            from app.services.readiness_action_generator import generate_readiness_actions

            readiness_actions = await generate_readiness_actions(db, building_id)
            result["readiness_actions"] = len(readiness_actions)
        except Exception:
            logger.exception("consequence_engine: readiness_action_generator failed for %s", building_id)
            result["errors"].append("readiness_action_generator")

        # 5. Trust score recalculation
        try:
            from app.services.trust_score_calculator import calculate_trust_score

            await calculate_trust_score(db, building_id, assessed_by="consequence_engine")
            result["trust_updated"] = True
        except Exception:
            logger.exception("consequence_engine: trust_score_calculator failed for %s", building_id)
            result["errors"].append("trust_score_calculator")

        # 6. Record building event
        try:
            from app.services.change_tracker_service import record_event

            event = await record_event(
                db,
                building_id,
                event_type="consequence_chain",
                title=f"Consequence chain triggered by {trigger_type}",
                actor_id=triggered_by_id,
                description=f"Trigger: {trigger_type}, trigger_id: {trigger_id}",
                severity="info",
                source_type=trigger_type,
            )
            result["event_recorded"] = str(event.id)
        except Exception:
            logger.exception("consequence_engine: record_event failed for %s", building_id)
            result["errors"].append("record_event")

        # 7. Signal detection
        try:
            from app.services.change_tracker_service import detect_signals

            signals = await detect_signals(db, building_id)
            result["signals_detected"] = len(signals)
        except Exception:
            logger.exception("consequence_engine: detect_signals failed for %s", building_id)
            result["errors"].append("detect_signals")

        # 8. Pack staleness check
        try:
            stale_packs = await self.check_pack_staleness(db, building_id)
            result["stale_packs"] = len(stale_packs)
        except Exception:
            logger.exception("consequence_engine: check_pack_staleness failed for %s", building_id)
            result["errors"].append("check_pack_staleness")

        # 9. Passport staleness check
        try:
            result["stale_passport"] = await self.check_passport_staleness(db, building_id)
        except Exception:
            logger.exception("consequence_engine: check_passport_staleness failed for %s", building_id)
            result["errors"].append("check_passport_staleness")

        # 10. Invalidation engine scan
        try:
            from app.services.invalidation_engine import InvalidationEngine

            inv_engine = InvalidationEngine()
            invalidations = await inv_engine.scan_for_invalidations(
                db, building_id, trigger_type, trigger_id=None
            )
            result["invalidations_detected"] = len(invalidations)
        except Exception:
            logger.exception("consequence_engine: invalidation_engine failed for %s", building_id)
            result["errors"].append("invalidation_engine")

        # Compute total consequences
        result["total_consequences"] = (
            result["contradictions_found"]
            + result["unknowns_detected"]
            + result["actions_generated"]
            + result["readiness_actions"]
            + (1 if result["trust_updated"] else 0)
            + (1 if result["event_recorded"] else 0)
            + result["signals_detected"]
            + result["stale_packs"]
            + (1 if result["stale_passport"] else 0)
            + result["invalidations_detected"]
        )

        # Remove errors key if empty
        if not result["errors"]:
            del result["errors"]

        # Persist the consequence run record
        status = "completed" if "errors" not in result else "partial"
        run = ConsequenceRun(
            building_id=building_id,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            triggered_by_id=triggered_by_id,
            result_json=result,
            status=status,
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )
        db.add(run)
        await db.flush()

        logger.info(
            "consequence_engine: completed for building %s (trigger=%s, total=%d)",
            building_id,
            trigger_type,
            result["total_consequences"],
        )

        return result

    async def check_pack_staleness(self, db: AsyncSession, building_id: UUID) -> list:
        """Check if any published packs are now stale because truth changed.

        A pack is stale if it was published/assembled before now (since we just
        changed truth). We mark stale packs by looking at complete/submitted packs.
        Returns list of stale pack IDs.
        """
        now = datetime.now(UTC)
        pack_result = await db.execute(
            select(EvidencePack).where(
                EvidencePack.building_id == building_id,
                EvidencePack.status.in_(["complete", "submitted"]),
            )
        )
        packs = list(pack_result.scalars().all())

        stale_ids: list[str] = []
        for pack in packs:
            # A pack assembled before now is potentially stale after a truth change
            assembled_at = pack.assembled_at
            if assembled_at and assembled_at < now:
                stale_ids.append(str(pack.id))

        return stale_ids

    async def check_passport_staleness(self, db: AsyncSession, building_id: UUID) -> bool:
        """Check if the current sovereign passport is stale.

        Stale if published before the current truth change (which is now).
        """
        result = await db.execute(
            select(BuildingPassportEnvelope).where(
                BuildingPassportEnvelope.building_id == building_id,
                BuildingPassportEnvelope.is_sovereign.is_(True),
                BuildingPassportEnvelope.status == "published",
            )
        )
        envelope = result.scalar_one_or_none()
        if envelope is None:
            return False

        # If published before now, it's stale after this truth change
        return envelope.published_at is not None


async def get_last_consequence_run(
    db: AsyncSession,
    building_id: UUID,
) -> ConsequenceRun | None:
    """Get the most recent consequence run for a building."""
    result = await db.execute(
        select(ConsequenceRun)
        .where(ConsequenceRun.building_id == building_id)
        .order_by(ConsequenceRun.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
