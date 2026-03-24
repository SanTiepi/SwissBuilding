"""BatiConnect — Intake Request service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.contact import Contact
from app.models.intake_request import IntakeRequest


async def submit_request(db: AsyncSession, data: dict) -> IntakeRequest:
    """Public submission — no auth required."""
    intake = IntakeRequest(status="new", **data)
    db.add(intake)
    await db.flush()
    await db.refresh(intake)
    return intake


async def list_requests(
    db: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    status: str | None = None,
) -> tuple[list[IntakeRequest], int]:
    query = select(IntakeRequest)
    count_query = select(func.count()).select_from(IntakeRequest)

    if status:
        query = query.where(IntakeRequest.status == status)
        count_query = count_query.where(IntakeRequest.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(IntakeRequest.created_at.desc()).offset((page - 1) * size).limit(size)
    items = (await db.execute(query)).scalars().all()
    return list(items), total


async def get_request(db: AsyncSession, intake_id: UUID) -> IntakeRequest | None:
    result = await db.execute(select(IntakeRequest).where(IntakeRequest.id == intake_id))
    return result.scalar_one_or_none()


async def qualify_request(
    db: AsyncSession,
    intake: IntakeRequest,
    user_id: UUID,
    notes: str | None = None,
) -> IntakeRequest:
    intake.status = "qualified"
    intake.qualified_by_user_id = user_id
    intake.qualified_at = datetime.now(UTC)
    if notes:
        intake.notes = notes
    await db.flush()
    await db.refresh(intake)
    return intake


async def reject_request(
    db: AsyncSession,
    intake: IntakeRequest,
    user_id: UUID,
    reason: str | None = None,
) -> IntakeRequest:
    intake.status = "rejected"
    intake.qualified_by_user_id = user_id
    intake.qualified_at = datetime.now(UTC)
    if reason:
        intake.notes = reason
    await db.flush()
    await db.refresh(intake)
    return intake


async def convert_request(
    db: AsyncSession,
    intake: IntakeRequest,
    user_id: UUID,
    organization_id: UUID | None = None,
    notes: str | None = None,
) -> IntakeRequest:
    """Convert an intake request into Contact + Building records."""
    # Create Contact from requester info
    contact = Contact(
        organization_id=organization_id,
        contact_type="person",
        name=intake.requester_name,
        company_name=intake.requester_company,
        email=intake.requester_email,
        phone=intake.requester_phone,
        source_type="manual",
        confidence="declared",
        source_ref=f"intake:{intake.id}",
        is_active=True,
        created_by=user_id,
    )
    db.add(contact)
    await db.flush()

    # Create Building from address info
    building = Building(
        address=intake.building_address,
        postal_code=intake.building_postal_code or "0000",
        city=intake.building_city or "Unknown",
        canton="XX",
        building_type="other",
        created_by=user_id,
        organization_id=organization_id,
    )
    if intake.building_egid and intake.building_egid.isdigit():
        building.egid = int(intake.building_egid)
    db.add(building)
    await db.flush()

    # Update intake with converted IDs
    intake.status = "converted"
    intake.converted_contact_id = contact.id
    intake.converted_building_id = building.id
    intake.qualified_by_user_id = user_id
    intake.qualified_at = datetime.now(UTC)
    if notes:
        intake.notes = notes
    await db.flush()
    await db.refresh(intake)
    return intake
