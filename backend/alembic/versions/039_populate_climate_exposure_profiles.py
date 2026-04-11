"""Populate climate exposure profiles with MeteoSwiss reference data.

Programme B.1: Populate ClimateExposureProfile with real climate data.

Sets default heating_degree_days and stress indicators for all buildings
that have a climate_exposure_profiles row with NULL heating_degree_days.
Actual per-building enrichment runs via the enrichment pipeline or
POST /buildings/{id}/enrich/climate.

Revision ID: 039_populate_climate_profiles
Revises: 038_material_recognition
Create Date: 2026-04-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "039_populate_climate_profiles"
down_revision: str | None = "038_material_recognition"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Set default Swiss plateau heating degree days where NULL
    op.execute(
        """
        UPDATE climate_exposure_profiles
        SET heating_degree_days = 3100,
            moisture_stress = 'moderate',
            thermal_stress = 'moderate',
            uv_exposure = 'moderate',
            wind_exposure = 'moderate',
            last_updated = NOW()
        WHERE heating_degree_days IS NULL
        """
    )

    # Create profiles for buildings that don't have one yet
    op.execute(
        """
        INSERT INTO climate_exposure_profiles (id, building_id, heating_degree_days,
            moisture_stress, thermal_stress, uv_exposure, wind_exposure, last_updated)
        SELECT gen_random_uuid(), b.id, 3100,
            'moderate', 'moderate', 'moderate', 'moderate', NOW()
        FROM buildings b
        LEFT JOIN climate_exposure_profiles c ON c.building_id = b.id
        WHERE c.id IS NULL
        """
    )


def downgrade() -> None:
    # Reset populated defaults back to NULL
    op.execute(
        """
        UPDATE climate_exposure_profiles
        SET heating_degree_days = NULL,
            moisture_stress = 'unknown',
            thermal_stress = 'unknown',
            uv_exposure = 'unknown',
            wind_exposure = NULL,
            last_updated = NULL
        WHERE data_sources IS NULL
        """
    )
