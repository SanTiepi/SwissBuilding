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
# Source registry — families, classes, statuses
# ---------------------------------------------------------------------------
SOURCE_FAMILIES = [
    "identity",
    "spatial",
    "constraint",
    "procedure",
    "standard",
    "commercial",
    "partner",
    "live",
    "document",
]

SOURCE_CLASSES = ["official", "observed", "commercial", "partner_fed", "derived"]

SOURCE_ACCESS_MODES = ["api", "bulk", "file", "portal", "partner", "watch_only"]

SOURCE_FRESHNESS_POLICIES = [
    "real_time",
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "event_driven",
    "on_demand",
]

SOURCE_TRUST_POSTURES = [
    "canonical_identity",
    "canonical_constraint",
    "observed_context",
    "supporting_evidence",
    "commercial_hint",
    "derived_only",
]

SOURCE_STATUSES = ["active", "degraded", "unavailable", "deprecated", "planned"]

SOURCE_PRIORITIES = ["now", "next", "later", "partner_gated"]

SOURCE_HEALTH_EVENT_TYPES = [
    "healthy",
    "degraded",
    "unavailable",
    "schema_drift",
    "timeout",
    "error",
    "recovered",
    "fallback_used",
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


# ---------------------------------------------------------------------------
# Work Families — corps de metier → procedure / authority / proof / contractor matrix
# ---------------------------------------------------------------------------

WORK_FAMILIES: dict[str, dict] = {
    "asbestos_removal": {
        "label_fr": "Desamiantage",
        "pollutant": "asbestos",
        "procedures": ["notification", "declaration", "declaration"],
        "procedure_names": [
            "Annonce SUVA",
            "Declaration cantonale polluants",
            "Plan d'elimination des dechets",
        ],
        "authorities": ["SUVA", "canton_environment", "commune"],
        "proof_required": [
            "diagnostic_amiante",
            "plan_travaux_protection",
            "notification_suva",
            "plan_elimination_dechets",
            "certification_entreprise",
        ],
        "contractor_categories": ["asbestos_specialist", "hazmat_supervisor"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_tender", "safe_to_demolish"],
        "cfst_category": "major",
        "regulatory_basis": "OTConst Art. 60a, Directive CFST 6503, OLED",
    },
    "pcb_removal": {
        "label_fr": "Elimination PCB",
        "pollutant": "pcb",
        "procedures": ["notification", "declaration", "declaration"],
        "procedure_names": [
            "Annonce SUVA",
            "Declaration cantonale polluants",
            "Plan d'elimination des dechets",
        ],
        "authorities": ["SUVA", "canton_environment"],
        "proof_required": [
            "diagnostic_pcb",
            "analyse_joints_peintures",
            "notification_suva",
            "plan_elimination_dechets",
            "bordereau_suivi_dechets",
        ],
        "contractor_categories": ["pcb_specialist", "hazmat_supervisor"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_tender", "safe_to_renovate"],
        "cfst_category": "major",
        "regulatory_basis": "ORRChim Annexe 2.15 (PCB > 50 mg/kg), OTConst Art. 60a, OLED",
    },
    "lead_removal": {
        "label_fr": "Elimination plomb",
        "pollutant": "lead",
        "procedures": ["notification", "declaration"],
        "procedure_names": [
            "Annonce SUVA",
            "Declaration cantonale polluants",
        ],
        "authorities": ["SUVA", "canton_environment"],
        "proof_required": [
            "diagnostic_plomb",
            "mesures_protection_ouvriers",
            "notification_suva",
            "analyse_peintures",
        ],
        "contractor_categories": ["lead_specialist", "hazmat_supervisor"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_tender", "safe_to_renovate"],
        "cfst_category": "medium",
        "regulatory_basis": "ORRChim Annexe 2.18 (plomb > 5000 mg/kg), OTConst Art. 60a",
    },
    "hap_removal": {
        "label_fr": "Elimination HAP",
        "pollutant": "hap",
        "procedures": ["notification", "declaration", "declaration"],
        "procedure_names": [
            "Annonce SUVA",
            "Declaration cantonale polluants",
            "Plan d'elimination des dechets",
        ],
        "authorities": ["SUVA", "canton_environment"],
        "proof_required": [
            "diagnostic_hap",
            "analyse_enrobes_etancheite",
            "notification_suva",
            "plan_elimination_dechets",
        ],
        "contractor_categories": ["hap_specialist", "hazmat_supervisor"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_tender"],
        "cfst_category": "medium",
        "regulatory_basis": "OLED, OTConst Art. 60a, ORRChim",
    },
    "radon_mitigation": {
        "label_fr": "Assainissement radon",
        "pollutant": "radon",
        "procedures": ["declaration"],
        "procedure_names": [
            "Declaration cantonale radon",
        ],
        "authorities": ["canton_health", "ofsp"],
        "proof_required": [
            "mesure_radon_long_terme",
            "rapport_assainissement",
            "mesure_controle_post_travaux",
        ],
        "contractor_categories": ["radon_specialist"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_sell", "safe_to_insure"],
        "cfst_category": None,
        "regulatory_basis": "ORaP Art. 110 (300/1000 Bq/m3), Directive OFSP radon",
    },
    "pfas_remediation": {
        "label_fr": "Remediation PFAS",
        "pollutant": "pfas",
        "procedures": ["declaration", "declaration"],
        "procedure_names": [
            "Declaration cantonale polluants",
            "Plan d'elimination des dechets",
        ],
        "authorities": ["canton_environment", "ofev"],
        "proof_required": [
            "diagnostic_pfas",
            "analyse_eau_sol",
            "plan_remediation",
            "suivi_post_remediation",
        ],
        "contractor_categories": ["pfas_specialist", "environmental_engineer"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_sell", "safe_to_finance"],
        "cfst_category": None,
        "regulatory_basis": "OSol, OEaux, Directive OFEV PFAS 2024",
    },
    "demolition": {
        "label_fr": "Demolition",
        "pollutant": None,
        "procedures": ["permit", "declaration", "notification", "declaration"],
        "procedure_names": [
            "Permis de demolir",
            "Declaration cantonale polluants",
            "Annonce SUVA",
            "Plan d'elimination des dechets",
        ],
        "authorities": ["commune", "canton_environment", "SUVA", "monuments_historiques"],
        "proof_required": [
            "permis_demolir",
            "diagnostic_polluants_complet",
            "plan_elimination_dechets",
            "notification_suva",
            "preavis_monuments",
            "enquete_publique",
        ],
        "contractor_categories": ["demolition_contractor", "asbestos_specialist", "waste_manager"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_tender", "safe_to_demolish"],
        "cfst_category": "major",
        "regulatory_basis": "LATC, OLED, OTConst Art. 60a, Directive cantonale polluants",
    },
    "renovation": {
        "label_fr": "Renovation generale",
        "pollutant": None,
        "procedures": ["permit", "declaration", "authorization"],
        "procedure_names": [
            "Permis de construire",
            "Declaration cantonale polluants",
            "Preavis monuments historiques",
        ],
        "authorities": ["commune", "canton_construction", "monuments_historiques"],
        "proof_required": [
            "permis_construire",
            "plans_architecte",
            "diagnostic_polluants",
            "descriptif_projet",
        ],
        "contractor_categories": ["general_contractor", "architect"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_tender", "safe_to_renovate"],
        "cfst_category": None,
        "regulatory_basis": "LATC, LAT, Normes SIA 118/180",
    },
    "roof_facade": {
        "label_fr": "Toiture et facades",
        "pollutant": None,
        "procedures": ["permit", "declaration"],
        "procedure_names": [
            "Permis de construire",
            "Declaration cantonale polluants",
        ],
        "authorities": ["commune", "canton_construction", "monuments_historiques"],
        "proof_required": [
            "permis_construire",
            "plans_facade_toiture",
            "diagnostic_polluants",
            "rapport_energetique",
        ],
        "contractor_categories": ["roofer", "facade_specialist", "scaffolding_contractor"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_tender"],
        "cfst_category": None,
        "regulatory_basis": "LATC, Normes SIA 232/233, MoPEC (enveloppe)",
    },
    "hvac": {
        "label_fr": "Chauffage, ventilation, climatisation",
        "pollutant": None,
        "procedures": ["permit", "declaration", "funding"],
        "procedure_names": [
            "Permis de construire simplifie",
            "Declaration installation chauffage",
            "Subvention Programme Batiments",
        ],
        "authorities": ["commune", "canton_energy", "programme_batiments"],
        "proof_required": [
            "plans_techniques_cvs",
            "bilan_energetique",
            "certificat_conformite_installation",
            "cecb",
        ],
        "contractor_categories": ["hvac_installer", "energy_engineer"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_tender", "safe_to_renovate"],
        "cfst_category": None,
        "regulatory_basis": "MoPEC, LVLEne, OPAir, Programme Batiments",
    },
    "electrical": {
        "label_fr": "Installations electriques",
        "pollutant": None,
        "procedures": ["inspection", "certification"],
        "procedure_names": [
            "Controle OIBT periodique",
            "Rapport de securite electrique (ESTI)",
        ],
        "authorities": ["esti", "organisme_controle_agree"],
        "proof_required": [
            "rapport_controle_oibt",
            "schema_electrique",
            "attestation_conformite",
            "rapport_securite_esti",
        ],
        "contractor_categories": ["electrician_ase", "electrical_inspector"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_sell", "safe_to_insure"],
        "cfst_category": None,
        "regulatory_basis": "OIBT (Ordonnance sur les installations basse tension), LIE",
    },
    "plumbing": {
        "label_fr": "Installations sanitaires",
        "pollutant": None,
        "procedures": ["permit", "inspection"],
        "procedure_names": [
            "Permis de construire simplifie",
            "Controle raccordement eau/eaux usees",
        ],
        "authorities": ["commune", "service_eaux"],
        "proof_required": [
            "plans_sanitaires",
            "attestation_raccordement",
            "rapport_conformite_eau_potable",
        ],
        "contractor_categories": ["plumber", "sanitary_engineer"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_sell"],
        "cfst_category": None,
        "regulatory_basis": "LEaux, OSEC, Normes SIA 385/386",
    },
    "fire_safety": {
        "label_fr": "Protection incendie",
        "pollutant": None,
        "procedures": ["authorization", "inspection", "certification"],
        "procedure_names": [
            "Autorisation ECA (concept protection incendie)",
            "Controle ECA periodique",
            "Certificat conformite protection incendie",
        ],
        "authorities": ["eca", "commune", "police_du_feu"],
        "proof_required": [
            "concept_protection_incendie",
            "plans_evacuation",
            "rapport_controle_eca",
            "attestation_conformite_incendie",
        ],
        "contractor_categories": ["fire_safety_engineer", "fire_protection_installer"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_sell", "safe_to_insure"],
        "cfst_category": None,
        "regulatory_basis": "Prescriptions AEAI, LPol incendie cantonale, Normes SIA",
    },
    "accessibility": {
        "label_fr": "Mise en conformite accessibilite",
        "pollutant": None,
        "procedures": ["permit", "authorization"],
        "procedure_names": [
            "Permis de construire",
            "Autorisation accessibilite (LHand)",
        ],
        "authorities": ["commune", "canton_construction", "bureau_egalite_handicapes"],
        "proof_required": [
            "plans_accessibilite",
            "rapport_conformite_lhand",
            "permis_construire",
        ],
        "contractor_categories": ["general_contractor", "accessibility_consultant"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_sell"],
        "cfst_category": None,
        "regulatory_basis": "LHand (Loi sur l'egalite pour les handicapes), Normes SIA 500",
    },
    "energy_renovation": {
        "label_fr": "Renovation energetique",
        "pollutant": None,
        "procedures": ["permit", "funding", "certification"],
        "procedure_names": [
            "Permis de construire simplifie",
            "Subvention Programme Batiments",
            "Certificat CECB",
        ],
        "authorities": ["commune", "canton_energy", "programme_batiments"],
        "proof_required": [
            "cecb_avant",
            "devis_travaux_energetiques",
            "accord_subvention",
            "justificatifs_fin_travaux",
            "cecb_apres",
        ],
        "contractor_categories": ["energy_consultant_cecb", "insulation_contractor", "hvac_installer"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_tender", "safe_to_finance"],
        "cfst_category": None,
        "regulatory_basis": "MoPEC, Loi sur le CO2, Programme Batiments, Normes SIA 380/1",
    },
    "waterproofing": {
        "label_fr": "Etancheite",
        "pollutant": None,
        "procedures": ["permit"],
        "procedure_names": [
            "Permis de construire simplifie",
        ],
        "authorities": ["commune"],
        "proof_required": [
            "plans_etancheite",
            "rapport_expertise_etancheite",
            "garantie_travaux",
        ],
        "contractor_categories": ["waterproofing_specialist", "roofer"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_insure"],
        "cfst_category": None,
        "regulatory_basis": "Normes SIA 271 (toitures plates), SIA 272 (etancheite)",
    },
    "interiors": {
        "label_fr": "Amenagements interieurs",
        "pollutant": None,
        "procedures": ["permit", "declaration"],
        "procedure_names": [
            "Permis de construire simplifie",
            "Declaration cantonale polluants",
        ],
        "authorities": ["commune"],
        "proof_required": [
            "plans_interieurs",
            "diagnostic_polluants",
            "descriptif_amenagements",
        ],
        "contractor_categories": ["general_contractor", "interior_designer"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_renovate"],
        "cfst_category": None,
        "regulatory_basis": "LATC (travaux interieurs), Normes SIA 118",
    },
    "external_works": {
        "label_fr": "Amenagements exterieurs",
        "pollutant": None,
        "procedures": ["permit"],
        "procedure_names": [
            "Permis de construire",
        ],
        "authorities": ["commune", "canton_construction"],
        "proof_required": [
            "plans_amenagement_exterieur",
            "etude_impact_environnement",
            "permis_construire",
        ],
        "contractor_categories": ["landscape_contractor", "civil_engineer"],
        "safe_to_x_implications": ["safe_to_start", "safe_to_tender"],
        "cfst_category": None,
        "regulatory_basis": "LATC, LAT, OAT",
    },
    "maintenance": {
        "label_fr": "Entretien courant",
        "pollutant": None,
        "procedures": [],
        "procedure_names": [],
        "authorities": [],
        "proof_required": [
            "carnet_entretien",
            "contrats_maintenance",
        ],
        "contractor_categories": ["building_manager", "general_contractor"],
        "safe_to_x_implications": ["safe_to_insure"],
        "cfst_category": None,
        "regulatory_basis": "Normes SIA 469 (conservation des ouvrages), CO Art. 256-259",
    },
    "transaction_transfer": {
        "label_fr": "Transaction / transfert de propriete",
        "pollutant": None,
        "procedures": ["transfer"],
        "procedure_names": [
            "Transfert immobilier (notaire/RF)",
        ],
        "authorities": ["registre_foncier", "notaire", "canton_fiscalite"],
        "proof_required": [
            "extrait_registre_foncier",
            "diagnostic_polluants",
            "cecb",
            "etat_locatif",
            "dossier_technique_complet",
            "assurance_batiment",
        ],
        "contractor_categories": ["notary", "real_estate_agent", "property_manager"],
        "safe_to_x_implications": ["safe_to_sell", "safe_to_finance"],
        "cfst_category": None,
        "regulatory_basis": "CC Art. 656 ss (registre foncier), LDFR, LFAIE, Droit cantonal notarial",
    },
    "insurance_claim": {
        "label_fr": "Sinistre / declaration assurance",
        "pollutant": None,
        "procedures": ["insurance", "declaration"],
        "procedure_names": [
            "Declaration de sinistre ECA/privee",
            "Expertise assurance",
        ],
        "authorities": ["eca", "assurance_privee"],
        "proof_required": [
            "declaration_sinistre",
            "rapport_expertise",
            "photos_degats",
            "devis_reparation",
            "police_assurance",
        ],
        "contractor_categories": ["loss_adjuster", "general_contractor", "restoration_specialist"],
        "safe_to_x_implications": ["safe_to_insure", "safe_to_start"],
        "cfst_category": None,
        "regulatory_basis": "LCA (Loi sur le contrat d'assurance), Legislation ECA cantonale",
    },
    "subsidy_funding": {
        "label_fr": "Subventions et financement",
        "pollutant": None,
        "procedures": ["funding"],
        "procedure_names": [
            "Demande de subvention (Programme Batiments / cantonal)",
        ],
        "authorities": ["canton_energy", "programme_batiments", "canton_environment"],
        "proof_required": [
            "formulaire_subvention",
            "devis_travaux",
            "cecb_ou_audit_energetique",
            "accord_prealable",
            "justificatifs_fin_travaux",
            "factures",
        ],
        "contractor_categories": ["energy_consultant_cecb", "financial_advisor"],
        "safe_to_x_implications": ["safe_to_finance", "safe_to_start"],
        "cfst_category": None,
        "regulatory_basis": "Loi sur le CO2, Programme Batiments, Legislations cantonales energie",
    },
}

# Convenience: list of all work family names
WORK_FAMILY_NAMES: list[str] = list(WORK_FAMILIES.keys())
