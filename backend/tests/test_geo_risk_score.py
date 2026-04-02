"""Tests for geo risk score service (A.16)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_geo_context import BuildingGeoContext
from app.models.user import User
from app.services.geo_risk_score_service import get_geo_risk_score, compute_geo_risk_score


class TestGeoRiskScore:
    """Tests for composite geo risk score calculation."""

    @pytest.mark.asyncio
    async def test_building_not_found(self, db: AsyncSession):
        """Test that building not found returns None."""
        non_existent_id = uuid.uuid4()
        result = await get_geo_risk_score(db, non_existent_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_with_full_geo_context_data(self, db: AsyncSession):
        """Test score calculation with full geo context data."""
        # Create test user (required for building)
        user = User(
            email=f"test_{uuid.uuid4()}@example.com",
            password_hash="test",
            first_name="Test",
            last_name="User",
            role="owner",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        # Create test building
        building = Building(
            egid=12345678,
            egrid="EG12345",
            address="Test Address 1",
            postal_code="8000",
            city="Zurich",
            canton="ZH",
            building_type="residential",
            latitude=47.5,
            longitude=8.5,
            created_by=user.id,
        )
        db.add(building)
        await db.flush()

        # Create geo context with all dimensions
        context_data = {
            "natural_hazards": {"gefahrenstufe": "erheblich"},  # inondation: 10
            "seismic": {"baugrundklasse": "D"},  # seismic: 8
            "grele": {"haeufigkeit": 7},  # grele: 7
            "contaminated_sites": {"status": "belastet"},  # contamination: 5
            "radon": {"radon_bq_m3": "400"},  # radon: 7
        }

        geo_ctx = BuildingGeoContext(
            building_id=building.id,
            context_data=context_data,
            source_version="geo.admin-v1",
        )
        db.add(geo_ctx)
        await db.commit()

        # Get score
        result = await get_geo_risk_score(db, building.id)

        assert result is not None
        assert "score" in result
        assert "inondation" in result
        assert "seismic" in result
        assert "grele" in result
        assert "contamination" in result
        assert "radon" in result

        # Validate score is 0-100
        assert 0 <= result["score"] <= 100
        # Each sub-dimension should be 0-10
        assert 0 <= result["inondation"] <= 10
        assert 0 <= result["seismic"] <= 10
        assert 0 <= result["grele"] <= 10
        assert 0 <= result["contamination"] <= 10
        assert 0 <= result["radon"] <= 10

        # Clean up
        await db.execute(delete(BuildingGeoContext).where(BuildingGeoContext.building_id == building.id))
        await db.execute(delete(Building).where(Building.id == building.id))
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()

    @pytest.mark.asyncio
    async def test_with_partial_data_defaults_to_zero(self, db: AsyncSession):
        """Test that missing sub-dimensions default to 0."""
        # Create test user
        user = User(
            email=f"test_partial_{uuid.uuid4()}@example.com",
            password_hash="test",
            first_name="Test",
            last_name="Partial",
            role="owner",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        # Create test building
        building = Building(
            egid=87654321,
            egrid="EG87654",
            address="Partial Test",
            postal_code="8000",
            city="Zurich",
            canton="ZH",
            building_type="commercial",
            latitude=47.5,
            longitude=8.5,
            created_by=user.id,
        )
        db.add(building)
        await db.flush()

        # Create geo context with only some dimensions
        context_data = {
            "natural_hazards": {"gefahrenstufe": "mittel"},  # inondation: 7
            "seismic": {"baugrundklasse": "A"},  # seismic: 2
            # grele, contamination, radon missing -> default to 0
        }

        geo_ctx = BuildingGeoContext(
            building_id=building.id,
            context_data=context_data,
            source_version="geo.admin-v1",
        )
        db.add(geo_ctx)
        await db.commit()

        # Get score
        result = await get_geo_risk_score(db, building.id)

        assert result is not None
        assert result["inondation"] == 7.0
        assert result["seismic"] == 2.0
        assert result["grele"] == 0.0
        assert result["contamination"] == 0.0
        assert result["radon"] == 0.0

        # Clean up
        await db.execute(delete(BuildingGeoContext).where(BuildingGeoContext.building_id == building.id))
        await db.execute(delete(Building).where(Building.id == building.id))
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()

    @pytest.mark.asyncio
    async def test_score_aggregation_formula(self, db: AsyncSession):
        """Test that composite score is correctly calculated as sum * weight."""
        # Create test user
        user = User(
            email=f"test_formula_{uuid.uuid4()}@example.com",
            password_hash="test",
            first_name="Test",
            last_name="Formula",
            role="owner",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        # Create test building
        building = Building(
            egid=11111111,
            egrid="EG11111",
            address="Formula Test",
            postal_code="8000",
            city="Zurich",
            canton="ZH",
            building_type="industrial",
            latitude=47.5,
            longitude=8.5,
            created_by=user.id,
        )
        db.add(building)
        await db.flush()

        # Set all sub-dimensions to specific values
        context_data = {
            "natural_hazards": {"gefahrenstufe": "erheblich"},  # inondation: 10
            "seismic": {"baugrundklasse": "D"},  # seismic: 8
            "grele": {"haeufigkeit": 7},  # grele: 7
            "contaminated_sites": {"status": "belastet"},  # contamination: 5
            "radon": {"radon_bq_m3": "500"},  # radon: 7
        }

        geo_ctx = BuildingGeoContext(
            building_id=building.id,
            context_data=context_data,
            source_version="geo.admin-v1",
        )
        db.add(geo_ctx)
        await db.commit()

        # Get score
        result = await get_geo_risk_score(db, building.id)

        assert result is not None

        # Expected calculation:
        # sum = 10 + 8 + 7 + 5 + 7 = 37
        # composite = 37 * 2 = 74
        expected_score = min(100, (10 + 8 + 7 + 5 + 7) * 2)
        assert result["score"] == expected_score

        # Clean up
        await db.execute(delete(BuildingGeoContext).where(BuildingGeoContext.building_id == building.id))
        await db.execute(delete(Building).where(Building.id == building.id))
        await db.execute(delete(User).where(User.id == user.id))
        await db.commit()


class TestComputeGeoRiskScore:
    """Unit tests for compute_geo_risk_score function."""

    def test_empty_context_data(self):
        """Test with empty context data."""
        result = compute_geo_risk_score({})
        assert result["score"] == 0
        assert result["inondation"] == 0.0
        assert result["seismic"] == 0.0
        assert result["grele"] == 0.0
        assert result["contamination"] == 0.0
        assert result["radon"] == 0.0

    def test_maximum_risk_capped_at_100(self):
        """Test that maximum score is 100."""
        context_data = {
            "natural_hazards": {"gefahrenstufe": "erheblich"},  # 10
            "seismic": {"baugrundklasse": "E"},  # 10
            "grele": {"haeufigkeit": 10},  # 10
            "contaminated_sites": {"status": "sanierungsbedürftig"},  # 10
            "radon": {"radon_bq_m3": "1500"},  # 10
        }
        result = compute_geo_risk_score(context_data)
        # 10 + 10 + 10 + 10 + 10 = 50, * 2 = 100
        assert result["score"] <= 100
