#!/usr/bin/env python3
"""Giant file regression guard. Warns on files exceeding size thresholds.

Scans key directories and flags files that have grown beyond doctrinal limits.
Known exceptions (justified large files) are listed explicitly.

Exit code 0 = pass (no NEW violations beyond exceptions), 1 = fail.
"""

import glob
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Thresholds: glob pattern -> max lines
THRESHOLDS = {
    "backend/app/services/*.py": 500,
    "backend/app/models/*.py": 300,
    "frontend/src/pages/*.tsx": 800,
    "frontend/src/components/**/*.tsx": 600,
    "backend/app/seeds/*.py": 400,
    "backend/app/api/*.py": 300,
}

# Known exceptions: pre-existing files that exceed thresholds.
# The guard's job is to catch NEW violations, not police existing debt.
# Each entry is (relative path with forward slashes, justification).
EXCEPTIONS = {
    # --- backend/app/api/ (threshold 300) ---
    "backend/app/api/decision_replay.py": "pre-existing",
    "backend/app/api/diagnostics.py": "pre-existing",
    "backend/app/api/exchange_hardening.py": "pre-existing",
    "backend/app/api/rituals.py": "pre-existing",
    "backend/app/api/router.py": "hub file - all route registrations",
    "backend/app/api/technical_plans.py": "pre-existing",
    "backend/app/api/truth_api.py": "truth exchange API v1",
    # --- backend/app/models/ (threshold 300) ---
    "backend/app/models/__init__.py": "hub file - 62 model re-exports",
    # --- backend/app/seeds/ (threshold 400) ---
    "backend/app/seeds/seed_bc_ops.py": "pre-existing",
    "backend/app/seeds/seed_canonical_cycle.py": "pre-existing",
    "backend/app/seeds/seed_data.py": "master seed dataset",
    "backend/app/seeds/seed_demo_authority.py": "pre-existing",
    "backend/app/seeds/seed_demo_enrich.py": "pre-existing",
    "backend/app/seeds/seed_demo_prospect.py": "pre-existing",
    "backend/app/seeds/seed_demo_workspace.py": "pre-existing",
    "backend/app/seeds/seed_diagnostic_integration.py": "pre-existing",
    "backend/app/seeds/seed_prospect_scenario.py": "G2 prospect seed — 5 buildings, data-heavy, justified",
    "backend/app/seeds/seed_jurisdictions.py": "pre-existing",
    "backend/app/seeds/seed_procedure_templates.py": "pre-existing",
    "backend/app/seeds/seed_real_buildings.py": "pre-existing",
    "backend/app/seeds/seed_source_registry.py": "pre-existing",
    # --- backend/app/services/ (threshold 500) ---
    "backend/app/services/access_control_service.py": "pre-existing",
    "backend/app/services/action_aggregation_service.py": "pre-existing",
    "backend/app/services/address_preview_service.py": "pre-existing",
    "backend/app/services/audience_pack_service.py": "pre-existing",
    "backend/app/services/audit_readiness_service.py": "pre-existing",
    "backend/app/services/authority_extraction_service.py": "pre-existing",
    "backend/app/services/authority_pack_service.py": "pre-existing",
    "backend/app/services/building_age_analysis_service.py": "pre-existing",
    "backend/app/services/building_certification_service.py": "pre-existing",
    "backend/app/services/building_enrichment_service.py": "orchestrates full enrichment pipeline",
    "backend/app/services/building_health_index_service.py": "pre-existing",
    "backend/app/services/building_life_service.py": "pre-existing",
    "backend/app/services/change_tracker_service.py": "pre-existing",
    "backend/app/services/climate_opportunity_service.py": "pre-existing",
    "backend/app/services/completeness_engine.py": "pre-existing",
    "backend/app/services/compliance_calendar_service.py": "pre-existing",
    "backend/app/services/compliance_gap_service.py": "pre-existing",
    "backend/app/services/compliance_timeline_service.py": "pre-existing",
    "backend/app/services/constraint_graph_service.py": "pre-existing",
    "backend/app/services/contract_extraction_service.py": "pre-existing",
    "backend/app/services/partner_submission_service.py": "governed partner submission flows (diagnostic + quote + ack)",
    "backend/app/services/passport_envelope_service.py": "sovereign passport lifecycle + transfer + diff",
    "backend/app/services/identity_chain_service.py": "canonical identity chain + reliability-grade (fallback/freshness/drift)",
    "backend/app/services/subsidy_source_service.py": "subsidy programs VD/GE/FR + reliability-grade (fallback/freshness/validation)",
    "backend/app/services/cantonal_procedure_source_service.py": "cantonal authorities VD/GE/FR + reliability-grade (fallback/freshness/validation)",
    "backend/app/services/dossier_workflow_service.py": "G1 wedge workflow — 7 lifecycle methods",
    "backend/app/services/pilot_scorecard_service.py": "G2 pilot scorecard — derives from 6 data sources",
    "backend/app/services/today_service.py": "today feed + weekly_focus (22 lines over, marginal)",
    "backend/app/services/transaction_workflow_service.py": "T1 transaction readiness orchestrator",
    "backend/app/services/pdf_generator_service.py": "P1 PDF generation (reportlab, 25 lines over, marginal)",
    "backend/app/services/insurance_workflow_service.py": "I1 insurance readiness orchestrator",
    "backend/app/services/cost_benefit_analysis_service.py": "pre-existing",
    "backend/app/services/counterfactual_analysis_service.py": "pre-existing",
    "backend/app/services/cross_building_pattern_service.py": "pre-existing",
    "backend/app/services/decision_replay_service.py": "pre-existing",
    "backend/app/services/diagnostic_extraction_service.py": "pre-existing",
    "backend/app/services/document_template_service.py": "pre-existing",
    "backend/app/services/dossier_service.py": "pre-existing",
    "backend/app/services/due_diligence_service.py": "pre-existing",
    "backend/app/services/environmental_impact_service.py": "pre-existing",
    "backend/app/services/evidence_chain_service.py": "pre-existing",
    "backend/app/services/freshness_watch_service.py": "pre-existing",
    "backend/app/services/handoff_pack_service.py": "pre-existing",
    "backend/app/services/incident_response_service.py": "pre-existing",
    "backend/app/services/instant_card_service.py": "pre-existing",
    "backend/app/services/insurance_risk_assessment_service.py": "pre-existing",
    "backend/app/services/intent_service.py": "pre-existing",
    "backend/app/services/knowledge_gap_service.py": "pre-existing",
    "backend/app/services/memory_transfer_service.py": "pre-existing",
    "backend/app/services/monitoring_plan_service.py": "pre-existing",
    "backend/app/services/occupancy_risk_service.py": "pre-existing",
    "backend/app/services/occupant_safety_service.py": "pre-existing",
    "backend/app/services/operational_gate_service.py": "pre-existing",
    "backend/app/services/pack_builder_service.py": "pre-existing",
    "backend/app/services/passport_exchange_service.py": "pre-existing",
    "backend/app/services/portfolio_summary_service.py": "pre-existing",
    "backend/app/services/portfolio_triage_service.py": "pre-existing",
    "backend/app/services/predictive_readiness_service.py": "pre-existing",
    "backend/app/services/priority_matrix_service.py": "pre-existing",
    "backend/app/services/project_setup_service.py": "pre-existing",
    "backend/app/services/quality_assurance_service.py": "pre-existing",
    "backend/app/services/quote_extraction_service.py": "pre-existing",
    "backend/app/services/readiness_reasoner.py": "pre-existing",
    "backend/app/services/regulatory_filing_service.py": "pre-existing",
    "backend/app/services/remediation_tracking_service.py": "pre-existing",
    "backend/app/services/renovation_sequencer_service.py": "pre-existing",
    "backend/app/services/renovation_simulator.py": "pre-existing",
    "backend/app/services/reporting_metrics_service.py": "pre-existing",
    "backend/app/services/rfq_service.py": "pre-existing",
    "backend/app/services/risk_aggregation_service.py": "pre-existing",
    "backend/app/services/risk_communication_service.py": "pre-existing",
    "backend/app/services/risk_mitigation_planner.py": "pre-existing",
    "backend/app/services/scenario_engine.py": "pre-existing",
    "backend/app/services/scenario_planning_service.py": "pre-existing",
    "backend/app/services/score_explainability_service.py": "pre-existing",
    "backend/app/services/spatial_risk_mapping_service.py": "pre-existing",
    "backend/app/services/stakeholder_notification_service.py": "pre-existing",
    "backend/app/services/stakeholder_report_service.py": "pre-existing",
    "backend/app/services/swiss_rules_spine_service.py": "legacy, decomposition planned",
    "backend/app/services/tenant_impact_service.py": "pre-existing",
    "backend/app/services/transaction_readiness_service.py": "pre-existing",
    "backend/app/services/unknowns_ledger_service.py": "pre-existing",
    "backend/app/services/ventilation_assessment_service.py": "pre-existing",
    "backend/app/services/weak_signal_watchtower.py": "pre-existing",
    "backend/app/services/work_phase_service.py": "pre-existing",
    "backend/app/services/zone_classification_service.py": "pre-existing",
    # --- frontend/src/components/ (threshold 600) ---
    "frontend/src/components/CommandPalette.tsx": "pre-existing",
    "frontend/src/components/ContradictionPanel.tsx": "pre-existing",
    "frontend/src/components/EvidencePackBuilder.tsx": "pre-existing",
    "frontend/src/components/OnboardingWizard.tsx": "pre-existing",
    "frontend/src/components/PassportCard.tsx": "pre-existing",
    "frontend/src/components/PostWorksDiffCard.tsx": "pre-existing",
    "frontend/src/components/RequalificationTimeline.tsx": "pre-existing",
    "frontend/src/components/TimeMachinePanel.tsx": "pre-existing",
    "frontend/src/components/TransferPackagePanel.tsx": "pre-existing",
    "frontend/src/components/UnknownIssuesPanel.tsx": "pre-existing",
    "frontend/src/components/building-detail/ContractsTab.tsx": "pre-existing",
    "frontend/src/components/building-detail/FormsWorkspace.tsx": "pre-existing",
    "frontend/src/components/building-detail/LeasesTab.tsx": "pre-existing",
    "frontend/src/components/building-detail/OverviewTab.tsx": "pre-existing",
    "frontend/src/components/building-detail/OwnershipTab.tsx": "pre-existing",
    "frontend/src/components/building-detail/ProjectWizard.tsx": "pre-existing",
    "frontend/src/components/building-detail/TenderTab.tsx": "pre-existing",
    "frontend/src/components/building-detail/UnknownsLedger.tsx": "pre-existing",
    "frontend/src/components/extractions/ExtractionReview.tsx": "pre-existing",
    "frontend/src/components/building-detail/DossierWorkflowPanel.tsx": "G1 wedge — full lifecycle state machine (9 stages)",
    "frontend/src/components/building-detail/TransactionReadinessPanel.tsx": "T1 transaction readiness — verdict + gaps + buyer summary",
    "frontend/src/components/building-detail/InsuranceReadinessPanel.tsx": "I1 insurance readiness — risk profile + incidents + insurer summary",
    # --- frontend/src/pages/ (threshold 800) ---
    "frontend/src/pages/Actions.tsx": "pre-existing",
    "frontend/src/pages/AdminAuditLogs.tsx": "pre-existing",
    "frontend/src/pages/AdminJurisdictions.tsx": "pre-existing",
    "frontend/src/pages/AdminUsers.tsx": "pre-existing",
    "frontend/src/pages/Assignments.tsx": "pre-existing",
    "frontend/src/pages/BuildingDetail.tsx": "pre-existing",
    "frontend/src/pages/BuildingExplorer.tsx": "pre-existing",
    "frontend/src/pages/BuildingSamples.tsx": "pre-existing",
    "frontend/src/pages/BuildingsList.tsx": "pre-existing",
    "frontend/src/pages/Campaigns.tsx": "pre-existing",
    "frontend/src/pages/CaseRoom.tsx": "pre-existing",
    "frontend/src/pages/ComplianceArtefacts.tsx": "pre-existing",
    "frontend/src/pages/Dashboard.tsx": "pre-existing",
    "frontend/src/pages/DiagnosticView.tsx": "pre-existing",
    "frontend/src/pages/Documents.tsx": "pre-existing",
    "frontend/src/pages/InterventionSimulator.tsx": "pre-existing",
    "frontend/src/pages/PortfolioCommand.tsx": "portfolio command center with heatmap + table + charts",
    "frontend/src/pages/OrganizationSettings.tsx": "pre-existing",
    "frontend/src/pages/ReadinessWallet.tsx": "pre-existing",
    "frontend/src/pages/SavedSimulations.tsx": "pre-existing",
}

# Baseline file: stores last-known violation counts for regression detection
BASELINE_PATH = REPO_ROOT / "backend" / "scripts" / "baselines" / "file_sizes_baseline.json"


def normalize_path(path: str) -> str:
    """Normalize path separators to forward slashes."""
    return path.replace("\\", "/")


def count_lines(filepath: Path) -> int:
    """Count lines in a file."""
    try:
        return sum(1 for _ in filepath.open("r", encoding="utf-8", errors="ignore"))
    except OSError:
        return 0


def scan_violations() -> list[dict]:
    """Scan all patterns and return violations."""
    violations = []

    for pattern, threshold in THRESHOLDS.items():
        full_pattern = str(REPO_ROOT / pattern)
        for filepath_str in glob.glob(full_pattern, recursive=True):
            filepath = Path(filepath_str)
            lines = count_lines(filepath)
            if lines > threshold:
                rel_path = normalize_path(str(filepath.relative_to(REPO_ROOT)))
                is_exception = rel_path in EXCEPTIONS
                violations.append(
                    {
                        "path": rel_path,
                        "lines": lines,
                        "threshold": threshold,
                        "over_by": lines - threshold,
                        "exception": is_exception,
                        "justification": EXCEPTIONS.get(rel_path),
                    }
                )

    violations.sort(key=lambda v: -v["lines"])
    return violations


def load_baseline() -> dict | None:
    """Load previous baseline if it exists."""
    if BASELINE_PATH.exists():
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return None


def save_baseline(violations: list[dict]) -> None:
    """Save current violation counts as baseline."""
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    baseline = {v["path"]: v["lines"] for v in violations}
    BASELINE_PATH.write_text(json.dumps(baseline, indent=2, sort_keys=True), encoding="utf-8")


def check_regressions(violations: list[dict], baseline: dict | None) -> list[str]:
    """Detect new violations not in baseline."""
    if baseline is None:
        return []

    regressions = []
    for v in violations:
        if v["exception"]:
            continue
        prev = baseline.get(v["path"])
        if prev is None:
            regressions.append(f"NEW violation: {v['path']} ({v['lines']} lines, threshold {v['threshold']})")
        elif v["lines"] > prev:
            regressions.append(f"GREW: {v['path']} ({prev} -> {v['lines']} lines, threshold {v['threshold']})")
    return regressions


def main() -> int:
    violations = scan_violations()
    baseline = load_baseline()

    unexcepted = [v for v in violations if not v["exception"]]
    excepted = [v for v in violations if v["exception"]]
    regressions = check_regressions(violations, baseline)

    # Pass if all violations are known exceptions and no regressions
    passed = len(unexcepted) == 0 and len(regressions) == 0

    # Save current state as baseline
    save_baseline(violations)

    result = {
        "check": "file_size_guard",
        "pass": passed,
        "total_violations": len(violations),
        "excepted_violations": len(excepted),
        "unexcepted_violations": len(unexcepted),
        "regressions": regressions,
        "warnings": [
            f"{v['path']}: {v['lines']} lines (threshold {v['threshold']}, over by {v['over_by']})" for v in unexcepted
        ],
        "excepted": [f"{v['path']}: {v['lines']} lines ({v['justification']})" for v in excepted],
    }

    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
