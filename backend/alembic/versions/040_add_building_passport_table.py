"""Add building_passport table for A-F grade system.

Revision ID: 040
Revises: 039
Create Date: 2026-04-02 03:50:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None


def upgrade():
    # Create building_passports table
    op.create_table(
        "building_passports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "building_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("structural_grade", sa.String(1), nullable=False),
        sa.Column("energy_grade", sa.String(1), nullable=False),
        sa.Column("safety_grade", sa.String(1), nullable=False),
        sa.Column("environmental_grade", sa.String(1), nullable=False),
        sa.Column("compliance_grade", sa.String(1), nullable=False),
        sa.Column("readiness_grade", sa.String(1), nullable=False),
        sa.Column("overall_grade", sa.String(1), nullable=False),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create index on building_id
    op.create_index(
        "idx_building_passports_building_id",
        "building_passports",
        ["building_id"],
    )
    
    # Create index on created_at for ordering
    op.create_index(
        "idx_building_passports_created_at",
        "building_passports",
        ["created_at"],
    )


def downgrade():
    op.drop_index(
        "idx_building_passports_created_at",
        table_name="building_passports",
    )
    op.drop_index(
        "idx_building_passports_building_id",
        table_name="building_passports",
    )
    op.drop_table("building_passports")
