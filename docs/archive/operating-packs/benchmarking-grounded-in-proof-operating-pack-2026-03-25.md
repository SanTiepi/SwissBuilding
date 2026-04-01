# Benchmarking Grounded in Proof Operating Pack

Date de controle: `25 mars 2026`

## Purpose

This is the execution-oriented companion to:

- [benchmarking-learning-and-market-intelligence-program.md](./benchmarking-learning-and-market-intelligence-program.md)

The goal is to make benchmarking useful and defensible by grounding it in
actual dossier truth, proof quality, blockers, and outcomes.

## Hard rule

No benchmarking without anchored evidence.

If a benchmark is not grounded in:

- obligations
- procedures
- blockers
- proof quality
- timeline outcomes

then it should not drive product behavior.

## Build posture

Build:

- internal snapshots
- privacy-safe aggregates
- explainable patterns
- product-learning hooks

Do not build:

- vanity dashboards
- cross-client exposure of sensitive data
- black-box scoring detached from dossier state

## Minimum objects

### BenchmarkSnapshot

Captures aggregate state for a bounded cohort.

Minimum shape:

- `id`
- `cohort_key`
- `snapshot_type`
- `sample_size`
- `generated_at`
- `metric_map`
- `confidence_level`

### PortfolioPattern

Represents a recurring pattern across buildings.

Minimum shape:

- `id`
- `pattern_type`
- `scope_key`
- `frequency`
- `impact_level`
- `explanation`

### PrivacySafeAggregate

Represents a product-safe aggregate boundary.

Minimum shape:

- `id`
- `aggregate_key`
- `grouping_type`
- `sample_size`
- `privacy_threshold_met`

### LearningSignal

Represents a validated learning input for downstream features.

Minimum shape:

- `id`
- `signal_type`
- `source_snapshot_id`
- `confidence`
- `recommended_product_use`

## Existing anchors to reuse

Benchmarking should consume:

- `ControlTower`
- `Obligation`
- `PermitProcedure`
- `ProofDelivery`
- `DiagnosticPublication`
- readiness and timeline signals

It should not invent a disconnected analytics universe.

## First product outputs

The first useful outputs are:

- common blocker cohorts
- time-to-ready comparisons
- proof completeness deltas
- frequent missing-piece patterns
- jurisdiction friction hotspots

These should improve workflow and commercial clarity, not just produce charts.

## Sequence

### B1

Internal snapshot layer only:

- `BenchmarkSnapshot`
- `PrivacySafeAggregate`

### B2

Pattern layer:

- `PortfolioPattern`
- `LearningSignal`

### B3

Later:

- recommendation tuning
- market pattern surfaces
- privacy-safe external benchmark claims

## Acceptance

This layer is useful when benchmarking makes actions smarter, sales clearer,
and product learning more grounded without exposing sensitive building truth.
