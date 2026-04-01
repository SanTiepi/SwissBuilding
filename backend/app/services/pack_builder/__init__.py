"""BatiConnect Pack Builder Package -- decomposed from pack_builder_service.py.

Re-exports all public names so existing imports continue to work.
"""

__all__ = [
    # pack_types
    "PACK_BUILDER_VERSION",
    "PACK_TO_PROFILE",
    "PACK_TYPES",
    # redaction
    "_FINANCIAL_FIELD_NAMES",
    "_FINANCIAL_SECTION_TYPES",
    # section_builders
    "_NEW_SECTION_BUILDERS",
    "_REDACTED_COST_MESSAGE",
    "_REDACTED_PLACEHOLDER",
    "_SECTION_NAMES",
    "_build_claims_history",
    "_build_cost_summary",
    "_build_insurance_status",
    # caveats
    "_build_pack_caveats",
    "_build_regulatory_requirements",
    "_build_risk_summary",
    "_build_safety_requirements",
    "_build_scope_summary",
    "_build_section",
    "_build_upcoming_obligations",
    "_build_work_conditions",
    "_build_zones_concerned",
    # orchestrator
    "_generate_transfer_pack",
    "_redact_item",
    "_redact_section",
    "_run_auto_conformance",
    "generate_pack",
    "list_available_packs",
]

from app.services.pack_builder.caveats import _build_pack_caveats
from app.services.pack_builder.orchestrator import (
    _generate_transfer_pack,
    _run_auto_conformance,
    generate_pack,
    list_available_packs,
)
from app.services.pack_builder.pack_types import (
    _SECTION_NAMES,
    PACK_BUILDER_VERSION,
    PACK_TO_PROFILE,
    PACK_TYPES,
)
from app.services.pack_builder.redaction import (
    _FINANCIAL_FIELD_NAMES,
    _FINANCIAL_SECTION_TYPES,
    _REDACTED_COST_MESSAGE,
    _REDACTED_PLACEHOLDER,
    _redact_item,
    _redact_section,
)
from app.services.pack_builder.section_builders import (
    _NEW_SECTION_BUILDERS,
    _build_claims_history,
    _build_cost_summary,
    _build_insurance_status,
    _build_regulatory_requirements,
    _build_risk_summary,
    _build_safety_requirements,
    _build_scope_summary,
    _build_section,
    _build_upcoming_obligations,
    _build_work_conditions,
    _build_zones_concerned,
)
