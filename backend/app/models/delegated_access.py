"""Adoption Loops — Enterprise rollout: tenant boundaries, delegated access grants, audit."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.sql import func

from app.database import Base


class TenantBoundary(Base):
    __tablename__ = "tenant_boundaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, unique=True)
    boundary_name = Column(String(200), nullable=False)
    allowed_building_ids = Column(JSON, nullable=True)  # null = all org buildings
    max_users = Column(Integer, nullable=True)
    max_external_viewers = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class DelegatedAccessGrant(Base):
    __tablename__ = "delegated_access_grants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    granted_to_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    granted_to_email = Column(String(200), nullable=True)
    grant_type = Column(String(30), nullable=False)  # viewer | contributor | temporary_admin | support
    scope = Column(JSON, nullable=True)  # {documents, diagnostics, procedures, financial, obligations}
    granted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)


class PrivilegedAccessEvent(Base):
    __tablename__ = "privileged_access_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=True)
    action_type = Column(
        String(50), nullable=False
    )  # grant_created | grant_revoked | support_access | admin_override | scope_change
    target_entity_type = Column(String(50), nullable=True)
    target_entity_id = Column(UUID(as_uuid=True), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=func.now())
