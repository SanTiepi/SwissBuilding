# SwissBuilding Inventory Report
Generated: 2026-03-29 by Duo Mode (Codex + Claude)

## Overview
- **258 services**, 109,640 lines of service code
- **240 API route files**, 151 models, 244 schemas
- **288 test files**, ~6,950 tests

## Service Classification
| Category | Count | % | Description |
|---|---|---|---|
| Core | 44 | 17% | Consumed by API routes AND other services |
| Leaf API | 173 | 67% | Consumed by API only |
| Internal | 17 | 7% | Consumed by other services only |
| **Orphans** | **24** | **9%** | **Nobody consumes them** |

## Hub Services (most consumers)
1. `building_service` — 71 API routes (the backbone)
2. `audit_service` — 17 API routes
3. `action_service` — 4 API routes
4. `search_service` — 4 API routes
5. `auth_service` — 3 API routes

## Orphan Services (24 total, ~11,000 lines)
These services are imported by NO API route and NO other service:

| Service | Lines | Imports |
|---|---|---|
| swiss_rules_spine_service | 1559 | none |
| contract_extraction_service | 1373 | consequence_engine |
| authority_extraction_service | 1227 | consequence_engine |
| cantonal_procedure_source_service | 697 | source_registry_service |
| memory_transfer_service | 691 | time_machine_service, passport_service, contradiction_detector |
| operational_gate_service | 701 | safe_to_start_service |
| partner_submission_service | 574 | review_queue_service, diagnostic_extraction_service, partner_trust_service |
| passport_envelope_service | 515 | conformance_service, passport_service |
| sample_optimization_service | 487 | building_data_loader |
| ecosystem_engagement_service | 449 | none |
| work_family_service | 427 | none |
| genealogy_service | 407 | none |
| ritual_service | 387 | none |
| truth_service | 370 | review_queue_service, consequence_engine |
| building_case_service | 364 | none |
| bulk_operations_service | 360 | dossier_completion_agent |
| prework_trigger_service | 321 | none |
| contractor_acknowledgment_service | 258 | partner_trust_service, eco_clause_template_service |
| value_notification_hooks | 220 | value_ledger_service |
| swiss_rules_projection_service | 196 | none |
| notification_preferences_service | 185 | none |
| background_job_service | 136 | none |
| shared_link_service | 113 | none |
| temporal_utils | 46 | none |

## SB-02 Classification Results (2026-03-29)

The initial scan flagged 24 services as orphans. Deep analysis reveals only 8 are truly unwired:

### ACTIVE (16 — not orphans, inventory error)
These services have API routes registered in `router.py` and/or active service consumers:
memory_transfer_service, operational_gate_service, partner_submission_service, passport_envelope_service,
sample_optimization_service, ecosystem_engagement_service, work_family_service, genealogy_service,
ritual_service, truth_service, building_case_service, bulk_operations_service,
contractor_acknowledgment_service, notification_preferences_service, background_job_service, shared_link_service

### DEAD CODE (4 — safe to remove)
| Service | Lines | Reason |
|---|---|---|
| contract_extraction_service | 1373 | No runtime consumer, no API route, test-only |
| authority_extraction_service | 1227 | No runtime consumer, no API route, test-only |
| value_notification_hooks | 220 | Never imported anywhere except canonical_registry |
| temporal_utils | 46 | Never imported anywhere except canonical_registry |

### BROKEN IMPORT (2 — need wiring or removal decision)
| Service | Lines | Reason |
|---|---|---|
| swiss_rules_spine_service | 1559 | Only consumed by script + tests, no API route |
| prework_trigger_service | 321 | Test-only, no API route, flagged in STUB_SERVICES_AUDIT.md |

### PLANNED FEATURE (2 — keep for now)
| Service | Lines | Reason |
|---|---|---|
| cantonal_procedure_source_service | 697 | Tested infrastructure for subsidy/cantonal procedures |
| swiss_rules_projection_service | 196 | Test infrastructure for SwissRules enablement pack |

## Recommendations (updated)
1. ~~**SB-02**: Classify orphans~~ ✅ Done
2. **SB-03**: Compute blast radius for the 4 dead-code services
3. **SB-04**: Remove 4 dead services + their tests (1 commit per service)
4. **SB-05**: Decide on 2 broken-import services (wire route or remove)
5. **SB-06+**: Continue with Wave 2
