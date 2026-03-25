import uuid

from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class MunicipalityReviewPack(Base):
    __tablename__ = "municipality_review_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    generated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    pack_version = Column(Integer, default=1)
    status = Column(String(20), default="draft")  # draft | ready | circulating | reviewed | archived
    sections = Column(JSON, nullable=True)
    content_hash = Column(String(64), nullable=True)
    review_deadline = Column(Date, nullable=True)
    circulated_to = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    building = relationship("Building")
    generated_by = relationship("User")
