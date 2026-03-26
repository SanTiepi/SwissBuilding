"""Portfolio triage service — read model for organization-level building urgency.

Classifies each building in an org portfolio by urgency level:
  critical (red), action_needed (orange), monitored (yellow), under_control (green).

Pure read — no new persistent entities.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.schemas.portfolio_triage import PortfolioTriageBuilding, PortfolioTriageResult

logger = logging.getLogger(__name__)


def _classify_building(
    passport_grade: str,
    blockers_count: int,
    trust: float,
) -> str:
    """Classify a building into a triage status based on passport + blockers + trust."""
    if blockers_count > 0 or passport_grade == "F":
        return "critical"
    if passport_grade in ("D", "E") or trust < 0.3:
        return "action_needed"
    if passport_grade == "C" or trust < 0.6:
        return "monitored"
    return "under_control"


_STATUS_ORDER = {"critical": 0, "action_needed": 1, "monitored": 2, "under_control": 3}


async def get_portfolio_triage(
    db: AsyncSession,
    org_id: UUID,
) -> PortfolioTriageResult:
    """Build a portfolio triage for all buildings in an organization.

    For each building: computes a lightweight instant card summary
    (passport grade + blockers count + trust) and classifies.
    """
    # Fetch org buildings
    result = await db.execute(select(Building).where(Building.organization_id == org_id))
    buildings = list(result.scalars().all())

    triage_buildings: list[PortfolioTriageBuilding] = []

    for building in buildings:
        passport_grade = "F"
        overall_trust = 0.0
        blockers_count = 0
        top_blocker: str | None = None
        next_action: str | None = None
        risk_score = 0.0

        # Get passport summary (lightweight)
        try:
            from app.services.passport_service import get_passport_summary

            passport = await get_passport_summary(db, building.id)
            if passport:
                passport_grade = passport.get("passport_grade", "F")
                overall_trust = passport.get("knowledge_state", {}).get("overall_trust", 0.0)
                blind_spots = passport.get("blind_spots", {})
                blockers_count = blind_spots.get("blocking", 0)

                # Risk score: inverse of completeness * trust
                completeness = passport.get("completeness", {}).get("overall_score", 0.0)
                risk_score = round(1.0 - (overall_trust * 0.5 + completeness * 0.5), 2)
        except Exception:
            logger.debug("Passport unavailable for building %s", building.id, exc_info=True)

        # Get top blocker from decision view
        try:
            from app.services.decision_view_service import get_building_decision_view

            dv = await get_building_decision_view(db, building.id)
            if dv and dv.blockers:
                blockers_count = max(blockers_count, len(dv.blockers))
                top_blocker = dv.blockers[0].title
        except Exception:
            logger.debug("Decision view unavailable for building %s", building.id, exc_info=True)

        # Get next action from readiness advisor
        try:
            from app.services.readiness_advisor_service import get_suggestions

            suggestions = await get_suggestions(db, building.id)
            if suggestions:
                next_action = suggestions[0].recommended_action or suggestions[0].title
        except Exception:
            logger.debug("Suggestions unavailable for building %s", building.id, exc_info=True)

        status = _classify_building(passport_grade, blockers_count, overall_trust)
        address = f"{building.address}, {building.postal_code} {building.city}"

        triage_buildings.append(
            PortfolioTriageBuilding(
                id=building.id,
                address=address,
                status=status,
                top_blocker=top_blocker,
                risk_score=risk_score,
                next_action=next_action,
                passport_grade=passport_grade,
            )
        )

    # Sort by urgency
    triage_buildings.sort(key=lambda b: (_STATUS_ORDER.get(b.status, 99), -b.risk_score))

    # Count by status
    counts = {"critical": 0, "action_needed": 0, "monitored": 0, "under_control": 0}
    for b in triage_buildings:
        if b.status in counts:
            counts[b.status] += 1

    return PortfolioTriageResult(
        org_id=org_id,
        critical_count=counts["critical"],
        action_needed_count=counts["action_needed"],
        monitored_count=counts["monitored"],
        under_control_count=counts["under_control"],
        buildings=triage_buildings,
    )
