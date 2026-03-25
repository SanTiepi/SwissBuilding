"""ControlTower v2 — Action Aggregation Service.

READ MODEL that aggregates existing sources into a unified, priority-sorted
action feed.  No persistent action entity — everything is computed on the fly
from Obligation, PermitProcedure, AuthorityRequest, DocumentInboxItem,
DiagnosticReportPublication, IntakeRequest, Lease, and Contract.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.authority_request import AuthorityRequest
from app.models.contract import Contract
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.document_inbox import DocumentInboxItem
from app.models.intake_request import IntakeRequest
from app.models.lease import Lease
from app.models.obligation import Obligation
from app.models.permit_procedure import PermitProcedure
from app.models.permit_step import PermitStep
from app.schemas.action_feed import ActionFeedItem, ActionFeedResponse, ActionFeedSummary

# ---------------------------------------------------------------------------
# Priority constants
# ---------------------------------------------------------------------------
P0_PROCEDURAL_BLOCKER = 0
P1_OVERDUE_AUTHORITY = 1
P2_OVERDUE_OBLIGATION = 2
P3_PENDING_REVIEW = 3
P4_UPCOMING_DEADLINE = 4

LABEL_MAP = {
    P0_PROCEDURAL_BLOCKER: "procedural_blocker",
    P1_OVERDUE_AUTHORITY: "overdue_authority_request",
    P2_OVERDUE_OBLIGATION: "overdue_obligation",
    P3_PENDING_REVIEW: "pending_review",
    P4_UPCOMING_DEADLINE: "upcoming_deadline",
}

_RENEWAL_HORIZON_DAYS = 90


# ---------------------------------------------------------------------------
# Individual collectors
# ---------------------------------------------------------------------------


async def _collect_obligations(
    db: AsyncSession,
    *,
    building_id: UUID | None = None,
    organization_id: UUID | None = None,
) -> list[ActionFeedItem]:
    """Obligations: overdue → P2, due_soon → P4."""
    stmt = select(Obligation).where(Obligation.status.in_(["overdue", "due_soon"]))
    if building_id:
        stmt = stmt.where(Obligation.building_id == building_id)
    if organization_id:
        stmt = stmt.where(Obligation.responsible_org_id == organization_id)
    result = await db.execute(stmt)
    items: list[ActionFeedItem] = []
    for ob in result.scalars().all():
        is_overdue = ob.status == "overdue"
        priority = P2_OVERDUE_OBLIGATION if is_overdue else P4_UPCOMING_DEADLINE
        items.append(
            ActionFeedItem(
                id=f"obligation:{ob.id}",
                priority=priority,
                priority_label=LABEL_MAP[priority],
                source_type="obligation",
                source_id=ob.id,
                building_id=ob.building_id,
                building_address=None,  # enriched later
                title=ob.title,
                description=ob.description or f"{ob.obligation_type} obligation",
                due_date=ob.due_date,
                assigned_org_id=ob.responsible_org_id,
                assigned_user_id=ob.responsible_user_id,
                link=f"/buildings/{ob.building_id}/obligations/{ob.id}",
            )
        )
    return items


async def _collect_permit_blockers(
    db: AsyncSession,
    *,
    building_id: UUID | None = None,
    organization_id: UUID | None = None,
) -> list[ActionFeedItem]:
    """PermitProcedure blockers: complement_requested procedures → P0,
    blocked steps → P0."""
    items: list[ActionFeedItem] = []

    # complement_requested procedures
    stmt = select(PermitProcedure).where(PermitProcedure.status == "complement_requested")
    if building_id:
        stmt = stmt.where(PermitProcedure.building_id == building_id)
    if organization_id:
        stmt = stmt.where(PermitProcedure.assigned_org_id == organization_id)
    result = await db.execute(stmt)
    for proc in result.scalars().all():
        items.append(
            ActionFeedItem(
                id=f"procedure:{proc.id}",
                priority=P0_PROCEDURAL_BLOCKER,
                priority_label=LABEL_MAP[P0_PROCEDURAL_BLOCKER],
                source_type="procedure",
                source_id=proc.id,
                building_id=proc.building_id,
                building_address=None,
                title=f"Permit blocked: {proc.title}",
                description=proc.description or f"{proc.procedure_type} — complement requested",
                due_date=None,
                assigned_org_id=proc.assigned_org_id,
                assigned_user_id=proc.assigned_user_id,
                link=f"/buildings/{proc.building_id}/permits/{proc.id}",
            )
        )

    # blocked steps
    stmt2 = select(PermitStep).where(PermitStep.status == "blocked").options(joinedload(PermitStep.procedure))
    if building_id:
        stmt2 = stmt2.join(PermitProcedure).where(PermitProcedure.building_id == building_id)
    result2 = await db.execute(stmt2)
    for step in result2.unique().scalars().all():
        proc = step.procedure
        if proc and (not organization_id or proc.assigned_org_id == organization_id):
            items.append(
                ActionFeedItem(
                    id=f"procedure:{step.id}",
                    priority=P0_PROCEDURAL_BLOCKER,
                    priority_label=LABEL_MAP[P0_PROCEDURAL_BLOCKER],
                    source_type="procedure",
                    source_id=step.id,
                    building_id=proc.building_id,
                    building_address=None,
                    title=f"Step blocked: {step.title}",
                    description=step.description or f"Blocked step in {proc.title}",
                    due_date=step.due_date,
                    assigned_org_id=step.assigned_org_id,
                    assigned_user_id=step.assigned_user_id,
                    link=f"/buildings/{proc.building_id}/permits/{proc.id}",
                )
            )
    return items


async def _collect_authority_requests(
    db: AsyncSession,
    *,
    building_id: UUID | None = None,
    organization_id: UUID | None = None,
) -> list[ActionFeedItem]:
    """AuthorityRequest overdue (response_due_date passed) → P1."""
    today = date.today()
    stmt = (
        select(AuthorityRequest)
        .where(
            AuthorityRequest.status.in_(["open", "overdue"]),
            AuthorityRequest.response_due_date <= today,
        )
        .options(joinedload(AuthorityRequest.procedure))
    )
    result = await db.execute(stmt)
    items: list[ActionFeedItem] = []
    for ar in result.unique().scalars().all():
        proc = ar.procedure
        if building_id and (not proc or proc.building_id != building_id):
            continue
        if organization_id and (not proc or proc.assigned_org_id != organization_id):
            continue
        b_id = proc.building_id if proc else None
        items.append(
            ActionFeedItem(
                id=f"authority_request:{ar.id}",
                priority=P1_OVERDUE_AUTHORITY,
                priority_label=LABEL_MAP[P1_OVERDUE_AUTHORITY],
                source_type="authority_request",
                source_id=ar.id,
                building_id=b_id,
                building_address=None,
                title=f"Overdue: {ar.subject}",
                description=ar.body[:200] if ar.body else "Authority request overdue",
                due_date=ar.response_due_date,
                assigned_org_id=proc.assigned_org_id if proc else None,
                assigned_user_id=proc.assigned_user_id if proc else None,
                link=f"/buildings/{b_id}/permits/{ar.procedure_id}" if b_id else f"/permits/{ar.procedure_id}",
            )
        )
    return items


async def _collect_inbox(
    db: AsyncSession,
    *,
    building_id: UUID | None = None,
) -> list[ActionFeedItem]:
    """DocumentInbox pending items → P3."""
    stmt = select(DocumentInboxItem).where(DocumentInboxItem.status == "pending")
    if building_id:
        stmt = stmt.where(DocumentInboxItem.suggested_building_id == building_id)
    result = await db.execute(stmt)
    items: list[ActionFeedItem] = []
    for item in result.scalars().all():
        items.append(
            ActionFeedItem(
                id=f"inbox:{item.id}",
                priority=P3_PENDING_REVIEW,
                priority_label=LABEL_MAP[P3_PENDING_REVIEW],
                source_type="inbox",
                source_id=item.id,
                building_id=item.suggested_building_id,
                building_address=None,
                title=f"Inbox: {item.filename}",
                description=item.notes or "Pending document in inbox",
                due_date=None,
                assigned_org_id=None,
                assigned_user_id=item.uploaded_by_user_id,
                link="/inbox",
            )
        )
    return items


async def _collect_publications(
    db: AsyncSession,
    *,
    building_id: UUID | None = None,
) -> list[ActionFeedItem]:
    """DiagnosticReportPublication unmatched/needs_review → P3."""
    stmt = select(DiagnosticReportPublication).where(
        DiagnosticReportPublication.match_state.in_(["unmatched", "needs_review"])
    )
    if building_id:
        stmt = stmt.where(DiagnosticReportPublication.building_id == building_id)
    result = await db.execute(stmt)
    items: list[ActionFeedItem] = []
    for pub in result.scalars().all():
        items.append(
            ActionFeedItem(
                id=f"publication:{pub.id}",
                priority=P3_PENDING_REVIEW,
                priority_label=LABEL_MAP[P3_PENDING_REVIEW],
                source_type="publication",
                source_id=pub.id,
                building_id=pub.building_id,
                building_address=None,
                title=f"Report review: {pub.source_mission_id}",
                description=f"{pub.mission_type} report ({pub.match_state})",
                due_date=None,
                assigned_org_id=None,
                assigned_user_id=None,
                link=f"/publications/{pub.id}",
            )
        )
    return items


async def _collect_intakes(
    db: AsyncSession,
) -> list[ActionFeedItem]:
    """IntakeRequest new → P3."""
    stmt = select(IntakeRequest).where(IntakeRequest.status == "new")
    result = await db.execute(stmt)
    items: list[ActionFeedItem] = []
    for ir in result.scalars().all():
        items.append(
            ActionFeedItem(
                id=f"intake:{ir.id}",
                priority=P3_PENDING_REVIEW,
                priority_label=LABEL_MAP[P3_PENDING_REVIEW],
                source_type="intake",
                source_id=ir.id,
                building_id=None,
                building_address=ir.building_address,
                title=f"New intake: {ir.requester_name}",
                description=ir.description or f"{ir.request_type} request",
                due_date=None,
                assigned_org_id=None,
                assigned_user_id=None,
                link="/intake",
            )
        )
    return items


async def _collect_permit_expiring(
    db: AsyncSession,
    *,
    building_id: UUID | None = None,
    organization_id: UUID | None = None,
) -> list[ActionFeedItem]:
    """PermitProcedure expiring soon (within 90 days) → P4."""
    today = date.today()
    horizon = today + timedelta(days=_RENEWAL_HORIZON_DAYS)
    stmt = select(PermitProcedure).where(
        PermitProcedure.status == "approved",
        PermitProcedure.expires_at.isnot(None),
        func.date(PermitProcedure.expires_at) <= horizon,
        func.date(PermitProcedure.expires_at) >= today,
    )
    if building_id:
        stmt = stmt.where(PermitProcedure.building_id == building_id)
    if organization_id:
        stmt = stmt.where(PermitProcedure.assigned_org_id == organization_id)
    result = await db.execute(stmt)
    items: list[ActionFeedItem] = []
    for proc in result.scalars().all():
        exp_date = proc.expires_at.date() if proc.expires_at else None
        items.append(
            ActionFeedItem(
                id=f"procedure:{proc.id}:expiring",
                priority=P4_UPCOMING_DEADLINE,
                priority_label=LABEL_MAP[P4_UPCOMING_DEADLINE],
                source_type="procedure",
                source_id=proc.id,
                building_id=proc.building_id,
                building_address=None,
                title=f"Permit expiring: {proc.title}",
                description=f"{proc.procedure_type} permit expires soon",
                due_date=exp_date,
                assigned_org_id=proc.assigned_org_id,
                assigned_user_id=proc.assigned_user_id,
                link=f"/buildings/{proc.building_id}/permits/{proc.id}",
            )
        )
    return items


async def _collect_lease_renewals(
    db: AsyncSession,
    *,
    building_id: UUID | None = None,
) -> list[ActionFeedItem]:
    """Lease renewals approaching (end_date within 90 days) → P4."""
    today = date.today()
    horizon = today + timedelta(days=_RENEWAL_HORIZON_DAYS)
    stmt = select(Lease).where(
        Lease.status == "active",
        Lease.date_end.isnot(None),
        Lease.date_end <= horizon,
        Lease.date_end >= today,
    )
    if building_id:
        stmt = stmt.where(Lease.building_id == building_id)
    result = await db.execute(stmt)
    items: list[ActionFeedItem] = []
    for lease in result.scalars().all():
        items.append(
            ActionFeedItem(
                id=f"lease:{lease.id}",
                priority=P4_UPCOMING_DEADLINE,
                priority_label=LABEL_MAP[P4_UPCOMING_DEADLINE],
                source_type="lease",
                source_id=lease.id,
                building_id=lease.building_id,
                building_address=None,
                title=f"Lease ending: {lease.reference_code}",
                description=f"Lease {lease.reference_code} ends on {lease.date_end}",
                due_date=lease.date_end,
                assigned_org_id=None,
                assigned_user_id=None,
                link=f"/buildings/{lease.building_id}/leases/{lease.id}",
            )
        )
    return items


async def _collect_contract_renewals(
    db: AsyncSession,
    *,
    building_id: UUID | None = None,
) -> list[ActionFeedItem]:
    """Contract renewals approaching (end_date within 90 days) → P4."""
    today = date.today()
    horizon = today + timedelta(days=_RENEWAL_HORIZON_DAYS)
    stmt = select(Contract).where(
        Contract.status == "active",
        Contract.date_end.isnot(None),
        Contract.date_end <= horizon,
        Contract.date_end >= today,
    )
    if building_id:
        stmt = stmt.where(Contract.building_id == building_id)
    result = await db.execute(stmt)
    items: list[ActionFeedItem] = []
    for c in result.scalars().all():
        items.append(
            ActionFeedItem(
                id=f"contract:{c.id}",
                priority=P4_UPCOMING_DEADLINE,
                priority_label=LABEL_MAP[P4_UPCOMING_DEADLINE],
                source_type="contract",
                source_id=c.id,
                building_id=c.building_id,
                building_address=None,
                title=f"Contract ending: {c.title}",
                description=f"Contract {c.reference_code} ends on {c.date_end}",
                due_date=c.date_end,
                assigned_org_id=None,
                assigned_user_id=None,
                link=f"/buildings/{c.building_id}/contracts/{c.id}",
            )
        )
    return items


# ---------------------------------------------------------------------------
# Address enrichment
# ---------------------------------------------------------------------------


async def _enrich_building_addresses(db: AsyncSession, items: list[ActionFeedItem]) -> None:
    """Batch-load building addresses for all items that have a building_id."""
    from app.models.building import Building

    bids = {it.building_id for it in items if it.building_id}
    if not bids:
        return
    result = await db.execute(select(Building.id, Building.address).where(Building.id.in_(bids)))
    addr_map = {row[0]: row[1] for row in result.all()}
    for it in items:
        if it.building_id and it.building_id in addr_map:
            it.building_address = addr_map[it.building_id]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_action_feed(
    db: AsyncSession,
    user_id: UUID,
    *,
    building_id: UUID | None = None,
    organization_id: UUID | None = None,
    priority_min: int | None = None,
    priority_max: int | None = None,
    source_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ActionFeedResponse:
    """Aggregate all action sources into a single priority-sorted feed."""
    all_items: list[ActionFeedItem] = []

    # Collect from all sources
    all_items.extend(await _collect_obligations(db, building_id=building_id, organization_id=organization_id))
    all_items.extend(await _collect_permit_blockers(db, building_id=building_id, organization_id=organization_id))
    all_items.extend(await _collect_authority_requests(db, building_id=building_id, organization_id=organization_id))
    all_items.extend(await _collect_inbox(db, building_id=building_id))
    all_items.extend(await _collect_publications(db, building_id=building_id))
    all_items.extend(await _collect_intakes(db))
    all_items.extend(await _collect_permit_expiring(db, building_id=building_id, organization_id=organization_id))
    all_items.extend(await _collect_lease_renewals(db, building_id=building_id))
    all_items.extend(await _collect_contract_renewals(db, building_id=building_id))

    # Apply filters
    if priority_min is not None:
        all_items = [it for it in all_items if it.priority >= priority_min]
    if priority_max is not None:
        all_items = [it for it in all_items if it.priority <= priority_max]
    if source_type:
        all_items = [it for it in all_items if it.source_type == source_type]

    # Sort: priority ASC (lower = more urgent), then due_date ASC (nulls last)
    all_items.sort(key=lambda it: (it.priority, it.due_date or date.max))

    total = len(all_items)
    page = all_items[offset : offset + limit]

    # Enrich with building addresses
    await _enrich_building_addresses(db, page)

    filters_applied = {}
    if building_id:
        filters_applied["building_id"] = str(building_id)
    if organization_id:
        filters_applied["organization_id"] = str(organization_id)
    if priority_min is not None:
        filters_applied["priority_min"] = priority_min
    if priority_max is not None:
        filters_applied["priority_max"] = priority_max
    if source_type:
        filters_applied["source_type"] = source_type

    return ActionFeedResponse(items=page, total=total, filters_applied=filters_applied)


async def get_feed_summary(
    db: AsyncSession,
    user_id: UUID,
) -> ActionFeedSummary:
    """Counts per priority level and source type."""
    feed = await get_action_feed(db, user_id, limit=10000, offset=0)
    by_priority: dict[int, int] = {}
    by_source: dict[str, int] = {}
    for item in feed.items:
        by_priority[item.priority] = by_priority.get(item.priority, 0) + 1
        by_source[item.source_type] = by_source.get(item.source_type, 0) + 1
    return ActionFeedSummary(
        total=feed.total,
        by_priority=by_priority,
        by_source_type=by_source,
    )
