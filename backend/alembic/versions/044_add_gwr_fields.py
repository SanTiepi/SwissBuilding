"""Add GWR (Registre fédéral des bâtiments) fields to buildings table.

Revision ID: 044_add_gwr_fields
Revises: 043_contractor_quotes
Create Date: 2026-04-03

New fields:
- heat_source: heating system type (gaz, mazout, pompe à chaleur, bois, électrique, district, autre)
- construction_period: construction period bracket (e.g. 1900-1920, 2010-2025)
- primary_use: primary building use (habitation, commerce, industrie, agriculture, etc.)
- renovation_year: year of last renovation
- hot_water_source: hot water system type (centralisé, décentralisé, sans)
- num_households: number of households/units in building
"""

import sqlalchemy as sa
from alembic import op


revision = "044_add_gwr_fields"
down_revision = "043_contractor_quotes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add GWR fields to buildings table."""
    op.add_column("buildings", sa.Column("heat_source", sa.String(100), nullable=True))
    op.add_column("buildings", sa.Column("construction_period", sa.String(50), nullable=True))
    op.add_column("buildings", sa.Column("primary_use", sa.String(100), nullable=True))
    op.add_column("buildings", sa.Column("hot_water_source", sa.String(100), nullable=True))
    op.add_column("buildings", sa.Column("num_households", sa.Integer, nullable=True))

    # Create indexes for performance on commonly queried fields
    op.create_index("idx_buildings_heat_source", "buildings", ["heat_source"])
    op.create_index("idx_buildings_primary_use", "buildings", ["primary_use"])
    op.create_index("idx_buildings_num_households", "buildings", ["num_households"])


def downgrade() -> None:
    """Remove GWR fields from buildings table."""
    op.drop_index("idx_buildings_num_households", table_name="buildings")
    op.drop_index("idx_buildings_primary_use", table_name="buildings")
    op.drop_index("idx_buildings_heat_source", table_name="buildings")

    op.drop_column("buildings", "num_households")
    op.drop_column("buildings", "hot_water_source")
    op.drop_column("buildings", "primary_use")
    op.drop_column("buildings", "construction_period")
    op.drop_column("buildings", "heat_source")
