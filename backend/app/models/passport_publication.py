"""BatiConnect — Passport Publication model.

Tracks published passport/pack deliveries to external audiences.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PassportPublication(Base):
    __tablename__ = "passport_publications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    contract_version_id = Column(
        UUID(as_uuid=True), ForeignKey("exchange_contract_versions.id"), nullable=False, index=True
    )
    audience_type = Column(String(30), nullable=False)
    publication_type = Column(String(50), nullable=False)
    pack_id = Column(UUID(as_uuid=True), nullable=True)
    content_hash = Column(String(64), nullable=False)  # SHA-256
    published_at = Column(DateTime, nullable=False, default=func.now())
    published_by_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    published_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    delivery_state = Column(
        String(20), nullable=False, default="draft"
    )  # draft | published | delivered | acknowledged | superseded
    superseded_by_id = Column(UUID(as_uuid=True), ForeignKey("passport_publications.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    contract_version = relationship("ExchangeContractVersion")
