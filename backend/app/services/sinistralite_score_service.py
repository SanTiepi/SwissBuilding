"""Sinistralite score service — calculates building incident history risk score.

Combines incident frequency, severity, recency, and type to produce a 0-100
sinistralite score and risk level classification (low/medium/high/critical).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import IncidentEpisode

logger = logging.getLogger(__name__)


class SinistraliteScoreService:
    """Calculate sinistralite (incident history) score for buildings."""

    SEVERITY_WEIGHTS = {
        "minor": 1,
        "moderate": 3,
        "major": 7,
        "critical": 15,
    }

    INCIDENT_WEIGHTS = {
        "leak": 2,
        "mold": 3,
        "flooding": 10,
        "fire": 15,
        "structural": 12,
        "subsidence": 10,
        "movement": 8,
        "breakage": 2,
        "equipment_failure": 2,
        "storm_damage": 5,
        "pest": 1,
        "contamination": 8,
        "vandalism": 1,
        "other": 2,
    }

    @staticmethod
    async def calculate_sinistralite_score(db: AsyncSession, building_id: UUID) -> dict[str, Any]:
        """Calculate sinistralite score (0-100) based on incident history.

        Args:
            db: AsyncSession for database queries
            building_id: UUID of the building

        Returns:
            dict with keys:
            - building_id: UUID
            - score: int (0-100)
            - level: str (low/medium/high/critical)
            - incident_count_10y: int (total incidents in 10 years)
            - incident_by_type: dict (type -> count)
            - recurrent_types: list (types with 3+ incidents)
        """
        # Query incidents from last 10 years
        cutoff_date = datetime.utcnow() - timedelta(days=365 * 10)

        stmt = select(IncidentEpisode).where(
            IncidentEpisode.building_id == building_id,
            IncidentEpisode.discovered_at >= cutoff_date,
        )

        result = await db.execute(stmt)
        incidents = result.scalars().all()

        # No incidents = low risk
        if not incidents:
            return {
                "building_id": building_id,
                "score": 0,
                "level": "low",
                "incident_count_10y": 0,
                "incident_by_type": {},
                "recurrent_types": [],
            }

        score = 0.0
        incident_counts: dict[str, int] = {}
        recurrent_types: list[str] = []

        for incident in incidents:
            # Base score from severity × incident type weight
            severity_weight = SinistraliteScoreService.SEVERITY_WEIGHTS.get(incident.severity, 2)
            incident_weight = SinistraliteScoreService.INCIDENT_WEIGHTS.get(incident.incident_type, 2)

            base_score = severity_weight * incident_weight

            # Recency multiplier (more recent = higher weight)
            days_ago = (datetime.utcnow() - incident.discovered_at).days
            if days_ago < 365:  # Last year
                recency_mult = 1.0
            elif days_ago < 730:  # 1-2 years
                recency_mult = 0.8
            else:  # 2+ years
                recency_mult = 0.6

            score += base_score * recency_mult

            # Track incident counts by type
            incident_counts[incident.incident_type] = incident_counts.get(incident.incident_type, 0) + 1

        # Identify recurrent types (3+ times in 10 years)
        for itype, count in incident_counts.items():
            if count >= 3:
                recurrent_types.append(itype)

        # Normalize score to 0-100
        final_score = min(int(score), 100)

        # Determine risk level
        if final_score >= 70:
            level = "critical"
        elif final_score >= 50:
            level = "high"
        elif final_score >= 25:
            level = "medium"
        else:
            level = "low"

        return {
            "building_id": building_id,
            "score": final_score,
            "level": level,
            "incident_count_10y": len(incidents),
            "incident_by_type": incident_counts,
            "recurrent_types": recurrent_types,
        }
