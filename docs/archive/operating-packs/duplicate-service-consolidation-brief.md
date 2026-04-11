# Duplicate Service Family Consolidation Brief

> Generated: 2026-03-24 | Source: W81 service consumer audit (`docs/service-consumer-map.md`)

## Overview

The W81 audit identified **14 service families** where multiple services share a domain context and overlap in data access, query patterns, or business logic. Together these families contain **61 satellite services** (excluding core anchors) totalling ~20,000 LOC. Most satellites are single-consumer, thin-API-only, or facade wrappers — prime candidates for consolidation into their family's core anchor.

## Priority Legend

| Priority | Criteria |
|----------|----------|
| **HIGH** | Core domain anchor exists with 5+ consumers; satellites duplicate queries or repackage the same data; consolidation reduces import graph significantly |
| **MEDIUM** | 3-4 services in family; moderate overlap; facade already exists or could absorb siblings cleanly |
| **LOW** | Services are conceptually related but functionally distinct; consolidation is optional cleanup |

---

## Family #1: `building` (9 satellites + 2 core)

**Priority: HIGH** | ~4,700 LOC in satellites | 9 low-signal services

| Service | LOC | Classification | Overlap |
|---------|----:|----------------|---------|
| `building_service` (anchor) | 166 | core_domain | CRUD, 30 API consumers |
| `building_data_loader` (anchor) | 89 | composed_helper | Shared query helpers, 50 service consumers |
| `building_age_analysis_service` | 708 | single_consumer | Queries building+diagnostics, overlaps health index |
| `building_benchmark_service` | 377 | single_consumer | Peer comparison, overlaps health index dimensions |
| `building_certification_service` | 585 | single_consumer | Certification status, overlaps compliance family |
| `building_clustering_service` | 434 | single_consumer | Portfolio grouping, overlaps portfolio family |
| `building_comparison_service` | 234 | thin_api_only | 2-10 building compare, overlaps benchmark |
| `building_dashboard_service` | 468 | thin_api_only | Dashboard aggregation, overlaps health index |
| `building_health_index_service` | 774 | single_consumer | Composite 0-100 score, overlaps risk aggregation |
| `building_lifecycle_service` | 416 | single_consumer | Phase derivation, overlaps compliance timeline |
| `building_valuation_service` | 438 | single_consumer | Cost impact, overlaps remediation cost |

**Recommendation**: Merge `health_index`, `benchmark`, `comparison`, `dashboard` into a single `building_analytics_service`. Merge `age_analysis`, `lifecycle`, `certification` into `building_assessment_service`. Keep `building_service` and `building_data_loader` as-is. Consider absorbing `valuation` into remediation family. `clustering` can move to portfolio family.

**Effort**: L (large) — highest LOC, most files, but low consumer count makes it safe.

---

## Family #2: `compliance` (4 satellites + 2 core)

**Priority: HIGH** | ~1,855 LOC in satellites | 4 low-signal services

| Service | LOC | Classification | Overlap |
|---------|----:|----------------|---------|
| `compliance_engine` (anchor) | 459 | core_domain | Threshold checks, 9 service consumers |
| `compliance_artefact_service` (anchor) | 174 | thin_api_only | Artefact CRUD |
| `compliance_facade` | 113 | single_consumer | Read-only wrapper over engine+artefacts |
| `compliance_gap_service` | 561 | single_consumer | Gap analysis, re-queries same diagnostic+sample data |
| `compliance_calendar_service` | 527 | single_consumer | Deadline calendar, overlaps compliance_timeline |
| `compliance_timeline_service` | 656 | single_consumer | Historical compliance state, overlaps gap+calendar |

**Recommendation**: Merge `facade` into `compliance_engine` (it's 113 LOC of passthrough). Merge `gap_service` + `timeline_service` + `calendar_service` into `compliance_analysis_service` — all three query the same diagnostic/sample/intervention data and compute compliance state from different angles.

**Effort**: M (medium) — high overlap means straightforward merge.

---

## Family #3: `risk` (3 satellites + 1 core)

**Priority: HIGH** | ~1,772 LOC in satellites | 3 low-signal services

| Service | LOC | Classification | Overlap |
|---------|----:|----------------|---------|
| `risk_engine` (anchor) | 400 | core_domain | Pollutant probability, 7 service consumers |
| `risk_aggregation_service` | 549 | single_consumer | Multi-dimensional 0-100 score, consumes risk_engine output |
| `risk_communication_service` | 517 | single_consumer | Human-readable risk reports, queries same diagnostic+sample data |
| `risk_mitigation_planner` | 706 | single_consumer | Remediation sequencing, overlaps remediation family |

**Recommendation**: Merge `aggregation` into `risk_engine` as additional public methods. Move `communication` to a `risk_reporting_service` or absorb into stakeholder family. Move `mitigation_planner` to remediation family (it's remediation sequencing, not risk calculation).

**Effort**: M — `risk_engine` is the natural home; `mitigation_planner` relocation is clean.

---

## Family #4: `regulatory` (4 services, all low-signal)

**Priority: MEDIUM** | ~1,874 LOC | No core anchor

| Service | LOC | Classification |
|---------|----:|----------------|
| `regulatory_change_impact_service` | 475 | single_consumer |
| `regulatory_deadline_service` | 368 | single_consumer |
| `regulatory_filing_service` | 602 | single_consumer |
| `regulatory_watch_service` | 429 | single_consumer |

**Recommendation**: Consolidate all four into `regulatory_service`. These all operate on the same regulatory pack + building data. `deadline` overlaps `compliance_calendar`. `filing` overlaps `compliance_artefact`. `watch` and `change_impact` are two sides of the same coin.

**Effort**: M — no existing anchor, so create one and fold in.

---

## Family #5: `evidence` (3 services, all low-signal)

**Priority: MEDIUM** | ~1,124 LOC | No core anchor

| Service | LOC | Classification |
|---------|----:|----------------|
| `evidence_chain_service` | 567 | thin_api_only |
| `evidence_facade` | 115 | single_consumer |
| `evidence_graph_service` | 442 | thin_api_only |

**Recommendation**: Merge all into `evidence_service`. The facade is 115 LOC of passthrough. Chain validation and graph traversal both query `EvidenceLink` + related entities and can share query infrastructure.

**Effort**: S (small) — clean merge, low consumer count.

---

## Family #6: `remediation` (3 services, all low-signal)

**Priority: MEDIUM** | ~1,010 LOC | No core anchor

| Service | LOC | Classification |
|---------|----:|----------------|
| `remediation_cost_service` | 358 | thin_api_only |
| `remediation_facade` | 106 | single_consumer |
| `remediation_tracking_service` | 546 | single_consumer |

**Recommendation**: Merge into `remediation_service`. Facade is passthrough. Cost estimation and progress tracking both query `ActionItem` + `Intervention` + `Sample`. After merge, consider absorbing `risk_mitigation_planner` here too.

**Effort**: S — straightforward, no complex dependencies.

---

## Family #7: `document` (4 services, all low-signal)

**Priority: MEDIUM** | ~1,422 LOC | No strong anchor

| Service | LOC | Classification |
|---------|----:|----------------|
| `document_service` | 142 | thin_api_only |
| `document_classification_service` | 267 | single_consumer |
| `document_completeness_service` | 357 | single_consumer |
| `document_template_service` | 656 | single_consumer |

**Recommendation**: Keep `document_service` as CRUD anchor. Merge `classification` + `completeness` into `document_analysis_service`. Keep `template_service` separate (it's generation, not analysis) or fold it in if template logic is thin.

**Effort**: S — `classification` and `completeness` are natural merge targets.

---

## Family #8: `notification` (3 services, all low-signal)

**Priority: MEDIUM** | ~901 LOC | No core anchor

| Service | LOC | Classification |
|---------|----:|----------------|
| `notification_digest_service` | 403 | single_consumer |
| `notification_preferences_service` | 184 | single_consumer |
| `notification_rules_service` | 314 | single_consumer |

**Recommendation**: Merge into `notification_service`. Digest, preferences, and rules are tightly coupled — rules determine what triggers a notification, preferences determine delivery, digest batches them.

**Effort**: S — all three serve the same domain with shared types.

---

## Family #9: `portfolio` (3 services, all low-signal)

**Priority: MEDIUM** | ~1,529 LOC | No core anchor

| Service | LOC | Classification |
|---------|----:|----------------|
| `portfolio_optimization_service` | 433 | single_consumer |
| `portfolio_risk_trends_service` | 471 | single_consumer |
| `portfolio_summary_service` | 625 | single_consumer |

**Recommendation**: Merge into `portfolio_analytics_service`. All three aggregate building-level data to portfolio level. Summary is the natural anchor; optimization and risk trends are projections on the same data.

**Effort**: S — all single-consumer, same data patterns.

---

## Family #10: `stakeholder` (3 services, all low-signal)

**Priority: LOW** | ~1,455 LOC | No core anchor

| Service | LOC | Classification |
|---------|----:|----------------|
| `stakeholder_dashboard_service` | 330 | single_consumer |
| `stakeholder_notification_service` | 551 | single_consumer |
| `stakeholder_report_service` | 574 | single_consumer |

**Recommendation**: Merge into `stakeholder_service`. Dashboard, notification, and report generation all serve the same audience-specific output concern. `notification` overlaps the notification family — consider merging there instead.

**Effort**: S — but cross-family overlap with notification family needs resolution first.

---

## Family #11: `campaign` (3 services, all low-signal)

**Priority: LOW** | ~898 LOC | Weak anchor

| Service | LOC | Classification |
|---------|----:|----------------|
| `campaign_service` | 286 | thin_api_only |
| `campaign_recommender` | 309 | single_consumer |
| `campaign_tracking_service` | 303 | single_consumer |

**Recommendation**: Merge `recommender` + `tracking` into `campaign_service`. The CRUD service is a natural anchor. Recommender and tracking are read-only projections on campaign data.

**Effort**: S — small files, clean boundaries.

---

## Family #12: `evidence_dossier` (2 satellites + 1 core)

**Priority: LOW** | ~1,648 LOC in satellites | 2 low-signal

| Service | LOC | Classification |
|---------|----:|----------------|
| `dossier_completion_agent` (anchor) | 239 | core_domain |
| `dossier_service` | 904 | thin_api_only |
| `authority_pack_service` | 505 | thin_api_only |

**Recommendation**: Keep `dossier_service` as the primary anchor (it's the largest). Consider merging `authority_pack_service` into it — authority packs are a specific dossier output format. `dossier_completion_agent` orchestrates both and should remain separate.

**Effort**: S — `authority_pack` is a natural subset of dossier output.

---

## Family #13: `building_memory` (2 satellites + 1 core)

**Priority: LOW** | ~527 LOC in satellites | 2 low-signal

| Service | LOC | Classification |
|---------|----:|----------------|
| `passport_service` (anchor) | 322 | core_domain |
| `decision_replay_service` | 351 | single_consumer |
| `time_machine_service` | 176 | thin_api_only |

**Recommendation**: Merge `time_machine_service` into `passport_service` — snapshots are a passport capability. Keep `decision_replay_service` separate if it has distinct query patterns, or merge if it primarily reads snapshot data.

**Effort**: S — small services, clear hierarchy.

---

## Family #14: `audit` (2 satellites + 1 core)

**Priority: LOW** | ~1,352 LOC in satellites | 2 low-signal

| Service | LOC | Classification |
|---------|----:|----------------|
| `audit_service` (anchor) | 85 | core_domain |
| `audit_export_service` | 158 | single_consumer |
| `audit_readiness_service` | 1194 | single_consumer |

**Recommendation**: Merge `audit_export_service` (158 LOC) into `audit_service`. Keep `audit_readiness_service` separate — at 1194 LOC it's the largest single service in any family and has distinct business logic (readiness checks).

**Effort**: XS — only the 158-LOC export service moves.

---

## Recommended Consolidation Sequence

| Phase | Families | Rationale |
|-------|----------|-----------|
| **Phase 1** | evidence, remediation, audit | Smallest, no core anchor conflicts, build merge muscle |
| **Phase 2** | notification, campaign, document | Small families, clear anchors, isolated domains |
| **Phase 3** | compliance, risk | HIGH priority, higher consumer counts, need careful API migration |
| **Phase 4** | regulatory, portfolio, stakeholder | Medium families, cross-family overlap resolution |
| **Phase 5** | building, building_memory, evidence_dossier | Largest family last, most files touched |

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total duplicate families | 14 |
| Total satellite services | 61 |
| Total satellite LOC | ~20,000 |
| HIGH priority families | 3 (building, compliance, risk) |
| MEDIUM priority families | 6 (regulatory, evidence, remediation, document, notification, portfolio) |
| LOW priority families | 5 (stakeholder, campaign, evidence_dossier, building_memory, audit) |
| Estimated target service count reduction | 35-40 services eliminated |
| Recommended phases | 5 |
