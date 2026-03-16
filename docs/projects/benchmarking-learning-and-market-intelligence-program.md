# Benchmarking, Learning, and Market Intelligence Program

## Mission

Turn the growing corpus of building dossiers, interventions, readiness states, and proof quality into structured learning and benchmarking advantage.

## Why This Matters

A true category leader does not only store building truth.
It learns across:
- portfolios
- interventions
- jurisdictions
- partner behavior
- proof maturity
- readiness transitions

This learning layer should strengthen:
- product recommendations
- commercial narrative
- portfolio steering
- scenario realism
- future data-network effects

## Strategic Outcomes

- stronger cross-building and cross-portfolio learning
- privacy-aware benchmarking
- recommendation and scenario engines grounded in validated aggregate signals
- market-intelligence surfaces that make SwissBuilding progressively harder to replicate

## Product Scope

This program should produce:
- internal benchmarking
- privacy-safe aggregates
- learning hooks for recommendations
- market-intelligence surfaces

It should not become:
- a vague analytics dashboard
- a privacy-dangerous cross-client data exposure layer

## Recommended Workstreams

### Workstream A - Internal benchmarking layer

Compare:
- dossier maturity
- trust
- readiness
- residual risk
- intervention outcomes
- time-to-pack
- completeness lift after workflow use

Candidate objects:
- `BenchmarkSnapshot`
- `PortfolioPattern`

### Workstream B - Privacy-aware learning signals

Enable useful learning without exposing sensitive building identity.

Expected outputs:
- aggregation boundaries
- anonymization / grouping approach
- confidence thresholds
- safe internal-versus-external usage split

Candidate objects:
- `PrivacySafeAggregate`
- `LearningSignal`

### Workstream C - Product learning hooks

Feed downstream engines with validated signals.

Examples:
- recommendation tuning
- campaign suggestion tuning
- opportunity engine tuning
- scenario realism improvement
- routing improvement

Candidate objects:
- `RecommendationLearningInput`
- `ScenarioLearningInput`

### Workstream D - Market-intelligence surfaces

Show where patterns are emerging:
- common gaps
- common contradictions
- recurring intervention sequences
- recurring dossier failures
- common post-works gaps
- rules-pack friction hotspots

Candidate objects:
- `MarketPatternSnapshot`
- `PatternAlert`

### Workstream E - Commercial leverage layer

Translate learning into GTM value.

Examples:
- benchmark claims supported by data
- readiness improvement deltas
- rework reduction evidence
- portfolio opportunity evidence

## Candidate Improvements

- `BenchmarkSnapshot`
- `PortfolioPattern`
- `PrivacySafeAggregate`
- `LearningSignal`
- `RecommendationLearningInput`
- `ScenarioLearningInput`
- `MarketPatternSnapshot`
- `PatternAlert`

## Acceptance Criteria

- SwissBuilding gains a credible path from stored truth to learning leverage
- benchmarking is treated as a product engine, not an afterthought
- privacy-safe learning becomes more explicit
- market intelligence starts reinforcing both product quality and moat

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
