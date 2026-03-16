from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.limiter import limiter
from app.models.user import User
from app.schemas.auth import LoginRequest, PasswordChange, ProfileUpdate, RegisterRequest, TokenResponse
from app.schemas.user import UserRead
from app.services.audit_service import log_action
from app.services.auth_service import authenticate_user, create_access_token, register_user

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate a user and return a JWT token."""
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token, expires_in = create_access_token(user)
    await log_action(db, user.id, "login", "user", user.id)
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserRead.model_validate(user),
    )


@router.post("/register", response_model=UserRead, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Self-register a new owner account."""
    if data.role != "owner":
        raise HTTPException(status_code=400, detail="Only 'owner' role can self-register")
    try:
        user = await register_user(
            db, data.email, data.password, data.first_name, data.last_name, data.role, data.language
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    await log_action(db, user.id, "register", "user", user.id)
    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user profile."""
    return UserRead.model_validate(current_user)


@router.put("/me", response_model=UserRead)
async def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    await log_action(db, current_user.id, "update_profile", "user", current_user.id)
    return UserRead.model_validate(current_user)


@router.put("/me/password", status_code=204)
async def change_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the current user's password."""
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    if not pwd_context.verify(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = pwd_context.hash(data.new_password)
    await db.commit()
    await log_action(db, current_user.id, "change_password", "user", current_user.id)
