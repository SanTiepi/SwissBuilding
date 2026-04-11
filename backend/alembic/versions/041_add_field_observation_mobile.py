"""Add mobile field observation columns + observation_risk_scores table.

Revision ID: 041_field_observation_mobile
Revises: 040_building_passport
"""

import sqlalchemy as sa
from alembic import op

revision = "041_field_observation_mobile"
down_revision = "040_building_passport"


def upgrade() -> None:
    # Add mobile columns to field_observations
    op.add_column("field_observations", sa.Column("condition_assessment", sa.String(20), nullable=True))
    op.add_column("field_observations", sa.Column("risk_flags", sa.Text(), nullable=True))
    op.add_column("field_observations", sa.Column("photos", sa.Text(), nullable=True))
    op.add_column("field_observations", sa.Column("gps_lat", sa.Float(), nullable=True))
    op.add_column("field_observations", sa.Column("gps_lon", sa.Float(), nullable=True))
    op.add_column("field_observations", sa.Column("compass_direction", sa.String(10), nullable=True))
    op.add_column("field_observations", sa.Column("inspection_duration_minutes", sa.Integer(), nullable=True))
    op.add_column("field_observations", sa.Column("ai_observation_summary", sa.Text(), nullable=True))
    op.add_column("field_observations", sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("field_observations", sa.Column("observer_name", sa.String(255), nullable=True))

    # Create observation_risk_scores table
    op.create_table(
        "observation_risk_scores",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "field_observation_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("field_observations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "building_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("buildings.id"),
            nullable=True,
        ),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("recommended_action", sa.String(50), nullable=False, server_default="monitor"),
        sa.Column("urgency_level", sa.String(20), nullable=False, server_default="low"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_obs_risk_building", "observation_risk_scores", ["building_id"])
    op.create_index("idx_obs_risk_urgency", "observation_risk_scores", ["urgency_level"])
    op.create_index("idx_obs_risk_score", "observation_risk_scores", ["risk_score"])


def downgrade() -> None:
    op.drop_index("idx_obs_risk_score", "observation_risk_scores")
    op.drop_index("idx_obs_risk_urgency", "observation_risk_scores")
    op.drop_index("idx_obs_risk_building", "observation_risk_scores")
    op.drop_table("observation_risk_scores")

    op.drop_column("field_observations", "observer_name")
    op.drop_column("field_observations", "ai_generated")
    op.drop_column("field_observations", "ai_observation_summary")
    op.drop_column("field_observations", "inspection_duration_minutes")
    op.drop_column("field_observations", "compass_direction")
    op.drop_column("field_observations", "gps_lon")
    op.drop_column("field_observations", "gps_lat")
    op.drop_column("field_observations", "photos")
    op.drop_column("field_observations", "risk_flags")
    op.drop_column("field_observations", "condition_assessment")
