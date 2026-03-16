# Dataset Scenario Factory and Seed Strategy

## Mission

Turn SwissBuilding datasets into a first-class product and validation layer instead of a late-stage afterthought.

This program should create a **layered scenario strategy** that supports:

- demos
- operator workflows
- real e2e
- portfolio views
- authority/compliance packs
- multimodal document flows
- dirty/contradictory edge cases
- future agent verification loops

The goal is not one giant seed.
The goal is a **scenario factory**:

- deterministic
- reviewable
- rich enough for the actual product surface
- expandable without corrupting the baseline

## Why This Matters

SwissBuilding now includes:

- readiness
- trust
- contradictions
- post-works truth
- authority packs
- passports
- timelines
- portfolio signals
- multimodal ambitions

If datasets stay too shallow:

- UI looks complete on unrealistically clean cases
- engines optimize for perfect data
- real e2e becomes brittle
- demos underrepresent the product
- future agentic systems are trained on weak situations

The repo already has useful seeds:

- `seed_data.py`
- `seed_demo.py`
- `seed_demo_enrich.py`
- `seed_demo_authority.py`
- `seed_jurisdictions.py`
- `seed_verify.py`

But these should now be treated as the beginning of a layered dataset system, not the end state.

## Core Outcomes

### 1. Canonical dataset layers

SwissBuilding should explicitly support these scenario layers:

1. `demo_dataset`
   - visually impressive
   - authority-ready
   - stable for screenshots and storytelling
2. `ops_dataset`
   - realistic operator scenarios
   - incomplete dossiers
   - missing pieces
   - contradictions
3. `portfolio_dataset`
   - large enough for campaigns, signals, trust ranking, CAPEX, benchmarking
4. `compliance_dataset`
   - AvT/ApT
   - authority artefacts
   - disposal chain
   - post-remediation proofs
5. `multimodal_dataset`
   - PDFs
   - plans
   - images
   - technical plans
   - field photos
   - conflicting artifacts
6. `edgecase_dataset`
   - broken imports
   - stale evidence
   - orphaned references
   - contradictory snapshots
   - empty-but-valid states

### 2. Deterministic scenario generation

Expected:

- deterministic outputs for each scenario family
- stable IDs or stable references where practical
- explicit scenario names
- repeatable seed/reseed behavior
- no hidden randomness in canonical demo scenarios

### 3. Validation-aware seeds

The dataset layer should integrate with validation:

- `seed_verify.py` should know which scenario family is expected
- real e2e should fail fast if the wrong dataset shape is present
- demos should have a quick integrity check
- authority/compliance demos should assert required artifacts

### 4. Scenario richness, not just entity count

The strategy should optimize for scenario usefulness, not only row count.

Needed examples include:

- highly complete building
- nearly ready building with one blocker
- contradiction-heavy building
- post-works building with before/after truth
- portfolio cluster of similar buildings
- owner-facing building with budgets/vault/insurance memory
- authority-facing building with procedure chain
- building with multimodal evidence and uncertain reconstruction

## Recommended Workstreams

### Workstream A — Dataset taxonomy and control plane

- define the scenario families above
- decide how each maps to existing seed entry points
- document which scripts own which layer
- avoid one seed script becoming a giant unstructured monolith

### Workstream B — Seed architecture cleanup

- keep `seed_data.py` network-free and baseline-safe
- keep `seed_demo.py` as the demo-oriented orchestrator
- use specialized enrichers/add-ons where needed instead of bloating one file
- clarify how `seed_demo_authority.py` and `seed_jurisdictions.py` fit the layered strategy

### Workstream C — Scenario content enrichment

- add richer scenario templates for:
  - trust/readiness
  - contradictions
  - passport/time machine
  - authority packs
  - post-works truth
  - portfolio execution
- make sure at least one scenario exists for each newly visible product layer

### Workstream D — Verification and preflight

- extend `seed_verify.py`
- add scenario-sensitive checks
- clearly separate:
  - baseline seed verification
  - demo verification
  - authority/compliance verification
  - real-e2e preflight expectations

### Workstream E — Multimodal and dirty-data groundwork

- add fixture-friendly seed references for:
  - document bundles
  - plan bundles
  - field-photo placeholders
  - contradictory inputs
- do not overengineer OCR/AI at this stage; prepare the scenario substrate

## Suggested Design Rules

- keep baseline seed safe and fast
- enrich through layered scenario scripts, not hidden conditionals
- prefer a small number of high-value canonical buildings over random bulk noise
- every big new surface should eventually have:
  - one clean scenario
  - one messy scenario
  - one contradictory scenario if applicable
- treat seeds as product infrastructure, not test junk

## Candidate Deliverables

- a documented layered seed strategy
- clearer seed script ownership
- richer authority/demo/portfolio scenarios
- expanded `seed_verify.py`
- real-e2e preflight expectations tied to scenario families
- optional scenario manifests if they reduce ambiguity

## Acceptance Criteria

This program is complete when:

- the repo has an explicit layered dataset strategy
- existing seed scripts have clearer roles
- demo, ops, portfolio, compliance, multimodal, and edge-case scenarios are represented
- `seed_verify.py` can meaningfully detect insufficient scenario state
- Claude can continue building UI/engines without guessing whether the dataset will support them
- the product can be demonstrated on realistic and imperfect data, not only polished happy paths

## Metadata

- `macro_domain`: `12_infrastructure_standards_and_intelligence`
- `ring`: `ring_2_to_4`
- `user_surface`: `internal / demo / qa / real_e2e`
- `go_to_market_relevance`: `supporting`
- `moat_type`: `scenario_infrastructure`
- `depends_on`: `seed_data + seed_demo + seed_verify + current product surface`
