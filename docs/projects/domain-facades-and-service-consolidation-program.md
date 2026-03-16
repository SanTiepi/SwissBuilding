# Domain Facades and Service Consolidation Program

## Mission

Reduce backend service sprawl by consolidating overlapping logic into clearer bounded contexts and domain facades.

This is not a rewrite for style.
It is a structural hardening pass to make the system:

- easier to compose
- easier to reason about
- easier to expose in UI
- easier to validate end to end

## Why This Matters

SwissBuilding now has a large number of backend services.
That depth is an asset, but only if the product can compose it.

Without consolidation:

- multiple services re-query the same models independently
- domain ownership becomes fuzzy
- the UI must over-compose raw calculators
- maintenance grows faster than value

## Core Outcomes

### 1. Bounded contexts become explicit

Expected domains include:

- evidence
- readiness
- trust
- compliance
- remediation / post-works
- portfolio

### 2. High-level facades exist where product surfaces need them

Expected:

- major screens and workflows can call clearer aggregate/facade services
- lower-level services remain available, but no longer define the main product contract by accident

### 3. Redundant service overlap becomes visible and reducible

Expected:

- overlap inventory
- consolidation candidates
- fewer isolated calculators with no strong consumer path

## Recommended Workstreams

### Workstream A - Service map

- inventory current services by domain
- mark:
  - primary owner domain
  - consumers
  - overlap
  - consolidation candidates

### Workstream B - Facade design

- define 5-6 domain facades
- keep them thin and compositional
- do not duplicate lower-level logic

### Workstream C - Migration of high-value consumers

- move the highest-value UI/API surfaces toward facade usage
- likely targets:
  - building detail aggregates
  - readiness/trust/passport surfaces
  - portfolio summary and command surfaces

### Workstream D - Dead or weak service review

- identify services with no meaningful consumer
- either:
  - merge them
  - park them
  - or justify them explicitly

## Acceptance Criteria

- core services are grouped into explicit bounded contexts
- at least the highest-value product surfaces can consume clearer domain facades
- overlap between trust/readiness/completeness/compliance/post-works style services is documented and reduced
- the repo becomes easier to navigate and safer to evolve

## Metadata

- `macro_domain`: `12_infrastructure_standards_and_intelligence`
- `ring`: `ring_4`
- `user_surface`: `internal / all`
- `go_to_market_relevance`: `supporting`
- `moat_type`: `operating_coherence`
- `depends_on`: `current backend services + read models + async orchestration`
