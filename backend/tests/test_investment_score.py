"""Tests for investment score service — Programme R+V composite."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.models.user import User
from app.services.investment_score_service import compute_investment_score
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _user(db: AsyncSession) -> User:
    u = User(
        id=uuid.uuid4(),
        email=f"inv-{uuid.uuid4().hex[:8]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Inv",
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
    canton: str = "VD",
    surface: float = 150.0,
    construction_year: int = 2000,
    enrichment: dict | None = None,
) -> Building:
    b = Building(
        id=uuid.uuid4(),
        address=f"Rue Inv {uuid.uuid4().hex[:4]}",
        postal_code="1000",
        city="Lausanne",
        canton=canton,
        building_type="residential",
        construction_year=construction_year,
        surface_area_m2=surface,
        created_by=user_id,
        status="active",
        source_metadata_json=enrichment,
    )
    db.add(b)
    await db.flush()
    return b


async def _add_pollutants(
    db: AsyncSession,
    building_id: uuid.UUID,
    samples: list[dict],
) -> None:
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type="pollutant",
        status="completed",
    )
    db.add(diag)
    await db.flush()
    for i, s in enumerate(samples):
        db.add(
            Sample(
                id=uuid.uuid4(),
                diagnostic_id=diag.id,
                sample_number=f"S-{i + 1}",
                pollutant_type=s.get("pollutant_type", "asbestos"),
                risk_level=s.get("risk_level", "high"),
                threshold_exceeded=s.get("threshold_exceeded", True),
            )
        )
    await db.flush()


# ===========================================================================
# compute_investment_score
# ===========================================================================


@pytest.mark.asyncio
async def test_investment_score_basic(db_session):
    """Basic score should return valid structure."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id)
    await db_session.commit()

    result = await compute_investment_score(db_session, bldg.id)
    assert 0 <= result["score"] <= 100
    assert result["grade"] in ("A", "B", "C", "D", "E", "F")
    assert "yield" in result["breakdown"]
    assert "risk" in result["breakdown"]
    assert isinstance(result["strengths"], list)
    assert isinstance(result["weaknesses"], list)
    assert isinstance(result["recommendation"], str)


@pytest.mark.asyncio
async def test_investment_score_clean_building_high(db_session):
    """Clean recent building should score higher than polluted old one."""
    user = await _user(db_session)
    good = await _building(db_session, user.id, construction_year=2020)
    bad = await _building(db_session, user.id, construction_year=1950)
    await _add_pollutants(
        db_session,
        bad.id,
        [
            {"pollutant_type": "asbestos", "risk_level": "critical", "threshold_exceeded": True},
            {"pollutant_type": "pcb", "risk_level": "high", "threshold_exceeded": True},
            {"pollutant_type": "lead", "risk_level": "high", "threshold_exceeded": True},
        ],
    )
    await db_session.commit()

    good_score = await compute_investment_score(db_session, good.id)
    bad_score = await compute_investment_score(db_session, bad.id)
    assert good_score["score"] > bad_score["score"]


@pytest.mark.asyncio
async def test_investment_score_geology_impact(db_session):
    """Building on contaminated site should score lower on risk."""
    user = await _user(db_session)
    safe = await _building(db_session, user.id)
    risky = await _building(
        db_session,
        user.id,
        enrichment={
            "contaminated_sites": {"is_contaminated": True},
            "seismic": {"seismic_zone": "3a"},
        },
    )
    await db_session.commit()

    safe_result = await compute_investment_score(db_session, safe.id)
    risky_result = await compute_investment_score(db_session, risky.id)
    assert safe_result["breakdown"]["risk"]["score"] > risky_result["breakdown"]["risk"]["score"]


@pytest.mark.asyncio
async def test_investment_score_grade_boundaries(db_session):
    """Grade should correspond to score ranges."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id)
    await db_session.commit()

    result = await compute_investment_score(db_session, bldg.id)
    score = result["score"]
    grade = result["grade"]

    if score >= 80:
        assert grade == "A"
    elif score >= 65:
        assert grade == "B"
    elif score >= 50:
        assert grade == "C"
    elif score >= 35:
        assert grade == "D"
    elif score >= 20:
        assert grade == "E"
    else:
        assert grade == "F"


@pytest.mark.asyncio
async def test_investment_score_not_found(db_session):
    """Non-existent building should raise ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await compute_investment_score(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_investment_score_breakdown_weights(db_session):
    """All 5 components should be present in breakdown."""
    user = await _user(db_session)
    bldg = await _building(db_session, user.id)
    await db_session.commit()

    result = await compute_investment_score(db_session, bldg.id)
    expected_keys = {"yield", "appreciation", "risk", "energy", "subsidy"}
    assert set(result["breakdown"].keys()) == expected_keys
    for k in expected_keys:
        assert "score" in result["breakdown"][k]
        assert "weight" in result["breakdown"][k]


@pytest.mark.asyncio
async def test_investment_score_subsidy_boost(db_session):
    """Building with subsidies in enrichment should score higher on subsidy component."""
    user = await _user(db_session)
    no_sub = await _building(db_session, user.id)
    with_sub = await _building(
        db_session,
        user.id,
        enrichment={
            "subsidies": {
                "eligible_programs": ["Programme bâtiments", "Bonus énergie"],
                "total_estimated_chf": 60000,
            }
        },
    )
    await db_session.commit()

    r1 = await compute_investment_score(db_session, no_sub.id)
    r2 = await compute_investment_score(db_session, with_sub.id)
    assert r2["breakdown"]["subsidy"]["score"] > r1["breakdown"]["subsidy"]["score"]


@pytest.mark.asyncio
async def test_investment_score_strengths_weaknesses(db_session):
    """Strengths and weaknesses should reflect component scores."""
    user = await _user(db_session)
    # Polluted old building = weak on risk + energy
    bldg = await _building(db_session, user.id, construction_year=1940)
    await _add_pollutants(
        db_session,
        bldg.id,
        [{"pollutant_type": "asbestos", "risk_level": "critical", "threshold_exceeded": True}],
    )
    await db_session.commit()

    result = await compute_investment_score(db_session, bldg.id)
    # Risk should be in weaknesses (critical pollutant = low risk score)
    assert "risk" in result["weaknesses"] or "energy" in result["weaknesses"]
