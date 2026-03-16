"""Tests for building age analysis service and API."""

import uuid

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.organization import Organization
from app.models.user import User
from app.models.zone import Zone
from app.services.building_age_analysis_service import (
    analyze_construction_era,
    get_age_based_risk_profile,
    get_portfolio_age_distribution,
    identify_era_specific_hotspots,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def org(db_session):
    o = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        type="property_management",
    )
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def org_user(db_session, org):
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


def _make_building(created_by_id, construction_year=None, **kwargs):
    return Building(
        id=uuid.uuid4(),
        address=kwargs.get("address", "Rue Test 1"),
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        construction_year=construction_year,
        building_type="residential",
        created_by=created_by_id,
        status="active",
        renovation_year=kwargs.get("renovation_year"),
    )


# ---------------------------------------------------------------------------
# FN1: analyze_construction_era — unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_era_pre_1950(db_session, admin_user):
    b = _make_building(admin_user.id, 1935)
    db_session.add(b)
    await db_session.commit()

    result = await analyze_construction_era(db_session, b.id)
    assert result.era == "pre_1950"
    assert result.diagnostic_priority == "high"
    pollutants = {p.pollutant: p.probability for p in result.pollutant_probabilities}
    assert pollutants["lead"] == "high"
    assert pollutants["asbestos"] == "low"


@pytest.mark.asyncio
async def test_era_1950_1975(db_session, admin_user):
    b = _make_building(admin_user.id, 1965)
    db_session.add(b)
    await db_session.commit()

    result = await analyze_construction_era(db_session, b.id)
    assert result.era == "1950_1975"
    assert result.diagnostic_priority == "critical"
    pollutants = {p.pollutant: p.probability for p in result.pollutant_probabilities}
    assert pollutants["asbestos"] == "high"
    assert pollutants["pcb"] == "high"


@pytest.mark.asyncio
async def test_era_1975_1991(db_session, admin_user):
    b = _make_building(admin_user.id, 1985)
    db_session.add(b)
    await db_session.commit()

    result = await analyze_construction_era(db_session, b.id)
    assert result.era == "1975_1991"
    assert result.diagnostic_priority == "high"
    pollutants = {p.pollutant: p.probability for p in result.pollutant_probabilities}
    assert pollutants["asbestos"] == "medium"
    assert pollutants["pcb"] == "medium"


@pytest.mark.asyncio
async def test_era_post_1991(db_session, admin_user):
    b = _make_building(admin_user.id, 2005)
    db_session.add(b)
    await db_session.commit()

    result = await analyze_construction_era(db_session, b.id)
    assert result.era == "post_1991"
    assert result.diagnostic_priority == "low"
    pollutants = {p.pollutant: p.probability for p in result.pollutant_probabilities}
    assert pollutants["asbestos"] == "negligible"


@pytest.mark.asyncio
async def test_era_unknown(db_session, admin_user):
    b = _make_building(admin_user.id, None)
    db_session.add(b)
    await db_session.commit()

    result = await analyze_construction_era(db_session, b.id)
    assert result.era == "unknown"
    assert result.diagnostic_priority == "medium"
    assert result.construction_year is None


@pytest.mark.asyncio
async def test_era_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await analyze_construction_era(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# FN2: get_age_based_risk_profile — unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_risk_profile_elevated_no_diag(db_session, admin_user):
    b = _make_building(admin_user.id, 1960)
    db_session.add(b)
    await db_session.commit()

    result = await get_age_based_risk_profile(db_session, b.id)
    assert result.baseline_risk == "elevated"
    assert result.has_diagnostics is False
    assert result.overall_risk == "elevated"
    assert any(m.factor == "no_diagnostic" for m in result.risk_modifiers)


@pytest.mark.asyncio
async def test_risk_profile_with_diagnostics(db_session, admin_user):
    b = _make_building(admin_user.id, 1960)
    db_session.add(b)
    await db_session.commit()

    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(d)
    await db_session.commit()

    result = await get_age_based_risk_profile(db_session, b.id)
    assert result.has_diagnostics is True
    assert result.diagnostic_count == 1
    assert result.completed_diagnostic_count == 1
    assert any(m.factor == "diagnostic_coverage" for m in result.risk_modifiers)


@pytest.mark.asyncio
async def test_risk_profile_with_intervention(db_session, admin_user):
    b = _make_building(admin_user.id, 1960)
    db_session.add(b)
    await db_session.commit()

    i = Intervention(
        id=uuid.uuid4(),
        building_id=b.id,
        intervention_type="removal",
        title="Asbestos removal",
        status="completed",
    )
    db_session.add(i)
    await db_session.commit()

    result = await get_age_based_risk_profile(db_session, b.id)
    assert any(m.factor == "intervention_history" for m in result.risk_modifiers)


@pytest.mark.asyncio
async def test_risk_profile_pre_ban_renovation(db_session, admin_user):
    b = _make_building(admin_user.id, 1950, renovation_year=1980)
    db_session.add(b)
    await db_session.commit()

    result = await get_age_based_risk_profile(db_session, b.id)
    assert any(m.factor == "pre_ban_renovation" for m in result.risk_modifiers)


@pytest.mark.asyncio
async def test_risk_profile_post_1991_low(db_session, admin_user):
    b = _make_building(admin_user.id, 2010)
    db_session.add(b)
    await db_session.commit()

    result = await get_age_based_risk_profile(db_session, b.id)
    assert result.baseline_risk == "low"
    assert result.overall_risk == "low"


@pytest.mark.asyncio
async def test_risk_profile_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await get_age_based_risk_profile(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# FN3: identify_era_specific_hotspots — unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hotspots_1960s_no_zones(db_session, admin_user):
    b = _make_building(admin_user.id, 1965)
    db_session.add(b)
    await db_session.commit()

    result = await identify_era_specific_hotspots(db_session, b.id)
    assert result.era == "1950_1975"
    assert len(result.hotspots) > 0
    assert result.total_matched_zones == 0
    # All hotspots should have no matched zone
    for h in result.hotspots:
        assert h.matched_zone_id is None


@pytest.mark.asyncio
async def test_hotspots_with_matching_zones(db_session, admin_user):
    b = _make_building(admin_user.id, 1965)
    db_session.add(b)
    await db_session.commit()

    z = Zone(
        id=uuid.uuid4(),
        building_id=b.id,
        zone_type="technical_room",
        name="Chaufferie",
    )
    db_session.add(z)
    await db_session.commit()

    result = await identify_era_specific_hotspots(db_session, b.id)
    matched = [h for h in result.hotspots if h.matched_zone_id is not None]
    assert len(matched) >= 1
    assert result.total_matched_zones >= 1
    assert matched[0].matched_zone_name == "Chaufferie"


@pytest.mark.asyncio
async def test_hotspots_post_1991_minimal(db_session, admin_user):
    b = _make_building(admin_user.id, 2005)
    db_session.add(b)
    await db_session.commit()

    result = await identify_era_specific_hotspots(db_session, b.id)
    assert result.era == "post_1991"
    assert len(result.hotspots) <= 2  # Only radon


@pytest.mark.asyncio
async def test_hotspots_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await identify_era_specific_hotspots(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# FN4: get_portfolio_age_distribution — unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_empty_org(db_session, org):
    result = await get_portfolio_age_distribution(db_session, org.id)
    assert result.total_buildings == 0
    assert result.era_buckets == []


@pytest.mark.asyncio
async def test_portfolio_with_buildings(db_session, org, org_user):
    b1 = _make_building(org_user.id, 1960, address="Rue A 1")
    b2 = _make_building(org_user.id, 1985, address="Rue B 2")
    b3 = _make_building(org_user.id, 2010, address="Rue C 3")
    db_session.add_all([b1, b2, b3])
    await db_session.commit()

    result = await get_portfolio_age_distribution(db_session, org.id)
    assert result.total_buildings == 3
    eras = {eb.era for eb in result.era_buckets}
    assert "1950_1975" in eras
    assert "1975_1991" in eras
    assert "post_1991" in eras


@pytest.mark.asyncio
async def test_portfolio_priority_buildings(db_session, org, org_user):
    b1 = _make_building(org_user.id, 1960, address="Old undiagnosed")
    b2 = _make_building(org_user.id, 2010, address="New building")
    db_session.add_all([b1, b2])
    await db_session.commit()

    result = await get_portfolio_age_distribution(db_session, org.id)
    # Old undiagnosed building should be in priority list
    priority_ids = [p.building_id for p in result.priority_buildings]
    assert b1.id in priority_ids
    # Post-1991 building should NOT be in priority list
    assert b2.id not in priority_ids


@pytest.mark.asyncio
async def test_portfolio_diagnosed_not_priority(db_session, org, org_user):
    b = _make_building(org_user.id, 1960)
    db_session.add(b)
    await db_session.commit()

    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=b.id,
        diagnostic_type="asbestos",
        status="completed",
    )
    db_session.add(d)
    await db_session.commit()

    result = await get_portfolio_age_distribution(db_session, org.id)
    priority_ids = [p.building_id for p in result.priority_buildings]
    assert b.id not in priority_ids
    # Bucket should show as diagnosed
    bucket = next(eb for eb in result.era_buckets if eb.era == "1950_1975")
    assert bucket.diagnosed_count == 1
    assert bucket.undiagnosed_count == 0


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_era_classification(client, admin_user, db_session, auth_headers):
    b = _make_building(admin_user.id, 1965)
    db_session.add(b)
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{b.id}/age-analysis", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["era"] == "1950_1975"
    assert data["diagnostic_priority"] == "critical"


@pytest.mark.asyncio
async def test_api_era_classification_404(client, auth_headers):
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/age-analysis", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_api_risk_profile(client, admin_user, db_session, auth_headers):
    b = _make_building(admin_user.id, 1960)
    db_session.add(b)
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{b.id}/age-risk-profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["baseline_risk"] == "elevated"
    assert data["era"] == "1950_1975"


@pytest.mark.asyncio
async def test_api_hotspots(client, admin_user, db_session, auth_headers):
    b = _make_building(admin_user.id, 1965)
    db_session.add(b)
    await db_session.commit()

    resp = await client.get(f"/api/v1/buildings/{b.id}/age-hotspots", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["era"] == "1950_1975"
    assert len(data["hotspots"]) > 0


@pytest.mark.asyncio
async def test_api_portfolio_age_distribution(client, admin_user, db_session, auth_headers, org, org_user):
    b = _make_building(org_user.id, 1960)
    db_session.add(b)
    await db_session.commit()

    resp = await client.get(f"/api/v1/organizations/{org.id}/age-distribution", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_buildings"] == 1


@pytest.mark.asyncio
async def test_api_unauthenticated(client):
    resp = await client.get(f"/api/v1/buildings/{uuid.uuid4()}/age-analysis")
    assert resp.status_code in (401, 403)
