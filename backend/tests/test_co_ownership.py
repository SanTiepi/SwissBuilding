"""Tests for co-ownership governance module."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.co_ownership_service import (
    calculate_remediation_cost_split,
    get_building_co_ownership_info,
    get_building_decision_log,
    get_portfolio_co_ownership_summary,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session: AsyncSession) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def org_user(db_session: AsyncSession, org: Organization) -> User:
    from tests.conftest import _HASH_ADMIN

    user = User(
        id=uuid.uuid4(),
        email="orguser@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Org",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def ppe_building(db_session: AsyncSession, admin_user: User) -> Building:
    building = Building(
        id=uuid.uuid4(),
        address="Avenue de Cour 15",
        postal_code="1007",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential_multi",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def sole_building(db_session: AsyncSession, admin_user: User) -> Building:
    building = Building(
        id=uuid.uuid4(),
        address="Chemin des Vignes 3",
        postal_code="1009",
        city="Pully",
        canton="VD",
        construction_year=1985,
        building_type="residential_single",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def commercial_building(db_session: AsyncSession, admin_user: User) -> Building:
    building = Building(
        id=uuid.uuid4(),
        address="Rue du Commerce 10",
        postal_code="1003",
        city="Lausanne",
        canton="VD",
        construction_year=1960,
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def diagnostic_with_samples(db_session: AsyncSession, ppe_building: Building, admin_user: User) -> Diagnostic:
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=ppe_building.id,
        diagnostic_type="asbestos",
        status="completed",
        diagnostician_id=admin_user.id,
    )
    db_session.add(diag)
    await db_session.flush()

    for i in range(3):
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number=f"S-{i + 1}",
            pollutant_type="asbestos",
            concentration=0.5 + i,
            unit="%",
            threshold_exceeded=i > 0,  # 2 exceeded
        )
        db_session.add(sample)

    await db_session.commit()
    await db_session.refresh(diag)
    return diag


@pytest.fixture
async def action_items(db_session: AsyncSession, ppe_building: Building, admin_user: User) -> list[ActionItem]:
    statuses = ["open", "in_progress", "completed", "cancelled"]
    items: list[ActionItem] = []
    for i, status in enumerate(statuses):
        action = ActionItem(
            id=uuid.uuid4(),
            building_id=ppe_building.id,
            source_type="diagnostic",
            action_type="remediation",
            title=f"Action {i + 1}",
            description=f"Description for action {i + 1}",
            priority="high",
            status=status,
            created_by=admin_user.id,
            completed_at=datetime.now(UTC) if status in ("completed", "cancelled") else None,
        )
        db_session.add(action)
        items.append(action)
    await db_session.commit()
    return items


# ---------------------------------------------------------------------------
# Service tests — get_building_co_ownership_info
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_co_ownership_ppe_type(db_session: AsyncSession, ppe_building: Building):
    info = await get_building_co_ownership_info(ppe_building.id, db_session)
    assert info.ownership_type == "ppe"
    assert info.building_id == ppe_building.id


@pytest.mark.asyncio
async def test_co_ownership_sole_type(db_session: AsyncSession, sole_building: Building):
    info = await get_building_co_ownership_info(sole_building.id, db_session)
    assert info.ownership_type == "sole_owner"
    assert len(info.co_owners) == 1
    assert info.co_owners[0].share_percentage == 100.0


@pytest.mark.asyncio
async def test_co_ownership_cooperative_type(db_session: AsyncSession, commercial_building: Building):
    info = await get_building_co_ownership_info(commercial_building.id, db_session)
    assert info.ownership_type == "cooperative"


@pytest.mark.asyncio
async def test_co_ownership_shares_sum_100(db_session: AsyncSession, ppe_building: Building):
    info = await get_building_co_ownership_info(ppe_building.id, db_session)
    total = sum(o.share_percentage for o in info.co_owners)
    assert abs(total - 100.0) < 0.01


@pytest.mark.asyncio
async def test_co_ownership_has_president(db_session: AsyncSession, ppe_building: Building):
    info = await get_building_co_ownership_info(ppe_building.id, db_session)
    roles = [o.role for o in info.co_owners]
    assert "president" in roles


@pytest.mark.asyncio
async def test_co_ownership_quorum_50(db_session: AsyncSession, ppe_building: Building):
    info = await get_building_co_ownership_info(ppe_building.id, db_session)
    assert info.decision_quorum_pct == 50.0


@pytest.mark.asyncio
async def test_co_ownership_tenant_rep_no_vote(db_session: AsyncSession, ppe_building: Building):
    info = await get_building_co_ownership_info(ppe_building.id, db_session)
    for owner in info.co_owners:
        if owner.role == "tenant_representative":
            assert owner.voting_rights is False


@pytest.mark.asyncio
async def test_co_ownership_not_found(db_session: AsyncSession):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await get_building_co_ownership_info(uuid.uuid4(), db_session)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_co_ownership_deterministic(db_session: AsyncSession, ppe_building: Building):
    info1 = await get_building_co_ownership_info(ppe_building.id, db_session)
    info2 = await get_building_co_ownership_info(ppe_building.id, db_session)
    assert [o.owner_id for o in info1.co_owners] == [o.owner_id for o in info2.co_owners]
    assert [o.share_percentage for o in info1.co_owners] == [o.share_percentage for o in info2.co_owners]


# ---------------------------------------------------------------------------
# Service tests — calculate_remediation_cost_split
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_split_by_share(
    db_session: AsyncSession, ppe_building: Building, diagnostic_with_samples: Diagnostic
):
    split = await calculate_remediation_cost_split(ppe_building.id, db_session, method="by_share")
    assert split.total_remediation_cost == 30_000.0  # 2 exceeded * 15k
    total_allocated = sum(a.allocated_amount for a in split.allocations)
    assert abs(total_allocated - 30_000.0) < 1.0


@pytest.mark.asyncio
async def test_cost_split_equal(db_session: AsyncSession, ppe_building: Building, diagnostic_with_samples: Diagnostic):
    split = await calculate_remediation_cost_split(ppe_building.id, db_session, method="equal")
    amounts = [a.allocated_amount for a in split.allocations]
    assert len(set(amounts)) == 1  # all equal


@pytest.mark.asyncio
async def test_cost_split_no_samples(db_session: AsyncSession, ppe_building: Building):
    split = await calculate_remediation_cost_split(ppe_building.id, db_session)
    assert split.total_remediation_cost == 0.0
    assert all(a.allocated_amount == 0.0 for a in split.allocations)


@pytest.mark.asyncio
async def test_cost_split_all_pending(
    db_session: AsyncSession, ppe_building: Building, diagnostic_with_samples: Diagnostic
):
    split = await calculate_remediation_cost_split(ppe_building.id, db_session)
    assert all(a.status == "pending" for a in split.allocations)


@pytest.mark.asyncio
async def test_cost_split_method_stored(db_session: AsyncSession, ppe_building: Building):
    split = await calculate_remediation_cost_split(ppe_building.id, db_session, method="by_affected_area")
    assert split.allocation_method == "by_affected_area"


# ---------------------------------------------------------------------------
# Service tests — get_building_decision_log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decision_log_maps_statuses(
    db_session: AsyncSession, ppe_building: Building, action_items: list[ActionItem]
):
    log = await get_building_decision_log(ppe_building.id, db_session)
    statuses = {d.status for d in log.decisions}
    assert statuses == {"proposed", "voted", "approved", "rejected"}


@pytest.mark.asyncio
async def test_decision_log_counts(db_session: AsyncSession, ppe_building: Building, action_items: list[ActionItem]):
    log = await get_building_decision_log(ppe_building.id, db_session)
    assert log.total_decisions == 4
    assert log.pending_decisions == 1  # "open" → proposed


@pytest.mark.asyncio
async def test_decision_log_approval_rate(
    db_session: AsyncSession, ppe_building: Building, action_items: list[ActionItem]
):
    log = await get_building_decision_log(ppe_building.id, db_session)
    # 1 approved, 1 rejected → 0.5
    assert log.approval_rate == 0.5


@pytest.mark.asyncio
async def test_decision_log_empty(db_session: AsyncSession, ppe_building: Building):
    log = await get_building_decision_log(ppe_building.id, db_session)
    assert log.total_decisions == 0
    assert log.approval_rate == 0.0


@pytest.mark.asyncio
async def test_decision_log_not_found(db_session: AsyncSession):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await get_building_decision_log(uuid.uuid4(), db_session)


# ---------------------------------------------------------------------------
# Service tests — get_portfolio_co_ownership_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_summary_counts(db_session: AsyncSession, org: Organization, org_user: User):
    # Create buildings under org_user
    ppe = Building(
        id=uuid.uuid4(),
        address="Rue Test PPE",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential_multi",
        created_by=org_user.id,
        status="active",
    )
    sole = Building(
        id=uuid.uuid4(),
        address="Rue Test Sole",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential_single",
        created_by=org_user.id,
        status="active",
    )
    db_session.add_all([ppe, sole])
    await db_session.commit()

    summary = await get_portfolio_co_ownership_summary(org.id, db_session)
    assert summary.total_ppe_buildings == 1
    assert summary.total_sole_owner_buildings == 1


@pytest.mark.asyncio
async def test_portfolio_summary_empty_org(db_session: AsyncSession, org: Organization):
    summary = await get_portfolio_co_ownership_summary(org.id, db_session)
    assert summary.total_ppe_buildings == 0
    assert summary.total_sole_owner_buildings == 0


@pytest.mark.asyncio
async def test_portfolio_summary_nonexistent_org(db_session: AsyncSession):
    summary = await get_portfolio_co_ownership_summary(uuid.uuid4(), db_session)
    assert summary.total_ppe_buildings == 0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_co_ownership_info(client: AsyncClient, auth_headers: dict, ppe_building: Building):
    resp = await client.get(
        f"/api/v1/co-ownership/buildings/{ppe_building.id}/info",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ownership_type"] == "ppe"
    assert data["building_id"] == str(ppe_building.id)


@pytest.mark.asyncio
async def test_api_cost_split(client: AsyncClient, auth_headers: dict, ppe_building: Building):
    resp = await client.get(
        f"/api/v1/co-ownership/buildings/{ppe_building.id}/cost-split",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["allocation_method"] == "by_share"


@pytest.mark.asyncio
async def test_api_cost_split_method_param(client: AsyncClient, auth_headers: dict, ppe_building: Building):
    resp = await client.get(
        f"/api/v1/co-ownership/buildings/{ppe_building.id}/cost-split?method=equal",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["allocation_method"] == "equal"


@pytest.mark.asyncio
async def test_api_decisions(
    client: AsyncClient, auth_headers: dict, ppe_building: Building, action_items: list[ActionItem]
):
    resp = await client.get(
        f"/api/v1/co-ownership/buildings/{ppe_building.id}/decisions",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_decisions"] == 4


@pytest.mark.asyncio
async def test_api_org_summary(client: AsyncClient, auth_headers: dict, org: Organization):
    resp = await client.get(
        f"/api/v1/co-ownership/organizations/{org.id}/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_ppe_buildings" in data


@pytest.mark.asyncio
async def test_api_info_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/co-ownership/buildings/{fake_id}/info",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_unauthorized(client: AsyncClient, ppe_building: Building):
    resp = await client.get(
        f"/api/v1/co-ownership/buildings/{ppe_building.id}/info",
    )
    assert resp.status_code == 403
