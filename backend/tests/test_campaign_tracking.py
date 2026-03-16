"""
Tests for campaign execution tracking (per-building progress within campaigns).
"""

import uuid
from datetime import date, timedelta

import pytest

from app.models.building import Building
from app.models.campaign import Campaign
from app.schemas.campaign_tracking import BuildingStatusUpdate
from app.services.campaign_tracking_service import (
    batch_update_status,
    get_blocked_buildings,
    get_building_statuses,
    get_campaign_progress,
    get_execution_summary,
    update_building_status,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


async def _make_campaign(db, user_id, building_ids=None, **kwargs):
    bids = [str(bid) for bid in (building_ids or [])]
    defaults = {
        "id": uuid.uuid4(),
        "title": "Test Campaign",
        "campaign_type": "diagnostic_campaign",
        "status": "active",
        "created_by": user_id,
        "building_ids": bids,
        "target_count": len(bids),
        "date_start": date.today() - timedelta(days=10),
    }
    defaults.update(kwargs)
    c = Campaign(**defaults)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


class TestGetBuildingStatuses:
    """Tests for get_building_statuses."""

    @pytest.mark.asyncio
    async def test_no_tracking_data_all_not_started(self, db_session, admin_user):
        """Buildings with no tracking data should all be not_started."""
        b1 = await _make_building(db_session, admin_user.id)
        b2 = await _make_building(db_session, admin_user.id, address="Rue Test 2")
        campaign = await _make_campaign(db_session, admin_user.id, [b1.id, b2.id])

        statuses = await get_building_statuses(db_session, campaign.id)

        assert len(statuses) == 2
        for s in statuses:
            assert s.status == "not_started"
            assert s.progress_pct == 0.0
            assert s.started_at is None
            assert s.completed_at is None

    @pytest.mark.asyncio
    async def test_empty_campaign(self, db_session, admin_user):
        """Campaign with no buildings returns empty list."""
        campaign = await _make_campaign(db_session, admin_user.id, [])
        statuses = await get_building_statuses(db_session, campaign.id)
        assert statuses == []

    @pytest.mark.asyncio
    async def test_404_for_missing_campaign(self, db_session):
        """Non-existent campaign should raise 404."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_building_statuses(db_session, uuid.uuid4())
        assert exc_info.value.status_code == 404


class TestUpdateBuildingStatus:
    """Tests for update_building_status."""

    @pytest.mark.asyncio
    async def test_update_to_in_progress(self, db_session, admin_user):
        """Updating to in_progress should set started_at."""
        b = await _make_building(db_session, admin_user.id)
        campaign = await _make_campaign(db_session, admin_user.id, [b.id])

        result = await update_building_status(
            db_session,
            campaign.id,
            b.id,
            BuildingStatusUpdate(status="in_progress", progress_pct=25.0),
        )

        assert result.status == "in_progress"
        assert result.started_at is not None
        assert result.progress_pct == 25.0

    @pytest.mark.asyncio
    async def test_update_to_blocked(self, db_session, admin_user):
        """Updating to blocked should store blocker_reason."""
        b = await _make_building(db_session, admin_user.id)
        campaign = await _make_campaign(db_session, admin_user.id, [b.id])

        result = await update_building_status(
            db_session,
            campaign.id,
            b.id,
            BuildingStatusUpdate(
                status="blocked",
                blocker_reason="Access denied by tenant",
            ),
        )

        assert result.status == "blocked"
        assert result.blocker_reason == "Access denied by tenant"

    @pytest.mark.asyncio
    async def test_update_to_completed(self, db_session, admin_user):
        """Updating to completed should set completed_at and progress to 100."""
        b = await _make_building(db_session, admin_user.id)
        campaign = await _make_campaign(db_session, admin_user.id, [b.id])

        result = await update_building_status(
            db_session,
            campaign.id,
            b.id,
            BuildingStatusUpdate(status="completed"),
        )

        assert result.status == "completed"
        assert result.completed_at is not None
        assert result.progress_pct == 100.0

    @pytest.mark.asyncio
    async def test_update_with_notes(self, db_session, admin_user):
        """Notes should be persisted."""
        b = await _make_building(db_session, admin_user.id)
        campaign = await _make_campaign(db_session, admin_user.id, [b.id])

        result = await update_building_status(
            db_session,
            campaign.id,
            b.id,
            BuildingStatusUpdate(status="in_progress", notes="First visit done"),
        )

        assert result.notes == "First visit done"

    @pytest.mark.asyncio
    async def test_update_building_not_in_campaign(self, db_session, admin_user):
        """Updating a building not in the campaign should 404."""
        from fastapi import HTTPException

        b = await _make_building(db_session, admin_user.id)
        campaign = await _make_campaign(db_session, admin_user.id, [])

        with pytest.raises(HTTPException) as exc_info:
            await update_building_status(
                db_session,
                campaign.id,
                b.id,
                BuildingStatusUpdate(status="in_progress"),
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_invalid_status(self, db_session, admin_user):
        """Invalid status should 400."""
        from fastapi import HTTPException

        b = await _make_building(db_session, admin_user.id)
        campaign = await _make_campaign(db_session, admin_user.id, [b.id])

        with pytest.raises(HTTPException) as exc_info:
            await update_building_status(
                db_session,
                campaign.id,
                b.id,
                BuildingStatusUpdate(status="invalid_status"),
            )
        assert exc_info.value.status_code == 400


class TestCampaignProgress:
    """Tests for get_campaign_progress."""

    @pytest.mark.asyncio
    async def test_progress_computation(self, db_session, admin_user):
        """Progress should reflect building statuses."""
        b1 = await _make_building(db_session, admin_user.id)
        b2 = await _make_building(db_session, admin_user.id, address="Rue Test 2")
        b3 = await _make_building(db_session, admin_user.id, address="Rue Test 3")
        b4 = await _make_building(db_session, admin_user.id, address="Rue Test 4")
        campaign = await _make_campaign(db_session, admin_user.id, [b1.id, b2.id, b3.id, b4.id])

        await update_building_status(db_session, campaign.id, b1.id, BuildingStatusUpdate(status="completed"))
        await update_building_status(
            db_session,
            campaign.id,
            b2.id,
            BuildingStatusUpdate(status="in_progress", progress_pct=50.0),
        )
        await update_building_status(
            db_session,
            campaign.id,
            b3.id,
            BuildingStatusUpdate(status="blocked", blocker_reason="No access"),
        )

        progress = await get_campaign_progress(db_session, campaign.id)

        assert progress.total_buildings == 4
        assert progress.by_status.get("completed") == 1
        assert progress.by_status.get("in_progress") == 1
        assert progress.by_status.get("blocked") == 1
        assert progress.by_status.get("not_started") == 1
        assert progress.at_risk_count >= 1  # blocked counts as at_risk

    @pytest.mark.asyncio
    async def test_velocity_and_estimated_completion(self, db_session, admin_user):
        """Velocity should be computed from elapsed days and completed count."""
        b1 = await _make_building(db_session, admin_user.id)
        b2 = await _make_building(db_session, admin_user.id, address="Rue Test 2")
        campaign = await _make_campaign(
            db_session,
            admin_user.id,
            [b1.id, b2.id],
            date_start=date.today() - timedelta(days=10),
        )

        await update_building_status(db_session, campaign.id, b1.id, BuildingStatusUpdate(status="completed"))

        progress = await get_campaign_progress(db_session, campaign.id)

        assert progress.velocity_per_day is not None
        assert progress.velocity_per_day > 0
        assert progress.estimated_completion is not None

    @pytest.mark.asyncio
    async def test_progress_empty_campaign(self, db_session, admin_user):
        """Empty campaign should have 0 progress."""
        campaign = await _make_campaign(db_session, admin_user.id, [])

        progress = await get_campaign_progress(db_session, campaign.id)

        assert progress.total_buildings == 0
        assert progress.overall_progress_pct == 0.0


class TestBlockedBuildings:
    """Tests for get_blocked_buildings."""

    @pytest.mark.asyncio
    async def test_blocked_filter(self, db_session, admin_user):
        """Only blocked buildings should be returned."""
        b1 = await _make_building(db_session, admin_user.id)
        b2 = await _make_building(db_session, admin_user.id, address="Rue Test 2")
        campaign = await _make_campaign(db_session, admin_user.id, [b1.id, b2.id])

        await update_building_status(
            db_session,
            campaign.id,
            b1.id,
            BuildingStatusUpdate(status="blocked", blocker_reason="Tenant refused"),
        )
        await update_building_status(
            db_session,
            campaign.id,
            b2.id,
            BuildingStatusUpdate(status="in_progress"),
        )

        blocked = await get_blocked_buildings(db_session, campaign.id)

        assert len(blocked) == 1
        assert blocked[0].building_id == b1.id
        assert blocked[0].blocker_reason == "Tenant refused"


class TestBatchUpdate:
    """Tests for batch_update_status."""

    @pytest.mark.asyncio
    async def test_batch_update(self, db_session, admin_user):
        """Batch update should update all specified buildings."""
        b1 = await _make_building(db_session, admin_user.id)
        b2 = await _make_building(db_session, admin_user.id, address="Rue Test 2")
        b3 = await _make_building(db_session, admin_user.id, address="Rue Test 3")
        campaign = await _make_campaign(db_session, admin_user.id, [b1.id, b2.id, b3.id])

        count = await batch_update_status(db_session, campaign.id, [b1.id, b2.id], "in_progress")

        assert count == 2

        statuses = await get_building_statuses(db_session, campaign.id)
        status_map = {s.building_id: s.status for s in statuses}
        assert status_map[b1.id] == "in_progress"
        assert status_map[b2.id] == "in_progress"
        assert status_map[b3.id] == "not_started"

    @pytest.mark.asyncio
    async def test_batch_update_skips_unknown_buildings(self, db_session, admin_user):
        """Buildings not in the campaign should be silently skipped."""
        b1 = await _make_building(db_session, admin_user.id)
        campaign = await _make_campaign(db_session, admin_user.id, [b1.id])

        count = await batch_update_status(db_session, campaign.id, [b1.id, uuid.uuid4()], "completed")

        assert count == 1


class TestExecutionSummary:
    """Tests for get_execution_summary."""

    @pytest.mark.asyncio
    async def test_stale_detection(self, db_session, admin_user):
        """Buildings with no update in 7+ days should be flagged as stale."""
        b1 = await _make_building(db_session, admin_user.id)
        b2 = await _make_building(db_session, admin_user.id, address="Rue Test 2")
        campaign = await _make_campaign(
            db_session,
            admin_user.id,
            [b1.id, b2.id],
            date_start=date.today() - timedelta(days=14),
        )

        # b1: update now (not stale)
        await update_building_status(
            db_session,
            campaign.id,
            b1.id,
            BuildingStatusUpdate(status="in_progress"),
        )

        # b2: never updated, campaign started 14 days ago → stale
        summary = await get_execution_summary(db_session, campaign.id)

        assert summary.campaign_name == "Test Campaign"
        assert summary.progress.total_buildings == 2
        assert b2.id in summary.stale_buildings

    @pytest.mark.asyncio
    async def test_recent_updates(self, db_session, admin_user):
        """Recent updates should be populated."""
        b = await _make_building(db_session, admin_user.id)
        campaign = await _make_campaign(db_session, admin_user.id, [b.id])

        await update_building_status(
            db_session,
            campaign.id,
            b.id,
            BuildingStatusUpdate(status="in_progress"),
        )

        summary = await get_execution_summary(db_session, campaign.id)

        assert len(summary.recent_updates) == 1
        assert summary.recent_updates[0]["status"] == "in_progress"


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------


class TestCampaignTrackingAPI:
    """Integration tests for campaign tracking API endpoints."""

    @pytest.mark.asyncio
    async def test_get_tracking_unauthorized(self, client):
        """Unauthenticated request should return 401/403."""
        resp = await client.get(f"/api/v1/campaigns/{uuid.uuid4()}/tracking")
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_get_tracking(self, client, db_session, admin_user, auth_headers):
        """GET tracking with valid campaign should return statuses."""
        b = await _make_building(db_session, admin_user.id)
        campaign = await _make_campaign(db_session, admin_user.id, [b.id])

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/tracking",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "not_started"

    @pytest.mark.asyncio
    async def test_put_tracking(self, client, db_session, admin_user, auth_headers):
        """PUT tracking should update building status."""
        b = await _make_building(db_session, admin_user.id)
        campaign = await _make_campaign(db_session, admin_user.id, [b.id])

        resp = await client.put(
            f"/api/v1/campaigns/{campaign.id}/tracking/{b.id}",
            headers=auth_headers,
            json={"status": "in_progress", "progress_pct": 30.0},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "in_progress"
        assert data["progress_pct"] == 30.0

    @pytest.mark.asyncio
    async def test_get_progress(self, client, db_session, admin_user, auth_headers):
        """GET progress should return aggregated metrics."""
        b = await _make_building(db_session, admin_user.id)
        campaign = await _make_campaign(db_session, admin_user.id, [b.id])

        resp = await client.get(
            f"/api/v1/campaigns/{campaign.id}/tracking/progress",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_buildings"] == 1

    @pytest.mark.asyncio
    async def test_batch_update_api(self, client, db_session, admin_user, auth_headers):
        """POST batch-update should update multiple buildings."""
        b1 = await _make_building(db_session, admin_user.id)
        b2 = await _make_building(db_session, admin_user.id, address="Rue Test 2")
        campaign = await _make_campaign(db_session, admin_user.id, [b1.id, b2.id])

        resp = await client.post(
            f"/api/v1/campaigns/{campaign.id}/tracking/batch-update",
            headers=auth_headers,
            json={"building_ids": [str(b1.id), str(b2.id)], "status": "completed"},
        )

        assert resp.status_code == 200
        assert resp.json()["updated"] == 2
