"""BatiConnect — DefectTimeline model for construction defect deadline tracking.

Art. 367 al. 1bis CO: 60 calendar days from discovery to notify (since 01.01.2026).
CO 371: 5-year prescription for hidden defects, 2 years for manifest.
"""

import uuid

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import ProvenanceMixin


class DefectTimeline(ProvenanceMixin, Base):
    __tablename__ = "defect_timelines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    diagnostic_id = Column(UUID(as_uuid=True), ForeignKey("diagnostics.id"), nullable=True)

    defect_type = Column(String(30), nullable=False)  # construction | pollutant | structural | installation | other
    description = Column(Text, nullable=True)

    discovery_date = Column(Date, nullable=False)
    purchase_date = Column(Date, nullable=True)

    notification_deadline = Column(Date, nullable=False)  # computed: discovery_date + 60 days
    guarantee_type = Column(String(30), nullable=False, default="standard")  # standard | new_build_rectification
    prescription_date = Column(Date, nullable=True)  # computed from purchase_date + defect_type

    status = Column(String(20), nullable=False, default="active")  # active | notified | expired | resolved

    notified_at = Column(DateTime, nullable=True)
    notification_pdf_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    diagnostic = relationship("Diagnostic", foreign_keys=[diagnostic_id])

    __table_args__ = (
        Index("idx_defect_timelines_status", "status"),
        Index("idx_defect_timelines_deadline", "notification_deadline"),
        Index("idx_defect_timelines_type", "defect_type"),
    )
