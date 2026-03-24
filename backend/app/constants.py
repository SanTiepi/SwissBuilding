"""Shared business constants for SwissBuildingOS."""

# Demo credentials (local/dev only)
DEMO_ADMIN_EMAIL = "admin@swissbuildingos.ch"
DEMO_ADMIN_PASSWORD = "noob42"

# Source dataset identifiers (used in importers, seeds, and tests)
SOURCE_DATASET_VAUD_PUBLIC = "vd-public-rcb"

# Canonical sample units stored in the database and returned by the API.
SAMPLE_UNIT_PERCENT_WEIGHT = "percent_weight"
SAMPLE_UNIT_FIBERS_PER_M3 = "fibers_per_m3"
SAMPLE_UNIT_MG_PER_KG = "mg_per_kg"
SAMPLE_UNIT_NG_PER_M3 = "ng_per_m3"
SAMPLE_UNIT_UG_PER_L = "ug_per_l"
SAMPLE_UNIT_BQ_PER_M3 = "bq_per_m3"

SUPPORTED_SAMPLE_UNITS = (
    SAMPLE_UNIT_PERCENT_WEIGHT,
    SAMPLE_UNIT_FIBERS_PER_M3,
    SAMPLE_UNIT_MG_PER_KG,
    SAMPLE_UNIT_NG_PER_M3,
    SAMPLE_UNIT_UG_PER_L,
    SAMPLE_UNIT_BQ_PER_M3,
)

# ---------------------------------------------------------------------------
# Action item source types
# ---------------------------------------------------------------------------
ACTION_SOURCE_RISK = "risk"
ACTION_SOURCE_DIAGNOSTIC = "diagnostic"
ACTION_SOURCE_DOCUMENT = "document"
ACTION_SOURCE_COMPLIANCE = "compliance"
ACTION_SOURCE_SIMULATION = "simulation"
ACTION_SOURCE_MANUAL = "manual"
ACTION_SOURCE_SYSTEM = "system"
ACTION_SOURCE_READINESS = "readiness"

ACTION_SOURCE_TYPES = (
    ACTION_SOURCE_RISK,
    ACTION_SOURCE_DIAGNOSTIC,
    ACTION_SOURCE_DOCUMENT,
    ACTION_SOURCE_COMPLIANCE,
    ACTION_SOURCE_SIMULATION,
    ACTION_SOURCE_MANUAL,
    ACTION_SOURCE_SYSTEM,
    ACTION_SOURCE_READINESS,
)

# ---------------------------------------------------------------------------
# Action item statuses
# ---------------------------------------------------------------------------
ACTION_STATUS_OPEN = "open"
ACTION_STATUS_IN_PROGRESS = "in_progress"
ACTION_STATUS_BLOCKED = "blocked"
ACTION_STATUS_DONE = "done"
ACTION_STATUS_DISMISSED = "dismissed"

ACTION_STATUSES = (
    ACTION_STATUS_OPEN,
    ACTION_STATUS_IN_PROGRESS,
    ACTION_STATUS_BLOCKED,
    ACTION_STATUS_DONE,
    ACTION_STATUS_DISMISSED,
)

# ---------------------------------------------------------------------------
# Action item priorities
# ---------------------------------------------------------------------------
ACTION_PRIORITY_LOW = "low"
ACTION_PRIORITY_MEDIUM = "medium"
ACTION_PRIORITY_HIGH = "high"
ACTION_PRIORITY_CRITICAL = "critical"

ACTION_PRIORITIES = (
    ACTION_PRIORITY_LOW,
    ACTION_PRIORITY_MEDIUM,
    ACTION_PRIORITY_HIGH,
    ACTION_PRIORITY_CRITICAL,
)

# ---------------------------------------------------------------------------
# Action types (system-generated)
# ---------------------------------------------------------------------------
ACTION_TYPE_CREATE_DIAGNOSTIC = "create_diagnostic"
ACTION_TYPE_ADD_SAMPLES = "add_samples"
ACTION_TYPE_UPLOAD_REPORT = "upload_report"
ACTION_TYPE_NOTIFY_SUVA = "notify_suva"
ACTION_TYPE_NOTIFY_CANTON = "notify_canton"
ACTION_TYPE_COMPLETE_DOSSIER = "complete_dossier"
ACTION_TYPE_VALIDATE_DIAGNOSTIC = "validate_diagnostic"
ACTION_TYPE_REMEDIATION = "remediation"
ACTION_TYPE_INVESTIGATION = "investigation"
ACTION_TYPE_NOTIFICATION = "notification"
ACTION_TYPE_PROCUREMENT = "procurement"
ACTION_TYPE_DOCUMENTATION = "documentation"

# ---------------------------------------------------------------------------
# Zone types
# ---------------------------------------------------------------------------
ZONE_TYPES = [
    "floor",
    "room",
    "facade",
    "roof",
    "basement",
    "staircase",
    "technical_room",
    "parking",
    "other",
]

# ---------------------------------------------------------------------------
# Building element types
# ---------------------------------------------------------------------------
ELEMENT_TYPES = [
    "wall",
    "floor",
    "ceiling",
    "pipe",
    "insulation",
    "coating",
    "window",
    "door",
    "duct",
    "structural",
    "other",
]

# ---------------------------------------------------------------------------
# Element conditions
# ---------------------------------------------------------------------------
ELEMENT_CONDITIONS = ["good", "fair", "poor", "critical", "unknown"]

# ---------------------------------------------------------------------------
# Material types
# ---------------------------------------------------------------------------
MATERIAL_TYPES = [
    "concrete",
    "fiber_cement",
    "plaster",
    "paint",
    "adhesive",
    "insulation_material",
    "sealant",
    "flooring",
    "tile",
    "wood",
    "metal",
    "glass",
    "bitumen",
    "mortar",
    "other",
]

# ---------------------------------------------------------------------------
# Material sources
# ---------------------------------------------------------------------------
MATERIAL_SOURCES = [
    "diagnostic",
    "visual_inspection",
    "documentation",
    "owner_declaration",
    "import",
]

# ---------------------------------------------------------------------------
# Intervention types
# ---------------------------------------------------------------------------
INTERVENTION_TYPES = [
    "renovation",
    "maintenance",
    "repair",
    "demolition",
    "installation",
    "inspection",
    "diagnostic",
    "asbestos_removal",
    "decontamination",
    "other",
]

# ---------------------------------------------------------------------------
# Intervention statuses
# ---------------------------------------------------------------------------
INTERVENTION_STATUSES = ["planned", "in_progress", "completed", "cancelled"]

# ---------------------------------------------------------------------------
# Technical plan types
# ---------------------------------------------------------------------------
PLAN_TYPES = [
    "floor_plan",
    "cross_section",
    "elevation",
    "technical_schema",
    "site_plan",
    "detail",
    "annotation",
    "other",
]

# ---------------------------------------------------------------------------
# Plan annotation types
# ---------------------------------------------------------------------------
PLAN_ANNOTATION_TYPES = [
    "marker",
    "zone_reference",
    "sample_location",
    "observation",
    "hazard_zone",
    "measurement_point",
]

# ---------------------------------------------------------------------------
# Evidence link source types
# ---------------------------------------------------------------------------
EVIDENCE_SOURCE_TYPES = [
    "sample",
    "diagnostic",
    "document",
    "pollutant_rule",
    "observation",
    "material",
    "intervention",
    "import",
    "manual",
]

# ---------------------------------------------------------------------------
# Evidence link target types
# ---------------------------------------------------------------------------
EVIDENCE_TARGET_TYPES = [
    "risk_score",
    "action_item",
    "recommendation",
    "compliance_result",
]

# ---------------------------------------------------------------------------
# Evidence relationship types
# ---------------------------------------------------------------------------
EVIDENCE_RELATIONSHIPS = [
    "proves",
    "supports",
    "contradicts",
    "requires",
    "triggers",
    "supersedes",
]

# ---------------------------------------------------------------------------
# Campaign types
# ---------------------------------------------------------------------------
CAMPAIGN_TYPES = ["diagnostic", "remediation", "inspection", "maintenance", "documentation", "other"]

# ---------------------------------------------------------------------------
# Campaign statuses
# ---------------------------------------------------------------------------
CAMPAIGN_STATUS_DRAFT = "draft"
CAMPAIGN_STATUS_ACTIVE = "active"
CAMPAIGN_STATUS_PAUSED = "paused"
CAMPAIGN_STATUS_COMPLETED = "completed"
CAMPAIGN_STATUS_CANCELLED = "cancelled"
CAMPAIGN_STATUSES = (
    CAMPAIGN_STATUS_DRAFT,
    CAMPAIGN_STATUS_ACTIVE,
    CAMPAIGN_STATUS_PAUSED,
    CAMPAIGN_STATUS_COMPLETED,
    CAMPAIGN_STATUS_CANCELLED,
)

# ---------------------------------------------------------------------------
# Simulation types
# ---------------------------------------------------------------------------
SIMULATION_TYPES = ["renovation", "remediation", "cost_estimate", "scenario"]

# ---------------------------------------------------------------------------
# Data quality issue types
# ---------------------------------------------------------------------------
DATA_QUALITY_ISSUE_TYPES = [
    "missing_field",
    "stale_data",
    "inconsistency",
    "duplicate",
    "format_error",
    "unverified",
]
DATA_QUALITY_SEVERITIES = ["low", "medium", "high", "critical"]
DATA_QUALITY_STATUSES = ["open", "acknowledged", "resolved", "dismissed"]
DATA_QUALITY_DETECTED_BY = ["system", "import", "manual", "agent"]

# ---------------------------------------------------------------------------
# Change signal types
# ---------------------------------------------------------------------------
CHANGE_SIGNAL_TYPES = [
    "regulation_change",
    "source_update",
    "requalification_needed",
    "evidence_stale",
    "new_data_available",
    "threshold_crossed",
]
CHANGE_SIGNAL_SEVERITIES = ["info", "warning", "action_required"]
CHANGE_SIGNAL_STATUSES = ["active", "acknowledged", "resolved", "expired"]

# ---------------------------------------------------------------------------
# Readiness types
# ---------------------------------------------------------------------------
READINESS_TYPES = [
    "safe_to_start",
    "safe_to_renovate",
    "safe_to_tender",
    "safe_to_sell",
    "safe_to_insure",
    "safe_to_finance",
    "safe_to_intervene",
    "safe_to_demolish",
]
READINESS_STATUSES = ["ready", "not_ready", "conditional", "unknown"]

# ---------------------------------------------------------------------------
# Building trust score
# ---------------------------------------------------------------------------
TRUST_SCORE_TRENDS = ["improving", "stable", "declining"]
TRUST_SCORE_ASSESSED_BY = ["system", "manual", "agent"]

# ---------------------------------------------------------------------------
# Unknown issue types
# ---------------------------------------------------------------------------
UNKNOWN_ISSUE_TYPES = [
    "uninspected_zone",
    "missing_plan",
    "unconfirmed_material",
    "undocumented_intervention",
    "incomplete_diagnostic",
    "missing_sample",
    "unverified_source",
    "accessibility_unknown",
]
UNKNOWN_ISSUE_SEVERITIES = ["low", "medium", "high", "critical"]
UNKNOWN_ISSUE_STATUSES = ["open", "acknowledged", "resolved", "accepted_risk"]

# ---------------------------------------------------------------------------
# Post-works state types
# ---------------------------------------------------------------------------
POST_WORKS_STATE_TYPES = [
    "removed",
    "remaining",
    "encapsulated",
    "treated",
    "recheck_needed",
    "unknown_after_works",
    "partially_removed",
    "newly_discovered",
]

# ---------------------------------------------------------------------------
# Transfer package
# ---------------------------------------------------------------------------
TRANSFER_PACKAGE_VERSION = "1.0"
TRANSFER_PACKAGE_SECTIONS = [
    "passport",
    "diagnostics",
    "documents",
    "interventions",
    "actions",
    "evidence",
    "contradictions",
    "unknowns",
    "snapshots",
    "completeness",
    "readiness",
    "diagnostic_publications",
]

# ---------------------------------------------------------------------------
# Pollutant types
# ---------------------------------------------------------------------------
ALL_POLLUTANTS = ("asbestos", "pcb", "lead", "hap", "radon", "pfas")

# Severity ranking (higher = more dangerous)
POLLUTANT_SEVERITY: dict[str, int] = {
    "asbestos": 5,
    "pcb": 4,
    "lead": 3,
    "hap": 2,
    "radon": 1,
    "pfas": 3,
}

# ---------------------------------------------------------------------------
# Construction era ranges
# ---------------------------------------------------------------------------
ERA_RANGES: list[tuple[str, int | None, int | None]] = [
    ("pre_1950", None, 1950),
    ("1950_1975", 1950, 1975),
    ("1975_1991", 1975, 1991),
    ("post_1991", 1991, None),
]

# ---------------------------------------------------------------------------
# Diagnostic validity years (per pollutant)
# ---------------------------------------------------------------------------
DIAGNOSTIC_VALIDITY_YEARS: dict[str, int] = {
    "asbestos": 3,
    "pcb": 5,
    "lead": 5,
    "hap": 5,
    "radon": 10,
    "full": 3,
}

_SAMPLE_UNIT_ALIASES = {
    "percent_weight": SAMPLE_UNIT_PERCENT_WEIGHT,
    "%": SAMPLE_UNIT_PERCENT_WEIGHT,
    "percent": SAMPLE_UNIT_PERCENT_WEIGHT,
    "fibers_per_m3": SAMPLE_UNIT_FIBERS_PER_M3,
    "fibres_per_m3": SAMPLE_UNIT_FIBERS_PER_M3,
    "fibers/m3": SAMPLE_UNIT_FIBERS_PER_M3,
    "fibers/m³": SAMPLE_UNIT_FIBERS_PER_M3,
    "fibres/m3": SAMPLE_UNIT_FIBERS_PER_M3,
    "fibres/m³": SAMPLE_UNIT_FIBERS_PER_M3,
    "f/m3": SAMPLE_UNIT_FIBERS_PER_M3,
    "f/m³": SAMPLE_UNIT_FIBERS_PER_M3,
    "laf/m3": SAMPLE_UNIT_FIBERS_PER_M3,
    "laf/m³": SAMPLE_UNIT_FIBERS_PER_M3,
    "mg_per_kg": SAMPLE_UNIT_MG_PER_KG,
    "mg/kg": SAMPLE_UNIT_MG_PER_KG,
    "ppm": SAMPLE_UNIT_MG_PER_KG,
    "ng_per_m3": SAMPLE_UNIT_NG_PER_M3,
    "ng/m3": SAMPLE_UNIT_NG_PER_M3,
    "ng/m³": SAMPLE_UNIT_NG_PER_M3,
    "ug_per_l": SAMPLE_UNIT_UG_PER_L,
    "ug/l": SAMPLE_UNIT_UG_PER_L,
    "µg/l": SAMPLE_UNIT_UG_PER_L,
    "μg/l": SAMPLE_UNIT_UG_PER_L,
    "bq_per_m3": SAMPLE_UNIT_BQ_PER_M3,
    "bq/m3": SAMPLE_UNIT_BQ_PER_M3,
    "bq/m³": SAMPLE_UNIT_BQ_PER_M3,
}


def _sample_unit_key(unit: str) -> str:
    return unit.strip().lower().replace("µ", "u").replace("μ", "u").replace("³", "3")


def normalize_sample_unit(unit: str | None, *, strict: bool = False) -> str | None:
    if unit is None:
        return None

    normalized = _SAMPLE_UNIT_ALIASES.get(_sample_unit_key(unit))
    if normalized is not None:
        return normalized

    if strict:
        supported = ", ".join(SUPPORTED_SAMPLE_UNITS)
        raise ValueError(f"Unsupported sample unit '{unit}'. Supported units: {supported}")

    return _sample_unit_key(unit)
