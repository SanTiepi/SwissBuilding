# Demo and Sales Enablement Program

## Mission

Turn SwissBuildingOS into a product that is not only impressive to build, but impossible to forget in a live demo and easier to sell repeatedly.

This program focuses on:

- killer demo flow
- sales-proof product surfaces
- buyer-specific packaging
- credibility in front of property managers, owners, authorities, insurers, and future enterprise buyers

## Why This Matters

SwissBuildingOS is aiming higher than a niche SaaS.
To become category-defining, it must not only work — it must create moments where the buyer feels:

- "I have never seen this before"
- "This changes how building knowledge should work"
- "This is the system that should sit above everything else"

That requires deliberate demo architecture, not accidental product storytelling.

## Core Outcomes

### 1. Demo flows become intentional

Expected:
- one or more canonical demo narratives
- seeded assets that highlight:
  - proof
  - readiness
  - unknowns
  - post-works truth
  - packs
  - portfolio steering

### 2. Product surfaces support selling

Expected:
- stronger executive views
- clearer "why this matters now" surfaces
- buyer-specific outputs
- fewer places where the product feels like an internal tool only

### 3. The product can sell by persona

Expected:
- property manager story
- owner / investor story
- authority / compliance story
- insurer / lender story later

## Recommended Workstreams

### Workstream A — Canonical demo scenarios

- define 3 to 5 seeded demo scenarios
- each should have:
  - starting point
  - reveal moment
  - proof moment
  - action moment
  - portfolio moment if relevant

### Workstream B — Wow-surface polish

- productize the strongest wow features into coherent flows:
  - time machine
  - proof heatmap
  - readiness wallet
  - intervention simulator
  - autonomous dossier completion

### Workstream C — Buyer-facing outputs

- owner pack
- authority pack
- contractor pack
- executive summary / board surface
- later insurer/lender surfaces

### Workstream D — Demo operator tooling

- seeded scenario selector
- reset/reseed helpers
- known-good walkthrough state
- ability to switch between narratives quickly

### Workstream E — Sales narrative hooks

- one-line explanations inside the product
- concise explanation surfaces:
  - why this score
  - why not ready
  - what changed
  - what to send
  - what to do next

## Candidate Improvements

- `DemoScenario`
- `DemoRunbook`
- `ExecutiveReadinessBoard`
- `OperatorDemoPanel`
- persona-specific pack presets
- seeded "wow asset" datasets
- presentation mode UI refinements

## Acceptance Criteria

- the product supports at least one repeatable, high-trust, high-wow demo flow
- seeded scenarios are deliberate, not incidental
- the strongest surfaces feel buyer-legible, not only builder-impressive
- the product can tell a convincing story by persona without changing its core truth model

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

This program is not about cosmetic polish alone.
It is about converting product depth into commercial inevitability.

Prefer:
- memorable decision surfaces
- buyer-legible proofs
- repeatable scenario quality

Avoid:
- fake flashiness without evidence
- isolated demo hacks that do not compound product truth
