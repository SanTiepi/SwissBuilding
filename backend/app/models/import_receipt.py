"""BatiConnect — Passport Import Receipt model.

Tracks inbound passport/pack imports from external systems.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PassportImportReceipt(Base):
    __tablename__ = "passport_import_receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=True, index=True)
    source_system = Column(String(100), nullable=False)
    contract_code = Column(String(50), nullable=False)
    contract_version = Column(Integer, nullable=False)
    import_reference = Column(String(200), nullable=True)
    imported_at = Column(DateTime, nullable=False, default=func.now())
    status = Column(String(20), nullable=False, default="received")  # received | validated | rejected | integrated
    content_hash = Column(String(64), nullable=False)  # SHA-256
    rejection_reason = Column(Text, nullable=True)
    matched_publication_id = Column(UUID(as_uuid=True), ForeignKey("passport_publications.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    building = relationship("Building")
    matched_publication = relationship("PassportPublication")
