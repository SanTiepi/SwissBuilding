import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ObservationRiskScore(Base):
    __tablename__ = "observation_risk_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_observation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("field_observations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=True, index=True)
    risk_score = Column(Float, nullable=False, default=0.0)
    recommended_action = Column(String(50), nullable=False, default="monitor")
    urgency_level = Column(String(20), nullable=False, default="low")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    observation = relationship("FieldObservation", backref="risk_score_entry")
    building = relationship("Building", backref="observation_risk_scores")

    __table_args__ = (
        Index("idx_obs_risk_building", "building_id"),
        Index("idx_obs_risk_urgency", "urgency_level"),
        Index("idx_obs_risk_score", "risk_score"),
    )
