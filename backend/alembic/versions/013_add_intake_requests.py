"""add intake_requests table

Revision ID: 013_add_intake_reqs
Revises: 012_add_obligations
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "013_add_intake_reqs"
down_revision = "012_add_obligations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intake_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("requester_name", sa.String(200), nullable=False),
        sa.Column("requester_email", sa.String(200), nullable=False),
        sa.Column("requester_phone", sa.String(50), nullable=True),
        sa.Column("requester_company", sa.String(200), nullable=True),
        sa.Column("building_address", sa.String(500), nullable=False),
        sa.Column("building_egid", sa.String(20), nullable=True),
        sa.Column("building_city", sa.String(100), nullable=True),
        sa.Column("building_postal_code", sa.String(10), nullable=True),
        sa.Column("request_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("urgency", sa.String(20), nullable=False, server_default="standard"),
        sa.Column("attachments", postgresql.JSON, nullable=True),
        sa.Column(
            "converted_contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id"),
            nullable=True,
        ),
        sa.Column(
            "converted_building_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=True,
        ),
        sa.Column("converted_mission_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "qualified_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("qualified_at", sa.DateTime, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="website"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_intake_requests_status", "intake_requests", ["status"])
    op.create_index("idx_intake_requests_email", "intake_requests", ["requester_email"])
    op.create_index("idx_intake_requests_created_at", "intake_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_intake_requests_created_at")
    op.drop_index("idx_intake_requests_email")
    op.drop_index("idx_intake_requests_status")
    op.drop_table("intake_requests")
