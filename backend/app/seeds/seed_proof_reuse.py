"""
Proof-reuse seed — demonstrates same diagnostic publication reused across audiences.

Creates on an existing Lausanne building:
- 1 DiagnosticReportPublication (auto_matched, asbestos_full, with structured_summary)
- 1 PermitProcedure (submitted, 4 steps, step 2 active = "review")
- 1 AuthorityRequest (complement_request, open, due in 7 days)
- 2 ProofDeliveries: 1 to authority (viewed), 1 to insurer (acknowledged)
- 2 Obligations: 1 due_soon (authority_submission), 1 upcoming (insurance_renewal)

Idempotent via UUID5.

Usage:
    python -m app.seeds.seed_proof_reuse
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.authority_request import AuthorityRequest
from app.models.building import Building
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.obligation import Obligation
from app.models.permit_procedure import PermitProcedure
from app.models.permit_step import PermitStep
from app.models.proof_delivery import ProofDelivery

logger = logging.getLogger(__name__)

# Stable namespace
_NS = uuid.UUID("pr00f-reu5-seed-0001-000000000000")


def _id(label: str) -> uuid.UUID:
    return uuid.uuid5(_NS, label)


# Pre-computed IDs
ID_PUBLICATION = _id("proof-reuse-publication")
ID_PERMIT = _id("proof-reuse-permit")
ID_STEP_SUBMISSION = _id("proof-reuse-step-submission")
ID_STEP_REVIEW = _id("proof-reuse-step-review")
ID_STEP_COMPLEMENT = _id("proof-reuse-step-complement")
ID_STEP_DECISION = _id("proof-reuse-step-decision")
ID_AUTH_REQUEST = _id("proof-reuse-auth-request")
ID_DELIVERY_AUTHORITY = _id("proof-reuse-delivery-authority")
ID_DELIVERY_INSURER = _id("proof-reuse-delivery-insurer")
ID_OBL_AUTHORITY = _id("proof-reuse-obligation-authority")
ID_OBL_INSURANCE = _id("proof-reuse-obligation-insurance")


async def _upsert(db: AsyncSession, model_class: type, obj_id: uuid.UUID, **kwargs) -> None:
    """Insert if not exists (idempotent)."""
    existing = await db.execute(select(model_class).where(model_class.id == obj_id))
    if existing.scalar_one_or_none() is None:
        db.add(model_class(id=obj_id, **kwargs))


async def seed_proof_reuse(db: AsyncSession) -> None:
    """Seed proof-reuse demo data onto the first Lausanne building."""
    result = await db.execute(select(Building).where(Building.city == "Lausanne").limit(1))
    building = result.scalar_one_or_none()
    if not building:
        logger.warning("seed_proof_reuse: no Lausanne building found — skipping")
        return

    bid = building.id
    today = date.today()
    now = datetime.now(UTC)

    # ─── 1. DiagnosticReportPublication ────────────────────────
    await _upsert(
        db,
        DiagnosticReportPublication,
        ID_PUBLICATION,
        building_id=bid,
        source_system="batiscan",
        source_mission_id="MISSION-2026-ASB-001",
        current_version=1,
        match_state="auto_matched",
        match_key=str(building.egid) if building.egid else "LAUSANNE-BUILDING-1",
        match_key_type="egid",
        report_pdf_url="/reports/amiante-full-2026-001.pdf",
        structured_summary={
            "pollutant": "asbestos",
            "zones_inspected": 12,
            "positive_samples": 3,
            "risk_level": "high",
            "recommendations": ["Desamiantage parties communes", "Confinement local technique"],
        },
        payload_hash=hashlib.sha256(b"proof-reuse-publication-v1").hexdigest(),
        mission_type="asbestos_full",
        published_at=now - timedelta(days=45),
        is_immutable=True,
    )

    # ─── 2. PermitProcedure (submitted, 4 steps) ──────────────
    await _upsert(
        db,
        PermitProcedure,
        ID_PERMIT,
        building_id=bid,
        procedure_type="construction_permit",
        title="Permis de construire — travaux de desamiantage",
        description="Autorisation pour travaux de desamiantage suite au rapport de diagnostic amiante.",
        authority_name="Service de l'urbanisme, Ville de Lausanne",
        authority_type="communal",
        status="submitted",
        submitted_at=now - timedelta(days=10),
        reference_number="PC-2026-00198",
    )
    await db.flush()

    # ─── 3. PermitSteps ───────────────────────────────────────
    steps = [
        (ID_STEP_SUBMISSION, "submission", "Depot du dossier", "completed", 1, None),
        (ID_STEP_REVIEW, "review", "Examen preliminaire", "active", 2, today + timedelta(days=14)),
        (ID_STEP_COMPLEMENT, "complement_request", "Demande de complements", "pending", 3, None),
        (ID_STEP_DECISION, "decision", "Decision finale", "pending", 4, None),
    ]
    for step_id, step_type, title, status, order, due in steps:
        await _upsert(
            db,
            PermitStep,
            step_id,
            procedure_id=ID_PERMIT,
            step_type=step_type,
            title=title,
            status=status,
            step_order=order,
            due_date=due,
            required_documents=(
                [
                    {"label": "Rapport diagnostic amiante", "required": True},
                    {"label": "Plan d'execution", "required": True},
                    {"label": "Formulaire SUVA", "required": True},
                ]
                if step_type == "review"
                else None
            ),
        )

    # ─── 4. AuthorityRequest (open, 7 days) ───────────────────
    await _upsert(
        db,
        AuthorityRequest,
        ID_AUTH_REQUEST,
        procedure_id=ID_PERMIT,
        step_id=ID_STEP_REVIEW,
        request_type="complement_request",
        from_authority=True,
        subject="Complements requis — rapport de diagnostic",
        body=(
            "Merci de fournir le rapport de diagnostic amiante complet "
            "ainsi que le plan d'execution des travaux. Delai: 7 jours."
        ),
        response_due_date=today + timedelta(days=7),
        status="open",
    )

    # ─── 5. ProofDeliveries — same publication, two audiences ─
    content_hash = hashlib.sha256(b"proof-reuse-publication-v1-delivery").hexdigest()

    await _upsert(
        db,
        ProofDelivery,
        ID_DELIVERY_AUTHORITY,
        building_id=bid,
        target_type="diagnostic_publication",
        target_id=ID_PUBLICATION,
        audience="authority",
        delivery_method="email",
        status="viewed",
        sent_at=now - timedelta(days=8),
        delivered_at=now - timedelta(days=8),
        viewed_at=now - timedelta(days=5),
        content_hash=content_hash,
        content_version=1,
    )

    await _upsert(
        db,
        ProofDelivery,
        ID_DELIVERY_INSURER,
        building_id=bid,
        target_type="diagnostic_publication",
        target_id=ID_PUBLICATION,
        audience="insurer",
        delivery_method="api",
        status="acknowledged",
        sent_at=now - timedelta(days=7),
        delivered_at=now - timedelta(days=7),
        viewed_at=now - timedelta(days=4),
        acknowledged_at=now - timedelta(days=2),
        content_hash=content_hash,
        content_version=1,
    )

    # ─── 6. Obligations ───────────────────────────────────────
    await _upsert(
        db,
        Obligation,
        ID_OBL_AUTHORITY,
        building_id=bid,
        title="Soumission dossier autorite — complement diagnostic",
        description="Repondre a la demande de complements de l'autorite avec le rapport de diagnostic amiante.",
        obligation_type="authority_submission",
        due_date=today + timedelta(days=7),
        status="due_soon",
        priority="high",
        linked_entity_type="permit_procedure",
        linked_entity_id=ID_PERMIT,
    )

    await _upsert(
        db,
        Obligation,
        ID_OBL_INSURANCE,
        building_id=bid,
        title="Renouvellement assurance RC batiment",
        description="Transmission du rapport amiante a l'assureur pour renouvellement police RC.",
        obligation_type="insurance_renewal",
        due_date=today + timedelta(days=45),
        status="upcoming",
        priority="medium",
        linked_entity_type="diagnostic_publication",
        linked_entity_id=ID_PUBLICATION,
    )

    await db.commit()
    logger.info("seed_proof_reuse: seeded proof-reuse demo data for building %s", bid)


async def main() -> None:
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await seed_proof_reuse(db)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
