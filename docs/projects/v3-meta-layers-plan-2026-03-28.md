# SwissBuilding — Ultimate Meta-Layers Plan

Date: 28 mars 2026
Extends: Master Future Steps, Frontier Layers Addendum
Status: Canonical meta-architecture — layers that make the system governable, durable, and hard to copy

---

## Purpose

These are not feature layers. They are the **systemic layers** that transform SwissBuilding from a rich feature set into:
- a temporal system
- a rights and sharing system
- a declarative/composable system
- a conformance system
- a review and governance system
- an economic reasoning system
- a source reliability system
- a multi-actor sovereignty system

---

## 8 Meta-Layers

### 1. Native Temporal Semantics

Time is a canonical dimension, not just `created_at`.

**Temporal fields for every important object:**

| Field | Meaning |
|---|---|
| `observed_at` | When was this observed/measured |
| `effective_at` | When does this take effect |
| `valid_from` | Start of validity window |
| `valid_until` | End of validity window |
| `stale_after` | When does this become unreliable |
| `superseded_at` | When was this replaced |
| `superseded_by` | What replaced it |
| `as_of` | Point-in-time evaluation date |
| `covered_time_window` | Period this evidence covers |

**Rules:**
- Any fact can be true at one date, false at another, or true only within a window
- Contradictions can be temporal, not just logical
- SafeToX, passport, transfer, and genealogy must be evaluable `as_of` any date
- Objects: `TemporalValidity`, `TimeWindow`

**Phase**: After canonical freeze (A+)

### 2. Rights, License, Sharing & Externalization

Extend redaction into full **rights governance**.

| Right | Description |
|---|---|
| `UsageRight` | Can this be used internally |
| `ReuseRight` | Can this be reused in derived outputs |
| `ExportRight` | Can this be exported outside the system |
| `TransferRight` | Can this be included in a sovereign transfer |
| `RepublishRight` | Can this appear in a publication |
| `LicenseConstraint` | Source licensing restrictions |
| `ExposurePolicy` | What external visibility is allowed |

**Rules:**
- Redaction controls visibility; rights control reusability
- Some objects can be visible but non-exportable
- Some objects can feed internal models without being transferable
- Transferable truth is distinct from internal truth
- Objects: `ExternalizationClass`

**Phase**: During projection/redaction (B)

### 3. Declarative / Compiler Layer

Prevent ad hoc service explosion with declarative profiles.

| Profile | What it configures |
|---|---|
| `SourceMappingProfile` | Source → canonical object mapping |
| `DocumentExtractionProfile` | Document type → extraction rules + field mapping |
| `ProcedureProfile` | Procedure → steps / artifacts / forms / authorities |
| `ProjectionProfile` | Workspace → sections / redaction / audience |
| `ExchangeProfile` | Transfer/passport → exchange contract |
| `WorkFamilyProfile` | Work type → requirements / blockers / authorities |

**Rules:**
- New source or procedure: config first, specific code only if necessary
- The core behaves as a truth compiler, not a collection of business-specific branches
- Profiles are inspectable, versionable, and auditable

**Phase**: During source + procedure OS (C)

### 4. Conformance Layer

Not just generation — explicit conformance checking.

| Object | What it checks |
|---|---|
| `RequirementProfile` | What a pack/import/publication must satisfy |
| `ConformanceCheck` | Evaluation of an artifact against a profile |
| `ConformanceResult` | Pass/fail/partial with detail |
| `ExchangeCompatibilityProfile` | Partner compatibility check |
| `ImportContractValidation` | Does this import meet the expected contract |
| `PublicationComplianceSummary` | Does this publication satisfy its requirements |

**Rules:**
- Machine-readable conformance where possible
- No promise of automatic legal certification
- Start with internal conformance and exchange contracts before external certification

**Phase**: During passport/exchange (D)

### 5. Trust Ops & Human Review Machine

From trust doctrine to operational governance.

| Object | Purpose |
|---|---|
| `ReviewQueue` | Pending human reviews by building/case/type |
| `ReviewPriority` | Urgency ranking for reviews |
| `TrustEscalationRule` | When must AI output be escalated to human |
| `HumanValidationTask` | Specific validation task with context |
| `ConflictResolutionTask` | Contradiction requiring human decision |
| `RulePromotionCandidate` | AI pattern ready for deterministic codification |

**Rules:**
- No important truth depends on implicit review
- Review queues visible in Today and Case Room
- User corrections become governance assets, not passive feedback
- Phase 1→2→3 AI progression is explicitly managed here

**Phase**: After canonical freeze (A+)

### 6. Explicit Economic Engine

Model the economic value of knowledge, inaction, and unknowns.

| Object | What it quantifies |
|---|---|
| `CostOfUnknown` | Cost of acting without information |
| `CostOfDelay` | Cost of postponing action |
| `CostOfInvalidation` | Cost when an artifact becomes stale |
| `CostOfNonCompliance` | Cost of regulatory non-compliance |
| `ValueOfCompleteness` | Value of a complete vs incomplete dossier |
| `ValueOfTransferability` | Value of a clean transfer vs chaotic handoff |
| `DecisionEconomicImpact` | Economic consequence of a decision |

**Uses:**
- Prioritize actions and campaigns
- Compare counterfactual scenarios
- Justify SafeToX blockers with economic reasoning
- Objectify the value of a document, validation, or refresh

**Rules:** Building-rooted and case-linked, not abstract finance

**Phase**: During finance/scenario/portfolio (D-E)

### 7. Source Reliability & Connector Operations

When the system connects "everything", connector reliability becomes critical.

| Object | Purpose |
|---|---|
| `SourceHealth` | Current health status per source |
| `ConnectorIncident` | Source failure or degradation event |
| `SchemaDriftEvent` | Source schema changed unexpectedly |
| `FallbackExecution` | Fallback source was used instead of primary |
| `CoverageLossSignal` | Source no longer covers expected scope |
| `ConnectorRecoveryPlan` | How to restore a degraded connector |

**Rules:**
- A broken source produces an explicit state, not silence
- Building Home, Case Room, Today, SafeToX can show that a gap comes from source unavailability, not absence of truth
- Bridges and compat layers never become black boxes

**Phase**: During source + procedure OS (C)

### 8. Multi-Actor Sovereignty

Formalize the distinction between truth domains.

| Layer | Who sees it | Transferable |
|---|---|---|
| `Canonical building truth` | All authorized actors | Yes (with redaction) |
| `Actor private layer` | Only the owning organization | No |
| `Transferable layer` | Crosses sovereignty boundary | Yes |
| `Shareable layer` | Visible to partners but not transferable | Partial |
| `Internal-only layer` | Never leaves the organization | No |
| `Shadow annotation layer` | Private notes, hypotheses, internal caveats | No |

**Objects:** `TruthDomain`, `SovereigntyBoundary`, `ActorPrivateLayer`

**Rules:**
- Building remains the shared root object
- Not all actors possess the same truth layer
- Transfer explicitly chooses which layers cross the boundary
- Publication and transfer declare their sovereignty scope

**Phase**: During projection/redaction + truth API (B)

---

## Roadmap Integration

| Phase | Meta-Layers Added |
|---|---|
| **A+** (post canonical freeze) | Temporal semantics, Trust Ops, Review Machine |
| **B** (projection/redaction) | Multi-actor sovereignty, Rights governance |
| **C** (source + procedure) | Source reliability, Compiler/declarative layer |
| **D** (passport/exchange) | Conformance layer, Import/export validation |
| **D-E** (finance/scenario) | Economic engine |

---

## Acceptance

- Every important object evaluable in time, not just "now"
- Shared/exported data governed by rights/license, not just role
- New source/procedure/projection addable via declarative profiles
- Pack/import/publication produces machine-readable conformance result
- Review queues visible, prioritizable, linked to real workflows
- System can show cost of unknown/delay/invalidation on at least one concrete case
- Broken/drifting source produces explicit state and clear reaction
- Transfer distinguishes private/shareable/transferable layers explicitly
