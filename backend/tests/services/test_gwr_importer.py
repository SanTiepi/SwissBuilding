"""Tests for GWR (Registre fédéral des bâtiments) bulk importer."""

import asyncio
import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.constants import SOURCE_DATASET_GWR
from app.ingestion.gwr_importer import (
    HEAT_SOURCE_MAP,
    PRIMARY_USE_MAP,
    GWRImporter,
    import_gwr_bulk,
)
from app.models import Building


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def gwr_importer(db_session):
    """Create a GWR importer with test database session."""
    importer = GWRImporter(session=db_session)
    yield importer
    importer.close()


def _mock_gwr_record(
    egid: int = 1234567,
    address: str = "Rue de Test 1",
    postal_code: str = "1200",
    city: str = "Genève",
    canton: str = "GE",
    latitude: float = 46.2017,
    longitude: float = 6.1432,
    construction_year: int = 1990,
    heat_source: str = "E02",
    construction_period: str = "9",
    primary_use: str = "10",
    hot_water_source: str = "1",
    num_households: int = 12,
) -> dict:
    """Create a mock GWR API record."""
    return {
        "egid": egid,
        "address": address,
        "postal_code": postal_code,
        "city": city,
        "canton": canton,
        "latitude": latitude,
        "longitude": longitude,
        "construction_year": construction_year,
        "building_type": "residential",
        "floors_above": 5,
        "surface_area_m2": 3500.0,
        "volume_m3": 12000.0,
        "heat_source": heat_source,
        "construction_period": construction_period,
        "primary_use": primary_use,
        "hot_water_source": hot_water_source,
        "num_households": num_households,
        "municipality_ofs": 6621,
    }


# ---------------------------------------------------------------------------
# Test 1: First import creates new buildings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gwr_first_import_creates_buildings(gwr_importer):
    """First import of GWR records creates new buildings."""
    # Arrange
    gwr_record = _mock_gwr_record(egid=1234567)

    # Mock API response
    mock_buildings = [gwr_record]

    with patch.object(gwr_importer, "fetch_buildings_for_cantons", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_buildings

        # Act
        result = await gwr_importer.import_bulk(cantons=["GE"], limit=None, dry_run=False)

    # Assert
    assert result["imported"] == 1
    assert result["updated"] == 0
    assert result["errors"] == 0

    # Verify building was created
    building = gwr_importer.session.query(Building).filter_by(egid=1234567).first()
    assert building is not None
    assert building.address == "Rue de Test 1"
    assert building.city == "Genève"
    assert building.canton == "GE"
    assert building.heat_source == "gas"  # E02 -> gas
    assert building.primary_use == "habitation"  # 10 -> habitation
    assert building.hot_water_source == "centralized"  # 1 -> centralized
    assert building.num_households == 12
    assert building.source_dataset == SOURCE_DATASET_GWR


# ---------------------------------------------------------------------------
# Test 2: Re-import is idempotent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gwr_reimport_is_idempotent(gwr_importer):
    """Re-importing the same records doesn't modify existing data."""
    # Arrange: Create initial building
    initial_record = _mock_gwr_record(egid=9876543, construction_year=1980)
    initial_record_2 = _mock_gwr_record(egid=9876543)

    mock_buildings = [initial_record]

    with patch.object(gwr_importer, "fetch_buildings_for_cantons", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_buildings

        # Act: First import
        result1 = await gwr_importer.import_bulk(cantons=["GE"], dry_run=False)

    # Assert first import created 1
    assert result1["imported"] == 1

    # Reset importer stats
    gwr_importer.imported_count = 0
    gwr_importer.updated_count = 0
    gwr_importer.skipped_count = 0

    # Re-import same data
    mock_buildings = [initial_record]

    with patch.object(gwr_importer, "fetch_buildings_for_cantons", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_buildings

        # Act: Second import
        result2 = await gwr_importer.import_bulk(cantons=["GE"], dry_run=False)

    # Assert second import skips (idempotent)
    assert result2["imported"] == 0
    assert result2["skipped"] == 1


# ---------------------------------------------------------------------------
# Test 3: Merge logic - update missing fields only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gwr_merge_logic_preserves_existing_data(gwr_importer, db_session):
    """Merge logic updates only missing fields, preserves existing data."""
    # Arrange: Create building with partial data
    egid = 5555555
    building = Building(
        egid=egid,
        address="Old Address",
        postal_code="1000",
        city="Zurich",
        canton="ZH",
        building_type="residential",
        created_by=uuid.uuid4(),
        heat_source="oil",  # Existing value
        # num_households is None
    )
    db_session.add(building)
    db_session.commit()

    # GWR record with same egid but different values
    gwr_record = _mock_gwr_record(
        egid=egid,
        address="New Address",
        postal_code="1200",
        city="Genève",
        heat_source="E02",  # Should be ignored
        num_households=10,  # Should be filled in
    )

    # Mock API response
    mock_buildings = [gwr_record]

    with patch.object(gwr_importer, "fetch_buildings_for_cantons", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_buildings

        # Act: Import
        result = await gwr_importer.import_bulk(cantons=["GE"], dry_run=False)

    # Assert: Updated (not skipped)
    assert result["updated"] == 1

    # Verify merge: existing data preserved, missing fields filled
    building = gwr_importer.session.query(Building).filter_by(egid=egid).first()
    assert building.address == "Old Address"  # Preserved
    assert building.heat_source == "oil"  # Preserved (was not None)
    assert building.num_households == 10  # Filled (was None)


# ---------------------------------------------------------------------------
# Test 4: Handles missing/invalid egid gracefully
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gwr_skips_records_without_egid(gwr_importer):
    """Records without egid are skipped."""
    # Arrange: Record without egid
    bad_record = _mock_gwr_record(egid=None)

    mock_buildings = [bad_record]

    with patch.object(gwr_importer, "fetch_buildings_for_cantons", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_buildings

        # Act
        result = await gwr_importer.import_bulk(cantons=["GE"], dry_run=False)

    # Assert
    assert result["imported"] == 0
    assert result["skipped"] == 1
    assert result["errors"] == 0


# ---------------------------------------------------------------------------
# Test 5: Batch processing and source tracking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gwr_batch_processing_and_source_tracking(gwr_importer):
    """Batch processing works correctly and source is tracked."""
    # Arrange: Multiple records
    mock_buildings = [
        _mock_gwr_record(egid=1000001),
        _mock_gwr_record(egid=1000002),
        _mock_gwr_record(egid=1000003),
    ]

    with patch.object(gwr_importer, "fetch_buildings_for_cantons", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_buildings

        # Act
        result = await gwr_importer.import_bulk(cantons=["GE"], dry_run=False)

    # Assert
    assert result["imported"] == 3
    assert result["errors"] == 0

    # Verify source tracking for all buildings
    for i in range(1, 4):
        building = gwr_importer.session.query(Building).filter_by(egid=1000000 + i).first()
        assert building is not None
        assert building.source_dataset == SOURCE_DATASET_GWR
        assert building.source_imported_at is not None
        assert building.source_metadata_json is not None
        assert building.source_metadata_json.get("gwr_source") == "geo.admin.ch"


# ---------------------------------------------------------------------------
# Test 6: Field normalization maps correctly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gwr_field_normalization(gwr_importer):
    """GWR codes are normalized correctly to readable values."""
    # Arrange: Record with various codes
    gwr_record = _mock_gwr_record(
        egid=7777777,
        heat_source="E04",  # Should map to heat_pump
        construction_period="8",  # Should map to 1975-1985
        primary_use="20",  # Should map to commerce
        hot_water_source="2",  # Should map to decentralized
    )

    mock_buildings = [gwr_record]

    with patch.object(gwr_importer, "fetch_buildings_for_cantons", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_buildings

        # Act
        result = await gwr_importer.import_bulk(cantons=["VD"], dry_run=False)

    # Assert: Created successfully
    assert result["imported"] == 1

    # Verify normalization
    building = gwr_importer.session.query(Building).filter_by(egid=7777777).first()
    assert building.heat_source == "heat_pump"
    assert building.construction_period == "1975-1985"
    assert building.primary_use == "commerce"
    assert building.hot_water_source == "decentralized"


# ---------------------------------------------------------------------------
# Convenience function test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_gwr_bulk_convenience_function(db_session):
    """Convenience function import_gwr_bulk works end-to-end."""
    # Mock the importer's fetch method
    mock_buildings = [_mock_gwr_record(egid=9999999)]

    with patch("app.ingestion.gwr_importer.GWRImporter.fetch_buildings_for_cantons", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_buildings

        # Act
        result = await import_gwr_bulk(cantons=["GE"], limit=None, dry_run=False)

    # Assert
    assert result["imported"] == 1
    assert result["errors"] == 0
