"""BatiConnect — Case Study Template model for reusable demo narratives."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class CaseStudyTemplate(Base):
    __tablename__ = "case_study_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_code = Column(String(50), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    persona_target = Column(String(50), nullable=False)
    workflow_type = Column(
        String(50), nullable=False
    )  # understand_building | know_blockers | produce_dossier | handle_complement | reuse_proof | portfolio_queue | transfer_building
    narrative_structure = Column(JSON, nullable=False)  # {before: str, trigger: str, after: str, proof_points: [str]}
    evidence_requirements = Column(JSON, nullable=False)  # [{type: str, source: str, required: bool}]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
