"""Add building_passport_states and dossier_versions tables

Revision ID: 004_passport_dossier_version
Revises: 003_add_physical_building_tables
Create Date: 2026-03-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "004_passport_dossier_version"
down_revision: Union[str, None] = "003_add_physical_building_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. building_passport_states (FK -> buildings, users)
    # ------------------------------------------------------------------
    op.create_table(
        "building_passport_states",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("previous_status", sa.String(50), nullable=True),
        sa.Column("changed_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_building_passport_states_building_id", "building_passport_states", ["building_id"])
    op.create_index("idx_building_passport_states_status", "building_passport_states", ["status"])

    # ------------------------------------------------------------------
    # 2. dossier_versions (FK -> buildings, users)
    # ------------------------------------------------------------------
    op.create_table(
        "dossier_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("created_by_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("snapshot_data", sa.JSON(), nullable=False),
        sa.Column("completeness_score", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_dossier_versions_building_id", "dossier_versions", ["building_id"])


def downgrade() -> None:
    op.drop_table("dossier_versions")
    op.drop_table("building_passport_states")
