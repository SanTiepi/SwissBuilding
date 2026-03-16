from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.audit_service import log_action

router = APIRouter()


@router.get("", response_model=PaginatedResponse[UserRead])
async def list_users_endpoint(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permission("users", "list")),
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only) with pagination."""
    # Count total
    count_result = await db.execute(select(func.count()).select_from(User))
    total = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * size
    result = await db.execute(select(User).order_by(User.created_at.desc()).offset(offset).limit(size))
    users = result.scalars().all()
    pages = (total + size - 1) // size

    return {
        "items": [UserRead.model_validate(u) for u in users],
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.post("", response_model=UserRead, status_code=201)
async def create_user_endpoint(
    data: UserCreate,
    current_user: User = Depends(require_permission("users", "create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user (admin only)."""
    from app.services.auth_service import register_user

    user = await register_user(db, data.email, data.password, data.first_name, data.last_name, data.role, data.language)
    await log_action(db, current_user.id, "create", "user", user.id)
    return UserRead.model_validate(user)


@router.put("/{user_id}", response_model=UserRead)
async def update_user_endpoint(
    user_id: UUID,
    data: UserUpdate,
    current_user: User = Depends(require_permission("users", "update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    await log_action(db, current_user.id, "update", "user", user_id)
    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user_endpoint(
    user_id: UUID,
    current_user: User = Depends(require_permission("users", "delete")),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a user (admin only). Does not hard-delete."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    user.is_active = False
    await db.commit()
    await log_action(db, current_user.id, "deactivate", "user", user_id)
