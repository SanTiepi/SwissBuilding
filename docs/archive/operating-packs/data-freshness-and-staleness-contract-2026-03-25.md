# Data Freshness and Staleness Contract

Date de controle: `25 mars 2026`

## Purpose

SwissBuilding should not only store facts.

It should show whether a fact is:

- current
- aging
- stale
- superseded
- review-dependent

## Rule

Any user-visible fact that can become outdated should have explicit freshness
semantics.

## Freshness targets

- diagnostic publications
- packs
- proof deliveries
- rules and source watches
- obligations
- building summaries
- public-system context
- imported external identifiers

## Minimal freshness states

### `current`

Meaning:

- no known replacement
- still within valid or expected time window

### `aging`

Meaning:

- still usable
- should be reviewed soon

### `stale`

Meaning:

- probably unsafe to rely on without review

### `superseded`

Meaning:

- a later version exists

### `review_dependent`

Meaning:

- freshness cannot be asserted until a human confirms it

## Product effects

- stale proof should not quietly look current
- superseded proof should remain visible but clearly secondary
- aging items should create soft attention before becoming blockers
- stale regulatory sources should affect confidence and review state

## Surface rules

Freshness should appear in:

- building overview
- diagnostics tab
- packs
- ProofDelivery surfaces
- rule explainability
- ControlTower when freshness creates action

## Acceptance

The contract is succeeding when users can tell:

- whether something is still safe to reuse
- whether a later version exists
- whether review is needed before relying on it
