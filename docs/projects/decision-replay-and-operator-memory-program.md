# Decision Replay and Operator Memory Program

## Mission

Preserve not only building state, but the reasoning, assumptions, human validations, and operational tradeoffs behind important building decisions.

## Why This Matters

The building memory should not stop at:
- documents
- interventions
- scores
- actions

It should also preserve:
- why a decision was made
- which assumptions were accepted
- who overrode the system
- what was known at the time

This makes the product dramatically stronger under turnover, audit, dispute, and long-lived building operations.

## Recommended Workstreams

### Workstream A - Decision record model

Candidate objects:
- `DecisionRecord`
- `DecisionAssumption`
- `OverrideReason`

### Workstream B - Replay and time-travel surfaces

- show what the operator knew then
- show what changed since
- replay decision context alongside proof and trust

### Workstream C - Human/system judgement split

- preserve where human judgement diverged from system output
- keep that difference explicit and reviewable

## Acceptance Criteria

- SwissBuilding can replay decision context, not only end state
- operator memory becomes a durable product asset rather than disappearing in chat/email

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
