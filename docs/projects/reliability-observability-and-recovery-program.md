# Reliability, Observability, and Recovery Program

## Mission

Turn SwissBuildingOS from a fast-moving ambitious product into an operationally trustworthy platform that can survive real usage, failed jobs, noisy integrations, and imperfect environments.

This program is not feature theatre.
It exists to make the product:

- resilient
- diagnosable
- recoverable
- supportable
- credible in demos, pilots, and early production

## Why This Matters

SwissBuildingOS now depends on:

- OCR and document pipelines
- dossier and pack generation
- async-style workflows
- search indexing
- growing cross-entity state
- imported public data
- increasingly important export/proof flows

At this level of product ambition, reliability is product.

If the platform cannot:
- explain failures,
- retry safely,
- surface degraded states,
- recover jobs,
- and preserve trust under operational stress,

then it cannot become infrastructure.

## Core Outcomes

### 1. Failure states become first-class

Expected:
- failed export jobs are inspectable and retryable
- failed OCR/document processing states are visible
- stale search index or sync lag is detectable
- partial ingestion and partial dossier generation are not silent

### 2. Recovery paths become productized

Expected:
- retry actions for key async-like flows
- resumable/rebuildable dossier and pack generation
- reindex / replay / recompute paths for critical derived state

### 3. Observability becomes operator-grade

Expected:
- traceable job lifecycle
- error correlation IDs where useful
- support-facing diagnostics for failed runs
- product-visible degraded-state banners where appropriate

### 4. Demo and pilot reliability improve

Expected:
- predictable seeded-state checks
- clearer environment health ownership
- safer startup / preflight / background dependency diagnostics

## Recommended Workstreams

### Workstream A — Export and pack recovery

- retry / rerun flow for `ExportJob`
- explicit failed / retriable / superseded states if useful
- inspectable error details

### Workstream B — Processing pipeline observability

- OCR / scan / parsing pipeline status surfaces
- safe retry semantics
- support/debug metadata without exposing internal clutter to end users

### Workstream C — Search and derived-state health

- Meilisearch sync status or last-indexed visibility
- ability to reindex entities safely
- health indicators for trust/readiness/unknowns derived layers if appropriate

### Workstream D — Environment and preflight hardening

- explicit backend ownership checks
- service dependency checks
- operator-grade preflight for real e2e / seeded demo / exports

### Workstream E — Product-facing degraded mode

- when a subsystem is degraded, the UI should remain honest
- banners or inline warnings for:
  - export unavailable
  - OCR delayed
  - indexing lag
  - stale derived state

## Candidate Improvements

- `SystemHealthSnapshot`
- `DerivedStateFreshness`
- `BackgroundJobRetry`
- `IndexSyncStatus`
- `OperatorDiagnosticsPanel`
- `SupportBundle` export for troubleshooting
- correlation IDs on critical long-running operations
- audit trail of recovery attempts

## Acceptance Criteria

- critical background-like flows have explicit failure and retry paths
- the wrong environment is easier to detect before real e2e or demo runs
- operators and product users can distinguish:
  - success
  - pending
  - failed
  - stale
  - degraded
- the product is more trustworthy under failure, not only under the happy path

## Validation

Backend if touched:

- `cd backend`
- `ruff check app/ tests/`
- `ruff format --check app/ tests/`
- `python -m pytest tests/ -q`

Frontend if touched:

- `cd frontend`
- `npm run validate`
- `npm test`
- `npm run test:e2e`
- `npm run build`

Real integration if touched:

- `cd frontend`
- `npm run test:e2e:real`

## Notes

This program should improve operational credibility without turning the app into an ops console.

Prefer:
- honest degraded states
- simple retry/recovery flows
- clear diagnostics

Avoid:
- overbuilding a heavy internal platform too early
- exposing raw technical noise to end users
