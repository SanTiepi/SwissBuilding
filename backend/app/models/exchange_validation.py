"""BatiConnect — Exchange Validation models.

ExchangeValidationReport: tracks import validation results.
ExternalRelianceSignal: tracks external consumption/acknowledgement of publications.
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class ExchangeValidationReport(Base):
    __tablename__ = "exchange_validation_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    import_receipt_id = Column(
        UUID(as_uuid=True), ForeignKey("passport_import_receipts.id"), nullable=False, index=True
    )
    schema_valid = Column(Boolean, nullable=True)
    contract_valid = Column(Boolean, nullable=True)
    version_valid = Column(Boolean, nullable=True)
    hash_valid = Column(Boolean, nullable=True)
    identity_safe = Column(Boolean, nullable=True)
    validation_errors = Column(JSON, nullable=True)
    overall_status = Column(String(20), nullable=False, default="review_required")
    validated_at = Column(DateTime, nullable=True)
    validated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())

    import_receipt = relationship("PassportImportReceipt")
    validated_by = relationship("User")


class ExternalRelianceSignal(Base):
    __tablename__ = "external_reliance_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    publication_id = Column(UUID(as_uuid=True), ForeignKey("passport_publications.id"), nullable=True, index=True)
    import_receipt_id = Column(UUID(as_uuid=True), ForeignKey("passport_import_receipts.id"), nullable=True, index=True)
    signal_type = Column(String(50), nullable=False)  # consumed|acknowledged|superseded|disputed
    partner_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=func.now())
    created_at = Column(DateTime, default=func.now())

    publication = relationship("PassportPublication")
    import_receipt = relationship("PassportImportReceipt")
    partner_org = relationship("Organization")
