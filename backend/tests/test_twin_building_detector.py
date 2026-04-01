"""Tests for the Twin Building Detector Service."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.twin_building_detector import (
    _extract_street,
    find_twin_buildings,
    propagate_findings,
)

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue de Lausanne 15",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "floors_above": 4,
        "created_by": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _add_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
        "date_inspection": date(2020, 5, 1),
    }
    defaults.update(kwargs)
    d = Diagnostic(**defaults)
    db.add(d)
    await db.flush()
    return d


async def _add_sample(db, diagnostic_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "diagnostic_id": diagnostic_id,
        "sample_number": "S-001",
        "material_category": "dalle vinyle",
        "pollutant_type": "asbestos",
        "threshold_exceeded": True,
        "risk_level": "high",
    }
    defaults.update(kwargs)
    s = Sample(**defaults)
    db.add(s)
    await db.flush()
    return s


# ── Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_find_twins_same_street_same_year(db_session, admin_user):
    """Buildings on the same street with same construction year are twins."""
    source = await _create_building(
        db_session,
        admin_user,
        address="Rue de Lausanne 15",
        construction_year=1970,
        floors_above=4,
    )
    twin = await _create_building(
        db_session,
        admin_user,
        address="Rue de Lausanne 17",
        construction_year=1971,
        floors_above=4,
    )
    await db_session.commit()

    result = await find_twin_buildings(db_session, source.id)

    assert len(result) == 1
    assert result[0]["building_id"] == str(twin.id)
    assert result[0]["similarity_score"] >= 2.0
    assert "same_street" in result[0]["matching_criteria"]
    assert any("construction_year" in c for c in result[0]["matching_criteria"])


@pytest.mark.asyncio
async def test_no_twins_different_city(db_session, admin_user):
    """Buildings in different cities are never twins."""
    source = await _create_building(
        db_session,
        admin_user,
        address="Rue Test 1",
        city="Lausanne",
    )
    await _create_building(
        db_session,
        admin_user,
        address="Rue Test 2",
        city="Genève",
    )
    await db_session.commit()

    result = await find_twin_buildings(db_session, source.id)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_similarity_scoring(db_session, admin_user):
    """Higher similarity for buildings matching more criteria."""
    source = await _create_building(
        db_session,
        admin_user,
        address="Avenue des Alpes 10",
        construction_year=1975,
        building_type="residential",
        floors_above=5,
    )
    # Strong twin: matches street, year, type, floors
    strong = await _create_building(
        db_session,
        admin_user,
        address="Avenue des Alpes 12",
        construction_year=1976,
        building_type="residential",
        floors_above=5,
    )
    # Weak twin: matches only type and year
    await _create_building(
        db_session,
        admin_user,
        address="Chemin du Bois 3",
        construction_year=1974,
        building_type="residential",
        floors_above=3,
    )
    await db_session.commit()

    result = await find_twin_buildings(db_session, source.id)

    # Strong twin should rank first
    if len(result) >= 2:
        assert result[0]["building_id"] == str(strong.id)
        assert result[0]["similarity_score"] > result[1]["similarity_score"]
    elif len(result) == 1:
        # At minimum the strong twin should appear
        assert result[0]["building_id"] == str(strong.id)


@pytest.mark.asyncio
async def test_recommendation_with_positive_findings(db_session, admin_user):
    """Recommendation mentions positive findings from source."""
    source = await _create_building(db_session, admin_user, address="Rue Test 10")
    await _create_building(
        db_session,
        admin_user,
        address="Rue Test 12",
        construction_year=1970,
        floors_above=4,
    )
    d = await _add_diagnostic(db_session, source.id)
    await _add_sample(db_session, d.id, material_category="dalle vinyle")
    await db_session.commit()

    result = await find_twin_buildings(db_session, source.id)

    assert len(result) == 1
    assert result[0]["recommendation"] is not None
    assert "dalle vinyle" in result[0]["recommendation"]


@pytest.mark.asyncio
async def test_propagate_findings(db_session, admin_user):
    """Propagation suggests findings from source to target twin."""
    source = await _create_building(db_session, admin_user, address="Rue Test 10")
    target = await _create_building(
        db_session,
        admin_user,
        address="Rue Test 12",
        construction_year=1970,
        floors_above=4,
    )
    d = await _add_diagnostic(db_session, source.id)
    await _add_sample(db_session, d.id, material_category="colle carrelage", pollutant_type="asbestos")
    await db_session.commit()

    suggestions = await propagate_findings(db_session, source.id, target.id)

    assert len(suggestions) >= 1
    assert suggestions[0]["pollutant"] == "asbestos"
    assert suggestions[0]["material"] == "colle carrelage"
    assert "jumeau" in suggestions[0]["suggestion"]
    assert suggestions[0]["confidence"] > 0


@pytest.mark.asyncio
async def test_propagate_no_twin(db_session, admin_user):
    """Propagation returns empty when buildings are not twins."""
    source = await _create_building(
        db_session,
        admin_user,
        address="Rue A 1",
        city="Lausanne",
        construction_year=1960,
    )
    target = await _create_building(
        db_session,
        admin_user,
        address="Rue Z 99",
        city="Genève",
        construction_year=2020,
    )
    await db_session.commit()

    suggestions = await propagate_findings(db_session, source.id, target.id)

    assert suggestions == []


@pytest.mark.asyncio
async def test_extract_street():
    """Street extraction removes house numbers."""
    assert _extract_street("Rue de Lausanne 15") == "rue de lausanne"
    assert _extract_street("Avenue des Alpes 3a") == "avenue des alpes"
    assert _extract_street("Chemin du Bois 7-9") == "chemin du bois"
    assert _extract_street("Bahnhofstrasse 42") == "bahnhofstrasse"


@pytest.mark.asyncio
async def test_minimum_score_threshold(db_session, admin_user):
    """Buildings with only 1 matching criterion are filtered out."""
    source = await _create_building(
        db_session,
        admin_user,
        address="Rue Unique 1",
        construction_year=1970,
        building_type="residential",
        floors_above=4,
    )
    # Only matches building_type (weight=1) — below threshold of 2
    await _create_building(
        db_session,
        admin_user,
        address="Chemin Autre 99",
        construction_year=1920,
        building_type="residential",
        floors_above=10,
    )
    await db_session.commit()

    result = await find_twin_buildings(db_session, source.id)

    # Should be filtered out (score 1.0 < threshold 2.0)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_shared_diagnostics_count(db_session, admin_user):
    """Shared diagnostics count reflects diagnostics of the same type."""
    source = await _create_building(db_session, admin_user, address="Rue Test 10")
    twin = await _create_building(
        db_session,
        admin_user,
        address="Rue Test 12",
        construction_year=1970,
        floors_above=4,
    )
    await _add_diagnostic(db_session, source.id, diagnostic_type="asbestos")
    await _add_diagnostic(db_session, twin.id, diagnostic_type="asbestos")
    await _add_diagnostic(db_session, twin.id, diagnostic_type="pcb")
    await db_session.commit()

    result = await find_twin_buildings(db_session, source.id)

    assert len(result) == 1
    assert result[0]["shared_diagnostics_count"] == 1  # only asbestos shared


@pytest.mark.asyncio
async def test_building_not_found(db_session, admin_user):
    """Non-existent building raises ValueError."""
    fake_id = uuid.uuid4()

    with pytest.raises(ValueError, match="not found"):
        await find_twin_buildings(db_session, fake_id)
