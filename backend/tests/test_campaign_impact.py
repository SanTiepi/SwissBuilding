import uuid
from datetime import date, timedelta

import pytest

from app.models.action_item import ActionItem
from app.models.campaign import Campaign


@pytest.fixture
async def sample_campaign(db_session, admin_user, sample_building):
    """Create a campaign with a building, date range, and budget."""
    campaign = Campaign(
        id=uuid.uuid4(),
        title="Test Impact Campaign",
        campaign_type="diagnostic",
        status="active",
        priority="high",
        building_ids=[str(sample_building.id)],
        target_count=1,
        date_start=date.today() - timedelta(days=30),
        date_end=date.today() + timedelta(days=15),
        budget_chf=100_000.0,
        spent_chf=45_000.0,
        created_by=admin_user.id,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign


@pytest.fixture
async def campaign_no_actions(db_session, admin_user):
    """Campaign with no linked actions."""
    campaign = Campaign(
        id=uuid.uuid4(),
        title="Empty Campaign",
        campaign_type="inspection",
        status="draft",
        priority="low",
        building_ids=[],
        target_count=0,
        created_by=admin_user.id,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign


async def _create_action(db_session, building, campaign, status="open"):
    action = ActionItem(
        id=uuid.uuid4(),
        building_id=building.id,
        source_type="manual",
        action_type="inspection",
        title=f"Action {status}",
        status=status,
        campaign_id=campaign.id,
    )
    db_session.add(action)
    await db_session.commit()
    return action


# ---------- Service-level tests ----------


@pytest.mark.asyncio
async def test_impact_no_actions(db_session, campaign_no_actions):
    """Campaign with no actions returns zeroes."""
    from app.services.campaign_service import get_campaign_impact

    impact = await get_campaign_impact(db_session, campaign_no_actions.id)
    assert impact is not None
    assert impact.actions_total == 0
    assert impact.actions_completed == 0
    assert impact.actions_in_progress == 0
    assert impact.completion_rate == 0.0
    assert impact.velocity == 0.0
    assert impact.budget_utilization == 0.0
    assert impact.estimated_completion_date is None
    assert impact.is_at_risk is False


@pytest.mark.asyncio
async def test_impact_mixed_statuses(db_session, sample_campaign, sample_building):
    """Campaign with mixed action statuses returns correct counts."""
    from app.services.campaign_service import get_campaign_impact

    await _create_action(db_session, sample_building, sample_campaign, "done")
    await _create_action(db_session, sample_building, sample_campaign, "done")
    await _create_action(db_session, sample_building, sample_campaign, "in_progress")
    await _create_action(db_session, sample_building, sample_campaign, "open")

    impact = await get_campaign_impact(db_session, sample_campaign.id)
    assert impact is not None
    assert impact.actions_total == 4
    assert impact.actions_completed == 2
    assert impact.actions_in_progress == 1
    assert impact.completion_rate == 0.5


@pytest.mark.asyncio
async def test_impact_velocity(db_session, sample_campaign, sample_building):
    """Velocity = completed actions / days since start."""
    from app.services.campaign_service import get_campaign_impact

    # Campaign started 30 days ago
    await _create_action(db_session, sample_building, sample_campaign, "done")
    await _create_action(db_session, sample_building, sample_campaign, "done")
    await _create_action(db_session, sample_building, sample_campaign, "done")

    impact = await get_campaign_impact(db_session, sample_campaign.id)
    assert impact is not None
    # 3 completed / 30 days = 0.1
    assert impact.velocity == pytest.approx(0.1, abs=0.01)


@pytest.mark.asyncio
async def test_impact_at_risk_detection(db_session, admin_user, sample_building):
    """At-risk is True when behind schedule and < 30 days remaining."""
    from app.services.campaign_service import get_campaign_impact

    campaign = Campaign(
        id=uuid.uuid4(),
        title="At Risk Campaign",
        campaign_type="remediation",
        status="active",
        priority="critical",
        building_ids=[str(sample_building.id)],
        target_count=1,
        date_start=date.today() - timedelta(days=60),
        date_end=date.today() + timedelta(days=10),
        created_by=admin_user.id,
    )
    db_session.add(campaign)
    await db_session.commit()

    # Only 1 of 10 actions done => very behind
    for _ in range(9):
        await _create_action(db_session, sample_building, campaign, "open")
    await _create_action(db_session, sample_building, campaign, "done")

    impact = await get_campaign_impact(db_session, campaign.id)
    assert impact is not None
    assert impact.is_at_risk is True
    assert impact.days_remaining == 10


@pytest.mark.asyncio
async def test_impact_budget_utilization(db_session, sample_campaign, sample_building):
    """Budget utilization = spent / budget."""
    from app.services.campaign_service import get_campaign_impact

    # sample_campaign has budget=100k, spent=45k
    impact = await get_campaign_impact(db_session, sample_campaign.id)
    assert impact is not None
    assert impact.budget_utilization == pytest.approx(0.45, abs=0.01)


@pytest.mark.asyncio
async def test_impact_estimated_completion(db_session, sample_campaign, sample_building):
    """Estimated completion date = start + total/velocity days."""
    from app.services.campaign_service import get_campaign_impact

    await _create_action(db_session, sample_building, sample_campaign, "done")
    await _create_action(db_session, sample_building, sample_campaign, "done")
    await _create_action(db_session, sample_building, sample_campaign, "open")
    await _create_action(db_session, sample_building, sample_campaign, "open")

    impact = await get_campaign_impact(db_session, sample_campaign.id)
    assert impact is not None
    assert impact.estimated_completion_date is not None
    # 2 done in 30 days => velocity 2/30, total 4 => 4/(2/30) = 60 days from start
    expected = sample_campaign.date_start + timedelta(days=60)
    assert impact.estimated_completion_date == expected


@pytest.mark.asyncio
async def test_impact_not_found(db_session):
    """Non-existent campaign returns None."""
    from app.services.campaign_service import get_campaign_impact

    result = await get_campaign_impact(db_session, uuid.uuid4())
    assert result is None


# ---------- API-level tests ----------


@pytest.mark.asyncio
async def test_api_impact_200(client, auth_headers, sample_campaign, sample_building, db_session):
    """GET /campaigns/{id}/impact returns 200 with valid data."""
    await _create_action(db_session, sample_building, sample_campaign, "done")

    resp = await client.get(f"/api/v1/campaigns/{sample_campaign.id}/impact", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["actions_total"] == 1
    assert data["actions_completed"] == 1
    assert data["buildings_affected"] == 1
    assert "completion_rate" in data
    assert "velocity" in data
    assert "is_at_risk" in data


@pytest.mark.asyncio
async def test_api_impact_404(client, auth_headers):
    """GET /campaigns/{id}/impact returns 404 for missing campaign."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/campaigns/{fake_id}/impact", headers=auth_headers)
    assert resp.status_code == 404
