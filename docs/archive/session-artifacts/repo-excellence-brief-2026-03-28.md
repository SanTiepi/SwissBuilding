# Repo Excellence Brief

Date: 28 mars 2026
Status: Execution brief — use when it is safe to shift Claude onto repo-quality hardening
Depends on:
- `docs/projects/repo-quality-recovery-plan-2026-03-28.md`
- `docs/projects/repo-quality-and-coherence-hardening.md`
- `docs/projects/continuous-review-and-modernization-program.md`
- `docs/projects/claude-moonshot-evaluation-and-feedback-pack-2026-03-28.md`

---

## Mission

Raise SwissBuilding from:

- ambitious
- fast-shipping
- strategically coherent

to:

- structurally governable
- machine-checked
- migration-safe
- CI-trustworthy
- shell-coherent
- infrastructure-grade in repo discipline

This brief is not a feature brief.
It is a repo-excellence brief.

The target is not "cleaner code".
The target is:

- fewer hidden failure modes
- fewer reviewer-memory dependencies
- fewer giant-file regressions
- less control-plane overload
- stronger confidence that the repo can sustain Moonshot V1 closeout and eventually V2

Before implementation starts, Claude is explicitly allowed to add a short layer of his own repo-quality suggestions if they improve this brief.

Rule:

- suggestions must tighten the repo, not broaden product scope
- suggestions must fit one of these categories:
  - repo hygiene
  - CI/integrity
  - control-plane/docs
  - architecture fitness functions
  - shell convergence
  - budgets
  - monolith decomposition
  - migration/schema/API safety
  - dependency/security/release parity
  - ownership/review topology
- suggestions must be ranked
- suggestions must say whether they are:
  - `add now`
  - `defer`
  - `reject`
- suggestions must not reopen doctrine or invent a parallel excellence program

---

## Hard Non-Negotiable Rules

- do not touch active product code paths that Claude is already using for Moonshot V1 unless the wave is explicitly retargeted
- do not broaden product scope under the excuse of hardening
- do not rewrite for elegance
- do not create new canonical product surfaces
- do not edit `ORCHESTRATOR.md` unless the repo-quality wave is explicitly active and owns that control-plane work
- prefer machine-checkable guardrails over aspirational documentation
- prefer shrinking ambiguity over increasing framework complexity

---

## Priority Order

Execute in this order. Do not skip ahead unless blocked.

### 1. Repo hygiene and false-signal removal

Close obvious integrity leaks first:

- stop tracking local-only DB/log artifacts
- tighten ignore rules
- ensure generated/local byproducts are not treated as repo truth

Exit:

- working tree noise drops
- repo truth becomes cleaner immediately

### 2. CI integrity and confidence gating

Turn CI into a more honest signal:

- add repo-specific guardrails
- add structural checks where cheap enough
- make fast path vs confidence path explicit
- keep CI cost bounded, but stop allowing obviously incomplete green states

Minimum adds:

- `lead:check`
- `router:check`
- seed/inventory verification where low-cost
- dependency/vulnerability audit path staged or live

Exit:

- CI green means "repo integrity held", not just "lint passed"

### 3. Control-plane and doc lifecycle discipline

Reduce cognitive overload:

- split active board from archive/history
- add doc lifecycle states:
  - `canonical`
  - `active`
  - `archived`
  - `superseded`
- make current sources of truth obvious without scanning 150 docs

Exit:

- active execution files become small enough to trust again

### 4. Architecture fitness functions

Promote core structural rules into checks:

- giant file growth guard
- route-shell drift guard
- compatibility-surface growth guard
- control-plane/doc-size guard
- specialist-vs-hub route inventory

Rule:

- new drift should fail fast or at least warn loudly

Exit:

- architecture discipline no longer depends only on reviewer memory

### 5. Shell convergence and route contraction

Make runtime topology match doctrine:

- classify all pages as:
  - hub
  - contextual workspace
  - bounded specialist route
  - deprecated
- reduce route-zoo pressure
- make `App.tsx` reflect the real shell instead of legacy accumulation

Exit:

- the 5-hub doctrine is visible in route topology, not just in plans

### 6. Structural budget enforcement

Set and enforce budgets for:

- service size
- page size
- seed module size
- router size
- control-plane doc size
- bundle or route-chunk growth where practical

Rollout:

- baseline
- warn
- enforce on regressions

Exit:

- giant files stop normalizing themselves into the repo

### 7. Monolith decomposition

Prioritize the top concentration risks:

- `building_enrichment_service.py`
- `seed_data.py`
- `swiss_rules_spine_service.py`
- giant shell-driving pages where they still act as product centers

Goal:

- keep facades if useful
- break the internals into bounded modules
- improve testability and mergeability

Exit:

- top-heavy file concentration starts falling materially

### 8. Migration, schema, and API governance

Elevate safe evolution to a first-class concern:

- migration naming/scope conventions
- backfill posture
- seed/migration compatibility checks
- API/schema registry:
  - canonical
  - projection
  - compatibility
  - exchange

Exit:

- model growth becomes safer and easier to review

### 9. Dependency, security, and release parity

Harden repo operations:

- JS and Python dependency review cadence
- vulnerability gating policy
- local/staging/prod parity review
- real e2e environment ownership
- release artifact ownership

Exit:

- repo trust improves not only in code shape, but in operational reproducibility

### 10. Ownership and review topology

Make hot spots explicit:

- high-centrality files
- hub files
- review-critical zones
- conflict-prone zones
- wave-collision zones

Exit:

- future waves can be planned from topology, not instinct

---

## Explicit Deliverables

This brief is complete only if it produces:

- one cleanup pass for tracked local artifacts
- one CI hardening pass
- one active-vs-archive control-plane split design
- one doc lifecycle registry or equivalent metadata rule
- one architecture fitness-function layer
- one route/page topology inventory with shell classification
- one structural budget baseline and enforcement rule
- one decomposition plan for the top monoliths
- one migration/schema/API governance pack
- one dependency/security/parity hardening pack
- one ownership/review topology map

Plus one optional pre-flight note:

- `Claude repo-quality suggestions before execution`

This note must stay short and include only:

- top `1-5` additions or corrections to the brief
- why they matter
- whether they should be added now, deferred, or rejected

---

## Repo Excellence Fitness Functions

These are the minimum machine-checkable functions the repo should grow toward.

### F1. Tracked artifact guard

Fail or warn when repo-tracked files include local-only artifacts such as:

- preview DBs
- pytest logs
- local scratch exports

Expected enforcement:

- `.gitignore`
- CI or local repo-integrity script

### F2. Control-plane size guard

Warn and later fail if active control-plane files exceed agreed limits:

- `ORCHESTRATOR.md`
- `MEMORY.md`

Expected enforcement:

- line-count thresholds
- archive split requirement when exceeded

### F3. Route-shell drift guard

Detect growth away from the 5-hub shell:

- count of standalone top-level routes
- count of bounded specialist routes
- count of deprecated-but-still-live routes

Expected enforcement:

- route inventory script
- warning on route-zoo growth

### F4. Giant file regression guard

Track and gate growth in:

- backend services
- frontend pages
- seeds
- router/bootstrap files

Expected enforcement:

- size thresholds
- exception list with explicit justification

### F5. Compatibility-surface growth guard

Detect when compatibility-only surfaces grow in semantics or footprint.

Targets:

- legacy APIs
- bridge services
- deprecated pages that still gain new logic

Expected enforcement:

- compatibility registry
- touched-file review rules

### F6. API/router coherence guard

Keep API growth legible and wired coherently.

Expected enforcement:

- `router:check`
- API inventory output
- classification of routes into:
  - canonical
  - projection
  - compatibility
  - exchange

### F7. Test budget guard

Keep test growth high-signal and bounded.

Expected enforcement:

- existing `test_budget_guard.py`
- refreshed baselines only after structural reductions, not as routine escape hatches

### F8. Dependency and vulnerability guard

Introduce explicit checks for:

- JS dependency vulnerabilities
- Python dependency vulnerabilities
- stale critical packages

Expected enforcement:

- CI job or scheduled check
- explicit exception posture

### F9. Seed and migration compatibility guard

Prevent schema growth from outrunning seed/runtime compatibility.

Expected enforcement:

- seed verify
- migration/seed contract checks
- backfill review path for risky changes

### F10. Bundle and performance budget guard

Keep scale friction visible.

Targets:

- frontend build chunk size
- page-level heavy bundles
- expensive route surfaces

Expected enforcement:

- build output checks
- explicit thresholds
- route-level offenders reported, not hidden

---

## Acceptance Gates

### Gate A — Hygiene

- no obvious local-only artifacts remain tracked
- generated noise is no longer confused with repo truth

### Gate B — Confidence

- CI checks repo-specific integrity, not just generic language tooling
- green CI correlates better with actual repo health

### Gate C — Governance

- active docs are distinguishable from archive and superseded material
- architecture constraints are partially machine-checkable

### Gate D — Runtime coherence

- route topology visibly converges toward 5 hubs + contextual workspaces
- giant page/service/seed concentrations stop getting worse

### Gate E — Safe evolution

- migration/backfill/API/schema discipline is explicit
- dependency/security/release posture is no longer ad hoc

### Gate F — V1 closeout readiness

Before allowing this repo to be treated as V2-capable, require:

- lean control plane
- doc lifecycle clarity
- shell convergence visible
- top monoliths on a real decomposition path
- repo integrity checks live
- structural budgets enforced on regressions

---

## Recommended Return Format for Claude

When Claude works from this brief, require this return format:

0. `Pre-flight suggestions`
- top `1-5` improvements to the brief itself before execution
- each tagged:
  - `add now`
  - `defer`
  - `reject`

1. `Material repo-quality progress`
- what became stricter or more governable

2. `Machine-checkable improvements`
- what moved from convention to enforcement

3. `Structural debt reduced`
- which giant files, route islands, or control-plane overloads got better

4. `Still risky`
- what remains dangerous or too manual

5. `Validation`
- exact commands/checks run
- exact result

6. `Next repo-quality move`
- one bounded recommendation only

---

## Final Rule

Repo excellence is not achieved when the repo looks nicer.

Repo excellence is achieved when:

- doctrine and runtime topology stop diverging
- structure stops relying on memory alone
- CI becomes a serious integrity signal
- large-scale change becomes safer
- and the repo can carry category ambition without collapsing under its own complexity
