"""Tests for score explainability service — proof trail for every metric."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.data_quality_issue import DataQualityIssue
from app.models.document import Document
from app.models.enrichment_run import BuildingEnrichmentRun
from app.models.evidence_link import EvidenceLink
from app.models.organization import Organization
from app.models.source_snapshot import BuildingSourceSnapshot
from app.models.user import User
from app.services.score_explainability_service import explain_building_scores

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def expl_org(db_session: AsyncSession):
    org = Organization(
        id=uuid.uuid4(),
        name="Explainability Test Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def expl_user(db_session: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        email="expl-test@test.ch",
        password_hash="$2b$12$LJ3m4ys3uz0MHl0BF6zz0u4.bfPKEfRz0PnWkKlCem0clfb/E.iai",
        first_name="Expl",
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
async def expl_building(db_session: AsyncSession, expl_org: Organization, expl_user: User):
    building = Building(
        id=uuid.uuid4(),
        address="123 Rue Explainability, 1000 Lausanne",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        organization_id=expl_org.id,
        created_by=expl_user.id,
        construction_year=1980,
    )
    db_session.add(building)
    await db_session.commit()
    await db_session.refresh(building)
    return building


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExplainBuildingScoresEmpty:
    """Test with a building that has no data — baseline."""

    @pytest.mark.asyncio
    async def test_nonexistent_building_returns_none(self, db_session: AsyncSession):
        result = await explain_building_scores(db_session, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_building_returns_report(self, db_session: AsyncSession, expl_building: Building):
        result = await explain_building_scores(db_session, expl_building.id)
        assert result is not None
        assert result.building_id == expl_building.id
        assert len(result.scores) == 7  # 5 base + hours + chf
        assert result.total_line_items == 0
        assert result.methodology_summary

    @pytest.mark.asyncio
    async def test_empty_building_all_scores_zero(self, db_session: AsyncSession, expl_building: Building):
        result = await explain_building_scores(db_session, expl_building.id)
        assert result is not None
        for score in result.scores:
            assert score.value == 0.0
            assert score.line_items == []

    @pytest.mark.asyncio
    async def test_score_names_correct(self, db_session: AsyncSession, expl_building: Building):
        result = await explain_building_scores(db_session, expl_building.id)
        assert result is not None
        names = [s.metric_name for s in result.scores]
        assert names == [
            "sources_unified",
            "contradictions_resolved",
            "proof_chains_count",
            "documents_with_provenance",
            "decisions_backed",
            "hours_saved",
            "value_chf",
        ]


class TestExplainBuildingScoresWithData:
    """Test with populated building data — each metric has line items."""

    @pytest.mark.asyncio
    async def test_sources_unified_line_items(
        self,
        db_session: AsyncSession,
        expl_building: Building,
    ):
        # Add enrichment run
        run = BuildingEnrichmentRun(
            id=uuid.uuid4(),
            building_id=expl_building.id,
            address_input=expl_building.address,
            status="completed",
            sources_attempted=3,
            sources_succeeded=2,
            sources_failed=1,
            created_at=datetime.now(UTC),
        )
        db_session.add(run)

        # Add source snapshot
        snap = BuildingSourceSnapshot(
            id=uuid.uuid4(),
            building_id=expl_building.id,
            enrichment_run_id=run.id,
            source_name="RegBL",
            source_category="identity",
            confidence="high",
            fetched_at=datetime.now(UTC),
        )
        db_session.add(snap)
        await db_session.commit()

        result = await explain_building_scores(db_session, expl_building.id)
        assert result is not None

        sources_score = next(s for s in result.scores if s.metric_name == "sources_unified")
        assert sources_score.value == 2.0  # 1 run + 1 snapshot
        assert len(sources_score.line_items) == 2
        assert sources_score.confidence == "exact"
        assert all(li.item_type == "enrichment_source" for li in sources_score.line_items)

    @pytest.mark.asyncio
    async def test_contradictions_line_items(
        self,
        db_session: AsyncSession,
        expl_building: Building,
    ):
        issue = DataQualityIssue(
            id=uuid.uuid4(),
            building_id=expl_building.id,
            issue_type="contradiction",
            severity="high",
            status="resolved",
            field_name="construction_year",
            description="Année de construction contradictoire entre RegBL et diagnostic",
            resolution_notes="Valeur du diagnostic retenue (1982)",
        )
        db_session.add(issue)
        await db_session.commit()

        result = await explain_building_scores(db_session, expl_building.id)
        assert result is not None

        contra_score = next(s for s in result.scores if s.metric_name == "contradictions_resolved")
        assert contra_score.value == 1.0
        assert len(contra_score.line_items) == 1
        li = contra_score.line_items[0]
        assert li.item_type == "contradiction"
        assert "construction_year" in li.label
        assert "Résolution:" in li.detail

    @pytest.mark.asyncio
    async def test_documents_with_provenance_line_items(
        self,
        db_session: AsyncSession,
        expl_building: Building,
        expl_user: User,
    ):
        doc = Document(
            id=uuid.uuid4(),
            building_id=expl_building.id,
            file_path="/uploads/test.pdf",
            file_name="rapport_amiante.pdf",
            document_type="diagnostic_report",
            content_hash="abc123def456789012345678901234567890123456789012345678901234",
            uploaded_by=expl_user.id,
        )
        db_session.add(doc)
        await db_session.commit()

        result = await explain_building_scores(db_session, expl_building.id)
        assert result is not None

        docs_score = next(s for s in result.scores if s.metric_name == "documents_with_provenance")
        assert docs_score.value == 1.0
        assert len(docs_score.line_items) == 1
        li = docs_score.line_items[0]
        assert li.item_type == "document"
        assert "rapport_amiante.pdf" in li.label
        assert "SHA-256" in li.detail
        assert li.link == f"/buildings/{expl_building.id}/documents"

    @pytest.mark.asyncio
    async def test_hours_and_chf_aggregate(
        self,
        db_session: AsyncSession,
        expl_building: Building,
        expl_user: User,
    ):
        # Add a document (0.5h) + enrichment run (2h) = 2.5h, 375 CHF
        doc = Document(
            id=uuid.uuid4(),
            building_id=expl_building.id,
            file_path="/uploads/test2.pdf",
            file_name="plan.pdf",
            document_type="plan",
            content_hash="aaabbbccc123456789012345678901234567890123456789012345678901",
            uploaded_by=expl_user.id,
        )
        run = BuildingEnrichmentRun(
            id=uuid.uuid4(),
            building_id=expl_building.id,
            address_input=expl_building.address,
            status="completed",
            sources_attempted=1,
            sources_succeeded=1,
            sources_failed=0,
            created_at=datetime.now(UTC),
        )
        db_session.add_all([doc, run])
        await db_session.commit()

        result = await explain_building_scores(db_session, expl_building.id)
        assert result is not None

        hours_score = next(s for s in result.scores if s.metric_name == "hours_saved")
        assert hours_score.value == 2.5  # 2h (source) + 0.5h (doc)
        assert hours_score.confidence == "estimated"
        assert len(hours_score.line_items) == 2

        chf_score = next(s for s in result.scores if s.metric_name == "value_chf")
        assert chf_score.value == 375.0  # 2.5h * 150
        assert chf_score.confidence == "heuristic"
        assert len(chf_score.line_items) == 2

    @pytest.mark.asyncio
    async def test_decisions_backed_line_items(
        self,
        db_session: AsyncSession,
        expl_building: Building,
        expl_user: User,
    ):
        action = ActionItem(
            id=uuid.uuid4(),
            building_id=expl_building.id,
            source_type="diagnostic",
            action_type="remediation",
            title="Retrait amiante niveau 2",
            priority="high",
            status="open",
        )
        db_session.add(action)
        await db_session.flush()

        # Add evidence link to this action
        ev_link = EvidenceLink(
            id=uuid.uuid4(),
            source_type="action_item",
            source_id=action.id,
            target_type="document",
            target_id=uuid.uuid4(),
            relationship="justifies",
            explanation="Rapport de diagnostic confirmant la présence d'amiante",
        )
        db_session.add(ev_link)
        await db_session.commit()

        result = await explain_building_scores(db_session, expl_building.id)
        assert result is not None

        decisions_score = next(s for s in result.scores if s.metric_name == "decisions_backed")
        assert decisions_score.value == 1.0
        assert len(decisions_score.line_items) == 1
        li = decisions_score.line_items[0]
        assert li.item_type == "action"
        assert "Retrait amiante" in li.label

    @pytest.mark.asyncio
    async def test_total_line_items_count(
        self,
        db_session: AsyncSession,
        expl_building: Building,
        expl_user: User,
    ):
        """Total line items should match sum of all score line items."""
        doc = Document(
            id=uuid.uuid4(),
            building_id=expl_building.id,
            file_path="/uploads/total.pdf",
            file_name="total.pdf",
            document_type="report",
            content_hash="zzz123def456789012345678901234567890123456789012345678901234",
            uploaded_by=expl_user.id,
        )
        db_session.add(doc)
        await db_session.commit()

        result = await explain_building_scores(db_session, expl_building.id)
        assert result is not None

        actual_total = sum(len(s.line_items) for s in result.scores)
        assert result.total_line_items == actual_total


class TestExplainScoreMetadata:
    """Test metadata fields: confidence, methodology, units, labels."""

    @pytest.mark.asyncio
    async def test_confidence_fields(self, db_session: AsyncSession, expl_building: Building):
        result = await explain_building_scores(db_session, expl_building.id)
        assert result is not None

        confidence_map = {s.metric_name: s.confidence for s in result.scores}
        assert confidence_map["sources_unified"] == "exact"
        assert confidence_map["contradictions_resolved"] == "exact"
        assert confidence_map["proof_chains_count"] == "exact"
        assert confidence_map["documents_with_provenance"] == "exact"
        assert confidence_map["decisions_backed"] == "exact"
        assert confidence_map["hours_saved"] == "estimated"
        assert confidence_map["value_chf"] == "heuristic"

    @pytest.mark.asyncio
    async def test_all_labels_french(self, db_session: AsyncSession, expl_building: Building):
        result = await explain_building_scores(db_session, expl_building.id)
        assert result is not None

        for score in result.scores:
            # Labels should be non-empty French strings
            assert score.metric_label
            assert score.methodology
            assert score.unit

    @pytest.mark.asyncio
    async def test_line_item_links_valid(
        self,
        db_session: AsyncSession,
        expl_building: Building,
        expl_user: User,
    ):
        doc = Document(
            id=uuid.uuid4(),
            building_id=expl_building.id,
            file_path="/uploads/link_test.pdf",
            file_name="link_test.pdf",
            document_type="plan",
            content_hash="lnk123def456789012345678901234567890123456789012345678901234",
            uploaded_by=expl_user.id,
        )
        db_session.add(doc)
        await db_session.commit()

        result = await explain_building_scores(db_session, expl_building.id)
        assert result is not None

        for score in result.scores:
            for li in score.line_items:
                # Links must start with /buildings/
                assert li.link.startswith(f"/buildings/{expl_building.id}")
