"""Add backbone FK columns to existing models

Revision ID: 006_add_backbone_fks
Revises: 005_add_backbone_tables
Create Date: 2026-03-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "006_add_backbone_fks"
down_revision: str | None = "005_add_backbone_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Building: add organization_id
    op.add_column("buildings", sa.Column("organization_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_buildings_organization_id",
        "buildings",
        "organizations",
        ["organization_id"],
        ["id"],
    )

    # Organization: add contact_person_id
    op.add_column(
        "organizations",
        sa.Column("contact_person_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_organizations_contact_person_id",
        "organizations",
        "contacts",
        ["contact_person_id"],
        ["id"],
    )

    # User: add linked_contact_id
    op.add_column("users", sa.Column("linked_contact_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_users_linked_contact_id",
        "users",
        "contacts",
        ["linked_contact_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_linked_contact_id", "users", type_="foreignkey")
    op.drop_column("users", "linked_contact_id")

    op.drop_constraint("fk_organizations_contact_person_id", "organizations", type_="foreignkey")
    op.drop_column("organizations", "contact_person_id")

    op.drop_constraint("fk_buildings_organization_id", "buildings", type_="foreignkey")
    op.drop_column("buildings", "organization_id")
