"""
SwissBuildingOS - Building Similarity Service

Find similar buildings for cross-building pattern analysis and pollutant predictions.
"""

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building


class BuildingSimilarityService:
    """Find similar buildings for pattern learning and correlation analysis."""

    @staticmethod
    async def find_similar_buildings(
        db: AsyncSession,
        building_id: UUID,
        max_results: int = 50,
    ) -> list[Building]:
        """
        Find buildings similar in age, type, location.
        
        Similarity criteria:
        - Same building type
        - Construction year within ±5 years
        - Same canton
        - Must have at least one diagnostic
        
        Args:
            db: Database session
            building_id: Target building ID
            max_results: Maximum number of results
            
        Returns:
            List of similar Building objects
        """
        # Get the reference building
        stmt = select(Building).where(Building.id == building_id)
        result = await db.execute(stmt)
        building = result.scalar_one_or_none()

        if not building:
            return []

        # Define similarity criteria
        age_range_min = (building.construction_year or 2000) - 5
        age_range_max = (building.construction_year or 2000) + 5

        # Find similar buildings
        stmt = (
            select(Building)
            .where(
                and_(
                    Building.id != building_id,
                    Building.building_type == building.building_type,
                    Building.construction_year >= age_range_min,
                    Building.construction_year <= age_range_max,
                    Building.canton == building.canton,
                )
            )
            .options(selectinload(Building.diagnostics))
            .limit(max_results)
        )

        result = await db.execute(stmt)
        similar_buildings = result.scalars().all()

        # Filter to only buildings with diagnostics
        similar_with_diagnostics = [b for b in similar_buildings if b.diagnostics]

        return similar_with_diagnostics

    @staticmethod
    async def similarity_score(
        db: AsyncSession,
        building_id_1: UUID,
        building_id_2: UUID,
    ) -> float:
        """
        Calculate similarity score between two buildings (0-1).
        
        Score components:
        - Type match (exact): +0.3
        - Age proximity: +0.3 (max)
        - Canton match: +0.2
        - Postal code prefix match: +0.2
        
        Args:
            db: Database session
            building_id_1: First building ID
            building_id_2: Second building ID
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        stmt = select(Building).where(Building.id == building_id_1)
        result = await db.execute(stmt)
        b1 = result.scalar_one_or_none()

        stmt = select(Building).where(Building.id == building_id_2)
        result = await db.execute(stmt)
        b2 = result.scalar_one_or_none()

        if not b1 or not b2:
            return 0.0

        score = 0.0

        # Type match (exact): +0.3
        if b1.building_type == b2.building_type:
            score += 0.3

        # Age proximity: +0.3 (max)
        age_diff = abs((b1.construction_year or 2000) - (b2.construction_year or 2000))
        score += 0.3 * max(0, 1 - age_diff / 20)

        # Canton match: +0.2
        if b1.canton == b2.canton:
            score += 0.2

        # Postal code prefix match: +0.2
        if b1.postal_code and b2.postal_code and b1.postal_code[:2] == b2.postal_code[:2]:
            score += 0.2

        return min(score, 1.0)

    @staticmethod
    async def get_reference_building(db: AsyncSession, building_id: UUID) -> Building | None:
        """Get reference building with all relationships loaded."""
        stmt = (
            select(Building)
            .where(Building.id == building_id)
            .options(selectinload(Building.diagnostics).selectinload("samples"))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
