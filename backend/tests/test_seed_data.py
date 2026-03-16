"""
Tests for seed_data.py — validates seed structure, jurisdiction integration,
timeline events, action auto-generation, and evidence links.
"""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import func, select

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.event import Event
from app.models.evidence_link import EvidenceLink
from app.models.jurisdiction import Jurisdiction
from app.models.sample import Sample
from app.models.user import User
from app.seeds.seed_data import _CANTON_JURISDICTION, _risk_score, seed
from app.seeds.seed_jurisdictions import (
    ID_CH_BE,
    ID_CH_GE,
    ID_CH_VD,
    ID_CH_VS,
    ID_CH_ZH,
    JURISDICTIONS,
    seed_jurisdictions,
)
from app.services.action_generator import generate_actions_from_diagnostic

# ---------------------------------------------------------------------------
# Jurisdiction integration
# ---------------------------------------------------------------------------


class TestJurisdictionIntegration:
    """Tests that jurisdictions are properly integrated into the seed."""

    def test_canton_jurisdiction_mapping_covers_seeded_cantons(self):
        """The mapping covers the 5 cantons that have jurisdiction UUIDs."""
        assert _CANTON_JURISDICTION["VD"] == ID_CH_VD
        assert _CANTON_JURISDICTION["GE"] == ID_CH_GE
        assert _CANTON_JURISDICTION["ZH"] == ID_CH_ZH
        assert _CANTON_JURISDICTION["BE"] == ID_CH_BE
        assert _CANTON_JURISDICTION["VS"] == ID_CH_VS

    def test_canton_jurisdiction_mapping_returns_none_for_unknown(self):
        """Cantons without seeded jurisdictions return None via .get()."""
        assert _CANTON_JURISDICTION.get("TI") is None
        assert _CANTON_JURISDICTION.get("NE") is None
        assert _CANTON_JURISDICTION.get("AG") is None

    def test_jurisdiction_uuids_are_stable(self):
        """UUID values must remain stable for idempotent seeding."""
        assert uuid.UUID("00000000-0000-4000-a000-000000000003") == ID_CH_VD
        assert uuid.UUID("00000000-0000-4000-a000-000000000004") == ID_CH_GE
        assert uuid.UUID("00000000-0000-4000-a000-000000000005") == ID_CH_ZH
        assert uuid.UUID("00000000-0000-4000-a000-000000000006") == ID_CH_BE
        assert uuid.UUID("00000000-0000-4000-a000-000000000007") == ID_CH_VS

    def test_jurisdiction_seed_data_has_swiss_cantons(self):
        """JURISDICTIONS list includes at least VD, GE, ZH, BE, VS."""
        codes = {j["code"] for j in JURISDICTIONS}
        assert {"ch-vd", "ch-ge", "ch-zh", "ch-be", "ch-vs"}.issubset(codes)

    async def test_seed_jurisdictions_creates_records(self, db_session):
        """seed_jurisdictions creates jurisdiction records in the database."""
        # Patch AsyncSessionLocal to use our test session

        from app.seeds import seed_jurisdictions as sj_module

        # Create a context manager that yields the test session
        class FakeSessionCtx:
            async def __aenter__(self):
                return db_session

            async def __aexit__(self, *args):
                pass

        with patch.object(sj_module, "AsyncSessionLocal", return_value=FakeSessionCtx()):
            await seed_jurisdictions()

        result = await db_session.execute(select(func.count()).select_from(Jurisdiction))
        count = result.scalar()
        assert count == len(JURISDICTIONS)

        # Verify VD exists
        result = await db_session.execute(select(Jurisdiction).where(Jurisdiction.id == ID_CH_VD))
        vd = result.scalar_one()
        assert vd.code == "ch-vd"
        assert vd.name == "Canton de Vaud"


# ---------------------------------------------------------------------------
# Risk score computation
# ---------------------------------------------------------------------------


class TestRiskScore:
    """Tests for _risk_score helper used in seed."""

    def test_1962_vd_residential(self):
        scores = _risk_score(1962, "VD", "residential")
        assert scores["overall_risk_level"] in ("high", "critical")
        assert scores["asbestos_probability"] > 0.5
        assert scores["confidence"] == 0.80

    def test_2010_modern_building(self):
        scores = _risk_score(2010, "VD", "commercial")
        assert scores["overall_risk_level"] in ("low", "medium")
        assert scores["asbestos_probability"] < 0.1

    def test_industrial_multiplier(self):
        """Industrial buildings should have higher probabilities."""
        residential = _risk_score(1970, "BE", "residential")
        industrial = _risk_score(1970, "BE", "industrial")
        assert industrial["asbestos_probability"] >= residential["asbestos_probability"]
        assert industrial["hap_probability"] >= residential["hap_probability"]

    def test_none_construction_year(self):
        scores = _risk_score(None, "ZH", "residential")
        assert scores["confidence"] == 0.65
        assert scores["overall_risk_level"] in ("low", "medium", "high", "critical")


# ---------------------------------------------------------------------------
# Action generation integration
# ---------------------------------------------------------------------------


class TestActionGeneration:
    """Tests that action auto-generation works for completed diagnostics."""

    async def test_generates_actions_for_completed_diagnostic(self, db_session):
        """generate_actions_from_diagnostic creates actions for threshold-exceeded samples."""
        # Create minimal user
        user = User(
            id=uuid.uuid4(),
            email="test-action-gen@test.ch",
            password_hash="fakehash",
            first_name="Test",
            last_name="Gen",
            role="diagnostician",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Create building
        building = Building(
            id=uuid.uuid4(),
            address="Test 1",
            postal_code="1000",
            city="Test",
            canton="VD",
            building_type="residential",
            created_by=user.id,
        )
        db_session.add(building)
        await db_session.flush()

        # Create completed diagnostic
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building.id,
            diagnostic_type="full",
            status="completed",
            diagnostician_id=user.id,
        )
        db_session.add(diag)
        await db_session.flush()

        # Create sample with threshold exceeded
        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="TEST-001",
            pollutant_type="asbestos",
            concentration=15.0,
            unit="percent_weight",
            threshold_exceeded=True,
            material_category="floor_covering_vinyl",
            material_state="intact",
        )
        db_session.add(sample)
        await db_session.commit()

        # Generate actions
        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)

        # Should create at least one action (asbestos remediation + upload document)
        assert len(actions) >= 1
        action_types = [a.action_type for a in actions]
        assert "remediation" in action_types

    async def test_idempotent_action_generation(self, db_session):
        """Running generate_actions twice should not create duplicate actions."""
        user = User(
            id=uuid.uuid4(),
            email="test-idempotent@test.ch",
            password_hash="fakehash",
            first_name="Test",
            last_name="Idemp",
            role="diagnostician",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        building = Building(
            id=uuid.uuid4(),
            address="Test 2",
            postal_code="1000",
            city="Test",
            canton="VD",
            building_type="residential",
            created_by=user.id,
        )
        db_session.add(building)
        await db_session.flush()

        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building.id,
            diagnostic_type="full",
            status="completed",
            diagnostician_id=user.id,
        )
        db_session.add(diag)
        await db_session.flush()

        sample = Sample(
            id=uuid.uuid4(),
            diagnostic_id=diag.id,
            sample_number="TEST-002",
            pollutant_type="pcb",
            concentration=120.0,
            unit="mg_per_kg",
            threshold_exceeded=True,
            material_category="sealant",
            material_state="degraded",
        )
        db_session.add(sample)
        await db_session.commit()

        first_run = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        second_run = await generate_actions_from_diagnostic(db_session, building.id, diag.id)

        assert len(first_run) >= 1
        assert len(second_run) == 0  # No duplicates

    async def test_no_actions_for_draft_diagnostic(self, db_session):
        """Draft diagnostics should not generate actions."""
        user = User(
            id=uuid.uuid4(),
            email="test-draft@test.ch",
            password_hash="fakehash",
            first_name="Test",
            last_name="Draft",
            role="diagnostician",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        building = Building(
            id=uuid.uuid4(),
            address="Test 3",
            postal_code="1000",
            city="Test",
            canton="VD",
            building_type="residential",
            created_by=user.id,
        )
        db_session.add(building)
        await db_session.flush()

        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building.id,
            diagnostic_type="full",
            status="draft",
            diagnostician_id=user.id,
        )
        db_session.add(diag)
        await db_session.commit()

        actions = await generate_actions_from_diagnostic(db_session, building.id, diag.id)
        assert len(actions) == 0


# ---------------------------------------------------------------------------
# Evidence links structure
# ---------------------------------------------------------------------------


class TestEvidenceLinkStructure:
    """Tests that evidence link model supports the required relationships."""

    async def test_evidence_link_creation(self, db_session):
        """EvidenceLink can be created with required fields."""
        link = EvidenceLink(
            id=uuid.uuid4(),
            source_type="diagnostic",
            source_id=uuid.uuid4(),
            target_type="building_risk_score",
            target_id=uuid.uuid4(),
            relationship="supports",
            confidence=0.85,
            explanation="Test evidence link",
        )
        db_session.add(link)
        await db_session.commit()

        result = await db_session.execute(select(EvidenceLink).where(EvidenceLink.id == link.id))
        fetched = result.scalar_one()
        assert fetched.source_type == "diagnostic"
        assert fetched.target_type == "building_risk_score"
        assert fetched.relationship == "supports"
        assert fetched.confidence == 0.85

    async def test_multiple_relationship_types(self, db_session):
        """EvidenceLink supports various relationship types used in seed."""
        relationship_types = ["proves", "supports", "triggers", "requires", "supersedes", "contradicts"]
        for rel_type in relationship_types:
            link = EvidenceLink(
                id=uuid.uuid4(),
                source_type="sample",
                source_id=uuid.uuid4(),
                target_type="building_risk_score",
                target_id=uuid.uuid4(),
                relationship=rel_type,
                confidence=0.9,
            )
            db_session.add(link)

        await db_session.commit()

        result = await db_session.execute(select(func.count()).select_from(EvidenceLink))
        count = result.scalar()
        assert count == len(relationship_types)


# ---------------------------------------------------------------------------
# Timeline events structure
# ---------------------------------------------------------------------------


class TestTimelineEvents:
    """Tests that Event model supports the event types used in the seed."""

    async def test_event_types_used_in_seed(self, db_session):
        """Verify all event types from the rich timeline can be stored."""
        user = User(
            id=uuid.uuid4(),
            email="test-events@test.ch",
            password_hash="fakehash",
            first_name="Test",
            last_name="Events",
            role="admin",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        building = Building(
            id=uuid.uuid4(),
            address="Test Events 1",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            created_by=user.id,
        )
        db_session.add(building)
        await db_session.flush()

        event_types = [
            "construction",
            "renovation",
            "diagnostic_completed",
            "diagnostic_validated",
            "diagnostic_started",
            "document_uploaded",
            "intervention_completed",
            "intervention_started",
            "sample_result",
            "notification_sent",
            "inspection_planned",
        ]

        for i, evt_type in enumerate(event_types):
            evt = Event(
                id=uuid.uuid4(),
                building_id=building.id,
                event_type=evt_type,
                date=date(2025, 1, i + 1),
                title=f"Test {evt_type}",
                created_by=user.id,
                metadata_json={"test": True},
            )
            db_session.add(evt)

        await db_session.commit()

        result = await db_session.execute(
            select(func.count()).select_from(Event).where(Event.building_id == building.id)
        )
        count = result.scalar()
        assert count == len(event_types)


# ---------------------------------------------------------------------------
# Seed function structure
# ---------------------------------------------------------------------------


class TestSeedStructure:
    """Tests that the seed function is properly structured."""

    async def test_seed_calls_seed_jurisdictions(self):
        """seed() should call seed_jurisdictions() before creating data."""
        with (
            patch("app.seeds.seed_data.seed_jurisdictions", new_callable=AsyncMock) as mock_jur,
            patch("app.seeds.seed_data.AsyncSessionLocal") as mock_session_cls,
        ):
            # Make the session check return an existing user (short-circuit)
            mock_session = AsyncMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session_cls.return_value = mock_ctx

            mock_result = MagicMock()
            existing_admin = MagicMock()
            existing_admin.password_hash = "$2b$12$LJ3m4ys3Lf.MpkBpOoWIyuFSMqGBNqXDB0QOsfXpHnRJfOQ8TxJzG"
            mock_result.scalar_one_or_none.return_value = existing_admin
            mock_session.execute = AsyncMock(return_value=mock_result)

            await seed()

            mock_jur.assert_called_once()

    async def test_seed_idempotency_skips_when_data_exists(self, capsys):
        """seed() should skip if admin user already exists."""
        with (
            patch("app.seeds.seed_data.seed_jurisdictions", new_callable=AsyncMock),
            patch("app.seeds.seed_data.AsyncSessionLocal") as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session_cls.return_value = mock_ctx

            mock_result = MagicMock()
            existing_admin = MagicMock()
            existing_admin.password_hash = "$2b$12$LJ3m4ys3Lf.MpkBpOoWIyuFSMqGBNqXDB0QOsfXpHnRJfOQ8TxJzG"
            mock_result.scalar_one_or_none.return_value = existing_admin
            mock_session.execute = AsyncMock(return_value=mock_result)

            await seed()

            out = capsys.readouterr().out
            assert "skipping" in out.lower()


# ---------------------------------------------------------------------------
# Building jurisdiction assignment
# ---------------------------------------------------------------------------


class TestBuildingJurisdiction:
    """Tests that buildings get correct jurisdiction_id."""

    async def test_building_with_jurisdiction(self, db_session):
        """Building model accepts jurisdiction_id FK."""
        # Create jurisdiction first
        jur = Jurisdiction(
            id=ID_CH_VD,
            code="ch-vd",
            name="Canton de Vaud",
            level="region",
            is_active=True,
        )
        db_session.add(jur)
        await db_session.flush()

        user = User(
            id=uuid.uuid4(),
            email="test-jur@test.ch",
            password_hash="fakehash",
            first_name="Test",
            last_name="Jur",
            role="admin",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        building = Building(
            id=uuid.uuid4(),
            address="Rue Test 1",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            building_type="residential",
            created_by=user.id,
            jurisdiction_id=ID_CH_VD,
        )
        db_session.add(building)
        await db_session.commit()

        result = await db_session.execute(select(Building).where(Building.id == building.id))
        fetched = result.scalar_one()
        assert fetched.jurisdiction_id == ID_CH_VD

    async def test_building_without_jurisdiction(self, db_session):
        """Building model accepts None jurisdiction_id (for cantons without seeded jurisdictions)."""
        user = User(
            id=uuid.uuid4(),
            email="test-nojur@test.ch",
            password_hash="fakehash",
            first_name="Test",
            last_name="NoJur",
            role="admin",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        building = Building(
            id=uuid.uuid4(),
            address="Via Test 1",
            postal_code="6900",
            city="Lugano",
            canton="TI",
            building_type="commercial",
            created_by=user.id,
            jurisdiction_id=None,
        )
        db_session.add(building)
        await db_session.commit()

        result = await db_session.execute(select(Building).where(Building.id == building.id))
        fetched = result.scalar_one()
        assert fetched.jurisdiction_id is None
