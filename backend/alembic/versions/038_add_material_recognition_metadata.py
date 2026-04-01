"""Add AI recognition metadata columns to materials table.

Programme C.6: Material recognition via Claude Vision API.

Revision ID: 038_material_recognition
Revises: 037_defect_timelines
Create Date: 2026-04-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "038_material_recognition"
down_revision: str | None = "037_defect_timelines"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("materials", sa.Column("identified_by_ai", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("materials", sa.Column("ai_confidence", sa.Float(), nullable=True))
    op.add_column("materials", sa.Column("year_estimated", sa.Integer(), nullable=True))
    op.add_column("materials", sa.Column("ai_pollutants", sa.JSON(), nullable=True))
    op.add_column("materials", sa.Column("ai_recommendations", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("materials", "ai_recommendations")
    op.drop_column("materials", "ai_pollutants")
    op.drop_column("materials", "year_estimated")
    op.drop_column("materials", "ai_confidence")
    op.drop_column("materials", "identified_by_ai")
