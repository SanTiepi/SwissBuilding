import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Jurisdiction(Base):
    __tablename__ = "jurisdictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False)  # "eu", "ch", "ch-vd", "ch-ge"
    name = Column(String(255), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("jurisdictions.id"), nullable=True)
    level = Column(String(20), nullable=False)  # "supranational", "country", "region", "commune"
    country_code = Column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    is_active = Column(Boolean, default=True)
    metadata_json = Column(JSON, nullable=True)  # authority names, contact info, etc.
    created_at = Column(DateTime, default=func.now())

    parent = relationship("Jurisdiction", remote_side=[id], backref="children")
    regulatory_packs = relationship("RegulatoryPack", back_populates="jurisdiction")
