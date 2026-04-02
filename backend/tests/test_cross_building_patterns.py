"""
Tests for cross-building correlation engine: similarity and pollutant prevalence.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.diagnostic import Diagnostic
from app.models.sample import Sample
from app.services.building_similarity_service import BuildingSimilarityService
from app.services.pollutant_prevalence_service import PollutantPrevalenceService


@pytest.fixture
async def reference_building(db: AsyncSession):
    """Create a reference building."""
    building = Building(
        id=uuid.uuid4(),
        egrid="CH001000000000",
        egid=1000,
        address="123 Rue de Test, Lausanne",
        postal_code="1200",
        city="Lausanne",
        canton="VD",
        building_type="apartment",
        construction_year=1970,
        status="active",
        created_by=uuid.uuid4(),
    )
    db.add(building)
    await db.flush()
    return building


@pytest.fixture
async def similar_buildings(db: AsyncSession, reference_building: Building):
    """Create similar buildings (same type, age ±5 years, same canton)."""
    buildings = []
    for i in range(3):
        year = 1970 + i - 1  # 1969, 1970, 1971
        building = Building(
            id=uuid.uuid4(),
            egrid=f"CH001000000{1000 + i:03d}",
            egid=1000 + i,
            address=f"{100 + i} Rue Similaire, Lausanne",
            postal_code="1200",
            city="Lausanne",
            canton="VD",
            building_type="apartment",
            construction_year=year,
            status="active",
            created_by=uuid.uuid4(),
        )
        db.add(building)
        buildings.append(building)

    await db.flush()
    return buildings


@pytest.fixture
async def diagnostics_with_samples(db: AsyncSession, similar_buildings: list[Building]):
    """Create diagnostics with samples for similar buildings."""
    diagnostics = []

    # Building 1: has amiante
    diag1 = Diagnostic(
        id=uuid.uuid4(),
        building_id=similar_buildings[0].id,
        diagnostic_type="amiante",
        status="completed",
        date_inspection=date(2020, 1, 1),
        date_report=date(2020, 1, 15),
        created_by=uuid.uuid4(),
    )
    db.add(diag1)
    await db.flush()

    sample1 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag1.id,
        sample_number="S001",
        location_floor="RDC",
        pollutant_type="amiante",
        threshold_exceeded=True,
        risk_level="high",
    )
    db.add(sample1)
    diagnostics.append(diag1)

    # Building 2: has amiante and pcb
    diag2 = Diagnostic(
        id=uuid.uuid4(),
        building_id=similar_buildings[1].id,
        diagnostic_type="amiante",
        status="completed",
        date_inspection=date(2021, 1, 1),
        date_report=date(2021, 1, 15),
        created_by=uuid.uuid4(),
    )
    db.add(diag2)
    await db.flush()

    sample2a = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag2.id,
        sample_number="S002",
        location_floor="1er",
        pollutant_type="amiante",
        threshold_exceeded=True,
        risk_level="high",
    )
    db.add(sample2a)

    sample2b = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag2.id,
        sample_number="S003",
        location_floor="2e",
        pollutant_type="pcb",
        threshold_exceeded=True,
        risk_level="high",
    )
    db.add(sample2b)
    diagnostics.append(diag2)

    # Building 3: amiante negative
    diag3 = Diagnostic(
        id=uuid.uuid4(),
        building_id=similar_buildings[2].id,
        diagnostic_type="amiante",
        status="completed",
        date_inspection=date(2022, 1, 1),
        date_report=date(2022, 1, 15),
        created_by=uuid.uuid4(),
    )
    db.add(diag3)
    await db.flush()

    sample3 = Sample(
        id=uuid.uuid4(),
        diagnostic_id=diag3.id,
        sample_number="S004",
        location_floor="RDC",
        pollutant_type="amiante",
        threshold_exceeded=False,
        risk_level="low",
    )
    db.add(sample3)
    diagnostics.append(diag3)

    await db.commit()
    return diagnostics


@pytest.mark.asyncio
async def test_find_similar_buildings_basic(
    db: AsyncSession,
    reference_building: Building,
    similar_buildings: list[Building],
):
    """Test finding similar buildings by type, age, and canton."""
    # Add diagnostics to similar buildings so they're included
    for building in similar_buildings:
        diag = Diagnostic(
            id=uuid.uuid4(),
            building_id=building.id,
            diagnostic_type="amiante",
            status="completed",
            created_by=uuid.uuid4(),
        )
        db.add(diag)

    await db.commit()

    result = await BuildingSimilarityService.find_similar_buildings(
        db,
        reference_building.id,
        max_results=50,
    )

    assert len(result) == 3
    assert all(b.building_type == "apartment" for b in result)
    assert all(b.canton == "VD" for b in result)


@pytest.mark.asyncio
async def test_find_similar_buildings_filters_without_diagnostics(
    db: AsyncSession,
    reference_building: Building,
):
    """Test that buildings without diagnostics are excluded."""
    # Create a similar building but WITHOUT diagnostic
    building_no_diag = Building(
        id=uuid.uuid4(),
        egrid="CH999000000999",
        egid=9999,
        address="999 No Diagnostic",
        postal_code="1200",
        city="Lausanne",
        canton="VD",
        building_type="apartment",
        construction_year=1970,
        status="active",
        created_by=uuid.uuid4(),
    )
    db.add(building_no_diag)

    # Add a diagnostic to reference building
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=reference_building.id,
        diagnostic_type="amiante",
        status="completed",
        created_by=uuid.uuid4(),
    )
    db.add(diag)

    await db.commit()

    result = await BuildingSimilarityService.find_similar_buildings(db, reference_building.id)

    # Should be empty since building_no_diag has no diagnostic
    assert len(result) == 0


@pytest.mark.asyncio
async def test_similarity_score_calculation(
    db: AsyncSession,
    reference_building: Building,
    similar_buildings: list[Building],
):
    """Test similarity score calculation between two buildings."""
    # Both same type and canton, 1 year apart
    b1 = reference_building
    b2 = similar_buildings[0]  # 1969, 1 year difference

    score = await BuildingSimilarityService.similarity_score(db, b1.id, b2.id)

    # Should be > 0.6: type (0.3) + canton (0.2) + age proximity (0.25+)
    assert score > 0.6
    assert score <= 1.0


@pytest.mark.asyncio
async def test_analyze_pollutant_patterns(
    db: AsyncSession,
    similar_buildings: list[Building],
    diagnostics_with_samples: list[Diagnostic],
):
    """Test pollutant pattern analysis across similar buildings."""
    findings = await PollutantPrevalenceService.analyze_pollutant_patterns(db, similar_buildings)

    assert "amiante" in findings
    assert findings["amiante"]["confirmed"] == 2
    assert findings["amiante"]["negative"] == 1
    assert findings["amiante"]["total_checked"] == 3

    assert "pcb" in findings
    assert findings["pcb"]["confirmed"] == 1


@pytest.mark.asyncio
async def test_get_building_pollutant_predictions(
    db: AsyncSession,
    reference_building: Building,
    similar_buildings: list[Building],
    diagnostics_with_samples: list[Diagnostic],
):
    """Test full pollutant prediction flow."""
    predictions = await PollutantPrevalenceService.get_building_pollutant_predictions(
        db, reference_building.id
    )

    assert predictions["building_id"] == str(reference_building.id)
    assert predictions["similar_buildings_count"] == 3
    assert len(predictions["pollutant_predictions"]) <= 5

    # Check structure
    for pred in predictions["pollutant_predictions"]:
        assert "pollutant" in pred
        assert "probability" in pred
        assert "probability_percent" in pred
        assert "count_confirmed" in pred
        assert "count_checked" in pred

    # Check ordering: highest probability first
    if len(predictions["pollutant_predictions"]) > 1:
        for i in range(len(predictions["pollutant_predictions"]) - 1):
            assert (
                predictions["pollutant_predictions"][i]["probability"]
                >= predictions["pollutant_predictions"][i + 1]["probability"]
            )


@pytest.mark.asyncio
async def test_get_building_pollutant_predictions_no_similar(
    db: AsyncSession,
    reference_building: Building,
):
    """Test predictions when no similar buildings found."""
    predictions = await PollutantPrevalenceService.get_building_pollutant_predictions(
        db, reference_building.id
    )

    assert predictions["building_id"] == str(reference_building.id)
    assert predictions["similar_buildings_count"] == 0
    assert predictions["pollutant_predictions"] == []
    assert "Insufficient" in predictions["notes"]


@pytest.mark.asyncio
async def test_probability_calculation(
    db: AsyncSession,
    reference_building: Building,
    similar_buildings: list[Building],
    diagnostics_with_samples: list[Diagnostic],
):
    """Test that probabilities are calculated correctly."""
    predictions = await PollutantPrevalenceService.get_building_pollutant_predictions(
        db, reference_building.id
    )

    # Find amiante prediction
    amiante_pred = next(
        (p for p in predictions["pollutant_predictions"] if p["pollutant"] == "amiante"),
        None,
    )

    assert amiante_pred is not None
    # 2 confirmed out of 3 = 66.7%
    assert abs(amiante_pred["probability"] - 0.667) < 0.01
    assert abs(amiante_pred["probability_percent"] - 66.7) < 1.0


@pytest.mark.asyncio
async def test_age_range_filtering(
    db: AsyncSession,
):
    """Test that age range filtering works (±5 years)."""
    ref_building = Building(
        id=uuid.uuid4(),
        egrid="CH010000000000",
        egid=10000,
        address="Age Test Building",
        postal_code="1200",
        city="Lausanne",
        canton="VD",
        building_type="apartment",
        construction_year=1970,
        status="active",
        created_by=uuid.uuid4(),
    )
    db.add(ref_building)

    # Add diagnostic
    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=ref_building.id,
        diagnostic_type="amiante",
        status="completed",
        created_by=uuid.uuid4(),
    )
    db.add(diag)

    # Create buildings within range (1965-1975) with diagnostics
    for year in [1965, 1970, 1975]:
        b = Building(
            id=uuid.uuid4(),
            egrid=f"CH010000{year:04d}00",
            egid=10000 + year - 1965,
            address=f"Building {year}",
            postal_code="1200",
            city="Lausanne",
            canton="VD",
            building_type="apartment",
            construction_year=year,
            status="active",
            created_by=uuid.uuid4(),
        )
        db.add(b)

        d = Diagnostic(
            id=uuid.uuid4(),
            building_id=b.id,
            diagnostic_type="amiante",
            status="completed",
            created_by=uuid.uuid4(),
        )
        db.add(d)

    # Create building outside range (1960) with diagnostic
    b_outside = Building(
        id=uuid.uuid4(),
        egrid="CH010000196000",
        egid=10100,
        address="Building 1960",
        postal_code="1200",
        city="Lausanne",
        canton="VD",
        building_type="apartment",
        construction_year=1960,
        status="active",
        created_by=uuid.uuid4(),
    )
    db.add(b_outside)

    d_outside = Diagnostic(
        id=uuid.uuid4(),
        building_id=b_outside.id,
        diagnostic_type="amiante",
        status="completed",
        created_by=uuid.uuid4(),
    )
    db.add(d_outside)

    await db.commit()

    similar = await BuildingSimilarityService.find_similar_buildings(db, ref_building.id)

    # Should find 3 buildings within range, not the 1960 building
    assert len(similar) == 3
    assert all(1965 <= b.construction_year <= 1975 for b in similar)


@pytest.mark.asyncio
async def test_canton_filtering(
    db: AsyncSession,
):
    """Test that canton filtering works correctly."""
    ref_building = Building(
        id=uuid.uuid4(),
        egrid="CH020000000000",
        egid=20000,
        address="Canton Test Building",
        postal_code="1200",
        city="Lausanne",
        canton="VD",
        building_type="apartment",
        construction_year=1970,
        status="active",
        created_by=uuid.uuid4(),
    )
    db.add(ref_building)

    diag = Diagnostic(
        id=uuid.uuid4(),
        building_id=ref_building.id,
        diagnostic_type="amiante",
        status="completed",
        created_by=uuid.uuid4(),
    )
    db.add(diag)

    # Create building in same canton
    b_vd = Building(
        id=uuid.uuid4(),
        egrid="CH020000000001",
        egid=20001,
        address="VD Building",
        postal_code="1200",
        city="Lausanne",
        canton="VD",
        building_type="apartment",
        construction_year=1970,
        status="active",
        created_by=uuid.uuid4(),
    )
    db.add(b_vd)

    d_vd = Diagnostic(
        id=uuid.uuid4(),
        building_id=b_vd.id,
        diagnostic_type="amiante",
        status="completed",
        created_by=uuid.uuid4(),
    )
    db.add(d_vd)

    # Create building in different canton
    b_ge = Building(
        id=uuid.uuid4(),
        egrid="CH020000000002",
        egid=20002,
        address="GE Building",
        postal_code="1200",
        city="Geneva",
        canton="GE",
        building_type="apartment",
        construction_year=1970,
        status="active",
        created_by=uuid.uuid4(),
    )
    db.add(b_ge)

    d_ge = Diagnostic(
        id=uuid.uuid4(),
        building_id=b_ge.id,
        diagnostic_type="amiante",
        status="completed",
        created_by=uuid.uuid4(),
    )
    db.add(d_ge)

    await db.commit()

    similar = await BuildingSimilarityService.find_similar_buildings(db, ref_building.id)

    # Should find only VD building, not GE
    assert len(similar) == 1
    assert similar[0].canton == "VD"
