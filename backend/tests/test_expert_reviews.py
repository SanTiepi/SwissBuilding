"""Tests for expert review governance API."""

import uuid

import pytest

from app.models.building import Building
from app.models.expert_review import ExpertReview


@pytest.fixture
async def building(db_session, admin_user):
    b = Building(
        id=uuid.uuid4(),
        address="Rue de Bourg 15",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        construction_year=1968,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
def review_payload(building):
    return {
        "target_type": "contradiction",
        "target_id": str(uuid.uuid4()),
        "building_id": str(building.id),
        "decision": "override",
        "confidence_level": "high",
        "justification": "Lab results confirm no asbestos in this material.",
        "override_value": {"risk_level": "low"},
        "original_value": {"risk_level": "high"},
    }


# --- Create ---


@pytest.mark.asyncio
async def test_create_review_success(client, auth_headers, building, review_payload):
    resp = await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["decision"] == "override"
    assert data["status"] == "active"
    assert data["justification"] == review_payload["justification"]
    assert data["building_id"] == str(building.id)


@pytest.mark.asyncio
async def test_create_review_agree(client, auth_headers, building, review_payload):
    review_payload["decision"] = "agree"
    resp = await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["decision"] == "agree"


@pytest.mark.asyncio
async def test_create_review_invalid_decision(client, auth_headers, building, review_payload):
    review_payload["decision"] = "invalid_decision"
    resp = await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_review_invalid_target_type(client, auth_headers, building, review_payload):
    review_payload["target_type"] = "nonexistent"
    resp = await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_review_invalid_confidence(client, auth_headers, building, review_payload):
    review_payload["confidence_level"] = "very_high"
    resp = await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)
    assert resp.status_code == 422


# --- List ---


@pytest.mark.asyncio
async def test_list_reviews_by_building(client, auth_headers, building, review_payload):
    # Create two reviews for this building
    await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)
    review_payload["decision"] = "disagree"
    await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)

    resp = await client.get(
        f"/api/v1/expert-reviews?building_id={building.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_reviews_by_target_type(client, auth_headers, building, review_payload):
    await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)
    review_payload["target_type"] = "trust_score"
    review_payload["decision"] = "agree"
    await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)

    resp = await client.get(
        "/api/v1/expert-reviews?target_type=contradiction",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["target_type"] == "contradiction"


# --- Get single ---


@pytest.mark.asyncio
async def test_get_review(client, auth_headers, building, review_payload):
    create_resp = await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)
    review_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/expert-reviews/{review_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == review_id


@pytest.mark.asyncio
async def test_get_review_not_found(client, auth_headers):
    resp = await client.get(f"/api/v1/expert-reviews/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


# --- Withdraw ---


@pytest.mark.asyncio
async def test_withdraw_review(client, auth_headers, building, review_payload):
    create_resp = await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)
    review_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/expert-reviews/{review_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "withdrawn"


@pytest.mark.asyncio
async def test_withdraw_review_not_found(client, auth_headers):
    resp = await client.delete(f"/api/v1/expert-reviews/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_withdrawn_review_excluded_from_list(client, auth_headers, building, review_payload):
    create_resp = await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)
    review_id = create_resp.json()["id"]
    await client.delete(f"/api/v1/expert-reviews/{review_id}", headers=auth_headers)

    resp = await client.get(
        f"/api/v1/expert-reviews?building_id={building.id}",
        headers=auth_headers,
    )
    assert resp.json()["total"] == 0


# --- Active overrides ---


@pytest.mark.asyncio
async def test_get_active_overrides(client, auth_headers, building, review_payload):
    # Create an override
    await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)
    # Create a non-override (agree)
    review_payload["decision"] = "agree"
    review_payload["target_id"] = str(uuid.uuid4())
    await client.post("/api/v1/expert-reviews", json=review_payload, headers=auth_headers)

    resp = await client.get(
        f"/api/v1/buildings/{building.id}/expert-overrides",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["decision"] == "override"


# --- Service-level: has_expert_override ---


@pytest.mark.asyncio
async def test_has_expert_override_true(db_session, admin_user, building):
    target_id = uuid.uuid4()
    review = ExpertReview(
        id=uuid.uuid4(),
        target_type="trust_score",
        target_id=target_id,
        building_id=building.id,
        decision="override",
        justification="Score should be higher based on recent lab results.",
        reviewed_by=admin_user.id,
        reviewer_role="admin",
        status="active",
    )
    db_session.add(review)
    await db_session.commit()

    from app.services.expert_review_service import has_expert_override

    result = await has_expert_override(db_session, "trust_score", target_id)
    assert result is True


@pytest.mark.asyncio
async def test_has_expert_override_false(db_session, admin_user, building):
    target_id = uuid.uuid4()
    # Create an "agree" review (not an override)
    review = ExpertReview(
        id=uuid.uuid4(),
        target_type="trust_score",
        target_id=target_id,
        building_id=building.id,
        decision="agree",
        justification="Score looks correct.",
        reviewed_by=admin_user.id,
        reviewer_role="admin",
        status="active",
    )
    db_session.add(review)
    await db_session.commit()

    from app.services.expert_review_service import has_expert_override

    result = await has_expert_override(db_session, "trust_score", target_id)
    assert result is False


@pytest.mark.asyncio
async def test_has_expert_override_withdrawn_not_counted(db_session, admin_user, building):
    target_id = uuid.uuid4()
    review = ExpertReview(
        id=uuid.uuid4(),
        target_type="readiness",
        target_id=target_id,
        building_id=building.id,
        decision="override",
        justification="Withdrawn override.",
        reviewed_by=admin_user.id,
        reviewer_role="admin",
        status="withdrawn",
    )
    db_session.add(review)
    await db_session.commit()

    from app.services.expert_review_service import has_expert_override

    result = await has_expert_override(db_session, "readiness", target_id)
    assert result is False
