"""Add artifact_versions and custody_events tables.

Revision ID: 031_artifact_custody
Revises: 030_add_exchange_hardening
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "031_artifact_custody"
down_revision = "030_add_exchange_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artifact_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_type", sa.String(50), nullable=False, index=True),
        sa.Column("artifact_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="current"),
        sa.Column("superseded_by_id", UUID(as_uuid=True), sa.ForeignKey("artifact_versions.id"), nullable=True),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime, nullable=True),
        sa.Column("archive_reason", sa.Text, nullable=True),
    )

    op.create_table(
        "custody_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "artifact_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("artifact_versions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("actor_type", sa.String(30), nullable=False, server_default="system"),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_name", sa.String(200), nullable=True),
        sa.Column("recipient_org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("details", JSON, nullable=True),
        sa.Column("occurred_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("custody_events")
    op.drop_table("artifact_versions")
