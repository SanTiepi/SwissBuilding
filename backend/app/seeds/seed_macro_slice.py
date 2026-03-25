"""
Macro-slice seed — ControlTower v2 demo data.

Creates realistic scenario for ONE existing seed building (Lausanne):
- 1 PermitProcedure (construction_permit, complement_requested, 4 steps)
- 1 AuthorityRequest (complement_request, overdue)
- 2 Obligations (1 overdue authority_submission, 1 due_soon diagnostic_followup)

Idempotent via UUID5.

Usage:
    python -m app.seeds.seed_macro_slice
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.authority_request import AuthorityRequest
from app.models.building import Building
from app.models.obligation import Obligation
from app.models.permit_procedure import PermitProcedure
from app.models.permit_step import PermitStep

logger = logging.getLogger(__name__)

# Stable namespace for idempotent UUIDs
_NS = uuid.UUID("c0n7r01-70w3-feed-0001-000000000000")


def _id(label: str) -> uuid.UUID:
    return uuid.uuid5(_NS, label)


# Pre-computed IDs
ID_PERMIT = _id("macro-permit-construction")
ID_STEP_SUBMISSION = _id("macro-step-submission")
ID_STEP_REVIEW = _id("macro-step-review")
ID_STEP_COMPLEMENT = _id("macro-step-complement")
ID_STEP_DECISION = _id("macro-step-decision")
ID_AUTH_REQUEST = _id("macro-auth-complement-request")
ID_OBL_OVERDUE = _id("macro-obligation-overdue")
ID_OBL_DUE_SOON = _id("macro-obligation-due-soon")


async def seed_macro_slice(db: AsyncSession) -> None:
    """Seed ControlTower v2 demo data onto the first Lausanne building."""
    # Find first Lausanne building
    result = await db.execute(select(Building).where(Building.city == "Lausanne").limit(1))
    building = result.scalar_one_or_none()
    if not building:
        logger.warning("seed_macro_slice: no Lausanne building found — skipping")
        return

    bid = building.id
    today = date.today()

    # --- PermitProcedure ---
    existing = await db.execute(select(PermitProcedure).where(PermitProcedure.id == ID_PERMIT))
    if not existing.scalar_one_or_none():
        db.add(
            PermitProcedure(
                id=ID_PERMIT,
                building_id=bid,
                procedure_type="construction_permit",
                title="Permis de construire — désamiantage parties communes",
                description="Autorisation de construire pour travaux de désamiantage des parties communes.",
                authority_name="Service de l'urbanisme, Ville de Lausanne",
                authority_type="communal",
                status="complement_requested",
                reference_number="PC-2026-00142",
            )
        )
        await db.flush()

    # --- PermitSteps (4) ---
    steps_data = [
        (ID_STEP_SUBMISSION, "submission", "Dépôt du dossier", "completed", 1),
        (ID_STEP_REVIEW, "review", "Examen préliminaire", "completed", 2),
        (ID_STEP_COMPLEMENT, "complement_request", "Demande de compléments", "active", 3),
        (ID_STEP_DECISION, "decision", "Décision finale", "pending", 4),
    ]
    for step_id, step_type, title, status, order in steps_data:
        existing_step = await db.execute(select(PermitStep).where(PermitStep.id == step_id))
        if not existing_step.scalar_one_or_none():
            due = today + timedelta(days=14) if status == "active" else None
            db.add(
                PermitStep(
                    id=step_id,
                    procedure_id=ID_PERMIT,
                    step_type=step_type,
                    title=title,
                    status=status,
                    step_order=order,
                    due_date=due,
                )
            )

    # --- AuthorityRequest (overdue) ---
    existing_ar = await db.execute(select(AuthorityRequest).where(AuthorityRequest.id == ID_AUTH_REQUEST))
    if not existing_ar.scalar_one_or_none():
        db.add(
            AuthorityRequest(
                id=ID_AUTH_REQUEST,
                procedure_id=ID_PERMIT,
                step_id=ID_STEP_COMPLEMENT,
                request_type="complement_request",
                from_authority=True,
                subject="Compléments requis — plan d'exécution désamiantage",
                body=(
                    "Veuillez fournir le plan d'exécution détaillé des travaux de désamiantage "
                    "ainsi que le rapport de conformité SUVA. Délai: 10 jours."
                ),
                response_due_date=today - timedelta(days=5),
                status="overdue",
            )
        )

    # --- Obligations ---
    existing_ob1 = await db.execute(select(Obligation).where(Obligation.id == ID_OBL_OVERDUE))
    if not existing_ob1.scalar_one_or_none():
        db.add(
            Obligation(
                id=ID_OBL_OVERDUE,
                building_id=bid,
                title="Soumission SUVA — notification travaux amiante",
                description="Notification obligatoire SUVA pour travaux de désamiantage catégorie majeure.",
                obligation_type="authority_submission",
                due_date=today - timedelta(days=10),
                status="overdue",
                priority="high",
                linked_entity_type="permit_procedure",
                linked_entity_id=ID_PERMIT,
            )
        )

    existing_ob2 = await db.execute(select(Obligation).where(Obligation.id == ID_OBL_DUE_SOON))
    if not existing_ob2.scalar_one_or_none():
        db.add(
            Obligation(
                id=ID_OBL_DUE_SOON,
                building_id=bid,
                title="Suivi diagnostic complémentaire PCB — prélèvements",
                description="Échéance pour planification des prélèvements complémentaires PCB.",
                obligation_type="diagnostic_followup",
                due_date=today + timedelta(days=12),
                status="due_soon",
                priority="medium",
            )
        )

    await db.commit()
    logger.info("seed_macro_slice: seeded ControlTower v2 demo data for building %s", bid)


async def main() -> None:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await seed_macro_slice(db)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
