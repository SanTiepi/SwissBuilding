import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.organization import Organization
from app.models.user import User


@pytest.fixture
async def org_a(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="Org Alpha",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def org_b(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="Org Beta",
        type="diagnostic_lab",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def org_c(db_session):
    org = Organization(
        id=uuid.uuid4(),
        name="Org Charlie",
        type="authority",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def owner_in_org_a(db_session, org_a):
    from tests.conftest import _HASH_OWNER

    user = User(
        id=uuid.uuid4(),
        email="owner_a@test.ch",
        password_hash=_HASH_OWNER,
        first_name="Owner",
        last_name="A",
        role="owner",
        organization_id=org_a.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def owner_in_org_b(db_session, org_b):
    from tests.conftest import _HASH_OWNER

    user = User(
        id=uuid.uuid4(),
        email="owner_b@test.ch",
        password_hash=_HASH_OWNER,
        first_name="Owner",
        last_name="B",
        role="owner",
        organization_id=org_b.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def buildings_org_a(db_session, owner_in_org_a):
    buildings = []
    for i in range(3):
        b = Building(
            id=uuid.uuid4(),
            address=f"Rue A {i}",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            construction_year=1960 + i,
            building_type="residential",
            created_by=owner_in_org_a.id,
            owner_id=owner_in_org_a.id,
            status="active",
        )
        db_session.add(b)
        buildings.append(b)
    await db_session.commit()
    for b in buildings:
        await db_session.refresh(b)
    return buildings


@pytest.fixture
async def buildings_org_b(db_session, owner_in_org_b):
    buildings = []
    for i in range(2):
        b = Building(
            id=uuid.uuid4(),
            address=f"Rue B {i}",
            postal_code="1200",
            city="Geneve",
            canton="GE",
            construction_year=1970 + i,
            building_type="commercial",
            created_by=owner_in_org_b.id,
            owner_id=owner_in_org_b.id,
            status="active",
        )
        db_session.add(b)
        buildings.append(b)
    await db_session.commit()
    for b in buildings:
        await db_session.refresh(b)
    return buildings


@pytest.fixture
async def risk_scores_org_a(db_session, buildings_org_a):
    scores = []
    levels = ["low", "medium", "high"]
    for i, b in enumerate(buildings_org_a):
        s = BuildingRiskScore(
            id=uuid.uuid4(),
            building_id=b.id,
            overall_risk_level=levels[i],
            confidence=0.5 + i * 0.1,
        )
        db_session.add(s)
        scores.append(s)
    await db_session.commit()
    return scores


@pytest.fixture
async def risk_scores_org_b(db_session, buildings_org_b):
    scores = []
    for b in buildings_org_b:
        s = BuildingRiskScore(
            id=uuid.uuid4(),
            building_id=b.id,
            overall_risk_level="critical",
            confidence=0.9,
        )
        db_session.add(s)
        scores.append(s)
    await db_session.commit()
    return scores


@pytest.fixture
async def actions_org_a(db_session, buildings_org_a, admin_user):
    # 2 pending (open), 1 critical
    a1 = ActionItem(
        id=uuid.uuid4(),
        building_id=buildings_org_a[0].id,
        source_type="diagnostic",
        action_type="remediation",
        title="Fix asbestos",
        priority="critical",
        status="open",
    )
    a2 = ActionItem(
        id=uuid.uuid4(),
        building_id=buildings_org_a[1].id,
        source_type="diagnostic",
        action_type="inspection",
        title="Inspect PCB",
        priority="medium",
        status="in_progress",
    )
    a3 = ActionItem(
        id=uuid.uuid4(),
        building_id=buildings_org_a[2].id,
        source_type="diagnostic",
        action_type="monitoring",
        title="Done action",
        priority="low",
        status="completed",
    )
    db_session.add_all([a1, a2, a3])
    await db_session.commit()
    return [a1, a2, a3]


def _make_headers(user):
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ---- Tests ----


@pytest.mark.asyncio
async def test_dashboard_no_orgs(client, admin_user, auth_headers):
    """Dashboard with no organizations returns empty."""
    resp = await client.get("/api/v1/multi-org/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_organizations"] == 0
    assert data["total_buildings"] == 0
    assert data["organizations"] == []


@pytest.mark.asyncio
async def test_dashboard_single_org_no_buildings(client, admin_user, auth_headers, org_a):
    """Dashboard with a single org that has no buildings."""
    resp = await client.get(f"/api/v1/multi-org/dashboard?org_ids={org_a.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_organizations"] == 1
    assert data["total_buildings"] == 0
    assert data["organizations"][0]["building_count"] == 0


@pytest.mark.asyncio
async def test_dashboard_single_org_with_buildings(
    client, admin_user, auth_headers, org_a, buildings_org_a, risk_scores_org_a, actions_org_a
):
    """Dashboard with a single org that has buildings, risk scores, and actions."""
    resp = await client.get(f"/api/v1/multi-org/dashboard?org_ids={org_a.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_organizations"] == 1
    assert data["total_buildings"] == 3
    org = data["organizations"][0]
    assert org["building_count"] == 3
    assert org["risk_distribution"]["low"] == 1
    assert org["risk_distribution"]["medium"] == 1
    assert org["risk_distribution"]["high"] == 1
    assert org["actions_pending"] == 2
    assert org["actions_critical"] == 1


@pytest.mark.asyncio
async def test_dashboard_multiple_orgs(
    client,
    admin_user,
    auth_headers,
    org_a,
    org_b,
    buildings_org_a,
    buildings_org_b,
    risk_scores_org_a,
    risk_scores_org_b,
):
    """Dashboard aggregates across multiple organizations."""
    resp = await client.get(f"/api/v1/multi-org/dashboard?org_ids={org_a.id},{org_b.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_organizations"] == 2
    assert data["total_buildings"] == 5
    assert data["global_risk_distribution"]["critical"] == 2
    assert data["global_risk_distribution"]["low"] == 1


@pytest.mark.asyncio
async def test_dashboard_all_orgs(client, admin_user, auth_headers, org_a, org_b, buildings_org_a, buildings_org_b):
    """Dashboard without org_ids returns all organizations."""
    resp = await client.get("/api/v1/multi-org/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_organizations"] >= 2


@pytest.mark.asyncio
async def test_dashboard_invalid_uuid(client, admin_user, auth_headers):
    """Dashboard with invalid UUID returns 422."""
    resp = await client.get("/api/v1/multi-org/dashboard?org_ids=not-a-uuid", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_dashboard_nonexistent_org(client, admin_user, auth_headers):
    """Dashboard with non-existent org returns empty results."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/multi-org/dashboard?org_ids={fake_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_organizations"] == 0


@pytest.mark.asyncio
async def test_compare_two_orgs(
    client,
    admin_user,
    auth_headers,
    org_a,
    org_b,
    buildings_org_a,
    buildings_org_b,
    risk_scores_org_a,
    risk_scores_org_b,
):
    """Compare two organizations returns items for all default metrics."""
    resp = await client.get(f"/api/v1/multi-org/compare?org_ids={org_a.id},{org_b.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["metric_names"]) == 4
    # 2 orgs x 4 metrics = 8 items
    assert len(data["items"]) == 8


@pytest.mark.asyncio
async def test_compare_with_metric_filter(
    client, admin_user, auth_headers, org_a, org_b, buildings_org_a, buildings_org_b
):
    """Compare with specific metrics filters the result."""
    resp = await client.get(
        f"/api/v1/multi-org/compare?org_ids={org_a.id},{org_b.id}&metrics=building_count",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["metric_names"] == ["building_count"]
    assert len(data["items"]) == 2
    for item in data["items"]:
        assert item["metric_name"] == "building_count"


@pytest.mark.asyncio
async def test_compare_single_org_rejected(client, admin_user, auth_headers, org_a):
    """Compare with fewer than 2 org IDs returns 422."""
    resp = await client.get(f"/api/v1/multi-org/compare?org_ids={org_a.id}", headers=auth_headers)
    assert resp.status_code == 422
    assert "At least 2" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_compare_missing_org_ids(client, admin_user, auth_headers):
    """Compare without org_ids param returns 422."""
    resp = await client.get("/api/v1/multi-org/compare", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_compare_invalid_uuid(client, admin_user, auth_headers):
    """Compare with invalid UUID returns 422."""
    resp = await client.get("/api/v1/multi-org/compare?org_ids=bad,worse", headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_compare_invalid_metric_falls_back(client, admin_user, auth_headers, org_a, org_b):
    """Compare with only invalid metrics falls back to all available metrics."""
    resp = await client.get(
        f"/api/v1/multi-org/compare?org_ids={org_a.id},{org_b.id}&metrics=nonexistent",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["metric_names"]) == 4


@pytest.mark.asyncio
async def test_dashboard_forbidden_for_owner(client, owner_user, owner_headers):
    """Owner role should not have organizations:list permission."""
    resp = await client.get("/api/v1/multi-org/dashboard", headers=owner_headers)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_compare_forbidden_for_owner(client, owner_user, owner_headers, org_a, org_b):
    """Owner role should not have organizations:list permission for compare."""
    resp = await client.get(f"/api/v1/multi-org/compare?org_ids={org_a.id},{org_b.id}", headers=owner_headers)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_dashboard_global_completeness_weighted(
    client,
    admin_user,
    auth_headers,
    org_a,
    org_b,
    buildings_org_a,
    buildings_org_b,
    risk_scores_org_a,
    risk_scores_org_b,
):
    """Global completeness is weighted average by building count."""
    resp = await client.get(f"/api/v1/multi-org/dashboard?org_ids={org_a.id},{org_b.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Org A: 3 buildings, confidence [0.5, 0.6, 0.7] → avg 0.6
    # Org B: 2 buildings, confidence [0.9, 0.9] → avg 0.9
    # Weighted: (0.6*3 + 0.9*2) / 5 = 3.6/5 = 0.72
    assert data["global_completeness_avg"] == 0.72


@pytest.mark.asyncio
async def test_compare_three_orgs(client, admin_user, auth_headers, org_a, org_b, org_c):
    """Compare works with 3 organizations."""
    resp = await client.get(
        f"/api/v1/multi-org/compare?org_ids={org_a.id},{org_b.id},{org_c.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # 3 orgs x 4 metrics = 12 items
    assert len(data["items"]) == 12
