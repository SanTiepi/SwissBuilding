"""Tests for subsidy tracking service + API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.subsidy_tracking_service import (
    analyze_funding_gap,
    get_building_subsidy_eligibility,
    get_building_subsidy_status,
    get_portfolio_subsidy_summary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(user):
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "exp": datetime.now(UTC) + timedelta(hours=8),
    }
    return jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
    o = Organization(
        id=uuid.uuid4(),
        name="Subsidy Test Org",
        type="property_management",
    )
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org_admin(db_session, org):
    from tests.conftest import _HASH_ADMIN

    u = User(
        id=uuid.uuid4(),
        email="subsidyadmin@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Sub",
        last_name="Admin",
        role="admin",
        is_active=True,
        language="fr",
        organization_id=org.id,
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest.fixture
async def vd_building(db_session, org_admin):
    """VD building with asbestos + PCB exceeded samples."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Subvention 5",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=org_admin.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=bldg.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(diag)
    await db_session.flush()

    # Asbestos exceeded
    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-001",
        pollutant_type="asbestos",
        concentration=5.0,
        unit="%",
        threshold_exceeded=True,
        risk_level="high",
    )
    # PCB exceeded
    s2 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-002",
        pollutant_type="pcb",
        concentration=80.0,
        unit="mg/kg",
        threshold_exceeded=True,
        risk_level="medium",
    )
    # Lead not exceeded
    s3 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S-003",
        pollutant_type="lead",
        concentration=100.0,
        unit="mg/kg",
        threshold_exceeded=False,
        risk_level="low",
    )
    db_session.add_all([s1, s2, s3])
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def ge_building(db_session, org_admin):
    """GE building with asbestos exceeded."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue de Genève 10",
        postal_code="1200",
        city="Genève",
        canton="GE",
        construction_year=1970,
        building_type="commercial",
        created_by=org_admin.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=bldg.id,
        diagnostic_type="asbestos",
        status="validated",
    )
    db_session.add(diag)
    await db_session.flush()

    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="G-001",
        pollutant_type="asbestos",
        concentration=3.0,
        unit="%",
        threshold_exceeded=True,
        risk_level="high",
    )
    db_session.add(s1)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def empty_building(db_session, org_admin):
    """Building with no diagnostics."""
    bldg = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1980,
        building_type="residential",
        created_by=org_admin.id,
        status="active",
    )
    db_session.add(bldg)
    await db_session.commit()
    await db_session.refresh(bldg)
    return bldg


@pytest.fixture
async def building_with_funding_actions(db_session, org_admin, vd_building):
    """Add funding-related actions to vd_building."""
    a1 = ActionItem(
        id=uuid.uuid4(),
        building_id=vd_building.id,
        source_type="manual",
        action_type="subsidy_application",
        title="Programme Bâtiments application",
        status="in_progress",
        priority="high",
        created_by=org_admin.id,
    )
    a2 = ActionItem(
        id=uuid.uuid4(),
        building_id=vd_building.id,
        source_type="manual",
        action_type="grant_request",
        title="Cantonal grant VD",
        status="completed",
        priority="medium",
        created_by=org_admin.id,
    )
    a3 = ActionItem(
        id=uuid.uuid4(),
        building_id=vd_building.id,
        source_type="manual",
        action_type="remediation",
        title="Non-funding action",
        status="open",
        priority="low",
        created_by=org_admin.id,
    )
    db_session.add_all([a1, a2, a3])
    await db_session.commit()
    return vd_building


# ===========================================================================
# FN1 — get_building_subsidy_eligibility
# ===========================================================================


class TestGetBuildingSubsidyEligibility:
    @pytest.mark.asyncio
    async def test_vd_building_eligible_programs(self, db_session, vd_building):
        result = await get_building_subsidy_eligibility(vd_building.id, db_session)
        assert result.building_id == vd_building.id
        # VD building with asbestos+pcb: federal + VD cantonal + municipal
        program_ids = {p.program_id for p in result.eligible_programs}
        assert "fed-batiments" in program_ids
        assert "vd-assainissement" in program_ids
        assert "municipal-support" in program_ids
        # GE program should NOT be included
        assert "ge-prime-energie" not in program_ids

    @pytest.mark.asyncio
    async def test_ge_building_eligible_programs(self, db_session, ge_building):
        result = await get_building_subsidy_eligibility(ge_building.id, db_session)
        program_ids = {p.program_id for p in result.eligible_programs}
        assert "ge-prime-energie" in program_ids
        assert "fed-batiments" in program_ids
        assert "vd-assainissement" not in program_ids

    @pytest.mark.asyncio
    async def test_total_potential_funding(self, db_session, vd_building):
        result = await get_building_subsidy_eligibility(vd_building.id, db_session)
        # federal 50k + VD 30k + municipal 10k = 90k
        assert result.total_potential_funding == 90000.0

    @pytest.mark.asyncio
    async def test_empty_building_no_eligibility(self, db_session, empty_building):
        result = await get_building_subsidy_eligibility(empty_building.id, db_session)
        assert result.eligible_programs == []
        assert result.total_potential_funding == 0.0

    @pytest.mark.asyncio
    async def test_recommended_priority_order(self, db_session, vd_building):
        result = await get_building_subsidy_eligibility(vd_building.id, db_session)
        # Sorted by coverage_percentage desc: federal(40%) > VD(30%) > municipal(15%)
        assert result.recommended_priority[0] == "fed-batiments"
        assert result.recommended_priority[-1] == "municipal-support"

    @pytest.mark.asyncio
    async def test_nonexistent_building_raises(self, db_session):
        fake_id = uuid.uuid4()
        with pytest.raises(ValueError, match="not found"):
            await get_building_subsidy_eligibility(fake_id, db_session)

    @pytest.mark.asyncio
    async def test_generated_at_present(self, db_session, vd_building):
        result = await get_building_subsidy_eligibility(vd_building.id, db_session)
        assert isinstance(result.generated_at, datetime)


# ===========================================================================
# FN2 — get_building_subsidy_status
# ===========================================================================


class TestGetBuildingSubsidyStatus:
    @pytest.mark.asyncio
    async def test_with_funding_actions(self, db_session, building_with_funding_actions):
        bldg = building_with_funding_actions
        result = await get_building_subsidy_status(bldg.id, db_session)
        assert result.building_id == bldg.id
        # 2 funding actions (subsidy_application, grant_request), not remediation
        assert len(result.applications) == 2

    @pytest.mark.asyncio
    async def test_application_status_mapping(self, db_session, building_with_funding_actions):
        bldg = building_with_funding_actions
        result = await get_building_subsidy_status(bldg.id, db_session)
        statuses = {a.status for a in result.applications}
        # in_progress -> submitted, completed -> approved
        assert "submitted" in statuses
        assert "approved" in statuses

    @pytest.mark.asyncio
    async def test_totals(self, db_session, building_with_funding_actions):
        bldg = building_with_funding_actions
        result = await get_building_subsidy_status(bldg.id, db_session)
        assert result.total_requested == 20000.0  # 2 x 10000
        assert result.total_approved == 10000.0  # 1 approved
        assert result.pending_count == 1  # 1 submitted

    @pytest.mark.asyncio
    async def test_no_funding_actions(self, db_session, empty_building):
        result = await get_building_subsidy_status(empty_building.id, db_session)
        assert result.applications == []
        assert result.total_requested == 0.0
        assert result.pending_count == 0

    @pytest.mark.asyncio
    async def test_nonexistent_building_raises(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_building_subsidy_status(uuid.uuid4(), db_session)


# ===========================================================================
# FN3 — analyze_funding_gap
# ===========================================================================


class TestAnalyzeFundingGap:
    @pytest.mark.asyncio
    async def test_vd_building_gaps(self, db_session, vd_building):
        result = await analyze_funding_gap(vd_building.id, db_session)
        assert result.building_id == vd_building.id
        # 2 pollutants exceeded: asbestos, pcb
        assert len(result.gaps) == 2
        pollutants = {g.pollutant_type for g in result.gaps}
        assert pollutants == {"asbestos", "pcb"}

    @pytest.mark.asyncio
    async def test_remediation_costs(self, db_session, vd_building):
        result = await analyze_funding_gap(vd_building.id, db_session)
        by_pollutant = {g.pollutant_type: g for g in result.gaps}
        # 1 diagnostic with asbestos exceeded -> 15000
        assert by_pollutant["asbestos"].estimated_remediation_cost == 15000.0
        # 1 diagnostic with pcb exceeded -> 8000
        assert by_pollutant["pcb"].estimated_remediation_cost == 8000.0

    @pytest.mark.asyncio
    async def test_total_cost_and_gap(self, db_session, vd_building):
        result = await analyze_funding_gap(vd_building.id, db_session)
        assert result.total_remediation_cost == 23000.0
        # total_available = 90000 (3 programs) spread across 2 pollutants = 45000 each
        assert result.total_available_funding == 90000.0
        # Gap is 0 since funding exceeds cost
        assert result.total_gap == 0.0
        assert result.funding_coverage_pct > 100.0

    @pytest.mark.asyncio
    async def test_empty_building_no_gaps(self, db_session, empty_building):
        result = await analyze_funding_gap(empty_building.id, db_session)
        assert result.gaps == []
        assert result.total_remediation_cost == 0.0
        assert result.funding_coverage_pct == 0.0

    @pytest.mark.asyncio
    async def test_gap_percentage_calculation(self, db_session, vd_building):
        result = await analyze_funding_gap(vd_building.id, db_session)
        for gap in result.gaps:
            if gap.gap_amount > 0:
                expected_pct = gap.gap_amount / gap.estimated_remediation_cost * 100
                assert abs(gap.gap_percentage - round(expected_pct, 2)) < 0.01

    @pytest.mark.asyncio
    async def test_nonexistent_building_raises(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await analyze_funding_gap(uuid.uuid4(), db_session)


# ===========================================================================
# FN4 — get_portfolio_subsidy_summary
# ===========================================================================


class TestGetPortfolioSubsidySummary:
    @pytest.mark.asyncio
    async def test_org_with_buildings(self, db_session, org, vd_building):
        result = await get_portfolio_subsidy_summary(org.id, db_session)
        assert result.organization_id == org.id
        assert result.total_buildings_eligible >= 1
        assert result.total_potential_funding > 0

    @pytest.mark.asyncio
    async def test_by_provider_breakdown(self, db_session, org, vd_building):
        result = await get_portfolio_subsidy_summary(org.id, db_session)
        assert "federal" in result.by_provider
        assert "cantonal" in result.by_provider

    @pytest.mark.asyncio
    async def test_empty_org(self, db_session):
        o = Organization(id=uuid.uuid4(), name="Empty Org", type="property_management")
        db_session.add(o)
        await db_session.commit()
        result = await get_portfolio_subsidy_summary(o.id, db_session)
        assert result.total_buildings_eligible == 0
        assert result.total_potential_funding == 0.0

    @pytest.mark.asyncio
    async def test_nonexistent_org_raises(self, db_session):
        with pytest.raises(ValueError, match="not found"):
            await get_portfolio_subsidy_summary(uuid.uuid4(), db_session)


# ===========================================================================
# API endpoint tests
# ===========================================================================


class TestSubsidyTrackingAPI:
    @pytest.mark.asyncio
    async def test_eligibility_endpoint(self, client, admin_user, sample_building):
        token = _make_token(admin_user)
        resp = await client.get(
            f"/api/v1/subsidy-tracking/buildings/{sample_building.id}/eligibility",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == str(sample_building.id)

    @pytest.mark.asyncio
    async def test_status_endpoint(self, client, admin_user, sample_building):
        token = _make_token(admin_user)
        resp = await client.get(
            f"/api/v1/subsidy-tracking/buildings/{sample_building.id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == str(sample_building.id)
        assert "applications" in data

    @pytest.mark.asyncio
    async def test_funding_gap_endpoint(self, client, admin_user, sample_building):
        token = _make_token(admin_user)
        resp = await client.get(
            f"/api/v1/subsidy-tracking/buildings/{sample_building.id}/funding-gap",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == str(sample_building.id)

    @pytest.mark.asyncio
    async def test_portfolio_summary_endpoint(self, client, admin_user):
        token = _make_token(admin_user)
        # Org doesn't exist so expect 404
        fake_org = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/organizations/{fake_org}/subsidy-summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_eligibility_not_found(self, client, admin_user):
        token = _make_token(admin_user)
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/subsidy-tracking/buildings/{fake_id}/eligibility",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client, sample_building):
        resp = await client.get(
            f"/api/v1/subsidy-tracking/buildings/{sample_building.id}/eligibility",
        )
        assert resp.status_code in (401, 403)
