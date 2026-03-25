"""BatiConnect — Marketplace Trust tests (Award, Completion, Review)."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.api.marketplace_trust import router as trust_router
from app.main import app
from app.models.building import Building
from app.models.client_request import ClientRequest
from app.models.company_profile import CompanyProfile
from app.models.completion_confirmation import CompletionConfirmation
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.organization import Organization
from app.models.quote import Quote
from app.services.marketplace_trust_service import (
    award_quote,
    confirm_completion_client,
    confirm_completion_company,
    get_award,
    get_company_rating_summary,
    get_company_reviews,
    get_completion,
    moderate_review,
    submit_review,
)

# Register router for HTTP tests
app.include_router(trust_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Trust Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1975,
        building_type="residential",
        created_by=user_id,
        status="active",
    )
    db.add(b)
    await db.flush()
    return b


async def _make_publication(db, building_id):
    pub = DiagnosticReportPublication(
        id=uuid.uuid4(),
        building_id=building_id,
        source_system="batiscan",
        source_mission_id="TRUST-TEST-001",
        match_state="auto_matched",
        match_key_type="egid",
        payload_hash="trust123",
        mission_type="asbestos_full",
        published_at=datetime.now(UTC),
    )
    db.add(pub)
    await db.flush()
    return pub


async def _make_org(db):
    org = Organization(id=uuid.uuid4(), name="Trust Test Org", type="contractor")
    db.add(org)
    await db.flush()
    return org


async def _make_company(db, org_id, name="Trust Co"):
    cp = CompanyProfile(
        id=uuid.uuid4(),
        organization_id=org_id,
        company_name=name,
        contact_email=f"{name.lower().replace(' ', '')}@test.ch",
        work_categories=["asbestos_removal"],
        is_active=True,
    )
    db.add(cp)
    await db.flush()
    return cp


async def _make_published_request(db, building_id, user_id, pub_id):
    req = ClientRequest(
        id=uuid.uuid4(),
        building_id=building_id,
        requester_user_id=user_id,
        title="Trust Test RFQ",
        work_category="major",
        status="published",
        diagnostic_publication_id=pub_id,
        published_at=datetime.now(UTC),
    )
    db.add(req)
    await db.flush()
    return req


async def _make_submitted_quote(db, request_id, company_id, amount="75000.00"):
    q = Quote(
        id=uuid.uuid4(),
        client_request_id=request_id,
        company_profile_id=company_id,
        amount_chf=Decimal(amount),
        currency="CHF",
        status="submitted",
        submitted_at=datetime.now(UTC),
        content_hash="a" * 64,
    )
    db.add(q)
    await db.flush()
    return q


async def _setup_full_context(db, user_id):
    """Create building + publication + org + company + request + quote."""
    building = await _make_building(db, user_id)
    pub = await _make_publication(db, building.id)
    org = await _make_org(db)
    company = await _make_company(db, org.id)
    req = await _make_published_request(db, building.id, user_id, pub.id)
    quote = await _make_submitted_quote(db, req.id, company.id)
    return building, req, quote, company


# ---------------------------------------------------------------------------
# Service: Award
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_award_quote_creates_award_and_completion(db_session, admin_user):
    _building, req, quote, _company = await _setup_full_context(db_session, admin_user.id)
    award = await award_quote(db_session, req.id, quote.id, admin_user.id, conditions="Test conditions")
    assert award.id is not None
    assert award.content_hash is not None
    assert len(award.content_hash) == 64
    assert award.award_amount_chf == quote.amount_chf
    assert award.conditions == "Test conditions"

    # Quote status updated
    assert quote.status == "awarded"
    # Request status updated
    assert req.status == "awarded"


@pytest.mark.asyncio
async def test_award_creates_completion_in_pending(db_session, admin_user):
    _building, req, quote, _company = await _setup_full_context(db_session, admin_user.id)
    award = await award_quote(db_session, req.id, quote.id, admin_user.id)

    result = await db_session.execute(
        select(CompletionConfirmation).where(CompletionConfirmation.award_confirmation_id == award.id)
    )
    completion = result.scalar_one_or_none()
    assert completion is not None
    assert completion.status == "pending"
    assert completion.client_confirmed is False
    assert completion.company_confirmed is False


@pytest.mark.asyncio
async def test_award_wrong_request_fails(db_session, admin_user):
    _building, _req, quote, _company = await _setup_full_context(db_session, admin_user.id)
    fake_request_id = uuid.uuid4()
    with pytest.raises(ValueError, match="does not belong"):
        await award_quote(db_session, fake_request_id, quote.id, admin_user.id)


@pytest.mark.asyncio
async def test_award_draft_quote_fails(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    pub = await _make_publication(db_session, building.id)
    org = await _make_org(db_session)
    company = await _make_company(db_session, org.id)
    req = await _make_published_request(db_session, building.id, admin_user.id, pub.id)
    # Draft quote (not submitted)
    q = Quote(
        id=uuid.uuid4(),
        client_request_id=req.id,
        company_profile_id=company.id,
        amount_chf=Decimal("50000.00"),
        currency="CHF",
        status="draft",
    )
    db_session.add(q)
    await db_session.flush()
    with pytest.raises(ValueError, match="Cannot award quote"):
        await award_quote(db_session, req.id, q.id, admin_user.id)


@pytest.mark.asyncio
async def test_award_draft_request_fails(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    org = await _make_org(db_session)
    company = await _make_company(db_session, org.id)
    req = ClientRequest(
        id=uuid.uuid4(),
        building_id=building.id,
        requester_user_id=admin_user.id,
        title="Draft Request",
        work_category="minor",
        status="draft",
    )
    db_session.add(req)
    await db_session.flush()
    q = Quote(
        id=uuid.uuid4(),
        client_request_id=req.id,
        company_profile_id=company.id,
        amount_chf=Decimal("40000.00"),
        status="submitted",
        submitted_at=datetime.now(UTC),
        content_hash="b" * 64,
    )
    db_session.add(q)
    await db_session.flush()
    with pytest.raises(ValueError, match="Cannot award request"):
        await award_quote(db_session, req.id, q.id, admin_user.id)


@pytest.mark.asyncio
async def test_get_award(db_session, admin_user):
    _building, req, quote, _company = await _setup_full_context(db_session, admin_user.id)
    award = await award_quote(db_session, req.id, quote.id, admin_user.id)
    fetched = await get_award(db_session, award.id)
    assert fetched is not None
    assert fetched.id == award.id


@pytest.mark.asyncio
async def test_get_award_not_found(db_session):
    result = await get_award(db_session, uuid.uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# Service: Completion Confirmation
# ---------------------------------------------------------------------------


async def _make_award_and_completion(db, user_id):
    _building, req, quote, company = await _setup_full_context(db, user_id)
    award = await award_quote(db, req.id, quote.id, user_id)
    result = await db.execute(
        select(CompletionConfirmation).where(CompletionConfirmation.award_confirmation_id == award.id)
    )
    completion = result.scalar_one()
    return award, completion, company, req


@pytest.mark.asyncio
async def test_confirm_client_only(db_session, admin_user):
    _award, completion, _company, _req = await _make_award_and_completion(db_session, admin_user.id)
    result = await confirm_completion_client(db_session, completion.id, admin_user.id, "Client OK")
    assert result.client_confirmed is True
    assert result.status == "client_confirmed"
    assert result.content_hash is None  # Not yet fully confirmed


@pytest.mark.asyncio
async def test_confirm_company_only(db_session, admin_user):
    _award, completion, _company, _req = await _make_award_and_completion(db_session, admin_user.id)
    result = await confirm_completion_company(db_session, completion.id, admin_user.id, "Company OK")
    assert result.company_confirmed is True
    assert result.status == "company_confirmed"


@pytest.mark.asyncio
async def test_double_confirmation_fully_confirms(db_session, admin_user):
    _award, completion, _company, _req = await _make_award_and_completion(db_session, admin_user.id)
    await confirm_completion_client(db_session, completion.id, admin_user.id)
    result = await confirm_completion_company(db_session, completion.id, admin_user.id)
    assert result.status == "fully_confirmed"
    assert result.content_hash is not None
    assert len(result.content_hash) == 64


@pytest.mark.asyncio
async def test_double_confirmation_reverse_order(db_session, admin_user):
    _award, completion, _company, _req = await _make_award_and_completion(db_session, admin_user.id)
    await confirm_completion_company(db_session, completion.id, admin_user.id)
    result = await confirm_completion_client(db_session, completion.id, admin_user.id)
    assert result.status == "fully_confirmed"


@pytest.mark.asyncio
async def test_client_double_confirm_fails(db_session, admin_user):
    _award, completion, _company, _req = await _make_award_and_completion(db_session, admin_user.id)
    await confirm_completion_client(db_session, completion.id, admin_user.id)
    with pytest.raises(ValueError, match="already confirmed"):
        await confirm_completion_client(db_session, completion.id, admin_user.id)


@pytest.mark.asyncio
async def test_company_double_confirm_fails(db_session, admin_user):
    _award, completion, _company, _req = await _make_award_and_completion(db_session, admin_user.id)
    await confirm_completion_company(db_session, completion.id, admin_user.id)
    with pytest.raises(ValueError, match="already confirmed"):
        await confirm_completion_company(db_session, completion.id, admin_user.id)


@pytest.mark.asyncio
async def test_get_completion(db_session, admin_user):
    _award, completion, _company, _req = await _make_award_and_completion(db_session, admin_user.id)
    fetched = await get_completion(db_session, completion.id)
    assert fetched is not None


@pytest.mark.asyncio
async def test_get_completion_not_found(db_session):
    result = await get_completion(db_session, uuid.uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# Service: Reviews — enforcement
# ---------------------------------------------------------------------------


async def _make_fully_confirmed(db, user_id):
    award, completion, company, req = await _make_award_and_completion(db, user_id)
    await confirm_completion_client(db, completion.id, user_id)
    await confirm_completion_company(db, completion.id, user_id)
    return award, completion, company, req


@pytest.mark.asyncio
async def test_submit_review_requires_fully_confirmed(db_session, admin_user):
    _award, completion, company, req = await _make_award_and_completion(db_session, admin_user.id)
    # Completion is still pending — review should fail
    with pytest.raises(ValueError, match="not fully confirmed"):
        await submit_review(
            db_session,
            {
                "completion_confirmation_id": completion.id,
                "client_request_id": req.id,
                "company_profile_id": company.id,
                "reviewer_type": "client",
                "rating": 4,
            },
            reviewer_user_id=admin_user.id,
        )


@pytest.mark.asyncio
async def test_submit_review_after_client_only_fails(db_session, admin_user):
    _award, completion, company, req = await _make_award_and_completion(db_session, admin_user.id)
    await confirm_completion_client(db_session, completion.id, admin_user.id)
    with pytest.raises(ValueError, match="not fully confirmed"):
        await submit_review(
            db_session,
            {
                "completion_confirmation_id": completion.id,
                "client_request_id": req.id,
                "company_profile_id": company.id,
                "reviewer_type": "client",
                "rating": 5,
            },
            reviewer_user_id=admin_user.id,
        )


@pytest.mark.asyncio
async def test_submit_review_fully_confirmed_succeeds(db_session, admin_user):
    _award, completion, company, req = await _make_fully_confirmed(db_session, admin_user.id)
    review = await submit_review(
        db_session,
        {
            "completion_confirmation_id": completion.id,
            "client_request_id": req.id,
            "company_profile_id": company.id,
            "reviewer_type": "client",
            "rating": 4,
            "quality_score": 5,
            "timeliness_score": 4,
            "communication_score": 3,
            "comment": "Good work",
        },
        reviewer_user_id=admin_user.id,
    )
    assert review.id is not None
    assert review.status == "submitted"
    assert review.submitted_at is not None
    assert review.rating == 4


# ---------------------------------------------------------------------------
# Service: Review moderation
# ---------------------------------------------------------------------------


async def _make_submitted_review(db, user_id):
    _award, completion, company, req = await _make_fully_confirmed(db, user_id)
    review = await submit_review(
        db,
        {
            "completion_confirmation_id": completion.id,
            "client_request_id": req.id,
            "company_profile_id": company.id,
            "reviewer_type": "client",
            "rating": 4,
            "comment": "Test review",
        },
        reviewer_user_id=user_id,
    )
    return review, company


@pytest.mark.asyncio
async def test_moderate_approve(db_session, admin_user):
    review, _company = await _make_submitted_review(db_session, admin_user.id)
    result = await moderate_review(db_session, review.id, admin_user.id, "approve", notes="Looks good")
    assert result.status == "published"
    assert result.published_at is not None
    assert result.moderated_by_user_id == admin_user.id


@pytest.mark.asyncio
async def test_moderate_reject(db_session, admin_user):
    review, _company = await _make_submitted_review(db_session, admin_user.id)
    result = await moderate_review(db_session, review.id, admin_user.id, "reject", rejection_reason="Inappropriate")
    assert result.status == "rejected"
    assert result.rejection_reason == "Inappropriate"


@pytest.mark.asyncio
async def test_moderate_already_published_fails(db_session, admin_user):
    review, _company = await _make_submitted_review(db_session, admin_user.id)
    await moderate_review(db_session, review.id, admin_user.id, "approve")
    with pytest.raises(ValueError, match="Cannot moderate"):
        await moderate_review(db_session, review.id, admin_user.id, "reject")


@pytest.mark.asyncio
async def test_moderate_invalid_decision(db_session, admin_user):
    review, _company = await _make_submitted_review(db_session, admin_user.id)
    with pytest.raises(ValueError, match="Invalid decision"):
        await moderate_review(db_session, review.id, admin_user.id, "maybe")


# ---------------------------------------------------------------------------
# Service: Company reviews / rating summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_company_reviews_only_published(db_session, admin_user):
    review, company = await _make_submitted_review(db_session, admin_user.id)
    # Before approval — no published reviews
    reviews = await get_company_reviews(db_session, company.id)
    assert len(reviews) == 0

    # Approve
    await moderate_review(db_session, review.id, admin_user.id, "approve")
    reviews = await get_company_reviews(db_session, company.id)
    assert len(reviews) == 1
    assert reviews[0].status == "published"


@pytest.mark.asyncio
async def test_rating_summary_empty(db_session, admin_user):
    org = await _make_org(db_session)
    company = await _make_company(db_session, org.id)
    summary = await get_company_rating_summary(db_session, company.id)
    assert summary["total_reviews"] == 0
    assert summary["average_rating"] is None


@pytest.mark.asyncio
async def test_rating_summary_with_published_review(db_session, admin_user):
    review, company = await _make_submitted_review(db_session, admin_user.id)
    await moderate_review(db_session, review.id, admin_user.id, "approve")
    summary = await get_company_rating_summary(db_session, company.id)
    assert summary["total_reviews"] == 1
    assert summary["average_rating"] == 4.0
    assert summary["rating_breakdown"]["4"] == 1


# ---------------------------------------------------------------------------
# API: Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_award_quote(client, auth_headers, sample_building):
    # Create request
    req_resp = await client.post(
        "/api/v1/marketplace/requests",
        json={
            "building_id": str(sample_building.id),
            "title": "Award API Test",
            "work_category": "major",
        },
        headers=auth_headers,
    )
    rid = req_resp.json()["id"]

    # Create quote (SQLite doesn't enforce FK)
    fake_cp_id = str(uuid.uuid4())
    quote_resp = await client.post(
        "/api/v1/marketplace/quotes",
        json={
            "client_request_id": rid,
            "company_profile_id": fake_cp_id,
            "amount_chf": "65000.00",
        },
        headers=auth_headers,
    )
    qid = quote_resp.json()["id"]

    # Submit quote
    await client.post(f"/api/v1/marketplace/quotes/{qid}/submit", headers=auth_headers)

    # Publish request (will fail in real DB because no diagnostic, but SQLite FK off)
    # Instead, award from draft status also fails — we test the validation
    resp = await client.post(
        f"/api/v1/marketplace/requests/{rid}/award",
        json={"quote_id": qid},
        headers=auth_headers,
    )
    # Draft request → 400
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_get_award_404(client, auth_headers):
    resp = await client.get(f"/api/v1/marketplace/awards/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_get_completion_404(client, auth_headers):
    resp = await client.get(f"/api/v1/marketplace/completions/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_submit_review_without_completion_400(client, auth_headers):
    resp = await client.post(
        "/api/v1/marketplace/reviews",
        json={
            "completion_confirmation_id": str(uuid.uuid4()),
            "client_request_id": str(uuid.uuid4()),
            "company_profile_id": str(uuid.uuid4()),
            "reviewer_type": "client",
            "rating": 4,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_get_company_reviews_empty(client, auth_headers):
    resp = await client.get(
        f"/api/v1/marketplace/companies/{uuid.uuid4()}/reviews",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_api_rating_summary_empty(client, auth_headers):
    resp = await client.get(
        f"/api/v1/marketplace/companies/{uuid.uuid4()}/rating-summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_reviews"] == 0


@pytest.mark.asyncio
async def test_api_moderate_review_404(client, auth_headers):
    resp = await client.post(
        f"/api/v1/marketplace/reviews/{uuid.uuid4()}/moderate",
        json={"decision": "approve"},
        headers=auth_headers,
    )
    assert resp.status_code == 400  # ValueError from service


@pytest.mark.asyncio
async def test_api_pending_reviews(client, auth_headers):
    resp = await client.get("/api/v1/marketplace/reviews/pending", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_api_link_building_404(client, auth_headers):
    resp = await client.post(
        f"/api/v1/marketplace/awards/{uuid.uuid4()}/link-building",
        headers=auth_headers,
    )
    assert resp.status_code == 400  # Award not found
