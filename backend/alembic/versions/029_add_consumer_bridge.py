"""Add consumer bridge columns to diagnostic_report_publications

Revision ID: 029_add_consumer_brdg
Revises: 028_add_intel_stack
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "029_add_consumer_brdg"
down_revision: str | None = "028_add_intel_stack"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("diagnostic_report_publications", sa.Column("consumer_state", sa.String(30), nullable=True))
    op.add_column("diagnostic_report_publications", sa.Column("contract_version", sa.String(20), nullable=True))
    op.add_column("diagnostic_report_publications", sa.Column("fetch_error", sa.Text, nullable=True))
    op.add_column("diagnostic_report_publications", sa.Column("fetched_at", sa.DateTime, nullable=True))


def downgrade() -> None:
    op.drop_column("diagnostic_report_publications", "fetched_at")
    op.drop_column("diagnostic_report_publications", "fetch_error")
    op.drop_column("diagnostic_report_publications", "contract_version")
    op.drop_column("diagnostic_report_publications", "consumer_state")
