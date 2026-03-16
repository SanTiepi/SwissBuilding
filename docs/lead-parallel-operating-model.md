# Lead Parallel Operating Model

This document defines what Codex should keep doing in parallel while Claude executes the large implementation waves.

Companion file:

- `docs/lead-master-plan.md` = canonical structured lead plan
- `docs/lead-ongoing-backlog.md` = durable long-form lead backlog of things Codex should keep pushing while Claude executes

It exists to avoid a bad operating pattern where:

- Claude ships code
- Codex waits passively
- strategic, QA, and next-wave work accumulates too late

Instead, Codex should stay ahead of execution through four continuous streams.

Use `docs/lead-master-plan.md` as the planning reference and this file as the concise operating doctrine.

## Non-Negotiable Invariants

Apply these invariants while running all four parallel streams:

- preserve identifier truth: `egid` != `egrid` != `official_id`
- prefer official public sources; avoid scraper-first ingestion shortcuts
- keep Vaud source layers and RegBL/MADD mapping layers explicitly separated
- avoid partially wired UX; hide or simplify incomplete flows
- optimize for autonomous `Codex + ClaudeCode` execution and command-based validation

## Delegation Rule

When a task is better suited to Claude, Codex should delegate it through repo-native briefs instead of holding it back.

Default split:

- Claude takes:
  - implementation-heavy work
  - large schema/service/API/UI waves
  - seed architecture changes
  - long-running refactors
  - integration-heavy work
  - test/fixture modernization when it spans multiple domains
- Codex keeps:
  - execution foresight
  - acceptance and QA parallelism
  - doc/repo coherence
  - frontier expansion
  - market/category/moat pressure
  - low-risk cleanup that does not interfere with active Claude waves

Rule:
- if Claude can do it better or faster, turn it into a repo-visible brief and move on
- Codex should not become a bottleneck by holding implementation-heavy work that already has a clear pull path
- once the system reaches service saturation, Codex should bias the repo toward depth:
  - consolidation
  - productization
  - dataset realism
  - integration truth
  - real validation
  rather than continuously opening more additive backend primitives

## 1. Execution Foresight

Purpose:

- keep the repo ahead of the current implementation wave

Responsibilities:

- keep `ORCHESTRATOR.md` ahead of the active execution state
- maintain:
  - `Execution Board`
  - `Immediate Post-W10 Chain`
  - `Next 10 Actions`
  - `Next Queue (11+)`
  - future horizons
  - runway waves
- keep `Next 10` strict at exactly `10` ranked items
- pre-package the next `3` executable waves with disjoint scopes
- require binary `PASS/FAIL` readiness gate before each wave launch
- require binary `PASS/FAIL` closeout gate before promoting the next wave
- convert emerging ideas into dedicated project briefs under `docs/projects/`
- detect sequencing risks and dependency traps before Claude hits them

Success condition:

- Claude never finishes a wave without a clear next pull already visible in the repo
- Claude can launch the next wave without waiting for ad-hoc clarification

## 2. Product Frontier Expansion

Purpose:

- push the product frontier beyond what is already built

Responsibilities:

- enrich `docs/product-frontier-map.md`
- structure new:
  - uses
  - engines
  - packs
  - states
  - standards
  - internal tools
- merge duplicates and keep the frontier map clean
- promote mature idea clusters into concrete project briefs

Priority families:

- `safe_to_sell / insure / finance`
- `building passport exchange`
- `portfolio command center`
- `ecosystem network`
- `agent governance`
- `field operations`
- `contradiction / unknowns / trust`

Success condition:

- the frontier keeps expanding without becoming chaotic, and the next 2–6 waves are always visible

## 3. Acceptance and QA Parallelism

Purpose:

- verify reality while Claude builds

Responsibilities:

- verify important Claude claims with real commands when useful
- run targeted UI and validation checks on recent surfaces
- detect:
  - `doc vs code`
  - `mock vs real`
  - `claim vs reality`
- push findings into repo-facing control-plane docs, not only into chat
- keep the `Lead Feed` current

Current QA priorities:

- outputs of `W10-A/B/C`
- readiness / trust / unknowns / post-works productization
- quality dashboard
- export progress UI
- visual regression noise
- `e2e:real` environment hardening

Success condition:

- important mismatches are found before they become product drift

## 4. Market, Category, and Moat Pressure

Purpose:

- prevent product drift toward feature accumulation without category power

Responsibilities:

- keep Europe model -> Switzerland launch -> canton execution logic coherent
- connect upcoming programs to:
  - wedge
  - moat
  - sales story
  - killer demos
- maintain international-class expectations:
  - proof
  - auditability
  - interoperability
  - reliability

Persistent strategic anchors:

- `safe-to-start dossier`
- `Building Evidence Layer`
- `Agent OS`
- `building passport`
- `proof + readiness + orchestration + portfolio`
- `international-class`, not just Swiss-tool grade

Success condition:

- the product remains category-shaping, not just feature-rich

## Maturity-Gate Leadership

Do not reason in calendar phases here.
Reason in **product maturity gates**:

### Gate 1 - Wedge dominance

Protect:
- evidence quality
- readiness clarity
- dossier completeness
- authority/contractor pack credibility
- workflow repeatability

Lead focus:
- remove wedge friction
- harden proof and compliance flows
- keep the first commercial promise undeniable

### Gate 2 - Building operating system

Protect:
- building memory coherence
- post-works truth
- physical model depth
- owner/occupancy/operations extensions
- contradiction and unknown handling

Lead focus:
- make the building indispensable day to day
- expand without breaking truth or usability

### Gate 3 - Portfolio and capital system

Protect:
- campaign execution
- scenario persistence
- CAPEX translation
- portfolio prioritization
- benchmark and trust comparability

Lead focus:
- turn many buildings into one decision surface
- keep portfolio logic grounded in proof, not dashboard theater

### Gate 4 - Infrastructure and market standard

Protect:
- exchange contracts
- legal-grade trust
- partner APIs
- identity/governance
- standards convergence
- ecosystem dependence

Lead focus:
- make SwissBuilding easier to build on top of than around
- convert product strength into market infrastructure strength

Rule:
- Claude should be evaluated against the current gate and the next gate
- Codex should keep the repo prepared for the next gate before the current one is fully saturated

## Immediate Operating Rule After W10

Once `W10-A/B/C` land:

1. verify they delivered:
   - real service logic
   - tests
   - actual product leverage
2. if yes, push productization in this order:
   - `BuildingTrustScore` into useful UI
   - `UnknownIssue` into useful UI
   - `PostWorksState` into before/after surfaces
   - readiness UI on top of them
3. if no, document the gap in `ORCHESTRATOR.md` immediately and reorder the next wave
4. then prioritize:
   - `legislative-compliance-hardening`
   - `trust-readiness-postworks-program`
   - `portfolio-execution-and-packs-program`

## Prioritization Rule

When several future moves are possible, prefer what:

1. reduces model debt
2. strengthens proof / trust / readiness
3. improves demonstrability
4. increases moat
5. prepares internationalization
6. lets Claude keep moving without a new prompt

Avoid prioritizing:

- isolated polish
- gadget features
- secondary screens without engine value
- modules that add no proof, memory, orchestration, or portfolio leverage
- additive primitives whose main effect is codebase breadth rather than clearer product truth

## Operating Success Criteria

Codex is doing the right parallel work when:

- Claude does not stall for lack of direction
- upcoming project briefs already exist in `docs/projects/`
- `ORCHESTRATOR.md` stays ahead of the active wave
- wave readiness and closeout gates are explicit and binary
- `Next 10` stays disciplined instead of absorbing overflow items
- the frontier keeps opening future territory
- QA catches real mismatches early
- strategy, market wedge, and product architecture remain coherent
