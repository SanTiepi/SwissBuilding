# Distribution and Embedded Channels Program

## Mission

Extend SwissBuildingOS beyond its own standalone UI by preparing the channels through which it can be embedded, linked, consumed, or distributed inside the workflows of the market.

This program should strengthen:

- product distribution
- interoperability as adoption leverage
- embedded proof/readiness surfaces
- account expansion paths

## Why This Matters

If SwissBuildingOS wants to become infrastructure, it cannot depend only on users living inside its own app.

It should also be able to appear as:
- linked dossier surfaces
- embedded widgets
- partner-visible bounded views
- pack/status endpoints
- portfolio signals inside incumbent systems

This is how an overlay becomes a market layer.

## Core Outcomes

### 1. SwissBuilding becomes easier to embed

Expected:
- bounded embeddable views or summary surfaces
- stable external-facing artifacts for selected use cases
- cleaner integration into existing workflows

### 2. Distribution becomes productized

Expected:
- more ways for the product to spread inside an account
- more ways for the product to appear in adjacent systems without full migration

### 3. Interop starts creating pull

Expected:
- the product becomes easier to adopt because it can plug into incumbent habits
- building truth can travel without requiring full tool replacement

## Recommended Workstreams

### Workstream A — Embedded summary surfaces

- bounded building passport summary
- readiness/trust summary surfaces
- portfolio summary widgets where useful

### Workstream B — External and partner views

- lightweight external views for:
  - contributors
  - owners
  - authorities
  - executive stakeholders

### Workstream C — Stable integration artifacts

- URLs, exports, contracts, and machine-readable summaries that are safe to embed into incumbent workflows
- compatibility with portal-like or dashboard-like integrations later

### Workstream D — Expansion channels

- identify and productize paths where one successful project spreads to:
  - another building
  - another team
  - another business unit
  - another partner in the same workflow

## Candidate Improvements

- `EmbeddedPassportCard`
- `ReadinessWidget`
- `TrustWidget`
- `ExternalViewer`
- `PartnerSummaryEndpoint`
- `ExecutiveSnapshot`
- `BoundedEmbedToken`
- `AccountExpansionTrigger`

## Acceptance Criteria

- the product is easier to insert into adjacent workflows
- bounded external-facing surfaces become more deliberate
- interop supports account spread instead of just data movement
- SwissBuilding looks more like a layer and less like an isolated app

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

## Notes

This program is about making the product easier to adopt and harder to displace.

Prefer:
- bounded, useful embedded surfaces
- low-friction integration artifacts
- channels that support land-and-expand

Avoid:
- full white-label complexity too early
- broad API surface with no adoption story
