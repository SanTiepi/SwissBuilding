"""Tests for building age intelligence service (Programme S/W)."""

import uuid

import pytest

from app.models.building import Building
from app.services.building_age_intelligence import (
    _classify_era,
    compute_age_risk_profile,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
    )


# ---------------------------------------------------------------------------
# Era classification (pure) tests
# ---------------------------------------------------------------------------


def test_classify_pre_1950():
    assert _classify_era(1935) == "pre_1950"
    assert _classify_era(1900) == "pre_1950"
    assert _classify_era(1949) == "pre_1950"


def test_classify_1950_1960():
    assert _classify_era(1950) == "1950_1960"
    assert _classify_era(1955) == "1950_1960"
    assert _classify_era(1959) == "1950_1960"


def test_classify_1960_1975():
    assert _classify_era(1960) == "1960_1975"
    assert _classify_era(1970) == "1960_1975"
    assert _classify_era(1974) == "1960_1975"


def test_classify_1975_1990():
    assert _classify_era(1975) == "1975_1990"
    assert _classify_era(1985) == "1975_1990"
    assert _classify_era(1989) == "1975_1990"


def test_classify_1990_2000():
    assert _classify_era(1990) == "1990_2000"
    assert _classify_era(1995) == "1990_2000"
    assert _classify_era(1999) == "1990_2000"


def test_classify_post_2000():
    assert _classify_era(2000) == "post_2000"
    assert _classify_era(2015) == "post_2000"
    assert _classify_era(2025) == "post_2000"


def test_classify_unknown():
    assert _classify_era(None) == "unknown"


# ---------------------------------------------------------------------------
# Boundary years
# ---------------------------------------------------------------------------


def test_classify_boundary_1950():
    assert _classify_era(1949) == "pre_1950"
    assert _classify_era(1950) == "1950_1960"


def test_classify_boundary_1960():
    assert _classify_era(1959) == "1950_1960"
    assert _classify_era(1960) == "1960_1975"


def test_classify_boundary_1975():
    assert _classify_era(1974) == "1960_1975"
    assert _classify_era(1975) == "1975_1990"


def test_classify_boundary_1990():
    assert _classify_era(1989) == "1975_1990"
    assert _classify_era(1990) == "1990_2000"


def test_classify_boundary_2000():
    assert _classify_era(1999) == "1990_2000"
    assert _classify_era(2000) == "post_2000"


# ---------------------------------------------------------------------------
# compute_age_risk_profile — async tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_profile_pre_1950(db_session, admin_user):
    b = _make_building(admin_user.id, 1935)
    db_session.add(b)
    await db_session.commit()

    result = await compute_age_risk_profile(db_session, b.id)
    assert result["era"] == "pre_1950"
    assert result["construction_year"] == 1935
    # Should have lead as high probability
    pollutant_types = [p["type"] for p in result["expected_pollutants"]]
    assert "lead" in pollutant_types
    lead = next(p for p in result["expected_pollutants"] if p["type"] == "lead")
    assert lead["probability"] > 0.7
    assert result["regulatory_era"] == "Pré-réglementaire"


@pytest.mark.asyncio
async def test_profile_peak_asbestos(db_session, admin_user):
    b = _make_building(admin_user.id, 1968)
    db_session.add(b)
    await db_session.commit()

    result = await compute_age_risk_profile(db_session, b.id)
    assert result["era"] == "1960_1975"
    assert "Pic amiante" in result["era_label"]
    pollutant_types = [p["type"] for p in result["expected_pollutants"]]
    assert "asbestos" in pollutant_types
    assert "pcb" in pollutant_types
    asbestos = next(p for p in result["expected_pollutants"] if p["type"] == "asbestos")
    assert asbestos["probability"] >= 0.9
    # Should recommend critical urgency diagnostics
    critical_diags = [d for d in result["recommended_diagnostics"] if d["urgency"] == "critical"]
    assert len(critical_diags) >= 2


@pytest.mark.asyncio
async def test_profile_modern_building(db_session, admin_user):
    b = _make_building(admin_user.id, 2015)
    db_session.add(b)
    await db_session.commit()

    result = await compute_age_risk_profile(db_session, b.id)
    assert result["era"] == "post_2000"
    assert "moderne" in result["era_label"].lower() or "2000" in result["era_label"]
    # Very few expected pollutants
    high_prob = [p for p in result["expected_pollutants"] if p["probability"] > 0.3]
    assert len(high_prob) == 0


@pytest.mark.asyncio
async def test_profile_unknown_year(db_session, admin_user):
    b = _make_building(admin_user.id, None)
    db_session.add(b)
    await db_session.commit()

    result = await compute_age_risk_profile(db_session, b.id)
    assert result["era"] == "unknown"
    assert result["construction_year"] is None
    # Should recommend diagnostics for all pollutants
    diag_types = [d["type"] for d in result["recommended_diagnostics"]]
    assert "asbestos" in diag_types
    assert "pcb" in diag_types


@pytest.mark.asyncio
async def test_profile_similar_buildings_count(db_session, admin_user):
    """Should count similar-era buildings in the system."""
    b1 = _make_building(admin_user.id, 1965, address="Bât 1")
    b2 = _make_building(admin_user.id, 1968, address="Bât 2")
    b3 = _make_building(admin_user.id, 1972, address="Bât 3")
    b4 = _make_building(admin_user.id, 2010, address="Bât moderne")
    db_session.add_all([b1, b2, b3, b4])
    await db_session.commit()

    result = await compute_age_risk_profile(db_session, b1.id)
    assert result["similar_buildings_in_system"] == 2  # b2 and b3 are same era


@pytest.mark.asyncio
async def test_profile_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await compute_age_risk_profile(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_profile_1975_1990_declining(db_session, admin_user):
    b = _make_building(admin_user.id, 1982)
    db_session.add(b)
    await db_session.commit()

    result = await compute_age_risk_profile(db_session, b.id)
    assert result["era"] == "1975_1990"
    asbestos = next(p for p in result["expected_pollutants"] if p["type"] == "asbestos")
    pcb = next(p for p in result["expected_pollutants"] if p["type"] == "pcb")
    # Both should be present but at moderate probability
    assert 0.3 <= asbestos["probability"] <= 0.7
    assert 0.3 <= pcb["probability"] <= 0.6


@pytest.mark.asyncio
async def test_profile_1990_2000_post_ban(db_session, admin_user):
    b = _make_building(admin_user.id, 1995)
    db_session.add(b)
    await db_session.commit()

    result = await compute_age_risk_profile(db_session, b.id)
    assert result["era"] == "1990_2000"
    # Asbestos should be negligible
    asbestos = next(p for p in result["expected_pollutants"] if p["type"] == "asbestos")
    assert asbestos["probability"] < 0.1
    assert "Post-ban" in result["regulatory_era"]


@pytest.mark.asyncio
async def test_profile_has_typical_issues(db_session, admin_user):
    """Every era profile should include typical issues."""
    b = _make_building(admin_user.id, 1960)
    db_session.add(b)
    await db_session.commit()

    result = await compute_age_risk_profile(db_session, b.id)
    assert len(result["typical_issues"]) > 0
    assert isinstance(result["typical_issues"][0], str)
    assert result["energy_era"] is not None
    assert result["regulatory_era"] is not None
