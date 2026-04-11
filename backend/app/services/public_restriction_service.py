"""BatiConnect -- Public Law Restriction (RDPPF) aggregation service.

Aggregates all known restrictions de droit public for a building from:
1. Enrichment metadata (building_zones, heritage, contaminated_sites, water_protection, flood_zones)
2. Manually entered PublicLawRestriction records

Provides renovation feasibility assessment based on restriction severity.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.public_law_restriction import PublicLawRestriction

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid restriction types
# ---------------------------------------------------------------------------
VALID_RESTRICTION_TYPES = {
    "zone_affectation",
    "alignement",
    "distance",
    "servitude_publique",
    "protection_patrimoine",
    "zone_danger",
    "zone_protection_eaux",
    "site_contamine",
    "zone_bruit",
    "other",
}

VALID_IMPACT_LEVELS = {"none", "minor", "major", "blocking"}

# ---------------------------------------------------------------------------
# Enrichment -> restriction mapping rules
# ---------------------------------------------------------------------------


def _flood_impact(data: dict[str, Any]) -> str:
    """Derive renovation impact from flood danger level."""
    level = str(data.get("flood_danger_level", "")).lower()
    if level in ("considerable", "elevee", "hoch", "elevated", "high"):
        return "blocking"
    if level in ("moyenne", "mittel", "medium", "moderate"):
        return "major"
    if level in ("faible", "gering", "low", "residuelle"):
        return "minor"
    return "none"


_ENRICHMENT_MAPPING: list[dict[str, Any]] = [
    {
        "meta_key": "heritage",
        "condition": lambda d: d.get("isos_protected") is True,
        "restriction_type": "protection_patrimoine",
        "description_fn": lambda d: (
            f"ISOS protection — {d.get('site_name', 'site protege')} (cat. {d.get('isos_category', '?')})"
        ),
        "legal_reference": "LPN Art. 5 / ISOS",
        "authority": "federation",
        "impact": "major",
    },
    {
        "meta_key": "contaminated_sites",
        "condition": lambda d: d.get("is_contaminated") is True,
        "restriction_type": "site_contamine",
        "description_fn": lambda d: (
            f"Site contamine (Altlasten) — {d.get('site_type', 'type inconnu')}, investigation: {d.get('investigation_status', 'inconnu')}"
        ),
        "legal_reference": "OSites Art. 2",
        "authority": "canton",
        "impact": "major",
    },
    {
        "meta_key": "water_protection",
        "condition": lambda d: bool(d.get("protection_zone") or d.get("zone_type")),
        "restriction_type": "zone_protection_eaux",
        "description_fn": lambda d: (
            f"Zone de protection des eaux — {d.get('protection_zone', d.get('zone_type', 'zone inconnue'))}"
        ),
        "legal_reference": "LEaux Art. 19",
        "authority": "canton",
        "impact": "minor",
    },
    {
        "meta_key": "flood_zones",
        "condition": lambda d: bool(d.get("flood_danger_level")),
        "restriction_type": "zone_danger",
        "description_fn": lambda d: f"Zone de danger inondation — niveau {d.get('flood_danger_level', 'inconnu')}",
        "legal_reference": "LEaux Art. 21",
        "authority": "canton",
        "impact": _flood_impact,
    },
    {
        "meta_key": "building_zones",
        "condition": lambda d: bool(d.get("zone_type") or d.get("zone_code")),
        "restriction_type": "zone_affectation",
        "description_fn": lambda d: (
            f"Zone d'affectation — {d.get('zone_description', d.get('zone_type', 'type inconnu'))}"
        ),
        "legal_reference": "LAT Art. 15",
        "authority": "commune",
        "impact": "none",
    },
]


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


async def aggregate_restrictions(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
    """Compile all known restrictions for a building.

    Returns:
        {
            restrictions: [{type, description, legal_ref, authority, impact, source}],
            total_count: N,
            blocking_count: N,
            major_count: N,
            renovation_feasibility: "unrestricted|constrained|heavily_constrained|blocked",
            summary: str
        }
    """
    # 1. Load building
    stmt = select(Building).where(Building.id == building_id)
    row = await db.execute(stmt)
    building = row.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    restrictions: list[dict[str, Any]] = []

    # 2. Restrictions from enrichment_meta
    meta: dict[str, Any] = building.source_metadata_json or {}
    for mapping in _ENRICHMENT_MAPPING:
        data = meta.get(mapping["meta_key"])
        if data and mapping["condition"](data):
            impact = mapping["impact"]
            if callable(impact):
                impact = impact(data)
            restrictions.append(
                {
                    "type": mapping["restriction_type"],
                    "description": mapping["description_fn"](data),
                    "legal_ref": mapping["legal_reference"],
                    "authority": mapping["authority"],
                    "impact": impact,
                    "source": "enrichment",
                }
            )

    # 3. Restrictions from PublicLawRestriction records
    stmt_plr = (
        select(PublicLawRestriction)
        .where(
            PublicLawRestriction.building_id == building_id,
            PublicLawRestriction.active.is_(True),
        )
        .order_by(PublicLawRestriction.created_at)
    )
    result = await db.execute(stmt_plr)
    for plr in result.scalars().all():
        restrictions.append(
            {
                "type": plr.restriction_type,
                "description": plr.description or "",
                "legal_ref": plr.legal_reference or "",
                "authority": plr.authority or "",
                "impact": plr.impact_on_renovation,
                "source": plr.source,
            }
        )

    # 4. Compute summary stats
    blocking = sum(1 for r in restrictions if r["impact"] == "blocking")
    major = sum(1 for r in restrictions if r["impact"] == "major")
    total = len(restrictions)

    feasibility = _compute_feasibility(blocking, major)
    summary = _build_summary(restrictions, blocking, major)

    return {
        "restrictions": restrictions,
        "total_count": total,
        "blocking_count": blocking,
        "major_count": major,
        "renovation_feasibility": feasibility,
        "summary": summary,
    }


def _compute_feasibility(blocking: int, major: int) -> str:
    """Derive renovation feasibility from restriction severity counts."""
    if blocking > 0:
        return "blocked"
    if major >= 2:
        return "heavily_constrained"
    if major == 1:
        return "constrained"
    return "unrestricted"


def _build_summary(restrictions: list[dict[str, Any]], blocking: int, major: int) -> str:
    """Build a human-readable summary of the restrictions."""
    if not restrictions:
        return "Aucune restriction de droit public connue"

    parts: list[str] = []
    if blocking > 0:
        labels = [r["description"] for r in restrictions if r["impact"] == "blocking"]
        parts.append(f"{blocking} restriction(s) bloquante(s): {', '.join(labels[:3])}")
    if major > 0:
        labels = [r["description"] for r in restrictions if r["impact"] == "major"]
        parts.append(f"{major} restriction(s) majeure(s): {', '.join(labels[:3])}")

    minor_count = sum(1 for r in restrictions if r["impact"] in ("minor", "none"))
    if minor_count > 0 and not parts:
        parts.append(f"{minor_count} restriction(s) mineure(s)")
    elif minor_count > 0:
        parts.append(f"{minor_count} autre(s)")

    return " — ".join(parts)


# ---------------------------------------------------------------------------
# Auto-create restrictions from enrichment
# ---------------------------------------------------------------------------


async def auto_create_restrictions_from_enrichment(
    db: AsyncSession,
    building_id: UUID,
) -> list[PublicLawRestriction]:
    """Read enrichment_meta and auto-create PublicLawRestriction records.

    Mapping:
    - heritage/ISOS -> protection_patrimoine
    - contaminated_sites -> site_contamine
    - water_protection -> zone_protection_eaux
    - flood_zones -> zone_danger
    - building_zones -> zone_affectation

    Idempotent: does not duplicate existing records with same building_id + restriction_type + source='enrichment'.
    """
    # Load building
    stmt = select(Building).where(Building.id == building_id)
    row = await db.execute(stmt)
    building = row.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    meta: dict[str, Any] = building.source_metadata_json or {}

    # Load existing enrichment-sourced restrictions for idempotency
    stmt_existing = select(PublicLawRestriction).where(
        PublicLawRestriction.building_id == building_id,
        PublicLawRestriction.source == "enrichment",
    )
    result = await db.execute(stmt_existing)
    existing_types = {plr.restriction_type for plr in result.scalars().all()}

    created: list[PublicLawRestriction] = []

    for mapping in _ENRICHMENT_MAPPING:
        data = meta.get(mapping["meta_key"])
        if not data or not mapping["condition"](data):
            continue

        rtype = mapping["restriction_type"]
        if rtype in existing_types:
            continue  # idempotent skip

        impact = mapping["impact"]
        if callable(impact):
            impact = impact(data)

        plr = PublicLawRestriction(
            building_id=building_id,
            restriction_type=rtype,
            description=mapping["description_fn"](data),
            legal_reference=mapping["legal_reference"],
            authority=mapping["authority"],
            impact_on_renovation=impact,
            source="enrichment",
            active=True,
        )
        db.add(plr)
        created.append(plr)

    if created:
        await db.flush()

    return created
