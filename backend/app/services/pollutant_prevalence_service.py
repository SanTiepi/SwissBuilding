"""
SwissBuildingOS - Pollutant Prevalence Service

Analyze pollutant patterns in similar buildings and generate risk predictions.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.services.building_similarity_service import BuildingSimilarityService


class PollutantPrevalenceService:
    """Analyze pollutant prevalence in similar buildings for prediction."""

    @staticmethod
    async def analyze_pollutant_patterns(
        db: AsyncSession,
        similar_buildings: list[Building],
    ) -> dict:
        """
        Analyze what pollutants were found in similar buildings.
        
        Collects sample data from all diagnostics of similar buildings
        and calculates prevalence rates for each pollutant type.
        
        Args:
            db: Database session
            similar_buildings: List of similar Building objects
            
        Returns:
            Dictionary with pollutant statistics and prevalence data
        """
        pollutant_findings = {}

        for building in similar_buildings:
            for diagnostic in building.diagnostics:
                for sample in diagnostic.samples:
                    if not sample.pollutant_type:
                        continue

                    pollutant_type = sample.pollutant_type.lower()

                    # Initialize pollutant entry if needed
                    if pollutant_type not in pollutant_findings:
                        pollutant_findings[pollutant_type] = {
                            "confirmed": 0,
                            "suspected": 0,
                            "negative": 0,
                            "total_checked": 0,
                        }

                    # Determine status from threshold_exceeded and risk_level
                    if sample.threshold_exceeded:
                        pollutant_findings[pollutant_type]["confirmed"] += 1
                    elif sample.risk_level in ("medium", "high"):
                        pollutant_findings[pollutant_type]["suspected"] += 1
                    else:
                        pollutant_findings[pollutant_type]["negative"] += 1

                    pollutant_findings[pollutant_type]["total_checked"] += 1

        return pollutant_findings

    @staticmethod
    async def get_building_pollutant_predictions(
        db: AsyncSession,
        building_id: UUID,
    ) -> dict:
        """
        Get pollutant predictions based on similar buildings.
        
        Returns top 5 pollutants by probability of occurrence based on
        patterns observed in similar buildings.
        
        Args:
            db: Database session
            building_id: Target building ID
            
        Returns:
            Dictionary with predictions including probability, counts, and metadata
        """
        # Find similar buildings
        similar = await BuildingSimilarityService.find_similar_buildings(db, building_id, max_results=50)

        if not similar:
            return {
                "building_id": str(building_id),
                "similar_buildings_count": 0,
                "pollutant_predictions": [],
                "notes": "Insufficient similar buildings for prediction",
            }

        # Analyze pollutant patterns
        pollutant_findings = await PollutantPrevalenceService.analyze_pollutant_patterns(db, similar)

        if not pollutant_findings:
            return {
                "building_id": str(building_id),
                "similar_buildings_count": len(similar),
                "pollutant_predictions": [],
                "notes": "No pollutant data available in similar buildings",
            }

        # Calculate probabilities and build prediction list
        predictions = []
        for pollutant, stats in pollutant_findings.items():
            total = stats["total_checked"]
            confirmed = stats["confirmed"]
            probability = confirmed / total if total > 0 else 0

            predictions.append({
                "pollutant": pollutant,
                "probability": round(probability, 3),
                "probability_percent": round(probability * 100, 1),
                "count_confirmed": confirmed,
                "count_checked": total,
            })

        # Sort by probability descending and take top 5
        predictions_sorted = sorted(
            predictions,
            key=lambda x: x["probability"],
            reverse=True,
        )[:5]

        return {
            "building_id": str(building_id),
            "similar_buildings_count": len(similar),
            "pollutant_predictions": predictions_sorted,
            "notes": f"Predictions based on {len(similar)} similar buildings",
        }
