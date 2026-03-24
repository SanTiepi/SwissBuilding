import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.mixins import ProvenanceMixin


class DiagnosticMissionOrder(ProvenanceMixin, Base):
    __tablename__ = "diagnostic_mission_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    requester_org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    mission_type = Column(
        String(50), nullable=False
    )  # asbestos_full | asbestos_complement | pcb | lead | hap | radon | pfas | multi
    status = Column(String(20), default="draft")  # draft | queued | sent | acknowledged | failed | cancelled
    last_error = Column(Text, nullable=True)  # last delivery error message
    context_notes = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)  # [{name: str, url: str, type: str}]
    building_identifiers = Column(
        JSON, nullable=True
    )  # {egid: str|null, egrid: str|null, official_id: str|null, address: str|null}
    external_mission_id = Column(String(100), nullable=True)  # ID returned by Batiscan after acceptance
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    requester_org = relationship("Organization")
