"""
BatiConnect — Value Notification Hooks

Hooks that fire on key events and record value deltas + create notifications
so users see cumulative value growth in their notification bell.

Each hook:
1. Records a DomainEvent via record_value_event
2. Creates a Notification (type=system) with a short French message
"""

from __future__ import annotations

import logging
import uuid as _uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.notification import Notification

logger = logging.getLogger(__name__)


async def _get_building_org_id(db: AsyncSession, building_id: UUID) -> UUID | None:
    """Resolve organization_id from a building."""
    result = await db.execute(select(Building.organization_id).where(Building.id == building_id))
    row = result.first()
    return row[0] if row else None


async def _get_org_user_ids(db: AsyncSession, org_id: UUID) -> list[UUID]:
    """Get all user IDs belonging to an organization."""
    from app.models.user import User

    result = await db.execute(select(User.id).where(User.organization_id == org_id))
    return [r[0] for r in result.all()]


async def _create_value_notification(
    db: AsyncSession,
    user_ids: list[UUID],
    title: str,
    body: str,
    building_id: UUID | None = None,
) -> None:
    """Create a system notification for each user in the list."""
    link = f"/buildings/{building_id}" if building_id else None
    for uid in user_ids:
        notification = Notification(
            id=_uuid.uuid4(),
            user_id=uid,
            type="system",
            title=title,
            body=body,
            link=link,
            status="unread",
            created_at=datetime.now(UTC),
        )
        db.add(notification)
    await db.flush()


async def on_enrichment_completed(
    db: AsyncSession,
    building_id: UUID,
) -> None:
    """Hook: enrichment completed — count new sources added, record value event."""
    from app.services.value_ledger_service import record_value_event

    org_id = await _get_building_org_id(db, building_id)
    if not org_id:
        return

    # Count enrichment sources for this building
    building = await db.get(Building, building_id)
    source_count = 0
    if building:
        if building.source_dataset:
            source_count += 1
        if building.source_metadata_json:
            source_count += 1

    delta = f"+{source_count} source(s) unifiée(s)" if source_count > 0 else "+1 enrichissement"

    await record_value_event(db, org_id, "enrichment_completed", building_id, delta)

    user_ids = await _get_org_user_ids(db, org_id)
    await _create_value_notification(
        db,
        user_ids,
        "Valeur ajoutee : enrichissement",
        f"Enrichissement termine pour un batiment — {delta}. Ces donnees sont desormais unifiees dans BatiConnect.",
        building_id,
    )

    logger.info("Value hook: enrichment completed for building %s — %s", building_id, delta)


async def on_contradiction_resolved(
    db: AsyncSession,
    building_id: UUID,
    issue_id: UUID,
) -> None:
    """Hook: contradiction resolved — record +1 contradiction resolved."""
    from app.services.value_ledger_service import record_value_event

    org_id = await _get_building_org_id(db, building_id)
    if not org_id:
        return

    delta = "+1 contradiction resolue"
    await record_value_event(db, org_id, "contradiction_resolved", building_id, delta)

    user_ids = await _get_org_user_ids(db, org_id)
    await _create_value_notification(
        db,
        user_ids,
        "Valeur ajoutee : contradiction resolue",
        "Une contradiction dans les donnees du batiment a ete detectee et resolue. "
        "Sans BatiConnect, cette incoherence serait restee invisible.",
        building_id,
    )

    logger.info("Value hook: contradiction resolved for building %s, issue %s", building_id, issue_id)


async def on_proof_chain_created(
    db: AsyncSession,
    building_id: UUID,
    evidence_link_id: UUID,
) -> None:
    """Hook: proof chain created — record +1 proof chain."""
    from app.services.value_ledger_service import record_value_event

    org_id = await _get_building_org_id(db, building_id)
    if not org_id:
        return

    delta = "+1 chaine de preuves creee"
    await record_value_event(db, org_id, "proof_chain_created", building_id, delta)

    user_ids = await _get_org_user_ids(db, org_id)
    await _create_value_notification(
        db,
        user_ids,
        "Valeur ajoutee : preuve chainee",
        "Un nouveau lien de preuve a ete etabli pour ce batiment. La tracabilite de vos decisions se renforce.",
        building_id,
    )

    logger.info("Value hook: proof chain created for building %s, link %s", building_id, evidence_link_id)


async def on_document_secured(
    db: AsyncSession,
    building_id: UUID,
    document_id: UUID,
) -> None:
    """Hook: document secured with hash — record +1 document secured."""
    from app.services.value_ledger_service import record_value_event

    org_id = await _get_building_org_id(db, building_id)
    if not org_id:
        return

    delta = "+1 document securise avec empreinte"
    await record_value_event(db, org_id, "document_secured", building_id, delta)

    user_ids = await _get_org_user_ids(db, org_id)
    await _create_value_notification(
        db,
        user_ids,
        "Valeur ajoutee : document securise",
        "Un document a ete archive avec son empreinte cryptographique. "
        "Son integrite est desormais garantie par BatiConnect.",
        building_id,
    )

    logger.info("Value hook: document secured for building %s, doc %s", building_id, document_id)


async def on_pack_generated(
    db: AsyncSession,
    building_id: UUID,
    pack_type: str,
) -> None:
    """Hook: audience pack generated — record value event."""
    from app.services.value_ledger_service import record_value_event

    org_id = await _get_building_org_id(db, building_id)
    if not org_id:
        return

    delta = f"pack {pack_type} genere"
    await record_value_event(db, org_id, "pack_generated", building_id, delta)

    pack_labels = {
        "authority": "autorite",
        "owner": "proprietaire",
        "contractor": "entreprise",
        "insurer": "assureur",
        "tenant": "locataire",
    }
    label = pack_labels.get(pack_type, pack_type)

    user_ids = await _get_org_user_ids(db, org_id)
    await _create_value_notification(
        db,
        user_ids,
        f"Valeur ajoutee : pack {label}",
        f"Un pack {label} a ete genere pour ce batiment. Chaque pack renforce votre dossier et votre credibilite.",
        building_id,
    )

    logger.info("Value hook: pack generated for building %s — type=%s", building_id, pack_type)
