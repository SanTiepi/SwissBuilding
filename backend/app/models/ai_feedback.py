"""BatiConnect — Lot 4: AIFeedback — human-in-the-loop feedback on AI outputs."""

import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class AIFeedback(Base):
    __tablename__ = "ai_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feedback_type = Column(String(30), nullable=False)  # confirm | correct | reject
    entity_type = Column(String(50), nullable=False)  # post_works_state | extraction | classification | comparison
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    original_output = Column(JSON, nullable=True)
    corrected_output = Column(JSON, nullable=True)
    ai_model = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_ai_feedback_entity", "entity_type", "entity_id"),
        Index("idx_ai_feedback_type", "feedback_type"),
        Index("idx_ai_feedback_user", "user_id"),
    )
