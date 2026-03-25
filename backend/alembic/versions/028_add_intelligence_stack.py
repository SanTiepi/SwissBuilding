"""Add intelligence stack: ai_rule_patterns + alter ai_extraction_logs

Revision ID: 028_add_intel_stack
Revises: 027_add_growth_stack
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "028_add_intel_stack"
down_revision: str | None = "027_add_growth_stack"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # AIRulePattern
    op.create_table(
        "ai_rule_patterns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pattern_type", sa.String(50), nullable=False),
        sa.Column("source_entity_type", sa.String(50), nullable=False),
        sa.Column("rule_key", sa.String(200), nullable=False),
        sa.Column("rule_definition", sa.JSON, nullable=True),
        sa.Column("sample_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_confirmed_at", sa.DateTime, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_ai_rule_patterns_type", "ai_rule_patterns", ["pattern_type"])
    op.create_index("idx_ai_rule_patterns_key", "ai_rule_patterns", ["rule_key"])

    # Add provider metadata to ai_extraction_logs
    op.add_column("ai_extraction_logs", sa.Column("provider_name", sa.String(50), nullable=True))
    op.add_column("ai_extraction_logs", sa.Column("model_version", sa.String(50), nullable=True))
    op.add_column("ai_extraction_logs", sa.Column("prompt_version", sa.String(20), nullable=True))
    op.add_column("ai_extraction_logs", sa.Column("latency_ms", sa.Integer, nullable=True))
    op.add_column("ai_extraction_logs", sa.Column("error_message", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("ai_extraction_logs", "error_message")
    op.drop_column("ai_extraction_logs", "latency_ms")
    op.drop_column("ai_extraction_logs", "prompt_version")
    op.drop_column("ai_extraction_logs", "model_version")
    op.drop_column("ai_extraction_logs", "provider_name")
    op.drop_index("idx_ai_rule_patterns_key", table_name="ai_rule_patterns")
    op.drop_index("idx_ai_rule_patterns_type", table_name="ai_rule_patterns")
    op.drop_table("ai_rule_patterns")
