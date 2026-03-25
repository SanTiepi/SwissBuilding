"""Tests for Exchange Hardening + Contributor Gateway.

Covers: diff computation, import validation, webhook delivery, contributor flow.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contributor_gateway import (
    ContributorGatewayRequest,
    ContributorReceipt,
    ContributorSubmission,
)
from app.models.exchange_contract import ExchangeContractVersion
from app.models.exchange_validation import ExchangeValidationReport, ExternalRelianceSignal
from app.models.import_receipt import PassportImportReceipt
from app.models.organization import Organization
from app.models.partner_webhook import PartnerDeliveryAttempt, PartnerWebhookSubscription
from app.models.passport_publication import PassportPublication
from app.models.passport_state_diff import PassportStateDiff

# ---- Helpers ----


async def _make_org(db: AsyncSession) -> Organization:
    org = Organization(id=uuid.uuid4(), name="Test Org", type="diagnostic_lab")
    db.add(org)
    await db.flush()
    return org


async def _make_contract(db: AsyncSession) -> ExchangeContractVersion:
    from datetime import date

    c = ExchangeContractVersion(
        id=uuid.uuid4(),
        contract_code="BC-PASS-v1",
        version=1,
        status="active",
        audience_type="partner",
        payload_type="passport",
        effective_from=date(2026, 1, 1),
    )
    db.add(c)
    await db.flush()
    return c


async def _make_publication(db: AsyncSession, building_id: uuid.UUID, contract_id: uuid.UUID) -> PassportPublication:
    pub = PassportPublication(
        id=uuid.uuid4(),
        building_id=building_id,
        contract_version_id=contract_id,
        audience_type="partner",
        publication_type="full_passport",
        content_hash=hashlib.sha256(b"test-content").hexdigest(),
        published_at=datetime.now(UTC),
        delivery_state="published",
    )
    db.add(pub)
    await db.flush()
    return pub


async def _make_receipt(db: AsyncSession, building_id: uuid.UUID | None = None) -> PassportImportReceipt:
    receipt = PassportImportReceipt(
        id=uuid.uuid4(),
        building_id=building_id,
        source_system="partner-sys",
        contract_code="BC-PASS-v1",
        contract_version=1,
        content_hash=hashlib.sha256(b"import-content").hexdigest(),
        status="received",
    )
    db.add(receipt)
    await db.flush()
    return receipt


# ---- Model Tests ----


@pytest.mark.asyncio
async def test_passport_state_diff_create(db_session: AsyncSession, sample_building):
    contract = await _make_contract(db_session)
    pub = await _make_publication(db_session, sample_building.id, contract.id)

    diff = PassportStateDiff(
        publication_id=pub.id,
        diff_summary={"added_sections": ["test"], "removed_sections": [], "changed_sections": []},
        sections_changed_count=1,
        computed_at=datetime.now(UTC),
    )
    db_session.add(diff)
    await db_session.flush()
    assert diff.id is not None
    assert diff.sections_changed_count == 1


@pytest.mark.asyncio
async def test_validation_report_create(db_session: AsyncSession, sample_building):
    receipt = await _make_receipt(db_session, sample_building.id)
    report = ExchangeValidationReport(
        import_receipt_id=receipt.id,
        schema_valid=True,
        contract_valid=True,
        version_valid=True,
        hash_valid=True,
        identity_safe=True,
        overall_status="passed",
        validated_at=datetime.now(UTC),
    )
    db_session.add(report)
    await db_session.flush()
    assert report.overall_status == "passed"


@pytest.mark.asyncio
async def test_reliance_signal_create(db_session: AsyncSession, sample_building):
    contract = await _make_contract(db_session)
    pub = await _make_publication(db_session, sample_building.id, contract.id)

    signal = ExternalRelianceSignal(
        publication_id=pub.id,
        signal_type="consumed",
        recorded_at=datetime.now(UTC),
    )
    db_session.add(signal)
    await db_session.flush()
    assert signal.signal_type == "consumed"


@pytest.mark.asyncio
async def test_webhook_subscription_create(db_session: AsyncSession):
    org = await _make_org(db_session)
    sub = PartnerWebhookSubscription(
        partner_org_id=org.id,
        endpoint_url="https://example.com/hook",
        hmac_secret=secrets.token_hex(32),
        subscribed_events=["passport_publication.created"],
        is_active=True,
    )
    db_session.add(sub)
    await db_session.flush()
    assert sub.is_active is True


@pytest.mark.asyncio
async def test_delivery_attempt_create(db_session: AsyncSession):
    org = await _make_org(db_session)
    sub = PartnerWebhookSubscription(
        partner_org_id=org.id,
        endpoint_url="https://example.com/hook",
        hmac_secret="secret",
        subscribed_events=["*"],
    )
    db_session.add(sub)
    await db_session.flush()

    attempt = PartnerDeliveryAttempt(
        subscription_id=sub.id,
        event_type="passport_publication.created",
        idempotency_key=f"test-{uuid.uuid4().hex[:8]}",
        payload={"test": True},
        status="delivered",
        http_status=200,
        attempt_count=1,
    )
    db_session.add(attempt)
    await db_session.flush()
    assert attempt.status == "delivered"


@pytest.mark.asyncio
async def test_contributor_request_create(db_session: AsyncSession, sample_building, admin_user):
    req = ContributorGatewayRequest(
        building_id=sample_building.id,
        contributor_type="contractor",
        scope_description="Test scope",
        access_token=secrets.token_urlsafe(48),
        expires_at=datetime.now(UTC) + timedelta(hours=72),
        status="open",
        created_by_user_id=admin_user.id,
    )
    db_session.add(req)
    await db_session.flush()
    assert req.status == "open"


@pytest.mark.asyncio
async def test_contributor_submission_create(db_session: AsyncSession, sample_building, admin_user):
    req = ContributorGatewayRequest(
        building_id=sample_building.id,
        contributor_type="lab",
        access_token=secrets.token_urlsafe(48),
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        status="open",
        created_by_user_id=admin_user.id,
    )
    db_session.add(req)
    await db_session.flush()

    sub = ContributorSubmission(
        request_id=req.id,
        submission_type="lab_results",
        notes="PCB analysis results",
        status="pending_review",
    )
    db_session.add(sub)
    await db_session.flush()
    assert sub.status == "pending_review"


@pytest.mark.asyncio
async def test_contributor_receipt_create(db_session: AsyncSession, sample_building, admin_user):
    req = ContributorGatewayRequest(
        building_id=sample_building.id,
        contributor_type="contractor",
        access_token=secrets.token_urlsafe(48),
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        status="open",
        created_by_user_id=admin_user.id,
    )
    db_session.add(req)
    await db_session.flush()

    sub = ContributorSubmission(
        request_id=req.id,
        submission_type="certificate",
        status="accepted",
    )
    db_session.add(sub)
    await db_session.flush()

    receipt = ContributorReceipt(
        submission_id=sub.id,
        receipt_hash=hashlib.sha256(b"test").hexdigest(),
        accepted_at=datetime.now(UTC),
    )
    db_session.add(receipt)
    await db_session.flush()
    assert receipt.receipt_hash is not None


# ---- Service Tests ----


@pytest.mark.asyncio
async def test_compute_publication_diff(db_session: AsyncSession, sample_building):
    from app.services.exchange_hardening_service import compute_publication_diff

    contract = await _make_contract(db_session)
    pub = await _make_publication(db_session, sample_building.id, contract.id)

    diff = await compute_publication_diff(db_session, pub.id)
    assert diff.sections_changed_count == 1
    assert "initial_publication" in diff.diff_summary["added_sections"]


@pytest.mark.asyncio
async def test_compute_diff_with_prior(db_session: AsyncSession, sample_building):
    from app.services.exchange_hardening_service import compute_publication_diff

    contract = await _make_contract(db_session)
    pub1 = await _make_publication(db_session, sample_building.id, contract.id)
    pub1.published_at = datetime(2026, 1, 1, tzinfo=UTC)
    await db_session.flush()

    # Create second publication with different hash
    pub2 = PassportPublication(
        building_id=sample_building.id,
        contract_version_id=contract.id,
        audience_type="partner",
        publication_type="full_passport",
        content_hash=hashlib.sha256(b"different-content").hexdigest(),
        published_at=datetime(2026, 2, 1, tzinfo=UTC),
        delivery_state="published",
    )
    db_session.add(pub2)
    await db_session.flush()

    diff = await compute_publication_diff(db_session, pub2.id)
    assert diff.prior_publication_id == pub1.id
    assert diff.sections_changed_count == 1


@pytest.mark.asyncio
async def test_validate_import_passed(db_session: AsyncSession, sample_building):
    from app.services.exchange_hardening_service import validate_import

    receipt = await _make_receipt(db_session, sample_building.id)
    report = await validate_import(db_session, receipt.id)
    assert report.overall_status == "passed"
    assert report.schema_valid is True
    assert report.hash_valid is True


@pytest.mark.asyncio
async def test_validate_import_failed_no_building(db_session: AsyncSession):
    from app.services.exchange_hardening_service import validate_import

    receipt = await _make_receipt(db_session, building_id=None)
    report = await validate_import(db_session, receipt.id)
    # identity_safe is False when no building_id
    assert report.identity_safe is False


@pytest.mark.asyncio
async def test_validate_import_bad_hash(db_session: AsyncSession, sample_building):
    from app.services.exchange_hardening_service import validate_import

    receipt = PassportImportReceipt(
        building_id=sample_building.id,
        source_system="test",
        contract_code="BC-PASS-v1",
        contract_version=1,
        content_hash="not-a-valid-hash",
        status="received",
    )
    db_session.add(receipt)
    await db_session.flush()

    report = await validate_import(db_session, receipt.id)
    assert report.hash_valid is False
    assert report.overall_status != "passed"


@pytest.mark.asyncio
async def test_review_import(db_session: AsyncSession, sample_building, admin_user):
    from app.services.exchange_hardening_service import review_import

    receipt = await _make_receipt(db_session, sample_building.id)
    updated = await review_import(db_session, receipt.id, admin_user.id, "validated")
    assert updated.status == "validated"


@pytest.mark.asyncio
async def test_integrate_import_requires_validated(db_session: AsyncSession, sample_building, admin_user):
    from app.services.exchange_hardening_service import integrate_import

    receipt = await _make_receipt(db_session, sample_building.id)
    with pytest.raises(ValueError, match="validated"):
        await integrate_import(db_session, receipt.id, admin_user.id)


@pytest.mark.asyncio
async def test_integrate_import_success(db_session: AsyncSession, sample_building, admin_user):
    from app.services.exchange_hardening_service import integrate_import

    receipt = await _make_receipt(db_session, sample_building.id)
    receipt.status = "validated"
    await db_session.flush()

    updated = await integrate_import(db_session, receipt.id, admin_user.id)
    assert updated.status == "integrated"


@pytest.mark.asyncio
async def test_record_reliance_signal(db_session: AsyncSession, sample_building):
    from app.services.exchange_hardening_service import record_reliance_signal

    contract = await _make_contract(db_session)
    pub = await _make_publication(db_session, sample_building.id, contract.id)

    signal = await record_reliance_signal(db_session, {"publication_id": pub.id, "signal_type": "consumed"})
    assert signal.signal_type == "consumed"


# ---- Webhook Service Tests ----


@pytest.mark.asyncio
async def test_webhook_create_and_list(db_session: AsyncSession):
    from app.services.partner_webhook_service import create_subscription, list_subscriptions

    org = await _make_org(db_session)
    sub = await create_subscription(
        db_session,
        {
            "partner_org_id": org.id,
            "endpoint_url": "https://example.com/hook",
            "hmac_secret": "test-secret",
            "subscribed_events": ["passport_publication.created"],
        },
    )
    assert sub.endpoint_url == "https://example.com/hook"

    subs = await list_subscriptions(db_session, org.id)
    assert len(subs) >= 1


@pytest.mark.asyncio
async def test_webhook_delete(db_session: AsyncSession):
    from app.services.partner_webhook_service import create_subscription, delete_subscription

    org = await _make_org(db_session)
    sub = await create_subscription(
        db_session,
        {
            "partner_org_id": org.id,
            "endpoint_url": "https://example.com/hook",
            "hmac_secret": "secret",
            "subscribed_events": ["*"],
        },
    )
    deleted = await delete_subscription(db_session, sub.id)
    assert deleted is True


@pytest.mark.asyncio
async def test_webhook_deliver_event(db_session: AsyncSession):
    from app.services.partner_webhook_service import create_subscription, deliver_event

    org = await _make_org(db_session)
    await create_subscription(
        db_session,
        {
            "partner_org_id": org.id,
            "endpoint_url": "https://example.com/hook",
            "hmac_secret": "secret",
            "subscribed_events": ["passport_publication.created"],
        },
    )

    attempts = await deliver_event(db_session, "passport_publication.created", {"building_id": "test"})
    assert len(attempts) == 1
    assert attempts[0].status == "delivered"
    assert "_signature" in attempts[0].payload


@pytest.mark.asyncio
async def test_webhook_deliver_no_match(db_session: AsyncSession):
    from app.services.partner_webhook_service import create_subscription, deliver_event

    org = await _make_org(db_session)
    await create_subscription(
        db_session,
        {
            "partner_org_id": org.id,
            "endpoint_url": "https://example.com/hook",
            "hmac_secret": "secret",
            "subscribed_events": ["passport_publication.created"],
        },
    )

    # Different event type — should not match
    attempts = await deliver_event(db_session, "some.other.event", {"test": True})
    assert len(attempts) == 0


@pytest.mark.asyncio
async def test_webhook_delivery_history(db_session: AsyncSession):
    from app.services.partner_webhook_service import (
        create_subscription,
        deliver_event,
        get_delivery_history,
    )

    org = await _make_org(db_session)
    sub = await create_subscription(
        db_session,
        {
            "partner_org_id": org.id,
            "endpoint_url": "https://example.com/hook",
            "hmac_secret": "secret",
            "subscribed_events": ["*"],
        },
    )
    await deliver_event(db_session, "test.event", {"data": True})

    history = await get_delivery_history(db_session, sub.id)
    assert len(history) >= 1


# ---- Contributor Gateway Service Tests ----


@pytest.mark.asyncio
async def test_contributor_create_request(db_session: AsyncSession, sample_building, admin_user):
    from app.services.contributor_gateway_service import create_request

    req = await create_request(
        db_session,
        building_id=sample_building.id,
        contributor_type="contractor",
        created_by_user_id=admin_user.id,
        scope_description="Completion report for zone B1",
    )
    assert req.status == "open"
    assert len(req.access_token) > 20


@pytest.mark.asyncio
async def test_contributor_validate_token(db_session: AsyncSession, sample_building, admin_user):
    from app.services.contributor_gateway_service import create_request, validate_token

    req = await create_request(
        db_session,
        building_id=sample_building.id,
        contributor_type="lab",
        created_by_user_id=admin_user.id,
    )
    validated = await validate_token(db_session, req.access_token)
    assert validated is not None
    assert validated.id == req.id


@pytest.mark.asyncio
async def test_contributor_expired_token(db_session: AsyncSession, sample_building, admin_user):
    from app.services.contributor_gateway_service import validate_token

    req = ContributorGatewayRequest(
        building_id=sample_building.id,
        contributor_type="contractor",
        access_token=secrets.token_urlsafe(48),
        expires_at=datetime.now(UTC) - timedelta(hours=1),
        status="open",
        created_by_user_id=admin_user.id,
    )
    db_session.add(req)
    await db_session.flush()

    validated = await validate_token(db_session, req.access_token)
    assert validated is None


@pytest.mark.asyncio
async def test_contributor_submit(db_session: AsyncSession, sample_building, admin_user):
    from app.services.contributor_gateway_service import create_request, submit

    req = await create_request(
        db_session,
        building_id=sample_building.id,
        contributor_type="contractor",
        created_by_user_id=admin_user.id,
    )
    sub = await submit(
        db_session,
        req.access_token,
        {
            "submission_type": "completion_report",
            "notes": "All zones treated",
        },
    )
    assert sub.status == "pending_review"


@pytest.mark.asyncio
async def test_contributor_accept(db_session: AsyncSession, sample_building, admin_user):
    from app.services.contributor_gateway_service import accept_submission, create_request, submit

    req = await create_request(
        db_session,
        building_id=sample_building.id,
        contributor_type="contractor",
        created_by_user_id=admin_user.id,
    )
    sub = await submit(db_session, req.access_token, {"submission_type": "certificate"})
    receipt = await accept_submission(db_session, sub.id, admin_user.id)
    assert receipt.receipt_hash is not None
    assert len(receipt.receipt_hash) == 64


@pytest.mark.asyncio
async def test_contributor_reject(db_session: AsyncSession, sample_building, admin_user):
    from app.services.contributor_gateway_service import create_request, reject_submission, submit

    req = await create_request(
        db_session,
        building_id=sample_building.id,
        contributor_type="lab",
        created_by_user_id=admin_user.id,
    )
    sub = await submit(db_session, req.access_token, {"submission_type": "lab_results"})
    rejected = await reject_submission(db_session, sub.id, admin_user.id, "Incomplete data")
    assert rejected.status == "rejected"
    assert rejected.review_notes == "Incomplete data"


@pytest.mark.asyncio
async def test_contributor_list_pending(db_session: AsyncSession, sample_building, admin_user):
    from app.services.contributor_gateway_service import (
        create_request,
        list_pending_submissions,
        submit,
    )

    req = await create_request(
        db_session,
        building_id=sample_building.id,
        contributor_type="contractor",
        created_by_user_id=admin_user.id,
    )
    await submit(db_session, req.access_token, {"submission_type": "photo_evidence"})

    pending = await list_pending_submissions(db_session)
    assert len(pending) >= 1


# ---- Additional Service Tests ----


@pytest.mark.asyncio
async def test_webhook_wildcard_subscription(db_session: AsyncSession):
    """Wildcard subscription should match any event type."""
    from app.services.partner_webhook_service import create_subscription, deliver_event

    org = await _make_org(db_session)
    await create_subscription(
        db_session,
        {
            "partner_org_id": org.id,
            "endpoint_url": "https://example.com/hook",
            "hmac_secret": "wildcard-secret",
            "subscribed_events": ["*"],
        },
    )
    attempts = await deliver_event(db_session, "any.random.event", {"test": True})
    assert len(attempts) == 1


@pytest.mark.asyncio
async def test_contributor_full_flow(db_session: AsyncSession, sample_building, admin_user):
    """End-to-end: create request -> submit -> accept -> receipt."""
    from app.services.contributor_gateway_service import (
        accept_submission,
        create_request,
        list_pending_submissions,
        submit,
    )

    req = await create_request(
        db_session,
        building_id=sample_building.id,
        contributor_type="contractor",
        created_by_user_id=admin_user.id,
        scope_description="Full flow test",
    )

    sub = await submit(db_session, req.access_token, {"submission_type": "attestation", "notes": "Complete"})
    assert sub.status == "pending_review"

    pending = await list_pending_submissions(db_session)
    assert any(p.id == sub.id for p in pending)

    receipt = await accept_submission(db_session, sub.id, admin_user.id)
    assert receipt.receipt_hash is not None

    # After acceptance, pending list should no longer include this submission
    pending2 = await list_pending_submissions(db_session)
    assert not any(p.id == sub.id for p in pending2)


@pytest.mark.asyncio
async def test_contributor_submit_invalid_token(db_session: AsyncSession):
    """Submit with invalid token should raise ValueError."""
    from app.services.contributor_gateway_service import submit

    with pytest.raises(ValueError, match="Invalid or expired"):
        await submit(db_session, "nonexistent-token", {"submission_type": "other"})


@pytest.mark.asyncio
async def test_accept_already_accepted(db_session: AsyncSession, sample_building, admin_user):
    """Cannot accept a submission that's already accepted."""
    from app.services.contributor_gateway_service import accept_submission, create_request, submit

    req = await create_request(
        db_session,
        building_id=sample_building.id,
        contributor_type="lab",
        created_by_user_id=admin_user.id,
    )
    sub = await submit(db_session, req.access_token, {"submission_type": "lab_results"})
    await accept_submission(db_session, sub.id, admin_user.id)

    with pytest.raises(ValueError, match="not pending"):
        await accept_submission(db_session, sub.id, admin_user.id)


@pytest.mark.asyncio
async def test_review_import_invalid_decision(db_session: AsyncSession, sample_building, admin_user):
    """Invalid decision should raise ValueError."""
    from app.services.exchange_hardening_service import review_import

    receipt = await _make_receipt(db_session, sample_building.id)
    with pytest.raises(ValueError, match="Decision must be"):
        await review_import(db_session, receipt.id, admin_user.id, "invalid_decision")
