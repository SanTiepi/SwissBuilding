# Full-Chain Integration and Demo Truth Program

## Mission

Prove that SwissBuildingOS works as a coherent end-to-end system on realistic data, not only as a collection of individually green services.

This program should validate and tighten the full journey:

- import
- enrichment
- diagnosis
- evidence and readiness
- actions and remediation
- post-works truth
- dossier / pack generation
- portfolio surfacing

The goal is to make the product demonstrably true across the whole chain.

## Why This Matters

The repo now has:

- a deep backend intelligence layer
- many focused services
- rich dossier and readiness logic
- growing UI surfaces

The main risk is no longer missing primitives.
The main risk is breadth without enough integrated proof that the whole chain works together on realistic scenarios.

This program is the antidote.

## Core Outcomes

### 1. Full-chain scenario exists and stays green

Expected:

- at least one canonical scenario proves:
  - ingest -> structure -> evidence -> readiness -> action -> intervention -> post-works -> pack
- the scenario is deterministic and reusable

### 2. Demo truth becomes stronger than synthetic comfort

Expected:

- authority/demo scenarios are validated against realistic data shapes
- the product does not only work on isolated happy-path calculators

### 3. Integration regressions become visible early

Expected:

- cross-domain failures are easier to catch
- packs, dossiers, actions, and trust states are exercised together

## Recommended Workstreams

### Workstream A - Canonical journey definition

- define 2-3 full-chain journeys:
  - authority-ready pre-work journey
  - remediation / post-works journey
  - portfolio escalation journey

### Workstream B - Integration fixtures and seeds

- bind these journeys to the dataset/scenario strategy
- make the scenarios seed-verifiable and replayable

### Workstream C - End-to-end assertions

- verify not only object creation, but state coherence:
  - trust
  - readiness
  - actions
  - evidence
  - packs
  - post-works

### Workstream D - Demo proof harness

- create a simple validation path for demo scenarios
- ensure generated artifacts are actually usable

## Acceptance Criteria

- at least one realistic full-chain journey is green end to end
- the journey is tied to seeded data, not hand-built test-only state
- dossier / pack / readiness / action outputs are validated together
- SwissBuilding can demonstrate one complete story without manual stitching across domains

## Metadata

- `macro_domain`: `01_pre_work_diagnostics_and_proof`
- `ring`: `ring_1_to_2`
- `user_surface`: `internal / demo / qa / authority / portfolio`
- `go_to_market_relevance`: `direct_wedge`
- `moat_type`: `integration_truth`
- `depends_on`: `seed strategy + dossier + readiness + post works + packs + portfolio surfaces`
