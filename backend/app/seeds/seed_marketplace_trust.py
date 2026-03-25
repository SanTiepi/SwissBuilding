"""BatiConnect — Marketplace Trust seed (idempotent).

Run: python -m app.seeds.seed_marketplace_trust

Creates:
- 1 AwardConfirmation (for existing seeded quote)
- 1 CompletionConfirmation (fully_confirmed)
- 2 Reviews (1 published with 4/5 rating, 1 under_moderation)
"""

import asyncio
import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.award_confirmation import AwardConfirmation
from app.models.client_request import ClientRequest
from app.models.completion_confirmation import CompletionConfirmation
from app.models.quote import Quote
from app.models.review import Review
from app.models.user import User

# Stable UUIDs for idempotent seed
SEED_AWARD_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234500010")
SEED_COMPLETION_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234500011")
SEED_REVIEW1_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234500012")
SEED_REVIEW2_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234500013")

# From seed_marketplace_rfq.py
SEED_REQUEST_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234500001")
SEED_QUOTE1_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234500006")


async def seed():
    async with AsyncSessionLocal() as db:
        # Check idempotency
        existing = await db.execute(select(AwardConfirmation).where(AwardConfirmation.id == SEED_AWARD_ID))
        if existing.scalar_one_or_none():
            print("Marketplace Trust seed already present — skipping.")
            return

        # Find admin user
        admin_result = await db.execute(select(User).where(User.email == "admin@swissbuildingos.ch"))
        admin = admin_result.scalar_one_or_none()
        if not admin:
            print("Admin user not found — run base seed first.")
            return

        # Verify the RFQ seed data exists
        quote_result = await db.execute(select(Quote).where(Quote.id == SEED_QUOTE1_ID))
        quote = quote_result.scalar_one_or_none()
        if not quote:
            print("Seeded quote not found — run seed_marketplace_rfq first.")
            return

        req_result = await db.execute(select(ClientRequest).where(ClientRequest.id == SEED_REQUEST_ID))
        req = req_result.scalar_one_or_none()
        if not req:
            print("Seeded client request not found — run seed_marketplace_rfq first.")
            return

        now = datetime.now(UTC)

        # 1. Update quote and request status to support award
        quote.status = "awarded"
        req.status = "awarded"
        await db.flush()

        # 2. AwardConfirmation
        award_content = {
            "client_request_id": str(SEED_REQUEST_ID),
            "quote_id": str(SEED_QUOTE1_ID),
            "company_profile_id": str(quote.company_profile_id),
            "award_amount_chf": str(quote.amount_chf),
            "conditions": "Travaux a realiser entre 8h et 17h, jours ouvrables uniquement.",
            "awarded_at": (now - timedelta(days=14)).isoformat(),
        }
        award_hash = hashlib.sha256(json.dumps(award_content, sort_keys=True).encode()).hexdigest()

        award = AwardConfirmation(
            id=SEED_AWARD_ID,
            client_request_id=SEED_REQUEST_ID,
            quote_id=SEED_QUOTE1_ID,
            company_profile_id=quote.company_profile_id,
            awarded_by_user_id=admin.id,
            award_amount_chf=quote.amount_chf,
            conditions="Travaux a realiser entre 8h et 17h, jours ouvrables uniquement.",
            content_hash=award_hash,
            awarded_at=now - timedelta(days=14),
        )
        db.add(award)
        await db.flush()

        # 3. CompletionConfirmation (fully_confirmed)
        completion = CompletionConfirmation(
            id=SEED_COMPLETION_ID,
            award_confirmation_id=SEED_AWARD_ID,
            client_confirmed=True,
            client_confirmed_at=now - timedelta(days=3),
            client_confirmed_by_user_id=admin.id,
            company_confirmed=True,
            company_confirmed_at=now - timedelta(days=2),
            company_confirmed_by_user_id=admin.id,
            status="fully_confirmed",
            completion_notes="Travaux termines sans incident. Zone propre.",
            final_amount_chf=quote.amount_chf,
        )
        comp_content = {
            "award_confirmation_id": str(SEED_AWARD_ID),
            "client_confirmed": True,
            "company_confirmed": True,
            "completion_notes": completion.completion_notes,
            "final_amount_chf": str(completion.final_amount_chf),
        }
        completion.content_hash = hashlib.sha256(json.dumps(comp_content, sort_keys=True).encode()).hexdigest()
        db.add(completion)
        await db.flush()

        # 4. Reviews
        review_published = Review(
            id=SEED_REVIEW1_ID,
            completion_confirmation_id=SEED_COMPLETION_ID,
            client_request_id=SEED_REQUEST_ID,
            company_profile_id=quote.company_profile_id,
            reviewer_user_id=admin.id,
            reviewer_type="client",
            rating=4,
            quality_score=4,
            timeliness_score=5,
            communication_score=4,
            comment="Excellent travail, equipe professionnelle et ponctuelle.",
            status="published",
            submitted_at=now - timedelta(days=1),
            published_at=now - timedelta(hours=12),
            moderated_by_user_id=admin.id,
            moderated_at=now - timedelta(hours=12),
        )

        review_pending = Review(
            id=SEED_REVIEW2_ID,
            completion_confirmation_id=SEED_COMPLETION_ID,
            client_request_id=SEED_REQUEST_ID,
            company_profile_id=quote.company_profile_id,
            reviewer_user_id=admin.id,
            reviewer_type="company",
            rating=5,
            quality_score=5,
            comment="Client tres cooperatif, acces facile au chantier.",
            status="under_moderation",
            submitted_at=now - timedelta(hours=6),
        )

        db.add_all([review_published, review_pending])

        await db.commit()
        print(f"Marketplace Trust seed complete: award={SEED_AWARD_ID}")
        print(f"  Completion: {SEED_COMPLETION_ID} (fully_confirmed)")
        print("  Reviews: 2 (1 published, 1 under_moderation)")


if __name__ == "__main__":
    asyncio.run(seed())
