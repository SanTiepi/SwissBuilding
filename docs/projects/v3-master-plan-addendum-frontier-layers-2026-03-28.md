# SwissBuilding — Master Plan Addendum: 15 Frontier Layers

Date: 28 mars 2026
Extends: v3-master-future-steps-plan
Status: Canonical future layers — mapped into existing roadmap

---

## Purpose

Capture 15 high-leverage layers that emerged after the initial master plan. These are canonical future layers, not side ideas. Each must strengthen at least one V3 root family and project into at least one workspace.

---

## 15 Frontier Layers

### 1. Document Intelligence OS
**Root**: Artifact, Evidence, Claim, Change
**Phase**: After canonical freeze (Phase A+)

Every incoming document is classified, segmented, extracted, normalized, and mapped into canonical roots. Raw document = source; canonical information = reusable truth.

Objects: extended extraction families (diagnostics, plans, permits, quotes, contracts, invoices, guarantees, attestations, emails, photos)
Outcome: reusable structured truth, contradiction detection, obligation/cost/exclusion extraction, pack generation from canonical truth

### 2. Building Genealogy OS
**Root**: Building, Change, Evidence, Spatial
**Phase**: Phase C (procedure + freshness)

Model the genealogy of the building — not only current state but transformation history.

Objects: `BuildingVersion`, `TransformationEpisode`, `ProcedureEpisode`, `OwnershipEpisode`, `HistoricalClaim`, `EvidenceWindow`, `GenealogyDelta`
Sources: historical aerial imagery, maps, cadastral history, permit archives, ownership/transfer history, insurance/revaluation history
Outcome: explain what changed when, detect undocumented transformations, compare observed vs declared vs authorized state

### 3. Long-Horizon Climate & Exposure Layer
**Root**: Change, Spatial, Evidence
**Phase**: Phase C

20+ year weather/climate history, heat/humidity/freeze-thaw/wind/extreme events, environmental exposure overlays.

Objects: `ClimateExposureProfile`, `WeatherEventWindow`, `BuildingClimateSignal`, `ExposureStressIndex`
Rule: explanatory layer, not standalone causality proof

### 4. Historical Imagery & Visual Time Layer
**Root**: Spatial, Change, Evidence
**Phase**: Phase C

swisstopo historical aerial imagery, orthophotos, time-travel maps, visual timeline per building, image-to-delta interpretation.

Objects: visual timeline, change hypotheses linked to spatial scope, before/after as evidence input
Outcome: visually anchored transformation episodes for genealogy and contradiction support

### 5. Unknowns Ledger
**Root**: Evidence, Intent, Action
**Phase**: Phase A+ (after canonical freeze)

First-class tracking of what is unknown, missing, unverified, stale, or spatially uncovered.

Objects: `UnknownLedgerEntry`, `CoverageGap`, `UnverifiedWindow`, `RiskOfActingUnderUnknown`
Outcome: SafeToX consumes unknowns directly, passport exposes unknowns honestly, cases turn unknowns into actions or caveats

### 6. Commitments & Caveats Graph
**Root**: Claim, Decision, Transfer, OperationalFinance
**Phase**: Phase D (finance/transfer)

Authority conditions, contractor exclusions, insurer exclusions, seller caveats, lender caveats, guarantees, undertakings, procedural reservations.

Objects: `Commitment`, `Condition`, `Exclusion`, `CaveatProfile`, `CommitmentTrace`
Outcome: every audience-facing pack carries explicit caveats, finance/insurance/transfer readiness strengthened

### 7. Invalidation Engine
**Root**: Change, Publication, Transfer, Action
**Phase**: Phase A+ (after canonical freeze)

First-class engine for when truth changes invalidate existing artifacts.

Triggers: source refresh, rule change, form change, document arrival, contradiction, post-works update, new evidence
Effects: invalidate pack/template/form, refresh SafeToX, reopen case, flag passport as supersession candidate
Objects: `InvalidationEvent`, `AffectedArtifact`, `SupersessionCandidate`, `ImpactReason`

### 8. Opportunity Window Engine
**Root**: Action, BuildingCase, OperationalFinance, Change
**Phase**: Phase C

Detect good windows to act, not just blockers.

Signals: weather windows, subsidy/tax timing, permit windows, service/utility windows, insurer renewals, occupancy/seasonality, maintenance windows
Objects: `OpportunityWindow`, `TimingAdvantage`, `WindowExpiryRisk`
Outcome: Today/Portfolio/Case Room show "best moment to move"

### 9. Material / Product / System Passport
**Root**: Spatial, Evidence, Change
**Phase**: Phase E (later moat)

Typed material/product/system memory beyond pollutants.

Objects: `MaterialPassport`, `SystemPassport`, `ComponentLifecycle`, `WarrantyWindow`, `EndOfLifePath`
Rule: tied to building truth + interventions + post-works, NOT generic product catalog

### 10. Incident & Damage Memory
**Root**: Change, BuildingCase, Evidence, OperationalFinance
**Phase**: Phase D

Explicit memory for leaks, mold, flooding, fire, subsidence, breakage, recurring failures.

Objects: `IncidentEpisode`, `DamageObservation`, `RepairTrace`, `LossContext`
Outcome: insurer readiness, recurring risk memory, explanation of defects/exclusions, stronger transfer truth

### 11. Building Kinship / Cousin Graph
**Root**: Building, Change, Evidence
**Phase**: Phase F (ecosystem)

Cross-building graph for learning: era, typology, spatial context, construction systems, materials, risk patterns.

Objects: `BuildingKinshipLink`, `PatternFamily`, `CousinSignal`
Rule: only where explainable and tied to actions — never opaque pseudo-scoring

### 12. Decision Replay Layer
**Root**: Decision, Evidence, Claim, Change
**Phase**: Phase D

Replayable decision history: what was decided, by whom, based on what, under which context, what changed since.

Objects: `DecisionReplay`, `DecisionBasisSnapshot`, `ChangedSinceDecision`
Outcome: crucial for authority/transfer/insurer/lender accountability

### 13. Utility / Service Twin Layer
**Root**: Building, OperationalFinance, Party, Change
**Phase**: Phase E

Utility accounts, meters, recurring vendors, service contracts, SLA, renewals, interruptions, recurring invoices.

Outcome: building operations become recurring, service truth feeds finance/incidents/performance

### 14. Counterfactual & Scenario Engine
**Root**: BuildingCase, OperationalFinance, Intent, Action
**Phase**: Phase D-E

Serious scenarios: do nothing, postpone, phase, widen/reduce scope, sell before/after, insure before/after, funding timing.

Objects: `CounterfactualScenario`, `ScenarioAssumptionSet`, `ScenarioRiskTradeoff`, `ScenarioOpportunityWindow`
Rule: must consume canonical truth/unknowns/caveats/cost/procedure — not generic spreadsheet planning

### 15. Truth API Doctrine
**Root**: All roots (transversal)
**Phase**: Phase A+ (foundational)

Read-first API making SwissBuilding a source of truth accessible externally.

Layers: canonical internal API (write), workspace projection API (bounded read), exchange/transfer API (passport/packs/receipts/diffs), controlled ingestion API (documents/imports/partner submissions)
Rules: no open mutable truth DB, external writes never bypass cases/validation/provenance/rituals, read exposure is role/redaction/projection driven

---

## Roadmap Integration

| Phase | Layers Added |
|---|---|
| **A+** (post canonical freeze) | Document Intelligence OS, Unknowns Ledger, Invalidation Engine, Truth API Doctrine |
| **C** (procedure + freshness) | Building Genealogy, Historical Imagery, Climate/Exposure, Opportunity Window, Utility/Service Twin |
| **D** (finance + transfer) | Commitments/Caveats, Incident/Damage, Decision Replay, Counterfactual Engine |
| **E-F** (later moat) | Material/System Passport, Building Kinship Graph |

---

## Acceptance

- Each layer sits in the roadmap with clear phase and root families
- None requires a new top-level navigation center
- Each has source model, procedure impact, and workspace destination
- Document Intelligence and Truth API are foundational, not "later polish"
- Unknowns Ledger reflects in trust, passport, and SafeToX
- Invalidation Engine links to packs, procedures, and transfer
- Another engineer can continue without reopening these conceptual gaps
