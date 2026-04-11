"""Tests for commune intelligence service."""

import uuid

import pytest

from app.models.building import Building
from app.models.commune_profile import CommuneProfile
from app.models.user import User
from app.services.commune_intelligence_service import (
    compute_fiscal_attractiveness,
    compute_socioeconomic_profile,
    get_commune_for_building,
    get_commune_profile,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_user(db) -> User:
    from tests.conftest import _HASH_ADMIN

    u = User(
        id=uuid.uuid4(),
        email=f"commune-test-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role="admin",
        is_active=True,
        language="fr",
    )
    db.add(u)
    await db.flush()
    return u


async def _seed_commune(db, **overrides) -> CommuneProfile:
    data = {
        "id": uuid.uuid4(),
        "commune_number": 5586,
        "name": "Lausanne",
        "canton": "VD",
        "population": 146372,
        "population_year": 2023,
        "tax_multiplier": 1.545,
        "median_income": 58000,
        "homeowner_rate_pct": 17.2,
        "vacancy_rate_pct": 0.38,
        "unemployment_rate_pct": 4.8,
        "population_growth_pct": 1.2,
        "dominant_age_group": "mixed",
        "financial_health": "good",
        "active": True,
    }
    data.update(overrides)
    profile = CommuneProfile(**data)
    db.add(profile)
    await db.flush()
    return profile


async def _seed_building(db, user_id, municipality_ofs=5586, **overrides) -> Building:
    data = {
        "id": uuid.uuid4(),
        "address": "Rue de Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
        "municipality_ofs": municipality_ofs,
    }
    data.update(overrides)
    bldg = Building(**data)
    db.add(bldg)
    await db.flush()
    return bldg


# ---------------------------------------------------------------------------
# get_commune_profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_commune_profile_found(db_session):
    """Lookup existing commune by BFS number."""
    await _seed_commune(db_session)
    await db_session.commit()

    result = await get_commune_profile(db_session, 5586)
    assert result is not None
    assert result.name == "Lausanne"
    assert result.commune_number == 5586


@pytest.mark.asyncio
async def test_get_commune_profile_not_found(db_session):
    """Lookup non-existent commune returns None."""
    result = await get_commune_profile(db_session, 99999)
    assert result is None


@pytest.mark.asyncio
async def test_get_commune_profile_inactive_excluded(db_session):
    """Inactive commune profiles are not returned."""
    await _seed_commune(db_session, active=False)
    await db_session.commit()

    result = await get_commune_profile(db_session, 5586)
    assert result is None


# ---------------------------------------------------------------------------
# get_commune_for_building
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_commune_for_building_found(db_session):
    """Resolve commune from building municipality_ofs."""
    user = await _seed_user(db_session)
    await _seed_commune(db_session)
    bldg = await _seed_building(db_session, user.id, municipality_ofs=5586)
    await db_session.commit()

    result = await get_commune_for_building(db_session, bldg.id)
    assert result is not None
    assert result.name == "Lausanne"


@pytest.mark.asyncio
async def test_get_commune_for_building_no_municipality(db_session):
    """Building without municipality_ofs returns None."""
    user = await _seed_user(db_session)
    bldg = await _seed_building(db_session, user.id, municipality_ofs=None)
    await db_session.commit()

    result = await get_commune_for_building(db_session, bldg.id)
    assert result is None


@pytest.mark.asyncio
async def test_get_commune_for_building_unknown_building(db_session):
    """Unknown building ID returns None."""
    result = await get_commune_for_building(db_session, uuid.uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# compute_fiscal_attractiveness
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fiscal_attractiveness_basic(db_session):
    """Fiscal attractiveness returns expected structure."""
    await _seed_commune(db_session, commune_number=5586, name="Lausanne", tax_multiplier=1.545)
    await _seed_commune(db_session, commune_number=5585, name="Pully", tax_multiplier=1.365)
    await _seed_commune(db_session, commune_number=5561, name="Nyon", tax_multiplier=1.395)
    await db_session.commit()

    result = await compute_fiscal_attractiveness(db_session, 5586)
    assert result is not None
    assert result["commune"] == "Lausanne"
    assert result["canton"] == "VD"
    assert result["tax_multiplier"] == 1.545
    assert "canton_average" in result
    assert result["comparison"] in ("below_average", "at_average", "above_average")
    assert "yearly_tax_estimate_for_income" in result
    assert 50000 in result["yearly_tax_estimate_for_income"]
    assert 80000 in result["yearly_tax_estimate_for_income"]
    assert 100000 in result["yearly_tax_estimate_for_income"]
    assert "ranking_in_canton" in result
    assert "nearby_cheaper" in result


@pytest.mark.asyncio
async def test_fiscal_attractiveness_above_average(db_session):
    """Commune with high tax multiplier is above average."""
    await _seed_commune(db_session, commune_number=5586, name="Lausanne", tax_multiplier=1.600)
    await _seed_commune(db_session, commune_number=5585, name="Pully", tax_multiplier=1.200)
    await _seed_commune(db_session, commune_number=5561, name="Nyon", tax_multiplier=1.200)
    await db_session.commit()

    result = await compute_fiscal_attractiveness(db_session, 5586)
    assert result["comparison"] == "above_average"
    assert len(result["nearby_cheaper"]) == 2


@pytest.mark.asyncio
async def test_fiscal_attractiveness_not_found(db_session):
    """Non-existent commune returns None."""
    result = await compute_fiscal_attractiveness(db_session, 99999)
    assert result is None


@pytest.mark.asyncio
async def test_fiscal_attractiveness_ranking(db_session):
    """Ranking reflects position among canton peers."""
    await _seed_commune(db_session, commune_number=5585, name="Pully", tax_multiplier=1.200)
    await _seed_commune(db_session, commune_number=5561, name="Nyon", tax_multiplier=1.300)
    await _seed_commune(db_session, commune_number=5586, name="Lausanne", tax_multiplier=1.545)
    await db_session.commit()

    result = await compute_fiscal_attractiveness(db_session, 5586)
    assert result["ranking_in_canton"] == "3 of 3"

    result_pully = await compute_fiscal_attractiveness(db_session, 5585)
    assert result_pully["ranking_in_canton"] == "1 of 3"


# ---------------------------------------------------------------------------
# compute_socioeconomic_profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_socioeconomic_profile_full(db_session):
    """Full socioeconomic profile for building with known commune."""
    user = await _seed_user(db_session)
    await _seed_commune(
        db_session,
        commune_number=5586,
        median_income=72000,
        vacancy_rate_pct=0.38,
        population_growth_pct=1.2,
        tax_multiplier=1.545,
    )
    bldg = await _seed_building(db_session, user.id, municipality_ofs=5586)
    await db_session.commit()

    result = await compute_socioeconomic_profile(db_session, bldg.id)
    assert result is not None
    assert result["commune"]["name"] == "Lausanne"
    assert result["income_level"] == "high"
    assert result["market_tension"] == "high"
    assert result["demographic_trend"] == "growing"
    assert result["fiscal_pressure"] in ("high", "moderate", "low")
    assert "family_attractiveness" in result["scores"]
    assert "retiree_attractiveness" in result["scores"]
    assert "investor_attractiveness" in result["scores"]
    # Scores are 0-10
    for key in ("family_attractiveness", "retiree_attractiveness", "investor_attractiveness"):
        assert 0 <= result["scores"][key] <= 10


@pytest.mark.asyncio
async def test_socioeconomic_profile_low_income(db_session):
    """Low median income is classified correctly."""
    user = await _seed_user(db_session)
    await _seed_commune(db_session, commune_number=5586, median_income=42000)
    bldg = await _seed_building(db_session, user.id, municipality_ofs=5586)
    await db_session.commit()

    result = await compute_socioeconomic_profile(db_session, bldg.id)
    assert result["income_level"] == "low"


@pytest.mark.asyncio
async def test_socioeconomic_profile_missing_commune(db_session):
    """Building with no matching commune returns None."""
    user = await _seed_user(db_session)
    bldg = await _seed_building(db_session, user.id, municipality_ofs=88888)
    await db_session.commit()

    result = await compute_socioeconomic_profile(db_session, bldg.id)
    assert result is None


@pytest.mark.asyncio
async def test_socioeconomic_geneva_fiscal_pressure(db_session):
    """Geneva communes use different fiscal pressure thresholds."""
    user = await _seed_user(db_session)
    await _seed_commune(
        db_session,
        commune_number=6621,
        name="Genève",
        canton="GE",
        tax_multiplier=0.4405,
        median_income=62000,
        vacancy_rate_pct=0.45,
        population_growth_pct=0.9,
    )
    bldg = await _seed_building(
        db_session,
        user.id,
        municipality_ofs=6621,
        city="Genève",
        canton="GE",
    )
    await db_session.commit()

    result = await compute_socioeconomic_profile(db_session, bldg.id)
    assert result is not None
    assert result["commune"]["canton"] == "GE"
    # GE multiplier 0.4405 is between 0.43 and 0.45 → moderate
    assert result["fiscal_pressure"] == "moderate"
