"""Tests for the Component Age Tracker Service."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.building_genealogy import TransformationEpisode
from app.models.intervention import Intervention
from app.services.component_age_tracker import (
    COMPONENT_TYPES,
    EXPECTED_LIFESPANS,
    compute_component_ages,
    compute_overall_building_age,
)

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue Test 1",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1970,
        "building_type": "residential",
        "created_by": admin_user.id,
        "status": "active",
    }
    defaults.update(kwargs)
    b = Building(**defaults)
    db.add(b)
    await db.flush()
    return b


async def _add_transformation(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "episode_type": "renovation",
        "title": "Rénovation",
        "evidence_basis": "documented",
    }
    defaults.update(kwargs)
    t = TransformationEpisode(**defaults)
    db.add(t)
    await db.flush()
    return t


async def _add_intervention(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "intervention_type": "renovation",
        "title": "Intervention",
        "status": "completed",
    }
    defaults.update(kwargs)
    i = Intervention(**defaults)
    db.add(i)
    await db.flush()
    return i


# ── Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_all_components_at_construction_year(db_session, admin_user):
    """Without any interventions, all components date to construction year."""
    b = await _create_building(db_session, admin_user, construction_year=1970)
    await db_session.commit()

    ages = await compute_component_ages(db_session, b.id)

    for comp in COMPONENT_TYPES:
        assert ages[comp]["year"] == 1970
        assert ages[comp]["is_original"] is True
        assert ages[comp]["source"] == "construction"


@pytest.mark.asyncio
async def test_component_override_by_transformation(db_session, admin_user):
    """Transformation episode overrides component year."""
    b = await _create_building(db_session, admin_user, construction_year=1970)
    await _add_transformation(
        db_session,
        b.id,
        title="Rénovation toiture complète",
        period_start=date(2005, 6, 1),
    )
    await db_session.commit()

    ages = await compute_component_ages(db_session, b.id)

    assert ages["roof"]["year"] == 2005
    assert ages["roof"]["is_original"] is False
    assert ages["roof"]["source"] == "transformation"
    # Other components remain original
    assert ages["structure"]["year"] == 1970
    assert ages["structure"]["is_original"] is True


@pytest.mark.asyncio
async def test_component_override_by_intervention(db_session, admin_user):
    """Intervention overrides component year."""
    b = await _create_building(db_session, admin_user, construction_year=1970)
    await _add_intervention(
        db_session,
        b.id,
        title="Remplacement fenêtres double vitrage",
        date_start=date(2015, 3, 1),
    )
    await db_session.commit()

    ages = await compute_component_ages(db_session, b.id)

    assert ages["windows"]["year"] == 2015
    assert ages["windows"]["is_original"] is False
    assert ages["windows"]["source"] == "intervention"


@pytest.mark.asyncio
async def test_intervention_takes_latest_year(db_session, admin_user):
    """When multiple interventions affect same component, latest wins."""
    b = await _create_building(db_session, admin_user, construction_year=1970)
    await _add_transformation(
        db_session,
        b.id,
        title="Remplacement chauffage",
        period_start=date(1995, 1, 1),
    )
    await _add_intervention(
        db_session,
        b.id,
        title="Nouveau système chauffage",
        date_start=date(2018, 11, 1),
    )
    await db_session.commit()

    ages = await compute_component_ages(db_session, b.id)

    assert ages["heating"]["year"] == 2018
    assert ages["heating"]["is_original"] is False


@pytest.mark.asyncio
async def test_remaining_life_and_urgency(db_session, admin_user):
    """Remaining life and urgency are correctly computed."""
    b = await _create_building(db_session, admin_user, construction_year=1970)
    await db_session.commit()

    ages = await compute_component_ages(db_session, b.id)

    today_year = date.today().year
    # Structure: lifespan 100, age = today - 1970
    structure_age = today_year - 1970
    expected_remaining = EXPECTED_LIFESPANS["structure"] - structure_age
    assert ages["structure"]["remaining_life"] == expected_remaining
    assert ages["structure"]["expected_lifespan"] == 100

    # Heating: lifespan 25, age = 56 → remaining = -31 → critical
    assert ages["heating"]["urgency"] == "critical"


@pytest.mark.asyncio
async def test_original_components_flagged(db_session, admin_user):
    """Components with no renovation are flagged as original."""
    b = await _create_building(db_session, admin_user, construction_year=1970)
    await _add_intervention(
        db_session,
        b.id,
        title="Rénovation façade",
        date_start=date(2010, 5, 1),
    )
    await db_session.commit()

    ages = await compute_component_ages(db_session, b.id)

    # Facade was renovated
    assert ages["facade"]["is_original"] is False
    # Everything else is original
    for comp in COMPONENT_TYPES:
        if comp != "facade":
            assert ages[comp]["is_original"] is True, f"{comp} should be original"


@pytest.mark.asyncio
async def test_biological_age_younger_after_renovations(db_session, admin_user):
    """Building with many renovations has lower biological age than chronological."""
    b = await _create_building(db_session, admin_user, construction_year=1970)
    # Renovate heavy-weight components
    await _add_intervention(db_session, b.id, title="Rénovation toiture", date_start=date(2020, 1, 1))
    await _add_intervention(db_session, b.id, title="Rénovation façade", date_start=date(2018, 1, 1))
    await _add_intervention(db_session, b.id, title="Remplacement fenêtres", date_start=date(2015, 1, 1))
    await _add_intervention(db_session, b.id, title="Nouveau chauffage", date_start=date(2019, 1, 1))
    await _add_intervention(db_session, b.id, title="Installation électrique neuve", date_start=date(2017, 1, 1))
    await db_session.commit()

    result = await compute_overall_building_age(db_session, b.id)

    today_year = date.today().year
    assert result["chronological_age"] == today_year - 1970
    assert result["biological_age"] < result["chronological_age"]
    assert result["delta"] < 0  # younger than chronological
    assert result["verdict"] in ("well_maintained", "showing_age")


@pytest.mark.asyncio
async def test_biological_age_no_renovations(db_session, admin_user):
    """Building with no renovations: biological age equals chronological age."""
    b = await _create_building(db_session, admin_user, construction_year=1970)
    await db_session.commit()

    result = await compute_overall_building_age(db_session, b.id)

    today_year = date.today().year
    assert result["chronological_age"] == today_year - 1970
    assert result["biological_age"] == float(today_year - 1970)
    assert result["delta"] == 0.0


@pytest.mark.asyncio
async def test_biological_age_unknown_construction_year(db_session, admin_user):
    """Building without construction year returns unknown verdict."""
    b = await _create_building(db_session, admin_user, construction_year=None)
    await db_session.commit()

    result = await compute_overall_building_age(db_session, b.id)

    assert result["chronological_age"] is None
    assert result["biological_age"] is None
    assert result["verdict"] == "unknown"


@pytest.mark.asyncio
async def test_building_not_found(db_session, admin_user):
    """Non-existent building raises ValueError."""
    fake_id = uuid.uuid4()

    with pytest.raises(ValueError, match="not found"):
        await compute_component_ages(db_session, fake_id)

    with pytest.raises(ValueError, match="not found"):
        await compute_overall_building_age(db_session, fake_id)
