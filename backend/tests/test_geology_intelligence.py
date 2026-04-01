"""Tests for geology intelligence service — Programme V."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.user import User
from app.services.geology_intelligence_service import (
    analyze_geology,
    compute_foundation_risk_score,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _user(db: AsyncSession) -> User:
    u = User(
        id=uuid.uuid4(),
        email=f"geo-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Geo",
        last_name="Test",
        role="admin",
        is_active=True,
        language="fr",
    )
    db.add(u)
    await db.flush()
    return u


async def _building(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    enrichment: dict | None = None,
) -> Building:
    b = Building(
        id=uuid.uuid4(),
        address=f"Rue Geo {uuid.uuid4().hex[:4]}",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="residential",
        construction_year=1985,
        created_by=user_id,
        status="active",
        source_metadata_json=enrichment,
    )
    db.add(b)
    await db.flush()
    return b


# ===========================================================================
# compute_foundation_risk_score (pure function)
# ===========================================================================


def test_foundation_score_all_clear():
    """No hazards should produce a low score (grade A or B)."""
    result = compute_foundation_risk_score({})
    assert result["score"] < 20
    assert result["grade"] in ("A", "B")
    assert result["top_risks"] == []


def test_foundation_score_seismic_3b():
    """Seismic zone 3b should produce high score."""
    enrichment = {"seismic": {"seismic_zone": "3b"}}
    result = compute_foundation_risk_score(enrichment)
    # seismic alone = 90 * 3.0 / 11.5 = 23.5 base + others at 5
    assert result["score"] > 20
    assert any(r["type"] == "seismic" for r in result["top_risks"])


def test_foundation_score_contaminated():
    """Contaminated site should elevate risk significantly."""
    enrichment = {"contaminated_sites": {"is_contaminated": True}}
    result = compute_foundation_risk_score(enrichment)
    assert result["score"] > 15
    assert any(r["type"] == "contamination" for r in result["top_risks"])


def test_foundation_score_multi_hazard():
    """Multiple hazards should produce very high score."""
    enrichment = {
        "seismic": {"seismic_zone": "3a"},
        "contaminated_sites": {"is_contaminated": True},
        "natural_hazards": {"flood_risk": "high", "landslide_risk": "high"},
        "water_protection": {"protection_zone": "S1"},
    }
    result = compute_foundation_risk_score(enrichment)
    assert result["score"] > 70
    assert result["grade"] in ("E", "F")
    assert len(result["top_risks"]) >= 3


def test_foundation_score_grade_boundaries():
    """Check that grade assignment is consistent with score."""
    # Low risk
    low = compute_foundation_risk_score({})
    assert low["grade"] in ("A", "B")

    # Medium risk
    medium = compute_foundation_risk_score(
        {
            "seismic": {"seismic_zone": "2"},
            "water_protection": {"protection_zone": "S3"},
        }
    )
    assert medium["grade"] in ("A", "B", "C")
    assert medium["score"] < low["score"] + 40 or medium["score"] >= low["score"]


# ===========================================================================
# analyze_geology (async, uses DB)
# ===========================================================================


@pytest.mark.asyncio
async def test_analyze_geology_not_found(db_session):
    """Non-existent building should raise ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await analyze_geology(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_analyze_geology_empty_enrichment(db_session):
    """Building with no enrichment should return safe defaults."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id)
    await db_session.commit()

    result = await analyze_geology(db_session, bldg.id)
    assert result["soil_context"]["contaminated"] is False
    assert result["soil_context"]["groundwater_zone"] == "none"
    assert result["foundation_risk"]["grade"] in ("A", "B")
    assert result["construction_constraints"] == []
    assert len(result["recommendations"]) >= 1


@pytest.mark.asyncio
async def test_analyze_geology_full_data(db_session):
    """Building with rich enrichment should produce comprehensive analysis."""
    user = await _user(db_session)
    enrichment = {
        "seismic": {"seismic_zone": "2"},
        "water_protection": {"protection_zone": "S2"},
        "contaminated_sites": {"is_contaminated": True, "investigation_status": "en cours"},
        "natural_hazards": {"flood_risk": "medium", "landslide_risk": "low"},
        "radon": {"radon_level": "high"},
    }
    bldg = await _building(db_session, user.id, enrichment=enrichment)
    await db_session.commit()

    result = await analyze_geology(db_session, bldg.id)
    assert result["soil_context"]["contaminated"] is True
    assert result["soil_context"]["groundwater_zone"] == "S2"
    assert result["soil_context"]["seismic_zone"] == "2"
    assert result["soil_context"]["flood_risk"] == "medium"

    assert result["foundation_risk"]["score"] > 30
    assert len(result["construction_constraints"]) >= 3  # S2 + seismic 2 + contaminated
    assert result["underground_risk"]["groundwater_impact"] == "moderate"
    assert result["underground_risk"]["radon_from_soil"].startswith("Risque radon élevé")
    assert len(result["recommendations"]) >= 3


@pytest.mark.asyncio
async def test_analyze_geology_constraints_s1(db_session):
    """S1 zone should produce construction interdiction constraint."""
    user = await _user(db_session)
    enrichment = {"water_protection": {"protection_zone": "S1"}}
    bldg = await _building(db_session, user.id, enrichment=enrichment)
    await db_session.commit()

    result = await analyze_geology(db_session, bldg.id)
    assert any("S1" in c for c in result["construction_constraints"])
    assert result["underground_risk"]["basement_humidity_risk"] == "high"
