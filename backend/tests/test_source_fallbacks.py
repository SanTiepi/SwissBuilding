"""Source adapter fallback + freshness + drift contract tests.

Tests the RELIABILITY upgrades for geo_context_service and subsidy_source_service:
- Per-layer fallback with explicit gap lists
- Freshness detection
- Schema drift detection
- Health event recording per layer
- Federal fallback for unknown cantons
- Program validation
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.building import Building
from app.models.building_geo_context import BuildingGeoContext
from app.models.source_registry import SourceHealthEvent, SourceRegistryEntry
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HASH = "$2b$12$LJ3m4ys3Lg3LzYHvjpnXaOaB0RVi0V.V.V.V.V.V.V.V.V.V.V.V"  # dummy


async def _make_user(db) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"fb-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH,
        first_name="Fb",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
    )
    db.add(user)
    await db.flush()
    return user


async def _make_building(
    db,
    *,
    lat=46.52,
    lon=6.63,
    canton="VD",
    construction_year=1965,
) -> Building:
    user = await _make_user(db)
    building = Building(
        id=uuid.uuid4(),
        address="Rue Fallback 1",
        postal_code="1000",
        city="Lausanne",
        canton=canton,
        construction_year=construction_year,
        building_type="residential",
        created_by=user.id,
        status="active",
        latitude=lat,
        longitude=lon,
    )
    db.add(building)
    await db.flush()
    return building


async def _make_source(
    db,
    name,
    *,
    family="constraint",
    circle=1,
    status="active",
) -> SourceRegistryEntry:
    source = SourceRegistryEntry(
        id=uuid.uuid4(),
        name=name,
        display_name=name.replace("_", " ").title(),
        family=family,
        circle=circle,
        source_class="official",
        access_mode="api",
        trust_posture="observed_context",
        status=status,
        freshness_policy="weekly",
        cache_ttl_hours=168,
        workspace_consumers=["building_home"],
        priority="now",
    )
    db.add(source)
    await db.flush()
    return source


def _ok_response(json_data):
    """Build a MagicMock that looks like a successful httpx.Response."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = json_data
    return resp


# ===========================================================================
# TestGeoContextFallbacks
# ===========================================================================


class TestGeoContextFallbacks:
    """Tests for geo_context_service reliability upgrades."""

    @pytest.mark.asyncio
    async def test_single_layer_failure_returns_partial(self, db):
        """When one layer fails, others still succeed; failed layers in gap list."""
        from app.services.geo_context_service import fetch_context_with_fallback

        call_count = 0

        async def _selective_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First layer (radon) succeeds
                return _ok_response({"results": [{"attributes": {"zone": "moderate", "radon_bq_m3": "300"}}]})
            # Second layer (noise_road) fails
            raise ConnectionError("network error")

        with patch("app.services.geo_context_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=_selective_fail)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await fetch_context_with_fallback(6.63, 46.52, layers=["radon", "noise_road"])

        assert "radon" in result["layers"]
        assert "noise_road" not in result["layers"]
        assert "noise_road" in result["failed_layers"]
        assert result["total_succeeded"] == 1
        assert result["total_failed"] == 1

    @pytest.mark.asyncio
    async def test_all_layers_fail_returns_empty_with_gaps(self, db):
        """When all layers fail, returns empty layers dict with all in failed_layers."""
        from app.services.geo_context_service import fetch_context_with_fallback

        with patch("app.services.geo_context_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("total failure"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            result = await fetch_context_with_fallback(6.63, 46.52, layers=["radon", "solar"])

        assert result["layers"] == {}
        assert set(result["failed_layers"]) == {"radon", "solar"}
        assert result["total_succeeded"] == 0
        assert result["total_failed"] == 2

    @pytest.mark.asyncio
    async def test_freshness_detects_stale_context(self, db):
        """Stale geo context (>7 days) is detected as not fresh."""
        from app.services.geo_context_service import check_context_freshness

        building = await _make_building(db)

        # Insert stale cache (10 days old)
        geo_ctx = BuildingGeoContext(
            building_id=building.id,
            context_data={"radon": {"zone": "stale"}},
            fetched_at=datetime.now(UTC) - timedelta(days=10),
            source_version="geo.admin-v1",
        )
        db.add(geo_ctx)
        await db.flush()

        result = await check_context_freshness(db, building.id)

        assert result["fresh"] is False
        assert result["recommended_action"] == "refresh"
        assert result["age_days"] > 7

    @pytest.mark.asyncio
    async def test_freshness_accepts_fresh_context(self, db):
        """Fresh geo context (<7 days) is accepted."""
        from app.services.geo_context_service import check_context_freshness

        building = await _make_building(db)

        # Insert fresh cache (1 day old)
        geo_ctx = BuildingGeoContext(
            building_id=building.id,
            context_data={"radon": {"zone": "fresh"}},
            fetched_at=datetime.now(UTC) - timedelta(days=1),
            source_version="geo.admin-v1",
        )
        db.add(geo_ctx)
        await db.flush()

        result = await check_context_freshness(db, building.id)

        assert result["fresh"] is True
        assert result["recommended_action"] == "none"
        assert result["age_days"] < 7

    @pytest.mark.asyncio
    async def test_schema_drift_on_unexpected_response(self, db):
        """Schema drift is detected when response has no expected attribute keys."""
        from app.services.geo_context_service import _validate_layer_response

        # Response with completely unexpected keys (simulates geo.admin format change)
        parsed = {
            "source": "ch.bag.radonkarte",
            "label": "Radon",
            "raw_attributes": {"completely_new_key": "value", "another_new": 42},
        }

        result = _validate_layer_response("radon", parsed)

        assert result["drift_detected"] is True
        assert result["valid"] is False
        assert len(result["missing_keys"]) > 0

    @pytest.mark.asyncio
    async def test_schema_drift_accepts_valid_response(self, db):
        """Valid response with expected keys passes drift check."""
        from app.services.geo_context_service import _validate_layer_response

        parsed = {
            "source": "ch.bag.radonkarte",
            "label": "Radon",
            "raw_attributes": {"zone": "moderate", "radon_bq_m3": "200"},
        }

        result = _validate_layer_response("radon", parsed)

        assert result["drift_detected"] is False
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_health_events_per_layer(self, db):
        """Per-layer health events are recorded during fetch_context_with_fallback."""
        from app.services.geo_context_service import fetch_context_with_fallback

        # Create source registry entries for the layers we will test
        await _make_source(db, "geo_admin_radon")
        await _make_source(db, "geo_admin_noise_road")

        call_count = 0

        async def _selective(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ok_response({"results": [{"attributes": {"zone": "moderate"}}]})
            raise ConnectionError("fail")

        with patch("app.services.geo_context_service.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=_selective)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            await fetch_context_with_fallback(6.63, 46.52, layers=["radon", "noise_road"], db=db)

        from sqlalchemy import select

        # radon should have healthy event
        stmt = (
            select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "geo_admin_radon",
                SourceHealthEvent.event_type == "healthy",
            )
        )
        result = await db.execute(stmt)
        assert len(list(result.scalars().all())) >= 1

        # noise_road should have degraded event
        stmt2 = (
            select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "geo_admin_noise_road",
                SourceHealthEvent.event_type == "degraded",
            )
        )
        result2 = await db.execute(stmt2)
        assert len(list(result2.scalars().all())) >= 1

    @pytest.mark.asyncio
    async def test_freshness_no_cache_returns_full_fetch(self, db):
        """No cached context results in full_fetch recommendation."""
        from app.services.geo_context_service import check_context_freshness

        building = await _make_building(db)

        result = await check_context_freshness(db, building.id)

        assert result["fresh"] is False
        assert result["recommended_action"] == "full_fetch"


# ===========================================================================
# TestSubsidyFallbacks
# ===========================================================================


class TestSubsidyFallbacks:
    """Tests for subsidy_source_service reliability upgrades."""

    @pytest.mark.asyncio
    async def test_unknown_canton_fallback_to_federal(self, db):
        """Unknown canton falls back to federal-level programs."""
        from app.services.subsidy_source_service import SubsidySourceService

        building = await _make_building(db, canton="ZH")

        with patch(
            "app.services.subsidy_source_service.SourceRegistryService.record_health_event",
            new_callable=AsyncMock,
        ):
            result = await SubsidySourceService.get_applicable_subsidies_with_fallback(db, building.id)

        assert result["used_fallback"] is True
        assert result["fallback_source"] == "federal"
        assert result["total_programs"] > 0
        assert result["catalog_name"] == "Programme Batiments federal"

    @pytest.mark.asyncio
    async def test_known_canton_no_fallback(self, db):
        """Known canton (VD) returns canton programs without fallback."""
        from app.services.subsidy_source_service import SubsidySourceService

        building = await _make_building(db, canton="VD")

        result = await SubsidySourceService.get_applicable_subsidies_with_fallback(db, building.id)

        assert result["used_fallback"] is False
        assert result["fallback_source"] is None
        assert result["total_programs"] > 0
        assert "VD" in result["catalog_name"]

    @pytest.mark.asyncio
    async def test_freshness_detects_stale_programs(self, db):
        """Programs with old last_updated date are detected as stale."""
        from app.services.subsidy_source_service import (
            SUBSIDY_PROGRAMS,
            SubsidySourceService,
        )

        # Temporarily make VD data look stale
        original = SUBSIDY_PROGRAMS["VD"]["last_updated"]
        SUBSIDY_PROGRAMS["VD"]["last_updated"] = "2024-01-01"
        try:
            with patch(
                "app.services.subsidy_source_service.SourceRegistryService.record_health_event",
                new_callable=AsyncMock,
            ):
                result = await SubsidySourceService.check_subsidy_freshness(db, "VD")
        finally:
            SUBSIDY_PROGRAMS["VD"]["last_updated"] = original

        assert result["fresh"] is False
        assert result["stale_since"] == "2024-01-01"
        assert result["recommended_action"] == "refresh"

    @pytest.mark.asyncio
    async def test_freshness_accepts_current_programs(self, db):
        """Programs with recent last_updated are considered fresh."""
        from app.services.subsidy_source_service import SubsidySourceService

        result = await SubsidySourceService.check_subsidy_freshness(db, "VD")

        assert result["fresh"] is True
        assert result["recommended_action"] == "none"

    @pytest.mark.asyncio
    async def test_program_validation_catches_missing_fields(self, db):
        """Program with missing required fields is flagged invalid."""
        from app.services.subsidy_source_service import SubsidySourceService

        invalid_program = {"max_chf": 5000}  # missing "name" and "category"
        result = SubsidySourceService._validate_subsidy_program(invalid_program)

        assert result["valid"] is False
        assert "name" in result["missing_fields"]
        assert "category" in result["missing_fields"]

    @pytest.mark.asyncio
    async def test_program_validation_accepts_valid_program(self, db):
        """Valid program passes validation."""
        from app.services.subsidy_source_service import SubsidySourceService

        valid_program = {"name": "Test Program", "category": "energy", "max_chf": 1000}
        result = SubsidySourceService._validate_subsidy_program(valid_program)

        assert result["valid"] is True
        assert result["missing_fields"] == []

    @pytest.mark.asyncio
    async def test_eligibility_with_degraded_data(self, db):
        """Eligibility check still works with federal fallback data."""
        from app.services.subsidy_source_service import SubsidySourceService

        # Building in unknown canton
        building = await _make_building(db, canton="TI")

        with patch(
            "app.services.subsidy_source_service.SourceRegistryService.record_health_event",
            new_callable=AsyncMock,
        ):
            result = await SubsidySourceService.get_applicable_subsidies_with_fallback(db, building.id)

        # Federal fallback should still provide programs
        assert result["used_fallback"] is True
        assert result["total_programs"] > 0
        assert result["total_potential_chf"] > 0

    @pytest.mark.asyncio
    async def test_health_event_on_refresh(self, db):
        """Health event recorded when subsidy data is refreshed."""
        from app.services.subsidy_source_service import SubsidySourceService

        await _make_source(db, "subsidy_programs_vd")

        await SubsidySourceService.refresh_subsidy_data(db, "VD")

        from sqlalchemy import select

        stmt = (
            select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "subsidy_programs_vd",
                SourceHealthEvent.event_type == "healthy",
            )
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_freshness_unknown_canton(self, db):
        """Freshness check for unknown canton returns appropriate result."""
        from app.services.subsidy_source_service import SubsidySourceService

        result = await SubsidySourceService.check_subsidy_freshness(db, "ZZ")

        assert result["fresh"] is False
        assert result["detail"] == "unknown_canton"
        assert result["recommended_action"] == "no_data_available"
