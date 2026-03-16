# Offline Field Sync and Resilient Capture Program

## Mission

Make SwissBuildingOS usable in poor-connectivity field conditions by supporting resilient capture, deferred sync, and conflict-aware reconciliation for high-value site observations.

## Why This Matters

Real building work does not happen on perfect networks.

Field users may need to capture:

- photos
- notes
- annotations
- observations
- zone restrictions
- material findings
- safety events

If this only works online, the field layer stays weak.

## Core Outcomes

### 1. Critical field capture is resilient

Expected:

- drafts survive connectivity loss
- local queueing exists for bounded capture flows
- sync status is visible

### 2. Conflicts are explicit

Expected:

- if server truth changed while the field user was offline, the merge/review path is visible
- no silent overwrite of building truth

### 3. Offline capability stays narrow and high-value

Expected:

- not a full offline clone of the product
- only the most valuable field flows are supported first

## Recommended Workstreams

### Workstream A - High-value offline capture inventory

- identify the minimal flows worth supporting:
  - field observation
  - photo evidence
  - plan annotation draft
  - safety restriction note

### Workstream B - Sync and queue model

- define local draft/sync states
- define retry and reconciliation rules

### Workstream C - Conflict surfacing

- connect to contradiction/decision replay rather than silently merging away conflicts

## Acceptance Criteria

- SwissBuilding can tolerate intermittent connectivity for core field truth capture
- sync status is explicit
- conflict resolution preserves trust and auditability

## Metadata

- `macro_domain`: `04_technical_systems_and_operations`
- `ring`: `ring_2_to_4`
- `user_surface`: `field / pro / operator`
- `go_to_market_relevance`: `expansion`
- `moat_type`: `resilient_field_truth`
- `depends_on`: `spatial truth + field operations + contradiction + audit trails`
