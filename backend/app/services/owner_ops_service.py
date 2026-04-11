"""BatiConnect — Owner Ops service for everyday building memory.

Provides the owner-level operational dashboard: recurring services, warranties,
insurance renewals, contract renewals, lease events, and annual cost summaries.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.contract import Contract
from app.models.insurance_policy import InsurancePolicy
from app.models.intervention import Intervention
from app.models.lease import Lease
from app.models.recurring_service import RecurringService, WarrantyRecord

# ---------------------------------------------------------------------------
# Frequency → timedelta mapping for next_service_date calculation
# ---------------------------------------------------------------------------

_FREQUENCY_DELTAS: dict[str, timedelta] = {
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
    "quarterly": timedelta(days=91),
    "semi_annual": timedelta(days=182),
    "annual": timedelta(days=365),
}


def _safe_date(val) -> date | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return None


async def _verify_building(db: AsyncSession, building_id: UUID) -> bool:
    result = await db.execute(select(Building.id).where(Building.id == building_id))
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# CRUD — Recurring Services
# ---------------------------------------------------------------------------


async def create_recurring_service(
    db: AsyncSession,
    building_id: UUID,
    org_id: UUID,
    data: dict,
) -> RecurringService:
    """Create a recurring service record."""
    service = RecurringService(building_id=building_id, organization_id=org_id, **data)
    db.add(service)
    await db.flush()
    await db.refresh(service)
    return service


async def list_recurring_services(
    db: AsyncSession,
    building_id: UUID,
    *,
    status_filter: str | None = None,
    service_type: str | None = None,
) -> list[RecurringService]:
    """List recurring services for a building."""
    query = select(RecurringService).where(RecurringService.building_id == building_id)
    if status_filter:
        query = query.where(RecurringService.status == status_filter)
    if service_type:
        query = query.where(RecurringService.service_type == service_type)
    query = query.order_by(RecurringService.next_service_date.asc().nullslast())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_recurring_service(db: AsyncSession, service_id: UUID) -> RecurringService | None:
    result = await db.execute(select(RecurringService).where(RecurringService.id == service_id))
    return result.scalar_one_or_none()


async def update_recurring_service(db: AsyncSession, service: RecurringService, data: dict) -> RecurringService:
    """Update recurring service fields."""
    for key, value in data.items():
        setattr(service, key, value)
    await db.flush()
    await db.refresh(service)
    return service


async def record_service_performed(
    db: AsyncSession,
    service: RecurringService,
    performed_date: date,
    notes: str | None = None,
) -> RecurringService:
    """Record that a recurring service was performed. Update next_service_date."""
    service.last_service_date = performed_date
    if notes:
        service.notes = notes

    # Calculate next service date based on frequency
    delta = _FREQUENCY_DELTAS.get(service.frequency)
    if delta:
        service.next_service_date = performed_date + delta
    # on_demand has no auto-next

    await db.flush()
    await db.refresh(service)
    return service


async def get_upcoming_services(
    db: AsyncSession,
    building_id: UUID,
    horizon_days: int = 30,
) -> list[RecurringService]:
    """Recurring services due within horizon."""
    today = date.today()
    horizon = today + timedelta(days=horizon_days)
    query = (
        select(RecurringService)
        .where(
            RecurringService.building_id == building_id,
            RecurringService.status == "active",
            RecurringService.next_service_date.isnot(None),
            RecurringService.next_service_date <= horizon,
        )
        .order_by(RecurringService.next_service_date.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# CRUD — Warranty Records
# ---------------------------------------------------------------------------


async def create_warranty(
    db: AsyncSession,
    building_id: UUID,
    org_id: UUID,
    data: dict,
) -> WarrantyRecord:
    """Create a warranty record."""
    warranty = WarrantyRecord(building_id=building_id, organization_id=org_id, **data)
    db.add(warranty)
    await db.flush()
    await db.refresh(warranty)
    return warranty


async def list_warranties(
    db: AsyncSession,
    building_id: UUID,
    *,
    status_filter: str | None = None,
    warranty_type: str | None = None,
) -> list[WarrantyRecord]:
    """List warranty records for a building."""
    query = select(WarrantyRecord).where(WarrantyRecord.building_id == building_id)
    if status_filter:
        query = query.where(WarrantyRecord.status == status_filter)
    if warranty_type:
        query = query.where(WarrantyRecord.warranty_type == warranty_type)
    query = query.order_by(WarrantyRecord.end_date.asc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_warranty(db: AsyncSession, warranty_id: UUID) -> WarrantyRecord | None:
    result = await db.execute(select(WarrantyRecord).where(WarrantyRecord.id == warranty_id))
    return result.scalar_one_or_none()


async def update_warranty(db: AsyncSession, warranty: WarrantyRecord, data: dict) -> WarrantyRecord:
    """Update warranty record fields."""
    for key, value in data.items():
        setattr(warranty, key, value)
    await db.flush()
    await db.refresh(warranty)
    return warranty


async def get_expiring_warranties(
    db: AsyncSession,
    building_id: UUID,
    horizon_days: int = 180,
) -> list[WarrantyRecord]:
    """Warranties expiring within horizon."""
    today = date.today()
    horizon = today + timedelta(days=horizon_days)
    query = (
        select(WarrantyRecord)
        .where(
            WarrantyRecord.building_id == building_id,
            WarrantyRecord.status == "active",
            WarrantyRecord.end_date <= horizon,
            WarrantyRecord.end_date >= today,
        )
        .order_by(WarrantyRecord.end_date.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Dashboard / Aggregation
# ---------------------------------------------------------------------------


async def get_owner_dashboard(
    db: AsyncSession,
    building_id: UUID,
) -> dict | None:
    """Owner-level dashboard: services, warranties, insurance, contracts, leases, costs."""
    if not await _verify_building(db, building_id):
        return None

    today = date.today()
    horizon_90 = today + timedelta(days=90)

    # Active recurring services
    services = await list_recurring_services(db, building_id, status_filter="active")
    upcoming_svc = [s for s in services if s.next_service_date and s.next_service_date <= horizon_90]

    # Active warranties
    all_warranties = await list_warranties(db, building_id)
    active_warranties = [w for w in all_warranties if w.status == "active"]
    expiring_warranties = [w for w in active_warranties if w.end_date and w.end_date <= horizon_90]

    # Insurance renewals
    ins_result = await db.execute(
        select(InsurancePolicy).where(
            InsurancePolicy.building_id == building_id,
            InsurancePolicy.status == "active",
        )
    )
    policies = list(ins_result.scalars().all())
    insurance_renewals = [
        {
            "id": str(p.id),
            "policy_type": p.policy_type,
            "insurer": p.insurer_name,
            "end_date": _safe_date(p.date_end).isoformat() if _safe_date(p.date_end) else None,
            "premium_chf": p.premium_annual_chf,
        }
        for p in policies
        if p.date_end and _safe_date(p.date_end) and _safe_date(p.date_end) <= horizon_90
    ]

    # Contract renewals
    ctr_result = await db.execute(
        select(Contract).where(
            Contract.building_id == building_id,
            Contract.status == "active",
        )
    )
    contracts = list(ctr_result.scalars().all())
    contract_renewals = [
        {
            "id": str(c.id),
            "title": c.title,
            "contract_type": c.contract_type,
            "end_date": _safe_date(c.date_end).isoformat() if _safe_date(c.date_end) else None,
            "auto_renewal": c.auto_renewal,
            "annual_cost_chf": c.annual_cost_chf,
        }
        for c in contracts
        if c.date_end and _safe_date(c.date_end) and _safe_date(c.date_end) <= horizon_90
    ]

    # Lease events
    lease_result = await db.execute(
        select(Lease).where(
            Lease.building_id == building_id,
            Lease.status == "active",
        )
    )
    leases = list(lease_result.scalars().all())
    lease_events = [
        {
            "id": str(le.id),
            "reference": le.reference_code,
            "lease_type": le.lease_type,
            "end_date": _safe_date(le.date_end).isoformat() if _safe_date(le.date_end) else None,
            "rent_monthly_chf": le.rent_monthly_chf,
        }
        for le in leases
        if le.date_end and _safe_date(le.date_end) and _safe_date(le.date_end) <= horizon_90
    ]

    # Financial summary
    services_cost = sum(s.annual_cost_chf or 0 for s in services)
    insurance_cost = sum(p.premium_annual_chf or 0 for p in policies)
    contracts_cost = sum(c.annual_cost_chf or 0 for c in contracts)

    return {
        "building_id": str(building_id),
        "evaluated_at": datetime.now(UTC).isoformat(),
        "services": {
            "active_count": len(services),
            "upcoming_90d": len(upcoming_svc),
            "items": [
                {
                    "id": str(s.id),
                    "service_type": s.service_type,
                    "provider": s.provider_name,
                    "next_date": s.next_service_date.isoformat() if s.next_service_date else None,
                    "frequency": s.frequency,
                    "annual_cost_chf": s.annual_cost_chf,
                }
                for s in upcoming_svc
            ],
        },
        "warranties": {
            "active_count": len(active_warranties),
            "expiring_90d": len(expiring_warranties),
            "items": [
                {
                    "id": str(w.id),
                    "warranty_type": w.warranty_type,
                    "subject": w.subject,
                    "provider": w.provider_name,
                    "end_date": w.end_date.isoformat(),
                    "claim_filed": w.claim_filed,
                }
                for w in expiring_warranties
            ],
        },
        "insurance_renewals": insurance_renewals,
        "contract_renewals": contract_renewals,
        "lease_events": lease_events,
        "annual_costs": {
            "services_chf": services_cost,
            "insurance_chf": insurance_cost,
            "contracts_chf": contracts_cost,
            "total_chf": services_cost + insurance_cost + contracts_cost,
        },
    }


async def get_annual_cost_summary(
    db: AsyncSession,
    building_id: UUID,
    year: int | None = None,
) -> dict | None:
    """Annual cost breakdown: services + insurance + contracts + interventions."""
    if not await _verify_building(db, building_id):
        return None

    target_year = year or date.today().year

    # Recurring services (active in target year)
    svc_result = await db.execute(
        select(RecurringService).where(
            RecurringService.building_id == building_id,
            RecurringService.status.in_(["active", "paused"]),
        )
    )
    services = list(svc_result.scalars().all())
    services_in_year = [
        s
        for s in services
        if s.start_date.year <= target_year and (s.end_date is None or s.end_date.year >= target_year)
    ]
    services_cost = sum(s.annual_cost_chf or 0 for s in services_in_year)

    # Insurance
    ins_result = await db.execute(
        select(InsurancePolicy).where(
            InsurancePolicy.building_id == building_id,
        )
    )
    policies = list(ins_result.scalars().all())
    policies_in_year = [
        p
        for p in policies
        if p.date_start.year <= target_year and (p.date_end is None or p.date_end.year >= target_year)
    ]
    insurance_cost = sum(p.premium_annual_chf or 0 for p in policies_in_year)

    # Contracts
    ctr_result = await db.execute(
        select(Contract).where(
            Contract.building_id == building_id,
        )
    )
    contracts = list(ctr_result.scalars().all())
    contracts_in_year = [
        c
        for c in contracts
        if c.date_start.year <= target_year and (c.date_end is None or c.date_end.year >= target_year)
    ]
    contracts_cost = sum(c.annual_cost_chf or 0 for c in contracts_in_year)

    # Interventions
    intv_result = await db.execute(
        select(Intervention).where(
            Intervention.building_id == building_id,
        )
    )
    interventions = list(intv_result.scalars().all())
    intv_in_year = [
        i
        for i in interventions
        if i.date_start
        and _safe_date(i.date_start).year <= target_year
        and (i.date_end is None or _safe_date(i.date_end) is None or _safe_date(i.date_end).year >= target_year)
    ]
    intv_cost = sum(getattr(i, "estimated_cost_chf", 0) or 0 for i in intv_in_year)

    total = services_cost + insurance_cost + contracts_cost + intv_cost

    return {
        "building_id": str(building_id),
        "year": target_year,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "breakdown": {
            "services": {
                "count": len(services_in_year),
                "total_chf": services_cost,
                "items": [
                    {
                        "service_type": s.service_type,
                        "provider": s.provider_name,
                        "annual_cost_chf": s.annual_cost_chf,
                    }
                    for s in services_in_year
                ],
            },
            "insurance": {
                "count": len(policies_in_year),
                "total_chf": insurance_cost,
                "items": [
                    {
                        "policy_type": p.policy_type,
                        "insurer": p.insurer_name,
                        "premium_chf": p.premium_annual_chf,
                    }
                    for p in policies_in_year
                ],
            },
            "contracts": {
                "count": len(contracts_in_year),
                "total_chf": contracts_cost,
                "items": [
                    {
                        "title": c.title,
                        "contract_type": c.contract_type,
                        "annual_cost_chf": c.annual_cost_chf,
                    }
                    for c in contracts_in_year
                ],
            },
            "interventions": {
                "count": len(intv_in_year),
                "total_chf": intv_cost,
            },
        },
        "total_chf": total,
    }
