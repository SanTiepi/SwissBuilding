"""Tests for CommuneProfile model + seed verification."""

import uuid

import pytest

from app.models.commune_profile import CommuneProfile
from app.seeds.seed_commune_profiles import COMMUNES

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LAUSANNE = {
    "commune_number": 5586,
    "name": "Lausanne",
    "canton": "VD",
    "population": 146372,
    "population_year": 2023,
    "tax_multiplier": 1.545,
    "median_income": 58000,
}


async def _create_profile(db, **overrides) -> CommuneProfile:
    data = {
        "id": uuid.uuid4(),
        "commune_number": 9999,
        "name": "TestCommune",
        "canton": "VD",
        "population": 10000,
        "population_year": 2023,
        "tax_multiplier": 1.400,
        "active": True,
    }
    data.update(overrides)
    profile = CommuneProfile(**data)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


# ---------------------------------------------------------------------------
# Model CRUD tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_commune_profile(db_session):
    """Create a commune profile with all fields."""
    profile = await _create_profile(db_session)
    assert profile.id is not None
    assert profile.commune_number == 9999
    assert profile.name == "TestCommune"
    assert profile.active is True


@pytest.mark.asyncio
async def test_commune_profile_defaults(db_session):
    """Verify default values (active=True, timestamps populated)."""
    profile = await _create_profile(db_session)
    assert profile.active is True
    assert profile.created_at is not None


@pytest.mark.asyncio
async def test_commune_profile_nullable_fields(db_session):
    """Optional fields can be None."""
    profile = await _create_profile(
        db_session,
        median_income=None,
        homeowner_rate_pct=None,
        vacancy_rate_pct=None,
        unemployment_rate_pct=None,
        population_growth_pct=None,
        dominant_age_group=None,
        financial_health=None,
    )
    assert profile.median_income is None
    assert profile.dominant_age_group is None


@pytest.mark.asyncio
async def test_commune_profile_unique_commune_number(db_session):
    """commune_number has unique constraint in model definition."""
    table = CommuneProfile.__table__
    # Verify unique=True on commune_number column
    col = table.columns["commune_number"]
    assert col.unique is True, "commune_number column must have unique=True"


@pytest.mark.asyncio
async def test_commune_profile_update(db_session):
    """Update fields on an existing profile."""
    profile = await _create_profile(db_session)
    profile.population = 20000
    profile.tax_multiplier = 1.500
    await db_session.commit()
    await db_session.refresh(profile)
    assert profile.population == 20000
    assert profile.tax_multiplier == 1.500


@pytest.mark.asyncio
async def test_commune_profile_deactivate(db_session):
    """Deactivating a commune profile."""
    profile = await _create_profile(db_session)
    profile.active = False
    await db_session.commit()
    await db_session.refresh(profile)
    assert profile.active is False


@pytest.mark.asyncio
async def test_commune_profile_canton_values(db_session):
    """Canton field stores 2-char codes."""
    for canton in ["VD", "GE", "ZH", "BE", "VS", "FR", "BS"]:
        profile = await _create_profile(
            db_session,
            commune_number=7000 + hash(canton) % 1000,
            canton=canton,
        )
        assert profile.canton == canton


# ---------------------------------------------------------------------------
# Seed data verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_commune_count():
    """Seed data contains expected number of communes."""
    assert len(COMMUNES) == 15


@pytest.mark.asyncio
async def test_seed_commune_ids_unique():
    """All seed communes have unique IDs and BFS numbers."""
    ids = [c["id"] for c in COMMUNES]
    assert len(ids) == len(set(ids))
    numbers = [c["commune_number"] for c in COMMUNES]
    assert len(numbers) == len(set(numbers))


@pytest.mark.asyncio
async def test_seed_lausanne_data():
    """Lausanne seed data matches expected values."""
    lausanne = next(c for c in COMMUNES if c["name"] == "Lausanne")
    assert lausanne["commune_number"] == 5586
    assert lausanne["canton"] == "VD"
    assert lausanne["tax_multiplier"] == 1.545
    assert lausanne["population"] == 146372
