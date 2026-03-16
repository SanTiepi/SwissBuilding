"""Tests for portfolio summary aggregate service and API endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_risk_score import BuildingRiskScore
from app.models.building_snapshot import BuildingSnapshot
from app.models.campaign import Campaign
from app.models.change_signal import ChangeSignal
from app.models.diagnostic import Diagnostic
from app.models.document import Document
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.unknown_issue import UnknownIssue
from app.models.user import User
from app.services.portfolio_summary_service import (
    get_portfolio_comparison,
    get_portfolio_health_score,
    get_portfolio_summary,
)

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(org_id=None, role="admin"):
    return User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash="$2b$12$LJ3m4ys3Lz0YEMPqhc8pFOb5VgnXBSPHEK.5GV5eJVXf6g5lyOzS",
        first_name="Test",
        last_name="User",
        role=role,
        is_active=True,
        language="fr",
        organization_id=org_id,
    )


def _make_building(created_by_id, status="active"):
    return Building(
        id=uuid.uuid4(),
        address=f"Rue {uuid.uuid4().hex[:6]}",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1970,
        building_type="residential",
        created_by=created_by_id,
        status=status,
    )


def _make_org(name="Org"):
    return Organization(
        id=uuid.uuid4(),
        name=name,
        type="property_management",
    )


def _auth_headers(user):
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


async def test_empty_portfolio(db_session: AsyncSession):
    """Empty portfolio returns all zeros."""
    summary = await get_portfolio_summary(db_session)
    assert summary.overview.total_buildings == 0
    assert summary.overview.total_diagnostics == 0
    assert summary.risk.avg_risk_score is None
    assert summary.compliance.unknown_count == 0
    assert summary.readiness.unknown_count == 0
    assert summary.grades.by_grade["A"] == 0
    assert summary.actions.total_open == 0
    assert summary.alerts.total_weak_signals == 0
    assert summary.generated_at is not None
    assert summary.organization_id is None


async def test_portfolio_building_counts(db_session: AsyncSession):
    """Counts buildings, diagnostics, interventions, documents."""
    user = _make_user()
    db_session.add(user)
    await db_session.flush()

    b1 = _make_building(user.id)
    b2 = _make_building(user.id)
    b_inactive = _make_building(user.id, status="archived")
    db_session.add_all([b1, b2, b_inactive])
    await db_session.flush()

    db_session.add(Diagnostic(id=uuid.uuid4(), building_id=b1.id, diagnostic_type="asbestos"))
    db_session.add(Diagnostic(id=uuid.uuid4(), building_id=b2.id, diagnostic_type="pcb"))
    db_session.add(Intervention(id=uuid.uuid4(), building_id=b1.id, intervention_type="removal", title="Remove"))
    db_session.add(Document(id=uuid.uuid4(), building_id=b1.id, file_path="/f", file_name="f.pdf"))
    db_session.add(Document(id=uuid.uuid4(), building_id=b2.id, file_path="/g", file_name="g.pdf"))
    await db_session.commit()

    summary = await get_portfolio_summary(db_session)
    assert summary.overview.total_buildings == 2  # archived excluded
    assert summary.overview.total_diagnostics == 2
    assert summary.overview.total_interventions == 1
    assert summary.overview.total_documents == 2


async def test_risk_distribution(db_session: AsyncSession):
    """Groups buildings by risk level."""
    user = _make_user()
    db_session.add(user)
    await db_session.flush()

    b1 = _make_building(user.id)
    b2 = _make_building(user.id)
    b3 = _make_building(user.id)
    db_session.add_all([b1, b2, b3])
    await db_session.flush()

    db_session.add(BuildingRiskScore(id=uuid.uuid4(), building_id=b1.id, overall_risk_level="low", confidence=0.3))
    db_session.add(BuildingRiskScore(id=uuid.uuid4(), building_id=b2.id, overall_risk_level="high", confidence=0.8))
    db_session.add(BuildingRiskScore(id=uuid.uuid4(), building_id=b3.id, overall_risk_level="critical", confidence=0.9))
    await db_session.commit()

    summary = await get_portfolio_summary(db_session)
    assert summary.risk.by_level["low"] == 1
    assert summary.risk.by_level["high"] == 1
    assert summary.risk.by_level["critical"] == 1
    assert summary.risk.by_level["medium"] == 0
    assert summary.risk.avg_risk_score is not None
    assert summary.risk.buildings_above_threshold == 2  # confidence > 0.7


async def test_grade_distribution_from_snapshots(db_session: AsyncSession):
    """Groups buildings by passport grade from latest snapshots."""
    user = _make_user()
    db_session.add(user)
    await db_session.flush()

    b1 = _make_building(user.id)
    b2 = _make_building(user.id)
    db_session.add_all([b1, b2])
    await db_session.flush()

    now = datetime.now(UTC)
    # b1: older snapshot grade C, newer grade A -> should use A
    db_session.add(
        BuildingSnapshot(
            id=uuid.uuid4(),
            building_id=b1.id,
            snapshot_type="manual",
            passport_grade="C",
            completeness_score=0.5,
            overall_trust=0.6,
            captured_at=now - timedelta(days=10),
        )
    )
    db_session.add(
        BuildingSnapshot(
            id=uuid.uuid4(),
            building_id=b1.id,
            snapshot_type="manual",
            passport_grade="A",
            completeness_score=0.9,
            overall_trust=0.95,
            captured_at=now,
        )
    )
    # b2: grade B
    db_session.add(
        BuildingSnapshot(
            id=uuid.uuid4(),
            building_id=b2.id,
            snapshot_type="manual",
            passport_grade="B",
            completeness_score=0.7,
            overall_trust=0.8,
            captured_at=now,
        )
    )
    await db_session.commit()

    summary = await get_portfolio_summary(db_session)
    assert summary.grades.by_grade["A"] == 1
    assert summary.grades.by_grade["B"] == 1
    assert summary.grades.by_grade["C"] == 0  # old snapshot, not latest


async def test_readiness_from_snapshots(db_session: AsyncSession):
    """Classifies buildings by completeness threshold."""
    user = _make_user()
    db_session.add(user)
    await db_session.flush()

    b1 = _make_building(user.id)
    b2 = _make_building(user.id)
    b3 = _make_building(user.id)
    b4 = _make_building(user.id)  # no snapshot
    db_session.add_all([b1, b2, b3, b4])
    await db_session.flush()

    now = datetime.now(UTC)
    db_session.add(
        BuildingSnapshot(
            id=uuid.uuid4(),
            building_id=b1.id,
            snapshot_type="manual",
            completeness_score=0.9,
            captured_at=now,
        )
    )
    db_session.add(
        BuildingSnapshot(
            id=uuid.uuid4(),
            building_id=b2.id,
            snapshot_type="manual",
            completeness_score=0.6,
            captured_at=now,
        )
    )
    db_session.add(
        BuildingSnapshot(
            id=uuid.uuid4(),
            building_id=b3.id,
            snapshot_type="manual",
            completeness_score=0.3,
            captured_at=now,
        )
    )
    await db_session.commit()

    summary = await get_portfolio_summary(db_session)
    assert summary.readiness.ready_count == 1
    assert summary.readiness.partially_ready_count == 1
    assert summary.readiness.not_ready_count == 1
    assert summary.readiness.unknown_count == 1


async def test_action_summary_by_status_and_priority(db_session: AsyncSession):
    """Groups actions by status and priority."""
    user = _make_user()
    db_session.add(user)
    await db_session.flush()

    b = _make_building(user.id)
    db_session.add(b)
    await db_session.flush()

    db_session.add(
        ActionItem(
            id=uuid.uuid4(),
            building_id=b.id,
            source_type="diagnostic",
            action_type="remove",
            title="A1",
            priority="high",
            status="open",
        )
    )
    db_session.add(
        ActionItem(
            id=uuid.uuid4(),
            building_id=b.id,
            source_type="diagnostic",
            action_type="sample",
            title="A2",
            priority="medium",
            status="in_progress",
        )
    )
    db_session.add(
        ActionItem(
            id=uuid.uuid4(),
            building_id=b.id,
            source_type="diagnostic",
            action_type="notify",
            title="A3",
            priority="low",
            status="completed",
        )
    )
    db_session.add(
        ActionItem(
            id=uuid.uuid4(),
            building_id=b.id,
            source_type="diagnostic",
            action_type="review",
            title="A4",
            priority="high",
            status="open",
            due_date=(datetime.now(UTC) - timedelta(days=10)).date(),
        )
    )
    await db_session.commit()

    summary = await get_portfolio_summary(db_session)
    assert summary.actions.total_open == 2
    assert summary.actions.total_in_progress == 1
    assert summary.actions.total_completed == 1
    assert summary.actions.by_priority["high"] == 2
    assert summary.actions.by_priority["medium"] == 1
    assert summary.actions.overdue_count == 1


async def test_alert_summary_weak_signals(db_session: AsyncSession):
    """Counts weak signals and buildings on critical path."""
    user = _make_user()
    db_session.add(user)
    await db_session.flush()

    b = _make_building(user.id)
    db_session.add(b)
    await db_session.flush()

    db_session.add(
        ChangeSignal(
            id=uuid.uuid4(),
            building_id=b.id,
            signal_type="decay",
            title="Signal 1",
            status="active",
        )
    )
    db_session.add(
        ChangeSignal(
            id=uuid.uuid4(),
            building_id=b.id,
            signal_type="regulatory",
            title="Signal 2",
            status="active",
        )
    )
    db_session.add(
        ChangeSignal(
            id=uuid.uuid4(),
            building_id=b.id,
            signal_type="other",
            title="Signal 3",
            status="acknowledged",  # not active
        )
    )
    db_session.add(
        BuildingRiskScore(
            id=uuid.uuid4(),
            building_id=b.id,
            overall_risk_level="critical",
            confidence=0.9,
        )
    )
    await db_session.commit()

    summary = await get_portfolio_summary(db_session)
    assert summary.alerts.total_weak_signals == 2
    assert summary.alerts.buildings_on_critical_path == 1


async def test_alert_stale_diagnostics(db_session: AsyncSession):
    """Buildings with >3 open unknowns are stale."""
    user = _make_user()
    db_session.add(user)
    await db_session.flush()

    b = _make_building(user.id)
    db_session.add(b)
    await db_session.flush()

    for i in range(4):
        db_session.add(
            UnknownIssue(
                id=uuid.uuid4(),
                building_id=b.id,
                unknown_type="missing_data",
                title=f"Unknown {i}",
                status="open",
            )
        )
    await db_session.commit()

    summary = await get_portfolio_summary(db_session)
    assert summary.alerts.buildings_with_stale_diagnostics == 1


async def test_alert_constraint_blockers(db_session: AsyncSession):
    """Counts unknowns that block readiness."""
    user = _make_user()
    db_session.add(user)
    await db_session.flush()

    b = _make_building(user.id)
    db_session.add(b)
    await db_session.flush()

    db_session.add(
        UnknownIssue(
            id=uuid.uuid4(),
            building_id=b.id,
            unknown_type="missing_data",
            title="Blocker",
            status="open",
            blocks_readiness=True,
        )
    )
    db_session.add(
        UnknownIssue(
            id=uuid.uuid4(),
            building_id=b.id,
            unknown_type="missing_data",
            title="Not blocker",
            status="open",
            blocks_readiness=False,
        )
    )
    await db_session.commit()

    summary = await get_portfolio_summary(db_session)
    assert summary.alerts.total_constraint_blockers == 1


async def test_organization_filter(db_session: AsyncSession):
    """Filtering by organization only counts that org's buildings."""
    org1 = _make_org("Org1")
    org2 = _make_org("Org2")
    db_session.add_all([org1, org2])
    await db_session.flush()

    user1 = _make_user(org_id=org1.id)
    user2 = _make_user(org_id=org2.id)
    db_session.add_all([user1, user2])
    await db_session.flush()

    b1 = _make_building(user1.id)
    b2 = _make_building(user1.id)
    b3 = _make_building(user2.id)
    db_session.add_all([b1, b2, b3])
    await db_session.commit()

    summary_org1 = await get_portfolio_summary(db_session, organization_id=org1.id)
    assert summary_org1.overview.total_buildings == 2
    assert summary_org1.organization_id == org1.id

    summary_org2 = await get_portfolio_summary(db_session, organization_id=org2.id)
    assert summary_org2.overview.total_buildings == 1


async def test_portfolio_comparison(db_session: AsyncSession):
    """Comparing multiple organizations returns a list of summaries."""
    org1 = _make_org("Org1")
    org2 = _make_org("Org2")
    db_session.add_all([org1, org2])
    await db_session.flush()

    user1 = _make_user(org_id=org1.id)
    user2 = _make_user(org_id=org2.id)
    db_session.add_all([user1, user2])
    await db_session.flush()

    db_session.add(_make_building(user1.id))
    db_session.add(_make_building(user2.id))
    db_session.add(_make_building(user2.id))
    await db_session.commit()

    results = await get_portfolio_comparison(db_session, [org1.id, org2.id])
    assert len(results) == 2
    assert results[0].overview.total_buildings == 1
    assert results[1].overview.total_buildings == 2


async def test_health_score_empty(db_session: AsyncSession):
    """Health score returns 0 for empty portfolio."""
    result = await get_portfolio_health_score(db_session)
    assert result["score"] == 0
    assert result["total_buildings"] == 0
    assert "breakdown" in result


async def test_health_score_with_data(db_session: AsyncSession):
    """Health score computes a weighted score."""
    user = _make_user()
    db_session.add(user)
    await db_session.flush()

    b = _make_building(user.id)
    db_session.add(b)
    await db_session.flush()

    # Risk: low -> good
    db_session.add(
        BuildingRiskScore(
            id=uuid.uuid4(),
            building_id=b.id,
            overall_risk_level="low",
            confidence=0.5,
        )
    )
    # Snapshot: high completeness
    db_session.add(
        BuildingSnapshot(
            id=uuid.uuid4(),
            building_id=b.id,
            snapshot_type="manual",
            completeness_score=0.9,
            overall_trust=0.8,
            passport_grade="A",
            captured_at=datetime.now(UTC),
        )
    )
    # Diagnostic: validated and recent
    db_session.add(
        Diagnostic(
            id=uuid.uuid4(),
            building_id=b.id,
            diagnostic_type="asbestos",
            status="validated",
        )
    )
    await db_session.commit()

    result = await get_portfolio_health_score(db_session)
    assert result["score"] > 0
    assert result["total_buildings"] == 1
    assert result["breakdown"]["risk"]["score"] == 100.0  # no high/critical
    assert result["breakdown"]["completeness"]["score"] == 90.0


async def test_active_campaigns_count(db_session: AsyncSession):
    """Counts only active campaigns."""
    user = _make_user()
    db_session.add(user)
    await db_session.flush()

    db_session.add(Campaign(id=uuid.uuid4(), title="C1", campaign_type="diagnostic", status="active"))
    db_session.add(Campaign(id=uuid.uuid4(), title="C2", campaign_type="diagnostic", status="active"))
    db_session.add(Campaign(id=uuid.uuid4(), title="C3", campaign_type="diagnostic", status="completed"))
    await db_session.commit()

    summary = await get_portfolio_summary(db_session)
    assert summary.overview.active_campaigns == 2


async def test_compliance_overview(db_session: AsyncSession):
    """Compliance overview classifies buildings by diagnostic status."""
    user = _make_user()
    db_session.add(user)
    await db_session.flush()

    b1 = _make_building(user.id)  # validated recent
    b2 = _make_building(user.id)  # no diagnostic -> unknown
    db_session.add_all([b1, b2])
    await db_session.flush()

    db_session.add(
        Diagnostic(
            id=uuid.uuid4(),
            building_id=b1.id,
            diagnostic_type="asbestos",
            status="validated",
        )
    )
    await db_session.commit()

    summary = await get_portfolio_summary(db_session)
    assert summary.compliance.unknown_count == 1  # b2 has no diagnostic
    assert summary.compliance.compliant_count == 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


async def test_api_portfolio_summary(client, admin_user, auth_headers, db_session):
    """GET /api/portfolio/summary returns 200."""
    resp = await client.get("/api/v1/portfolio/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "overview" in data
    assert "risk" in data
    assert "compliance" in data
    assert "readiness" in data
    assert "grades" in data
    assert "actions" in data
    assert "alerts" in data
    assert "generated_at" in data


async def test_api_portfolio_summary_with_org_filter(client, admin_user, auth_headers, db_session):
    """GET /api/portfolio/summary?organization_id=... filters by org."""
    org = _make_org()
    db_session.add(org)
    await db_session.commit()

    resp = await client.get(f"/api/v1/portfolio/summary?organization_id={org.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["overview"]["total_buildings"] == 0


async def test_api_portfolio_compare(client, admin_user, auth_headers, db_session):
    """POST /api/portfolio/compare returns list."""
    org1 = _make_org("A")
    org2 = _make_org("B")
    db_session.add_all([org1, org2])
    await db_session.commit()

    resp = await client.post(
        "/api/v1/portfolio/compare",
        json={"organization_ids": [str(org1.id), str(org2.id)]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


async def test_api_portfolio_health_score(client, admin_user, auth_headers, db_session):
    """GET /api/portfolio/health-score returns dict with score."""
    resp = await client.get("/api/v1/portfolio/health-score", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "score" in data
    assert "breakdown" in data
    assert "total_buildings" in data


async def test_api_portfolio_summary_unauthorized(client):
    """GET /api/portfolio/summary without auth returns 403."""
    resp = await client.get("/api/v1/portfolio/summary")
    assert resp.status_code == 403
