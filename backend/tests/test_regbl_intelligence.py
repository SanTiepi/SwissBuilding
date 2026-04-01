"""Tests for the RegBL Intelligence Service."""

import uuid

import pytest

from app.models.building import Building
from app.models.user import User
from app.services.regbl_intelligence_service import (
    _classify_era,
    _compute_renovation_need_score,
    _decade_label,
    _generate_insights,
    analyze_regbl_data,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(db):
    user = User(
        id=uuid.uuid4(),
        email=f"regbl-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="RegBL",
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
        "construction_year": 1968,
        "building_type": "residential",
        "created_by": user_id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


# ---------------------------------------------------------------------------
# Full analysis tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_analysis_with_regbl_data(db_session):
    """Full analysis with rich RegBL data returns all sections."""
    user = await _create_user(db_session)
    building = await _create_building(
        db_session,
        user.id,
        source_metadata_json={
            "regbl_data": {
                "construction_year": 1968,
                "floors": 4,
                "dwellings": 6,
                "living_area_m2": 450.0,
                "heating_type_code": "7420",
                "energy_source_code": "7520",  # mazout
                "building_category_code": "1040",
                "building_class_code": "1110",
                "renovation_period_code": None,
            }
        },
    )
    await db_session.commit()

    result = await analyze_regbl_data(db_session, building.id)

    # Construction
    assert result["construction"]["year"] == 1968
    assert result["construction"]["decade"] == "1960s"
    assert result["construction"]["era_label"] is not None
    assert "1961-1980" in result["construction"]["era_label"]
    assert result["construction"]["building_class"] is not None
    assert result["construction"]["building_category"] is not None

    # Physical
    assert result["physical"]["floors"] == 4
    assert result["physical"]["dwellings"] == 6
    assert result["physical"]["living_area_m2"] == 450.0

    # Energy
    assert result["energy"]["heating_type"] is not None
    assert "Chauffage central" in result["energy"]["heating_type"]
    assert result["energy"]["energy_source"] is not None
    assert "Mazout" in result["energy"]["energy_source"]

    # Renovation
    assert result["renovation"]["renovation_status"] == "never"
    assert result["renovation"]["renovation_need_score"] > 0

    # Data quality
    assert result["data_quality"]["fields_available"] >= 7
    assert result["data_quality"]["fields_total"] == 39
    assert result["data_quality"]["completeness_pct"] > 0

    # Insights
    assert isinstance(result["insights"], list)
    assert len(result["insights"]) > 0


@pytest.mark.asyncio
async def test_analysis_missing_regbl_data(db_session):
    """Building without RegBL data returns empty but structured result."""
    user = await _create_user(db_session)
    building = await _create_building(db_session, user.id)
    await db_session.commit()

    result = await analyze_regbl_data(db_session, building.id)

    # Construction year from building model directly
    assert result["construction"]["year"] == 1968
    assert result["construction"]["building_class"] is None
    assert result["construction"]["building_category"] is None

    # Missing critical fields
    assert len(result["data_quality"]["missing_critical"]) == len(
        [
            "construction_year",
            "floors",
            "dwellings",
            "heating_type_code",
            "energy_source_code",
            "building_category_code",
            "living_area_m2",
        ]
    )


@pytest.mark.asyncio
async def test_analysis_not_found(db_session):
    """Non-existent building raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await analyze_regbl_data(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_heating_oil_insight(db_session):
    """Oil heating triggers replacement warning insight."""
    user = await _create_user(db_session)
    building = await _create_building(
        db_session,
        user.id,
        source_metadata_json={
            "regbl_data": {
                "heating_type_code": "7420",
                "energy_source_code": "7520",  # mazout
            }
        },
    )
    await db_session.commit()

    result = await analyze_regbl_data(db_session, building.id)
    oil_insights = [i for i in result["insights"] if "mazout" in i.lower() or "remplacement" in i.lower()]
    assert len(oil_insights) >= 1


@pytest.mark.asyncio
async def test_renovation_need_old_fossil(db_session):
    """Old building with fossil heating has high renovation need score."""
    user = await _create_user(db_session)
    building = await _create_building(
        db_session,
        user.id,
        construction_year=1955,
        source_metadata_json={
            "regbl_data": {
                "construction_year": 1955,
                "heating_type_code": "7420",
                "energy_source_code": "7520",
            }
        },
    )
    await db_session.commit()

    result = await analyze_regbl_data(db_session, building.id)
    assert result["renovation"]["renovation_need_score"] >= 70


@pytest.mark.asyncio
async def test_recent_building_low_renovation_need(db_session):
    """Recently built building with heat pump has low renovation score."""
    user = await _create_user(db_session)
    building = await _create_building(
        db_session,
        user.id,
        construction_year=2020,
        source_metadata_json={
            "regbl_data": {
                "construction_year": 2020,
                "heating_type_code": "7436",  # heat pump
                "energy_source_code": "7511",  # geothermal
            }
        },
    )
    await db_session.commit()

    result = await analyze_regbl_data(db_session, building.id)
    assert result["renovation"]["renovation_need_score"] <= 20


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


class TestClassifyEra:
    def test_none(self):
        assert _classify_era(None) is None

    def test_pre_1900(self):
        assert _classify_era(1850) == "pre_1900"

    def test_post_2010(self):
        assert _classify_era(2022) == "post_2010"

    def test_1961_1980(self):
        assert _classify_era(1968) == "1961_1980"


class TestDecadeLabel:
    def test_none(self):
        assert _decade_label(None) is None

    def test_1960s(self):
        assert _decade_label(1968) == "1960s"

    def test_2020s(self):
        assert _decade_label(2023) == "2020s"


class TestRenovationNeedScore:
    def test_new_building(self):
        score = _compute_renovation_need_score(2022, None, "7436", "7511")
        assert score <= 10

    def test_old_oil_no_renovation(self):
        score = _compute_renovation_need_score(1955, None, "7420", "7520")
        assert score >= 80

    def test_renovated_modern(self):
        score = _compute_renovation_need_score(1970, 2015, "7436", "7511")
        assert score <= 30

    def test_no_data(self):
        score = _compute_renovation_need_score(None, None, None, None)
        assert score == 0


class TestGenerateInsights:
    def test_oil_heating_insight(self):
        insights = _generate_insights(1968, None, "7520", "7420", 6, 450.0, 4)
        assert any("remplacement" in i.lower() or "mazout" in i.lower() for i in insights)

    def test_no_renovation_insight(self):
        insights = _generate_insights(1955, None, "7511", "7436", None, None, None)
        assert any("aucune renovation" in i.lower() for i in insights)

    def test_high_floors_insight(self):
        insights = _generate_insights(1968, None, None, None, None, None, 6)
        assert any("accessibilite" in i.lower() for i in insights)
