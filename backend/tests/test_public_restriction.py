"""Tests for PublicLawRestriction model, aggregation, and auto-create from enrichment."""

import uuid

import pytest

from app.models.building import Building
from app.models.public_law_restriction import PublicLawRestriction
from app.models.user import User
from app.services.public_restriction_service import (
    _build_summary,
    _compute_feasibility,
    aggregate_restrictions,
    auto_create_restrictions_from_enrichment,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(db):
    user = User(
        id=uuid.uuid4(),
        email=f"plr-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="PLR",
        last_name="Tester",
        role="admin",
        is_active=True,
        language="fr",
    )
    db.add(user)
    await db.flush()
    return user


async def _create_building(db, user_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _create_restriction(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "restriction_type": "zone_affectation",
        "description": "Zone residentielle",
        "legal_reference": "LAT Art. 15",
        "authority": "commune",
        "impact_on_renovation": "none",
        "source": "manual",
        "active": True,
    }
    defaults.update(kwargs)
    plr = PublicLawRestriction(**defaults)
    db.add(plr)
    await db.flush()
    return plr


# ---------------------------------------------------------------------------
# Model CRUD tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_restriction_basic(db_session):
    """PublicLawRestriction can be created with required fields."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    plr = await _create_restriction(db_session, building.id)
    await db_session.commit()

    assert plr.id is not None
    assert plr.building_id == building.id
    assert plr.restriction_type == "zone_affectation"
    assert plr.active is True


@pytest.mark.asyncio
async def test_create_restriction_all_types(db_session):
    """All restriction types can be stored."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)

    types = [
        "zone_affectation",
        "alignement",
        "distance",
        "servitude_publique",
        "protection_patrimoine",
        "zone_danger",
        "zone_protection_eaux",
        "site_contamine",
        "zone_bruit",
        "other",
    ]
    for rtype in types:
        await _create_restriction(db_session, building.id, restriction_type=rtype)
    await db_session.commit()


@pytest.mark.asyncio
async def test_restriction_default_values(db_session):
    """Default values for impact and source are applied."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    plr = PublicLawRestriction(
        building_id=building.id,
        restriction_type="other",
    )
    db_session.add(plr)
    await db_session.flush()
    await db_session.commit()

    assert plr.impact_on_renovation == "none"
    assert plr.source == "manual"
    assert plr.active is True


# ---------------------------------------------------------------------------
# Aggregation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aggregate_empty_building(db_session):
    """Building with no restrictions returns unrestricted."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    await db_session.commit()

    result = await aggregate_restrictions(db_session, building.id)
    assert result["total_count"] == 0
    assert result["blocking_count"] == 0
    assert result["major_count"] == 0
    assert result["renovation_feasibility"] == "unrestricted"
    assert result["restrictions"] == []


@pytest.mark.asyncio
async def test_aggregate_from_enrichment_meta(db_session):
    """Restrictions are extracted from source_metadata_json enrichment data."""
    user = await _create_user(db_session)
    building = await _create_building(
        db_session,
        user.id,
        source_metadata_json={
            "heritage": {"isos_protected": True, "isos_category": "a", "site_name": "Vieux-Lausanne"},
            "building_zones": {"zone_type": "residential", "zone_description": "Zone residentielle"},
        },
    )
    await db_session.commit()

    result = await aggregate_restrictions(db_session, building.id)
    assert result["total_count"] == 2
    assert result["major_count"] == 1  # heritage = major
    types = {r["type"] for r in result["restrictions"]}
    assert "protection_patrimoine" in types
    assert "zone_affectation" in types


@pytest.mark.asyncio
async def test_aggregate_mixed_sources(db_session):
    """Both enrichment and manual restrictions are combined."""
    user = await _create_user(db_session)
    building = await _create_building(
        db_session,
        user.id,
        source_metadata_json={
            "contaminated_sites": {"is_contaminated": True, "site_type": "industrie"},
        },
    )
    await _create_restriction(
        db_session,
        building.id,
        restriction_type="alignement",
        impact_on_renovation="minor",
    )
    await db_session.commit()

    result = await aggregate_restrictions(db_session, building.id)
    assert result["total_count"] == 2
    sources = {r["source"] for r in result["restrictions"]}
    assert "enrichment" in sources
    assert "manual" in sources


@pytest.mark.asyncio
async def test_aggregate_blocking_feasibility(db_session):
    """Blocking restriction makes feasibility 'blocked'."""
    user = await _create_user(db_session)
    building = await _create_building(
        db_session,
        user.id,
        source_metadata_json={
            "flood_zones": {"flood_danger_level": "elevee"},
        },
    )
    await db_session.commit()

    result = await aggregate_restrictions(db_session, building.id)
    assert result["blocking_count"] == 1
    assert result["renovation_feasibility"] == "blocked"


@pytest.mark.asyncio
async def test_aggregate_heavily_constrained(db_session):
    """Two major restrictions -> heavily_constrained."""
    user = await _create_user(db_session)
    building = await _create_building(
        db_session,
        user.id,
        source_metadata_json={
            "heritage": {"isos_protected": True, "site_name": "Old Town"},
            "contaminated_sites": {"is_contaminated": True, "site_type": "depot"},
        },
    )
    await db_session.commit()

    result = await aggregate_restrictions(db_session, building.id)
    assert result["major_count"] == 2
    assert result["renovation_feasibility"] == "heavily_constrained"


@pytest.mark.asyncio
async def test_aggregate_not_found(db_session):
    """Non-existent building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await aggregate_restrictions(db_session, uuid.uuid4())


# ---------------------------------------------------------------------------
# Auto-create from enrichment tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_create_from_enrichment(db_session):
    """Auto-creates PublicLawRestriction records from enrichment meta."""
    user = await _create_user(db_session)
    building = await _create_building(
        db_session,
        user.id,
        source_metadata_json={
            "heritage": {"isos_protected": True, "isos_category": "b", "site_name": "Centre historique"},
            "contaminated_sites": {"is_contaminated": True, "site_type": "industrie"},
            "water_protection": {"protection_zone": "S2"},
        },
    )
    await db_session.commit()

    created = await auto_create_restrictions_from_enrichment(db_session, building.id)
    await db_session.commit()

    assert len(created) == 3
    types = {plr.restriction_type for plr in created}
    assert types == {"protection_patrimoine", "site_contamine", "zone_protection_eaux"}
    assert all(plr.source == "enrichment" for plr in created)


@pytest.mark.asyncio
async def test_auto_create_idempotent(db_session):
    """Running auto-create twice does not duplicate records."""
    user = await _create_user(db_session)
    building = await _create_building(
        db_session,
        user.id,
        source_metadata_json={
            "heritage": {"isos_protected": True, "site_name": "Test"},
        },
    )
    await db_session.commit()

    first_run = await auto_create_restrictions_from_enrichment(db_session, building.id)
    await db_session.commit()
    assert len(first_run) == 1

    second_run = await auto_create_restrictions_from_enrichment(db_session, building.id)
    await db_session.commit()
    assert len(second_run) == 0


@pytest.mark.asyncio
async def test_auto_create_skips_empty_enrichment(db_session):
    """No records created when enrichment data is absent."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    await db_session.commit()

    created = await auto_create_restrictions_from_enrichment(db_session, building.id)
    assert len(created) == 0


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


class TestComputeFeasibility:
    def test_unrestricted(self):
        assert _compute_feasibility(0, 0) == "unrestricted"

    def test_constrained(self):
        assert _compute_feasibility(0, 1) == "constrained"

    def test_heavily_constrained(self):
        assert _compute_feasibility(0, 2) == "heavily_constrained"

    def test_blocked(self):
        assert _compute_feasibility(1, 0) == "blocked"
        assert _compute_feasibility(2, 3) == "blocked"


class TestBuildSummary:
    def test_empty(self):
        assert _build_summary([], 0, 0) == "Aucune restriction de droit public connue"

    def test_with_blocking(self):
        restrictions = [{"impact": "blocking", "description": "Zone inondation"}]
        summary = _build_summary(restrictions, 1, 0)
        assert "bloquante" in summary
        assert "Zone inondation" in summary
