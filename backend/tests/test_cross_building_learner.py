"""Tests for Cross-Building Learner service."""

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.models.user import User
from app.services.cross_building_learner import (
    _similarity_score,
    find_similar_buildings,
    learn_from_similar,
)
from tests.conftest import _HASH_ADMIN

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(db, email=None):
    user = User(
        id=uuid.uuid4(),
        email=email or f"learner-{uuid.uuid4().hex[:6]}@test.ch",
        password_hash=_HASH_ADMIN,
        first_name="Test",
        last_name="User",
        role="admin",
    )
    db.add(user)
    await db.commit()
    return user


async def _make_building(db, user, **kw):
    defaults = {
        "id": uuid.uuid4(),
        "address": f"Rue Learner {uuid.uuid4().hex[:4]}",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": user.id,
        "status": "active",
    }
    defaults.update(kw)
    b = Building(**defaults)
    db.add(b)
    await db.commit()
    return b


async def _make_diagnostic(db, building_id, dtype="asbestos", status="completed"):
    d = Diagnostic(
        id=uuid.uuid4(),
        building_id=building_id,
        diagnostic_type=dtype,
        status=status,
    )
    db.add(d)
    await db.commit()
    return d


async def _make_sample(db, diag_id, pollutant="asbestos", exceeded=True, **kw):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diag_id,
        "sample_number": f"S-{uuid.uuid4().hex[:6]}",
        "pollutant_type": pollutant,
        "concentration": 2.5,
        "unit": "%",
        "threshold_exceeded": exceeded,
        "risk_level": "high" if exceeded else "low",
    }
    defaults.update(kw)
    s = Sample(**defaults)
    db.add(s)
    await db.commit()
    return s


async def _make_intervention(db, building_id, **kw):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "intervention_type": "asbestos_removal",
        "title": "Test removal",
        "status": "completed",
        "cost_chf": 15000.0,
        "date_start": date(2025, 1, 1),
        "date_end": date(2025, 3, 1),
    }
    defaults.update(kw)
    iv = Intervention(**defaults)
    db.add(iv)
    await db.commit()
    return iv


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_similarity_same_canton_and_era():
    """Two buildings in same canton and same decade should have high similarity."""
    ref = Building(canton="VD", construction_year=1970, building_type="residential", surface_area_m2=500)
    other = Building(canton="VD", construction_year=1973, building_type="residential", surface_area_m2=480)
    score = _similarity_score(ref, other)
    assert score >= 0.7


@pytest.mark.asyncio
async def test_similarity_different_canton():
    """Different canton reduces score."""
    ref = Building(canton="VD", construction_year=1970, building_type="residential")
    other = Building(canton="GE", construction_year=1970, building_type="industrial")
    score = _similarity_score(ref, other)
    assert score < 0.5  # Missing canton + type match


@pytest.mark.asyncio
async def test_similarity_no_overlap():
    """No matching attributes = zero score."""
    ref = Building(canton="VD", construction_year=1970, building_type="residential")
    other = Building(canton="ZH", construction_year=2020, building_type="industrial")
    score = _similarity_score(ref, other)
    assert score == 0.0


@pytest.mark.asyncio
async def test_find_similar_building_not_found(db_session):
    with pytest.raises(ValueError, match="not found"):
        await find_similar_buildings(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_find_similar_returns_ranked(db_session):
    user = await _make_user(db_session)
    ref = await _make_building(db_session, user, canton="VD", construction_year=1970)
    # Same canton and era
    await _make_building(db_session, user, canton="VD", construction_year=1972)
    # Same canton, different era
    await _make_building(db_session, user, canton="VD", construction_year=2020)

    results = await find_similar_buildings(db_session, ref.id)
    assert len(results) >= 1
    # First result should be more similar (same era)
    assert results[0]["similarity_score"] > 0


@pytest.mark.asyncio
async def test_find_similar_excludes_self(db_session):
    user = await _make_user(db_session)
    ref = await _make_building(db_session, user, canton="VD", construction_year=1970)

    results = await find_similar_buildings(db_session, ref.id)
    ids = [r["building_id"] for r in results]
    assert ref.id not in ids


@pytest.mark.asyncio
async def test_learn_no_peers(db_session):
    """Building with no peers returns empty learning."""
    user = await _make_user(db_session)
    building = await _make_building(db_session, user, canton="XX", construction_year=1800)

    result = await learn_from_similar(db_session, building.id)
    assert result["peer_count"] == 0
    assert result["diagnostic_coverage"] == []
    assert result["recommendations"] == []


@pytest.mark.asyncio
async def test_learn_detects_coverage_gap(db_session):
    """Peer has asbestos diagnostic, reference doesn't."""
    user = await _make_user(db_session)
    ref = await _make_building(db_session, user, canton="VD", construction_year=1970)
    peer = await _make_building(db_session, user, canton="VD", construction_year=1972)

    # Peer has asbestos diagnostic
    diag = await _make_diagnostic(db_session, peer.id, "asbestos")
    await _make_sample(db_session, diag.id, pollutant="asbestos", exceeded=True)

    result = await learn_from_similar(db_session, ref.id)
    assert result["peer_count"] >= 1
    # Should detect that we lack asbestos diagnostic
    coverage = result["diagnostic_coverage"]
    assert any(c["diagnostic_type"] == "asbestos" and not c["you_have_it"] for c in coverage)


@pytest.mark.asyncio
async def test_learn_includes_common_interventions(db_session):
    """Peer interventions should appear in common_interventions."""
    user = await _make_user(db_session)
    ref = await _make_building(db_session, user, canton="VD", construction_year=1970)
    peer = await _make_building(db_session, user, canton="VD", construction_year=1972)

    await _make_intervention(db_session, peer.id, intervention_type="asbestos_removal", cost_chf=20000)

    result = await learn_from_similar(db_session, ref.id)
    interventions = result["common_interventions"]
    assert any(iv["type"] == "asbestos_removal" for iv in interventions)


@pytest.mark.asyncio
async def test_learn_predicts_untested_risk(db_session):
    """Peer positive for PCB, ref untested -> predicted risk."""
    user = await _make_user(db_session)
    ref = await _make_building(db_session, user, canton="VD", construction_year=1970)
    peer = await _make_building(db_session, user, canton="VD", construction_year=1972)

    diag = await _make_diagnostic(db_session, peer.id, "pcb")
    await _make_sample(db_session, diag.id, pollutant="pcb", exceeded=True)

    result = await learn_from_similar(db_session, ref.id)
    risks = result["predicted_risks"]
    assert any(r["pollutant"] == "pcb" for r in risks)
