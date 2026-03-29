#!/usr/bin/env python3
"""API route registry. Classifies all API routes as canonical/projection/compatibility/exchange.

Parses router.py to extract all registered API modules, classifies each,
and outputs a structured registry with pass/fail.

Exit code 0 = pass (all modules classified), 1 = fail (unknown modules detected).
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ROUTER_PATH = REPO_ROOT / "backend" / "app" / "api" / "router.py"

# Classification buckets.
# Canonical: core BatiConnect domain modules (truth system, building intelligence)
CANONICAL = {
    "building_cases",
    "building_truth",
    "building_changes",
    "building_life",
    "intents",
    "passport_envelopes",
    "passport_envelope_diff",
    "rituals",
    "procedures",
    "forms",
    "today",
    "action_queue",
    "consequences",
    "invalidations",
    "review_queue",
    "source_registry",
    "portfolio_command",
    "building_dashboard",
    "decision_view",
    "completion_workspace",
    "pack_builder",
    "pack_impact",
    "unknowns_ledger",
    "evidence_chain",
    "evidence_graph",
    "evidence_summary",
    "field_observations",
    "extractions",
    "identity_chain",
    "digital_vault",
    "artifact_custody",
    "dossier_workflow",
    "renovation_readiness",
    "pilot_scorecard",
    "transaction_workflow",
    "pack_export",
    "insurance_readiness",
}

# Compatibility: frozen surfaces kept for backward compat
COMPATIBILITY = {
    "change_signals",
}

# Exchange: external-facing API surfaces
EXCHANGE = {
    "truth_api",
    "exchange",
    "exchange_hardening",
    "shared_links",
    "erp_integration",
    "transfer",
    "partner_contracts",
    "partner_submissions",
}

# Projection: read-only views / dashboards / summaries
PROJECTION = {
    "passport",
    "passport_export",
    "completeness",
    "readiness",
    "trust_scores",
    "data_quality",
    "data_provenance",
    "instant_card",
    "portfolio_summary",
    "portfolio_trends",
    "portfolio_triage",
    "evidence_packs",
    "compliance_summary",
    "remediation_summary",
    "compliance_artefacts",
    "compliance_calendar",
    "compliance_gap",
    "compliance_timeline",
    "conformance",
    "building_health_index",
    "building_quality",
    "building_lifecycle",
    "building_comparison",
    "building_snapshots",
    "building_benchmark",
    "building_age_analysis",
    "building_clustering",
    "building_genealogy",
    "building_elements",
    "building_certifications",
    "building_valuations",
    "campaign_tracking",
    "predictive_readiness",
    "timeline",
    "timeline_enrichment",
    "requalification",
    "transaction_readiness",
    "anomaly_detection",
    "cross_building_pattern",
    "weak_signals",
    "constraint_graph",
    "decision_replay",
    "freshness_watch",
    "knowledge_gap",
    "reporting_metrics",
    "value_ledger",
    "risk_aggregation",
    "priority_matrix",
    "diagnostic_quality",
    "execution_quality",
    "expert_reviews",
    "indispensability",
    "dossier_completion",
    "multi_org_dashboard",
    "spatial_enrichment",
    "geo_context",
    "climate_exposure",
    "score_explainability",
    "energy_performance",
    "environmental_impact",
}

# Admin: operator/admin-only surfaces
ADMIN = {
    "auth",
    "users",
    "organizations",
    "invitations",
    "audit_logs",
    "audit_export",
    "audit_readiness",
    "jurisdictions",
    "access_control",
    "gdpr",
    "notification_rules",
    "notification_preferences",
    "notification_digest",
    "notifications",
    "background_jobs",
    "demo_path",
    "demo_pilot",
    "expansion",
    "rollout",
    "public_sector",
    "onboarding",
    "marketplace",
    "marketplace_rfq",
    "marketplace_trust",
    "partner_trust",
    "remediation_intelligence",
    "swiss_rules_watch",
    "admin_contributor_gateway",
}

# Operational: CRUD / workflow modules that serve specific domain operations
OPERATIONAL = {
    "buildings",
    "diagnostics",
    "samples",
    "events",
    "documents",
    "document_inbox",
    "document_classification",
    "document_completeness",
    "document_templates",
    "risk_analysis",
    "pollutant_inventory",
    "pollutant_map",
    "actions",
    "exports",
    "assignments",
    "obligations",
    "workspace",
    "zones",
    "zone_classification",
    "zone_safety",
    "materials",
    "material_inventory",
    "material_recommendations",
    "intake",
    "interventions",
    "project_setup",
    "leases",
    "contact_lookup",
    "contracts",
    "ownership",
    "technical_plans",
    "evidence",
    "dossier",
    "search",
    "campaigns",
    "capex_planning",
    "control_tower_v2",
    "permit_procedures",
    "permit_tracking",
    "post_works",
    "rfq",
    "contractor_acknowledgment",
    "contractor_matching",
    "saved_simulations",
    "bulk_operations",
    "sample_optimization",
    "sampling_planner",
    "authority_packs",
    "audience_packs",
    "package_presets",
    "memory_transfers",
    "remediation_post_works",
    "remediation_workspace",
    "remediation_costs",
    "remediation_tracking",
    "proof_delivery",
    "co_ownership",
    "commitments",
    "unknowns",
    "handoff_pack",
    "portfolio",
    "financial_entries",
    "owner_ops",
    "budget_tracking",
    "subsidy_tracking",
    "regulatory_change_impact",
    "regulatory_deadlines",
    "regulatory_filing",
    "regulatory_watch",
    "cost_benefit_analysis",
    "counterfactual_analysis",
    "due_diligence",
    "quality_assurance",
    "renovation_sequencer",
    "scenario_engine",
    "scenario_planning",
    "risk_communication",
    "risk_mitigation",
    "insurance_risk_assessment",
    "maintenance_forecast",
    "monitoring_plan",
    "occupant_safety",
    "occupancy_risks",
    "operational_gates",
    "spatial_risk_mapping",
    "stakeholder_dashboard",
    "stakeholder_notifications",
    "stakeholder_report",
    "waste_management",
    "tenant_impact",
    "diagnostic_integration",
    "incident_response",
    "incidents",
    "eco_clauses",
    "ecosystem_engagements",
    "ventilation_assessment",
    "warranty_obligations",
    "sensor_integration",
    "work_families",
    "work_phases",
    "lab_result",
    "workflow_orchestration",
    "portfolio_optimization",
    "action_queue",
}


def extract_api_modules(router_content: str) -> list[dict]:
    """Parse router.py to extract all include_router calls."""
    # Match: api_router.include_router(module_name.router, prefix="...", tags=["..."])
    pattern = re.compile(
        r"api_router\.include_router\(\s*(\w+)\.router\s*,"
        r'\s*prefix="([^"]*)"'
        r'\s*,\s*tags=\["([^"]+)"\]'
    )
    modules = []
    for match in pattern.finditer(router_content):
        modules.append(
            {
                "module": match.group(1),
                "prefix": match.group(2),
                "tag": match.group(3),
            }
        )
    return modules


def classify_api_module(module_name: str) -> str:
    """Classify an API module into a category."""
    if module_name in CANONICAL:
        return "canonical"
    if module_name in COMPATIBILITY:
        return "compatibility"
    if module_name in EXCHANGE:
        return "exchange"
    if module_name in PROJECTION:
        return "projection"
    if module_name in ADMIN:
        return "admin"
    if module_name in OPERATIONAL:
        return "operational"
    return "unknown"


def main() -> int:
    if not ROUTER_PATH.exists():
        print(json.dumps({"check": "api_registry", "pass": False, "error": f"File not found: {ROUTER_PATH}"}))
        return 1

    content = ROUTER_PATH.read_text(encoding="utf-8")
    modules = extract_api_modules(content)

    classified = []
    unknown_modules = []
    summary = {}

    for mod in modules:
        category = classify_api_module(mod["module"])
        entry = {**mod, "category": category}
        classified.append(entry)
        summary[category] = summary.get(category, 0) + 1
        if category == "unknown":
            unknown_modules.append(mod["module"])

    passed = len(unknown_modules) == 0

    warnings = []
    if unknown_modules:
        warnings.append(
            f"{len(unknown_modules)} unclassified API module(s): {unknown_modules}. "
            "Add each to the appropriate classification bucket in check_api_registry.py."
        )

    result = {
        "check": "api_registry",
        "pass": passed,
        "total_modules": len(modules),
        "summary": summary,
        "unknown_modules": unknown_modules,
        "warnings": warnings,
        "registry": classified,
    }

    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
