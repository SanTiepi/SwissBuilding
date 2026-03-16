# openBIM, Digital Logbook, and Passport Convergence Program

## Mission

Make SwissBuildingOS converge with the strongest emerging interoperability and building-record standards instead of remaining an isolated product model.

This program should align the platform with:

- openBIM interoperability
- Digital Building Logbook direction in Europe
- building renovation passport logic
- machine-readable exchange requirements
- future building/passport exchange standardization

## Why This Matters

Recent signals from Europe and openBIM ecosystems point in the same direction:

- machine-readable building records
- predictable exchange requirements
- interoperable building data
- reusable building passports/logbooks
- stronger digital permit, proof, and renovation workflows

If SwissBuilding wants to become a European reference layer, it should not invent everything in isolation.
It should align where standards are becoming strong, and differentiate where the market is still fragmented.

## Core Outcomes

### 1. SwissBuilding becomes openBIM-aware

Expected:
- clear support path for IFC-based building structure exchange
- BCF-style issue / contradiction / coordination interoperability where useful
- IDS-inspired validation of required information packages

### 2. SwissBuilding becomes Digital Building Logbook-ready

Expected:
- building passport and building memory can map toward a Digital Building Logbook logic
- readiness, proof, and post-works truth become exportable as structured building record layers

### 3. SwissBuilding gains stronger European credibility

Expected:
- closer fit with emerging EU and openBIM direction
- easier future integration with external BIM/CDE ecosystems
- less risk of becoming a dead-end proprietary model

## Recommended Workstreams

### Workstream A — openBIM interoperability foundations

- define how building, zone, element, material, plan, issue, and evidence concepts relate to:
  - IFC
  - BCF
  - IDS
  - bSDD
- do not overpromise full BIM authoring support
- focus on import/export, validation, and issue/proof coordination

### Workstream B — Digital Building Logbook mapping

- define a SwissBuilding mapping toward:
  - building passport
  - renovation history
  - documents
  - evidence
  - readiness
  - post-works truth
- make sure building memory is not just app-internal

### Workstream C — Renovation passport and readiness convergence

- align `safe_to_start`, `safe_to_renovate`, post-works truth, and dossier completeness with future renovation-passport style artifacts
- machine-readable outputs where sensible

### Workstream D — Information requirements and compliance checking

- introduce an IDS-like mindset:
  - what information is required
  - what is missing
  - what is invalid
  - what is satisfied
- this should strengthen readiness and pack generation

### Workstream E — Standards-facing export strategy

- define what SwissBuilding should export as:
  - machine-readable passport package
  - evidence bundle
  - issue/contradiction set
  - requirement compliance summary

## Candidate Improvements

- `IFCMappingProfile`
- `BCFIssueBridge`
- `IDSRequirementProfile`
- `DigitalBuildingLogbookMapping`
- `RenovationPassportExport`
- `BuildingPassportManifest`

## Reference Signals

Recent standards and policy references worth aligning with:

- EU Digital Building Logbook / renovation passport direction under EPBD-related work
- buildingSMART IFC 4.3 as the current ISO baseline
- buildingSMART IDS 1.0 as a finalized standard
- BCF / bSDD as interoperability patterns in openBIM ecosystems

This program should align pragmatically, not symbolically.

## Acceptance Criteria

- the repo contains a clear interoperability direction instead of implicit wishful thinking
- SwissBuilding concepts can be mapped toward openBIM and digital logbook/passport ecosystems
- readiness/completeness can evolve toward machine-readable requirement checking
- the product becomes more future-proof for European expansion

## Validation

If docs/architecture only:
- consistency check across:
  - `docs/architecture.md`
  - `docs/vision-100x-master-brief.md`
  - `docs/roadmap-next-batches.md`
  - `docs/product-frontier-map.md`
  - `MEMORY.md`

If code is touched:

Backend:
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

Prefer:
- selective high-value interoperability
- requirement validation leverage
- machine-readable record strategy

Avoid:
- pretending to become a full BIM authoring suite
- building giant standard adapters with no user value
