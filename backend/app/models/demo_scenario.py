"""BatiConnect — Demo Scenario + Runbook Step models for guided demonstrations."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base


class DemoScenario(Base):
    __tablename__ = "demo_scenarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_code = Column(String(50), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    persona_target = Column(
        String(50), nullable=False
    )  # property_manager | owner | authority | insurer | contractor | fiduciary
    starting_state_description = Column(Text, nullable=False)
    reveal_surfaces = Column(
        JSON, nullable=False
    )  # e.g. ["ControlTower","ProcedureCard","AuthorityRoom","PassportCard"]
    proof_moment = Column(Text, nullable=True)
    action_moment = Column(Text, nullable=True)
    seed_key = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    runbook_steps = relationship("DemoRunbookStep", back_populates="scenario", order_by="DemoRunbookStep.step_order")


class DemoRunbookStep(Base):
    __tablename__ = "demo_runbook_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("demo_scenarios.id"), nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    expected_ui_state = Column(String(200), nullable=True)
    fallback_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())

    scenario = relationship("DemoScenario", back_populates="runbook_steps")
