"""Tests for the Building Biography Service."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.models.building import Building
from app.models.building_genealogy import OwnershipEpisode, TransformationEpisode
from app.models.diagnostic import Diagnostic
from app.models.intervention import Intervention
from app.models.sample import Sample
from app.services.building_biography_service import generate_biography

# ── Helpers ────────────────────────────────────────────────────────


async def _create_building(db, admin_user, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "address": "Rue de Lausanne 15",
        "postal_code": "1000",
        "city": "Lausanne",
        "canton": "VD",
        "construction_year": 1965,
        "building_type": "residential",
        "floors_above": 4,
        "floors_below": 1,
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
        "title": "Rénovation toiture",
        "evidence_basis": "documented",
        "period_start": date(2005, 6, 1),
    }
    defaults.update(kwargs)
    t = TransformationEpisode(**defaults)
    db.add(t)
    await db.flush()
    return t


async def _add_ownership(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "owner_name": "Famille Dupont",
        "owner_type": "individual",
        "period_start": date(1965, 1, 1),
        "evidence_basis": "registry",
        "acquisition_type": "purchase",
    }
    defaults.update(kwargs)
    o = OwnershipEpisode(**defaults)
    db.add(o)
    await db.flush()
    return o


async def _add_diagnostic(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "diagnostic_type": "asbestos",
        "status": "completed",
        "date_inspection": date(2015, 3, 10),
        "conclusion": "positive",
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
        "material_category": "colle carrelage",
        "pollutant_type": "asbestos",
        "threshold_exceeded": True,
        "risk_level": "high",
    }
    defaults.update(kwargs)
    s = Sample(**defaults)
    db.add(s)
    await db.flush()
    return s


async def _add_intervention(db, building_id, **kwargs):
    defaults = {
        "id": uuid.uuid4(),
        "building_id": building_id,
        "intervention_type": "remediation",
        "title": "Assainissement amiante partiel",
        "status": "completed",
        "date_start": date(2020, 9, 1),
    }
    defaults.update(kwargs)
    i = Intervention(**defaults)
    db.add(i)
    await db.flush()
    return i


# ── Tests ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_biography(db_session, admin_user):
    """Full biography includes all sections with correct structure."""
    b = await _create_building(db_session, admin_user)
    await _add_transformation(db_session, b.id)
    await _add_ownership(db_session, b.id)
    d = await _add_diagnostic(db_session, b.id)
    await _add_sample(db_session, d.id)
    await _add_intervention(db_session, b.id)
    await db_session.commit()

    bio = await generate_biography(db_session, b.id)

    assert bio["building_id"] == str(b.id)
    assert bio["identity"]["construction_year"] == 1965
    assert bio["identity"]["address"] == "Rue de Lausanne 15"
    assert len(bio["chapters"]) >= 4  # construction + transformation + diagnostic + intervention
    assert len(bio["ownership_chain"]) == 1
    assert "component_ages" in bio
    assert "narrative" in bio
    assert bio["key_events_count"]["transformations"] == 1
    assert bio["key_events_count"]["diagnostics"] == 1
    assert bio["key_events_count"]["interventions"] == 1


@pytest.mark.asyncio
async def test_empty_building(db_session, admin_user):
    """Building with no history still produces a valid biography."""
    b = await _create_building(db_session, admin_user, construction_year=None)
    await db_session.commit()

    bio = await generate_biography(db_session, b.id)

    assert bio["building_id"] == str(b.id)
    assert bio["identity"]["construction_year"] is None
    assert len(bio["chapters"]) == 0  # no construction chapter without year
    assert len(bio["ownership_chain"]) == 0
    assert bio["key_events_count"]["transformations"] == 0


@pytest.mark.asyncio
async def test_narrative_contains_construction_year(db_session, admin_user):
    """Narrative mentions the construction year."""
    b = await _create_building(db_session, admin_user, construction_year=1972)
    await db_session.commit()

    bio = await generate_biography(db_session, b.id)

    assert "1972" in bio["narrative"]
    assert "résidentiel" in bio["narrative"]


@pytest.mark.asyncio
async def test_narrative_unknown_year(db_session, admin_user):
    """Narrative handles unknown construction year gracefully."""
    b = await _create_building(db_session, admin_user, construction_year=None)
    await db_session.commit()

    bio = await generate_biography(db_session, b.id)

    assert "inconnue" in bio["narrative"]


@pytest.mark.asyncio
async def test_component_ages_in_biography(db_session, admin_user):
    """Biography includes component ages with expected structure."""
    b = await _create_building(db_session, admin_user, construction_year=1965)
    await db_session.commit()

    bio = await generate_biography(db_session, b.id)

    ages = bio["component_ages"]
    assert "structure" in ages
    assert "roof" in ages
    assert ages["structure"]["is_original"] is True
    assert ages["structure"]["year"] == 1965


@pytest.mark.asyncio
async def test_component_ages_override_by_transformation(db_session, admin_user):
    """Transformation episode overrides component age."""
    b = await _create_building(db_session, admin_user, construction_year=1965)
    await _add_transformation(
        db_session,
        b.id,
        episode_type="renovation",
        title="Rénovation toiture complète",
        period_start=date(2005, 6, 1),
    )
    await db_session.commit()

    bio = await generate_biography(db_session, b.id)

    assert bio["component_ages"]["roof"]["year"] == 2005
    assert bio["component_ages"]["roof"]["is_original"] is False
    assert bio["component_ages"]["structure"]["year"] == 1965
    assert bio["component_ages"]["structure"]["is_original"] is True


@pytest.mark.asyncio
async def test_ownership_chain_order(db_session, admin_user):
    """Ownership chain is ordered chronologically."""
    b = await _create_building(db_session, admin_user)
    await _add_ownership(
        db_session,
        b.id,
        owner_name="Premier Propriétaire",
        period_start=date(1965, 1, 1),
        period_end=date(1990, 12, 31),
    )
    await _add_ownership(
        db_session,
        b.id,
        owner_name="Second Propriétaire",
        period_start=date(1991, 1, 1),
    )
    await db_session.commit()

    bio = await generate_biography(db_session, b.id)

    assert len(bio["ownership_chain"]) == 2
    assert bio["ownership_chain"][0]["owner"] == "Premier Propriétaire"
    assert bio["ownership_chain"][1]["owner"] == "Second Propriétaire"


@pytest.mark.asyncio
async def test_chapters_chronological_order(db_session, admin_user):
    """Chapters are sorted chronologically by year."""
    b = await _create_building(db_session, admin_user, construction_year=1965)
    await _add_diagnostic(db_session, b.id, date_inspection=date(2015, 3, 10))
    await _add_transformation(
        db_session,
        b.id,
        title="Extension étage",
        period_start=date(1992, 4, 1),
    )
    await _add_intervention(db_session, b.id, date_start=date(2020, 9, 1))
    await db_session.commit()

    bio = await generate_biography(db_session, b.id)

    years = [c["year"] for c in bio["chapters"] if c["year"] is not None]
    assert years == sorted(years)
    assert years[0] == 1965  # construction first


@pytest.mark.asyncio
async def test_diagnostic_with_positive_samples(db_session, admin_user):
    """Diagnostic chapter mentions positive materials."""
    b = await _create_building(db_session, admin_user)
    d = await _add_diagnostic(db_session, b.id)
    await _add_sample(db_session, d.id, material_category="colle carrelage")
    await db_session.commit()

    bio = await generate_biography(db_session, b.id)

    diag_chapters = [c for c in bio["chapters"] if c["type"] == "diagnostic"]
    assert len(diag_chapters) == 1
    assert "colle carrelage" in diag_chapters[0]["description"]


@pytest.mark.asyncio
async def test_building_not_found(db_session, admin_user):
    """Requesting biography for non-existent building raises ValueError."""
    fake_id = uuid.uuid4()

    with pytest.raises(ValueError, match="not found"):
        await generate_biography(db_session, fake_id)
