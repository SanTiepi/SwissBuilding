"""BatiConnect — CounterfactualScenario: persisted what-if scenario for a building.

Evaluates different futures: do nothing, postpone, phase, widen/reduce scope,
sell before/after works, insure before/after, funding timing, alternative approach.
All projections consume canonical truth (passport, completeness, readiness, trust)
and are clearly marked as projections, not truth.
"""

import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.database import Base

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCENARIO_TYPES = (
    "do_nothing",
    "postpone",
    "phase",
    "widen_scope",
    "reduce_scope",
    "sell_before_works",
    "sell_after_works",
    "insure_before",
    "insure_after",
    "different_sequence",
    "funding_timing",
    "alternative_approach",
)

SCENARIO_STATUSES = ("draft", "evaluated", "compared", "archived")


class CounterfactualScenario(Base):
    """A what-if scenario for a building or case.

    Scenarios consume canonical truth (passport, completeness, readiness, trust,
    cost) to project alternative futures.  Projections are clearly marked as
    projections, not truth.
    """

    __tablename__ = "counterfactual_scenarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id"), nullable=False, index=True)
    case_id = Column(UUID(as_uuid=True), ForeignKey("building_cases.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    scenario_type = Column(String(50), nullable=False)  # see SCENARIO_TYPES
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Assumptions (JSON dict)
    # e.g. {"delay_months": 6, "scope_change": "remove_basement", "funding_scenario": "with_subsidy"}
    assumptions = Column(JSON, nullable=True)

    # Projected outcomes (all clearly projections)
    projected_grade = Column(String(2), nullable=True)  # A-F
    projected_completeness = Column(Float, nullable=True)
    projected_readiness = Column(JSON, nullable=True)  # {"safe_to_start": "blocked", ...}
    projected_cost_chf = Column(Float, nullable=True)
    projected_risk_level = Column(String(20), nullable=True)
    projected_timeline_months = Column(Integer, nullable=True)

    # Baseline snapshot at evaluation time
    baseline_grade = Column(String(2), nullable=True)
    baseline_cost_chf = Column(Float, nullable=True)

    # Trade-offs (JSON arrays)
    advantages = Column(JSON, nullable=True)  # ["lower cost", "faster timeline"]
    disadvantages = Column(JSON, nullable=True)  # ["higher risk", "incomplete readiness"]
    risk_tradeoffs = Column(JSON, nullable=True)  # [{"risk": ..., "probability": ..., "impact": ...}]

    # Opportunity windows
    optimal_window_start = Column(Date, nullable=True)
    optimal_window_end = Column(Date, nullable=True)
    window_reason = Column(String(500), nullable=True)

    # Status
    status = Column(String(20), nullable=False, default="draft")  # see SCENARIO_STATUSES

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    building = relationship("Building")
    case = relationship("BuildingCase", foreign_keys=[case_id])
    organization = relationship("Organization")
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("idx_counterfactual_scenarios_building_id", "building_id"),
        Index("idx_counterfactual_scenarios_org_id", "organization_id"),
        Index("idx_counterfactual_scenarios_status", "status"),
        Index("idx_counterfactual_scenarios_type", "scenario_type"),
    )
