"""Seed data for Exchange Hardening + Contributor Gateway.

Idempotent — checks for existing rows before inserting.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contributor_gateway import (
    ContributorGatewayRequest,
    ContributorReceipt,
    ContributorSubmission,
)
from app.models.exchange_validation import ExchangeValidationReport, ExternalRelianceSignal
from app.models.partner_webhook import PartnerDeliveryAttempt, PartnerWebhookSubscription
from app.models.passport_state_diff import PassportStateDiff


async def seed_exchange_hardening(db: AsyncSession) -> dict:
    """Seed exchange hardening demo data. Returns summary of created objects."""
    from app.models.building import Building
    from app.models.import_receipt import PassportImportReceipt
    from app.models.organization import Organization
    from app.models.passport_publication import PassportPublication
    from app.models.user import User

    # Check if already seeded
    existing = await db.execute(select(PassportStateDiff).limit(1))
    if existing.scalar_one_or_none():
        return {"status": "already_seeded"}

    # Get references
    building_result = await db.execute(select(Building).limit(1))
    building = building_result.scalar_one_or_none()
    if not building:
        return {"status": "skipped", "reason": "no buildings"}

    user_result = await db.execute(select(User).limit(1))
    user = user_result.scalar_one_or_none()

    org_result = await db.execute(select(Organization).limit(1))
    org = org_result.scalar_one_or_none()

    pub_result = await db.execute(select(PassportPublication).limit(1))
    pub = pub_result.scalar_one_or_none()

    receipt_result = await db.execute(select(PassportImportReceipt).limit(1))
    receipt = receipt_result.scalar_one_or_none()

    created = {}

    # 1. PassportStateDiff
    if pub:
        diff = PassportStateDiff(
            publication_id=pub.id,
            prior_publication_id=None,
            diff_summary={
                "added_sections": ["initial_publication"],
                "removed_sections": [],
                "changed_sections": [],
            },
            sections_changed_count=1,
            computed_at=datetime.now(UTC),
        )
        db.add(diff)
        created["diff"] = 1

    # 2. ExchangeValidationReport
    if receipt:
        report = ExchangeValidationReport(
            import_receipt_id=receipt.id,
            schema_valid=True,
            contract_valid=True,
            version_valid=True,
            hash_valid=True,
            identity_safe=True,
            validation_errors=None,
            overall_status="passed",
            validated_at=datetime.now(UTC),
            validated_by_user_id=user.id if user else None,
        )
        db.add(report)
        created["validation_report"] = 1

    # 3. ExternalRelianceSignal
    if pub:
        signal = ExternalRelianceSignal(
            publication_id=pub.id,
            signal_type="acknowledged",
            partner_org_id=org.id if org else None,
            notes="Partner confirmed receipt of publication",
            recorded_at=datetime.now(UTC),
        )
        db.add(signal)
        created["reliance_signal"] = 1

    # 4. PartnerWebhookSubscription
    if org:
        webhook = PartnerWebhookSubscription(
            partner_org_id=org.id,
            endpoint_url="https://partner.example.com/webhooks/baticonnect",
            hmac_secret=secrets.token_hex(32),
            subscribed_events=["passport_publication.created", "passport_import.received"],
            is_active=True,
        )
        db.add(webhook)
        await db.flush()
        created["webhook_subscription"] = 1

        # 5. PartnerDeliveryAttempt
        attempt = PartnerDeliveryAttempt(
            subscription_id=webhook.id,
            event_type="passport_publication.created",
            idempotency_key=f"seed-{uuid.uuid4().hex[:12]}",
            payload={"event": "passport_publication.created", "building_id": str(building.id)},
            status="delivered",
            http_status=200,
            attempt_count=1,
            last_attempt_at=datetime.now(UTC),
        )
        db.add(attempt)
        created["delivery_attempt"] = 1

    # 6. ContributorGatewayRequest
    if user:
        contrib_req = ContributorGatewayRequest(
            building_id=building.id,
            contributor_type="contractor",
            scope_description="Asbestos removal completion report",
            access_token=secrets.token_urlsafe(48),
            expires_at=datetime.now(UTC) + timedelta(hours=72),
            status="open",
            created_by_user_id=user.id,
        )
        db.add(contrib_req)
        await db.flush()
        created["contributor_request"] = 1

        # 7. ContributorSubmission
        submission = ContributorSubmission(
            request_id=contrib_req.id,
            contributor_name="Sanacore AG",
            submission_type="completion_report",
            structured_data={"zones_treated": ["B1-01", "B1-02"], "method": "encapsulation"},
            notes="All zones treated per specification",
            status="pending_review",
        )
        db.add(submission)
        await db.flush()
        created["submission"] = 1

        # 8. ContributorReceipt (for a pre-accepted scenario)
        receipt_obj = ContributorReceipt(
            submission_id=submission.id,
            receipt_hash=hashlib.sha256(f"seed-receipt-{submission.id}".encode()).hexdigest(),
            accepted_at=datetime.now(UTC),
        )
        db.add(receipt_obj)
        # Mark submission as accepted for the receipt
        submission.status = "accepted"
        submission.reviewed_by_user_id = user.id
        submission.reviewed_at = datetime.now(UTC)
        created["receipt"] = 1

    await db.flush()
    return {"status": "seeded", "created": created}
