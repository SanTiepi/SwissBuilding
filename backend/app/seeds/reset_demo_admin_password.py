"""
Reset or bootstrap the local demo admin credentials.

Usage:
    python -m app.seeds.reset_demo_admin_password
    python -m app.seeds.reset_demo_admin_password --password noob
    python -m app.seeds.reset_demo_admin_password --email admin@example.com --password secret123
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

from sqlalchemy import select

from app.constants import DEMO_ADMIN_EMAIL, DEMO_ADMIN_PASSWORD
from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.auth_service import hash_password


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset local demo admin credentials.")
    parser.add_argument("--email", default=DEMO_ADMIN_EMAIL, help="Admin email to reset/create.")
    parser.add_argument("--password", default=DEMO_ADMIN_PASSWORD, help="New password to set.")
    parser.add_argument(
        "--no-create-missing",
        dest="create_missing",
        action="store_false",
        help="Fail if the admin user does not exist.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == args.email))
        user = result.scalar_one_or_none()

        if user is None:
            if not args.create_missing:
                raise SystemExit(f"User not found: {args.email}")
            user = User(
                id=uuid.uuid4(),
                email=args.email,
                password_hash=hash_password(args.password),
                first_name="Admin",
                last_name="System",
                role="admin",
                language="fr",
                is_active=True,
            )
            db.add(user)
            await db.commit()
            print(f"[RESET-ADMIN] Created and activated admin user: {args.email}")
            return

        user.password_hash = hash_password(args.password)
        user.is_active = True
        await db.commit()
        print(f"[RESET-ADMIN] Password updated and user activated: {args.email}")


if __name__ == "__main__":
    asyncio.run(main())
