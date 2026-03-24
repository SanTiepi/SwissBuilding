import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

# ---------------------------------------------------------------------------
# Prework trigger sub-schema
# ---------------------------------------------------------------------------

PreworkTriggerType = Literal[
    "amiante_check",
    "pcb_check",
    "lead_check",
    "hap_check",
    "radon_check",
    "pfas_check",
]

PreworkTriggerUrgency = Literal["low", "medium", "high"]

# Maps readiness check IDs to the prework trigger they imply.
# Only pollutant-related checks are eligible.
_CHECK_TO_TRIGGER: dict[str, tuple[PreworkTriggerType, str]] = {
    "all_pollutants_evaluated": ("amiante_check", "Missing pollutant evaluation may include asbestos"),
    "suva_notification": ("amiante_check", "SUVA notification required — asbestos diagnostic needed"),
    "cfst_work_category": ("amiante_check", "CFST work category undetermined — asbestos assessment needed"),
    "pfas_assessment": ("pfas_check", "PFAS environmental assessment required"),
}

# Pollutant names found in check details → trigger type
_POLLUTANT_TRIGGER_MAP: dict[str, PreworkTriggerType] = {
    "asbestos": "amiante_check",
    "pcb": "pcb_check",
    "lead": "lead_check",
    "hap": "hap_check",
    "radon": "radon_check",
    "pfas": "pfas_check",
}


class PreworkTrigger(BaseModel):
    """A deterministic signal that a specific pre-work diagnostic is needed."""

    trigger_type: PreworkTriggerType
    reason: str
    urgency: PreworkTriggerUrgency
    source_check: str


def _derive_prework_triggers(
    checks: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Derive prework triggers from readiness checks (deterministic)."""
    if not checks:
        return []

    triggers: list[dict[str, Any]] = []
    seen: set[str] = set()

    for check in checks:
        check_id = check.get("id", "")
        status = check.get("status", "")
        detail = (check.get("detail") or "").lower()

        # Skip checks that are not failing / blocking
        if status not in ("fail",):
            continue

        # 1. Direct check-to-trigger mapping
        if check_id in _CHECK_TO_TRIGGER:
            trigger_type, reason = _CHECK_TO_TRIGGER[check_id]
            if trigger_type not in seen:
                seen.add(trigger_type)
                triggers.append(
                    {
                        "trigger_type": trigger_type,
                        "reason": reason,
                        "urgency": "high" if check.get("required", True) else "medium",
                        "source_check": check_id,
                    }
                )

        # 2. Detect missing pollutants from the "all_pollutants_evaluated" detail
        if check_id == "all_pollutants_evaluated" and "missing" in detail:
            for pollutant, ttype in _POLLUTANT_TRIGGER_MAP.items():
                if pollutant in detail and ttype not in seen:
                    seen.add(ttype)
                    triggers.append(
                        {
                            "trigger_type": ttype,
                            "reason": f"Missing {pollutant} evaluation — diagnostic required",
                            "urgency": "high",
                            "source_check": check_id,
                        }
                    )

        # 3. Positive-samples-classified check implies pollutant prework
        if check_id == "positive_samples_classified" and "amiante_check" not in seen:
            seen.add("amiante_check")
            triggers.append(
                {
                    "trigger_type": "amiante_check",
                    "reason": "Positive samples not fully classified — review needed",
                    "urgency": "high",
                    "source_check": check_id,
                }
            )

    return triggers


# ---------------------------------------------------------------------------
# CRUD schemas
# ---------------------------------------------------------------------------


class ReadinessAssessmentCreate(BaseModel):
    readiness_type: str
    status: str
    score: float | None = None
    checks_json: list[dict[str, Any]] | None = None
    blockers_json: list[dict[str, Any]] | None = None
    conditions_json: list[dict[str, Any]] | None = None
    valid_until: datetime | None = None
    notes: str | None = None


class ReadinessAssessmentUpdate(BaseModel):
    readiness_type: str | None = None
    status: str | None = None
    score: float | None = None
    checks_json: list[dict[str, Any]] | None = None
    blockers_json: list[dict[str, Any]] | None = None
    conditions_json: list[dict[str, Any]] | None = None
    valid_until: datetime | None = None
    notes: str | None = None


class ReadinessAssessmentRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    readiness_type: str
    status: str
    score: float | None
    checks_json: list[dict[str, Any]] | None
    blockers_json: list[dict[str, Any]] | None
    conditions_json: list[dict[str, Any]] | None
    prework_triggers: list[PreworkTrigger] = []
    assessed_at: datetime
    valid_until: datetime | None
    assessed_by: uuid.UUID | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _populate_prework_triggers(self) -> "ReadinessAssessmentRead":
        """Derive prework triggers deterministically from checks_json."""
        if not self.prework_triggers:
            raw = _derive_prework_triggers(self.checks_json)
            self.prework_triggers = [PreworkTrigger(**t) for t in raw]
        return self
