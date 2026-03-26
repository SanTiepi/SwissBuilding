"""Wave 2 intelligence tests — portfolio triage, ERP payload, decision view."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.organization import Organization
from app.models.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def w2_org(db_session: AsyncSession):
    org = Organization(
        id=uuid.uuid4(),
        name="Wave2 Test Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def w2_building(db_session: AsyncSession, admin_user: User, w2_org: Organization):
    building = Building(
        id=uuid.uuid4(),
        address="Rue Test 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
        organization_id=w2_org.id,
        construction_year=1970,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def w2_building_with_blocker(db_session: AsyncSession, admin_user: User, w2_org: Organization):
    """Building with a blocking unknown issue."""
    from app.models.unknown_issue import UnknownIssue

    building = Building(
        id=uuid.uuid4(),
        address="Rue Bloquee 5",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=admin_user.id,
        organization_id=w2_org.id,
        construction_year=1955,
    )
    db_session.add(building)
    await db_session.flush()

    unknown = UnknownIssue(
        id=uuid.uuid4(),
        building_id=building.id,
        unknown_type="missing_diagnostic",
        title="Asbestos diagnostic missing",
        severity="critical",
        status="open",
        blocks_readiness=True,
    )
    db_session.add(unknown)
    await db_session.commit()
    await db_session.refresh(building)
    return building


# ---------------------------------------------------------------------------
# 1. Portfolio triage
# ---------------------------------------------------------------------------


class TestPortfolioTriageClassification:
    """Tests for the _classify_building function and portfolio triage service."""

    def test_blockers_classify_as_critical(self):
        from app.services.portfolio_triage_service import _classify_building

        result = _classify_building(passport_grade="B", blockers_count=2, trust=0.9)
        assert result == "critical"

    def test_grade_f_classifies_as_critical(self):
        from app.services.portfolio_triage_service import _classify_building

        result = _classify_building(passport_grade="F", blockers_count=0, trust=0.5)
        assert result == "critical"

    def test_grade_d_classifies_as_action_needed(self):
        from app.services.portfolio_triage_service import _classify_building

        result = _classify_building(passport_grade="D", blockers_count=0, trust=0.8)
        assert result == "action_needed"

    def test_low_trust_classifies_as_action_needed(self):
        from app.services.portfolio_triage_service import _classify_building

        result = _classify_building(passport_grade="B", blockers_count=0, trust=0.2)
        assert result == "action_needed"

    def test_grade_c_classifies_as_monitored(self):
        from app.services.portfolio_triage_service import _classify_building

        result = _classify_building(passport_grade="C", blockers_count=0, trust=0.8)
        assert result == "monitored"

    def test_good_grade_high_trust_classifies_as_under_control(self):
        from app.services.portfolio_triage_service import _classify_building

        result = _classify_building(passport_grade="A", blockers_count=0, trust=0.9)
        assert result == "under_control"

    @pytest.mark.asyncio
    async def test_portfolio_counts_match_classifications(
        self,
        db_session: AsyncSession,
        admin_user: User,
        w2_org: Organization,
    ):
        """Triage result counts should sum to total buildings."""
        from app.services.portfolio_triage_service import get_portfolio_triage

        # Create 3 buildings (all will default to grade F -> critical)
        for i in range(3):
            b = Building(
                id=uuid.uuid4(),
                address=f"Rue Count {i}",
                postal_code="1000",
                city="Lausanne",
                canton="VD",
                building_type="residential",
                created_by=admin_user.id,
                organization_id=w2_org.id,
            )
            db_session.add(b)
        await db_session.commit()

        result = await get_portfolio_triage(db_session, w2_org.id)
        total = result.critical_count + result.action_needed_count + result.monitored_count + result.under_control_count
        assert total == len(result.buildings)
        assert total == 3

    @pytest.mark.asyncio
    async def test_empty_portfolio_returns_zero_counts(
        self,
        db_session: AsyncSession,
        w2_org: Organization,
    ):
        """Org with no buildings returns zeroes everywhere."""
        from app.services.portfolio_triage_service import get_portfolio_triage

        result = await get_portfolio_triage(db_session, w2_org.id)
        assert result.critical_count == 0
        assert result.action_needed_count == 0
        assert result.monitored_count == 0
        assert result.under_control_count == 0
        assert result.buildings == []


# ---------------------------------------------------------------------------
# 2. ERP payload
# ---------------------------------------------------------------------------


class TestErpPayload:
    """Tests for the ERP payload schemas."""

    def test_payload_version_is_1_0(self):
        from app.schemas.erp_payload import ERP_PAYLOAD_VERSION

        assert ERP_PAYLOAD_VERSION == "1.0"

    def test_building_payload_includes_safe_to_start(self):
        from app.schemas.erp_payload import ErpBuildingPayload

        payload = ErpBuildingPayload(
            building_id=uuid.uuid4(),
            generated_at=datetime.now(UTC),
        )
        assert payload.safe_to_start is not None
        assert payload.safe_to_start.status == "memory_incomplete"

    def test_building_payload_blockers_list(self):
        from app.schemas.erp_payload import ErpBlocker, ErpBuildingPayload

        blocker = ErpBlocker(type="obligation", title="Overdue asbestos check", severity="critical")
        payload = ErpBuildingPayload(
            building_id=uuid.uuid4(),
            generated_at=datetime.now(UTC),
            blockers=[blocker],
        )
        assert len(payload.blockers) == 1
        assert payload.blockers[0].title == "Overdue asbestos check"

    def test_building_payload_identity_fields(self):
        from app.schemas.erp_payload import ErpBuildingPayload

        bid = uuid.uuid4()
        payload = ErpBuildingPayload(
            building_id=bid,
            generated_at=datetime.now(UTC),
            egid=884846,
            egrid="CH656183944565",
            address="Avenue Gabriel-de-Rumine 34",
            npa="1005",
            city="Lausanne",
        )
        assert payload.building_id == bid
        assert payload.egid == 884846
        assert payload.egrid == "CH656183944565"
        assert payload.address == "Avenue Gabriel-de-Rumine 34"

    def test_portfolio_payload_includes_buildings(self):
        from app.schemas.erp_payload import ErpBuildingPayload, ErpPortfolioPayload

        b1 = ErpBuildingPayload(building_id=uuid.uuid4(), generated_at=datetime.now(UTC))
        b2 = ErpBuildingPayload(building_id=uuid.uuid4(), generated_at=datetime.now(UTC))
        portfolio = ErpPortfolioPayload(
            org_id=uuid.uuid4(),
            generated_at=datetime.now(UTC),
            building_count=2,
            buildings=[b1, b2],
        )
        assert portfolio.building_count == 2
        assert len(portfolio.buildings) == 2

    def test_proof_status_reflects_coverage(self):
        from app.schemas.erp_payload import ErpBuildingPayload, ErpProofStatus

        proof = ErpProofStatus(
            diagnostic_coverage=0.8,
            authority_pack_ready=True,
            pollutants_assessed=["asbestos", "pcb", "lead"],
            pollutants_missing=["radon"],
        )
        payload = ErpBuildingPayload(
            building_id=uuid.uuid4(),
            generated_at=datetime.now(UTC),
            proof_status=proof,
        )
        assert payload.proof_status.diagnostic_coverage == 0.8
        assert payload.proof_status.authority_pack_ready is True
        assert "asbestos" in payload.proof_status.pollutants_assessed
        assert "radon" in payload.proof_status.pollutants_missing

    def test_empty_payload_has_defaults(self):
        from app.schemas.erp_payload import ErpBuildingPayload

        payload = ErpBuildingPayload(
            building_id=uuid.uuid4(),
            generated_at=datetime.now(UTC),
        )
        assert payload.blockers == []
        assert payload.next_actions == []
        assert payload.obligations == []
        assert payload.proof_status.diagnostic_coverage == 0.0
        assert payload.passport_grade is None


# ---------------------------------------------------------------------------
# 3. Decision view
# ---------------------------------------------------------------------------


class TestDecisionView:
    """Tests for the decision view service."""

    @pytest.mark.asyncio
    async def test_decision_view_returns_passport_grade(
        self,
        db_session: AsyncSession,
        w2_building: Building,
    ):
        from app.services.decision_view_service import get_building_decision_view

        dv = await get_building_decision_view(db_session, w2_building.id)
        assert dv is not None
        assert dv.passport_grade in ("A", "B", "C", "D", "E", "F")

    @pytest.mark.asyncio
    async def test_blockers_from_unknowns(
        self,
        db_session: AsyncSession,
        w2_building_with_blocker: Building,
    ):
        from app.services.decision_view_service import get_building_decision_view

        dv = await get_building_decision_view(db_session, w2_building_with_blocker.id)
        assert dv is not None
        assert len(dv.blockers) >= 1
        titles = [b.title for b in dv.blockers]
        assert any("Asbestos" in t for t in titles)

    @pytest.mark.asyncio
    async def test_audience_readiness_sections_present(
        self,
        db_session: AsyncSession,
        w2_building: Building,
    ):
        from app.services.decision_view_service import get_building_decision_view

        dv = await get_building_decision_view(db_session, w2_building.id)
        assert dv is not None
        audiences = [ar.audience for ar in dv.audience_readiness]
        assert "authority" in audiences
        assert "insurer" in audiences
        assert "lender" in audiences
        assert "transaction" in audiences

    @pytest.mark.asyncio
    async def test_nonexistent_building_returns_none(self, db_session: AsyncSession):
        from app.services.decision_view_service import get_building_decision_view

        dv = await get_building_decision_view(db_session, uuid.uuid4())
        assert dv is None

    @pytest.mark.asyncio
    async def test_decision_view_has_building_address(
        self,
        db_session: AsyncSession,
        w2_building: Building,
    ):
        from app.services.decision_view_service import get_building_decision_view

        dv = await get_building_decision_view(db_session, w2_building.id)
        assert dv is not None
        assert dv.building_name == "Rue Test 1"
        assert "1000" in dv.building_address
