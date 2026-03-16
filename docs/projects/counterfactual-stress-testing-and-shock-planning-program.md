# Counterfactual Stress Testing and Shock Planning Program

## Mission

Give SwissBuilding the ability to test buildings and portfolios against counterfactual shocks and scenario changes, including regulation, insurance, financing, climate, documentation loss, contractor delay, and evidence degradation.

## Why This Matters

The product already knows a lot about:
- current building state
- trust and readiness
- unknowns and contradictions
- interventions and post-works truth

The next category jump is to answer:
- what breaks if one rule changes?
- what happens if a proof expires?
- what becomes blocked if a lender or insurer raises the bar?
- which assets remain robust under stress?

This turns the platform from descriptive intelligence into resilience and strategy intelligence.

## Strategic Outcomes

- stronger portfolio and capital-allocation logic
- readiness that can be tested under shock, not just measured in the present
- better sales narrative for insurers, lenders, public owners, and executives
- more compelling “why act now” surfaces

## Product Scope

This program should produce:
- counterfactual scenario definitions
- stress profiles at building and portfolio level
- shock propagation through readiness / trust / packs / actions
- resilience comparisons between current and stressed states

## Recommended Workstreams

### Workstream A — Scenario model

Candidate objects:
- `StressScenario`
- `ShockAssumption`
- `CounterfactualRun`

### Workstream B — Impact propagation

Candidate objects:
- `ShockImpact`
- `ReadinessStressResult`
- `PackInvalidationResult`
- `CapitalStressSummary`

### Workstream C — Decision surfaces

Candidate objects:
- `StressComparisonCard`
- `ResilienceRanking`
- `WhatChangedIf` view

## Acceptance Criteria

- SwissBuilding can express at least one meaningful what-if stress path for buildings and portfolios
- readiness and trust can be compared under current and shocked assumptions
- the system gains a credible path toward board-grade scenario planning rather than static status reporting

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
