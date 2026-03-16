# Service Consumer Mapping and Dead-Code Pruning Program

## Mission

Reduce backend breadth without losing capability by making service usage explicit, identifying orphaned primitives, and pruning or consolidating code that no longer earns its maintenance cost.

## Why this matters now

SwissBuilding has accumulated a large service surface. The main risk is no longer missing primitives, but:

- overlapping calculators querying the same models independently
- services with no meaningful frontend, API, job, seed, or facade consumer
- domain logic spread across too many first-class modules
- rising maintenance cost without proportional product value

This program exists to convert "many services" into "few coherent domain surfaces".

## Strategic outcome

- explicit map of which services are actually consumed
- domain-level facades backed by smaller internal helpers
- fewer orphaned services
- clearer productization path from backend capability to user-facing value
- less accidental architecture breadth

## Macro metadata

- `macro_domain`: `12_infrastructure_standards_and_intelligence`
- `ring`: `ring_1_to_3`
- `user_surface`: `internal`
- `go_to_market_relevance`: `supporting`
- `moat_type`: `operability_and_productization_discipline`
- `depends_on`: `domain-facades-and-service-consolidation-program.md`, `full-chain-integration-and-demo-truth-program.md`

## Scope

1. Build a service inventory:
   - service file
   - domain
   - primary purpose
   - consumers:
     - API
     - background job
     - seed/demo flow
     - frontend surface (direct or via API)
     - other service/facade

2. Classify each service:
   - `core_domain`
   - `composed_helper`
   - `orphaned`
   - `duplicate_or_overlapping`
   - `legacy_candidate`

3. Produce a pruning and consolidation plan:
   - merge overlapping services into facades
   - demote internal helpers from first-class status when appropriate
   - remove clearly unused dead code where low-risk
   - mark keep-but-internal where still useful

4. Add a lightweight guardrail:
   - no new service without:
     - domain fit
     - consumer path
     - explanation for why it is not an extension of an existing facade

## Baseline inventory artifacts

The first automatic inventory now exists and should be treated as the factual starting point for this program:

- `backend/scripts/service_consumer_inventory.py`
- `docs/service-consumer-map.md`
- `docs/service-consumer-map.json`

Current baseline from the generated inventory:

- total backend service modules: `121`
- heuristic classifications:
  - `115` `core_domain`
  - `2` `composed_helper`
  - `4` `orphaned`
- largest context clusters:
  - `building`
  - `compliance`
  - `document`
  - `risk`
- clear orphaned review candidates already visible:
  - `avt_apt_transition`
  - `data_export_service`
  - `dossier_archive_service`
  - `maintenance_schedule_service`

Important:
- this baseline is intentionally import-driven and conservative
- it is good enough to identify obvious orphans and cluster pressure
- it is not yet a semantic architecture verdict
- the next step is a context/facade review, not blind deletion

## Suggested workstreams

### A. Inventory and consumer graph

- generate a machine-readable map:
  - service -> consumers
  - domain -> services
  - orphan candidates

### B. Facade alignment

- align services into bounded contexts such as:
  - Evidence
  - Readiness
  - Trust
  - Compliance
  - Portfolio
  - Post-Works / Remediation

### C. Low-risk pruning

- remove or quarantine services with:
  - no caller
  - superseded behavior
  - duplicated value

### D. Repo guidance

- add one concise rule in repo docs:
  - a new service must justify its consumer path or facade fit

## Acceptance criteria

- there is an explicit service inventory
- orphan / duplicate / legacy candidates are identified
- the most obvious dead or duplicate surfaces are removed or demoted
- domain-facade work and pruning work are aligned, not competing
- the repo makes it harder to keep shipping orphaned services

## Out of scope

- rewriting all services at once
- deleting useful internal helpers just to reduce counts
- forcing a purity refactor that breaks shipped flows
