"""Add demo_scenarios, demo_runbook_steps, pilot_scorecards, pilot_metrics, case_study_templates tables

Revision ID: 018_add_demo_pilot
Revises: 015_add_proof_delivery
Create Date: 2026-03-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "018_add_demo_pilot"
down_revision: str | None = "015_add_proof_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Demo Scenarios
    op.create_table(
        "demo_scenarios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_code", sa.String(50), unique=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("persona_target", sa.String(50), nullable=False),
        sa.Column("starting_state_description", sa.Text, nullable=False),
        sa.Column("reveal_surfaces", sa.JSON, nullable=False),
        sa.Column("proof_moment", sa.Text, nullable=True),
        sa.Column("action_moment", sa.Text, nullable=True),
        sa.Column("seed_key", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Demo Runbook Steps
    op.create_table(
        "demo_runbook_steps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_id", UUID(as_uuid=True), sa.ForeignKey("demo_scenarios.id"), nullable=False, index=True),
        sa.Column("step_order", sa.Integer, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("expected_ui_state", sa.String(200), nullable=True),
        sa.Column("fallback_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Pilot Scorecards
    op.create_table(
        "pilot_scorecards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("pilot_name", sa.String(200), nullable=False),
        sa.Column("pilot_code", sa.String(50), unique=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("target_buildings", sa.Integer, nullable=True),
        sa.Column("target_users", sa.Integer, nullable=True),
        sa.Column("exit_state", sa.String(20), nullable=True),
        sa.Column("exit_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Pilot Metrics
    op.create_table(
        "pilot_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "scorecard_id", UUID(as_uuid=True), sa.ForeignKey("pilot_scorecards.id"), nullable=False, index=True
        ),
        sa.Column("dimension", sa.String(50), nullable=False),
        sa.Column("target_value", sa.Float, nullable=True),
        sa.Column("current_value", sa.Float, nullable=True),
        sa.Column("evidence_source", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("measured_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Case Study Templates
    op.create_table(
        "case_study_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("template_code", sa.String(50), unique=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("persona_target", sa.String(50), nullable=False),
        sa.Column("workflow_type", sa.String(50), nullable=False),
        sa.Column("narrative_structure", sa.JSON, nullable=False),
        sa.Column("evidence_requirements", sa.JSON, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("pilot_metrics")
    op.drop_table("pilot_scorecards")
    op.drop_table("demo_runbook_steps")
    op.drop_table("demo_scenarios")
    op.drop_table("case_study_templates")
