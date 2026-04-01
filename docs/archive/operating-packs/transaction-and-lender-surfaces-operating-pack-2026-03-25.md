# Transaction and Lender Surfaces Operating Pack

Date de controle: `25 mars 2026`

## Purpose

This is the execution-oriented companion to:

- [transaction-insurance-finance-readiness-program.md](./transaction-insurance-finance-readiness-program.md)

The goal is to make SwissBuilding useful for transactions and lender review
without turning it into a transaction platform or lending stack.

## Hard rule

Transaction and lender surfaces must stay:

- pack-centric
- trust-centric
- risk-legible
- bounded in scope

They should help a decision happen, not try to own the entire deal workflow.

## Build posture

Build:

- transaction readiness signals
- lender-facing pack structures
- caveat and unknown summaries
- trust-oriented delivery and receipt traces

Do not build:

- full deal room replacement
- loan origination workflow
- deep underwriting engines

## Minimum objects

### TransactionReadinessPack

Represents a bounded transaction-facing pack.

Minimum shape:

- `id`
- `building_id`
- `pack_version`
- `scope_summary`
- `unknowns_summary`
- `contradictions_summary`
- `proof_refs`

### LenderReadinessPack

Represents a bounded lender-facing pack.

Minimum shape:

- `id`
- `building_id`
- `pack_version`
- `residual_risk_summary`
- `proof_refs`
- `trust_refs`

### DecisionCaveatProfile

Represents the explicit caveats that should travel with a transaction or lender
surface.

Minimum shape:

- `id`
- `audience_type`
- `caveat_sections`
- `unknowns_policy`
- `redaction_rules`

## Existing anchors to reuse

These surfaces should extend:

- readiness wallet
- pack architecture
- `ProofDelivery`
- buyer packaging
- proof and contradiction layers

They should not create:

- a second due-diligence engine
- a second sharing or trust model

## First useful outputs

The first valuable outputs are:

- transaction-facing pack preset
- lender-facing pack preset
- explicit caveat profile
- trust and receipt trace tied to the pack

## Sequence

### TL1

Pack preset and caveat layer only.

### TL2

Readiness and trust reinforcement.

### TL3

Later:

- stronger finance-readiness pathways
- richer transaction chronology surfaces

## Acceptance

This pack is useful when transaction and lender audiences can consume a more
trustworthy dossier without forcing SwissBuilding into their full operating
stack.
