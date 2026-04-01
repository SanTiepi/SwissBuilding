"""Add swissBUILDINGS3D fields to buildings table.

Revision ID: 036_swissbuildings3d
Revises: 035_memory_transfers
Create Date: 2026-04-01
"""

import sqlalchemy as sa

from alembic import op

revision = "036_swissbuildings3d"
down_revision = "035_memory_transfers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("buildings", sa.Column("footprint_wkt", sa.Text(), nullable=True))
    op.add_column("buildings", sa.Column("building_height", sa.Float(), nullable=True))
    op.add_column("buildings", sa.Column("roof_type", sa.String(100), nullable=True))
    op.add_column("buildings", sa.Column("floor_count_3d", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("buildings", "floor_count_3d")
    op.drop_column("buildings", "roof_type")
    op.drop_column("buildings", "building_height")
    op.drop_column("buildings", "footprint_wkt")
