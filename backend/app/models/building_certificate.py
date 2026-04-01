"""BuildingCertificate model — signed, verifiable certificate of building state.

The BatiConnect Certificate is the first monetizable proof-of-state product.
It can be presented to insurance, banks, authorities, or buyers, and verified
via a public endpoint using its certificate_id.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class BuildingCertificate(Base):
    __tablename__ = "building_certificates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certificate_number = Column(String(30), unique=True, nullable=False)

    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    requested_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # standard | authority | transaction
    certificate_type = Column(String(30), nullable=False, default="standard")

    # Cached scores at time of issuance
    evidence_score = Column(Integer, nullable=True)
    passport_grade = Column(String(2), nullable=True)

    # Full certificate payload
    content_json = Column(JSON, nullable=False)
    integrity_hash = Column(String(64), nullable=False)
    previous_hash = Column(String(64), nullable=True)

    # Lifecycle
    issued_at = Column(DateTime, nullable=False, default=func.now())
    valid_until = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="active")  # active | expired | revoked

    created_at = Column(DateTime, default=func.now())

    # Relationships
    building = relationship("Building")
    requested_by = relationship("User")

    __table_args__ = (
        Index("idx_building_certificates_building_id", "building_id"),
        Index("idx_building_certificates_status", "status"),
        Index("idx_building_certificates_number", "certificate_number"),
    )
