"""
SwissBuildingOS - Authentication Service

Handles user authentication, JWT token creation, password hashing.
"""

from datetime import UTC, datetime, timedelta

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return pwd_context.verify(plain, hashed)
    except (ValueError, TypeError):
        # bcrypt rejects NULL bytes and certain edge-case inputs
        return False


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """
    Query user by email and verify the password.
    Returns the User if credentials are valid, None otherwise.
    """
    stmt = select(User).where(User.email == email, User.is_active == True)  # noqa: E712
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def create_access_token(user: User) -> tuple[str, int]:
    """
    Create a JWT access token for the given user.

    Returns:
        A tuple of (token_string, expires_in_seconds).
    """
    expires_in_seconds = settings.JWT_EXPIRATION_MINUTES * 60
    expire = datetime.now(UTC) + timedelta(seconds=expires_in_seconds)

    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return token, expires_in_seconds


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: str = "owner",
    language: str = "fr",
) -> User:
    """
    Register a new user with a hashed password.
    Creates the user record, commits the transaction, and returns the user.
    Raises ValueError if email is already taken.
    """
    # Check for existing email
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ValueError(f"Email '{email}' is already registered")

    hashed = hash_password(password)

    user = User(
        email=email,
        password_hash=hashed,
        first_name=first_name,
        last_name=last_name,
        role=role,
        language=language,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user
