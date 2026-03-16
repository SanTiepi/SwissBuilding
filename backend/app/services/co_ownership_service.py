"""Co-ownership governance service for PPE buildings.

Manages co-owner simulation, cost allocation, and decision tracking
for multi-owner buildings (propriété par étages).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.schemas.co_ownership import (
    BuildingCoOwnershipInfo,
    BuildingDecisionLog,
    CoOwner,
    CostAllocation,
    DecisionItem,
    PortfolioCoOwnershipSummary,
    RemediationCostSplit,
)
from app.services.building_data_loader import load_org_buildings

# Roles assigned round-robin to simulated co-owners
_CO_OWNER_ROLES = [
    "president",
    "property_manager",
    "member",
    "tenant_representative",
    "member",
    "member",
    "member",
    "member",
]

# Swiss first/last name pools for deterministic simulation
_FIRST_NAMES = ["Marie", "Pierre", "Jean", "Sophie", "Marc", "Anna", "Luca", "Elena"]
_LAST_NAMES = ["Müller", "Schmid", "Meier", "Keller", "Weber", "Huber", "Schneider", "Fischer"]

# Unit cost per exceeded sample (CHF) for remediation estimation
_UNIT_COST_PER_EXCEEDED_SAMPLE = 15_000.0


def _ownership_type_for_building(building: Building) -> str:
    """Derive ownership type from building_type."""
    if building.building_type in ("residential_multi", "mixed_use"):
        return "ppe"
    if building.building_type == "commercial":
        return "cooperative"
    return "sole_owner"


def _generate_co_owners(building: Building) -> list[CoOwner]:
    """Generate deterministic simulated co-owners from address hash."""
    seed = int(hashlib.md5(building.address.encode()).hexdigest(), 16)
    count = (seed % 7) + 2  # 2-8 owners

    # Build share percentages that sum to 100
    raw = [(seed >> (i * 4)) % 10 + 1 for i in range(count)]
    total_raw = sum(raw)
    shares = [round(r / total_raw * 100, 2) for r in raw]
    # Fix rounding drift on last entry
    shares[-1] = round(100.0 - sum(shares[:-1]), 2)

    owners: list[CoOwner] = []
    for i in range(count):
        idx = (seed + i) % len(_FIRST_NAMES)
        first = _FIRST_NAMES[idx]
        last = _LAST_NAMES[idx]
        role = _CO_OWNER_ROLES[i % len(_CO_OWNER_ROLES)]
        owners.append(
            CoOwner(
                owner_id=f"co-{i + 1}",
                name=f"{first} {last}",
                share_percentage=shares[i],
                contact_email=f"{first.lower()}.{last.lower()}@example.ch",
                role=role,
                voting_rights=role != "tenant_representative",
            )
        )
    return owners


async def get_building_co_ownership_info(
    building_id: UUID,
    db: AsyncSession,
) -> BuildingCoOwnershipInfo:
    """Return co-ownership structure for a building."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Building not found")

    ownership_type = _ownership_type_for_building(building)

    if ownership_type in ("ppe", "cooperative"):
        co_owners = _generate_co_owners(building)
    else:
        co_owners = [
            CoOwner(
                owner_id="sole-1",
                name="Propriétaire unique",
                share_percentage=100.0,
                contact_email=None,
                role="president",
                voting_rights=True,
            )
        ]

    return BuildingCoOwnershipInfo(
        building_id=building.id,
        ownership_type=ownership_type,
        co_owners=co_owners,
        total_shares=100.0,
        decision_quorum_pct=50.0,
        generated_at=datetime.now(UTC),
    )


async def calculate_remediation_cost_split(
    building_id: UUID,
    db: AsyncSession,
    method: str = "by_share",
) -> RemediationCostSplit:
    """Calculate remediation cost split across co-owners."""
    co_info = await get_building_co_ownership_info(building_id, db)

    # Estimate total remediation cost from exceeded samples
    stmt = (
        select(Sample)
        .join(Diagnostic, Sample.diagnostic_id == Diagnostic.id)
        .where(Diagnostic.building_id == building_id, Sample.threshold_exceeded.is_(True))
    )
    result = await db.execute(stmt)
    exceeded_samples = result.scalars().all()
    total_cost = len(exceeded_samples) * _UNIT_COST_PER_EXCEEDED_SAMPLE

    allocations: list[CostAllocation] = []
    owner_count = len(co_info.co_owners)

    for owner in co_info.co_owners:
        if method == "equal" and owner_count > 0:
            amount = round(total_cost / owner_count, 2)
        else:
            # by_share and by_affected_area both use share percentage
            amount = round(total_cost * owner.share_percentage / 100.0, 2)

        allocations.append(
            CostAllocation(
                owner_id=owner.owner_id,
                owner_name=owner.name,
                share_percentage=owner.share_percentage,
                allocated_amount=amount,
                status="pending",
            )
        )

    return RemediationCostSplit(
        building_id=building_id,
        total_remediation_cost=total_cost,
        allocations=allocations,
        allocation_method=method,
        generated_at=datetime.now(UTC),
    )


async def get_building_decision_log(
    building_id: UUID,
    db: AsyncSession,
) -> BuildingDecisionLog:
    """Generate decision log from action items."""
    # Verify building exists
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Building not found")

    result = await db.execute(select(ActionItem).where(ActionItem.building_id == building_id))
    actions = result.scalars().all()

    decisions: list[DecisionItem] = []
    approved_count = 0
    rejected_count = 0
    pending_count = 0

    for action in actions:
        status_map = {
            "open": "proposed",
            "in_progress": "voted",
            "completed": "approved",
            "cancelled": "rejected",
        }
        decision_status = status_map.get(action.status, "deferred")

        if decision_status == "proposed":
            votes_for, votes_against, votes_abstain = 0, 0, 0
            quorum = False
            pending_count += 1
        elif decision_status == "voted":
            votes_for, votes_against, votes_abstain = 4, 1, 1
            quorum = True
        elif decision_status == "approved":
            votes_for, votes_against, votes_abstain = 5, 1, 0
            quorum = True
            approved_count += 1
        else:  # rejected / deferred
            votes_for, votes_against, votes_abstain = 1, 4, 1
            quorum = True
            rejected_count += 1

        decided_date = None
        if decision_status in ("approved", "rejected"):
            decided_date = action.completed_at.date() if action.completed_at else datetime.now(UTC).date()

        decisions.append(
            DecisionItem(
                decision_id=f"dec-{action.id}",
                title=action.title,
                description=action.description or "",
                decision_type="remediation_approval",
                status=decision_status,
                votes_for=votes_for,
                votes_against=votes_against,
                votes_abstain=votes_abstain,
                quorum_reached=quorum,
                decided_date=decided_date,
            )
        )

    total_resolved = approved_count + rejected_count
    approval_rate = (approved_count / total_resolved) if total_resolved > 0 else 0.0

    return BuildingDecisionLog(
        building_id=building_id,
        decisions=decisions,
        total_decisions=len(decisions),
        pending_decisions=pending_count,
        approval_rate=round(approval_rate, 2),
        generated_at=datetime.now(UTC),
    )


async def get_portfolio_co_ownership_summary(
    org_id: UUID,
    db: AsyncSession,
) -> PortfolioCoOwnershipSummary:
    """Portfolio-level co-ownership summary for an organization."""
    buildings = await load_org_buildings(db, org_id)

    ppe_count = 0
    sole_count = 0
    pending_decisions = 0
    approval_rates: list[float] = []
    total_pending_costs = 0.0

    for bldg in buildings:
        otype = _ownership_type_for_building(bldg)
        if otype == "ppe":
            ppe_count += 1
        elif otype == "sole_owner":
            sole_count += 1
        else:
            ppe_count += 1  # cooperative counted with ppe

        decision_log = await get_building_decision_log(bldg.id, db)
        if decision_log.pending_decisions > 0:
            pending_decisions += 1
        if decision_log.total_decisions > 0:
            approval_rates.append(decision_log.approval_rate)

        cost_split = await calculate_remediation_cost_split(bldg.id, db)
        total_pending_costs += sum(a.allocated_amount for a in cost_split.allocations if a.status == "pending")

    avg_rate = (sum(approval_rates) / len(approval_rates)) if approval_rates else 0.0

    return PortfolioCoOwnershipSummary(
        organization_id=org_id,
        total_ppe_buildings=ppe_count,
        total_sole_owner_buildings=sole_count,
        buildings_with_pending_decisions=pending_decisions,
        average_decision_approval_rate=round(avg_rate, 2),
        total_pending_cost_allocations=round(total_pending_costs, 2),
        generated_at=datetime.now(UTC),
    )
