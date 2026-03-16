import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SavedSimulation(Base):
    __tablename__ = "saved_simulations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    simulation_type = Column(String(50), nullable=False, default="renovation")

    # Input snapshot
    parameters_json = Column(JSON, nullable=False)

    # Result snapshot
    results_json = Column(JSON, nullable=False)
    total_cost_chf = Column(Float, nullable=True)
    total_duration_weeks = Column(Integer, nullable=True)
    risk_level_before = Column(String(20), nullable=True)
    risk_level_after = Column(String(20), nullable=True)

    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())

    building = relationship("Building")
