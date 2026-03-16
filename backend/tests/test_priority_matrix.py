"""Tests for the Priority Matrix service, schemas, and API routes."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.user import User
from app.services.priority_matrix_service import (
    build_priority_matrix,
    get_critical_path_items,
    get_portfolio_priority_overview,
    suggest_quick_wins,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
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
async def org_user(db_session, org):
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
async def building_with_org(db_session, org_user):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Priorité 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def critical_action(db_session, sample_building, admin_user):
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        source_type="diagnostic",
        action_type="immediate_encapsulation",
        title="Encapsulate exposed asbestos in basement",
        description="Friable asbestos found in basement pipe insulation",
        priority="critical",
        status="open",
        due_date=datetime.now(UTC).date(),
        created_by=admin_user.id,
        metadata_json={"risk_level": "critical", "pollutant_type": "asbestos"},
    )
    db_session.add(action)
    await db_session.commit()
    await db_session.refresh(action)
    return action


@pytest.fixture
async def high_action(db_session, sample_building, admin_user):
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        source_type="diagnostic",
        action_type="suva_notification",
        title="File SUVA notification for asbestos",
        priority="high",
        status="open",
        due_date=(datetime.now(UTC) + timedelta(days=7)).date(),
        created_by=admin_user.id,
        metadata_json={"risk_level": "high"},
    )
    db_session.add(action)
    await db_session.commit()
    await db_session.refresh(action)
    return action


@pytest.fixture
async def medium_action(db_session, sample_building, admin_user):
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        source_type="diagnostic",
        action_type="monitoring_required",
        title="Schedule air monitoring in office area",
        priority="medium",
        status="open",
        created_by=admin_user.id,
        metadata_json={"risk_level": "medium"},
    )
    db_session.add(action)
    await db_session.commit()
    await db_session.refresh(action)
    return action


@pytest.fixture
async def low_action(db_session, sample_building, admin_user):
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        source_type="manual",
        action_type="further_investigation",
        title="Investigate potential PCB in window sealant",
        priority="low",
        status="open",
        created_by=admin_user.id,
    )
    db_session.add(action)
    await db_session.commit()
    await db_session.refresh(action)
    return action


@pytest.fixture
async def completed_action(db_session, sample_building, admin_user):
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        source_type="diagnostic",
        action_type="waste_classification",
        title="Classify waste type",
        priority="high",
        status="completed",
        created_by=admin_user.id,
    )
    db_session.add(action)
    await db_session.commit()
    await db_session.refresh(action)
    return action


@pytest.fixture
async def planned_intervention(db_session, sample_building, admin_user):
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        intervention_type="removal",
        title="Remove asbestos pipe insulation in basement",
        status="in_progress",
        date_start=datetime.now(UTC).date(),
        date_end=(datetime.now(UTC) + timedelta(days=14)).date(),
        created_by=admin_user.id,
    )
    db_session.add(intervention)
    await db_session.commit()
    await db_session.refresh(intervention)
    return intervention


@pytest.fixture
async def monitoring_intervention(db_session, sample_building, admin_user):
    intervention = Intervention(
        id=uuid.uuid4(),
        building_id=sample_building.id,
        intervention_type="monitoring",
        title="Air quality monitoring",
        status="planned",
        date_start=(datetime.now(UTC) + timedelta(days=30)).date(),
        created_by=admin_user.id,
    )
    db_session.add(intervention)
    await db_session.commit()
    await db_session.refresh(intervention)
    return intervention


# ---------------------------------------------------------------------------
# Service tests — FN1: build_priority_matrix
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_priority_matrix_empty_building(db_session, sample_building):
    """Matrix for a building with no actions or interventions."""
    result = await build_priority_matrix(db_session, sample_building.id)
    assert result.building_id == sample_building.id
    assert result.total_items == 0
    assert len(result.cells) == 16  # 4 urgency x 4 impact


@pytest.mark.asyncio
async def test_build_priority_matrix_not_found(db_session):
    """Raises ValueError for nonexistent building."""
    with pytest.raises(ValueError, match="not found"):
        await build_priority_matrix(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_build_priority_matrix_with_actions(
    db_session, sample_building, critical_action, high_action, medium_action, low_action
):
    """Matrix places actions into correct quadrants."""
    result = await build_priority_matrix(db_session, sample_building.id)
    assert result.total_items == 4
    # Find the immediate_critical cell
    imm_crit = [c for c in result.cells if c.urgency == "immediate" and c.impact == "critical"]
    assert len(imm_crit) == 1
    assert imm_crit[0].count >= 1


@pytest.mark.asyncio
async def test_build_priority_matrix_excludes_completed(db_session, sample_building, critical_action, completed_action):
    """Completed/closed actions should not appear in the matrix."""
    result = await build_priority_matrix(db_session, sample_building.id)
    all_ids = {item.id for cell in result.cells for item in cell.items}
    assert completed_action.id not in all_ids
    assert critical_action.id in all_ids


@pytest.mark.asyncio
async def test_build_priority_matrix_with_intervention(db_session, sample_building, planned_intervention):
    """Interventions appear in the matrix."""
    result = await build_priority_matrix(db_session, sample_building.id)
    assert result.total_items >= 1
    all_items = [item for cell in result.cells for item in cell.items]
    intervention_items = [i for i in all_items if i.item_type == "intervention"]
    assert len(intervention_items) >= 1


@pytest.mark.asyncio
async def test_build_priority_matrix_summary(db_session, sample_building, critical_action, medium_action):
    """Summary contains correct quadrant counts."""
    result = await build_priority_matrix(db_session, sample_building.id)
    assert isinstance(result.summary, dict)
    total_from_summary = sum(result.summary.values())
    assert total_from_summary == result.total_items


# ---------------------------------------------------------------------------
# Service tests — FN2: get_critical_path_items
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_critical_path_empty(db_session, sample_building):
    """No critical path items when building has no actions."""
    result = await get_critical_path_items(db_session, sample_building.id)
    assert result.building_id == sample_building.id
    assert result.total_blocking == 0
    assert result.estimated_total_days == 0


@pytest.mark.asyncio
async def test_critical_path_not_found(db_session):
    """Raises ValueError for nonexistent building."""
    with pytest.raises(ValueError, match="not found"):
        await get_critical_path_items(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_critical_path_finds_urgent_critical(db_session, sample_building, critical_action):
    """Critical action with immediate urgency appears in critical path."""
    result = await get_critical_path_items(db_session, sample_building.id)
    assert result.total_blocking >= 1
    ids = {item.id for item in result.items}
    assert critical_action.id in ids


@pytest.mark.asyncio
async def test_critical_path_has_dependencies(db_session, sample_building, critical_action):
    """Critical path items have blocking reasons and dependencies."""
    result = await get_critical_path_items(db_session, sample_building.id)
    for item in result.items:
        assert item.blocking_reason
        assert item.estimated_days > 0


@pytest.mark.asyncio
async def test_critical_path_excludes_low_priority(db_session, sample_building, low_action, medium_action):
    """Low/medium priority items don't appear in critical path."""
    result = await get_critical_path_items(db_session, sample_building.id)
    ids = {item.id for item in result.items}
    assert low_action.id not in ids
    assert medium_action.id not in ids


@pytest.mark.asyncio
async def test_critical_path_intervention(db_session, sample_building, planned_intervention):
    """In-progress removal intervention appears as critical path item."""
    result = await get_critical_path_items(db_session, sample_building.id)
    ids = {item.id for item in result.items}
    assert planned_intervention.id in ids


# ---------------------------------------------------------------------------
# Service tests — FN3: suggest_quick_wins
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quick_wins_empty(db_session, sample_building):
    """No quick wins when building has no actions."""
    result = await suggest_quick_wins(db_session, sample_building.id)
    assert result.building_id == sample_building.id
    assert result.total_quick_wins == 0


@pytest.mark.asyncio
async def test_quick_wins_not_found(db_session):
    """Raises ValueError for nonexistent building."""
    with pytest.raises(ValueError, match="not found"):
        await suggest_quick_wins(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_quick_wins_finds_low_effort(db_session, sample_building, high_action):
    """SUVA notification (1 day effort) qualifies as quick win."""
    result = await suggest_quick_wins(db_session, sample_building.id)
    assert result.total_quick_wins >= 1
    ids = {item.id for item in result.items}
    assert high_action.id in ids


@pytest.mark.asyncio
async def test_quick_wins_excludes_completed(db_session, sample_building, completed_action):
    """Completed actions don't appear as quick wins."""
    result = await suggest_quick_wins(db_session, sample_building.id)
    ids = {item.id for item in result.items}
    assert completed_action.id not in ids


@pytest.mark.asyncio
async def test_quick_wins_has_cost_benefit(db_session, sample_building, high_action):
    """Quick win items include cost/benefit assessment."""
    result = await suggest_quick_wins(db_session, sample_building.id)
    for item in result.items:
        assert item.cost_benefit
        assert item.risk_reduction in ("significant", "moderate", "minor")
        assert item.effort_days <= 7


@pytest.mark.asyncio
async def test_quick_wins_monitoring_intervention(db_session, sample_building, monitoring_intervention):
    """Monitoring intervention qualifies as quick win if impact is not low."""
    result = await suggest_quick_wins(db_session, sample_building.id)
    # monitoring_intervention has impact "low" so should NOT be a quick win
    ids = {item.id for item in result.items}
    assert monitoring_intervention.id not in ids


# ---------------------------------------------------------------------------
# Service tests — FN4: get_portfolio_priority_overview
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_overview_empty_org(db_session):
    """Empty overview for org with no users."""
    result = await get_portfolio_priority_overview(db_session, uuid.uuid4())
    assert result.building_count == 0
    assert result.total_items == 0


@pytest.mark.asyncio
async def test_portfolio_overview_with_building(db_session, org, org_user, building_with_org):
    """Portfolio overview finds buildings via org users."""
    # Add a critical action to the building
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building_with_org.id,
        source_type="diagnostic",
        action_type="immediate_encapsulation",
        title="Critical encapsulation",
        priority="critical",
        status="open",
        due_date=datetime.now(UTC).date(),
        created_by=org_user.id,
        metadata_json={"risk_level": "critical"},
    )
    db_session.add(action)
    await db_session.commit()

    result = await get_portfolio_priority_overview(db_session, org.id)
    assert result.building_count == 1
    assert result.total_items >= 1
    assert len(result.buildings_most_critical) >= 1
    assert result.buildings_most_critical[0].critical_count >= 1


@pytest.mark.asyncio
async def test_portfolio_overview_recommendations(db_session, org, org_user, building_with_org):
    """Portfolio overview includes resource allocation recommendations."""
    result = await get_portfolio_priority_overview(db_session, org.id)
    assert isinstance(result.resource_allocation, list)
    assert len(result.resource_allocation) >= 1


@pytest.mark.asyncio
async def test_portfolio_overview_quadrant_totals(db_session, org, org_user, building_with_org):
    """Quadrant totals cover all 16 combinations."""
    result = await get_portfolio_priority_overview(db_session, org.id)
    assert len(result.quadrant_totals) == 16


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_priority_matrix(client, auth_headers, sample_building):
    """GET /buildings/{id}/priority-matrix returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/priority-matrix",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)
    assert len(data["cells"]) == 16


@pytest.mark.asyncio
async def test_api_priority_matrix_404(client, auth_headers):
    """GET /buildings/{id}/priority-matrix returns 404 for unknown building."""
    resp = await client.get(
        f"/api/v1/buildings/{uuid.uuid4()}/priority-matrix",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_critical_path(client, auth_headers, sample_building):
    """GET /buildings/{id}/critical-path returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/critical-path",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_quick_wins(client, auth_headers, sample_building):
    """GET /buildings/{id}/priority-quick-wins returns 200."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/priority-quick-wins",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_portfolio_priority_overview(client, auth_headers):
    """GET /organizations/{id}/priority-overview returns 200."""
    org_id = uuid.uuid4()
    resp = await client.get(
        f"/api/v1/organizations/{org_id}/priority-overview",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["organization_id"] == str(org_id)


@pytest.mark.asyncio
async def test_api_unauthenticated(client, sample_building):
    """API routes require authentication."""
    resp = await client.get(
        f"/api/v1/buildings/{sample_building.id}/priority-matrix",
    )
    assert resp.status_code in (401, 403)
