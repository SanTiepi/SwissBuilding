"""BatiConnect — Minimal contact lookup for lease creation, scoped to building's org."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.building import Building
from app.models.contact import Contact
from app.models.user import User

router = APIRouter()


@router.get("/buildings/{building_id}/contacts/lookup")
async def lookup_contacts(
    building_id: UUID,
    q: str = Query("", min_length=0, description="Search by name or email"),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(require_permission("leases", "list")),
    db: AsyncSession = Depends(get_db),
):
    """Lookup contacts scoped to the building's organization."""
    result = await db.execute(select(Building).where(Building.id == building_id))
    building = result.scalar_one_or_none()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    # Building without org → no contacts (never expose global annuaire)
    if not building.organization_id:
        return []

    query = (
        select(Contact).where(Contact.is_active.is_(True)).where(Contact.organization_id == building.organization_id)
    )

    if q:
        query = query.where(Contact.name.ilike(f"%{q}%") | Contact.email.ilike(f"%{q}%"))
    query = query.order_by(Contact.name).limit(limit)
    result = await db.execute(query)
    contacts = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "email": c.email,
            "contact_type": c.contact_type,
        }
        for c in contacts
    ]
