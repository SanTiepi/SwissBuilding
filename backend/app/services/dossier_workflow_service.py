"""Safe-to-Start Dossier Workflow -- the sellable wedge.

Orchestrates the full lifecycle:
  assess -> fix gaps -> generate pack -> submit -> complement -> resubmit -> acknowledged

This is a pure orchestrator: no DB models, no new state. Lifecycle stage is
derived from existing data (readiness, packs, rituals, actions, unknowns).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.evidence_pack import EvidencePack
from app.models.truth_ritual import TruthRitual
from app.schemas.authority_pack import AuthorityPackConfig
from app.services import (
    authority_pack_service,
    completeness_engine,
    readiness_action_generator,
    ritual_service,
)
from app.services.invalidation_engine import InvalidationEngine
from app.services.readiness_reasoner import evaluate_readiness
from app.services.unknowns_ledger_service import get_unknowns_impact, scan_building

logger = logging.getLogger(__name__)

# Work types accepted by the workflow
SUPPORTED_WORK_TYPES = (
    "asbestos_removal",
    "pcb_remediation",
    "lead_remediation",
    "full_pollutant",
)

# Lifecycle stages (derived, never stored)
LIFECYCLE_STAGES = (
    "not_assessed",
    "not_ready",
    "partially_ready",
    "ready",
    "pack_generated",
    "submitted",
    "complement_requested",
    "resubmitted",
    "acknowledged",
)

# Progress step definitions (French labels)
_PROGRESS_STEPS = [
    "Evaluation initiale",
    "Resolution des manques",
    "Generation du pack",
    "Soumission",
    "Traitement complements",
    "Accuse de reception",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_building(db: AsyncSession, building_id: UUID) -> Building:
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")
    return building


async def _get_latest_pack(
    db: AsyncSession,
    building_id: UUID,
) -> EvidencePack | None:
    """Get the most recent non-expired authority pack for a building."""
    result = await db.execute(
        select(EvidencePack)
        .where(
            EvidencePack.building_id == building_id,
            EvidencePack.pack_type == "authority_pack",
            EvidencePack.status != "expired",
        )
        .order_by(
            EvidencePack.assembled_at.desc().nullslast(),
            EvidencePack.created_at.desc(),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_open_actions(
    db: AsyncSession,
    building_id: UUID,
) -> list[ActionItem]:
    result = await db.execute(
        select(ActionItem).where(
            and_(
                ActionItem.building_id == building_id,
                ActionItem.status.in_(["open", "in_progress"]),
            )
        )
    )
    return list(result.scalars().all())


async def _get_pack_rituals(
    db: AsyncSession,
    building_id: UUID,
    pack_id: UUID,
) -> list[TruthRitual]:
    """Get rituals linked to a specific pack."""
    return await ritual_service.get_ritual_history(
        db,
        building_id=building_id,
        target_type="pack",
        target_id=pack_id,
    )


def _derive_pack_status(pack: EvidencePack | None, rituals: list[TruthRitual]) -> str:
    """Derive the pack lifecycle status from pack record + rituals."""
    if pack is None:
        return "not_generated"

    # Check for acknowledge ritual
    has_acknowledge = any(r.ritual_type == "acknowledge" for r in rituals)
    if has_acknowledge:
        return "acknowledged"

    # Check if pack notes contain complement marker
    notes = pack.notes or ""
    if "complement_requested" in notes:
        return "complement_requested"

    if pack.submitted_at is not None:
        return "submitted"

    if pack.status in ("complete", "assembling"):
        return "draft"

    return "draft"


def _derive_lifecycle_stage(
    readiness_status: str,
    readiness_score: float,
    pack_status: str,
) -> str:
    """Derive the overall lifecycle stage from readiness + pack status."""
    if pack_status == "acknowledged":
        return "acknowledged"
    if pack_status == "complement_requested":
        return "complement_requested"
    if pack_status == "submitted":
        return "submitted"
    if pack_status in ("draft",):
        return "pack_generated"

    # No pack yet: derive from readiness
    if readiness_status == "ready":
        return "ready"
    if readiness_status == "conditional":
        return "partially_ready"
    if readiness_status == "blocked":
        return "not_ready"

    return "not_assessed"


def _build_progress_steps(lifecycle_stage: str) -> list[dict]:
    """Build progress step list with statuses based on lifecycle stage."""
    stage_order = {
        "not_assessed": 0,
        "not_ready": 1,
        "partially_ready": 1,
        "ready": 2,
        "pack_generated": 3,
        "submitted": 4,
        "complement_requested": 4,
        "resubmitted": 4,
        "acknowledged": 6,
    }
    current = stage_order.get(lifecycle_stage, 0)

    steps = []
    for i, name in enumerate(_PROGRESS_STEPS):
        step_number = i + 1
        if step_number < current:
            status = "done"
        elif step_number == current:
            status = "in_progress"
        else:
            status = "pending"
        steps.append({"name": name, "status": status})

    return steps


def _derive_next_action(
    lifecycle_stage: str,
    readiness_blockers: list[str],
) -> dict:
    """Determine the recommended next action for the user."""
    if lifecycle_stage == "not_assessed":
        return {
            "title": "Lancer l'evaluation initiale",
            "description": "Evaluez la readiness du batiment pour determiner les manques.",
            "action_type": "fix_blocker",
        }
    if lifecycle_stage in ("not_ready", "partially_ready"):
        first_blocker = readiness_blockers[0] if readiness_blockers else "Resoudre les blocages"
        return {
            "title": "Resoudre les blocages",
            "description": first_blocker,
            "action_type": "fix_blocker",
        }
    if lifecycle_stage == "ready":
        return {
            "title": "Generer le pack autorite",
            "description": "Le dossier est pret. Generez le pack pour soumission.",
            "action_type": "generate_pack",
        }
    if lifecycle_stage == "pack_generated":
        return {
            "title": "Soumettre le pack a l'autorite",
            "description": "Le pack est pret. Soumettez-le a l'autorite competente.",
            "action_type": "submit",
        }
    if lifecycle_stage == "complement_requested":
        return {
            "title": "Traiter les complements demandes",
            "description": "L'autorite a demande des complements. Resolvedez les avant de resoumettre.",
            "action_type": "fix_complement",
        }
    if lifecycle_stage in ("submitted", "resubmitted"):
        return {
            "title": "En attente de l'autorite",
            "description": "Le pack a ete soumis. Attendez l'accuse de reception.",
            "action_type": "wait",
        }
    if lifecycle_stage == "acknowledged":
        return {
            "title": "Dossier accepte",
            "description": "L'autorite a accuse reception du dossier.",
            "action_type": "wait",
        }
    return {
        "title": "Evaluer le dossier",
        "description": "Lancez l'evaluation pour determiner l'etat du dossier.",
        "action_type": "fix_blocker",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class DossierWorkflowService:
    """Orchestrates the full safe-to-start dossier lifecycle."""

    async def get_dossier_status(
        self,
        db: AsyncSession,
        building_id: UUID,
        work_type: str = "asbestos_removal",
    ) -> dict:
        """Get the current dossier lifecycle status for a building + work type.

        Returns a comprehensive status dict covering readiness, completeness,
        unknowns, actions, pack status, progress steps, and next action.
        """
        await _get_building(db, building_id)

        # 1. Evaluate readiness
        try:
            assessment = await evaluate_readiness(db, building_id, "safe_to_start")
            readiness_status = assessment.status or "blocked"
            readiness_score = assessment.score or 0.0
            blockers = [b.get("message", str(b)) for b in (assessment.blockers_json or [])]
            conditions = [c.get("message", str(c)) for c in (assessment.conditions_json or [])]
            safe_to_start = {
                "status": readiness_status,
                "score": readiness_score,
                "checks_count": len(assessment.checks_json or []),
            }
        except Exception:
            readiness_status = "blocked"
            readiness_score = 0.0
            blockers = ["Evaluation en erreur"]
            conditions = []
            safe_to_start = {"status": "error", "score": 0.0, "checks_count": 0}

        # 2. Evaluate completeness
        try:
            completeness = await completeness_engine.evaluate_completeness(db, building_id, "avt")
            completeness_data = {
                "score_pct": round(completeness.overall_score * 100, 1),
                "documented": [c.label_key for c in completeness.checks if c.status == "complete"],
                "missing": completeness.missing_items,
                "expired": [c.label_key for c in completeness.checks if c.status == "partial"],
            }
        except Exception:
            completeness_data = {
                "score_pct": 0.0,
                "documented": [],
                "missing": [],
                "expired": [],
            }

        # 3. Unknowns
        try:
            unknowns_impact = await get_unknowns_impact(db, building_id)
            critical_unknowns = []
            for entry in unknowns_impact.get("most_urgent", []):
                if hasattr(entry, "subject"):
                    critical_unknowns.append(entry.subject)
                elif isinstance(entry, dict):
                    critical_unknowns.append(entry.get("subject", str(entry)))
            unknowns_data = {
                "count": unknowns_impact.get("total_open", 0),
                "critical": critical_unknowns[:5],
            }
        except Exception:
            unknowns_data = {"count": 0, "critical": []}

        # 4. Actions
        open_actions = await _get_open_actions(db, building_id)
        high_priority_actions = [
            {"title": a.title, "priority": a.priority, "status": a.status}
            for a in open_actions
            if a.priority in ("critical", "high")
        ][:5]
        actions_data = {
            "total_open": len(open_actions),
            "high_priority": high_priority_actions,
        }

        # 5. Pack status
        pack = await _get_latest_pack(db, building_id)
        pack_rituals = await _get_pack_rituals(db, building_id, pack.id) if pack else []
        pack_status = _derive_pack_status(pack, pack_rituals)

        pack_data = {
            "status": pack_status,
            "pack_id": str(pack.id) if pack else None,
            "conformance": None,
            "submitted_at": pack.submitted_at.isoformat() if pack and pack.submitted_at else None,
            "complement_details": None,
        }

        # Check if complement was requested (stored in notes)
        if pack and pack.notes and "complement_requested" in pack.notes:
            try:
                import json

                notes_data = json.loads(pack.notes)
                pack_data["complement_details"] = notes_data.get("complement_details")
            except Exception:
                pass

        # 6. Derive lifecycle stage
        lifecycle_stage = _derive_lifecycle_stage(readiness_status, readiness_score, pack_status)

        # 7. Progress steps
        progress_steps = _build_progress_steps(lifecycle_stage)
        steps_completed = sum(1 for s in progress_steps if s["status"] == "done")

        # 8. Next action
        next_action = _derive_next_action(lifecycle_stage, blockers)

        return {
            "building_id": str(building_id),
            "work_type": work_type,
            "lifecycle_stage": lifecycle_stage,
            "readiness": {
                "verdict": readiness_status,
                "safe_to_start": safe_to_start,
                "blockers": blockers,
                "conditions": conditions,
            },
            "completeness": completeness_data,
            "unknowns": unknowns_data,
            "actions": actions_data,
            "pack": pack_data,
            "progress": {
                "steps_completed": steps_completed,
                "steps_total": 6,
                "steps": progress_steps,
            },
            "next_action": next_action,
        }

    async def fix_blocker(
        self,
        db: AsyncSession,
        building_id: UUID,
        blocker_type: str,
        resolution_data: dict,
        resolved_by_id: UUID,
    ) -> dict:
        """Resolve a specific blocker (expired diagnostic, missing document, etc).

        Triggers re-evaluation of readiness and unknowns after resolution.
        Returns updated dossier status.
        """
        await _get_building(db, building_id)

        # Re-scan unknowns (will auto-resolve those that are fixed)
        await scan_building(db, building_id)

        # Re-evaluate readiness
        await evaluate_readiness(db, building_id, "safe_to_start", assessed_by_id=resolved_by_id)

        # Generate/update readiness actions
        await readiness_action_generator.generate_readiness_actions(db, building_id, "safe_to_start")

        await db.commit()

        return await self.get_dossier_status(db, building_id)

    async def generate_dossier_pack(
        self,
        db: AsyncSession,
        building_id: UUID,
        work_type: str,
        created_by_id: UUID,
        org_id: UUID | None = None,
    ) -> dict:
        """Generate the authority-ready pack for this dossier.

        Only allowed when readiness >= partially_ready (conditional or ready).
        Returns pack data + updated dossier status.
        """
        await _get_building(db, building_id)

        # Check readiness
        assessment = await evaluate_readiness(db, building_id, "safe_to_start")
        if assessment.status == "blocked":
            raise ValueError(
                "Impossible de generer le pack: le dossier n'est pas pret. "
                "Resolvez les blocages avant de generer le pack."
            )

        # Generate authority pack
        config = AuthorityPackConfig(
            building_id=building_id,
            language="fr",
        )
        pack_result = await authority_pack_service.generate_authority_pack(db, building_id, config, created_by_id)

        return {
            "pack_id": str(pack_result.pack_id),
            "overall_completeness": pack_result.overall_completeness,
            "total_sections": pack_result.total_sections,
            "sha256_hash": pack_result.sha256_hash,
            "status": await self.get_dossier_status(db, building_id, work_type),
        }

    async def submit_to_authority(
        self,
        db: AsyncSession,
        building_id: UUID,
        pack_id: UUID,
        submitted_by_id: UUID,
        org_id: UUID | None = None,
        submission_reference: str | None = None,
    ) -> dict:
        """Mark the pack as submitted to the authority.

        Records a TruthRitual (publish) and updates pack submitted_at.
        """
        await _get_building(db, building_id)

        # Fetch the pack
        result = await db.execute(select(EvidencePack).where(EvidencePack.id == pack_id))
        pack = result.scalar_one_or_none()
        if pack is None:
            raise ValueError(f"Pack {pack_id} not found")
        if pack.building_id != building_id:
            raise ValueError("Pack does not belong to this building")

        # Update pack status
        pack.status = "submitted"
        pack.submitted_at = datetime.now(UTC)
        if submission_reference:
            existing_notes = pack.notes or ""
            pack.notes = existing_notes + f"\n[submission_reference]: {submission_reference}"

        # Record publish ritual
        await ritual_service.publish(
            db,
            building_id=building_id,
            target_type="pack",
            target_id=pack_id,
            published_by_id=submitted_by_id,
            org_id=org_id or submitted_by_id,
            reason=f"Pack soumis a l'autorite — ref: {submission_reference or 'N/A'}",
        )

        await db.commit()

        return await self.get_dossier_status(db, building_id)

    async def handle_complement_request(
        self,
        db: AsyncSession,
        building_id: UUID,
        pack_id: UUID,
        complement_details: str,
        received_by_id: UUID,
    ) -> dict:
        """Handle authority complement request.

        - Marks the pack with complement details
        - Creates actions for missing pieces
        - Triggers invalidation engine
        - Re-evaluates readiness
        Returns updated dossier status with new actions.
        """
        await _get_building(db, building_id)

        # Fetch the pack
        result = await db.execute(select(EvidencePack).where(EvidencePack.id == pack_id))
        pack = result.scalar_one_or_none()
        if pack is None:
            raise ValueError(f"Pack {pack_id} not found")

        # Mark complement request in notes
        import json

        try:
            notes_data = json.loads(pack.notes) if pack.notes else {}
        except (json.JSONDecodeError, TypeError):
            notes_data = {}
        notes_data["complement_requested"] = True
        notes_data["complement_details"] = complement_details
        notes_data["complement_requested_at"] = datetime.now(UTC).isoformat()
        pack.notes = json.dumps(notes_data, default=str)

        # Create an action for the complement
        action = ActionItem(
            building_id=building_id,
            source_type="dossier_workflow",
            action_type="documentation",
            title="Complement autorite requis",
            description=complement_details,
            priority="high",
            status="open",
        )
        db.add(action)

        # Record reopen ritual
        await ritual_service.reopen(
            db,
            building_id=building_id,
            target_type="pack",
            target_id=pack_id,
            reopened_by_id=received_by_id,
            org_id=received_by_id,
            reason=f"Complement demande par l'autorite: {complement_details}",
        )

        # Trigger invalidation engine
        engine = InvalidationEngine()
        await engine.scan_for_invalidations(db, building_id, trigger_type="complement_requested", trigger_id=pack_id)

        # Re-evaluate readiness
        await evaluate_readiness(db, building_id, "safe_to_start")

        await db.commit()

        return await self.get_dossier_status(db, building_id)

    async def resubmit_pack(
        self,
        db: AsyncSession,
        building_id: UUID,
        work_type: str,
        resubmitted_by_id: UUID,
        org_id: UUID | None = None,
    ) -> dict:
        """Regenerate and resubmit after fixing complement issues.

        Supersedes the previous pack. Returns new pack + conformance.
        """
        await _get_building(db, building_id)

        # Get previous pack for supersede ritual
        old_pack = await _get_latest_pack(db, building_id)

        # Generate new pack
        config = AuthorityPackConfig(
            building_id=building_id,
            language="fr",
        )
        new_pack_result = await authority_pack_service.generate_authority_pack(
            db, building_id, config, resubmitted_by_id
        )

        # Mark old pack as expired (superseded) and record ritual
        if old_pack:
            old_pack.status = "expired"
            await ritual_service.supersede(
                db,
                building_id=building_id,
                target_type="pack",
                target_id=old_pack.id,
                superseded_by_id=resubmitted_by_id,
                org_id=org_id or resubmitted_by_id,
                new_target_id=new_pack_result.pack_id,
                reason="Resoumission apres complement autorite",
            )

        # Auto-submit the new pack
        result = await db.execute(select(EvidencePack).where(EvidencePack.id == new_pack_result.pack_id))
        new_pack = result.scalar_one_or_none()
        if new_pack:
            new_pack.status = "submitted"
            new_pack.submitted_at = datetime.now(UTC)

        # Record publish ritual
        await ritual_service.publish(
            db,
            building_id=building_id,
            target_type="pack",
            target_id=new_pack_result.pack_id,
            published_by_id=resubmitted_by_id,
            org_id=org_id or resubmitted_by_id,
            reason="Resoumission du pack apres complement",
        )

        await db.commit()

        return {
            "pack_id": str(new_pack_result.pack_id),
            "overall_completeness": new_pack_result.overall_completeness,
            "total_sections": new_pack_result.total_sections,
            "sha256_hash": new_pack_result.sha256_hash,
            "status": await self.get_dossier_status(db, building_id, work_type),
        }

    async def acknowledge_receipt(
        self,
        db: AsyncSession,
        building_id: UUID,
        pack_id: UUID,
        acknowledged_by_id: UUID,
        org_id: UUID | None = None,
    ) -> dict:
        """Record that the authority acknowledged the submission.

        Records a TruthRitual (acknowledge).
        Marks the dossier as authority-ready.
        """
        await _get_building(db, building_id)

        # Verify pack exists and is submitted
        result = await db.execute(select(EvidencePack).where(EvidencePack.id == pack_id))
        pack = result.scalar_one_or_none()
        if pack is None:
            raise ValueError(f"Pack {pack_id} not found")
        if pack.building_id != building_id:
            raise ValueError("Pack does not belong to this building")
        if pack.submitted_at is None:
            raise ValueError("Pack has not been submitted yet")

        # Record acknowledge ritual
        await ritual_service.acknowledge(
            db,
            building_id=building_id,
            target_type="pack",
            target_id=pack_id,
            acknowledged_by_id=acknowledged_by_id,
            org_id=org_id or acknowledged_by_id,
            reason="Accuse de reception de l'autorite",
        )

        await db.commit()

        return await self.get_dossier_status(db, building_id)
