"""BatiConnect -- Permit Intelligence Service.

Analyzes permit/procedure history from existing PermitProcedure and PermitStep
models. Detects buildings that may have undeclared renovations (no permit in
20+ years for pre-1990 construction) and generates actionable insights.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.permit_procedure import PermitProcedure

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
_NO_PERMIT_YEARS_THRESHOLD = 20
_PRE_1990_YEAR = 1990


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------


async def analyze_permit_history(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
    """Analyze permit/procedure data for a building.

    Returns:
        {
            permits: [{type, date, authority, status, description}],
            total_permits: N,
            last_permit: {type, date} | None,
            years_since_last_permit: N | None,
            building_without_permit_flag: bool,
            insights: [str]
        }
    """
    # Load building
    stmt_building = select(Building).where(Building.id == building_id)
    row = await db.execute(stmt_building)
    building = row.scalar_one_or_none()
    if building is None:
        raise ValueError(f"Building {building_id} not found")

    # Load all permit procedures for this building
    stmt = (
        select(PermitProcedure)
        .where(PermitProcedure.building_id == building_id)
        .order_by(PermitProcedure.submitted_at.desc().nulls_last(), PermitProcedure.created_at.desc())
    )
    result = await db.execute(stmt)
    procedures = list(result.scalars().all())

    # Build permit list
    permits: list[dict[str, Any]] = []
    for proc in procedures:
        permit_date = proc.approved_at or proc.submitted_at or proc.created_at
        permits.append(
            {
                "type": proc.procedure_type,
                "date": permit_date.isoformat() if permit_date else None,
                "authority": proc.authority_name or "",
                "status": proc.status,
                "description": proc.title or "",
            }
        )

    total = len(permits)

    # Determine last permit
    last_permit = None
    years_since_last: int | None = None
    if permits:
        # Find the most recent permit with a date
        for p in permits:
            if p["date"]:
                last_permit = {"type": p["type"], "date": p["date"]}
                # Parse date to compute years
                try:
                    permit_date_str = p["date"][:10]  # YYYY-MM-DD
                    permit_year = int(permit_date_str[:4])
                    years_since_last = date.today().year - permit_year
                except (ValueError, IndexError):
                    pass
                break

    # Building without permit flag
    construction_year = building.construction_year
    building_without_permit_flag = _check_no_permit_flag(
        construction_year=construction_year,
        total_permits=total,
        years_since_last=years_since_last,
    )

    # Generate insights
    insights = _generate_permit_insights(
        construction_year=construction_year,
        total_permits=total,
        last_permit=last_permit,
        years_since_last=years_since_last,
        building_without_permit_flag=building_without_permit_flag,
        permits=permits,
    )

    return {
        "permits": permits,
        "total_permits": total,
        "last_permit": last_permit,
        "years_since_last_permit": years_since_last,
        "building_without_permit_flag": building_without_permit_flag,
        "insights": insights,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_no_permit_flag(
    construction_year: int | None,
    total_permits: int,
    years_since_last: int | None,
) -> bool:
    """Flag buildings with no permit in 20+ years if pre-1990 construction."""
    if construction_year is None or construction_year >= _PRE_1990_YEAR:
        return False

    # No permits at all
    if total_permits == 0:
        return True

    # Has permits but last one is old
    return years_since_last is not None and years_since_last >= _NO_PERMIT_YEARS_THRESHOLD


def _generate_permit_insights(
    construction_year: int | None,
    total_permits: int,
    last_permit: dict[str, Any] | None,
    years_since_last: int | None,
    building_without_permit_flag: bool,
    permits: list[dict[str, Any]],
) -> list[str]:
    """Generate human-readable insights about permit history."""
    insights: list[str] = []

    if building_without_permit_flag:
        if total_permits == 0:
            insights.append(
                f"Aucun permis enregistre — probable que des travaux non declares aient eu lieu "
                f"(construction {construction_year})"
            )
        elif years_since_last and last_permit:
            year_str = last_permit["date"][:4] if last_permit.get("date") else "?"
            insights.append(f"Aucun permis depuis {year_str} — probable que des travaux non declares aient eu lieu")

    if total_permits == 0 and not building_without_permit_flag:
        insights.append("Aucun permis enregistre dans le systeme")

    if last_permit and years_since_last is not None:
        if years_since_last <= 5:
            insights.append(f"Permis recent ({last_permit['type']}) — activite de renovation recente")
        elif years_since_last <= 10:
            insights.append(f"Dernier permis il y a {years_since_last} ans ({last_permit['type']})")

    # Count rejected permits
    rejected = sum(1 for p in permits if p["status"] == "rejected")
    if rejected > 0:
        insights.append(f"{rejected} permis refuse(s) — verifier les raisons de refus")

    # Count pending permits
    pending = sum(1 for p in permits if p["status"] in ("draft", "submitted", "under_review"))
    if pending > 0:
        insights.append(f"{pending} permis en cours de traitement")

    return insights
