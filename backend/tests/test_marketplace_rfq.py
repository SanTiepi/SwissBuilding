"""BatiConnect — Marketplace RFQ tests (service-layer + route-level)."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.api.marketplace_rfq import router as rfq_router
from app.main import app
from app.models.building import Building
from app.models.company_profile import CompanyProfile
from app.models.company_subscription import CompanySubscription
from app.models.company_verification import CompanyVerification
from app.models.diagnostic_publication import DiagnosticReportPublication
from app.models.organization import Organization
from app.services.marketplace_rfq_service import (
    add_document,
    cancel_request,
    close_request,
    create_quote,
    create_request,
    get_quote_comparison,
    get_request_detail,
    list_requests,
    publish_request,
    send_invitations,
    submit_quote,
    withdraw_quote,
)

# Register router for HTTP tests
app.include_router(rfq_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id):
    b = Building(
        id=uuid.uuid4(),
        address="Rue Test RFQ 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
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
        source_mission_id="TEST-MISSION-001",
        match_state="auto_matched",
        match_key_type="egid",
        payload_hash="abc123def456",
        mission_type="asbestos_full",
        published_at=datetime.now(UTC),
    )
    db.add(pub)
    await db.flush()
    return pub


async def _make_org(db):
    org = Organization(id=uuid.uuid4(), name="Test Contractor Org", type="contractor")
    db.add(org)
    await db.flush()
    return org


async def _make_eligible_company(db, org_id, name="Test Co"):
    """Create a company profile with approved verification + active subscription."""
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

    verif = CompanyVerification(
        id=uuid.uuid4(),
        company_profile_id=cp.id,
        status="approved",
        verification_type="initial",
        verified_at=datetime.now(UTC),
    )
    db.add(verif)

    sub = CompanySubscription(
        id=uuid.uuid4(),
        company_profile_id=cp.id,
        plan_type="professional",
        status="active",
        started_at=datetime.now(UTC),
        is_network_eligible=True,
    )
    db.add(sub)
    await db.flush()
    return cp


async def _make_ineligible_company(db, org_id, name="Ineligible Co"):
    """Create a company profile WITHOUT verification (not eligible)."""
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


# ---------------------------------------------------------------------------
# Service: ClientRequest CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_request(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    data = {
        "building_id": building.id,
        "title": "Test RFQ",
        "work_category": "minor",
        "pollutant_types": ["asbestos"],
    }
    req = await create_request(db_session, data, requester_user_id=admin_user.id)
    assert req.id is not None
    assert req.status == "draft"
    assert req.title == "Test RFQ"


@pytest.mark.asyncio
async def test_create_request_with_all_fields(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    data = {
        "building_id": building.id,
        "title": "Full RFQ",
        "description": "Complete removal",
        "work_category": "major",
        "pollutant_types": ["asbestos", "pcb"],
        "estimated_area_m2": 500.0,
        "deadline": date(2026, 12, 31),
        "budget_indication": "100k_500k",
        "site_access_notes": "Key at reception",
    }
    req = await create_request(db_session, data, requester_user_id=admin_user.id)
    assert req.estimated_area_m2 == 500.0
    assert req.budget_indication == "100k_500k"


@pytest.mark.asyncio
async def test_list_requests_empty(db_session, admin_user):
    _items, total = await list_requests(db_session)
    assert total == 0


@pytest.mark.asyncio
async def test_list_requests_by_building(db_session, admin_user):
    b1 = await _make_building(db_session, admin_user.id)
    b2 = await _make_building(db_session, admin_user.id)
    await create_request(db_session, {"building_id": b1.id, "title": "R1", "work_category": "minor"}, admin_user.id)
    await create_request(db_session, {"building_id": b2.id, "title": "R2", "work_category": "minor"}, admin_user.id)
    _items, total = await list_requests(db_session, building_id=b1.id)
    assert total == 1


@pytest.mark.asyncio
async def test_list_requests_by_status(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    await create_request(
        db_session, {"building_id": building.id, "title": "R1", "work_category": "minor"}, admin_user.id
    )
    _items, total = await list_requests(db_session, status="draft")
    assert total == 1
    _items, total = await list_requests(db_session, status="published")
    assert total == 0


@pytest.mark.asyncio
async def test_get_request_detail(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Detail", "work_category": "minor"}, admin_user.id
    )
    detail = await get_request_detail(db_session, req.id)
    assert detail is not None
    assert detail.title == "Detail"


@pytest.mark.asyncio
async def test_get_request_detail_not_found(db_session):
    detail = await get_request_detail(db_session, uuid.uuid4())
    assert detail is None


# ---------------------------------------------------------------------------
# Service: Publish enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_without_diagnostic_fails(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "No Diag", "work_category": "minor"}, admin_user.id
    )
    with pytest.raises(ValueError, match="No valid diagnostic publication"):
        await publish_request(db_session, req.id)


@pytest.mark.asyncio
async def test_publish_with_wrong_building_diagnostic_fails(db_session, admin_user):
    b1 = await _make_building(db_session, admin_user.id)
    b2 = await _make_building(db_session, admin_user.id)
    pub = await _make_publication(db_session, b2.id)  # pub for b2
    req = await create_request(
        db_session,
        {"building_id": b1.id, "title": "Wrong", "work_category": "minor", "diagnostic_publication_id": pub.id},
        admin_user.id,
    )
    with pytest.raises(ValueError, match="No valid diagnostic publication"):
        await publish_request(db_session, req.id)


@pytest.mark.asyncio
async def test_publish_with_valid_diagnostic_succeeds(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    pub = await _make_publication(db_session, building.id)
    req = await create_request(
        db_session,
        {
            "building_id": building.id,
            "title": "Valid",
            "work_category": "minor",
            "diagnostic_publication_id": pub.id,
        },
        admin_user.id,
    )
    published = await publish_request(db_session, req.id)
    assert published.status == "published"
    assert published.published_at is not None


@pytest.mark.asyncio
async def test_publish_already_published_fails(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    pub = await _make_publication(db_session, building.id)
    req = await create_request(
        db_session,
        {"building_id": building.id, "title": "Dup", "work_category": "minor", "diagnostic_publication_id": pub.id},
        admin_user.id,
    )
    await publish_request(db_session, req.id)
    with pytest.raises(ValueError, match="Cannot publish"):
        await publish_request(db_session, req.id)


# ---------------------------------------------------------------------------
# Service: Close / Cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_published_request(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    pub = await _make_publication(db_session, building.id)
    req = await create_request(
        db_session,
        {"building_id": building.id, "title": "Close", "work_category": "minor", "diagnostic_publication_id": pub.id},
        admin_user.id,
    )
    await publish_request(db_session, req.id)
    closed = await close_request(db_session, req.id)
    assert closed.status == "closed"
    assert closed.closed_at is not None


@pytest.mark.asyncio
async def test_close_draft_fails(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Draft", "work_category": "minor"}, admin_user.id
    )
    with pytest.raises(ValueError, match="Cannot close"):
        await close_request(db_session, req.id)


@pytest.mark.asyncio
async def test_cancel_draft_request(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Cancel", "work_category": "minor"}, admin_user.id
    )
    cancelled = await cancel_request(db_session, req.id)
    assert cancelled.status == "cancelled"


@pytest.mark.asyncio
async def test_cancel_already_cancelled_fails(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Twice", "work_category": "minor"}, admin_user.id
    )
    await cancel_request(db_session, req.id)
    with pytest.raises(ValueError, match="Cannot cancel"):
        await cancel_request(db_session, req.id)


# ---------------------------------------------------------------------------
# Service: Documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_document(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Doc", "work_category": "minor"}, admin_user.id
    )
    doc = await add_document(
        db_session,
        req.id,
        {"filename": "spec.pdf", "document_type": "specification"},
        uploaded_by_user_id=admin_user.id,
    )
    assert doc.filename == "spec.pdf"
    assert doc.client_request_id == req.id


# ---------------------------------------------------------------------------
# Service: Invitations — eligibility enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_invitation_to_eligible_company(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    pub = await _make_publication(db_session, building.id)
    req = await create_request(
        db_session,
        {"building_id": building.id, "title": "Inv", "work_category": "minor", "diagnostic_publication_id": pub.id},
        admin_user.id,
    )
    org = await _make_org(db_session)
    cp = await _make_eligible_company(db_session, org.id)
    invitations = await send_invitations(db_session, req.id, [cp.id])
    assert len(invitations) == 1
    assert invitations[0].status == "pending"


@pytest.mark.asyncio
async def test_send_invitation_to_ineligible_company_fails(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Inv Fail", "work_category": "minor"}, admin_user.id
    )
    org = await _make_org(db_session)
    cp = await _make_ineligible_company(db_session, org.id)
    with pytest.raises(ValueError, match="not network-eligible"):
        await send_invitations(db_session, req.id, [cp.id])


@pytest.mark.asyncio
async def test_send_multiple_invitations(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Multi Inv", "work_category": "minor"}, admin_user.id
    )
    org1 = await _make_org(db_session)
    org2 = await _make_org(db_session)
    cp1 = await _make_eligible_company(db_session, org1.id, "Co Alpha")
    cp2 = await _make_eligible_company(db_session, org2.id, "Co Beta")
    invitations = await send_invitations(db_session, req.id, [cp1.id, cp2.id])
    assert len(invitations) == 2


# ---------------------------------------------------------------------------
# Service: Quotes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_quote(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Quote", "work_category": "minor"}, admin_user.id
    )
    org = await _make_org(db_session)
    cp = await _make_eligible_company(db_session, org.id)
    quote = await create_quote(
        db_session,
        {
            "client_request_id": req.id,
            "company_profile_id": cp.id,
            "amount_chf": Decimal("50000.00"),
            "description": "Test quote",
        },
    )
    assert quote.status == "draft"
    assert quote.amount_chf == Decimal("50000.00")


@pytest.mark.asyncio
async def test_submit_quote_computes_hash(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Q Submit", "work_category": "minor"}, admin_user.id
    )
    org = await _make_org(db_session)
    cp = await _make_eligible_company(db_session, org.id)
    quote = await create_quote(
        db_session,
        {
            "client_request_id": req.id,
            "company_profile_id": cp.id,
            "amount_chf": Decimal("45000.00"),
            "includes": ["mobilization"],
        },
    )
    submitted = await submit_quote(db_session, quote.id)
    assert submitted.status == "submitted"
    assert submitted.submitted_at is not None
    assert submitted.content_hash is not None
    assert len(submitted.content_hash) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_submit_already_submitted_fails(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Q Dup", "work_category": "minor"}, admin_user.id
    )
    org = await _make_org(db_session)
    cp = await _make_eligible_company(db_session, org.id)
    quote = await create_quote(
        db_session,
        {
            "client_request_id": req.id,
            "company_profile_id": cp.id,
            "amount_chf": Decimal("30000.00"),
        },
    )
    await submit_quote(db_session, quote.id)
    with pytest.raises(ValueError, match="Cannot submit"):
        await submit_quote(db_session, quote.id)


@pytest.mark.asyncio
async def test_withdraw_draft_quote(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Q WD", "work_category": "minor"}, admin_user.id
    )
    org = await _make_org(db_session)
    cp = await _make_eligible_company(db_session, org.id)
    quote = await create_quote(
        db_session,
        {
            "client_request_id": req.id,
            "company_profile_id": cp.id,
            "amount_chf": Decimal("20000.00"),
        },
    )
    withdrawn = await withdraw_quote(db_session, quote.id)
    assert withdrawn.status == "withdrawn"


@pytest.mark.asyncio
async def test_withdraw_submitted_quote(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Q WS", "work_category": "minor"}, admin_user.id
    )
    org = await _make_org(db_session)
    cp = await _make_eligible_company(db_session, org.id)
    quote = await create_quote(
        db_session,
        {
            "client_request_id": req.id,
            "company_profile_id": cp.id,
            "amount_chf": Decimal("25000.00"),
        },
    )
    await submit_quote(db_session, quote.id)
    withdrawn = await withdraw_quote(db_session, quote.id)
    assert withdrawn.status == "withdrawn"


@pytest.mark.asyncio
async def test_withdraw_already_withdrawn_fails(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Q WW", "work_category": "minor"}, admin_user.id
    )
    org = await _make_org(db_session)
    cp = await _make_eligible_company(db_session, org.id)
    quote = await create_quote(
        db_session,
        {
            "client_request_id": req.id,
            "company_profile_id": cp.id,
            "amount_chf": Decimal("15000.00"),
        },
    )
    await withdraw_quote(db_session, quote.id)
    with pytest.raises(ValueError, match="Cannot withdraw"):
        await withdraw_quote(db_session, quote.id)


# ---------------------------------------------------------------------------
# Service: Quote comparison — neutral, deterministic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quote_comparison_neutral_order(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Q Comp", "work_category": "minor"}, admin_user.id
    )
    org1 = await _make_org(db_session)
    org2 = await _make_org(db_session)
    cp1 = await _make_eligible_company(db_session, org1.id, "Alpha Corp")
    cp2 = await _make_eligible_company(db_session, org2.id, "Beta Corp")

    # Create and submit quotes (cp1 first, then cp2)
    q1 = await create_quote(
        db_session,
        {
            "client_request_id": req.id,
            "company_profile_id": cp1.id,
            "amount_chf": Decimal("80000.00"),
            "includes": ["mobilization"],
        },
    )
    q2 = await create_quote(
        db_session,
        {
            "client_request_id": req.id,
            "company_profile_id": cp2.id,
            "amount_chf": Decimal("60000.00"),
            "includes": ["mobilization", "waste_disposal"],
        },
    )
    await submit_quote(db_session, q1.id)
    await submit_quote(db_session, q2.id)

    comparison = await get_quote_comparison(db_session, req.id)
    assert comparison["client_request_id"] == req.id
    assert len(comparison["quotes"]) == 2
    # Sorted by submitted_at — q1 was submitted first
    assert comparison["quotes"][0]["quote_id"] == q1.id
    assert comparison["quotes"][1]["quote_id"] == q2.id
    # NO ranking, NO scoring — just data
    for entry in comparison["quotes"]:
        assert "score" not in entry
        assert "rank" not in entry
        assert "recommendation" not in entry


@pytest.mark.asyncio
async def test_quote_comparison_excludes_draft(db_session, admin_user):
    building = await _make_building(db_session, admin_user.id)
    req = await create_request(
        db_session, {"building_id": building.id, "title": "Q Exc", "work_category": "minor"}, admin_user.id
    )
    org = await _make_org(db_session)
    cp = await _make_eligible_company(db_session, org.id)
    await create_quote(
        db_session,
        {
            "client_request_id": req.id,
            "company_profile_id": cp.id,
            "amount_chf": Decimal("40000.00"),
        },
    )
    # Draft quote should not appear in comparison
    comparison = await get_quote_comparison(db_session, req.id)
    assert len(comparison["quotes"]) == 0


# ---------------------------------------------------------------------------
# API: Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_create_request(client, auth_headers, sample_building):
    resp = await client.post(
        "/api/v1/marketplace/requests",
        json={
            "building_id": str(sample_building.id),
            "title": "API RFQ",
            "work_category": "minor",
            "pollutant_types": ["asbestos"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "draft"
    assert data["title"] == "API RFQ"


@pytest.mark.asyncio
async def test_api_list_requests(client, auth_headers, sample_building):
    await client.post(
        "/api/v1/marketplace/requests",
        json={"building_id": str(sample_building.id), "title": "L1", "work_category": "minor"},
        headers=auth_headers,
    )
    resp = await client.get("/api/v1/marketplace/requests", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_api_get_request(client, auth_headers, sample_building):
    create_resp = await client.post(
        "/api/v1/marketplace/requests",
        json={"building_id": str(sample_building.id), "title": "G1", "work_category": "minor"},
        headers=auth_headers,
    )
    rid = create_resp.json()["id"]
    resp = await client.get(f"/api/v1/marketplace/requests/{rid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "G1"


@pytest.mark.asyncio
async def test_api_get_request_404(client, auth_headers):
    resp = await client.get(f"/api/v1/marketplace/requests/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_publish_without_diagnostic_400(client, auth_headers, sample_building):
    create_resp = await client.post(
        "/api/v1/marketplace/requests",
        json={"building_id": str(sample_building.id), "title": "No Diag API", "work_category": "minor"},
        headers=auth_headers,
    )
    rid = create_resp.json()["id"]
    resp = await client.post(f"/api/v1/marketplace/requests/{rid}/publish", headers=auth_headers)
    assert resp.status_code == 400
    assert "diagnostic publication" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_cancel_request(client, auth_headers, sample_building):
    create_resp = await client.post(
        "/api/v1/marketplace/requests",
        json={"building_id": str(sample_building.id), "title": "Cancel API", "work_category": "minor"},
        headers=auth_headers,
    )
    rid = create_resp.json()["id"]
    resp = await client.post(f"/api/v1/marketplace/requests/{rid}/cancel", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_api_add_document(client, auth_headers, sample_building):
    create_resp = await client.post(
        "/api/v1/marketplace/requests",
        json={"building_id": str(sample_building.id), "title": "Doc API", "work_category": "minor"},
        headers=auth_headers,
    )
    rid = create_resp.json()["id"]
    resp = await client.post(
        f"/api/v1/marketplace/requests/{rid}/documents",
        json={"filename": "plan.pdf", "document_type": "plan"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["filename"] == "plan.pdf"


@pytest.mark.asyncio
async def test_api_create_and_list_quotes(client, auth_headers, sample_building):
    create_resp = await client.post(
        "/api/v1/marketplace/requests",
        json={"building_id": str(sample_building.id), "title": "Q API", "work_category": "minor"},
        headers=auth_headers,
    )
    rid = create_resp.json()["id"]

    # We need a company profile for the quote — create via DB directly isn't easy from API test.
    # Use the API to create a quote with a random company_profile_id (FK check is off in SQLite).
    fake_cp_id = str(uuid.uuid4())
    quote_resp = await client.post(
        "/api/v1/marketplace/quotes",
        json={
            "client_request_id": rid,
            "company_profile_id": fake_cp_id,
            "amount_chf": "55000.00",
        },
        headers=auth_headers,
    )
    assert quote_resp.status_code == 201
    assert quote_resp.json()["status"] == "draft"

    # List quotes
    list_resp = await client.get(f"/api/v1/marketplace/requests/{rid}/quotes", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1
