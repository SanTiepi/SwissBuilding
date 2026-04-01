"""Tests for UnknownsLedger model, service, and API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.organization import Organization
from app.models.unknowns_ledger import UnknownEntry
from app.models.user import User
from app.models.zone import Zone

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db(db_session: AsyncSession):
    """Alias for db_session to match test convention."""
    yield db_session


@pytest.fixture
async def sample_organization(db: AsyncSession):
    """Create a test organization."""
    org = Organization(
        id=uuid.uuid4(),
        name="Test Org Unknowns",
        type="property_management",
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@pytest.fixture
async def sample_user(db: AsyncSession, sample_organization):
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email=f"unknowns-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfakeh",
        first_name="Test",
        last_name="User",
        role="admin",
        organization_id=sample_organization.id,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def building_old(db: AsyncSession, sample_organization, sample_user):
    """Pre-1990 building that needs a diagnostic."""
    b = Building(
        id=uuid.uuid4(),
        address="1 Rue Test",
        city="Lausanne",
        canton="VD",
        postal_code="1000",
        building_type="residential",
        construction_year=1970,
        created_by=sample_user.id,
        organization_id=sample_organization.id,
    )
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


@pytest.fixture
async def building_new(db: AsyncSession, sample_organization, sample_user):
    """Post-1991 building that should NOT need a diagnostic."""
    b = Building(
        id=uuid.uuid4(),
        address="2 Rue Test",
        city="Lausanne",
        canton="VD",
        postal_code="1000",
        building_type="residential",
        construction_year=2010,
        created_by=sample_user.id,
        organization_id=sample_organization.id,
    )
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestScanBuilding:
    async def test_scan_detects_missing_diagnostic(self, db: AsyncSession, building_old):
        from app.services.unknowns_ledger_service import scan_building

        result = await scan_building(db, building_old.id)
        assert result["total"] > 0
        assert result["created"] > 0
        assert "missing_diagnostic" in result["by_type"]

    async def test_scan_idempotent(self, db: AsyncSession, building_old):
        from app.services.unknowns_ledger_service import scan_building

        result1 = await scan_building(db, building_old.id)
        result2 = await scan_building(db, building_old.id)
        # Second scan should not create duplicates
        assert result2["created"] == 0
        assert result2["total"] == result1["total"]

    async def test_scan_new_building_no_diagnostic_needed(self, db: AsyncSession, building_new):
        from app.services.unknowns_ledger_service import scan_building

        result = await scan_building(db, building_new.id)
        assert result["by_type"].get("missing_diagnostic", 0) == 0

    async def test_scan_detects_expired_diagnostic(self, db: AsyncSession, building_old):
        from app.services.unknowns_ledger_service import scan_building

        # Add a very old completed diagnostic (created_at set far in the past)
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building_old.id,
            diagnostic_type="asbestos",
            status="completed",
            created_at=datetime.now(UTC) - timedelta(days=1200),
        )
        db.add(diag)
        await db.flush()

        result = await scan_building(db, building_old.id)
        assert "expired_diagnostic" in result["by_type"]

    async def test_scan_detects_spatial_gaps(self, db: AsyncSession, building_old):
        from app.services.unknowns_ledger_service import scan_building

        # Add zone with no elements
        zone = Zone(
            id=uuid.uuid4(),
            building_id=building_old.id,
            zone_type="room",
            name="Cave vide",
        )
        db.add(zone)
        await db.flush()

        result = await scan_building(db, building_old.id)
        assert "spatial_gap" in result["by_type"]

    async def test_scan_nonexistent_building(self, db: AsyncSession):
        from app.services.unknowns_ledger_service import scan_building

        result = await scan_building(db, uuid.uuid4())
        assert result["total"] == 0

    async def test_scan_auto_resolves(self, db: AsyncSession, building_old):
        from app.services.unknowns_ledger_service import scan_building

        # First scan creates entries
        await scan_building(db, building_old.id)

        # Add a completed diagnostic to resolve the missing_diagnostic gap
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building_old.id,
            diagnostic_type="asbestos",
            status="completed",
        )
        db.add(diag)
        await db.flush()

        result = await scan_building(db, building_old.id)
        assert result["resolved"] > 0


class TestGetLedger:
    async def test_get_ledger_default_open(self, db: AsyncSession, building_old):
        from app.services.unknowns_ledger_service import get_ledger, scan_building

        await scan_building(db, building_old.id)
        entries = await get_ledger(db, building_old.id)
        assert len(entries) > 0
        assert all(e.status == "open" for e in entries)

    async def test_get_ledger_severity_filter(self, db: AsyncSession, building_old):
        from app.services.unknowns_ledger_service import get_ledger, scan_building

        await scan_building(db, building_old.id)
        entries = await get_ledger(db, building_old.id, severity="critical")
        assert all(e.severity == "critical" for e in entries)


class TestResolveUnknown:
    async def test_resolve_sets_fields(self, db: AsyncSession, building_old, sample_user):
        from app.services.unknowns_ledger_service import resolve_unknown, scan_building

        await scan_building(db, building_old.id)
        entries_result = await db.execute(
            select(UnknownEntry).where(
                UnknownEntry.building_id == building_old.id,
                UnknownEntry.status == "open",
            )
        )
        entry = entries_result.scalars().first()
        assert entry is not None

        resolved = await resolve_unknown(
            db,
            entry.id,
            resolved_by_id=sample_user.id,
            method="new_evidence",
            note="Diagnostic ordered",
        )
        assert resolved.status == "resolved"
        assert resolved.resolved_by_id == sample_user.id
        assert resolved.resolution_method == "new_evidence"

    async def test_resolve_nonexistent(self, db: AsyncSession, sample_user):
        from app.services.unknowns_ledger_service import resolve_unknown

        with pytest.raises(ValueError, match="not found"):
            await resolve_unknown(db, uuid.uuid4(), sample_user.id, "new_evidence")


class TestAcceptRisk:
    async def test_accept_risk_requires_note(self, db: AsyncSession, building_old, sample_user):
        from app.services.unknowns_ledger_service import accept_risk, scan_building

        await scan_building(db, building_old.id)
        entries_result = await db.execute(
            select(UnknownEntry).where(
                UnknownEntry.building_id == building_old.id,
                UnknownEntry.status == "open",
            )
        )
        entry = entries_result.scalars().first()
        assert entry is not None

        with pytest.raises(ValueError, match="requires a note"):
            await accept_risk(db, entry.id, sample_user.id, "")

    async def test_accept_risk_with_note(self, db: AsyncSession, building_old, sample_user):
        from app.services.unknowns_ledger_service import accept_risk, scan_building

        await scan_building(db, building_old.id)
        entries_result = await db.execute(
            select(UnknownEntry).where(
                UnknownEntry.building_id == building_old.id,
                UnknownEntry.status == "open",
            )
        )
        entry = entries_result.scalars().first()
        assert entry is not None

        accepted = await accept_risk(db, entry.id, sample_user.id, "Client accepts risk for renovation timeline.")
        assert accepted.status == "accepted_risk"
        assert accepted.resolution_note == "Client accepts risk for renovation timeline."


class TestCoverageMap:
    async def test_coverage_map_empty(self, db: AsyncSession, building_old):
        from app.services.unknowns_ledger_service import get_coverage_map

        result = await get_coverage_map(db, building_old.id)
        assert result["covered"] == []
        assert result["gaps"] == []
        assert result["partial"] == []


class TestImpact:
    async def test_impact_summary(self, db: AsyncSession, building_old):
        from app.services.unknowns_ledger_service import get_unknowns_impact, scan_building

        await scan_building(db, building_old.id)
        impact = await get_unknowns_impact(db, building_old.id)
        assert impact["total_open"] > 0
        assert isinstance(impact["blocked_safe_to_x"], dict)
        assert isinstance(impact["most_urgent"], list)


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


class TestLedgerAPI:
    async def test_get_ledger_endpoint(self, client, auth_headers, db, building_old):
        from app.services.unknowns_ledger_service import scan_building

        await scan_building(db, building_old.id)
        await db.commit()

        resp = await client.get(
            f"/api/v1/buildings/{building_old.id}/unknowns-ledger",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0

    async def test_scan_endpoint(self, client, auth_headers, building_old):
        resp = await client.post(
            f"/api/v1/buildings/{building_old.id}/unknowns-ledger/scan",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "created" in data

    async def test_coverage_endpoint(self, client, auth_headers, building_old):
        resp = await client.get(
            f"/api/v1/buildings/{building_old.id}/unknowns-ledger/coverage",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "covered" in data
        assert "gaps" in data

    async def test_impact_endpoint(self, client, auth_headers, building_old):
        resp = await client.get(
            f"/api/v1/buildings/{building_old.id}/unknowns-ledger/impact",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total_open" in data

    async def test_resolve_endpoint(self, client, auth_headers, db, building_old):
        from app.services.unknowns_ledger_service import scan_building

        await scan_building(db, building_old.id)
        await db.commit()

        entries_result = await db.execute(
            select(UnknownEntry).where(
                UnknownEntry.building_id == building_old.id,
                UnknownEntry.status == "open",
            )
        )
        entry = entries_result.scalars().first()
        assert entry is not None

        resp = await client.post(
            f"/api/v1/unknowns-ledger/{entry.id}/resolve",
            headers=auth_headers,
            json={"method": "new_evidence", "note": "Fixed it"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    async def test_accept_risk_endpoint(self, client, auth_headers, db, building_old):
        from app.services.unknowns_ledger_service import scan_building

        await scan_building(db, building_old.id)
        await db.commit()

        entries_result = await db.execute(
            select(UnknownEntry).where(
                UnknownEntry.building_id == building_old.id,
                UnknownEntry.status == "open",
            )
        )
        entry = entries_result.scalars().first()
        assert entry is not None

        resp = await client.post(
            f"/api/v1/unknowns-ledger/{entry.id}/accept-risk",
            headers=auth_headers,
            json={"note": "Client accepts this risk"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted_risk"

    async def test_accept_risk_requires_note(self, client, auth_headers, db, building_old):
        from app.services.unknowns_ledger_service import scan_building

        await scan_building(db, building_old.id)
        await db.commit()

        entries_result = await db.execute(
            select(UnknownEntry).where(
                UnknownEntry.building_id == building_old.id,
                UnknownEntry.status == "open",
            )
        )
        entry = entries_result.scalars().first()
        assert entry is not None

        # Empty note should fail at schema validation (note is required)
        resp = await client.post(
            f"/api/v1/unknowns-ledger/{entry.id}/accept-risk",
            headers=auth_headers,
            json={},
        )
        assert resp.status_code == 422
