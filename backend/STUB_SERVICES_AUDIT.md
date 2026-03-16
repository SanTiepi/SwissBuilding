# Service Stub Audit — SwissBuilding Backend

**Date:** 2026-03-16
**Scope:** `backend/app/services/` (143 service files, excluding `__init__.py`)
**Method:** AST-parsed every service for empty/placeholder functions; grep-searched all imports across `app/api/`, `app/services/`, `app/seeds/`, and `tests/`.

## Key Finding

**None of the 143 services are stubs.** Every file contains real, working implementations with actual database queries, business logic, and return values. The AST analysis found only 5 functions (across 5 files) that could be considered placeholders — out of ~1,400 total functions. These are fully implemented services, not scaffolding.

The smallest file (`audit_service.py`, 85 lines) contains two complete async functions with full SQLAlchemy queries. The largest (`transaction_readiness_service.py`, 1,382 lines) has 24 fully implemented functions.

---

## Services by Import Status

### Imported by API Routes (133 services — all actively wired)

All of the following are imported and called by endpoint handlers in `app/api/`. They are production code.

| # | File | Lines | Description |
|---|------|------:|-------------|
| 1 | `access_control_service.py` | 661 | Role-based access control and permission checking |
| 2 | `action_generator.py` | 344 | Generates action items from diagnostic results |
| 3 | `action_service.py` | 277 | CRUD and status management for action items |
| 4 | `activity_service.py` | 105 | Building activity feed aggregation |
| 5 | `anomaly_detection_service.py` | 447 | Detects anomalies in building diagnostic data |
| 6 | `audit_export_service.py` | 158 | Exports audit trail data in CSV/JSON/XLSX |
| 7 | `audit_readiness_service.py` | 1194 | Comprehensive audit readiness evaluation |
| 8 | `audit_service.py` | 85 | Audit logging for user actions |
| 9 | `auth_service.py` | 114 | Authentication (login, token, registration) |
| 10 | `authority_pack_service.py` | 505 | Authority pack generation for regulatory submissions |
| 11 | `background_job_service.py` | 135 | Generic background job tracking |
| 12 | `budget_tracking_service.py` | 429 | Budget tracking for remediation projects |
| 13 | `building_age_analysis_service.py` | 708 | Age-based building risk analysis |
| 14 | `building_benchmark_service.py` | 377 | Building benchmarking against peers |
| 15 | `building_certification_service.py` | 585 | Building certification status and tracking |
| 16 | `building_clustering_service.py` | 434 | Groups buildings by similarity patterns |
| 17 | `building_comparison_service.py` | 234 | Side-by-side building comparison |
| 18 | `building_dashboard_service.py` | 468 | Dashboard aggregate data for buildings |
| 19 | `building_health_index_service.py` | 774 | Composite building health index calculation |
| 20 | `building_lifecycle_service.py` | 416 | Building lifecycle stage tracking |
| 21 | `building_service.py` | 162 | Core building CRUD operations |
| 22 | `building_valuation_service.py` | 438 | Building valuation estimates |
| 23 | `bulk_operations_service.py` | 359 | Batch operations across multiple buildings |
| 24 | `campaign_recommender.py` | 309 | Campaign recommendation engine |
| 25 | `campaign_service.py` | 286 | Diagnostic campaign management |
| 26 | `campaign_tracking_service.py` | 303 | Campaign progress and status tracking |
| 27 | `capex_planning_service.py` | 387 | Capital expenditure planning |
| 28 | `co_ownership_service.py` | 295 | Co-ownership governance for PPE buildings |
| 29 | `completeness_engine.py` | 616 | Data completeness scoring engine |
| 30 | `completion_workspace_service.py` | 369 | Interactive completion workspace |
| 31 | `compliance_artefact_service.py` | 174 | Compliance artefact management |
| 32 | `compliance_calendar_service.py` | 527 | Compliance deadlines and calendar |
| 33 | `compliance_engine.py` | 444 | Regulatory compliance evaluation |
| 34 | `compliance_facade.py` | 113 | Read-only compliance domain facade |
| 35 | `compliance_gap_service.py` | 561 | Compliance gap analysis |
| 36 | `compliance_timeline_service.py` | 656 | Compliance timeline projection |
| 37 | `constraint_graph_service.py` | 634 | Dependency constraint graph for interventions |
| 38 | `contractor_acknowledgment_service.py` | 165 | Contractor acknowledgment workflow |
| 39 | `contractor_matching_service.py` | 495 | Contractor matching for remediation work |
| 40 | `contradiction_detector.py` | 409 | Detects contradictions across diagnostics |
| 41 | `cost_benefit_analysis_service.py` | 501 | Cost-benefit analysis for interventions |
| 42 | `counterfactual_analysis_service.py` | 581 | What-if counterfactual scenario analysis |
| 43 | `cross_building_pattern_service.py` | 506 | Cross-building pattern detection |
| 44 | `data_provenance_service.py` | 492 | Data origin and transformation tracking |
| 45 | `decision_replay_service.py` | 351 | Decision history replay and analysis |
| 46 | `diagnostic_quality_service.py` | 429 | Diagnostic quality evaluation |
| 47 | `diagnostic_service.py` | 137 | Core diagnostic CRUD operations |
| 48 | `digital_vault_service.py` | 281 | Document trust verification and integrity |
| 49 | `document_classification_service.py` | 267 | Auto-classification of building documents |
| 50 | `document_completeness_service.py` | 357 | Document completeness assessment |
| 51 | `document_service.py` | 142 | Core document CRUD operations |
| 52 | `document_template_service.py` | 656 | Document template generation |
| 53 | `dossier_completion_agent.py` | 239 | Automated dossier completion orchestration |
| 54 | `dossier_service.py` | 904 | Building dossier generation |
| 55 | `due_diligence_service.py` | 644 | Due diligence report generation |
| 56 | `energy_performance_service.py` | 322 | Energy performance analysis |
| 57 | `environmental_impact_service.py` | 511 | Environmental impact assessment |
| 58 | `evidence_chain_service.py` | 567 | Evidence chain validation and provenance |
| 59 | `evidence_facade.py` | 115 | Read-only evidence domain facade |
| 60 | `evidence_graph_service.py` | 442 | Evidence link graph traversal |
| 61 | `execution_quality_service.py` | 249 | Execution quality and acceptance control |
| 62 | `expert_review_service.py` | 132 | Expert review governance |
| 63 | `field_observation_service.py` | 186 | Field observation CRUD and verification |
| 64 | `geospatial_service.py` | 280 | Geospatial queries and mapping |
| 65 | `handoff_pack_service.py` | 1037 | Handoff pack generation for transitions |
| 66 | `incident_response_service.py` | 658 | Incident response planning and tracking |
| 67 | `insurance_risk_assessment_service.py` | 645 | Insurance risk assessment |
| 68 | `intervention_simulator.py` | 401 | Intervention outcome simulation |
| 69 | `knowledge_gap_service.py` | 503 | Knowledge gap identification |
| 70 | `lab_result_service.py` | 452 | Lab result analysis and interpretation |
| 71 | `maintenance_forecast_service.py` | 392 | Maintenance forecasting |
| 72 | `material_inventory_service.py` | 388 | Material inventory, risk, and lifecycle |
| 73 | `monitoring_plan_service.py` | 521 | Monitoring plan management |
| 74 | `multi_org_dashboard_service.py` | 147 | Multi-organization dashboard aggregation |
| 75 | `notification_digest_service.py` | 403 | Notification digest generation |
| 76 | `notification_preferences_service.py` | 184 | Extended notification preferences |
| 77 | `notification_rules_service.py` | 314 | Configurable notification rules engine |
| 78 | `occupancy_risk_service.py` | 661 | Occupancy risk evaluation |
| 79 | `occupant_safety_service.py` | 681 | Occupant safety assessment |
| 80 | `pack_impact_service.py` | 401 | Predicts evidence pack staleness |
| 81 | `passport_exchange_service.py` | 91 | Standardized passport exchange documents |
| 82 | `passport_export_service.py` | 440 | Structured building passport exports |
| 83 | `passport_service.py` | 292 | Building passport summary |
| 84 | `permit_tracking_service.py` | 442 | Renovation permit tracking |
| 85 | `plan_heatmap_service.py` | 463 | Plan heatmap visualization data |
| 86 | `pollutant_inventory_service.py` | 293 | Consolidated pollutant views |
| 87 | `portfolio_optimization_service.py` | 433 | Portfolio optimization recommendations |
| 88 | `portfolio_risk_trends_service.py` | 471 | Portfolio risk trend analysis |
| 89 | `portfolio_summary_service.py` | 555 | Portfolio summary aggregation |
| 90 | `post_works_service.py` | 277 | Post-works state management |
| 91 | `priority_matrix_service.py` | 657 | Priority matrix for building interventions |
| 92 | `quality_assurance_service.py` | 763 | Comprehensive quality assurance |
| 93 | `quality_service.py` | 175 | Building data quality scoring |
| 94 | `readiness_action_generator.py` | 298 | Readiness-driven action generation |
| 95 | `readiness_reasoner.py` | 969 | Readiness reasoning engine |
| 96 | `regulatory_change_impact_service.py` | 475 | Regulatory change impact analysis |
| 97 | `regulatory_deadline_service.py` | 368 | Regulatory deadline tracking |
| 98 | `regulatory_filing_service.py` | 602 | Regulatory filing for pollutant declarations |
| 99 | `regulatory_watch_service.py` | 429 | Regulatory watch and updates |
| 100 | `remediation_cost_service.py` | 358 | Remediation cost estimation |
| 101 | `remediation_facade.py` | 106 | Read-only remediation domain facade |
| 102 | `remediation_tracking_service.py` | 546 | Remediation progress tracking |
| 103 | `renovation_sequencer_service.py` | 574 | Renovation sequencing and scheduling |
| 104 | `renovation_simulator.py` | 505 | Renovation outcome simulation |
| 105 | `reporting_metrics_service.py` | 662 | Reporting metrics aggregation |
| 106 | `requalification_service.py` | 474 | Requalification replay timeline |
| 107 | `risk_aggregation_service.py` | 549 | Risk aggregation across dimensions |
| 108 | `risk_communication_service.py` | 517 | Risk communication report generation |
| 109 | `risk_engine.py` | 400 | Core risk scoring engine |
| 110 | `risk_mitigation_planner.py` | 706 | Risk mitigation planning |
| 111 | `sample_optimization_service.py` | 486 | Sampling plan optimization |
| 112 | `sampling_planner.py` | 285 | Sampling strategy planning |
| 113 | `scenario_planning_service.py` | 502 | Scenario planning and modeling |
| 114 | `search_service.py` | 354 | Meilisearch full-text search integration |
| 115 | `sensor_integration_service.py` | 399 | IoT sensor data integration |
| 116 | `shared_link_service.py` | 112 | Audience-bounded sharing links |
| 117 | `spatial_risk_mapping_service.py` | 575 | Spatial risk mapping |
| 118 | `stakeholder_dashboard_service.py` | 330 | Stakeholder-specific dashboards |
| 119 | `stakeholder_notification_service.py` | 551 | Stakeholder-targeted notifications |
| 120 | `stakeholder_report_service.py` | 574 | Stakeholder-specific report generation |
| 121 | `subsidy_tracking_service.py` | 406 | Subsidy tracking and eligibility |
| 122 | `tenant_impact_service.py` | 628 | Tenant impact assessment |
| 123 | `time_machine_service.py` | 176 | Historical state reconstruction |
| 124 | `timeline_enrichment_service.py` | 243 | Timeline event enrichment |
| 125 | `timeline_service.py` | 224 | Building timeline aggregation |
| 126 | `transaction_readiness_service.py` | 1382 | Transaction readiness evaluation |
| 127 | `transfer_package_service.py` | 302 | Building memory transfer packages |
| 128 | `ventilation_assessment_service.py` | 522 | Ventilation assessment |
| 129 | `warranty_obligations_service.py` | 403 | Warranty obligations and defect tracking |
| 130 | `waste_management_service.py` | 425 | OLED-compliant waste management |
| 131 | `weak_signal_watchtower.py` | 568 | Weak signal detection and monitoring |
| 132 | `work_phase_service.py` | 509 | Work phase management |
| 133 | `workflow_orchestration_service.py` | 296 | Multi-step workflow state machine |

### Imported by Other Services Only (not directly by API routes)

These are internal building blocks used by other services but not directly by API endpoints.

| # | File | Lines | Imported By | Description |
|---|------|------:|-------------|-------------|
| 1 | `building_data_loader.py` | 89 | `completeness_engine`, `compliance_engine`, `passport_service`, `dossier_completion_agent`, others | Shared building data loading utilities |
| 2 | `rule_resolver.py` | 267 | `compliance_engine`, `completeness_engine` | Regulatory rule resolution logic |
| 3 | `eco_clause_template_service.py` | 499 | `authority_pack_service` | Eco clause templates for authority packs |
| 4 | `file_processing_service.py` | 170 | `document_service` | Virus scanning (ClamAV) + OCR pipeline |
| 5 | `trust_score_calculator.py` | 298 | `bulk_operations_service`, `dossier_completion_agent`, seeds | Building trust score calculation |
| 6 | `unknown_generator.py` | 393 | `bulk_operations_service`, `dossier_completion_agent`, `sampling_planner`, seeds | Unknown issue detection and generation |
| 7 | `change_signal_generator.py` | 425 | Seeds only (`seed_demo_authority`, `seed_scenarios`) | Change signal detection for buildings |

### Imported by Tests Only (1 service)

| # | File | Lines | Description |
|---|------|------:|-------------|
| 1 | `prework_trigger_service.py` | 320 | Pre-work diagnostic requirement lifecycle — has its own test file but no API route or service consumer |

### Not Imported Anywhere Outside Own File (0 services)

No services are completely orphaned. Every service file is referenced by at least one test.

---

## Also Examined: Zone Classification Services

| File | Lines | Description |
|------|------:|-------------|
| `zone_classification_service.py` | 541 | Zone classification (imported by API) |
| `zone_safety_service.py` | 180 | Zone safety readiness (imported by API) |

---

## Summary

| Category | Count | Action |
|----------|------:|--------|
| Used by API routes | 133 | Keep — production code |
| Used by other services (not API) | 7 | Keep — internal dependencies |
| Used by seeds only | 1 (`change_signal_generator`) | Keep — needed for demo/seed data |
| Test-only (no production consumer) | 1 (`prework_trigger_service`) | Candidate for wiring to an API route or removal |
| Completely unused | 0 | — |

**Bottom line:** There are no stub/placeholder services to delete. All 143 files contain real implementations. The only service without a production consumer is `prework_trigger_service.py` (320 lines, tested, but not wired to any API route or called by another service).
