"""
SwissBuildingOS - Rule Resolution Service

Resolves regulatory rules from RegulatoryPack data, walking the jurisdiction
hierarchy (commune → canton → country → supranational) for fallback.

When no pack data is found, returns None so callers can fall back to hardcoded
defaults during the transition period.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jurisdiction import Jurisdiction
from app.models.regulatory_pack import RegulatoryPack


async def _walk_jurisdiction_chain(
    db: AsyncSession,
    jurisdiction_id: UUID,
) -> list[UUID]:
    """Return jurisdiction IDs from most specific to most general (self → parent → …)."""
    chain: list[UUID] = []
    current_id: UUID | None = jurisdiction_id

    # Safety limit to avoid infinite loops on bad data
    for _ in range(10):
        if current_id is None:
            break
        chain.append(current_id)
        result = await db.execute(select(Jurisdiction.parent_id).where(Jurisdiction.id == current_id))
        row = result.scalar_one_or_none()
        current_id = row  # None if no parent

    return chain


async def _find_active_pack(
    db: AsyncSession,
    jurisdiction_ids: list[UUID],
    pollutant_type: str,
) -> RegulatoryPack | None:
    """Find the most specific active pack for a pollutant, walking the hierarchy."""
    for jid in jurisdiction_ids:
        result = await db.execute(
            select(RegulatoryPack).where(
                RegulatoryPack.jurisdiction_id == jid,
                RegulatoryPack.pollutant_type == pollutant_type.lower(),
                RegulatoryPack.is_active.is_(True),
            )
        )
        pack = result.scalars().first()
        if pack is not None:
            return pack
    return None


async def _find_all_packs_for_pollutant(
    db: AsyncSession,
    jurisdiction_ids: list[UUID],
    pollutant_type: str,
) -> list[RegulatoryPack]:
    """Find all active packs for a pollutant across the hierarchy (most specific first)."""
    packs: list[RegulatoryPack] = []
    for jid in jurisdiction_ids:
        result = await db.execute(
            select(RegulatoryPack).where(
                RegulatoryPack.jurisdiction_id == jid,
                RegulatoryPack.pollutant_type == pollutant_type.lower(),
                RegulatoryPack.is_active.is_(True),
            )
        )
        packs.extend(result.scalars().all())
    return packs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def resolve_threshold(
    db: AsyncSession,
    jurisdiction_id: UUID | None,
    pollutant_type: str,
    unit: str,
) -> dict | None:
    """
    Resolve threshold for a pollutant + unit from the most specific jurisdiction pack.

    Returns dict with keys: threshold, unit, legal_ref, action — or None if no pack found.
    """
    if jurisdiction_id is None:
        return None

    chain = await _walk_jurisdiction_chain(db, jurisdiction_id)
    pack = await _find_active_pack(db, chain, pollutant_type)

    if pack is None or pack.threshold_value is None:
        return None

    # Check unit compatibility (pack unit must match requested unit)
    if pack.threshold_unit and pack.threshold_unit != unit:
        return None

    return {
        "threshold": pack.threshold_value,
        "unit": pack.threshold_unit or unit,
        "legal_ref": pack.legal_reference,
        "action": pack.threshold_action or "remediate",
        "jurisdiction_id": str(pack.jurisdiction_id),
        "pack_version": pack.version,
    }


async def resolve_cantonal_requirements(
    db: AsyncSession,
    jurisdiction_id: UUID | None,
) -> dict | None:
    """
    Resolve cantonal requirements (authority, notification, forms) from jurisdiction metadata
    and its regulatory packs.

    Returns dict with keys: authority_name, notification_delay_days, form_name,
    diagnostic_required_before_year, requires_waste_elimination_plan — or None.
    """
    if jurisdiction_id is None:
        return None

    # Get jurisdiction metadata
    result = await db.execute(select(Jurisdiction).where(Jurisdiction.id == jurisdiction_id))
    jurisdiction = result.scalar_one_or_none()
    if jurisdiction is None:
        return None

    meta = jurisdiction.metadata_json or {}

    # Find notification pack (prefer asbestos since it drives most notification rules)
    chain = await _walk_jurisdiction_chain(db, jurisdiction_id)
    pack = await _find_active_pack(db, chain, "asbestos")

    requirements: dict = {
        "authority_name": meta.get("authority_name"),
        "canton": jurisdiction.code.split("-")[-1].upper() if "-" in jurisdiction.code else jurisdiction.code.upper(),
    }

    if pack:
        requirements["notification_delay_days"] = pack.notification_delay_days
        requirements["notification_authority"] = pack.notification_authority
        requirements["notification_required"] = pack.notification_required

    # Merge jurisdiction metadata for canton-specific fields
    if meta.get("diagnostic_required_before_year"):
        requirements["diagnostic_required_before_year"] = meta["diagnostic_required_before_year"]
    if meta.get("requires_waste_elimination_plan") is not None:
        requirements["requires_waste_elimination_plan"] = meta["requires_waste_elimination_plan"]
    if meta.get("form_name"):
        requirements["form_name"] = meta["form_name"]
    if meta.get("online_system"):
        requirements["online_system"] = meta["online_system"]

    return requirements


async def resolve_risk_calibration(
    db: AsyncSession,
    jurisdiction_id: UUID | None,
    pollutant_type: str,
) -> dict | None:
    """
    Resolve risk calibration data (year bands, base probability) from regulatory packs.

    Returns dict with keys: risk_year_start, risk_year_end, base_probability,
    pack_version — or None if no pack found.
    """
    if jurisdiction_id is None:
        return None

    chain = await _walk_jurisdiction_chain(db, jurisdiction_id)
    pack = await _find_active_pack(db, chain, pollutant_type)

    if pack is None or pack.base_probability is None:
        return None

    return {
        "risk_year_start": pack.risk_year_start,
        "risk_year_end": pack.risk_year_end,
        "base_probability": pack.base_probability,
        "pack_version": pack.version,
        "jurisdiction_id": str(pack.jurisdiction_id),
    }


async def resolve_work_categories(
    db: AsyncSession,
    jurisdiction_id: UUID | None,
    pollutant_type: str,
) -> dict | None:
    """
    Resolve CFST-like work categories from regulatory pack.

    Returns the work_categories_json dict or None.
    """
    if jurisdiction_id is None:
        return None

    chain = await _walk_jurisdiction_chain(db, jurisdiction_id)
    pack = await _find_active_pack(db, chain, pollutant_type)

    if pack is None or pack.work_categories_json is None:
        return None

    return pack.work_categories_json


async def resolve_waste_classification(
    db: AsyncSession,
    jurisdiction_id: UUID | None,
    pollutant_type: str,
) -> dict | None:
    """
    Resolve OLED-like waste classification from regulatory pack.

    Returns the waste_classification_json dict or None.
    """
    if jurisdiction_id is None:
        return None

    chain = await _walk_jurisdiction_chain(db, jurisdiction_id)
    pack = await _find_active_pack(db, chain, pollutant_type)

    if pack is None or pack.waste_classification_json is None:
        return None

    return pack.waste_classification_json


async def resolve_notification_rules(
    db: AsyncSession,
    jurisdiction_id: UUID | None,
    pollutant_type: str,
) -> dict | None:
    """
    Resolve notification rules for a specific pollutant from regulatory packs.

    Returns dict with notification_required, notification_authority,
    notification_delay_days — or None.
    """
    if jurisdiction_id is None:
        return None

    chain = await _walk_jurisdiction_chain(db, jurisdiction_id)
    pack = await _find_active_pack(db, chain, pollutant_type)

    if pack is None:
        return None

    return {
        "notification_required": pack.notification_required or False,
        "notification_authority": pack.notification_authority,
        "notification_delay_days": pack.notification_delay_days,
        "legal_reference": pack.legal_reference,
    }
