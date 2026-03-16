# Weak-Signal Watchtower Program

## Mission

Detect the small signals that precede dossier drift, readiness loss, cost escalation, or risk requalification before they become obvious blockers.

## Why This Matters

Most systems react only once a state has already turned red.
SwissBuilding should become useful earlier by spotting weak signals such as:
- repeated missing attachments
- growing contradiction density
- rising time-to-close actions
- repeated post-works reopenings
- expiring proof that is not yet blocking but is trending toward failure

## Recommended Workstreams

### Workstream A - Weak signal registry

Candidate objects:
- `WeakSignal`
- `SignalPattern`
- `SignalSeverityTrend`

### Workstream B - Watchtower scoring

- combine low-grade signals into higher-confidence warnings
- separate noise from meaningful drift

### Workstream C - Escalation surfaces

- surface weak signals before they become blockers
- connect them to actions, trust, readiness, and budgets

## Acceptance Criteria

- SwissBuilding can represent and surface pre-blocker risk signals
- the product becomes predictive in operations, not only reactive

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
