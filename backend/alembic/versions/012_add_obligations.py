"""add obligations table

Revision ID: 012_add_obligations
Revises: 009_add_diagnostic_integ
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "012_add_obligations"
down_revision = "009_add_diagnostic_integ"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "obligations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("obligation_type", sa.String(50), nullable=False),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column("recurrence", sa.String(30), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="upcoming"),
        sa.Column("priority", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("responsible_org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("responsible_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("completed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("linked_entity_type", sa.String(50), nullable=True),
        sa.Column("linked_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reminder_days_before", sa.Integer, server_default="30"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_obligations_building_id", "obligations", ["building_id"])
    op.create_index("idx_obligations_status", "obligations", ["status"])
    op.create_index("idx_obligations_due_date", "obligations", ["due_date"])
    op.create_index("idx_obligations_type", "obligations", ["obligation_type"])


def downgrade() -> None:
    op.drop_index("idx_obligations_type")
    op.drop_index("idx_obligations_due_date")
    op.drop_index("idx_obligations_status")
    op.drop_index("idx_obligations_building_id")
    op.drop_table("obligations")
