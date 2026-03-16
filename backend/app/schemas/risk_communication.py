"""
SwissBuildingOS - Risk Communication Schemas

Pydantic v2 schemas for risk communication outputs:
occupant notices, worker safety briefings, stakeholder notifications,
and communication audit logs.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Occupant Notice
# ---------------------------------------------------------------------------


class OccupantNoticeSection(BaseModel):
    title: str
    content: str


class OccupantNotice(BaseModel):
    building_id: UUID
    generated_at: datetime
    language: str = "fr"
    overall_risk_level: str
    sections: list[OccupantNoticeSection]
    situation: str
    risk_level_explanation: str
    precautions: list[str]
    planned_actions: list[str]
    contacts: list[str]


# ---------------------------------------------------------------------------
# Worker Safety Briefing
# ---------------------------------------------------------------------------


class PPERequirement(BaseModel):
    equipment: str
    standard: str
    mandatory: bool = True


class ZoneBriefing(BaseModel):
    zone: str
    pollutants_present: list[str]
    work_category: str  # minor / medium / major (CFST 6503)
    ppe_requirements: list[PPERequirement]
    work_restrictions: list[str]


class DecontaminationStep(BaseModel):
    step_number: int
    description: str


class WorkerSafetyBriefing(BaseModel):
    building_id: UUID
    generated_at: datetime
    cfst_reference: str = "CFST 6503"
    overall_work_category: str
    zones: list[ZoneBriefing]
    emergency_procedures: list[str]
    decontamination_steps: list[DecontaminationStep]
    general_ppe: list[PPERequirement]


# ---------------------------------------------------------------------------
# Stakeholder Notification
# ---------------------------------------------------------------------------


class StakeholderAction(BaseModel):
    action: str
    deadline: str | None = None
    priority: str = "medium"


class StakeholderNotification(BaseModel):
    building_id: UUID
    generated_at: datetime
    audience: str  # owner / tenant / authority / insurer
    summary: str
    key_facts: list[str]
    implications: list[str]
    required_actions: list[StakeholderAction]
    timeline: str | None = None
    detail_level: str  # brief / standard / detailed


# ---------------------------------------------------------------------------
# Communication Log
# ---------------------------------------------------------------------------


class CommunicationLogEntry(BaseModel):
    id: str
    communication_type: str
    audience: str | None = None
    generated_at: datetime
    summary: str

    model_config = ConfigDict(from_attributes=True)


class CommunicationLog(BaseModel):
    building_id: UUID
    total_count: int
    entries: list[CommunicationLogEntry]
