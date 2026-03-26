"""Tests for value ledger, value events, and indispensability export services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.data_quality_issue import DataQualityIssue
from app.models.document import Document
from app.models.organization import Organization
from app.models.user import User

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def vl_org(db_session: AsyncSession):
    org = Organization(
        id=uuid.uuid4(),
        name="Value Ledger Test Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def vl_user(db_session: AsyncSession):
    user = User(
        id=uuid.uuid4(),
        email="vl-test@test.ch",
        password_hash="$2b$12$LJ3m4ys3uz0MHl0BF6zz0u4.bfPKEfRz0PnWkKlCem0clfb/E.iai",
        first_name="VL",
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
async def empty_org(db_session: AsyncSession):
    """Organization with zero buildings."""
    org = Organization(
        id=uuid.uuid4(),
        name="Empty Org",
        type="property_management",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def org_with_buildings(db_session: AsyncSession, vl_user: User, vl_org: Organization):
    """Organization with buildings, documents, and resolved contradictions."""
    buildings = []
    for i in range(3):
        b = Building(
            id=uuid.uuid4(),
            address=f"Rue de la Valeur {i + 1}",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            created_by=vl_user.id,
            organization_id=vl_org.id,
            construction_year=1970 + i,
        )
        db_session.add(b)
        buildings.append(b)

    await db_session.flush()

    # Add documents with content_hash to first two buildings
    for b in buildings[:2]:
        for j in range(2):
            doc = Document(
                id=uuid.uuid4(),
                building_id=b.id,
                file_path=f"/docs/{b.id}_{j}.pdf",
                file_name=f"report_{j}.pdf",
                document_type="diagnostic_report",
                content_hash=f"sha256_{b.id}_{j}",
                uploaded_by=vl_user.id,
            )
            db_session.add(doc)

    # Add resolved contradictions to first building
    for k in range(2):
        dqi = DataQualityIssue(
            id=uuid.uuid4(),
            building_id=buildings[0].id,
            issue_type="contradiction",
            severity="medium",
            status="resolved",
            description=f"Resolved contradiction {k}",
            detected_by="system",
            resolved_at=datetime.now(UTC),
        )
        db_session.add(dqi)

    # Add open contradiction (should NOT count)
    dqi_open = DataQualityIssue(
        id=uuid.uuid4(),
        building_id=buildings[0].id,
        issue_type="contradiction",
        severity="medium",
        status="open",
        description="Open contradiction",
        detected_by="system",
    )
    db_session.add(dqi_open)

    await db_session.commit()
    for b in buildings:
        await db_session.refresh(b)
    return buildings


# ---------------------------------------------------------------------------
# 1. Value Ledger (6 tests)
# ---------------------------------------------------------------------------


class TestValueLedger:
    @pytest.mark.asyncio
    async def test_empty_org_all_counters_zero_and_stable(self, db_session: AsyncSession, empty_org: Organization):
        from app.services.value_ledger_service import get_value_ledger

        result = await get_value_ledger(db_session, empty_org.id)
        # Empty org returns None
        assert result is None

    @pytest.mark.asyncio
    async def test_org_with_buildings_documents_secured(
        self, db_session: AsyncSession, vl_org: Organization, org_with_buildings
    ):
        from app.services.value_ledger_service import get_value_ledger

        result = await get_value_ledger(db_session, vl_org.id)
        assert result is not None
        assert result.documents_secured_total > 0

    @pytest.mark.asyncio
    async def test_contradictions_resolved_counted(
        self, db_session: AsyncSession, vl_org: Organization, org_with_buildings
    ):
        from app.services.value_ledger_service import get_value_ledger

        result = await get_value_ledger(db_session, vl_org.id)
        assert result is not None
        assert result.contradictions_resolved_total == 2

    @pytest.mark.asyncio
    async def test_hours_saved_non_negative(self, db_session: AsyncSession, vl_org: Organization, org_with_buildings):
        from app.services.value_ledger_service import get_value_ledger

        result = await get_value_ledger(db_session, vl_org.id)
        assert result is not None
        assert result.hours_saved_estimate >= 0.0

    @pytest.mark.asyncio
    async def test_value_chf_equals_hours_times_150(
        self, db_session: AsyncSession, vl_org: Organization, org_with_buildings
    ):
        from app.services.value_ledger_service import get_value_ledger

        result = await get_value_ledger(db_session, vl_org.id)
        assert result is not None
        expected = round(result.hours_saved_estimate * 150, 2)
        assert result.value_chf_estimate == expected

    @pytest.mark.asyncio
    async def test_days_active_from_first_building(
        self, db_session: AsyncSession, vl_org: Organization, org_with_buildings
    ):
        from app.services.value_ledger_service import get_value_ledger

        result = await get_value_ledger(db_session, vl_org.id)
        assert result is not None
        # days_active should be at least 0 (building just created)
        assert result.days_active >= 0


# ---------------------------------------------------------------------------
# 2. Value Events (3 tests)
# ---------------------------------------------------------------------------


class TestValueEvents:
    @pytest.mark.asyncio
    async def test_record_value_event_creates_domain_event(
        self, db_session: AsyncSession, vl_org: Organization, org_with_buildings
    ):
        from app.services.value_ledger_service import record_value_event

        building_id = org_with_buildings[0].id
        await record_value_event(
            db_session,
            org_id=vl_org.id,
            event_type="document_secured",
            building_id=building_id,
            delta_description="Document sécurisé avec hash SHA-256",
        )
        await db_session.commit()

        # Verify DomainEvent was created
        from sqlalchemy import select

        from app.models.domain_event import DomainEvent

        q = select(DomainEvent).where(
            DomainEvent.aggregate_type == "organization",
            DomainEvent.aggregate_id == vl_org.id,
        )
        result = await db_session.execute(q)
        events = list(result.scalars().all())
        assert len(events) >= 1
        assert events[0].event_type == "value_accumulated"

    @pytest.mark.asyncio
    async def test_value_events_retrievable_and_sorted(
        self, db_session: AsyncSession, vl_org: Organization, org_with_buildings
    ):
        from app.services.value_ledger_service import get_value_events, record_value_event

        # Record two events
        await record_value_event(
            db_session,
            org_id=vl_org.id,
            event_type="contradiction_resolved",
            building_id=org_with_buildings[0].id,
            delta_description="Contradiction résolue",
        )
        await record_value_event(
            db_session,
            org_id=vl_org.id,
            event_type="proof_chain_created",
            building_id=org_with_buildings[1].id,
            delta_description="Chaîne de preuves créée",
        )
        await db_session.commit()

        events = await get_value_events(db_session, vl_org.id)
        assert len(events) >= 2
        # Should be sorted by date descending
        for i in range(len(events) - 1):
            assert events[i].created_at >= events[i + 1].created_at

    @pytest.mark.asyncio
    async def test_delta_description_non_empty(
        self, db_session: AsyncSession, vl_org: Organization, org_with_buildings
    ):
        from app.services.value_ledger_service import get_value_events, record_value_event

        await record_value_event(
            db_session,
            org_id=vl_org.id,
            event_type="source_unified",
            building_id=None,
            delta_description="Source de données unifiée",
        )
        await db_session.commit()

        events = await get_value_events(db_session, vl_org.id)
        assert len(events) >= 1
        for e in events:
            assert isinstance(e.delta_description, str)
            assert len(e.delta_description) > 0


# ---------------------------------------------------------------------------
# 3. Indispensability Export (5 tests)
# ---------------------------------------------------------------------------


class TestIndispensabilityExport:
    @pytest.mark.asyncio
    async def test_building_export_title_contains_address(
        self, db_session: AsyncSession, vl_org: Organization, org_with_buildings
    ):
        from app.services.indispensability_export_service import build_indispensability_export

        building = org_with_buildings[0]
        export = await build_indispensability_export(db_session, building.id, vl_org.id)
        assert building.address in export.title

    @pytest.mark.asyncio
    async def test_executive_summary_non_empty_french(
        self, db_session: AsyncSession, vl_org: Organization, org_with_buildings
    ):
        from app.services.indispensability_export_service import build_indispensability_export

        building = org_with_buildings[0]
        export = await build_indispensability_export(db_session, building.id, vl_org.id)
        assert isinstance(export.executive_summary, str)
        assert len(export.executive_summary) > 20
        # Should contain French words
        has_french = any(
            w in export.executive_summary.lower()
            for w in ["rapport", "bâtiment", "valeur", "fragmentation", "plateforme", "démontre"]
        )
        assert has_french, f"Expected French text, got: {export.executive_summary}"

    @pytest.mark.asyncio
    async def test_export_contains_all_sections(
        self, db_session: AsyncSession, vl_org: Organization, org_with_buildings
    ):
        from app.services.indispensability_export_service import build_indispensability_export

        building = org_with_buildings[0]
        export = await build_indispensability_export(db_session, building.id, vl_org.id)
        assert export.fragmentation_section is not None
        assert export.defensibility_section is not None
        assert export.counterfactual_section is not None
        assert export.value_ledger_section is not None

    @pytest.mark.asyncio
    async def test_recommendation_contains_swissbuilding(
        self, db_session: AsyncSession, vl_org: Organization, org_with_buildings
    ):
        from app.services.indispensability_export_service import build_indispensability_export

        building = org_with_buildings[0]
        export = await build_indispensability_export(db_session, building.id, vl_org.id)
        assert isinstance(export.recommendation, str)
        assert len(export.recommendation) > 0
        assert "SwissBuilding" in export.recommendation

    @pytest.mark.asyncio
    async def test_portfolio_export_aggregates_buildings(
        self, db_session: AsyncSession, vl_org: Organization, org_with_buildings
    ):
        from app.services.indispensability_export_service import (
            build_portfolio_indispensability_export,
        )

        building_ids = [b.id for b in org_with_buildings]
        export = await build_portfolio_indispensability_export(db_session, vl_org.id, building_ids)
        assert export.buildings_count == len(org_with_buildings)
        assert export.fragmentation_section is not None
        assert export.value_ledger_section is not None
        assert len(export.executive_summary) > 20
