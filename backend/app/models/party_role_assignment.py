import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class PartyRoleAssignment(Base):
    __tablename__ = "party_role_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    party_type = Column(String(30), nullable=False)  # contact | user | organization
    party_id = Column(UUID(as_uuid=True), nullable=False)
    entity_type = Column(
        String(30), nullable=False
    )  # building | unit | portfolio | lease | contract | intervention | diagnostic
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    role = Column(
        String(50), nullable=False
    )  # legal_owner | co_owner | tenant | manager | insurer | contractor | notary | trustee | syndic | architect | diagnostician | reviewer
    share_pct = Column(Float, nullable=True)
    valid_from = Column(Date, nullable=True)
    valid_until = Column(Date, nullable=True)
    is_primary = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("party_type", "party_id", "entity_type", "entity_id", "role", name="uq_party_role_assignment"),
        Index("idx_party_roles_entity", "entity_type", "entity_id"),
        Index("idx_party_roles_party", "party_type", "party_id"),
        Index("idx_party_roles_role", "role"),
    )
