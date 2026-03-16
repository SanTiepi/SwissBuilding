# Sensor Fusion and Live Building State Program

## Mission

Extend SwissBuilding from a dossier- and event-driven building memory into a live state layer that can absorb signals from meters, BMS, IoT devices, air-quality probes, leak detectors, occupancy sensors, and other operational feeds.

## Why This Matters

The product already models:
- building truth
- evidence
- readiness
- interventions
- post-works memory

The next leap is to detect when the building is drifting in the real world, not only when a human uploads a document.

This creates a path toward:
- live operating intelligence
- earlier risk detection
- readiness degradation alerts
- system-specific anomaly detection
- stronger links between dossier truth and actual building behavior

## Strategic Outcomes

- bridge static building memory with live building state
- create a feed of operational signals that can trigger:
  - unknowns
  - contradictions
  - requalification
  - incident workflows
  - maintenance recommendations
- prepare the product for enterprise and portfolio-grade building operations

## Product Scope

This program should produce:
- a sensor / meter ingest profile layer
- a normalized live state model
- building- and system-level health signals
- anomaly and drift detection hooks
- readiness and trust degradation inputs
- bounded UI surfaces for live status without turning the product into a generic BMS clone

## Recommended Workstreams

### Workstream A — Ingest and normalization

Candidate objects:
- `SensorProfile`
- `MeterProfile`
- `LiveSignalWindow`
- `TelemetryIngestRun`

### Workstream B — Building live state and anomalies

Candidate objects:
- `BuildingLiveState`
- `SystemLiveState`
- `AnomalySignal`
- `DriftAlert`

### Workstream C — Productization and packs

Candidate objects:
- `LiveReadinessImpact`
- `OperationsHealthCard`
- `LiveIncidentTrigger`

## Acceptance Criteria

- SwissBuilding gains a credible live-state layer without losing its evidence-first identity
- operational feeds can later influence readiness, contradiction, incident, and maintenance logic
- the system remains building-truth-centric rather than becoming a generic telemetry dashboard

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
