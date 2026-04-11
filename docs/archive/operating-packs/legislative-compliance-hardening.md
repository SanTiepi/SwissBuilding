# Legislative Compliance Hardening

## Mission

Run a dedicated product and architecture hardening project so SwissBuildingOS moves from:

- evidence-backed workflow assistant

to:

- executable regulatory reasoning layer with auditable proof outputs

This project is additive. It does not replace the other active workstreams. It should run in parallel when capacity exists and land in slices that strengthen the core dossier, readiness, and authority-pack story.

## Why This Project Exists

The app already has strong foundations:

- jurisdictions and regulatory packs
- dossier generation
- evidence links
- completeness and readiness primitives
- actions and packs

But there is still a structural gap between:

- the product narrative

and:

- the actual legal/compliance execution engine

The current system is still too generic in key places:

- thresholds and canton requirements are still partially hard-coded
- completeness can be mistaken for legal readiness
- dossier generation is not yet a fully archived proof artefact chain
- canton execution remains too generic
- AvT -> ApT and post-works proof are not yet treated as first-class compliance transitions

## Strategic Goal

Make SwissBuildingOS credible as:

- a building evidence layer
- a renovation readiness layer
- a dossier/proof engine

without overclaiming that the product itself guarantees legal compliance.

Target posture:

- the product guarantees completeness, provenance, versioning, workflow traceability, and proof packaging
- human experts and responsible actors remain accountable for legal sign-off

## Source Hygiene

For this project, official and regulatory sources come first:

- BFS / OFS
- BFE / OFEN
- BAFU / OFEV
- Suva / OTConst materials
- VD official canton sources
- GE official canton sources
- OFSP / BAG where relevant

Vendor claims may support workflow or competitor context, but not legal assertions.

If an important legal or workflow point is not fully verified, it must be marked as:

- `inference`
- `to_verify`

## Current Gaps To Close

### 1. Regulatory packs are not yet the true engine

The product already models `Jurisdiction` and `RegulatoryPack`, but the core compliance logic still relies too much on hard-coded Swiss and cantonal defaults.

Target:

- `RegulatoryPack` becomes the source of truth for thresholds, notifications, references, delays, work categories, and rule applicability

### 2. Completeness is not the same as legal readiness

Current completeness/readiness logic is useful product-wise, but it is too generic to be treated as a legally meaningful readiness engine.

Target:

- separate:
  - dossier completeness
  - dossier trust / reliability
  - legal/workflow readiness

### 3. Dossier output is not yet a full compliance archive chain

Generated packs and dossiers need durable archival and traceability.

Target:

- every generated authority-ready dossier becomes a first-class archived artefact
- export jobs reference durable files and metadata

### 4. Cantonal workflows are too generic

VD and GE are present conceptually, but not yet modeled as real execution packs with distinct artefacts, stages, and required attachments.

Target:

- first-class canton execution packs
- stage-sensitive obligations and artefacts

### 5. AvT -> ApT and post-works truth remain under-modeled

The system must understand not only what is required before work, but what is true after work.

Target:

- explicit before/after states
- reusable memory for future interventions

## Scope

### Workstream A — Executable Regulatory Packs

Goals:

- replace hard-coded thresholds and delays with pack-driven logic
- formalize pack layering:
  - Europe model
  - CH layer
  - canton layer
  - workflow / pollutant layer

Expected outputs:

- rule resolution service
- pack versioning discipline
- clear fallback behavior when no pack is fully defined

### Workstream B — Real Readiness Reasoner

Goals:

- stop conflating completeness and legal readiness
- introduce explicit states such as:
  - `safe_to_start`
  - `safe_to_tender`
  - `safe_to_reopen`
  - `safe_to_requalify`

Expected outputs:

- readiness reasoner fed by rules packs
- explicit checks, blockers, conditions, legal basis
- separation from generic completeness score

### Workstream C — Proof Artefacts and Dossier Archival

Goals:

- make generated dossiers and packs durable, versioned, and auditable

Expected outputs:

- archived PDF or HTML artefacts
- durable file linkage through `ExportJob`
- provenance metadata
- hash/version strategy if cleanly feasible

### Workstream D — Authority and Compliance Artefacts

Introduce first-class support for artefacts such as:

- authority submission
- authority acknowledgement
- waste manifest / disposal certificate
- post-remediation report
- air clearance report
- attestation of hazardous substances where applicable

These do not all need full UI immediately, but they should become modeled or reserved in a structured way if low-regret.

### Workstream E — AvT -> ApT and Post-Works Truth

Goals:

- represent what changes after intervention
- preserve what remains true, removed, encapsulated, or must be checked again

Expected outputs:

- stronger `PostWorksState` concept
- before/after comparison
- bridge with interventions, materials, evidence, and readiness

### Workstream F — UX and Liability Wording Hardening

Goals:

- ensure the product does not overclaim legal certainty
- keep UI wording disciplined

Rules:

- say:
  - completeness
  - provenance
  - traceability
  - readiness support
- avoid saying:
  - “legal compliance guaranteed”
  - “fully compliant by default”

## Recommended Delivery Sequence

1. make packs executable
2. build readiness reasoner on top
3. archive dossier outputs properly
4. model authority/compliance artefacts
5. land AvT -> ApT / post-works truth
6. harden wording and final proof UX

## Acceptance Criteria

This project is successful when:

- `RegulatoryPack` drives the main compliance reasoning path
- readiness output is distinct from completeness scoring
- dossier generation produces durable archived artefacts
- VD/GE are modeled as true execution packs, not generic metadata
- AvT -> ApT and post-works truth become explicit concepts
- no major UI surface overclaims legal guarantee

## Validation Expectations

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

## Delivery Rule

This project should be executed as a focused parallel track from `ORCHESTRATOR.md`.

It is not “nice to have”.
It is the hardening layer that makes the evidence/readiness/dossier story defensible at international-class quality.
