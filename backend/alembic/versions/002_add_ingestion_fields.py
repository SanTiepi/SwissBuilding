"""Add ingestion fields to buildings (egid, municipality_ofs, source_*)

Revision ID: 002_add_ingestion_fields
Revises: 001_initial_schema
Create Date: 2026-03-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002_add_ingestion_fields"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("buildings", sa.Column("egid", sa.Integer(), nullable=True))
    op.add_column("buildings", sa.Column("municipality_ofs", sa.Integer(), nullable=True))
    op.add_column("buildings", sa.Column("source_dataset", sa.String(50), nullable=True))
    op.add_column("buildings", sa.Column("source_imported_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("buildings", sa.Column("source_metadata_json", sa.JSON(), nullable=True))

    op.create_index("ix_buildings_egid", "buildings", ["egid"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_buildings_egid", table_name="buildings")
    op.drop_column("buildings", "source_metadata_json")
    op.drop_column("buildings", "source_imported_at")
    op.drop_column("buildings", "source_dataset")
    op.drop_column("buildings", "municipality_ofs")
    op.drop_column("buildings", "egid")
