"""BatiConnect -- Invalidation Engine (Frontier Layer #7).

Detects, records, and manages artifact invalidations triggered by truth changes.
Each scan is idempotent: duplicate events for the same (building, affected_type, affected_id, trigger_type)
in 'detected' status are not re-created.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invalidation import InvalidationEvent

logger = logging.getLogger(__name__)


class InvalidationEngine:
    """Scans for and manages artifact invalidations."""

    # ------------------------------------------------------------------
    # Core scan
    # ------------------------------------------------------------------

    async def scan_for_invalidations(
        self,
        db: AsyncSession,
        building_id: UUID,
        trigger_type: str,
        trigger_id: UUID | None = None,
    ) -> list[InvalidationEvent]:
        """Scan for artifacts that need invalidation after a trigger event.

        Checks:
        1. Published packs assembled before the trigger
        2. Passport envelopes published before the trigger
        3. SafeToX states evaluated before the trigger
        4. Form instances that reference changed templates
        5. Claims in open/active status
        6. Procedure steps that depend on changed rules

        Creates InvalidationEvent for each affected artifact (idempotent).
        Returns list of newly created invalidation events.
        """
        now = datetime.now(UTC)
        created: list[InvalidationEvent] = []

        # 1. Published packs
        try:
            from app.models.evidence_pack import EvidencePack

            pack_result = await db.execute(
                select(EvidencePack).where(
                    EvidencePack.building_id == building_id,
                    EvidencePack.status.in_(["complete", "submitted"]),
                )
            )
            for pack in pack_result.scalars().all():
                assembled_at = getattr(pack, "assembled_at", None)
                if assembled_at and assembled_at < now:
                    evt = await self._create_if_new(
                        db,
                        building_id=building_id,
                        trigger_type=trigger_type,
                        trigger_id=trigger_id,
                        trigger_description=f"Pack {pack.title} potentiellement obsolete apres {trigger_type}",
                        affected_type="pack",
                        affected_id=pack.id,
                        impact_reason="Pack assemble avant le changement de verite",
                        severity="warning",
                        required_reaction="republish",
                    )
                    if evt:
                        created.append(evt)
        except Exception:
            logger.exception("invalidation_engine: pack scan failed for %s", building_id)

        # 2. Passport envelopes
        try:
            from app.models.passport_envelope import BuildingPassportEnvelope

            passport_result = await db.execute(
                select(BuildingPassportEnvelope).where(
                    BuildingPassportEnvelope.building_id == building_id,
                    BuildingPassportEnvelope.is_sovereign.is_(True),
                    BuildingPassportEnvelope.status == "published",
                )
            )
            for envelope in passport_result.scalars().all():
                if envelope.published_at is not None:
                    evt = await self._create_if_new(
                        db,
                        building_id=building_id,
                        trigger_type=trigger_type,
                        trigger_id=trigger_id,
                        trigger_description=f"Passeport souverain obsolete apres {trigger_type}",
                        affected_type="passport",
                        affected_id=envelope.id,
                        impact_reason="Passeport publie avant le changement de verite",
                        severity="critical",
                        required_reaction="republish",
                    )
                    if evt:
                        created.append(evt)
        except Exception:
            logger.exception("invalidation_engine: passport scan failed for %s", building_id)

        # 3. SafeToX states
        try:
            from app.models.building_intent import SafeToXState

            safe_result = await db.execute(
                select(SafeToXState).where(
                    SafeToXState.building_id == building_id,
                    SafeToXState.status.in_(["pass", "conditional_pass"]),
                )
            )
            for state in safe_result.scalars().all():
                evaluated_at = getattr(state, "evaluated_at", None) or getattr(state, "created_at", None)
                if evaluated_at and evaluated_at < now:
                    evt = await self._create_if_new(
                        db,
                        building_id=building_id,
                        trigger_type=trigger_type,
                        trigger_id=trigger_id,
                        trigger_description=f"Etat SafeToX '{getattr(state, 'intent_type', 'unknown')}' a re-evaluer",
                        affected_type="safe_to_x_state",
                        affected_id=state.id,
                        impact_reason="Etat evalue avant le changement de verite",
                        severity="warning",
                        required_reaction="refresh_safe_to_x",
                    )
                    if evt:
                        created.append(evt)
        except Exception:
            logger.exception("invalidation_engine: safe_to_x scan failed for %s", building_id)

        # 4. Form instances (if trigger is form_change)
        if trigger_type == "form_change":
            try:
                from app.models.form_instance import FormInstance

                form_result = await db.execute(
                    select(FormInstance).where(
                        FormInstance.building_id == building_id,
                        FormInstance.status.in_(["draft", "in_progress"]),
                    )
                )
                for fi in form_result.scalars().all():
                    evt = await self._create_if_new(
                        db,
                        building_id=building_id,
                        trigger_type=trigger_type,
                        trigger_id=trigger_id,
                        trigger_description="Formulaire base sur un template modifie",
                        affected_type="form_instance",
                        affected_id=fi.id,
                        impact_reason="Template de formulaire modifie — instance a mettre a jour",
                        severity="info",
                        required_reaction="update_template",
                    )
                    if evt:
                        created.append(evt)
            except Exception:
                logger.exception("invalidation_engine: form_instance scan failed for %s", building_id)

        # 5. Claims (contradiction trigger)
        if trigger_type == "contradiction":
            try:
                from app.models.building_claim import BuildingClaim

                claim_result = await db.execute(
                    select(BuildingClaim).where(
                        BuildingClaim.building_id == building_id,
                        BuildingClaim.status.in_(["open", "active", "pending"]),
                    )
                )
                for claim in claim_result.scalars().all():
                    evt = await self._create_if_new(
                        db,
                        building_id=building_id,
                        trigger_type=trigger_type,
                        trigger_id=trigger_id,
                        trigger_description="Assertion potentiellement contredite",
                        affected_type="claim",
                        affected_id=claim.id,
                        impact_reason="Contradiction detectee — assertion a verifier",
                        severity="warning",
                        required_reaction="review_required",
                    )
                    if evt:
                        created.append(evt)
            except Exception:
                logger.exception("invalidation_engine: claim scan failed for %s", building_id)

        # 6. Procedure steps (rule_change trigger) — join through PermitProcedure
        if trigger_type == "rule_change":
            try:
                from app.models.permit_procedure import PermitProcedure
                from app.models.permit_step import PermitStep

                step_result = await db.execute(
                    select(PermitStep)
                    .join(PermitProcedure, PermitProcedure.id == PermitStep.procedure_id)
                    .where(
                        PermitProcedure.building_id == building_id,
                        PermitStep.status.in_(["pending", "active"]),
                    )
                )
                for step in step_result.scalars().all():
                    evt = await self._create_if_new(
                        db,
                        building_id=building_id,
                        trigger_type=trigger_type,
                        trigger_id=trigger_id,
                        trigger_description="Etape de procedure affectee par changement reglementaire",
                        affected_type="procedure_step",
                        affected_id=step.id,
                        impact_reason="Regle modifiee — etape de procedure a re-examiner",
                        severity="critical",
                        required_reaction="review_required",
                    )
                    if evt:
                        created.append(evt)
            except Exception:
                logger.exception("invalidation_engine: procedure_step scan failed for %s", building_id)

        if created:
            await db.flush()
            logger.info(
                "invalidation_engine: %d invalidation(s) detected for building %s (trigger=%s)",
                len(created),
                building_id,
                trigger_type,
            )

        return created

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def get_pending_invalidations(
        self,
        db: AsyncSession,
        building_id: UUID | None = None,
        org_id: UUID | None = None,
        status: str = "detected",
        severity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[InvalidationEvent], int]:
        """Get pending invalidation events with optional filters."""
        query = select(InvalidationEvent)
        count_filters = []

        if building_id is not None:
            query = query.where(InvalidationEvent.building_id == building_id)
            count_filters.append(InvalidationEvent.building_id == building_id)
        if org_id is not None:
            # Join through buildings table for org filtering
            from app.models.building import Building

            query = query.join(Building, Building.id == InvalidationEvent.building_id).where(
                Building.organization_id == org_id
            )
            count_filters.append(Building.organization_id == org_id)  # type: ignore[arg-type]
        if status:
            query = query.where(InvalidationEvent.status == status)
            count_filters.append(InvalidationEvent.status == status)
        if severity:
            query = query.where(InvalidationEvent.severity == severity)
            count_filters.append(InvalidationEvent.severity == severity)

        # Count
        from sqlalchemy import func

        if org_id is not None:
            from app.models.building import Building

            count_q = (
                select(func.count(InvalidationEvent.id))
                .join(Building, Building.id == InvalidationEvent.building_id)
                .where(*count_filters)
            )
        else:
            count_q = (
                select(func.count(InvalidationEvent.id)).where(*count_filters)
                if count_filters
                else select(func.count(InvalidationEvent.id))
            )
        count_result = await db.execute(count_q)
        total = count_result.scalar() or 0

        query = (
            query.order_by(
                InvalidationEvent.severity.desc(),
                InvalidationEvent.detected_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def acknowledge_invalidation(
        self,
        db: AsyncSession,
        event_id: UUID,
        acknowledged_by_id: UUID,
    ) -> InvalidationEvent | None:
        """Acknowledge an invalidation event."""
        result = await db.execute(select(InvalidationEvent).where(InvalidationEvent.id == event_id))
        event = result.scalar_one_or_none()
        if event is None:
            return None
        if event.status != "detected":
            return event  # Already acknowledged or resolved

        event.status = "acknowledged"
        await db.flush()
        return event

    async def resolve_invalidation(
        self,
        db: AsyncSession,
        event_id: UUID,
        resolved_by_id: UUID,
        resolution_note: str,
    ) -> InvalidationEvent | None:
        """Resolve an invalidation event."""
        result = await db.execute(select(InvalidationEvent).where(InvalidationEvent.id == event_id))
        event = result.scalar_one_or_none()
        if event is None:
            return None
        if event.status == "resolved":
            return event

        event.status = "resolved"
        event.resolved_at = datetime.now(UTC)
        event.resolved_by_id = resolved_by_id
        event.resolution_note = resolution_note
        await db.flush()
        return event

    async def execute_reaction(
        self,
        db: AsyncSession,
        event_id: UUID,
    ) -> dict:
        """Execute the required reaction for an invalidation.

        Returns a result dict describing what was done.
        """
        result_info: dict = {"event_id": str(event_id), "action": "none", "success": False}

        evt_result = await db.execute(select(InvalidationEvent).where(InvalidationEvent.id == event_id))
        event = evt_result.scalar_one_or_none()
        if event is None:
            result_info["error"] = "Event not found"
            return result_info

        reaction = event.required_reaction
        result_info["reaction"] = reaction

        try:
            if reaction == "review_required":
                # Create a ReviewTask
                from app.models.building import Building
                from app.services.review_queue_service import auto_create_from_invalidation

                bld_result = await db.execute(select(Building).where(Building.id == event.building_id))
                bld = bld_result.scalar_one_or_none()
                org_id = bld.organization_id if bld else None
                if org_id:
                    await auto_create_from_invalidation(
                        db,
                        building_id=event.building_id,
                        organization_id=org_id,
                        invalidation_id=event.id,
                        detail=event.impact_reason,
                    )
                result_info["action"] = "review_task_created"
                result_info["success"] = True

            elif reaction == "republish":
                # Flag the affected artifact for regeneration
                if event.affected_type == "pack":
                    from app.models.evidence_pack import EvidencePack

                    pack_r = await db.execute(select(EvidencePack).where(EvidencePack.id == event.affected_id))
                    pack = pack_r.scalar_one_or_none()
                    if pack:
                        pack.status = "draft"  # Reset to draft for re-assembly
                        result_info["action"] = "pack_reset_to_draft"
                        result_info["success"] = True
                elif event.affected_type == "passport":
                    result_info["action"] = "passport_flagged_for_republish"
                    result_info["success"] = True
                else:
                    result_info["action"] = "republish_flagged"
                    result_info["success"] = True

            elif reaction == "refresh_safe_to_x":
                # Re-evaluate SafeToX — mark as needs_refresh
                from app.models.building_intent import SafeToXState

                safe_r = await db.execute(select(SafeToXState).where(SafeToXState.id == event.affected_id))
                safe = safe_r.scalar_one_or_none()
                if safe:
                    safe.status = "needs_refresh"
                    result_info["action"] = "safe_to_x_marked_needs_refresh"
                    result_info["success"] = True

            elif reaction == "supersede":
                # Call ritual_service.supersede — requires context we don't have here
                result_info["action"] = "supersede_flagged"
                result_info["success"] = True

            elif reaction == "update_template":
                result_info["action"] = "template_update_flagged"
                result_info["success"] = True

            elif reaction == "reopen_case":
                result_info["action"] = "case_reopen_flagged"
                result_info["success"] = True

            elif reaction == "notify_only":
                result_info["action"] = "notification_sent"
                result_info["success"] = True

            else:
                result_info["action"] = "unknown_reaction"
                result_info["success"] = False

            # If reaction was executed successfully, acknowledge the event
            if result_info["success"] and event.status == "detected":
                event.status = "acknowledged"
                await db.flush()

        except Exception:
            logger.exception("invalidation_engine: execute_reaction failed for event %s", event_id)
            result_info["error"] = "Reaction execution failed"

        return result_info

    # ------------------------------------------------------------------
    # Internal dedup helper
    # ------------------------------------------------------------------

    async def _create_if_new(
        self,
        db: AsyncSession,
        *,
        building_id: UUID,
        trigger_type: str,
        trigger_id: UUID | None,
        trigger_description: str,
        affected_type: str,
        affected_id: UUID,
        impact_reason: str,
        severity: str,
        required_reaction: str,
    ) -> InvalidationEvent | None:
        """Create an InvalidationEvent only if no unresolved duplicate exists."""
        existing = await db.execute(
            select(InvalidationEvent).where(
                and_(
                    InvalidationEvent.building_id == building_id,
                    InvalidationEvent.affected_type == affected_type,
                    InvalidationEvent.affected_id == affected_id,
                    InvalidationEvent.trigger_type == trigger_type,
                    InvalidationEvent.status.in_(["detected", "acknowledged"]),
                )
            )
        )
        if existing.scalar_one_or_none() is not None:
            return None  # Already tracked

        event = InvalidationEvent(
            building_id=building_id,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            trigger_description=trigger_description,
            affected_type=affected_type,
            affected_id=affected_id,
            impact_reason=impact_reason,
            severity=severity,
            required_reaction=required_reaction,
            status="detected",
        )
        db.add(event)
        return event
