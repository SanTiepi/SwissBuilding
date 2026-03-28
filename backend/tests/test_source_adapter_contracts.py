"""Identity chain adapter contract tests — reliability-grade.

Tests the RELIABILITY contracts of the identity chain service:
- Fallback chains (EGID, EGRID, RDPPF)
- Freshness enforcement
- Schema-drift detection
- Health event recording on success/failure/fallback
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.models.building import Building
from app.models.building_identity import BuildingIdentityChain
from app.models.source_registry import SourceHealthEvent, SourceRegistryEntry
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers (mirrored from test_source_reliability.py)
# ---------------------------------------------------------------------------

_HASH = "$2b$12$LJ3m4ys3Lg3LzYHvjpnXaOaB0RVi0V0V.V.V.V.V.V.V.V.V.V.V"  # dummy


async def _make_user(db) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"contract-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH,
        first_name="Contract",
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
    egid=None,
    egrid=None,
    address="Rue Test 1",
) -> Building:
    user = await _make_user(db)
    building = Building(
        id=uuid.uuid4(),
        address=address,
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=1965,
        building_type="residential",
        created_by=user.id,
        status="active",
        latitude=lat,
        longitude=lon,
        egid=egid,
        egrid=egrid,
    )
    db.add(building)
    await db.flush()
    return building


async def _make_source(
    db,
    name,
    *,
    family="identity",
    circle=1,
    status="active",
    freshness_policy="on_demand",
    cache_ttl_hours=None,
    priority="now",
) -> SourceRegistryEntry:
    source = SourceRegistryEntry(
        id=uuid.uuid4(),
        name=name,
        display_name=name.replace("_", " ").title(),
        family=family,
        circle=circle,
        source_class="official",
        access_mode="api",
        trust_posture="canonical_identity",
        status=status,
        freshness_policy=freshness_policy,
        cache_ttl_hours=cache_ttl_hours,
        workspace_consumers=["building_home"],
        priority=priority,
    )
    db.add(source)
    await db.flush()
    return source


# ═══════════════════════════════════════════════════════════════════════════
# TestIdentityChainFallback — fallback chain contracts
# ═══════════════════════════════════════════════════════════════════════════


class TestIdentityChainFallback:
    """Contract tests proving identity_chain_service fallback behavior."""

    @pytest.mark.asyncio
    async def test_egid_fallback_on_primary_failure(self, db):
        """When primary resolve_egid raises, fallback to coordinate lookup returns EGID."""
        from app.services import identity_chain_service as svc
        from app.services.identity_chain_service import resolve_egid_with_fallback

        await _make_source(db, "geo_admin_madd")

        # Mock resolve_egid to raise (simulating full API failure)
        # Mock _egid_from_coordinates to succeed (fallback path)
        with (
            patch.object(
                svc,
                "resolve_egid",
                new_callable=AsyncMock,
                side_effect=ConnectionError("MADD API unreachable"),
            ),
            patch.object(
                svc,
                "_egid_from_coordinates",
                new_callable=AsyncMock,
                return_value={
                    "egid": 999888,
                    "address": "Rue Fallback 1",
                    "municipality": "Lausanne",
                    "canton": "VD",
                    "coordinates": (46.52, 6.63),
                    "source": "madd",
                    "confidence": 0.85,
                },
            ),
        ):
            result = await resolve_egid_with_fallback(
                db,
                address="Nonexistent Street 999",
                coordinates=(46.52, 6.63),
            )

        assert result["egid"] == 999888
        assert result.get("fallback_used") is True

    @pytest.mark.asyncio
    async def test_egid_fallback_all_paths_fail(self, db):
        """When both primary and fallback fail, returns gap descriptor."""
        from app.services.identity_chain_service import resolve_egid_with_fallback

        await _make_source(db, "geo_admin_madd")

        with patch(
            "app.services.identity_chain_service._fetch_json",
            new_callable=AsyncMock,
            return_value={"results": []},
        ):
            result = await resolve_egid_with_fallback(
                db,
                address="Nonexistent Street 999",
                coordinates=(46.52, 6.63),
            )

        assert result["egid"] is None
        assert result["fallback_used"] is True
        assert "gap" in result
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_egrid_fallback_on_cadastre_failure(self, db):
        """When cadastre API fails, chain continues with gap."""
        from app.services.identity_chain_service import resolve_egrid_with_fallback

        await _make_source(db, "geo_admin_cadastre")

        with patch(
            "app.services.identity_chain_service._fetch_json",
            new_callable=AsyncMock,
            return_value={"results": []},
        ):
            result = await resolve_egrid_with_fallback(
                db,
                egid=123456,
                coordinates=(46.52, 6.63),
            )

        assert result["egrid"] is None
        assert result["fallback_used"] is True
        assert "gap" in result

    @pytest.mark.asyncio
    async def test_rdppf_fallback_on_api_failure(self, db):
        """RDPPF failure doesn't crash — returns partial chain with gap."""
        from app.services.identity_chain_service import fetch_rdppf_with_fallback

        await _make_source(db, "rdppf_federal")

        with patch(
            "app.services.identity_chain_service.fetch_rdppf",
            new_callable=AsyncMock,
            side_effect=ConnectionError("RDPPF service unavailable"),
        ):
            result = await fetch_rdppf_with_fallback(db, egrid="CH1234567890")

        assert result["restrictions"] == []
        assert result["themes"] == []
        assert result["fallback_used"] is True
        assert "gap" in result

    @pytest.mark.asyncio
    async def test_full_chain_fallback_cascade(self, db):
        """All APIs fail — returns maximum partial data with all gaps listed."""
        from app.services import identity_chain_service as svc

        building = await _make_building(db, egid=None, egrid=None, lat=None, lon=None)
        await _make_source(db, "geo_admin_madd")

        with (
            patch.object(svc, "resolve_egid", new_callable=AsyncMock, return_value={}),
            patch.object(svc, "resolve_egrid", new_callable=AsyncMock, return_value={}),
            patch.object(svc, "fetch_rdppf", new_callable=AsyncMock, return_value={}),
            patch.object(svc.SourceRegistryService, "record_health_event", new_callable=AsyncMock),
        ):
            result = await svc.resolve_full_chain(db, building.id)

        assert result["chain_complete"] is False
        assert "egid_not_resolved" in result["chain_gaps"]
        assert "rdppf_skipped_no_egrid" in result["chain_gaps"]
        assert result["egid"]["value"] is None
        assert result["egrid"]["value"] is None


# ═══════════════════════════════════════════════════════════════════════════
# TestIdentityChainFreshness — freshness enforcement contracts
# ═══════════════════════════════════════════════════════════════════════════


class TestIdentityChainFreshness:
    """Contract tests for freshness enforcement."""

    @pytest.mark.asyncio
    async def test_freshness_check_detects_stale_data(self, db):
        """Cached data older than TTL is flagged as stale."""
        from app.services.identity_chain_service import check_freshness

        building = await _make_building(db, egid=123456)

        # Create a source with 24h TTL
        await _make_source(db, "geo_admin_madd", cache_ttl_hours=24)
        await _make_source(db, "geo_admin_cadastre", cache_ttl_hours=24)
        await _make_source(db, "rdppf_federal", cache_ttl_hours=24)

        # Pre-populate identity chain with old data (48h ago)
        old_time = datetime.now(UTC) - timedelta(hours=48)
        chain = BuildingIdentityChain(
            building_id=building.id,
            egid=123456,
            egid_source="madd",
            egid_confidence=0.9,
            egid_resolved_at=old_time,
            egrid="CH1234567890",
            egrid_source="cadastre",
            egrid_resolved_at=old_time,
            rdppf_data={"restrictions": [], "themes": []},
            rdppf_source="geo.admin.ch",
            rdppf_resolved_at=old_time,
            chain_complete=True,
            chain_gaps=None,
        )
        db.add(chain)
        await db.flush()

        result = await check_freshness(db, building.id)

        assert result["fresh"] is False
        assert len(result["stale_components"]) > 0
        assert result["recommended_action"] == "refresh"

    @pytest.mark.asyncio
    async def test_freshness_check_fresh_data(self, db):
        """Recently cached data is flagged as fresh."""
        from app.services.identity_chain_service import check_freshness

        building = await _make_building(db, egid=123456)

        # Create sources (on_demand = no TTL = always fresh)
        await _make_source(db, "geo_admin_madd")
        await _make_source(db, "geo_admin_cadastre")
        await _make_source(db, "rdppf_federal")

        # Pre-populate identity chain with fresh data (1h ago)
        recent_time = datetime.now(UTC) - timedelta(hours=1)
        chain = BuildingIdentityChain(
            building_id=building.id,
            egid=123456,
            egid_source="madd",
            egid_confidence=0.9,
            egid_resolved_at=recent_time,
            egrid="CH1234567890",
            egrid_source="cadastre",
            egrid_resolved_at=recent_time,
            rdppf_data={"restrictions": [{"type": "test"}], "themes": ["test"]},
            rdppf_source="geo.admin.ch",
            rdppf_resolved_at=recent_time,
            chain_complete=True,
            chain_gaps=None,
        )
        db.add(chain)
        await db.flush()

        result = await check_freshness(db, building.id)

        assert result["fresh"] is True
        assert result["stale_components"] == []
        assert result["recommended_action"] == "none"

    @pytest.mark.asyncio
    async def test_freshness_check_no_cached_chain(self, db):
        """No cached chain returns fresh=False with recommended_action=resolve."""
        from app.services.identity_chain_service import check_freshness

        fake_id = uuid.uuid4()

        # Patch resolve_full_chain to avoid HTTP calls (get_identity_chain calls it when no cache)
        with patch(
            "app.services.identity_chain_service.resolve_full_chain",
            new_callable=AsyncMock,
            return_value={"error": "building_not_found", "chain_complete": False, "chain_gaps": ["building_not_found"]},
        ):
            result = await check_freshness(db, fake_id)

        assert result["fresh"] is False
        assert "all" in result["stale_components"]
        assert result["recommended_action"] == "resolve"


# ═══════════════════════════════════════════════════════════════════════════
# TestIdentityChainSchemaDrift — schema-drift detection contracts
# ═══════════════════════════════════════════════════════════════════════════


class TestIdentityChainSchemaDrift:
    """Contract tests for schema-drift detection."""

    def test_schema_drift_detected_missing_fields(self):
        """Missing expected fields in API response triggers drift detection."""
        from app.services.identity_chain_service import (
            _EGID_OPTIONAL,
            EXPECTED_EGID_FIELDS,
            validate_response_schema,
        )

        # Response missing "canton" and "municipality"
        incomplete_response = {
            "egid": 123456,
            "address": "Rue Test 1",
        }
        result = validate_response_schema(incomplete_response, EXPECTED_EGID_FIELDS, _EGID_OPTIONAL)

        assert result["valid"] is False
        assert "canton" in result["missing_fields"]
        assert "municipality" in result["missing_fields"]

    def test_schema_drift_detected_unexpected_fields(self):
        """Unexpected fields in API response are flagged."""
        from app.services.identity_chain_service import (
            _EGID_OPTIONAL,
            EXPECTED_EGID_FIELDS,
            validate_response_schema,
        )

        response_with_extra = {
            "egid": 123456,
            "address": "Rue Test 1",
            "municipality": "Lausanne",
            "canton": "VD",
            "new_api_field": "surprise",
            "another_new_field": 42,
        }
        result = validate_response_schema(response_with_extra, EXPECTED_EGID_FIELDS, _EGID_OPTIONAL)

        assert result["valid"] is True  # all expected fields present
        assert "another_new_field" in result["unexpected_fields"]
        assert "new_api_field" in result["unexpected_fields"]

    def test_schema_valid_response(self):
        """Normal API response passes schema validation."""
        from app.services.identity_chain_service import (
            _EGID_OPTIONAL,
            EXPECTED_EGID_FIELDS,
            validate_response_schema,
        )

        valid_response = {
            "egid": 123456,
            "address": "Rue Test 1",
            "municipality": "Lausanne",
            "canton": "VD",
            "source": "madd",
            "confidence": 0.9,
        }
        result = validate_response_schema(valid_response, EXPECTED_EGID_FIELDS, _EGID_OPTIONAL)

        assert result["valid"] is True
        assert result["missing_fields"] == []
        assert result["unexpected_fields"] == []

    def test_schema_empty_response(self):
        """Empty response is flagged as invalid with all fields missing."""
        from app.services.identity_chain_service import (
            _EGID_OPTIONAL,
            EXPECTED_EGID_FIELDS,
            validate_response_schema,
        )

        result = validate_response_schema({}, EXPECTED_EGID_FIELDS, _EGID_OPTIONAL)

        assert result["valid"] is False
        assert len(result["missing_fields"]) == len(EXPECTED_EGID_FIELDS)

    def test_rdppf_schema_validation(self):
        """RDPPF response schema validation works correctly."""
        from app.services.identity_chain_service import (
            _RDPPF_OPTIONAL,
            EXPECTED_RDPPF_FIELDS,
            validate_response_schema,
        )

        valid_rdppf = {
            "restrictions": [{"type": "test"}],
            "themes": ["test"],
            "parcel_info": {"egrid": "CH123"},
            "source": "geo.admin.ch",
        }
        result = validate_response_schema(valid_rdppf, EXPECTED_RDPPF_FIELDS, _RDPPF_OPTIONAL)
        assert result["valid"] is True

        # Missing source
        incomplete_rdppf = {
            "restrictions": [],
            "themes": [],
        }
        result2 = validate_response_schema(incomplete_rdppf, EXPECTED_RDPPF_FIELDS, _RDPPF_OPTIONAL)
        assert result2["valid"] is False
        assert "source" in result2["missing_fields"]

    @pytest.mark.asyncio
    async def test_schema_drift_records_health_event(self, db):
        """Schema drift triggers a health event via SourceRegistryService."""
        from app.services.identity_chain_service import _record_schema_drift

        await _make_source(db, "geo_admin_madd")

        drift_validation = {
            "valid": False,
            "missing_fields": ["canton"],
            "unexpected_fields": ["new_field"],
        }

        await _record_schema_drift(db, "geo_admin_madd", drift_validation)

        from sqlalchemy import select as sa_select

        stmt = (
            sa_select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "geo_admin_madd",
                SourceHealthEvent.event_type == "schema_drift",
            )
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())
        assert len(events) >= 1
        assert "canton" in events[0].description


# ═══════════════════════════════════════════════════════════════════════════
# TestIdentityChainHealthEvents — health event recording contracts
# ═══════════════════════════════════════════════════════════════════════════


class TestIdentityChainHealthEvents:
    """Contract tests for health event recording on success/failure/fallback."""

    @pytest.mark.asyncio
    async def test_health_events_on_success(self, db):
        """Health events recorded for successful EGID resolution."""
        from app.services import identity_chain_service as svc

        building = await _make_building(db, egid=123456)
        await _make_source(db, "geo_admin_madd")
        await _make_source(db, "geo_admin_cadastre")

        with (
            patch.object(svc, "resolve_egrid", new_callable=AsyncMock, return_value={}),
            patch.object(svc, "fetch_rdppf", new_callable=AsyncMock, return_value={}),
        ):
            await svc.resolve_full_chain(db, building.id)

        from sqlalchemy import select as sa_select

        stmt = (
            sa_select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "geo_admin_madd",
                SourceHealthEvent.event_type == "healthy",
            )
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_health_events_on_failure(self, db):
        """Health events recorded for failed EGID resolution."""
        from app.services import identity_chain_service as svc

        building = await _make_building(db, egid=None, lat=None, lon=None)
        await _make_source(db, "geo_admin_madd")

        with (
            patch.object(svc, "resolve_egid", new_callable=AsyncMock, return_value={}),
            patch.object(svc, "resolve_egrid", new_callable=AsyncMock, return_value={}),
        ):
            await svc.resolve_full_chain(db, building.id)

        from sqlalchemy import select as sa_select

        stmt = (
            sa_select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "geo_admin_madd",
                SourceHealthEvent.event_type == "degraded",
            )
        )
        result = await db.execute(stmt)
        events = list(result.scalars().all())
        assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_fallback_records_degraded_health(self, db):
        """When fallback is used, health event shows 'degraded' not 'healthy'."""
        from app.services import identity_chain_service as svc
        from app.services.identity_chain_service import resolve_egid_with_fallback

        await _make_source(db, "geo_admin_madd")

        # Mock resolve_egid to raise (triggers outer fallback path)
        # Mock _egid_from_coordinates to succeed
        with (
            patch.object(
                svc,
                "resolve_egid",
                new_callable=AsyncMock,
                side_effect=ConnectionError("MADD down"),
            ),
            patch.object(
                svc,
                "_egid_from_coordinates",
                new_callable=AsyncMock,
                return_value={
                    "egid": 777666,
                    "address": "Rue Fallback 1",
                    "municipality": "Lausanne",
                    "canton": "VD",
                    "coordinates": (46.52, 6.63),
                    "source": "madd",
                    "confidence": 0.85,
                },
            ),
        ):
            result = await resolve_egid_with_fallback(
                db,
                address="Nonexistent Street 999",
                coordinates=(46.52, 6.63),
            )

        assert result["egid"] == 777666
        assert result.get("fallback_used") is True

        # Should have a degraded event, NOT healthy
        from sqlalchemy import select as sa_select

        stmt = (
            sa_select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "geo_admin_madd",
                SourceHealthEvent.event_type == "degraded",
            )
        )
        result_db = await db.execute(stmt)
        events = list(result_db.scalars().all())
        assert len(events) >= 1
        assert events[0].fallback_used is True

    @pytest.mark.asyncio
    async def test_rdppf_failure_records_error_health(self, db):
        """When RDPPF fetch raises, error health event is recorded."""
        from app.services.identity_chain_service import fetch_rdppf_with_fallback

        await _make_source(db, "rdppf_federal")

        with patch(
            "app.services.identity_chain_service.fetch_rdppf",
            new_callable=AsyncMock,
            side_effect=ConnectionError("timeout"),
        ):
            result = await fetch_rdppf_with_fallback(db, egrid="CH1234567890")

        assert result["fallback_used"] is True
        assert "gap" in result

        from sqlalchemy import select as sa_select

        stmt = (
            sa_select(SourceHealthEvent)
            .join(SourceRegistryEntry)
            .where(
                SourceRegistryEntry.name == "rdppf_federal",
                SourceHealthEvent.event_type == "error",
            )
        )
        result_db = await db.execute(stmt)
        events = list(result_db.scalars().all())
        assert len(events) >= 1
