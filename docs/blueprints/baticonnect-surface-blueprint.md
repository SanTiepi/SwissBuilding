# BatiConnect Surface Blueprint

> BatiConnect -- l'OS de verite, de preuve, de completude et de decision des actifs immobiliers.

Version: 1.0 | Date: 2026-03-21

---

## Architecture

Two app surfaces built on a shared canonical write-side:

- **BatiConnect Ops** -- internal/operator/backoffice/orchestration/intelligence
- **BatiConnect Workspace** -- client/partner/regie/authority/owner/portfolio

Canonical root: `Asset` (first concrete shape = `Building`).
`Party` separated from org/role; explicit `PartyRoleAssignment`.
Read models (Passport, Readiness, Pack, SharedView, PortfolioSummary) = derived projections, never primary truth.

---

## Surface Schema

For each surface:
- **Source objects**: which write-side truth entities are consumed
- **Read model**: which projection is used (or direct entity read)
- **Actor roles**: which roles see this surface
- **Exposure constraints**: what is hidden/filtered by role
- **Primary CTAs**: main user actions available

---

# Part 1: BatiConnect Ops Surfaces

## Ops-01: Ops Dashboard

| Field | Value |
|---|---|
| **Source objects** | Portfolio, Asset(Building), Obligation, ChangeSignal, Recommendation, ActionItem, BuildingRiskScore |
| **Read model** | PortfolioSummary (via `portfolio_summary_service`) + ObligationCalendar (planned) |
| **Actor roles** | admin (full), owner (scoped to org) |
| **Exposure constraints** | owner sees only own org buildings; admin sees all. Internal analytics (anomaly scores, agent reports) hidden from non-admin |
| **Primary CTAs** | Navigate to asset detail, acknowledge obligation, view recommendation, drill into risk cluster, open campaign |

**Current implementation**: Dashboard.tsx (partial -- shows risk/compliance/activity overview). PortfolioSummary service exists. Obligation entity and ObligationCalendar projection are planned.

---

## Ops-02: Asset Registry

| Field | Value |
|---|---|
| **Source objects** | Asset(Building), Unit (planned), Zone, BuildingElement, Material, TechnicalPlan |
| **Read model** | Direct entity read + BuildingDashboard (via `building_dashboard_service`) |
| **Actor roles** | admin (full CRUD), owner/diagnostician/architect (scoped read), contractor (assigned assets only) |
| **Exposure constraints** | Non-admin roles see only buildings in their org scope. Contractor sees only assigned buildings. Financial data excluded from diagnostician view |
| **Primary CTAs** | Create asset, add unit (planned), view physical structure (zones/elements/materials), link to portfolio, open explorer, manage plans |

**Current implementation**: BuildingsList.tsx + BuildingDetail.tsx (5 tabs: overview/activity/diagnostics/documents/details) + BuildingExplorer.tsx + BuildingPlans.tsx. Backend: `building_service`, `building_dashboard_service`, Zone/Element/Material CRUD APIs. Unit entity is planned.

---

## Ops-03: Party & Contact Manager

| Field | Value |
|---|---|
| **Source objects** | Party (planned), PartyRoleAssignment (planned), Organization, User, Assignment |
| **Read model** | Direct entity read |
| **Actor roles** | admin (full CRUD), owner (own org contacts) |
| **Exposure constraints** | Non-admin sees only contacts within own org. Email/phone hidden from unauthorized roles |
| **Primary CTAs** | Create contact, assign role, link to user account, import from ERP (planned), manage assignments |

**Current implementation**: AdminUsers.tsx + AdminOrganizations.tsx + Assignments.tsx. Backend: User/Organization CRUD + Assignment service. Party and PartyRoleAssignment entities are planned -- currently modeled as User + Organization + Assignment.

---

## Ops-04: Ownership Registry

| Field | Value |
|---|---|
| **Source objects** | Ownership (planned), Asset(Building), Party (planned), Document |
| **Read model** | Direct entity read |
| **Actor roles** | admin (full CRUD), owner (read own), authority (read for compliance) |
| **Exposure constraints** | Owner sees only own assets. Authority sees compliance-relevant ownership data only. Financial terms hidden from authority |
| **Primary CTAs** | Record ownership, transfer ownership (planned), view ownership history (planned), attach proof document |

**Current implementation**: Co-ownership service exists (`co_ownership_service.py`, API `co_ownership.py`). Formal Ownership entity with full lifecycle is planned.

---

## Ops-05: Lease Management

| Field | Value |
|---|---|
| **Source objects** | Lease (planned), LeaseEvent (planned), Unit (planned), Party (planned), Asset(Building) |
| **Read model** | OccupancyDashboard (planned) |
| **Actor roles** | admin (full CRUD), owner (own assets) |
| **Exposure constraints** | Owner sees only own portfolio leases. Tenant financial terms visible only to admin/owner |
| **Primary CTAs** | Create lease, terminate, renew, adjust rent, view vacancy, track lease events |

**Current implementation**: Planned. Tenant impact service exists (`tenant_impact_service.py`) for pollutant-related tenant impact assessment, but no Lease entity or lifecycle management yet.

---

## Ops-06: Contract Management

| Field | Value |
|---|---|
| **Source objects** | Contract (planned), Asset(Building), Party (planned), Obligation (planned) |
| **Read model** | Direct entity read |
| **Actor roles** | admin (full CRUD), owner (own contracts) |
| **Exposure constraints** | Owner sees only contracts for own assets. Financial terms visible to admin/owner only |
| **Primary CTAs** | Create contract, renew, terminate, track SLA (planned), view obligations, link to asset |

**Current implementation**: Planned. Warranty obligations service exists (`warranty_obligations_service.py`) but formal Contract entity not yet created.

---

## Ops-07: Insurance & Claims

| Field | Value |
|---|---|
| **Source objects** | InsurancePolicy (planned), Claim (planned), Asset(Building), Party (planned), Document, Intervention |
| **Read model** | InsuranceRiskAssessment (via `insurance_risk_assessment_service`) |
| **Actor roles** | admin (full CRUD), owner (own policies), authority (read) |
| **Exposure constraints** | Owner sees own policies only. Authority sees compliance-relevant insurance status. Premium details hidden from authority |
| **Primary CTAs** | Add policy, file claim (planned), track claim status (planned), attach evidence, view risk assessment |

**Current implementation**: `insurance_risk_assessment_service.py` (implemented -- risk tier, coverage restrictions, comparison). InsurancePolicy and Claim entities are planned.

---

## Ops-08: Financial Workspace

| Field | Value |
|---|---|
| **Source objects** | FinancialEntry (planned), Asset(Building), Lease (planned), Contract (planned), Intervention |
| **Read model** | BuildingFinancialProfile (planned) |
| **Actor roles** | admin (full CRUD), owner (own assets) |
| **Exposure constraints** | Strictly scoped to org. No cross-org financial visibility. Diagnostician/contractor have zero financial access |
| **Primary CTAs** | Record expense/income, view budget vs actual, export report, view cost-per-asset, capex planning |

**Current implementation**: `budget_tracking_service.py` (implemented -- budget allocation, tracking, variance). `capex_planning_service.py` (implemented). `remediation_cost_service.py` (implemented). `cost_benefit_analysis_service.py` (implemented). FinancialEntry entity is planned; current services derive costs from interventions/actions.

---

## Ops-09: Tax & Fiscal

| Field | Value |
|---|---|
| **Source objects** | TaxContext (planned), Asset(Building), Document |
| **Read model** | Direct entity read |
| **Actor roles** | admin (full CRUD), owner (own assets) |
| **Exposure constraints** | Tax data visible only to admin and asset owner. No cross-org visibility |
| **Primary CTAs** | Record tax assessment (planned), view fiscal summary (planned), attach tax notice, link to financial entries |

**Current implementation**: Planned. No TaxContext entity or fiscal services exist yet.

---

## Ops-10: Inventory & Equipment

| Field | Value |
|---|---|
| **Source objects** | InventoryItem (planned), Asset(Building), Zone, Contract (planned) |
| **Read model** | Direct entity read |
| **Actor roles** | admin (full CRUD), owner (own assets), contractor (assigned items) |
| **Exposure constraints** | Contractor sees only items assigned to them. Owner sees own asset inventory |
| **Primary CTAs** | Add equipment (planned), schedule maintenance (planned), link to contract, view by zone |

**Current implementation**: `material_inventory_service.py` (implemented -- tracks materials/pollutants across zones). InventoryItem as a formal entity for non-pollutant equipment is planned.

---

## Ops-11: Obligation Calendar

| Field | Value |
|---|---|
| **Source objects** | Obligation (planned), Contract (planned), Lease (planned), InsurancePolicy (planned), ComplianceArtefact, RegulatoryDeadline |
| **Read model** | ObligationCalendar (planned, composed from multiple sources) |
| **Actor roles** | all roles (scoped to their accessible entities) |
| **Exposure constraints** | Each role sees only obligations related to entities they can access. Financial obligation amounts hidden from non-admin/non-owner |
| **Primary CTAs** | Acknowledge obligation, complete, snooze, create manual obligation, view deadline calendar |

**Current implementation**: `compliance_calendar_service.py` (implemented -- regulatory compliance deadlines). `regulatory_deadline_service.py` (implemented). `warranty_obligations_service.py` (implemented). Formal Obligation entity unifying all obligation types is planned.

---

## Ops-12: Communication Inbox

| Field | Value |
|---|---|
| **Source objects** | Communication (planned: Thread + Message), Asset(Building), Lease (planned), Contract (planned), Party (planned) |
| **Read model** | Direct entity read |
| **Actor roles** | all roles (scoped to relevant threads) |
| **Exposure constraints** | Users see only threads where they are participants. Internal ops threads hidden from workspace users |
| **Primary CTAs** | Create thread (planned), send message (planned), attach document, close thread, link to entity |

**Current implementation**: Notification system exists (`notification_service`, `notification_digest_service`, `notification_rules_service`). Formal Communication entity with threaded messaging is planned.

---

## Ops-13: Evidence Workspace

| Field | Value |
|---|---|
| **Source objects** | EvidenceItem (EvidenceLink), Document, Sample, Diagnostic, FieldObservation, ExpertReview |
| **Read model** | EvidenceChain (via `evidence_chain_service`) + EvidenceGraph (via `evidence_graph_service`) |
| **Actor roles** | admin, diagnostician, architect |
| **Exposure constraints** | Diagnostician sees evidence for assigned buildings. Architect sees structural evidence. Contractor excluded from evidence workspace |
| **Primary CTAs** | Link evidence, build proof chain, detect contradictions, view evidence graph, verify field observations |

**Current implementation**: Fully implemented. Services: `evidence_facade.py`, `evidence_chain_service.py`, `evidence_graph_service.py`, `contradiction_detector.py`, `field_observation_service.py`, `expert_review_service.py`, `data_provenance_service.py`. Frontend: BuildingExplorer.tsx, FieldObservations.tsx. APIs: `evidence.py`, `evidence_chain.py`, `evidence_graph.py`, `evidence_packs.py`, `field_observations.py`, `expert_reviews.py`.

---

## Ops-14: Diagnostic Center

| Field | Value |
|---|---|
| **Source objects** | Diagnostic, Sample, Material, ReadinessAssessment, ComplianceArtefact, Zone, BuildingElement |
| **Read model** | ReadinessState (via `readiness_reasoner`) + CompletenessResult (via `completeness_engine`) |
| **Actor roles** | admin, diagnostician, authority |
| **Exposure constraints** | Authority sees only validated diagnostics and compliance submissions. Draft/in-progress diagnostics hidden from authority. Internal notes hidden from non-diagnostician |
| **Primary CTAs** | Create diagnostic, add samples, validate findings, submit compliance artefact, evaluate readiness, manage lab results |

**Current implementation**: Fully implemented. Services: `diagnostic_service.py`, `completeness_engine.py`, `readiness_reasoner.py`, `compliance_artefact_service.py`, `compliance_engine.py`, `lab_result_service.py`, `sample_optimization_service.py`. Frontend: DiagnosticView.tsx, BuildingSamples.tsx, ReadinessWallet.tsx, SafeToXCockpit.tsx, ComplianceArtefacts.tsx. APIs: `diagnostics.py`, `samples.py`, `readiness.py`, `completeness.py`, `compliance_artefacts.py`.

---

## Ops-15: Decision Room

| Field | Value |
|---|---|
| **Source objects** | DecisionRecord, ExpertReview, SavedSimulation, Recommendation (planned), ActionItem |
| **Read model** | DecisionRoom (planned projection; current: direct entity reads) |
| **Actor roles** | admin, owner, architect |
| **Exposure constraints** | Owner sees only decisions for own assets. Architect sees structural decisions. Internal scoring hidden from non-admin |
| **Primary CTAs** | Record decision, run simulation, request expert review, compare scenarios, view decision history |

**Current implementation**: Partial. Models: `decision_record.py`, `expert_review.py`, `saved_simulation.py`. Services: `intervention_simulator.py`, `expert_review_service.py`, `scenario_planning_service.py`, `counterfactual_analysis_service.py`, `decision_replay_service.py`. Frontend: InterventionSimulator.tsx, SavedSimulations.tsx, RiskSimulator.tsx. DecisionRoom as unified projection is planned.

---

## Ops-16: Campaign Command

| Field | Value |
|---|---|
| **Source objects** | Campaign, Asset(Building), ActionItem, Portfolio (planned formal entity) |
| **Read model** | CampaignProgress (via `campaign_tracking_service`) + CampaignRecommendation (via `campaign_recommender`) |
| **Actor roles** | admin, owner |
| **Exposure constraints** | Owner sees only campaigns for own org buildings. Campaign cost details visible to admin/owner only |
| **Primary CTAs** | Create campaign, assign assets, track progress, view AI recommendations, compare campaign scenarios |

**Current implementation**: Fully implemented. Services: `campaign_service.py`, `campaign_recommender.py`, `campaign_tracking_service.py`. Frontend: Campaigns.tsx. APIs: `campaigns.py`, `campaign_tracking.py`. Model: `campaign.py`.

---

## Ops-17: Rules Pack Studio

| Field | Value |
|---|---|
| **Source objects** | Jurisdiction, RegulatoryPack, PollutantRule |
| **Read model** | Direct entity read |
| **Actor roles** | admin |
| **Exposure constraints** | Admin-only surface. No visibility to any other role |
| **Primary CTAs** | Create rule pack, edit thresholds, manage jurisdictions, simulate pack impact, view regulatory change impact |

**Current implementation**: Fully implemented. Services: `rule_resolver.py`, `pack_impact_service.py`, `regulatory_change_impact_service.py`. Frontend: RulesPackStudio.tsx, AdminJurisdictions.tsx. APIs: `jurisdictions.py`, `pack_impact.py`, `regulatory_change_impact.py`. Models: `jurisdiction.py`, `regulatory_pack.py`, `pollutant_rule.py`.

---

# Part 2: BatiConnect Workspace Surfaces

## Ws-01: Owner Dashboard

| Field | Value |
|---|---|
| **Source objects** | Asset(Building), FinancialEntry (planned), Obligation (planned), Lease (planned), InsurancePolicy (planned) |
| **Read model** | PortfolioSummary (scoped to owner's assets, via `portfolio_summary_service`) |
| **Actor roles** | owner |
| **Exposure constraints** | Only own assets visible. No internal diagnostician notes, agent reports, or admin analytics. No cross-org data |
| **Primary CTAs** | View assets, view financials (planned), view obligations (planned), download packs, view readiness status |

**Current implementation**: Partial. Portfolio.tsx provides portfolio-level view. Owner role scoping implemented via RBAC. Financial/lease/obligation sections planned pending new entities.

---

## Ws-02: Tenant Portal

| Field | Value |
|---|---|
| **Source objects** | Lease (planned), Communication (planned), Document, Obligation (planned) |
| **Read model** | Direct entity read (scoped to tenant's lease) |
| **Actor roles** | tenant (planned role) or via shared link |
| **Exposure constraints** | Only own lease visible. Only approved communications. No building-level diagnostics, risk scores, or financial data. No other tenant data |
| **Primary CTAs** | View lease details (planned), send message (planned), view documents, report incident (planned) |

**Current implementation**: Planned. No tenant role exists. SharedView.tsx could serve as interim access mechanism via shared links.

---

## Ws-03: Authority Portal

| Field | Value |
|---|---|
| **Source objects** | ComplianceArtefact, ReadinessAssessment, EvidencePack, Asset(Building) |
| **Read model** | SharedPack/AuthorityPack (via `authority_pack_service`) |
| **Actor roles** | authority |
| **Exposure constraints** | Compliance-relevant data only. No financials, no internal notes, no tenant data, no insurance details. Only validated diagnostics visible |
| **Primary CTAs** | Review submissions, acknowledge artefacts, request additional info, download authority packs, verify evidence |

**Current implementation**: Largely implemented. Services: `authority_pack_service.py`, `compliance_artefact_service.py`, `regulatory_filing_service.py`. Frontend: AuthorityPacks.tsx, ComplianceArtefacts.tsx. APIs: `authority_packs.py`, `compliance_artefacts.py`. Authority role exists with RBAC scoping.

---

## Ws-04: Partner/Contractor Portal

| Field | Value |
|---|---|
| **Source objects** | Intervention, ContractorAcknowledgment, ActionItem, Asset(Building) |
| **Read model** | Direct entity read (scoped to assigned interventions) |
| **Actor roles** | contractor |
| **Exposure constraints** | Only assigned interventions and assets visible. No diagnostics, financials, compliance, or evidence data. Safety requirements always visible for assigned work |
| **Primary CTAs** | Acknowledge safety requirements, view work scope, report completion, view assigned actions |

**Current implementation**: Largely implemented. Services: `contractor_acknowledgment_service.py`, `contractor_matching_service.py`. APIs: `contractor_acknowledgment.py`, `contractor_matching.py`. Model: `contractor_acknowledgment.py`. Contractor role exists with RBAC scoping. Frontend: contractor-specific views within BuildingInterventions.tsx.

---

## Ws-05: Regie/Manager Dashboard

| Field | Value |
|---|---|
| **Source objects** | Portfolio (planned), Asset(Building), Lease (planned), Contract (planned), FinancialEntry (planned), Obligation (planned) |
| **Read model** | PortfolioSummary + OccupancyDashboard (planned) |
| **Actor roles** | owner (property_management org type) |
| **Exposure constraints** | Only managed portfolio visible. Cross-portfolio comparison only within own management scope. Individual owner financials hidden |
| **Primary CTAs** | View vacancy (planned), manage leases (planned), track rent (planned), manage contracts (planned), view portfolio health, run campaigns |

**Current implementation**: Partial. Portfolio.tsx + BuildingComparison.tsx provide portfolio views. PortfolioSummary service implemented. Multi-org dashboard service exists (`multi_org_dashboard_service.py`). Lease/contract/occupancy management planned.

---

## Ws-06: Insurer Portal

| Field | Value |
|---|---|
| **Source objects** | InsurancePolicy (planned), Claim (planned), Asset(Building), EvidencePack |
| **Read model** | SharedPack (Insurer Pack, planned) + InsuranceRiskAssessment (via `insurance_risk_assessment_service`) |
| **Actor roles** | insurer (planned role) or via shared link |
| **Exposure constraints** | Policy/claim data + building risk profile only. No internal notes, no tenant data, no financial details beyond insured values. Evidence limited to risk-relevant items |
| **Primary CTAs** | Review claims (planned), assess risk, view evidence packs, download insurer pack (planned) |

**Current implementation**: Partial. `insurance_risk_assessment_service.py` (implemented -- risk tier, restrictions, comparison). SharedView.tsx as interim access. Insurer role and dedicated portal planned.

---

# Part 3: Shared/Public Surfaces

## Shared-01: Shared View

| Field | Value |
|---|---|
| **Source objects** | Any entity via SharedLink |
| **Read model** | SharedView (audience-scoped, via `shared_link_service`) |
| **Actor roles** | anonymous (with valid link token) |
| **Exposure constraints** | Only sections allowed by `SharedLink.allowed_sections`. Time-limited (configurable expiry). Max view count enforced. No edit capability |
| **Primary CTAs** | View, download PDF, verify provenance (no edit) |

**Current implementation**: Implemented. Service: `shared_link_service.py`. Frontend: SharedView.tsx. API: `shared_links.py`. Model: `shared_link.py`. Supports audience types, section filtering, expiry, max views.

---

## Shared-02: Authority Pack

| Field | Value |
|---|---|
| **Source objects** | ComplianceArtefact, Diagnostic, EvidenceLink, ReadinessAssessment, Sample, Document |
| **Read model** | SharedPack (via `authority_pack_service`) |
| **Actor roles** | authority (via portal), anonymous (via shared link) |
| **Exposure constraints** | Regulatory-grade bundle only. Structured sections: building identity, diagnostics, samples, compliance, risk, interventions, documents. No financials or internal notes |
| **Primary CTAs** | Verify, download, share with authority body |

**Current implementation**: Implemented. Service: `authority_pack_service.py`. Frontend: AuthorityPacks.tsx. API: `authority_packs.py`. Model: `evidence_pack.py`.

---

## Shared-03: Owner Pack

| Field | Value |
|---|---|
| **Source objects** | Ownership (planned), PassportSnapshot, FinancialEntry (planned), Lease (planned), InsurancePolicy (planned) |
| **Read model** | SharedPack (Owner Transfer variant, via `transfer_package_service`) |
| **Actor roles** | owner, anonymous (via shared link to buyer/notary) |
| **Exposure constraints** | Ownership transfer bundle. Includes passport grade, readiness state, evidence summary. Financial details included only when explicitly allowed. Tenant PII redacted |
| **Primary CTAs** | Generate pack, review contents, share with buyer/notary |

**Current implementation**: Partial. `transfer_package_service.py` (implemented -- 11-section building intelligence bundle). Owner-specific pack variant with financial/lease sections planned pending new entities.

---

## Shared-04: Insurer Pack

| Field | Value |
|---|---|
| **Source objects** | InsurancePolicy (planned), BuildingTrustScore, BuildingRiskScore, EvidenceLink, Asset(Building) |
| **Read model** | SharedPack (Insurer variant, planned) |
| **Actor roles** | insurer (planned), anonymous (via shared link) |
| **Exposure constraints** | Underwriting assessment bundle. Risk profile, trust score, evidence chain for pollutant state. No tenant data, no financial details beyond insured values |
| **Primary CTAs** | Generate, review, share with insurer |

**Current implementation**: Partial. `insurance_risk_assessment_service.py` (risk assessment implemented). SharedPack insurer variant and dedicated generation flow planned.

---

## Shared-05: Passport Page

| Field | Value |
|---|---|
| **Source objects** | Full building state: Diagnostic, Sample, Intervention, Document, EvidenceLink, Zone, BuildingElement, Material, ActionItem, UnknownIssue, DataQualityIssue, ReadinessAssessment, BuildingTrustScore |
| **Read model** | PassportSnapshot (via `passport_service`) |
| **Actor roles** | all roles (with access to building), anonymous (via shared link, audience-filtered) |
| **Exposure constraints** | Public-facing building passport. Audience filtering controls visible sections. Anonymous users see grade + summary only. Full evidence detail requires authenticated access |
| **Primary CTAs** | View grade (A-F), explore sections (knowledge/readiness/blindspots/contradictions/evidence), verify evidence provenance |

**Current implementation**: Implemented. Service: `passport_service.py` (A-F grade, 5 sections). API: `passport.py`, `passport_export.py`. `passport_exchange_service.py` (cross-building passport exchange). SharedView.tsx for public access. PassportSnapshot model: `building_passport_state.py`.

---

## Shared-06: Public Intake

| Field | Value |
|---|---|
| **Source objects** | Document (incoming), Communication (incoming, planned) |
| **Read model** | None (write-only surface) |
| **Actor roles** | anonymous (with intake link) |
| **Exposure constraints** | Submission only, zero read access. No building data visible. Upload size/type restrictions enforced. ClamAV scanning on all uploads |
| **Primary CTAs** | Upload document, submit information, send message (planned) |

**Current implementation**: Planned. File upload with ClamAV scanning exists (`file_processing_service.py`). Public intake portal with anonymous submission flow is planned.

---

# Appendix: Role-Surface Access Matrix

| Surface | admin | owner | diagnostician | architect | authority | contractor | tenant* | insurer* | anonymous |
|---|---|---|---|---|---|---|---|---|---|
| Ops Dashboard | full | scoped | - | - | - | - | - | - | - |
| Asset Registry | full | scoped | scoped | scoped | - | assigned | - | - | - |
| Party & Contact Manager | full | scoped | - | - | - | - | - | - | - |
| Ownership Registry | full | scoped | - | - | read | - | - | - | - |
| Lease Management | full | scoped | - | - | - | - | - | - | - |
| Contract Management | full | scoped | - | - | - | - | - | - | - |
| Insurance & Claims | full | scoped | - | - | read | - | - | - | - |
| Financial Workspace | full | scoped | - | - | - | - | - | - | - |
| Tax & Fiscal | full | scoped | - | - | - | - | - | - | - |
| Inventory & Equipment | full | scoped | - | - | - | assigned | - | - | - |
| Obligation Calendar | full | scoped | scoped | scoped | scoped | scoped | - | - | - |
| Communication Inbox | full | scoped | scoped | scoped | scoped | scoped | - | - | - |
| Evidence Workspace | full | - | scoped | scoped | - | - | - | - | - |
| Diagnostic Center | full | - | scoped | - | scoped | - | - | - | - |
| Decision Room | full | scoped | - | scoped | - | - | - | - | - |
| Campaign Command | full | scoped | - | - | - | - | - | - | - |
| Rules Pack Studio | full | - | - | - | - | - | - | - | - |
| Owner Dashboard | - | full | - | - | - | - | - | - | - |
| Tenant Portal | - | - | - | - | - | - | full* | - | - |
| Authority Portal | - | - | - | - | full | - | - | - | - |
| Contractor Portal | - | - | - | - | - | scoped | - | - | - |
| Regie/Manager Dashboard | - | scoped | - | - | - | - | - | - | - |
| Insurer Portal | - | - | - | - | - | - | - | full* | - |
| Shared View | - | - | - | - | - | - | - | - | link |
| Passport Page | scoped | scoped | scoped | scoped | scoped | scoped | - | - | link |
| Public Intake | - | - | - | - | - | - | - | - | link |

`*` = planned role, `scoped` = filtered to accessible entities, `link` = via shared link token

---

# Appendix: Entity-to-Surface Mapping

## Write-Side Entities

| Entity | Status | Primary Surfaces |
|---|---|---|
| Portfolio | planned | Ops Dashboard, Campaign Command, Regie Dashboard |
| Asset (=Building) | implemented | Asset Registry, all surfaces |
| Unit | planned | Asset Registry, Lease Management |
| Party | planned | Party Manager, Ownership, Lease, Contract |
| PartyRoleAssignment | planned | Party Manager |
| Ownership | planned | Ownership Registry, Owner Pack |
| Lease | planned | Lease Management, Tenant Portal, Regie Dashboard |
| Contract | planned | Contract Management, Obligation Calendar |
| InsurancePolicy | planned | Insurance & Claims, Insurer Portal, Insurer Pack |
| Claim | planned | Insurance & Claims, Insurer Portal |
| Document | implemented | Evidence Workspace, all sharing surfaces |
| EvidenceItem (EvidenceLink) | implemented | Evidence Workspace, Authority Pack |
| Communication | planned | Communication Inbox, Tenant Portal |
| Obligation | planned | Obligation Calendar, Ops Dashboard |
| Incident | planned | Insurance & Claims, Communication Inbox |
| Intervention | implemented | Contractor Portal, Decision Room |
| FinancialEntry | planned | Financial Workspace, Owner Dashboard |
| TaxContext | planned | Tax & Fiscal |
| InventoryItem | planned | Inventory & Equipment |
| Recommendation | planned | Ops Dashboard, Decision Room |
| AIAnalysis | planned | Decision Room, Ops Dashboard |
| MemorySignal | planned | (internal -- feeds AI layer) |

## Read-Side Projections

| Projection | Status | Consumed By |
|---|---|---|
| PassportSnapshot | implemented | Passport Page, Owner Pack, all dashboards |
| ReadinessState | implemented | Diagnostic Center, SafeToX Cockpit |
| PortfolioSummary | implemented | Ops Dashboard, Owner Dashboard, Regie Dashboard |
| CompletionWorkspace | implemented | Evidence Workspace, Diagnostic Center |
| DecisionRoom | planned | Decision Room |
| SharedView | implemented | Shared View, all packs |
| SharedPack | implemented (authority), partial (owner, insurer) | Authority Pack, Owner Pack, Insurer Pack |
