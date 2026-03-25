"""BatiConnect — Marketplace tests (service-layer + route-level)."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.api.marketplace import router as marketplace_router
from app.main import app
from app.models.company_profile import CompanyProfile
from app.models.organization import Organization
from app.services.marketplace_service import (
    check_network_eligibility,
    compute_profile_completeness,
    create_company_profile,
    create_subscription,
    get_company_profile,
    list_company_profiles,
    list_eligible_companies,
    list_verification_queue,
    review_verification,
    submit_for_verification,
    update_company_profile,
    update_subscription_status,
)

# Register marketplace router for HTTP tests (not yet in router.py hub file)
app.include_router(marketplace_router, prefix="/api/v1")


# ---- Helpers ----


async def _make_org(db) -> Organization:
    org = Organization(id=uuid.uuid4(), name=f"Test Org {uuid.uuid4().hex[:6]}", type="contractor")
    db.add(org)
    await db.flush()
    return org


async def _make_profile(db, org_id=None, **overrides) -> CompanyProfile:
    if org_id is None:
        org = await _make_org(db)
        org_id = org.id
    data = {
        "organization_id": org_id,
        "company_name": f"Test Company {uuid.uuid4().hex[:6]}",
        "contact_email": "test@example.ch",
        "work_categories": ["asbestos_removal"],
        **overrides,
    }
    return await create_company_profile(db, data)


# ---- Profile completeness ----


def test_completeness_full():
    """Fully filled profile should score near 1.0."""
    profile = CompanyProfile(
        company_name="Test SA",
        legal_form="SA",
        uid_number="CHE-123.456.789",
        address="Rue Test 1",
        city="Lausanne",
        postal_code="1000",
        canton="VD",
        contact_email="test@test.ch",
        contact_phone="+41 21 000 00 00",
        website="https://test.ch",
        description="Full description here",
        work_categories=["asbestos_removal"],
        certifications=[{"name": "SUVA"}],
        regions_served=["VD"],
        employee_count=10,
        years_experience=5,
        insurance_info={"rc_policy": "POL-001"},
    )
    score = compute_profile_completeness(profile)
    assert score >= 0.95


def test_completeness_minimal():
    """Minimal profile should score low."""
    profile = CompanyProfile(
        company_name="Minimal",
        contact_email="min@test.ch",
        work_categories=[],
    )
    score = compute_profile_completeness(profile)
    assert score <= 0.25


def test_completeness_empty_list_not_counted():
    """Empty work_categories list should not count."""
    profile = CompanyProfile(
        company_name="Test",
        contact_email="t@t.ch",
        work_categories=[],
    )
    score = compute_profile_completeness(profile)
    full = CompanyProfile(
        company_name="Test",
        contact_email="t@t.ch",
        work_categories=["asbestos_removal"],
    )
    score_full = compute_profile_completeness(full)
    assert score_full > score


# ---- Profile CRUD (service) ----


@pytest.mark.asyncio
async def test_create_profile(db_session):
    profile = await _make_profile(db_session)
    assert profile.id is not None
    assert profile.profile_completeness is not None
    assert profile.profile_completeness > 0


@pytest.mark.asyncio
async def test_get_profile(db_session):
    profile = await _make_profile(db_session)
    fetched = await get_company_profile(db_session, profile.id)
    assert fetched is not None
    assert fetched.company_name == profile.company_name


@pytest.mark.asyncio
async def test_update_profile(db_session):
    profile = await _make_profile(db_session)
    updated = await update_company_profile(db_session, profile, {"description": "Updated desc"})
    assert updated.description == "Updated desc"
    assert updated.profile_completeness is not None


@pytest.mark.asyncio
async def test_list_profiles(db_session):
    for _ in range(3):
        await _make_profile(db_session)
    items, total = await list_company_profiles(db_session)
    assert total == 3
    assert len(items) == 3


@pytest.mark.asyncio
async def test_list_profiles_filter_canton(db_session):
    await _make_profile(db_session, canton="VD")
    await _make_profile(db_session, canton="GE")
    items, total = await list_company_profiles(db_session, canton="VD")
    assert total == 1
    assert items[0].canton == "VD"


@pytest.mark.asyncio
async def test_list_profiles_filter_work_category(db_session):
    await _make_profile(db_session, work_categories=["asbestos_removal", "pcb_remediation"])
    await _make_profile(db_session, work_categories=["demolition"])
    _items, total = await list_company_profiles(db_session, work_category="asbestos_removal")
    assert total == 1


# ---- Verification workflow ----


@pytest.mark.asyncio
async def test_submit_verification(db_session):
    profile = await _make_profile(db_session)
    verif = await submit_for_verification(db_session, profile.id)
    assert verif.status == "pending"
    assert verif.verification_type == "initial"


@pytest.mark.asyncio
async def test_review_verification_approve(db_session, admin_user):
    profile = await _make_profile(db_session)
    verif = await submit_for_verification(db_session, profile.id)
    decision = {
        "status": "approved",
        "checks_performed": [{"check_type": "uid_valid", "result": "pass"}],
        "valid_until": date(2027, 12, 31),
    }
    updated = await review_verification(db_session, verif, decision, admin_user.id)
    assert updated.status == "approved"
    assert updated.verified_by_user_id == admin_user.id
    assert updated.verified_at is not None
    assert updated.valid_until == date(2027, 12, 31)


@pytest.mark.asyncio
async def test_review_verification_reject(db_session, admin_user):
    profile = await _make_profile(db_session)
    verif = await submit_for_verification(db_session, profile.id)
    decision = {
        "status": "rejected",
        "rejection_reason": "Missing insurance documentation",
    }
    updated = await review_verification(db_session, verif, decision, admin_user.id)
    assert updated.status == "rejected"
    assert updated.rejection_reason == "Missing insurance documentation"


@pytest.mark.asyncio
async def test_verification_queue(db_session):
    p1 = await _make_profile(db_session)
    p2 = await _make_profile(db_session)
    await submit_for_verification(db_session, p1.id)
    await submit_for_verification(db_session, p2.id)
    queue = await list_verification_queue(db_session)
    assert len(queue) == 2
    assert all(v.status == "pending" for v in queue)


@pytest.mark.asyncio
async def test_list_profiles_verified_only(db_session, admin_user):
    p1 = await _make_profile(db_session)
    await _make_profile(db_session)
    verif = await submit_for_verification(db_session, p1.id)
    await review_verification(
        db_session, verif, {"status": "approved", "valid_until": date(2027, 12, 31)}, admin_user.id
    )
    items, total = await list_company_profiles(db_session, verified_only=True)
    assert total == 1
    assert items[0].id == p1.id


# ---- Subscription ----


@pytest.mark.asyncio
async def test_create_subscription(db_session):
    profile = await _make_profile(db_session)
    now = datetime.now(UTC)
    sub = await create_subscription(
        db_session,
        profile.id,
        {
            "plan_type": "professional",
            "started_at": now,
            "expires_at": now + timedelta(days=365),
        },
    )
    assert sub.id is not None
    assert sub.plan_type == "professional"
    assert sub.status == "active"


@pytest.mark.asyncio
async def test_update_subscription(db_session):
    profile = await _make_profile(db_session)
    now = datetime.now(UTC)
    sub = await create_subscription(
        db_session,
        profile.id,
        {
            "plan_type": "basic",
            "started_at": now,
        },
    )
    updated = await update_subscription_status(db_session, sub, {"status": "expired"})
    assert updated.status == "expired"


# ---- Network eligibility ----


@pytest.mark.asyncio
async def test_eligibility_verified_and_active(db_session, admin_user):
    """Verified + active subscription = eligible."""
    profile = await _make_profile(db_session)
    verif = await submit_for_verification(db_session, profile.id)
    await review_verification(
        db_session, verif, {"status": "approved", "valid_until": date(2027, 12, 31)}, admin_user.id
    )
    now = datetime.now(UTC)
    await create_subscription(
        db_session,
        profile.id,
        {
            "plan_type": "professional",
            "started_at": now,
        },
    )
    result = await check_network_eligibility(db_session, profile.id)
    assert result["is_eligible"] is True
    assert result["is_verified"] is True
    assert result["has_active_subscription"] is True


@pytest.mark.asyncio
async def test_eligibility_not_verified(db_session):
    """Not verified = not eligible."""
    profile = await _make_profile(db_session)
    now = datetime.now(UTC)
    await create_subscription(
        db_session,
        profile.id,
        {
            "plan_type": "basic",
            "started_at": now,
        },
    )
    result = await check_network_eligibility(db_session, profile.id)
    assert result["is_eligible"] is False
    assert result["is_verified"] is False
    assert result["has_active_subscription"] is True


@pytest.mark.asyncio
async def test_eligibility_no_subscription(db_session, admin_user):
    """Verified but no subscription = not eligible."""
    profile = await _make_profile(db_session)
    verif = await submit_for_verification(db_session, profile.id)
    await review_verification(
        db_session, verif, {"status": "approved", "valid_until": date(2027, 12, 31)}, admin_user.id
    )
    result = await check_network_eligibility(db_session, profile.id)
    assert result["is_eligible"] is False
    assert result["is_verified"] is True
    assert result["has_active_subscription"] is False


@pytest.mark.asyncio
async def test_eligibility_expired_subscription(db_session, admin_user):
    """Verified + expired subscription = not eligible."""
    profile = await _make_profile(db_session)
    verif = await submit_for_verification(db_session, profile.id)
    await review_verification(
        db_session, verif, {"status": "approved", "valid_until": date(2027, 12, 31)}, admin_user.id
    )
    now = datetime.now(UTC)
    sub = await create_subscription(
        db_session,
        profile.id,
        {
            "plan_type": "basic",
            "started_at": now - timedelta(days=365),
        },
    )
    await update_subscription_status(db_session, sub, {"status": "expired"})
    result = await check_network_eligibility(db_session, profile.id)
    assert result["is_eligible"] is False
    assert result["has_active_subscription"] is False


@pytest.mark.asyncio
async def test_list_eligible_companies_service(db_session, admin_user):
    """Only verified + active subscription companies appear in eligible list."""
    # Eligible company
    p1 = await _make_profile(db_session)
    v1 = await submit_for_verification(db_session, p1.id)
    await review_verification(db_session, v1, {"status": "approved", "valid_until": date(2027, 12, 31)}, admin_user.id)
    now = datetime.now(UTC)
    await create_subscription(db_session, p1.id, {"plan_type": "professional", "started_at": now})

    # Non-eligible: not verified
    p2 = await _make_profile(db_session)
    await create_subscription(db_session, p2.id, {"plan_type": "basic", "started_at": now})

    # Non-eligible: no subscription
    p3 = await _make_profile(db_session)
    v3 = await submit_for_verification(db_session, p3.id)
    await review_verification(db_session, v3, {"status": "approved", "valid_until": date(2027, 12, 31)}, admin_user.id)

    items, total = await list_eligible_companies(db_session)
    assert total == 1
    assert items[0].id == p1.id


# ---- API tests ----


@pytest.mark.asyncio
async def test_api_create_company(client, auth_headers, db_session):
    org = await _make_org(db_session)
    await db_session.commit()
    payload = {
        "organization_id": str(org.id),
        "company_name": "API Test Company",
        "contact_email": "api@test.ch",
        "work_categories": ["asbestos_removal"],
    }
    resp = await client.post("/api/v1/marketplace/companies", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["company_name"] == "API Test Company"
    assert body["profile_completeness"] is not None


@pytest.mark.asyncio
async def test_api_list_companies(client, auth_headers, db_session):
    for _ in range(2):
        await _make_profile(db_session)
    await db_session.commit()
    resp = await client.get("/api/v1/marketplace/companies", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2


@pytest.mark.asyncio
async def test_api_get_company(client, auth_headers, db_session):
    profile = await _make_profile(db_session)
    await db_session.commit()
    resp = await client.get(f"/api/v1/marketplace/companies/{profile.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(profile.id)


@pytest.mark.asyncio
async def test_api_get_company_not_found(client, auth_headers):
    resp = await client.get(f"/api/v1/marketplace/companies/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_update_company(client, auth_headers, db_session):
    profile = await _make_profile(db_session)
    await db_session.commit()
    resp = await client.put(
        f"/api/v1/marketplace/companies/{profile.id}",
        json={"description": "Updated via API"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated via API"


@pytest.mark.asyncio
async def test_api_submit_verification(client, auth_headers, db_session):
    profile = await _make_profile(db_session)
    await db_session.commit()
    resp = await client.post(
        f"/api/v1/marketplace/companies/{profile.id}/verify",
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_api_verification_queue(client, auth_headers, db_session):
    profile = await _make_profile(db_session)
    await submit_for_verification(db_session, profile.id)
    await db_session.commit()
    resp = await client.get("/api/v1/marketplace/verifications/queue", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_api_decide_verification(client, auth_headers, db_session):
    profile = await _make_profile(db_session)
    verif = await submit_for_verification(db_session, profile.id)
    await db_session.commit()
    resp = await client.post(
        f"/api/v1/marketplace/verifications/{verif.id}/decide",
        json={"status": "approved", "valid_until": "2027-12-31"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_api_decide_verification_invalid_status(client, auth_headers, db_session):
    profile = await _make_profile(db_session)
    verif = await submit_for_verification(db_session, profile.id)
    await db_session.commit()
    resp = await client.post(
        f"/api/v1/marketplace/verifications/{verif.id}/decide",
        json={"status": "invalid_status"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_check_eligibility(client, auth_headers, db_session, admin_user):
    profile = await _make_profile(db_session)
    verif = await submit_for_verification(db_session, profile.id)
    await review_verification(
        db_session, verif, {"status": "approved", "valid_until": date(2027, 12, 31)}, admin_user.id
    )
    now = datetime.now(UTC)
    await create_subscription(db_session, profile.id, {"plan_type": "professional", "started_at": now})
    await db_session.commit()
    resp = await client.get(f"/api/v1/marketplace/companies/{profile.id}/eligibility", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_eligible"] is True


@pytest.mark.asyncio
async def test_api_create_subscription(client, auth_headers, db_session):
    profile = await _make_profile(db_session)
    await db_session.commit()
    now = datetime.now(UTC).isoformat()
    resp = await client.post(
        f"/api/v1/marketplace/companies/{profile.id}/subscription",
        json={"plan_type": "basic", "started_at": now},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["plan_type"] == "basic"


@pytest.mark.asyncio
async def test_api_get_subscription(client, auth_headers, db_session):
    profile = await _make_profile(db_session)
    now = datetime.now(UTC)
    await create_subscription(db_session, profile.id, {"plan_type": "professional", "started_at": now})
    await db_session.commit()
    resp = await client.get(f"/api/v1/marketplace/companies/{profile.id}/subscription", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["plan_type"] == "professional"


@pytest.mark.asyncio
async def test_api_update_subscription(client, auth_headers, db_session):
    profile = await _make_profile(db_session)
    now = datetime.now(UTC)
    sub = await create_subscription(db_session, profile.id, {"plan_type": "basic", "started_at": now})
    await db_session.commit()
    resp = await client.put(
        f"/api/v1/marketplace/subscriptions/{sub.id}",
        json={"status": "cancelled"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_api_eligible_companies(client, auth_headers, db_session, admin_user):
    # Create 1 eligible company
    profile = await _make_profile(db_session)
    verif = await submit_for_verification(db_session, profile.id)
    await review_verification(
        db_session, verif, {"status": "approved", "valid_until": date(2027, 12, 31)}, admin_user.id
    )
    now = datetime.now(UTC)
    await create_subscription(db_session, profile.id, {"plan_type": "professional", "started_at": now})
    # Create 1 non-eligible
    await _make_profile(db_session)
    await db_session.commit()
    resp = await client.get("/api/v1/marketplace/companies/eligible", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_api_unauthorized(client):
    resp = await client.get("/api/v1/marketplace/companies")
    assert resp.status_code in (401, 403)
