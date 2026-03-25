# BatiConnect Capability Blueprint

> All product capabilities grouped by layer, with implementation status verified against codebase.

Version: 2.0 | Date: 2026-03-21

---

## Status Legend

- `implemented` -- exists in current codebase with service + API + tests
- `partial` -- partially built (service exists but missing entity, API, or frontend)
- `planned` -- new for BatiConnect, no implementation yet

---

# Layer 1: Ingestion

## 1.1 Document Intake (Upload + ClamAV + OCR)

| Field | Value |
|---|---|
| **Description** | Upload documents with virus scanning (ClamAV) and OCR processing (OCRmyPDF) to make scanned PDFs searchable |
| **Source entities** | Document, Asset(Building) |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/file_processing_service.py` |
| **API path** | `backend/app/api/documents.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13), all surfaces that accept document uploads |
| **Dependencies** | ClamAV Docker service, OCRmyPDF, MinIO (S3) |

## 1.2 PDF Diagnostic Report Parsing

| Field | Value |
|---|---|
| **Description** | Parse structured PDF diagnostic reports into structured data (two-step: parse then review then apply) |
| **Source entities** | Document, Diagnostic, Sample |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/document_service.py` |
| **API path** | `backend/app/api/documents.py` |
| **BatiConnect surface** | Diagnostic Center (Ops-14) |
| **Dependencies** | Document Intake (1.1) |

## 1.3 Vaud Public Data Import (RegBL/Cantonal)

| Field | Value |
|---|---|
| **Description** | Import building data from Vaud cantonal public registers (3 layers: vd.adresse, vd.batiment_rcb, vd.batiment -- 556 fields) |
| **Source entities** | Asset(Building) |
| **Status** | `implemented` |
| **Service path** | `backend/app/importers/vaud_public.py` |
| **BatiConnect surface** | Asset Registry (Ops-02) |
| **Dependencies** | None (standalone importer) |

## 1.4 Mail Parsing and Projection

| Field | Value |
|---|---|
| **Description** | Parse incoming emails, extract structured data, and project to relevant entities (documents, communications, obligations) |
| **Source entities** | Communication (planned), Document |
| **Status** | `planned` |
| **BatiConnect surface** | Communication Inbox (Ops-12), Evidence Workspace (Ops-13) |
| **Dependencies** | Communication entity, Document Intake (1.1), Data Extraction (1.6) |

## 1.5 Document Classification (AI)

| Field | Value |
|---|---|
| **Description** | Auto-classify building documents by analyzing metadata, filename patterns, and content context into 10 categories |
| **Source entities** | Document, Diagnostic |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/document_classification_service.py` |
| **API path** | `backend/app/api/document_classification.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13) |
| **Dependencies** | Document Intake (1.1) |

## 1.6 Data Extraction from Documents (AI)

| Field | Value |
|---|---|
| **Description** | AI-powered extraction of structured data from unstructured documents (dates, amounts, pollutant values, parties) |
| **Source entities** | Document, various target entities |
| **Status** | `planned` |
| **BatiConnect surface** | Evidence Workspace (Ops-13), Financial Workspace (Ops-08) |
| **Dependencies** | Document Intake (1.1), Document Classification (1.5) |

## 1.7 Matching Incoming Data to Existing Entities

| Field | Value |
|---|---|
| **Description** | Match incoming documents and data to existing buildings, diagnostics, parties, and contracts using fuzzy matching |
| **Source entities** | All write-side entities |
| **Status** | `planned` |
| **BatiConnect surface** | Evidence Workspace (Ops-13), Communication Inbox (Ops-12) |
| **Dependencies** | Document Classification (1.5), Meilisearch |

## 1.8 Bulk Import from ERP

| Field | Value |
|---|---|
| **Description** | Bulk import buildings, contacts, leases, and financial data from external ERP systems via structured file upload |
| **Source entities** | Asset, Party, Lease, FinancialEntry |
| **Status** | `planned` |
| **BatiConnect surface** | Asset Registry (Ops-02), Party Manager (Ops-03) |
| **Dependencies** | Matching (1.7) |

## 1.9 Full-Text Search (Meilisearch)

| Field | Value |
|---|---|
| **Description** | Cross-entity full-text search across buildings, diagnostics, and documents with filterable attributes |
| **Source entities** | Building, Diagnostic, Document |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/search_service.py` |
| **API path** | `backend/app/api/search.py` |
| **BatiConnect surface** | All Ops surfaces (Cmd+K global search) |
| **Dependencies** | Meilisearch Docker service |

---

# Layer 2: Truth / Evidence

## 2.1 Evidence Chain Linking

| Field | Value |
|---|---|
| **Description** | Link evidence items with typed relationships (proves/supports/contradicts/supersedes/derived_from) across all entity types |
| **Source entities** | EvidenceLink, Document, Diagnostic, Sample, Intervention, Zone, ActionItem |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/evidence_chain_service.py` |
| **API path** | `backend/app/api/evidence_chain.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13) |
| **Dependencies** | None |

## 2.2 Evidence Graph Visualization

| Field | Value |
|---|---|
| **Description** | Build and traverse navigable graphs of evidence relationships with path finding, neighbor queries, and graph statistics |
| **Source entities** | EvidenceLink, all entity types as nodes |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/evidence_graph_service.py` |
| **API path** | `backend/app/api/evidence_graph.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13), Passport Page (Shared-05) |
| **Dependencies** | Evidence Chain Linking (2.1) |

## 2.3 Source Confidence Tracking

| Field | Value |
|---|---|
| **Description** | Track confidence level of each data point (proven/inferred/declared/obsolete/contradictory) feeding into trust score |
| **Source entities** | BuildingTrustScore, EvidenceLink, Document, Sample |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/trust_score_calculator.py` |
| **API path** | `backend/app/api/trust_scores.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13), Passport Page (Shared-05) |
| **Dependencies** | Evidence Chain Linking (2.1) |

## 2.4 Contradiction Detection

| Field | Value |
|---|---|
| **Description** | Detect 5 contradiction types in building data (idempotent, auto-resolve when source data changes) |
| **Source entities** | Diagnostic, Sample, Document, Intervention, BuildingElement |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/contradiction_detector.py` |
| **API path** | (invoked via evidence/passport endpoints) |
| **BatiConnect surface** | Evidence Workspace (Ops-13), Passport Page (Shared-05) |
| **Dependencies** | Evidence Chain Linking (2.1) |

## 2.5 Expert Review and Override

| Field | Value |
|---|---|
| **Description** | Governance layer for expert reviews: create, list, withdraw reviews that can override automated findings |
| **Source entities** | ExpertReview, DecisionRecord |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/expert_review_service.py` |
| **API path** | `backend/app/api/expert_reviews.py` |
| **BatiConnect surface** | Decision Room (Ops-15), Evidence Workspace (Ops-13) |
| **Dependencies** | None |

## 2.6 Data Quality Issue Tracking

| Field | Value |
|---|---|
| **Description** | Track data quality issues (missing, inconsistent, stale, unverified) per building with severity and resolution status |
| **Source entities** | DataQualityIssue |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/quality_service.py`, `backend/app/services/diagnostic_quality_service.py` |
| **API path** | `backend/app/api/data_quality.py`, `backend/app/api/diagnostic_quality.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13), Diagnostic Center (Ops-14) |
| **Dependencies** | None |

## 2.7 Unknown Gap Detection

| Field | Value |
|---|---|
| **Description** | Auto-detect 7 gap categories (missing diagnostic, missing sample, unscanned zone, etc.) with idempotent generation and auto-resolve |
| **Source entities** | UnknownIssue |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/unknown_generator.py` |
| **API path** | `backend/app/api/unknowns.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13), Passport Page (Shared-05) |
| **Dependencies** | None |

## 2.8 Change Signal Generation

| Field | Value |
|---|---|
| **Description** | Generate 7 signal types from building data events (new diagnostic, sample result, intervention completed, etc.) |
| **Source entities** | ChangeSignal |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/change_signal_generator.py` |
| **API path** | `backend/app/api/change_signals.py` |
| **BatiConnect surface** | Ops Dashboard (Ops-01), Evidence Workspace (Ops-13) |
| **Dependencies** | None |

## 2.9 Provenance Tracking

| Field | Value |
|---|---|
| **Description** | Trace origin and transformations of every data entity with lineage tree and integrity verification |
| **Source entities** | Building, Diagnostic, Document, Sample, ActionItem |
| **Status** | `partial` |
| **Service path** | `backend/app/services/data_provenance_service.py` |
| **API path** | `backend/app/api/data_provenance.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13) |
| **Dependencies** | None |
| **Gap** | Currently Building-centric; extend to all canonical entities (Lease, Contract, Party, etc.) |

## 2.10 Field Observation Capture and Verification

| Field | Value |
|---|---|
| **Description** | Capture on-site observations with structured verification workflow (create, verify, summarize) |
| **Source entities** | FieldObservation |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/field_observation_service.py` |
| **API path** | `backend/app/api/field_observations.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13), Diagnostic Center (Ops-14) |
| **Dependencies** | None |

## 2.11 Digital Vault (Document Integrity)

| Field | Value |
|---|---|
| **Description** | Document trust verification and integrity tracking with hash-based tamper detection |
| **Source entities** | Document, Building, Diagnostic, Sample |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/digital_vault_service.py` |
| **API path** | `backend/app/api/digital_vault.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13) |
| **Dependencies** | Document Intake (1.1) |

---

# Layer 3: Occupancy

## 3.1 Lease Lifecycle Management

| Field | Value |
|---|---|
| **Description** | Full lease CRUD with lifecycle events (create, renew, terminate, adjust) and status tracking |
| **Source entities** | Lease (planned), LeaseEvent (planned), Unit (planned), Party (planned) |
| **Status** | `planned` |
| **BatiConnect surface** | Lease Management (Ops-05), Regie Dashboard (Ws-05), Tenant Portal (Ws-02) |
| **Dependencies** | Party entity, Unit entity |

## 3.2 Tenant Onboarding

| Field | Value |
|---|---|
| **Description** | Structured tenant onboarding flow: document collection, lease signing, safety acknowledgment |
| **Source entities** | Lease (planned), Party (planned), Document, ContractorAcknowledgment (pattern reuse) |
| **Status** | `planned` |
| **BatiConnect surface** | Lease Management (Ops-05), Tenant Portal (Ws-02) |
| **Dependencies** | Lease Lifecycle (3.1), Party entity |

## 3.3 Vacancy Tracking

| Field | Value |
|---|---|
| **Description** | Track unit occupancy status, vacancy periods, and vacancy cost impact |
| **Source entities** | Unit (planned), Lease (planned), Asset(Building) |
| **Status** | `planned` |
| **BatiConnect surface** | Regie Dashboard (Ws-05), Owner Dashboard (Ws-01) |
| **Dependencies** | Lease Lifecycle (3.1), Unit entity |

## 3.4 Occupancy Economics

| Field | Value |
|---|---|
| **Description** | Compute rent impact, disruption cost, and occupancy-related financial projections |
| **Source entities** | Lease (planned), Unit (planned), FinancialEntry (planned) |
| **Status** | `planned` |
| **BatiConnect surface** | Financial Workspace (Ops-08), Regie Dashboard (Ws-05) |
| **Dependencies** | Lease Lifecycle (3.1), Financial Recording (5.1) |
| **Note** | `occupancy_risk_service.py` exists for pollutant-related occupancy risk assessment, not financial occupancy economics |

## 3.5 Rent Index Adjustment

| Field | Value |
|---|---|
| **Description** | Apply Swiss rent index adjustments to lease terms based on reference rate changes |
| **Source entities** | Lease (planned), LeaseEvent (planned) |
| **Status** | `planned` |
| **BatiConnect surface** | Lease Management (Ops-05) |
| **Dependencies** | Lease Lifecycle (3.1) |

## 3.6 Lease Event History

| Field | Value |
|---|---|
| **Description** | Chronological log of all lease events (creation, renewal, adjustment, termination, dispute) |
| **Source entities** | LeaseEvent (planned), Lease (planned) |
| **Status** | `planned` |
| **BatiConnect surface** | Lease Management (Ops-05), Tenant Portal (Ws-02) |
| **Dependencies** | Lease Lifecycle (3.1) |

## 3.7 Unit Management

| Field | Value |
|---|---|
| **Description** | Define units within assets (apartments, offices, parking, commercial spaces) with physical attributes |
| **Source entities** | Unit (planned), Asset(Building), Zone |
| **Status** | `planned` |
| **BatiConnect surface** | Asset Registry (Ops-02), Lease Management (Ops-05) |
| **Dependencies** | None (extends existing Zone model) |

---

# Layer 4: Contractual / Insurance

## 4.1 Contract Lifecycle

| Field | Value |
|---|---|
| **Description** | Full contract CRUD with lifecycle (create, renew, terminate) and obligation auto-generation |
| **Source entities** | Contract (planned), Party (planned), Asset(Building), Obligation (planned) |
| **Status** | `planned` |
| **BatiConnect surface** | Contract Management (Ops-06) |
| **Dependencies** | Party entity, Obligation entity |

## 4.2 SLA Monitoring

| Field | Value |
|---|---|
| **Description** | Track service level agreements within contracts, monitor compliance, and alert on breaches |
| **Source entities** | Contract (planned), Obligation (planned) |
| **Status** | `planned` |
| **BatiConnect surface** | Contract Management (Ops-06), Obligation Calendar (Ops-11) |
| **Dependencies** | Contract Lifecycle (4.1) |

## 4.3 Insurance Policy Management

| Field | Value |
|---|---|
| **Description** | Record and manage insurance policies (building, liability, RC) with coverage details and renewal tracking |
| **Source entities** | InsurancePolicy (planned), Asset(Building), Party (planned) |
| **Status** | `planned` |
| **BatiConnect surface** | Insurance & Claims (Ops-07), Insurer Portal (Ws-06) |
| **Dependencies** | Party entity |

## 4.4 Claims Workflow

| Field | Value |
|---|---|
| **Description** | Structured claims lifecycle (open, review, settle/reject) with evidence attachment and status tracking |
| **Source entities** | Claim (planned), InsurancePolicy (planned), Document, EvidenceLink |
| **Status** | `planned` |
| **BatiConnect surface** | Insurance & Claims (Ops-07), Insurer Portal (Ws-06) |
| **Dependencies** | Insurance Policy Management (4.3), Evidence Chain Linking (2.1) |

## 4.5 Contract Obligation Auto-Generation

| Field | Value |
|---|---|
| **Description** | Automatically generate obligations from contract terms (maintenance schedules, renewal dates, compliance deadlines) |
| **Source entities** | Contract (planned), Obligation (planned) |
| **Status** | `planned` |
| **BatiConnect surface** | Contract Management (Ops-06), Obligation Calendar (Ops-11) |
| **Dependencies** | Contract Lifecycle (4.1) |

## 4.6 Insurance Risk Assessment

| Field | Value |
|---|---|
| **Description** | Evaluate insurance risk for buildings based on pollutant state, construction history, and Swiss regulatory thresholds. Tier assignment, coverage restrictions, cross-building comparison |
| **Source entities** | Building, Diagnostic, Sample, Intervention |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/insurance_risk_assessment_service.py` |
| **API path** | `backend/app/api/insurance_risk_assessment.py` |
| **BatiConnect surface** | Insurance & Claims (Ops-07), Insurer Portal (Ws-06), Insurer Pack (Shared-04) |
| **Dependencies** | None |

## 4.7 Contractor Acknowledgment Workflow

| Field | Value |
|---|---|
| **Description** | Create, send, view, acknowledge, refuse safety acknowledgments for contractor interventions with SHA-256 hash |
| **Source entities** | ContractorAcknowledgment, Intervention |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/contractor_acknowledgment_service.py` |
| **API path** | `backend/app/api/contractor_acknowledgment.py` |
| **BatiConnect surface** | Contractor Portal (Ws-04) |
| **Dependencies** | None |

## 4.8 Warranty Obligations Tracking

| Field | Value |
|---|---|
| **Description** | Track warranty terms and obligations arising from interventions and contracts |
| **Source entities** | Intervention, Building |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/warranty_obligations_service.py` |
| **API path** | `backend/app/api/warranty_obligations.py` |
| **BatiConnect surface** | Contract Management (Ops-06), Obligation Calendar (Ops-11) |
| **Dependencies** | None |

---

# Layer 5: Financial / Fiscal

## 5.1 Expense/Income Recording

| Field | Value |
|---|---|
| **Description** | Record financial entries (expenses, income) linked to assets, interventions, contracts, and leases |
| **Source entities** | FinancialEntry (planned), Asset(Building), Intervention, Contract (planned), Lease (planned) |
| **Status** | `planned` |
| **BatiConnect surface** | Financial Workspace (Ops-08) |
| **Dependencies** | None |

## 5.2 Budget vs Actual Tracking

| Field | Value |
|---|---|
| **Description** | Track budget allocations against actual spend per asset, with variance analysis and alerts |
| **Source entities** | FinancialEntry (planned), Asset(Building) |
| **Status** | `partial` |
| **Service path** | `backend/app/services/budget_tracking_service.py` |
| **API path** | `backend/app/api/budget_tracking.py` |
| **BatiConnect surface** | Financial Workspace (Ops-08) |
| **Dependencies** | Financial Recording (5.1) |
| **Gap** | Service exists but derives budget from interventions/actions; formal FinancialEntry entity needed |

## 5.3 Cost-per-Asset Analysis

| Field | Value |
|---|---|
| **Description** | Compute total cost of ownership per asset including remediation, maintenance, and compliance costs |
| **Source entities** | FinancialEntry (planned), Intervention, ActionItem, Asset(Building) |
| **Status** | `partial` |
| **Service path** | `backend/app/services/remediation_cost_service.py`, `backend/app/services/cost_benefit_analysis_service.py` |
| **API path** | `backend/app/api/remediation_costs.py`, `backend/app/api/cost_benefit_analysis.py` |
| **BatiConnect surface** | Financial Workspace (Ops-08), Owner Dashboard (Ws-01) |
| **Dependencies** | Financial Recording (5.1) |
| **Gap** | Remediation cost and cost-benefit services exist; generalize to full asset costing with FinancialEntry |

## 5.4 Tax Record Management

| Field | Value |
|---|---|
| **Description** | Record tax assessments, fiscal values, and tax notices per asset |
| **Source entities** | TaxContext (planned), Asset(Building), Document |
| **Status** | `planned` |
| **BatiConnect surface** | Tax & Fiscal (Ops-09) |
| **Dependencies** | None |

## 5.5 Fiscal Year Reporting

| Field | Value |
|---|---|
| **Description** | Generate fiscal year summaries with income/expense/depreciation per asset and portfolio |
| **Source entities** | FinancialEntry (planned), TaxContext (planned), Asset(Building) |
| **Status** | `planned` |
| **BatiConnect surface** | Tax & Fiscal (Ops-09), Financial Workspace (Ops-08) |
| **Dependencies** | Financial Recording (5.1), Tax Record Management (5.4) |

## 5.6 Financial Summary Projections

| Field | Value |
|---|---|
| **Description** | Project future financial state based on planned interventions, lease income, and maintenance costs |
| **Source entities** | FinancialEntry (planned), Intervention, Lease (planned) |
| **Status** | `partial` |
| **Service path** | `backend/app/services/capex_planning_service.py` |
| **API path** | `backend/app/api/capex_planning.py` |
| **BatiConnect surface** | Financial Workspace (Ops-08), Decision Room (Ops-15) |
| **Dependencies** | Financial Recording (5.1) |
| **Gap** | Capex planning service exists for remediation investment; extend with lease income and general projections |

## 5.7 ERP Bridge (external_ref linking)

| Field | Value |
|---|---|
| **Description** | Link BatiConnect entities to external ERP identifiers for bidirectional sync and overlay positioning |
| **Source entities** | All entities (via external_ref fields) |
| **Status** | `planned` |
| **BatiConnect surface** | Asset Registry (Ops-02), Financial Workspace (Ops-08) |
| **Dependencies** | Bulk Import (1.8) |

## 5.8 Subsidy Tracking

| Field | Value |
|---|---|
| **Description** | Track available and applied subsidies for remediation and energy renovation per building |
| **Source entities** | Building, Intervention |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/subsidy_tracking_service.py` |
| **API path** | `backend/app/api/subsidy_tracking.py` |
| **BatiConnect surface** | Financial Workspace (Ops-08), Decision Room (Ops-15) |
| **Dependencies** | None |

---

# Layer 6: Readiness / Passport

## 6.1 Regulatory Readiness Assessment

| Field | Value |
|---|---|
| **Description** | Evaluate go/no-go for 4 regulatory milestones: safe_to_start, safe_to_tender, safe_to_reopen, safe_to_requalify |
| **Source entities** | ReadinessAssessment, Building, Diagnostic, Sample, Document, Intervention, ActionItem |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/readiness_reasoner.py` |
| **API path** | `backend/app/api/readiness.py` |
| **BatiConnect surface** | Diagnostic Center (Ops-14), Passport Page (Shared-05) |
| **Dependencies** | None |

## 6.2 Building Passport Generation

| Field | Value |
|---|---|
| **Description** | Aggregate building knowledge into unified passport with A-F grade across 5 sections (knowledge, readiness, blindspots, contradictions, evidence) |
| **Source entities** | Building, Diagnostic, Sample, Intervention, Document, EvidenceLink, Zone, BuildingElement, Material, ActionItem, UnknownIssue, DataQualityIssue, ReadinessAssessment, BuildingTrustScore |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/passport_service.py` |
| **API path** | `backend/app/api/passport.py` |
| **BatiConnect surface** | Passport Page (Shared-05), Owner Dashboard (Ws-01) |
| **Dependencies** | Trust Score (6.4), Completeness (6.3), Readiness (6.1) |

## 6.3 Completeness Scoring

| Field | Value |
|---|---|
| **Description** | Evaluate dossier completeness with 16 checks across 5 categories (diagnostics, samples, documents, actions, compliance) |
| **Source entities** | Building, Diagnostic, Sample, Document, ActionItem, TechnicalPlan |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/completeness_engine.py` |
| **API path** | `backend/app/api/completeness.py` |
| **BatiConnect surface** | Diagnostic Center (Ops-14), Evidence Workspace (Ops-13) |
| **Dependencies** | None |

## 6.4 Trust Scoring

| Field | Value |
|---|---|
| **Description** | Compute trust score reflecting data reliability based on proven/inferred/declared/obsolete/contradictory classification |
| **Source entities** | BuildingTrustScore, EvidenceLink, Document, Sample, Diagnostic, Intervention, Zone, BuildingElement, Material, TechnicalPlan, ActionItem |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/trust_score_calculator.py` |
| **API path** | `backend/app/api/trust_scores.py` |
| **BatiConnect surface** | Passport Page (Shared-05), Evidence Workspace (Ops-13) |
| **Dependencies** | Evidence Chain Linking (2.1) |

## 6.5 Dossier Archival with SHA-256 Versioning

| Field | Value |
|---|---|
| **Description** | Archive dossier state with content-addressed SHA-256 hash for tamper detection and version history |
| **Source entities** | DossierVersion |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/dossier_service.py` |
| **API path** | `backend/app/api/dossier.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13), Authority Pack (Shared-02) |
| **Dependencies** | None |

## 6.6 PreworkTrigger Detection

| Field | Value |
|---|---|
| **Description** | Persistent lifecycle for pre-work diagnostic requirements: sync from readiness, escalate by age/urgency, CRUD |
| **Source entities** | PreworkTrigger |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/prework_trigger_service.py` |
| **API path** | (invoked via readiness endpoints) |
| **BatiConnect surface** | Diagnostic Center (Ops-14), Ops Dashboard (Ops-01) |
| **Dependencies** | Regulatory Readiness (6.1) |

## 6.7 Transaction Readiness (sell/insure/finance/lease)

| Field | Value |
|---|---|
| **Description** | Evaluate readiness for transactional milestones using passport grade, completeness, trust, and contradiction data |
| **Source entities** | Building, Diagnostic, Sample, Intervention, EvidenceLink, UnknownIssue, DataQualityIssue |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/transaction_readiness_service.py` |
| **API path** | `backend/app/api/transaction_readiness.py` |
| **BatiConnect surface** | Decision Room (Ops-15), Owner Pack (Shared-03) |
| **Dependencies** | Passport (6.2), Completeness (6.3), Trust (6.4), Contradiction Detection (2.4) |

## 6.8 Ownership Completeness Check

| Field | Value |
|---|---|
| **Description** | Verify ownership documentation is complete for transaction readiness (title, registry extract, co-ownership shares) |
| **Source entities** | Ownership (planned), Document |
| **Status** | `planned` |
| **BatiConnect surface** | Ownership Registry (Ops-04), Owner Pack (Shared-03) |
| **Dependencies** | Ownership entity, Transaction Readiness (6.7) |

## 6.9 Occupancy-Aware Readiness

| Field | Value |
|---|---|
| **Description** | Factor lease status and tenant presence into readiness evaluations (e.g., occupied units affect safe_to_start) |
| **Source entities** | Lease (planned), ReadinessAssessment |
| **Status** | `planned` |
| **BatiConnect surface** | Diagnostic Center (Ops-14), Regie Dashboard (Ws-05) |
| **Dependencies** | Lease Lifecycle (3.1), Regulatory Readiness (6.1) |

## 6.10 Financial Readiness (for transaction)

| Field | Value |
|---|---|
| **Description** | Assess financial readiness for transactions (reserves, outstanding liabilities, remediation budget coverage) |
| **Source entities** | FinancialEntry (planned), Intervention, Building |
| **Status** | `partial` |
| **Service path** | `backend/app/services/transaction_readiness_service.py` (includes cost analysis) |
| **BatiConnect surface** | Financial Workspace (Ops-08), Owner Pack (Shared-03) |
| **Dependencies** | Transaction Readiness (6.7), Financial Recording (5.1) |
| **Gap** | Transaction readiness includes cost assessment from interventions; extend with formal FinancialEntry data |

## 6.11 Requalification Replay

| Field | Value |
|---|---|
| **Description** | Chronological state-change timeline showing why a building's grade/readiness changed over time |
| **Source entities** | ChangeSignal, BuildingSnapshot, Diagnostic, Intervention |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/requalification_service.py` |
| **API path** | `backend/app/api/requalification.py` |
| **BatiConnect surface** | Decision Room (Ops-15), Evidence Workspace (Ops-13) |
| **Dependencies** | Change Signal Generation (2.8), Building Snapshots (7.8) |

## 6.12 Compliance Timeline

| Field | Value |
|---|---|
| **Description** | Projected compliance deadlines and regulatory milestones with countdown tracking |
| **Source entities** | Building, ComplianceArtefact, RegulatoryPack |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/compliance_timeline_service.py` |
| **API path** | `backend/app/api/compliance_timeline.py` |
| **BatiConnect surface** | Diagnostic Center (Ops-14), Obligation Calendar (Ops-11) |
| **Dependencies** | Rules Pack (6.13) |

## 6.13 Rule Resolution (Pack-Driven)

| Field | Value |
|---|---|
| **Description** | Resolve applicable rules via jurisdiction hierarchy walk with canton-specific rule packs and fallback |
| **Source entities** | Jurisdiction, RegulatoryPack, PollutantRule |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/rule_resolver.py` |
| **API path** | `backend/app/api/jurisdictions.py` |
| **BatiConnect surface** | Rules Pack Studio (Ops-17), Diagnostic Center (Ops-14) |
| **Dependencies** | None |

## 6.14 Post-Works State Assessment

| Field | Value |
|---|---|
| **Description** | Generate post-intervention state from completed interventions with before/after comparison |
| **Source entities** | PostWorksState, Intervention |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/post_works_service.py` |
| **API path** | `backend/app/api/post_works.py` |
| **BatiConnect surface** | Diagnostic Center (Ops-14), Contractor Portal (Ws-04) |
| **Dependencies** | None |

---

# Layer 7: Portfolio

## 7.1 Portfolio Management

| Field | Value |
|---|---|
| **Description** | Create and manage portfolios of buildings with org-scoped access and aggregated metrics |
| **Source entities** | Portfolio (planned formal entity), Asset(Building), Organization |
| **Status** | `partial` |
| **Service path** | `backend/app/services/portfolio_summary_service.py` |
| **API path** | `backend/app/api/portfolio.py`, `backend/app/api/portfolio_summary.py` |
| **BatiConnect surface** | Ops Dashboard (Ops-01), Regie Dashboard (Ws-05) |
| **Dependencies** | None |
| **Gap** | PortfolioSummary service exists with rich aggregation; formal Portfolio entity with explicit membership is planned |

## 7.2 Building Comparison

| Field | Value |
|---|---|
| **Description** | Compare 2-10 buildings side by side across passport, trust, readiness, and completeness dimensions |
| **Source entities** | Building, BuildingTrustScore, ReadinessAssessment, DataQualityIssue, UnknownIssue, Diagnostic |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/building_comparison_service.py` |
| **API path** | `backend/app/api/building_comparison.py` |
| **BatiConnect surface** | Regie Dashboard (Ws-05), Ops Dashboard (Ops-01) |
| **Dependencies** | Passport (6.2), Completeness (6.3) |

## 7.3 Campaign Orchestration

| Field | Value |
|---|---|
| **Description** | Multi-building campaign lifecycle: create, assign buildings, link actions, track progress |
| **Source entities** | Campaign, Building, ActionItem |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/campaign_service.py`, `backend/app/services/campaign_tracking_service.py` |
| **API path** | `backend/app/api/campaigns.py`, `backend/app/api/campaign_tracking.py` |
| **BatiConnect surface** | Campaign Command (Ops-16) |
| **Dependencies** | None |

## 7.4 Campaign AI Recommendations

| Field | Value |
|---|---|
| **Description** | AI analysis of portfolio state recommending highest-impact campaigns (5 analyzers: risk cluster, readiness gap, documentation debt, pollutant prevalence, compliance deadline) |
| **Source entities** | Building, BuildingRiskScore, Diagnostic, Sample, ActionItem |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/campaign_recommender.py` |
| **API path** | `backend/app/api/campaigns.py` |
| **BatiConnect surface** | Campaign Command (Ops-16) |
| **Dependencies** | Campaign Orchestration (7.3) |

## 7.5 Portfolio Optimization

| Field | Value |
|---|---|
| **Description** | Prioritize buildings for intervention, allocate budgets optimally, identify highest-leverage actions across portfolio |
| **Source entities** | Building, ActionItem, Diagnostic |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/portfolio_optimization_service.py` |
| **API path** | `backend/app/api/portfolio_optimization.py` |
| **BatiConnect surface** | Ops Dashboard (Ops-01), Regie Dashboard (Ws-05) |
| **Dependencies** | Portfolio Management (7.1) |

## 7.6 Portfolio Trends Analysis

| Field | Value |
|---|---|
| **Description** | Analyze temporal trends in portfolio risk, compliance, completeness, and activity metrics |
| **Source entities** | Building, BuildingSnapshot, ChangeSignal, ActionItem |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/portfolio_risk_trends_service.py` |
| **API path** | `backend/app/api/portfolio_trends.py` |
| **BatiConnect surface** | Ops Dashboard (Ops-01), Regie Dashboard (Ws-05) |
| **Dependencies** | Portfolio Management (7.1), Building Snapshots (7.8) |

## 7.7 Benchmarking

| Field | Value |
|---|---|
| **Description** | Benchmark buildings against peers by age, type, location, and pollutant profile |
| **Source entities** | Building, BuildingRiskScore, Diagnostic, Sample |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/building_benchmark_service.py` |
| **API path** | `backend/app/api/building_benchmark.py` |
| **BatiConnect surface** | Ops Dashboard (Ops-01), Building Comparison |
| **Dependencies** | None |

## 7.8 Building Snapshots (Time Machine)

| Field | Value |
|---|---|
| **Description** | Point-in-time snapshots: capture, compare, list building state over time |
| **Source entities** | BuildingSnapshot |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/time_machine_service.py` |
| **API path** | `backend/app/api/building_snapshots.py` |
| **BatiConnect surface** | Decision Room (Ops-15), Evidence Workspace (Ops-13) |
| **Dependencies** | None |

## 7.9 Cross-Portfolio Obligations View

| Field | Value |
|---|---|
| **Description** | Unified view of all obligations across multiple portfolios with filtering and priority sorting |
| **Source entities** | Obligation (planned), Portfolio (planned), Asset(Building) |
| **Status** | `planned` |
| **BatiConnect surface** | Obligation Calendar (Ops-11), Regie Dashboard (Ws-05) |
| **Dependencies** | Obligation entity, Portfolio Management (7.1) |

## 7.10 Multi-Org Dashboard

| Field | Value |
|---|---|
| **Description** | Cross-organization portfolio aggregation for property management firms managing multiple owners |
| **Source entities** | Building, Organization |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/multi_org_dashboard_service.py` |
| **API path** | `backend/app/api/multi_org_dashboard.py` |
| **BatiConnect surface** | Regie Dashboard (Ws-05) |
| **Dependencies** | Portfolio Management (7.1) |

---

# Layer 8: Sharing

## 8.1 Audience-Scoped Shared Links

| Field | Value |
|---|---|
| **Description** | Create time-limited, audience-bounded sharing links with section filtering and max view enforcement |
| **Source entities** | SharedLink |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/shared_link_service.py` |
| **API path** | `backend/app/api/shared_links.py` |
| **BatiConnect surface** | Shared View (Shared-01) |
| **Dependencies** | None |

## 8.2 Evidence Packs (Authority/Contractor/Owner)

| Field | Value |
|---|---|
| **Description** | Bundle structured evidence packs for specific audiences with sections covering building identity, diagnostics, compliance, risk |
| **Source entities** | EvidencePack, Building, Diagnostic, ComplianceArtefact, Document, Intervention |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/authority_pack_service.py` |
| **API path** | `backend/app/api/authority_packs.py`, `backend/app/api/evidence_packs.py` |
| **BatiConnect surface** | Authority Pack (Shared-02), Contractor Portal (Ws-04) |
| **Dependencies** | None |

## 8.3 Export Jobs (Dossier/Handoff/Audit)

| Field | Value |
|---|---|
| **Description** | Async export job pipeline: queue, process, complete/fail with downloadable results |
| **Source entities** | ExportJob |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/handoff_pack_service.py`, `backend/app/services/audit_export_service.py` |
| **API path** | `backend/app/api/exports.py`, `backend/app/api/handoff_pack.py`, `backend/app/api/audit_export.py` |
| **BatiConnect surface** | All Ops surfaces (export action) |
| **Dependencies** | Background Jobs (Redis + Dramatiq) |

## 8.4 Transfer Package (11 Sections)

| Field | Value |
|---|---|
| **Description** | Bundle complete building intelligence into portable, auditable 11-section transfer package for handoff/sale |
| **Source entities** | Building, Diagnostic, Document, EvidenceLink, Intervention, UnknownIssue, ActionItem, BuildingSnapshot |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/transfer_package_service.py` |
| **API path** | `backend/app/api/transfer.py` |
| **BatiConnect surface** | Owner Pack (Shared-03), Decision Room (Ops-15) |
| **Dependencies** | Passport (6.2), Completeness (6.3) |

## 8.5 Shared View with Section Filtering

| Field | Value |
|---|---|
| **Description** | Render audience-scoped view of any entity with configurable visible sections |
| **Source entities** | SharedLink, any entity |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/shared_link_service.py` |
| **Frontend path** | `frontend/src/pages/SharedView.tsx` |
| **BatiConnect surface** | Shared View (Shared-01) |
| **Dependencies** | Audience-Scoped Shared Links (8.1) |

## 8.6 Insurer Pack

| Field | Value |
|---|---|
| **Description** | Dedicated underwriting assessment bundle with risk profile, trust score, pollutant state, and evidence chain |
| **Source entities** | InsurancePolicy (planned), BuildingTrustScore, BuildingRiskScore, EvidenceLink, Building |
| **Status** | `planned` |
| **BatiConnect surface** | Insurer Pack (Shared-04), Insurer Portal (Ws-06) |
| **Dependencies** | Insurance Risk Assessment (4.6), Trust Scoring (6.4) |

## 8.7 Owner Transfer Pack

| Field | Value |
|---|---|
| **Description** | Ownership transfer bundle including passport, readiness, financials, leases, and insurance for buyer/notary |
| **Source entities** | Ownership (planned), PassportSnapshot, FinancialEntry (planned), Lease (planned), InsurancePolicy (planned) |
| **Status** | `planned` |
| **BatiConnect surface** | Owner Pack (Shared-03) |
| **Dependencies** | Transfer Package (8.4), Ownership entity, Financial Recording (5.1) |

## 8.8 Public Intake Portal

| Field | Value |
|---|---|
| **Description** | Anonymous document submission portal with intake link, ClamAV scanning, and zero read access |
| **Source entities** | Document, Communication (planned) |
| **Status** | `planned` |
| **BatiConnect surface** | Public Intake (Shared-06) |
| **Dependencies** | Document Intake (1.1) |

## 8.9 Audit Trail on All Shares

| Field | Value |
|---|---|
| **Description** | Log every share action (create link, view, download) with timestamp, actor, and audience for compliance |
| **Source entities** | AuditLog, SharedLink |
| **Status** | `partial` |
| **Service path** | `backend/app/services/audit_service.py` |
| **API path** | `backend/app/api/audit_logs.py` |
| **BatiConnect surface** | All sharing surfaces |
| **Dependencies** | Audience-Scoped Shared Links (8.1) |
| **Gap** | Audit service exists for general actions; extend to explicitly log all share events with download tracking |

## 8.10 Passport Export (PDF/Exchange)

| Field | Value |
|---|---|
| **Description** | Export passport as PDF or structured exchange format for interoperability |
| **Source entities** | PassportSnapshot |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/passport_export_service.py`, `backend/app/services/passport_exchange_service.py` |
| **API path** | `backend/app/api/passport_export.py` |
| **BatiConnect surface** | Passport Page (Shared-05) |
| **Dependencies** | Passport Generation (6.2), Gotenberg (PDF) |

## 8.11 Stakeholder Reports

| Field | Value |
|---|---|
| **Description** | Generate audience-specific reports for stakeholders (owner summary, authority brief, contractor scope) |
| **Source entities** | Building, Diagnostic, Intervention |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/stakeholder_report_service.py` |
| **API path** | `backend/app/api/stakeholder_report.py` |
| **BatiConnect surface** | All sharing surfaces |
| **Dependencies** | None |

---

# Layer 9: AI / Intelligence

## 9.1 Dossier Completion Agent

| Field | Value |
|---|---|
| **Description** | Autonomous agent orchestrating unknowns + trust + completeness + readiness into unified completion report with blockers and recommendations |
| **Source entities** | Building, Diagnostic, UnknownIssue, BuildingTrustScore, ReadinessAssessment |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/dossier_completion_agent.py` |
| **API path** | `backend/app/api/dossier_completion.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13), Diagnostic Center (Ops-14) |
| **Dependencies** | Unknown Generator (2.7), Trust Scoring (6.4), Completeness (6.3), Readiness (6.1) |

## 9.2 Completion Workspace

| Field | Value |
|---|---|
| **Description** | Transform completion report into ordered, dependency-aware actionable steps for human operators |
| **Source entities** | (derived from DossierCompletionReport) |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/completion_workspace_service.py` |
| **API path** | `backend/app/api/completion_workspace.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13) |
| **Dependencies** | Dossier Completion Agent (9.1) |

## 9.3 Action Generation (Idempotent)

| Field | Value |
|---|---|
| **Description** | Auto-generate actions from diagnostic findings and readiness gaps (18 mappings, idempotent + auto-resolve) |
| **Source entities** | ActionItem, Diagnostic, ReadinessAssessment |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/action_generator.py`, `backend/app/services/readiness_action_generator.py` |
| **API path** | `backend/app/api/actions.py` |
| **BatiConnect surface** | Ops Dashboard (Ops-01), Diagnostic Center (Ops-14) |
| **Dependencies** | Readiness (6.1) |

## 9.4 Anomaly Detection (Statistical)

| Field | Value |
|---|---|
| **Description** | Scan building data for anomalies: value spikes, missing data, inconsistent states, temporal gaps, pattern deviations |
| **Source entities** | Building, BuildingRiskScore, Diagnostic, Sample, Intervention |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/anomaly_detection_service.py` |
| **API path** | `backend/app/api/anomaly_detection.py` |
| **BatiConnect surface** | Evidence Workspace (Ops-13), Ops Dashboard (Ops-01) |
| **Dependencies** | None |

## 9.5 Report Copilot

| Field | Value |
|---|---|
| **Description** | AI-assisted generation of narrative reports (diagnostic summaries, compliance narratives, stakeholder briefings) |
| **Source entities** | Building, Diagnostic, PassportSnapshot, ReadinessAssessment |
| **Status** | `planned` |
| **BatiConnect surface** | Diagnostic Center (Ops-14), Decision Room (Ops-15) |
| **Dependencies** | Passport (6.2), Readiness (6.1) |

## 9.6 Smart Intake (AI Classification + Extraction + Projection)

| Field | Value |
|---|---|
| **Description** | End-to-end AI pipeline: classify incoming document, extract structured data, match to entities, project to correct surfaces |
| **Source entities** | Document, all target entities |
| **Status** | `planned` |
| **BatiConnect surface** | Evidence Workspace (Ops-13), Communication Inbox (Ops-12) |
| **Dependencies** | Document Classification (1.5), Data Extraction (1.6), Matching (1.7) |

## 9.7 Learned Preferences (MemorySignal)

| Field | Value |
|---|---|
| **Description** | Track user and org behavioral patterns (MemorySignal) to personalize recommendations, defaults, and UI priorities |
| **Source entities** | MemorySignal (planned) |
| **Status** | `planned` |
| **BatiConnect surface** | All surfaces (personalization layer) |
| **Dependencies** | None |

## 9.8 Portfolio Intelligence (Cross-Asset Patterns)

| Field | Value |
|---|---|
| **Description** | Detect cross-asset patterns: correlated risk, shared contractors, systemic pollutant exposure, geographic clustering |
| **Source entities** | Building, BuildingRiskScore, Diagnostic, Sample |
| **Status** | `partial` |
| **Service path** | `backend/app/services/cross_building_pattern_service.py`, `backend/app/services/building_clustering_service.py`, `backend/app/services/spatial_risk_mapping_service.py` |
| **API path** | `backend/app/api/cross_building_pattern.py`, `backend/app/api/building_clustering.py`, `backend/app/api/spatial_risk_mapping.py` |
| **BatiConnect surface** | Ops Dashboard (Ops-01), Campaign Command (Ops-16) |
| **Dependencies** | Portfolio Management (7.1) |
| **Gap** | Cross-building pattern, clustering, and spatial risk services exist; enhance with formal MemorySignal feedback loop |

## 9.9 Financial Anomaly Detection

| Field | Value |
|---|---|
| **Description** | Detect unusual financial patterns: cost spikes, budget overruns, suspicious invoicing across portfolio |
| **Source entities** | FinancialEntry (planned), Intervention, Contract (planned) |
| **Status** | `planned` |
| **BatiConnect surface** | Financial Workspace (Ops-08), Ops Dashboard (Ops-01) |
| **Dependencies** | Financial Recording (5.1), Anomaly Detection (9.4) |

## 9.10 Scenario Planning

| Field | Value |
|---|---|
| **Description** | Model what-if scenarios for interventions, regulatory changes, and budget allocation across buildings |
| **Source entities** | Building, Intervention, Diagnostic, ActionItem, SavedSimulation |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/scenario_planning_service.py`, `backend/app/services/intervention_simulator.py`, `backend/app/services/counterfactual_analysis_service.py` |
| **API path** | `backend/app/api/scenario_planning.py`, `backend/app/api/saved_simulations.py` |
| **BatiConnect surface** | Decision Room (Ops-15), Campaign Command (Ops-16) |
| **Dependencies** | Passport (6.2), Readiness (6.1) |

## 9.11 Weak Signal Watchtower

| Field | Value |
|---|---|
| **Description** | Continuous monitoring for early warning signals: emerging risk patterns, regulatory shifts, building degradation trends |
| **Source entities** | ChangeSignal, BuildingRiskScore, Building |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/weak_signal_watchtower.py` |
| **API path** | `backend/app/api/weak_signals.py` |
| **BatiConnect surface** | Ops Dashboard (Ops-01) |
| **Dependencies** | Change Signal Generation (2.8) |

## 9.12 Risk Engine (Core)

| Field | Value |
|---|---|
| **Description** | Core risk probability algorithm computing pollutant risk scores per building based on age, materials, diagnostics, and Swiss regulatory thresholds |
| **Source entities** | Building, Diagnostic, Sample, BuildingRiskScore |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/risk_engine.py` |
| **API path** | `backend/app/api/risk_analysis.py` |
| **BatiConnect surface** | Diagnostic Center (Ops-14), Passport Page (Shared-05) |
| **Dependencies** | None |

## 9.13 Renovation Sequencing

| Field | Value |
|---|---|
| **Description** | Optimal sequencing of renovation interventions considering dependencies, costs, and risk reduction |
| **Source entities** | Building, Intervention, ActionItem |
| **Status** | `implemented` |
| **Service path** | `backend/app/services/renovation_sequencer_service.py` |
| **API path** | `backend/app/api/renovation_sequencer.py` |
| **BatiConnect surface** | Decision Room (Ops-15) |
| **Dependencies** | Scenario Planning (9.10) |

---

# Appendix A: Capability Status Summary

| Status | Count | Percentage |
|---|---|---|
| `implemented` | 47 | 54% |
| `partial` | 10 | 12% |
| `planned` | 29 | 34% |
| **Total** | **86** | 100% |

## By Layer

| Layer | Implemented | Partial | Planned | Total |
|---|---|---|---|---|
| 1. Ingestion | 4 | 0 | 5 | 9 |
| 2. Truth/Evidence | 9 | 1 | 0 | 10 + 1 |
| 3. Occupancy | 0 | 0 | 7 | 7 |
| 4. Contractual/Insurance | 3 | 0 | 5 | 8 |
| 5. Financial/Fiscal | 1 | 3 | 4 | 8 |
| 6. Readiness/Passport | 10 | 1 | 3 | 14 |
| 7. Portfolio | 7 | 1 | 1 | 9 + 1 |
| 8. Sharing | 7 | 1 | 3 | 11 |
| 9. AI/Intelligence | 8 | 1 | 4 | 13 |

---

# Appendix B: Key Implementation Gaps for BatiConnect

## New Canonical Entities Required

| Entity | Layer | Blocking Capabilities |
|---|---|---|
| Portfolio | 7 | Portfolio Management (formal), Cross-Portfolio Obligations |
| Unit | 3 | All occupancy capabilities, Lease Management |
| Party | 3, 4, 5 | Contact Manager, Ownership, Lease, Contract, Insurance |
| PartyRoleAssignment | 3 | Party Manager role assignment |
| Ownership | 6 | Ownership Registry, Ownership Completeness Check |
| Lease | 3 | All occupancy capabilities |
| LeaseEvent | 3 | Lease Event History, Rent Index Adjustment |
| Contract | 4 | Contract Lifecycle, SLA, Obligation Auto-Generation |
| InsurancePolicy | 4 | Policy Management, Insurer Pack |
| Claim | 4 | Claims Workflow |
| Communication | 1, 8 | Communication Inbox, Mail Parsing |
| Obligation | 4, 7 | Obligation Calendar, SLA Monitoring |
| FinancialEntry | 5 | All financial capabilities |
| TaxContext | 5 | Tax Record Management, Fiscal Reporting |
| InventoryItem | 3 | Inventory & Equipment |
| Recommendation | 9 | Next-Best-Action (formal) |
| AIAnalysis | 9 | Report Copilot |
| MemorySignal | 9 | Learned Preferences |

## New Roles Required

| Role | Surfaces | Dependencies |
|---|---|---|
| tenant | Tenant Portal (Ws-02) | Lease entity |
| insurer | Insurer Portal (Ws-06) | InsurancePolicy entity |

## Strongest Layers (highest implementation ratio)

1. **Truth/Evidence** (Layer 2): 91% implemented -- core strength
2. **Readiness/Passport** (Layer 6): 71% implemented -- core differentiation
3. **Portfolio** (Layer 7): 78% implemented -- operational
4. **AI/Intelligence** (Layer 9): 62% implemented -- strong foundation

## Weakest Layers (most planned work)

1. **Occupancy** (Layer 3): 100% planned -- entirely new
2. **Contractual** (Layer 4): 62% planned -- mostly new
3. **Financial** (Layer 5): 50% planned -- partially covered by remediation cost services

---

## Planned -- Remediation Marketplace

> Mise en concurrence encadree for pollutant remediation. Closed verified network with 5 delivery lots.

### MKT-1: Company Verification and Onboarding

| Field | Value |
|---|---|
| **Description** | Verify remediation companies (certifications, SUVA recognition, trade categories, service regions) before they can receive RFQs |
| **Source entities** | CompanyProfile, CompanyVerification |
| **Status** | `planned` |
| **Dependencies** | Organization backbone, Document Intake (1.1) |

### MKT-2: Neutral RFQ Lifecycle

| Field | Value |
|---|---|
| **Description** | Property managers create ClientRequests (RFQs) scoped to building + pollutant type + work category. Verified companies receive RequestInvitations and submit Quotes. No platform ranking or recommendation. |
| **Source entities** | ClientRequest, RequestDocument, RequestInvitation, Quote |
| **Status** | `planned` |
| **Dependencies** | MKT-1, Building asset, Document Intake (1.1) |

### MKT-3: Award and Trust Chain

| Field | Value |
|---|---|
| **Description** | Formal award of RFQ to selected quote with hash-signed AwardConfirmation. Post-works CompletionConfirmation with dual sign-off. Verified Review only after confirmed completion. |
| **Source entities** | AwardConfirmation, CompletionConfirmation, Review |
| **Status** | `planned` |
| **Dependencies** | MKT-2 |

### MKT-4: Subscription Monetization

| Field | Value |
|---|---|
| **Description** | Company subscription management (plan tiers, billing lifecycle). Subscription tier does NOT influence visibility or ranking in RFQ results. |
| **Source entities** | CompanySubscription |
| **Status** | `planned` |
| **Dependencies** | MKT-1 |

### MKT-5: Site Integration

| Field | Value |
|---|---|
| **Description** | Public-facing company profiles, RFQ submission forms, and marketplace navigation integrated into BatiConnect Workspace surface |
| **Source entities** | CompanyProfile (read projection) |
| **Status** | `planned` |
| **Dependencies** | MKT-1, MKT-2 |

### Marketplace Invariants

- No recommendation: platform never ranks or recommends companies to clients
- Payment != ranking: subscription tier does not influence visibility in RFQ results
- Verified contracts only: awards and reviews require completed verification chain
