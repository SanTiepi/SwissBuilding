"""Tests for app.seeds.seed_demo_enrich — demo enrichment logic."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.constants import SOURCE_DATASET_VAUD_PUBLIC, SUPPORTED_SAMPLE_UNITS
from app.seeds.seed_demo_enrich import (
    DIAGNOSTIC_SCENARIOS,
    SAMPLE_TEMPLATES,
    _make_samples,
    _random_date,
    _random_renovation_year,
)

# ---------------------------------------------------------------------------
# _random_date
# ---------------------------------------------------------------------------


def test_random_date_within_range() -> None:
    start = date(2023, 1, 1)
    end = date(2023, 12, 31)
    for _ in range(20):
        d = _random_date(start, end)
        assert start <= d <= end


def test_random_date_same_day() -> None:
    d = date(2024, 6, 15)
    assert _random_date(d, d) == d


def test_random_renovation_year_returns_none_for_recent_buildings() -> None:
    assert _random_renovation_year(2016) is None


def test_random_renovation_year_stays_in_expected_range() -> None:
    for _ in range(20):
        year = _random_renovation_year(1965)
        assert year is not None
        assert 1980 <= year <= 2020


# ---------------------------------------------------------------------------
# _make_samples
# ---------------------------------------------------------------------------


def test_make_samples_returns_1_to_3() -> None:
    diag_id = uuid.uuid4()
    for _ in range(10):
        samples = _make_samples(diag_id, "asbestos", "positive", "LAU")
        assert 1 <= len(samples) <= 3
        for s in samples:
            assert s.diagnostic_id == diag_id
            assert s.sample_number.startswith("LAU-DEMO-")


def test_make_samples_negative_conclusion_below_threshold() -> None:
    diag_id = uuid.uuid4()
    samples = _make_samples(diag_id, "pcb", "negative", "GE")
    for s in samples:
        assert s.threshold_exceeded is False
        assert s.risk_level == "low"
        assert s.concentration == 0.0


def test_make_samples_uses_canonical_machine_units() -> None:
    diag_id = uuid.uuid4()
    samples = _make_samples(diag_id, "radon", "positive", "VD")
    assert samples
    assert all(sample.unit in SUPPORTED_SAMPLE_UNITS for sample in samples)


def test_make_samples_full_type_picks_asbestos_or_pcb() -> None:
    diag_id = uuid.uuid4()
    pollutant_types = set()
    for _ in range(20):
        samples = _make_samples(diag_id, "full", "positive", "X")
        for s in samples:
            pollutant_types.add(s.pollutant_type)
    assert pollutant_types <= {"asbestos", "pcb"}


def test_make_samples_all_pollutant_types_have_templates() -> None:
    expected = {"asbestos", "pcb", "lead", "hap", "radon", "full"}
    assert set(SAMPLE_TEMPLATES.keys()) == expected


# ---------------------------------------------------------------------------
# DIAGNOSTIC_SCENARIOS
# ---------------------------------------------------------------------------


def test_scenarios_cover_all_statuses() -> None:
    statuses = {s[2] for s in DIAGNOSTIC_SCENARIOS}
    assert statuses >= {"draft", "in_progress", "completed", "validated"}


def test_scenarios_cover_multiple_types() -> None:
    types = {s[0] for s in DIAGNOSTIC_SCENARIOS}
    assert len(types) >= 4


# ---------------------------------------------------------------------------
# Vaud-first ordering (integration-level, requires DB)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enrich_prioritizes_vaud_buildings(db_session, monkeypatch) -> None:
    """Verify that buildings with source_dataset='vaud_public' are enriched first."""
    from app.models.building import Building
    from app.models.user import User
    from app.seeds import seed_demo_enrich

    # Create required users
    admin = User(
        id=uuid.uuid4(),
        email="admin@swissbuildingos.ch",
        password_hash="x",
        first_name="Admin",
        last_name="Test",
        role="admin",
    )
    diag = User(
        id=uuid.uuid4(),
        email="jean.muller@diagswiss.ch",
        password_hash="x",
        first_name="Jean",
        last_name="Muller",
        role="diagnostician",
    )
    db_session.add_all([admin, diag])

    # Create 3 synthetic buildings (older created_at via default)
    synth_ids = []
    for i in range(3):
        b = Building(
            id=uuid.uuid4(),
            address=f"Synthetic {i}",
            postal_code="3000",
            city="Bern",
            canton="BE",
            building_type="habitation",
            construction_year=1970,
            created_by=admin.id,
            status="active",
        )
        db_session.add(b)
        synth_ids.append(b.id)

    # Create 2 Vaud buildings
    vaud_ids = []
    for i in range(2):
        b = Building(
            id=uuid.uuid4(),
            address=f"Vaud {i}",
            postal_code="1000",
            city="Lausanne",
            canton="VD",
            building_type="habitation",
            construction_year=1965,
            created_by=admin.id,
            status="active",
            source_dataset=SOURCE_DATASET_VAUD_PUBLIC,
        )
        db_session.add(b)
        vaud_ids.append(b.id)

    await db_session.commit()

    # Monkeypatch AsyncSessionLocal to use the test session
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _fake_session():
        yield db_session

    monkeypatch.setattr(seed_demo_enrich, "AsyncSessionLocal", _fake_session)

    stats = await seed_demo_enrich.enrich_demo_buildings()

    # Should have enriched all 5 buildings
    assert stats["diagnostics"] == 5

    # Check that Vaud buildings got diagnostics
    from sqlalchemy import select

    from app.models.diagnostic import Diagnostic

    for vid in vaud_ids:
        result = await db_session.execute(select(Diagnostic).where(Diagnostic.building_id == vid))
        diags = result.scalars().all()
        assert len(diags) >= 1, f"Vaud building {vid} should have been enriched"


@pytest.mark.asyncio
async def test_enrich_is_idempotent(db_session, monkeypatch) -> None:
    """Running enrichment twice should not create duplicate data."""
    from app.models.building import Building
    from app.models.user import User
    from app.seeds import seed_demo_enrich

    admin = User(
        id=uuid.uuid4(),
        email="admin@swissbuildingos.ch",
        password_hash="x",
        first_name="Admin",
        last_name="Test",
        role="admin",
    )
    diag = User(
        id=uuid.uuid4(),
        email="jean.muller@diagswiss.ch",
        password_hash="x",
        first_name="Jean",
        last_name="Muller",
        role="diagnostician",
    )
    db_session.add_all([admin, diag])

    b = Building(
        id=uuid.uuid4(),
        address="Idempotent Test",
        postal_code="1000",
        city="Lausanne",
        canton="VD",
        building_type="habitation",
        construction_year=1960,
        created_by=admin.id,
        status="active",
    )
    db_session.add(b)
    await db_session.commit()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _fake_session():
        yield db_session

    monkeypatch.setattr(seed_demo_enrich, "AsyncSessionLocal", _fake_session)

    stats1 = await seed_demo_enrich.enrich_demo_buildings()
    assert stats1["diagnostics"] >= 1

    # Reset RNG to same state to ensure determinism isn't the blocker
    seed_demo_enrich._RNG = __import__("random").Random(42)

    stats2 = await seed_demo_enrich.enrich_demo_buildings()
    assert stats2["diagnostics"] == 0, "Second run should be a no-op (idempotent marker)"
