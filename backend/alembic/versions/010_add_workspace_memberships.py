"""Add workspace_memberships table for per-building shared access

Revision ID: 010_add_workspace_member
Revises: 009_add_diag_integration
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "010_add_workspace_member"
down_revision: str | None = "009_add_diag_integration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_memberships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("building_id", UUID(as_uuid=True), sa.ForeignKey("buildings.id"), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("access_scope", sa.JSON, nullable=True),
        sa.Column("granted_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("granted_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("idx_ws_membership_building", "workspace_memberships", ["building_id"])
    op.create_index("idx_ws_membership_org", "workspace_memberships", ["organization_id"])
    op.create_index("idx_ws_membership_user", "workspace_memberships", ["user_id"])
    op.create_index("idx_ws_membership_active", "workspace_memberships", ["building_id", "is_active"])


def downgrade() -> None:
    op.drop_index("idx_ws_membership_active", table_name="workspace_memberships")
    op.drop_index("idx_ws_membership_user", table_name="workspace_memberships")
    op.drop_index("idx_ws_membership_org", table_name="workspace_memberships")
    op.drop_index("idx_ws_membership_building", table_name="workspace_memberships")
    op.drop_table("workspace_memberships")
