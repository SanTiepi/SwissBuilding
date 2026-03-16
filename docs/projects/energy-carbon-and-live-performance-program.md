# Energy, Carbon, and Live Performance Program

## Mission

Extend SwissBuildingOS from static dossier intelligence into ongoing energy, carbon, and live building performance intelligence.

## Why This Matters

The long-term category cannot stop at pollutant and renovation readiness.
It must also absorb:
- energy performance
- carbon trajectory
- live performance deltas
- operating inefficiencies

This is one of the most credible bridges from renovation workflows to recurring building intelligence.

## Strategic Outcomes

- stronger link between renovation truth and energy/carbon outcomes
- recurring operational value beyond project moments
- future bridge to sensors, meters, and live building data

## Product Scope

This program should produce:
- energy/carbon state model
- performance snapshots
- target vs observed performance gaps
- recommendation linkage to interventions and portfolio planning

## Recommended Workstreams

### Workstream A - Performance state model

Candidate objects:
- `PerformanceSnapshot`
- `CarbonState`
- `EnergyState`

### Workstream B - Gap and drift logic

Candidate objects:
- `PerformanceGap`
- `DriftSignal`

### Workstream C - Live or periodic data hooks

Candidate objects:
- `MeterIngestProfile`
- `SensorDataWindow`
- `PerformanceFeed`

## Acceptance Criteria

- SwissBuilding gains a credible path from static building truth to recurring performance intelligence
- renovation and portfolio decisions can later connect to live energy/carbon reality

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
