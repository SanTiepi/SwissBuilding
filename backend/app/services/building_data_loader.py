"""Shared building data loading utilities.

Centralises the org-scoped building query pattern that was duplicated across
building_clustering_service, building_age_analysis_service, building_lifecycle_service,
building_valuation_service and others.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.user import User
from app.models.zone import Zone


async def load_org_buildings(db: AsyncSession, org_id: UUID) -> list[Building]:
    """Fetch all buildings belonging to users in the given organization."""
    user_stmt = select(User.id).where(User.organization_id == org_id)
    user_result = await db.execute(user_stmt)
    user_ids = [row[0] for row in user_result.all()]
    if not user_ids:
        return []

    stmt = select(Building).where(Building.created_by.in_(user_ids))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def load_building_with_context(
    db: AsyncSession,
    building_id: UUID,
    include_diagnostics: bool = False,
    include_samples: bool = False,
    include_documents: bool = False,
    include_zones: bool = False,
    include_interventions: bool = False,
    include_actions: bool = False,
) -> dict | None:
    """Load a building with optional related data in a single batch.

    Returns dict with keys: building, diagnostics, samples, documents, zones,
    interventions, actions.  Only included keys are populated.
    Returns ``None`` when the building does not exist.
    """
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if building is None:
        return None

    out: dict = {"building": building}

    if include_diagnostics:
        diag_result = await db.execute(select(Diagnostic).where(Diagnostic.building_id == building_id))
        out["diagnostics"] = list(diag_result.scalars().all())

    if include_samples:
        sample_result = await db.execute(
            select(Sample)
            .join(Diagnostic, Diagnostic.id == Sample.diagnostic_id)
            .where(Diagnostic.building_id == building_id)
        )
        out["samples"] = list(sample_result.scalars().all())

    if include_documents:
        doc_result = await db.execute(select(Document).where(Document.building_id == building_id))
        out["documents"] = list(doc_result.scalars().all())

    if include_zones:
        zone_result = await db.execute(select(Zone).where(Zone.building_id == building_id))
        out["zones"] = list(zone_result.scalars().all())

    if include_interventions:
        intv_result = await db.execute(select(Intervention).where(Intervention.building_id == building_id))
        out["interventions"] = list(intv_result.scalars().all())

    if include_actions:
        action_result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
        out["actions"] = list(action_result.scalars().all())

    return out
