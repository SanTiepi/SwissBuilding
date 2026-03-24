"""BatiConnect — Workspace Membership model.

Per-building shared access: "Organization X / User Y has role Z on Building B"
with fine-grained scope control.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base

# Valid workspace roles
WORKSPACE_ROLES = (
    "owner",
    "manager",
    "diagnostician",
    "architect",
    "authority",
    "contractor",
    "viewer",
)

# Default access scope per workspace role
DEFAULT_SCOPE_BY_ROLE: dict[str, dict[str, bool]] = {
    "owner": {
        "documents": True,
        "diagnostics": True,
        "financial": True,
        "interventions": True,
        "contracts": True,
        "leases": True,
        "ownership": True,
    },
    "manager": {
        "documents": True,
        "diagnostics": True,
        "financial": True,
        "interventions": True,
        "contracts": True,
        "leases": True,
        "ownership": True,
    },
    "diagnostician": {
        "documents": True,
        "diagnostics": True,
        "financial": False,
        "interventions": True,
        "contracts": False,
        "leases": False,
        "ownership": False,
    },
    "architect": {
        "documents": True,
        "diagnostics": True,
        "financial": False,
        "interventions": True,
        "contracts": False,
        "leases": False,
        "ownership": False,
    },
    "authority": {
        "documents": True,
        "diagnostics": True,
        "financial": False,
        "interventions": True,
        "contracts": False,
        "leases": False,
        "ownership": False,
    },
    "contractor": {
        "documents": True,
        "diagnostics": True,
        "financial": False,
        "interventions": True,
        "contracts": True,
        "leases": False,
        "ownership": False,
    },
    "viewer": {
        "documents": True,
        "diagnostics": True,
        "financial": False,
        "interventions": False,
        "contracts": False,
        "leases": False,
        "ownership": False,
    },
}


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    role = Column(
        String(30), nullable=False
    )  # owner | manager | diagnostician | architect | authority | contractor | viewer
    access_scope = Column(
        JSON, nullable=True
    )  # {documents, diagnostics, financial, interventions, contracts, leases, ownership}
    granted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime, default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    building = relationship("Building", foreign_keys=[building_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    user = relationship("User", foreign_keys=[user_id])
    granted_by = relationship("User", foreign_keys=[granted_by_user_id])

    __table_args__ = (
        Index("idx_ws_membership_building", "building_id"),
        Index("idx_ws_membership_org", "organization_id"),
        Index("idx_ws_membership_user", "user_id"),
        Index("idx_ws_membership_active", "building_id", "is_active"),
    )
