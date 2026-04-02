"""Add post_work_items and works_completion_certificates tables.

Revision ID: 041
Revises: 040
Create Date: 2026-04-02 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "post_work_items",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("building_id", sa.UUID(), sa.ForeignKey("buildings.id"), nullable=False, index=True),
        sa.Column("work_item_id", sa.UUID(), nullable=True),
        sa.Column("building_element_id", sa.UUID(), sa.ForeignKey("building_elements.id"), nullable=True),
        sa.Column("completion_status", sa.String(50), server_default="pending"),
        sa.Column("completion_date", sa.DateTime(), nullable=True),
        sa.Column("contractor_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("photo_uris", sa.JSON(), nullable=True),
        sa.Column("before_after_pairs", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("verification_score", sa.Float(), server_default="0.0"),
        sa.Column("flagged_for_review", sa.Boolean(), server_default="false"),
        sa.Column("ai_generated", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_post_work_building_contractor", "post_work_items", ["building_id", "contractor_id"])
    op.create_index("idx_post_work_status", "post_work_items", ["completion_status"])

    op.create_table(
        "works_completion_certificates",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("building_id", sa.UUID(), sa.ForeignKey("buildings.id"), nullable=False, unique=True),
        sa.Column("pdf_uri", sa.String(500), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("verified_items", sa.Integer(), nullable=False),
        sa.Column("completion_percentage", sa.Float(), nullable=False),
        sa.Column("issued_date", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("contractor_signature_uri", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_cert_building", "works_completion_certificates", ["building_id"])


def downgrade() -> None:
    op.drop_table("works_completion_certificates")
    op.drop_table("post_work_items")
