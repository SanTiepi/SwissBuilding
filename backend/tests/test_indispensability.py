"""Tests for the indispensability service — fragmentation, defensibility, counterfactual."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.building_snapshot import BuildingSnapshot
from app.models.data_quality_issue import DataQualityIssue
from app.models.document import Document
from app.models.enrichment_run import BuildingEnrichmentRun
from app.models.organization import Organization
from app.models.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def ind_org(db_session: AsyncSession):
    org = Organization(
        id=uuid.uuid4(),
        name="Indispensability Test Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def ind_user(db_session: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        email="ind-test@test.ch",
        password_hash="$2b$12$LJ3m4ys3uz0MHl0BF6zz0u4.bfPKEfRz0PnWkKlCem0clfb/E.iai",
        first_name="Ind",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def bare_building(db_session: AsyncSession, ind_user: User, ind_org: Organization):
    """Building with zero data — maximum fragmentation."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=ind_user.id,
        organization_id=ind_org.id,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


@pytest.fixture
async def enriched_building(db_session: AsyncSession, ind_user: User, ind_org: Organization):
    """Building with enrichment data, documents, data quality issues, actions, snapshots."""
    building = Building(
        id=uuid.uuid4(),
        address="Rue Enrichie 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=ind_user.id,
        organization_id=ind_org.id,
        construction_year=1965,
    )
    db_session.add(building)
    await db_session.flush()

    # Enrichment run
    enrichment = BuildingEnrichmentRun(
        id=uuid.uuid4(),
        building_id=building.id,
        address_input="Rue Enrichie 10, 1000 Lausanne",
        status="completed",
        sources_attempted=3,
        sources_succeeded=2,
    )
    db_session.add(enrichment)

    # Documents
    for i in range(3):
        doc = Document(
            id=uuid.uuid4(),
            building_id=building.id,
            file_path=f"/docs/test_{i}.pdf",
            file_name=f"test_{i}.pdf",
            document_type="diagnostic_report",
            content_hash=f"sha256_{i}",
            uploaded_by=ind_user.id,
        )
        db_session.add(doc)

    # Data quality issues
    for i in range(2):
        dqi = DataQualityIssue(
            id=uuid.uuid4(),
            building_id=building.id,
            issue_type="contradiction",
            severity="medium",
            status="open",
            description=f"Test contradiction {i}",
            detected_by="system",
        )
        db_session.add(dqi)

    # Action items
    for i in range(4):
        action = ActionItem(
            id=uuid.uuid4(),
            building_id=building.id,
            source_type="diagnostic",
            action_type="remediation",
            title=f"Action test {i}",
            priority="medium",
            status="open",
        )
        db_session.add(action)

    # Snapshots (spanning 90 days)
    now = datetime.now(UTC)
    for _i, days_ago in enumerate([90, 45, 0]):
        snap = BuildingSnapshot(
            id=uuid.uuid4(),
            building_id=building.id,
            snapshot_type="manual",
            passport_grade="C",
            overall_trust=0.5,
            completeness_score=0.6,
            captured_at=now - timedelta(days=days_ago),
        )
        db_session.add(snap)

    await db_session.commit()
    await db_session.refresh(building)
    return building


# ---------------------------------------------------------------------------
# 1. Fragmentation Score (6 tests)
# ---------------------------------------------------------------------------


class TestFragmentationScore:
    @pytest.mark.asyncio
    async def test_bare_building_high_fragmentation(self, db_session: AsyncSession, bare_building: Building):
        from app.services.indispensability_service import compute_fragmentation_score

        result = await compute_fragmentation_score(db_session, bare_building.id)
        assert result["fragmentation_score"] >= 80.0, "Empty building should be highly fragmented"

    @pytest.mark.asyncio
    async def test_enriched_building_sources_unified(self, db_session: AsyncSession, enriched_building: Building):
        from app.services.indispensability_service import compute_fragmentation_score

        result = await compute_fragmentation_score(db_session, enriched_building.id)
        assert result["sources_unified"] > 0

    @pytest.mark.asyncio
    async def test_documents_with_provenance_counted(self, db_session: AsyncSession, enriched_building: Building):
        from app.services.indispensability_service import compute_fragmentation_score

        result = await compute_fragmentation_score(db_session, enriched_building.id)
        assert result["documents_with_provenance"] == 3

    @pytest.mark.asyncio
    async def test_contradictions_detected_counted(self, db_session: AsyncSession, enriched_building: Building):
        from app.services.indispensability_service import compute_fragmentation_score

        result = await compute_fragmentation_score(db_session, enriched_building.id)
        assert result["contradictions_detected"] == 2

    @pytest.mark.asyncio
    async def test_score_between_0_and_100(self, db_session: AsyncSession, enriched_building: Building):
        from app.services.indispensability_service import compute_fragmentation_score

        result = await compute_fragmentation_score(db_session, enriched_building.id)
        assert 0.0 <= result["fragmentation_score"] <= 100.0

    @pytest.mark.asyncio
    async def test_systems_replaced_non_empty(self, db_session: AsyncSession, enriched_building: Building):
        from app.services.indispensability_service import compute_fragmentation_score

        result = await compute_fragmentation_score(db_session, enriched_building.id)
        assert len(result["systems_replaced"]) > 0


# ---------------------------------------------------------------------------
# 2. Defensibility Score (5 tests)
# ---------------------------------------------------------------------------


class TestDefensibilityScore:
    @pytest.mark.asyncio
    async def test_no_decisions_low_defensibility(self, db_session: AsyncSession, bare_building: Building):
        from app.services.indispensability_service import compute_defensibility_score

        result = await compute_defensibility_score(db_session, bare_building.id)
        assert result["defensibility_score"] == 0.0

    @pytest.mark.asyncio
    async def test_action_items_tracked(self, db_session: AsyncSession, enriched_building: Building):
        from app.services.indispensability_service import compute_defensibility_score

        result = await compute_defensibility_score(db_session, enriched_building.id)
        assert result["decisions_tracked"] == 4

    @pytest.mark.asyncio
    async def test_snapshots_give_time_coverage(self, db_session: AsyncSession, enriched_building: Building):
        from app.services.indispensability_service import compute_defensibility_score

        result = await compute_defensibility_score(db_session, enriched_building.id)
        assert result["time_coverage_days"] > 0

    @pytest.mark.asyncio
    async def test_vulnerability_points_are_french(self, db_session: AsyncSession, bare_building: Building):
        from app.services.indispensability_service import compute_defensibility_score

        result = await compute_defensibility_score(db_session, bare_building.id)
        # All vulnerability points should be in French
        for vp in result["vulnerability_points"]:
            assert isinstance(vp, str)
            assert len(vp) > 5
            # French markers: accented chars or common French words
            has_french = any(w in vp.lower() for w in ["aucun", "pas", "document", "décision", "historique"])
            assert has_french, f"Expected French string, got: {vp}"

    @pytest.mark.asyncio
    async def test_defensibility_score_between_0_and_1(self, db_session: AsyncSession, enriched_building: Building):
        from app.services.indispensability_service import compute_defensibility_score

        result = await compute_defensibility_score(db_session, enriched_building.id)
        assert 0.0 <= result["defensibility_score"] <= 1.0


# ---------------------------------------------------------------------------
# 3. Counterfactual Analysis (4 tests)
# ---------------------------------------------------------------------------


class TestCounterfactualAnalysis:
    @pytest.mark.asyncio
    async def test_without_platform_zero_trust(self, db_session: AsyncSession, bare_building: Building):
        from app.services.indispensability_service import compute_counterfactual

        result = await compute_counterfactual(db_session, bare_building.id)
        assert result["without_platform"]["trust"] == 0.0
        assert result["without_platform"]["grade"] == "unknown"

    @pytest.mark.asyncio
    async def test_with_platform_reflects_state(self, db_session: AsyncSession, enriched_building: Building):
        from app.services.indispensability_service import compute_counterfactual

        result = await compute_counterfactual(db_session, enriched_building.id)
        # With platform should have some actual state (even if grade F for sparse data)
        assert "trust" in result["with_platform"]
        assert "grade" in result["with_platform"]

    @pytest.mark.asyncio
    async def test_delta_list_non_empty(self, db_session: AsyncSession, bare_building: Building):
        from app.services.indispensability_service import compute_counterfactual

        result = await compute_counterfactual(db_session, bare_building.id)
        assert len(result["delta"]) > 0

    @pytest.mark.asyncio
    async def test_cost_of_fragmentation_non_negative(self, db_session: AsyncSession, enriched_building: Building):
        from app.services.indispensability_service import compute_counterfactual

        result = await compute_counterfactual(db_session, enriched_building.id)
        assert result["cost_of_fragmentation"] >= 0.0


# ---------------------------------------------------------------------------
# 4. Integration (3 tests)
# ---------------------------------------------------------------------------


class TestIndispensabilityIntegration:
    @pytest.mark.asyncio
    async def test_full_report_contains_all_sections(self, db_session: AsyncSession, enriched_building: Building):
        from app.services.indispensability_service import get_indispensability_report

        report = await get_indispensability_report(db_session, enriched_building.id)
        assert "fragmentation" in report
        assert "defensibility" in report
        assert "counterfactual" in report
        assert "headline" in report

    @pytest.mark.asyncio
    async def test_portfolio_summary_aggregates(
        self, db_session: AsyncSession, bare_building: Building, enriched_building: Building
    ):
        from app.services.indispensability_service import get_portfolio_indispensability

        result = await get_portfolio_indispensability(
            db_session,
            [bare_building.id, enriched_building.id],
        )
        assert result["building_count"] == 2
        assert result["avg_fragmentation"] > 0.0
        assert result["total_documents"] >= 3

    @pytest.mark.asyncio
    async def test_headline_is_french_string(self, db_session: AsyncSession, enriched_building: Building):
        from app.services.indispensability_service import get_indispensability_report

        report = await get_indispensability_report(db_session, enriched_building.id)
        headline = report["headline"]
        assert isinstance(headline, str)
        assert len(headline) > 10
        # Should contain French words
        has_french = any(
            w in headline.lower()
            for w in ["bâtiment", "plateforme", "portefeuille", "fragmentation", "traçabilité", "consolidation"]
        )
        assert has_french, f"Expected French headline, got: {headline}"
