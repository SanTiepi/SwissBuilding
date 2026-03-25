"""BatiConnect — Seed data for expansion signals and customer success milestones."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_success import CustomerSuccessMilestone
from app.models.expansion_signal import (
    AccountExpansionTrigger,
    DistributionLoopSignal,
    ExpansionOpportunity,
)
from app.models.organization import Organization


async def seed_expansion_data(db: AsyncSession) -> dict:
    """Seed expansion triggers, distribution signals, opportunities, and milestones.

    Returns summary of created records.
    """
    # Get first org for seeding
    org_result = await db.execute(select(Organization).limit(1))
    org = org_result.scalar_one_or_none()
    if not org:
        return {"status": "skipped", "reason": "no organizations found"}

    from app.models.building import Building

    building_result = await db.execute(select(Building).limit(1))
    building = building_result.scalar_one_or_none()
    if not building:
        return {"status": "skipped", "reason": "no buildings found"}

    now = datetime.now(UTC)

    # --- 3 Expansion Triggers ---
    triggers = [
        AccountExpansionTrigger(
            id=uuid.uuid4(),
            organization_id=org.id,
            trigger_type="second_actor_active",
            evidence_summary="Second user from org logged in and performed workspace actions",
            detected_at=now - timedelta(days=5),
        ),
        AccountExpansionTrigger(
            id=uuid.uuid4(),
            organization_id=org.id,
            trigger_type="pack_consulted",
            source_entity_type="evidence_pack",
            source_entity_id=uuid.uuid4(),
            evidence_summary="Authority pack consulted 3 times in the last week",
            detected_at=now - timedelta(days=2),
        ),
        AccountExpansionTrigger(
            id=uuid.uuid4(),
            organization_id=org.id,
            trigger_type="proof_reused",
            source_entity_type="proof_delivery",
            source_entity_id=uuid.uuid4(),
            evidence_summary="Diagnostic proof reused for insurer after initial authority delivery",
            detected_at=now - timedelta(days=1),
        ),
    ]
    for t in triggers:
        db.add(t)

    # --- 2 Distribution Loop Signals ---
    signals = [
        DistributionLoopSignal(
            id=uuid.uuid4(),
            building_id=building.id,
            organization_id=org.id,
            signal_type="pack_shared",
            audience_type="authority",
            source_entity_type="evidence_pack",
            source_entity_id=uuid.uuid4(),
        ),
        DistributionLoopSignal(
            id=uuid.uuid4(),
            building_id=building.id,
            organization_id=org.id,
            signal_type="embed_viewed",
            audience_type="insurer",
        ),
    ]
    for s in signals:
        db.add(s)

    # --- 1 Expansion Opportunity ---
    opp = ExpansionOpportunity(
        id=uuid.uuid4(),
        organization_id=org.id,
        opportunity_type="add_building",
        status="detected",
        recommended_action="Organization has proven value on 1 building — suggest adding remaining portfolio",
        evidence=[
            {"signal_type": "second_actor_active", "entity": "user", "date": str(now.date())},
            {"signal_type": "pack_consulted", "entity": "evidence_pack", "date": str(now.date())},
        ],
        priority="high",
        detected_at=now,
    )
    db.add(opp)

    # --- 6 Customer Success Milestones (3 achieved, 3 pending) ---
    milestones = [
        CustomerSuccessMilestone(
            id=uuid.uuid4(),
            organization_id=org.id,
            milestone_type="first_workflow_win",
            status="achieved",
            achieved_at=now - timedelta(days=10),
            evidence_entity_type="permit_procedure",
            evidence_entity_id=uuid.uuid4(),
            evidence_summary="Permit 'Renovation amiante Rue Test' approved",
        ),
        CustomerSuccessMilestone(
            id=uuid.uuid4(),
            organization_id=org.id,
            milestone_type="first_proof_reuse",
            status="achieved",
            achieved_at=now - timedelta(days=7),
            evidence_entity_type="proof_delivery",
            evidence_entity_id=uuid.uuid4(),
            evidence_summary="Same proof delivered to authority and insurer",
        ),
        CustomerSuccessMilestone(
            id=uuid.uuid4(),
            organization_id=org.id,
            milestone_type="first_actor_spread",
            status="achieved",
            achieved_at=now - timedelta(days=3),
            evidence_summary="3 distinct users active in workspace",
        ),
        CustomerSuccessMilestone(
            id=uuid.uuid4(),
            organization_id=org.id,
            milestone_type="first_blocker_caught",
            status="pending",
        ),
        CustomerSuccessMilestone(
            id=uuid.uuid4(),
            organization_id=org.id,
            milestone_type="first_trusted_pack",
            status="pending",
        ),
        CustomerSuccessMilestone(
            id=uuid.uuid4(),
            organization_id=org.id,
            milestone_type="first_exchange_publication",
            status="pending",
            blocker_description="No exchange contract version configured yet",
        ),
    ]
    for m in milestones:
        db.add(m)

    await db.flush()

    return {
        "status": "seeded",
        "triggers": len(triggers),
        "distribution_signals": len(signals),
        "opportunities": 1,
        "milestones": len(milestones),
    }
