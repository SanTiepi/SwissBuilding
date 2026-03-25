"""Tests for the passport export module — service + API."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_item import ActionItem
from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.sample import Sample
from app.models.user import User
from app.services.passport_export_service import (
    compare_passports,
    generate_building_passport,
    get_portfolio_passport_summary,
    validate_passport,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session: AsyncSession) -> Organization:
    o = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="diagnostic_lab",
    )
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org_user(db_session: AsyncSession, org: Organization) -> User:
    from tests.conftest import _HASH_ADMIN

    u = User(
        id=uuid.uuid4(),
        email="orguser@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Org",
        last_name="User",
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
async def full_building(db_session: AsyncSession, admin_user: User) -> Building:
    """Building with diagnostics, samples, interventions, and actions."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Complète 10",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        egid=12345,
        egrid="CH123456789",
        construction_year=1965,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
        surface_area_m2=500.0,
        floors_above=4,
    )
    db_session.add(b)
    await db_session.flush()

    # Diagnostic with samples
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="asbestos",
        status="completed",
        date_report=date.today() - timedelta(days=30),
    )
    db_session.add(diag)
    await db_session.flush()

    s1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S001",
        pollutant_type="asbestos",
        threshold_exceeded=True,
        risk_level="high",
    )
    s2 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag.id,
        sample_number="S002",
        pollutant_type="asbestos",
        threshold_exceeded=False,
        risk_level="low",
    )
    db_session.add_all([s1, s2])

    # Intervention
    interv = Intervention(
        id=uuid.uuid4(),
        building_id=b.id,
        intervention_type="removal",
        title="Asbestos removal",
        status="completed",
        cost_chf=15000.0,
    )
    db_session.add(interv)

    # Action items
    action_open = ActionItem(
        id=uuid.uuid4(),
        building_id=b.id,
        source_type="diagnostic",
        action_type="remediation",
        title="Remove asbestos in basement",
        priority="high",
        status="open",
        due_date=date.today() + timedelta(days=90),
    )
    action_done = ActionItem(
        id=uuid.uuid4(),
        building_id=b.id,
        source_type="diagnostic",
        action_type="monitoring",
        title="Quarterly air check",
        priority="medium",
        status="completed",
    )
    db_session.add_all([action_open, action_done])
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def minimal_building(db_session: AsyncSession, admin_user: User) -> Building:
    """Building with minimal data — no diagnostics, no EGID."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Vide 1",
        postal_code="1200",
        city="Genève",
        canton="GE",
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()
    await db_session.refresh(b)
    return b


@pytest.fixture
async def old_diagnostic_building(db_session: AsyncSession, admin_user: User) -> Building:
    """Building with an old diagnostic (>5 years)."""
    b = Building(
        id=uuid.uuid4(),
        address="Rue Ancienne 5",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        egid=99999,
        construction_year=1970,
        building_type="residential",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.flush()

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="pcb",
        status="completed",
        date_report=date.today() - timedelta(days=2200),  # ~6 years
    )
    db_session.add(diag)
    await db_session.commit()
    await db_session.refresh(b)
    return b


# ---------------------------------------------------------------------------
# Service: generate_building_passport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_passport_full(db_session: AsyncSession, full_building: Building):
    passport = await generate_building_passport(full_building.id, db_session)
    assert passport is not None
    assert passport.passport_version == "1.0.0"
    assert passport.export_format == "json"
    assert passport.identity.building_id == full_building.id
    assert passport.identity.egid == 12345
    assert passport.identity.canton == "VD"
    assert len(passport.pollutant_sections) == 5


@pytest.mark.asyncio
async def test_generate_passport_pollutant_sections(db_session: AsyncSession, full_building: Building):
    passport = await generate_building_passport(full_building.id, db_session)
    assert passport is not None
    asbestos = next(s for s in passport.pollutant_sections if s.pollutant_type == "asbestos")
    assert asbestos.diagnosed is True
    assert asbestos.sample_count == 2
    assert asbestos.exceeded_count == 1
    assert asbestos.risk_level == "high"
    assert asbestos.compliance_status == "non_compliant"


@pytest.mark.asyncio
async def test_generate_passport_undiagnosed_pollutant(db_session: AsyncSession, full_building: Building):
    passport = await generate_building_passport(full_building.id, db_session)
    assert passport is not None
    radon = next(s for s in passport.pollutant_sections if s.pollutant_type == "radon")
    assert radon.diagnosed is False
    assert radon.sample_count == 0
    assert radon.compliance_status == "unknown"


@pytest.mark.asyncio
async def test_generate_passport_interventions(db_session: AsyncSession, full_building: Building):
    passport = await generate_building_passport(full_building.id, db_session)
    assert passport is not None
    assert passport.intervention_summary.intervention_count == 1
    assert passport.intervention_summary.completed_count == 1
    assert passport.intervention_summary.total_estimated_cost == 15000.0
    assert "removal" in passport.intervention_summary.intervention_types


@pytest.mark.asyncio
async def test_generate_passport_compliance(db_session: AsyncSession, full_building: Building):
    passport = await generate_building_passport(full_building.id, db_session)
    assert passport is not None
    assert passport.compliance.overall_status == "partial"
    assert passport.compliance.open_actions == 1
    assert passport.compliance.critical_actions == 0
    assert passport.compliance.next_deadline is not None


@pytest.mark.asyncio
async def test_generate_passport_scores(db_session: AsyncSession, full_building: Building):
    passport = await generate_building_passport(full_building.id, db_session)
    assert passport is not None
    assert 0.0 <= passport.quality_score <= 1.0
    assert 0.0 <= passport.completeness_score <= 1.0
    assert passport.quality_score > 0


@pytest.mark.asyncio
async def test_generate_passport_not_found(db_session: AsyncSession):
    result = await generate_building_passport(uuid.uuid4(), db_session)
    assert result is None


@pytest.mark.asyncio
async def test_generate_passport_minimal(db_session: AsyncSession, minimal_building: Building):
    passport = await generate_building_passport(minimal_building.id, db_session)
    assert passport is not None
    assert passport.identity.egid is None
    assert passport.completeness_score < 1.0
    assert passport.compliance.overall_status == "unknown"


@pytest.mark.asyncio
async def test_generate_passport_format_summary(db_session: AsyncSession, full_building: Building):
    passport = await generate_building_passport(full_building.id, db_session, format_type="summary")
    assert passport is not None
    assert passport.export_format == "summary"


# ---------------------------------------------------------------------------
# Service: validate_passport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_passport_full(db_session: AsyncSession, full_building: Building):
    result = await validate_passport(full_building.id, db_session)
    assert result is not None
    assert result.is_valid is True
    assert len(result.missing_fields) == 0
    assert result.completeness_pct > 0


@pytest.mark.asyncio
async def test_validate_passport_minimal_missing_fields(db_session: AsyncSession, minimal_building: Building):
    result = await validate_passport(minimal_building.id, db_session)
    assert result is not None
    assert result.is_valid is False
    assert "egid" in result.missing_fields
    assert "at_least_one_diagnostic" in result.missing_fields


@pytest.mark.asyncio
async def test_validate_passport_old_diagnostic_warning(db_session: AsyncSession, old_diagnostic_building: Building):
    result = await validate_passport(old_diagnostic_building.id, db_session)
    assert result is not None
    old_warnings = [w for w in result.warnings if "older than 5 years" in w]
    assert len(old_warnings) >= 1


@pytest.mark.asyncio
async def test_validate_passport_not_found(db_session: AsyncSession):
    result = await validate_passport(uuid.uuid4(), db_session)
    assert result is None


@pytest.mark.asyncio
async def test_validate_passport_missing_pollutant_coverage(db_session: AsyncSession, full_building: Building):
    result = await validate_passport(full_building.id, db_session)
    assert result is not None
    coverage_warnings = [w for w in result.warnings if "Missing pollutant coverage" in w]
    assert len(coverage_warnings) == 1  # only asbestos diagnosed


# ---------------------------------------------------------------------------
# Service: compare_passports
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_passports_both_exist(
    db_session: AsyncSession, full_building: Building, minimal_building: Building
):
    result = await compare_passports(full_building.id, minimal_building.id, db_session)
    assert result is not None
    assert result.building_a_id == full_building.id
    assert result.building_b_id == minimal_building.id
    assert 0.0 <= result.similarity_score <= 1.0
    assert isinstance(result.differing_fields, list)
    assert isinstance(result.recommendation, str)


@pytest.mark.asyncio
async def test_compare_passports_one_missing(db_session: AsyncSession, full_building: Building):
    result = await compare_passports(full_building.id, uuid.uuid4(), db_session)
    assert result is None


@pytest.mark.asyncio
async def test_compare_passports_same_building(db_session: AsyncSession, full_building: Building):
    result = await compare_passports(full_building.id, full_building.id, db_session)
    assert result is not None
    assert result.similarity_score == 1.0
    assert len(result.differing_fields) == 0


# ---------------------------------------------------------------------------
# Service: get_portfolio_passport_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_summary(db_session: AsyncSession, org: Organization, org_user: User):
    # Create a building for the org user
    b = Building(
        id=uuid.uuid4(),
        address="Rue Portfolio 1",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        created_by=org_user.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()

    result = await get_portfolio_passport_summary(org.id, db_session)
    assert result is not None
    assert result.organization_id == org.id
    assert result.total_buildings == 1


@pytest.mark.asyncio
async def test_portfolio_summary_empty_org(db_session: AsyncSession, org: Organization):
    result = await get_portfolio_passport_summary(org.id, db_session)
    assert result is not None
    assert result.total_buildings == 0
    assert result.passports_complete == 0


@pytest.mark.asyncio
async def test_portfolio_summary_no_users(db_session: AsyncSession):
    result = await get_portfolio_passport_summary(uuid.uuid4(), db_session)
    assert result is not None
    assert result.total_buildings == 0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_generate_passport(client: AsyncClient, auth_headers: dict, sample_building: Building):
    resp = await client.get(
        f"/api/v1/passport-export/buildings/{sample_building.id}/generate",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["passport_version"] == "1.0.0"
    assert data["identity"]["building_id"] == str(sample_building.id)


@pytest.mark.asyncio
async def test_api_generate_passport_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        f"/api/v1/passport-export/buildings/{uuid.uuid4()}/generate",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_validate_passport(client: AsyncClient, auth_headers: dict, sample_building: Building):
    resp = await client.get(
        f"/api/v1/passport-export/buildings/{sample_building.id}/validate",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "is_valid" in data
    assert "missing_fields" in data


@pytest.mark.asyncio
async def test_api_compare_passports(
    client: AsyncClient, auth_headers: dict, sample_building: Building, db_session: AsyncSession, admin_user: User
):
    b2 = Building(
        id=uuid.uuid4(),
        address="Rue Autre 2",
        postal_code="1200",
        city="Genève",
        canton="GE",
        building_type="commercial",
        created_by=admin_user.id,
        status="active",
    )
    db_session.add(b2)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/passport-export/compare",
        params={"building_a": str(sample_building.id), "building_b": str(b2.id)},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "similarity_score" in data
    assert "recommendation" in data


@pytest.mark.asyncio
async def test_api_portfolio_summary(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        f"/api/v1/passport-export/organizations/{uuid.uuid4()}/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_buildings"] == 0


@pytest.mark.asyncio
async def test_api_validate_passport_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(
        f"/api/v1/passport-export/buildings/{uuid.uuid4()}/validate",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_compare_passports_not_found(client: AsyncClient, auth_headers: dict, sample_building: Building):
    resp = await client.get(
        "/api/v1/passport-export/compare",
        params={"building_a": str(sample_building.id), "building_b": str(uuid.uuid4())},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_generate_passport_unauthenticated(client: AsyncClient, sample_building: Building):
    resp = await client.get(
        f"/api/v1/passport-export/buildings/{sample_building.id}/generate",
    )
    assert resp.status_code == 401
