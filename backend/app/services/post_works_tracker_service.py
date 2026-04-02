"""Post-works truth tracker: validates contractor completion, calculates progress, flags reviews."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post_work_item import PostWorkItem, WorksCompletionCertificate

VALID_STATUSES = {"pending", "in_progress", "completed", "verified"}
MIN_PHOTOS_PER_ITEM = 1
REVIEW_THRESHOLD = 80.0  # Flag for manual review if score < 80


async def list_post_work_items(
    db: AsyncSession,
    building_id: UUID,
    *,
    status: str | None = None,
    page: int = 1,
    size: int = 20,
) -> dict:
    """List post-work items for a building with optional status filter."""
    query = select(PostWorkItem).where(PostWorkItem.building_id == building_id)
    count_q = select(func.count()).select_from(PostWorkItem).where(PostWorkItem.building_id == building_id)

    if status:
        query = query.where(PostWorkItem.completion_status == status)
        count_q = count_q.where(PostWorkItem.completion_status == status)

    total = (await db.execute(count_q)).scalar() or 0
    query = query.order_by(PostWorkItem.created_at.desc()).offset((page - 1) * size).limit(size)
    items = (await db.execute(query)).scalars().all()
    pages = (total + size - 1) // size if total > 0 else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


async def create_post_work_item(
    db: AsyncSession,
    building_id: UUID,
    contractor_id: UUID,
    data: dict,
) -> PostWorkItem:
    """Create a new post-work item for tracking."""
    item = PostWorkItem(building_id=building_id, contractor_id=contractor_id, **data)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def complete_post_work_item(
    db: AsyncSession,
    item: PostWorkItem,
    photo_uris: list[str],
    *,
    before_after_pairs: list[dict] | None = None,
    notes: str | None = None,
) -> PostWorkItem:
    """Contractor submits completion with photo evidence. Validates and scores."""
    score = _compute_verification_score(photo_uris, before_after_pairs, item)

    item.photo_uris = photo_uris
    item.before_after_pairs = before_after_pairs
    item.notes = notes
    item.completion_status = "completed"
    item.completion_date = datetime.now(UTC)
    item.verification_score = score
    item.flagged_for_review = score < REVIEW_THRESHOLD

    await db.commit()
    await db.refresh(item)
    return item


def _compute_verification_score(
    photo_uris: list[str],
    before_after_pairs: list[dict] | None,
    item: PostWorkItem,
) -> float:
    """Score 0-100 based on evidence quality."""
    score = 0.0

    # Photo count: at least 1 required, bonus for more
    photo_count = len(photo_uris) if photo_uris else 0
    if photo_count >= MIN_PHOTOS_PER_ITEM:
        score += 40.0
    if photo_count >= 3:
        score += 10.0

    # Before/after pairs present
    if before_after_pairs and len(before_after_pairs) > 0:
        score += 25.0

    # Timestamp logical: completion after creation
    if item.created_at:
        score += 15.0

    # Has notes / description
    if item.notes and len(item.notes) > 10:
        score += 10.0

    return min(score, 100.0)


async def get_completion_status(db: AsyncSession, building_id: UUID) -> dict:
    """Calculate overall completion % and breakdown for a building."""
    result = await db.execute(select(PostWorkItem).where(PostWorkItem.building_id == building_id))
    items = result.scalars().all()

    total = len(items)
    if total == 0:
        return {
            "building_id": building_id,
            "total_items": 0,
            "completed_items": 0,
            "verified_items": 0,
            "completion_percentage": 0.0,
            "items_by_status": {},
            "last_updated": None,
        }

    status_counts: dict[str, int] = {}
    last_updated = None
    for item in items:
        status_counts[item.completion_status] = status_counts.get(item.completion_status, 0) + 1
        if last_updated is None or item.updated_at > last_updated:
            last_updated = item.updated_at

    completed = status_counts.get("completed", 0) + status_counts.get("verified", 0)
    verified = status_counts.get("verified", 0)
    pct = round((completed / total) * 100, 1) if total > 0 else 0.0

    return {
        "building_id": building_id,
        "total_items": total,
        "completed_items": completed,
        "verified_items": verified,
        "completion_percentage": pct,
        "items_by_status": status_counts,
        "last_updated": last_updated,
    }


async def get_or_create_certificate(
    db: AsyncSession, building_id: UUID, contractor_signature_uri: str | None = None
) -> WorksCompletionCertificate | None:
    """Generate certificate if 100% complete; return existing if already issued."""
    status = await get_completion_status(db, building_id)
    if status["completion_percentage"] < 100.0:
        return None

    # Check existing
    existing = await db.execute(
        select(WorksCompletionCertificate).where(WorksCompletionCertificate.building_id == building_id)
    )
    cert = existing.scalar_one_or_none()
    if cert:
        return cert

    # Generate new
    from app.services.completion_certificate_generator import generate_completion_pdf

    pdf_uri = await generate_completion_pdf(db, building_id, status)

    cert = WorksCompletionCertificate(
        building_id=building_id,
        pdf_uri=pdf_uri,
        total_items=status["total_items"],
        verified_items=status["verified_items"],
        completion_percentage=status["completion_percentage"],
        contractor_signature_uri=contractor_signature_uri,
    )
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    return cert
