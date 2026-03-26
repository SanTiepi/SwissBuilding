"""Tests for enrichment tracking: EnrichmentRun, SourceSnapshot, address preview, instant card."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.api.instant_card import router as instant_card_router
from app.main import app as _app
from app.models.building import Building
from app.models.enrichment_run import BuildingEnrichmentRun
from app.models.source_snapshot import BuildingSourceSnapshot

# Register instant_card routes if not already present
_registered_paths = {r.path for r in _app.routes}
if "/api/v1/intelligence/address-preview" not in _registered_paths:
    _app.include_router(instant_card_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestEnrichmentRunModel:
    """Test BuildingEnrichmentRun model."""

    @pytest.mark.asyncio
    async def test_create_enrichment_run(self, db_session):
        """EnrichmentRun can be created with building_id=null (address preview)."""
        run = BuildingEnrichmentRun(
            id=uuid.uuid4(),
            building_id=None,
            address_input="Rue de Bourg 1 1003 Lausanne",
            status="pending",
            sources_attempted=0,
            sources_succeeded=0,
            sources_failed=0,
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        assert run.id is not None
        assert run.building_id is None
        assert run.address_input == "Rue de Bourg 1 1003 Lausanne"
        assert run.status == "pending"

    @pytest.mark.asyncio
    async def test_enrichment_run_with_building(self, db_session, sample_building):
        """EnrichmentRun can reference an existing building."""
        run = BuildingEnrichmentRun(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            address_input=sample_building.address,
            status="completed",
            sources_attempted=5,
            sources_succeeded=4,
            sources_failed=1,
            duration_ms=1234,
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        assert run.building_id == sample_building.id
        assert run.sources_attempted == 5
        assert run.sources_succeeded == 4
        assert run.sources_failed == 1
        assert run.duration_ms == 1234

    @pytest.mark.asyncio
    async def test_enrichment_run_status_values(self, db_session):
        """EnrichmentRun supports all status values."""
        for status in ("pending", "running", "completed", "failed"):
            run = BuildingEnrichmentRun(
                id=uuid.uuid4(),
                address_input="Test Address",
                status=status,
            )
            db_session.add(run)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_enrichment_run_error_summary(self, db_session):
        """EnrichmentRun can store error summary."""
        run = BuildingEnrichmentRun(
            id=uuid.uuid4(),
            address_input="Bad Address",
            status="failed",
            error_summary="geocode: timeout; regbl: 404",
        )
        db_session.add(run)
        await db_session.commit()
        await db_session.refresh(run)

        assert run.error_summary == "geocode: timeout; regbl: 404"


class TestSourceSnapshotModel:
    """Test BuildingSourceSnapshot model."""

    @pytest.mark.asyncio
    async def test_create_snapshot(self, db_session, sample_building):
        """SourceSnapshot stores raw + normalized data."""
        snap = BuildingSourceSnapshot(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            source_name="geo.admin.ch/gwr",
            source_category="identity",
            raw_data={"gbauj": 1965, "gastw": 4},
            normalized_data={"construction_year": 1965, "floors": 4},
            fetched_at=datetime.now(UTC),
            freshness_state="current",
            confidence="high",
        )
        db_session.add(snap)
        await db_session.commit()
        await db_session.refresh(snap)

        assert snap.source_name == "geo.admin.ch/gwr"
        assert snap.source_category == "identity"
        assert snap.normalized_data["construction_year"] == 1965
        assert snap.confidence == "high"

    @pytest.mark.asyncio
    async def test_snapshot_without_building(self, db_session):
        """SourceSnapshot can exist without building (address preview)."""
        run = BuildingEnrichmentRun(
            id=uuid.uuid4(),
            address_input="Preview Address",
            status="completed",
        )
        db_session.add(run)
        await db_session.flush()

        snap = BuildingSourceSnapshot(
            id=uuid.uuid4(),
            building_id=None,
            enrichment_run_id=run.id,
            source_name="ch.bag.radonkarte",
            source_category="environment",
            raw_data={"risk_level": "medium"},
            normalized_data={"risk_level": "medium"},
            fetched_at=datetime.now(UTC),
        )
        db_session.add(snap)
        await db_session.commit()
        await db_session.refresh(snap)

        assert snap.building_id is None
        assert snap.enrichment_run_id == run.id

    @pytest.mark.asyncio
    async def test_snapshot_categories(self, db_session):
        """SourceSnapshot supports all source categories."""
        categories = [
            "identity",
            "environment",
            "energy",
            "transport",
            "risk",
            "social",
            "regulatory",
            "computed",
        ]
        for cat in categories:
            snap = BuildingSourceSnapshot(
                id=uuid.uuid4(),
                source_name=f"test/{cat}",
                source_category=cat,
                raw_data={},
                fetched_at=datetime.now(UTC),
            )
            db_session.add(snap)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_snapshot_freshness_values(self, db_session):
        """SourceSnapshot supports current/aging/stale freshness states."""
        for state in ("current", "aging", "stale"):
            snap = BuildingSourceSnapshot(
                id=uuid.uuid4(),
                source_name="test/freshness",
                source_category="identity",
                raw_data={},
                fetched_at=datetime.now(UTC),
                freshness_state=state,
            )
            db_session.add(snap)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_snapshot_confidence_values(self, db_session):
        """SourceSnapshot supports high/medium/low confidence."""
        for conf in ("high", "medium", "low"):
            snap = BuildingSourceSnapshot(
                id=uuid.uuid4(),
                source_name="test/conf",
                source_category="identity",
                raw_data={},
                fetched_at=datetime.now(UTC),
                confidence=conf,
            )
            db_session.add(snap)
        await db_session.commit()


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestFreshnessComputation:
    """Test freshness state computation."""

    def test_current_freshness(self):
        from app.services.address_preview_service import _freshness

        now = datetime.now(UTC)
        assert _freshness(now) == "current"

    def test_aging_freshness(self):
        from app.services.address_preview_service import _freshness

        two_days_ago = datetime.now(UTC) - timedelta(days=2)
        assert _freshness(two_days_ago) == "aging"

    def test_stale_freshness(self):
        from app.services.address_preview_service import _freshness

        two_weeks_ago = datetime.now(UTC) - timedelta(days=14)
        assert _freshness(two_weeks_ago) == "stale"


class TestConfidenceForSource:
    """Test source confidence assignment."""

    def test_geo_admin_high(self):
        from app.services.address_preview_service import _confidence_for_source

        assert _confidence_for_source("geo.admin.ch/gwr") == "high"

    def test_ch_source_high(self):
        from app.services.address_preview_service import _confidence_for_source

        assert _confidence_for_source("ch.bag.radonkarte") == "high"

    def test_computed_medium(self):
        from app.services.address_preview_service import _confidence_for_source

        assert _confidence_for_source("computed/scores") == "medium"


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestAddressPreviewSchemas:
    """Test address preview schemas."""

    def test_address_preview_request(self):
        from app.schemas.address_preview import AddressPreviewRequest

        req = AddressPreviewRequest(address="Rue de Bourg 1", postal_code="1003", city="Lausanne")
        assert req.address == "Rue de Bourg 1"
        assert req.postal_code == "1003"

    def test_address_preview_request_minimal(self):
        from app.schemas.address_preview import AddressPreviewRequest

        req = AddressPreviewRequest(address="Rue de Bourg 1")
        assert req.postal_code is None
        assert req.city is None

    def test_address_preview_result_defaults(self):
        from app.schemas.address_preview import AddressPreviewResult

        result = AddressPreviewResult()
        assert result.identity.egid is None
        assert result.physical.construction_year is None
        assert result.metadata.sources_used == []
        assert result.metadata.freshness == "current"

    def test_instant_card_result(self):
        from app.schemas.address_preview import InstantCardResult

        card = InstantCardResult(building_id=uuid.uuid4())
        assert card.building_id is not None
        assert card.identity.lat is None

    def test_source_snapshot_read(self):
        from app.schemas.address_preview import SourceSnapshotRead

        snap = SourceSnapshotRead(
            id=uuid.uuid4(),
            source_name="geo.admin.ch/gwr",
            source_category="identity",
            freshness_state="current",
            confidence="high",
        )
        assert snap.source_name == "geo.admin.ch/gwr"

    def test_enrichment_run_read(self):
        from app.schemas.address_preview import EnrichmentRunRead

        run = EnrichmentRunRead(
            id=uuid.uuid4(),
            address_input="Test",
            status="completed",
            sources_attempted=10,
            sources_succeeded=8,
            sources_failed=2,
        )
        assert run.status == "completed"
        assert run.sources_attempted == 10


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


class TestAddressPreviewAPI:
    """Test address preview API endpoint."""

    @pytest.mark.asyncio
    async def test_address_preview_returns_structured_data(self, client, auth_headers):
        """POST /intelligence/address-preview returns structured result."""
        with (
            patch(
                "app.services.building_enrichment_service.geocode_address",
                new_callable=AsyncMock,
                return_value={"lat": 46.5197, "lon": 6.6323, "egid": 12345},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_regbl_data",
                new_callable=AsyncMock,
                return_value={"construction_year": 1965, "floors": 4, "dwellings": 8},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_radon_risk",
                new_callable=AsyncMock,
                return_value={"risk_level": "medium"},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_noise_data",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_natural_hazards",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_solar_potential",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_transport_quality",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_seismic_zone",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_nearest_stops",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            resp = await client.post(
                "/api/v1/intelligence/address-preview",
                json={"address": "Rue de Bourg 1", "postal_code": "1003"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["identity"]["lat"] == 46.5197
        assert data["identity"]["egid"] == 12345
        assert data["physical"]["construction_year"] == 1965
        assert data["environment"]["radon"]["risk_level"] == "medium"
        assert "run_id" in data["metadata"]
        assert len(data["metadata"]["sources_used"]) > 0

    @pytest.mark.asyncio
    async def test_address_preview_does_not_create_building(self, client, auth_headers, db_session):
        """Address preview is read-only — no Building created."""
        from sqlalchemy import func, select

        with (
            patch(
                "app.services.building_enrichment_service.geocode_address",
                new_callable=AsyncMock,
                return_value={"lat": 46.5, "lon": 6.6},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_radon_risk",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_noise_data",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_natural_hazards",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_solar_potential",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_transport_quality",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_seismic_zone",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "app.services.building_enrichment_service.fetch_nearest_stops",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            resp = await client.post(
                "/api/v1/intelligence/address-preview",
                json={"address": "Test Preview 99"},
                headers=auth_headers,
            )

        assert resp.status_code == 200

        # Verify no building was created
        count_stmt = select(func.count()).select_from(Building)
        result = await db_session.execute(count_stmt)
        count = result.scalar()
        # Only buildings from fixtures should exist (0 for this test since no sample_building fixture)
        assert count == 0


class TestInstantCardAPI:
    """Test instant card API endpoint."""

    @pytest.mark.asyncio
    async def test_instant_card_returns_aggregated_data(self, client, auth_headers, sample_building, db_session):
        """GET /buildings/{id}/instant-card returns aggregated card."""
        # Add a source snapshot
        snap = BuildingSourceSnapshot(
            id=uuid.uuid4(),
            building_id=sample_building.id,
            source_name="ch.bag.radonkarte",
            source_category="environment",
            raw_data={"risk": "low"},
            normalized_data={"risk_level": "low"},
            fetched_at=datetime.now(UTC),
            freshness_state="current",
            confidence="high",
        )
        db_session.add(snap)
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/instant-card",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["building_id"] == str(sample_building.id)
        assert data["identity"]["address_normalized"] == sample_building.address
        assert data["physical"]["construction_year"] == 1965
        assert data["environment"]["radon"]["risk_level"] == "low"

    @pytest.mark.asyncio
    async def test_instant_card_404_for_missing_building(self, client, auth_headers):
        """GET /buildings/{id}/instant-card returns 404 for unknown building."""
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/buildings/{fake_id}/instant-card",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestSourceSnapshotsAPI:
    """Test source snapshots API endpoint."""

    @pytest.mark.asyncio
    async def test_get_source_snapshots(self, client, auth_headers, sample_building, db_session):
        """GET /buildings/{id}/source-snapshots returns snapshots with freshness."""
        now = datetime.now(UTC)
        for source, cat in [("geo.admin.ch/gwr", "identity"), ("ch.bag.radonkarte", "environment")]:
            snap = BuildingSourceSnapshot(
                id=uuid.uuid4(),
                building_id=sample_building.id,
                source_name=source,
                source_category=cat,
                raw_data={},
                normalized_data={"test": True},
                fetched_at=now,
                freshness_state="current",
                confidence="high",
            )
            db_session.add(snap)
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/source-snapshots",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {s["source_name"] for s in data}
        assert "geo.admin.ch/gwr" in names
        assert "ch.bag.radonkarte" in names
        assert all(s["freshness_state"] == "current" for s in data)

    @pytest.mark.asyncio
    async def test_source_snapshots_empty(self, client, auth_headers, sample_building):
        """GET /buildings/{id}/source-snapshots returns empty list when none exist."""
        resp = await client.get(
            f"/api/v1/buildings/{sample_building.id}/source-snapshots",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []
