# Repo Quality Recovery Plan

Date: 28 mars 2026
Status: Active supporting plan — safe to prepare in parallel while Moonshot V1 is executing
Depends on:
- `docs/projects/repo-quality-and-coherence-hardening.md`
- `docs/projects/continuous-review-and-modernization-program.md`
- `docs/projects/duplicate-service-consolidation-brief.md`
- `docs/projects/service-consumer-mapping-and-dead-code-pruning-program.md`
- `docs/projects/claude-moonshot-evaluation-and-feedback-pack-2026-03-28.md`

---

## Summary

SwissBuilding has strong product ambition and a credible category direction.
The current repo risk is no longer "not enough ideas".
It is:

- control-plane overload
- documentation sprawl
- monolithic service/page/seed concentration
- shell convergence lag
- CI confidence gaps
- repo hygiene drift

This plan is intentionally stricter than the existing coherence docs.
It treats repo quality as a **delivery risk**, not as cosmetic cleanup.

It is still not the "ultimate repo" plan unless it also covers:

- machine-checkable architecture fitness functions
- dependency and vulnerability governance
- migration and backfill safety
- release/environment parity
- ownership and review topology
- schema/API registry discipline
- performance and bundle budgets
- observability and recovery posture for critical developer and operator flows

Operating rule while Claude is executing Moonshot V1:

- safe in parallel:
  - audits
  - docs/plans
  - non-mutating inventories
  - later-ready remediation briefs
- unsafe in parallel:
  - touching active product code paths Claude is likely editing
  - changing `ORCHESTRATOR.md`
  - broad route-shell refactors
  - large seed/service decomposition

So this plan is structured in four buckets:

- `Fix now`
- `Fix this week`
- `Fix before V1 closeout`
- `Acceptable debt`

And across three ambition levels:

- `Recovery` = stop obvious repo drift
- `Governance` = make structural quality machine-checkable
- `Excellence` = make the repo durable enough for market-infrastructure ambitions

---

## Current Severity Assessment

### 1. Control-plane and doc load is too high

Signals:

- `ORCHESTRATOR.md` is ~2748 lines and mixes live control plane, historical baselines, and broad runway
- `MEMORY.md` is ~350 lines and still accumulating strategy stack references
- `docs/projects/` contains ~150 project docs

Risk:

- agents scan too much
- source-of-truth boundaries blur
- active execution gets slower and less reliable

### 2. Backend concentration is too high in a few files

High-risk concentrations:

- `backend/app/services/building_enrichment_service.py`
- `backend/app/services/swiss_rules_spine_service.py`
- `backend/app/seeds/seed_data.py`

Risk:

- merge conflicts
- poor testability
- hidden coupling
- hard-to-review logic blobs

### 3. Frontend shell convergence is not yet real

Signals:

- `frontend/src/App.tsx` still carries a broad route zoo
- `frontend/src/pages/` contains ~70+ pages
- several specialist pages remain very large and effectively own product centers

Risk:

- doctrine says `5 hubs + contextual workspaces`
- runtime still behaves like many product islands

### 4. CI and repo hygiene under-prove correctness

Signals:

- CI does not run repo-specific guardrails
- backend CI excludes integration tests by default
- repo-tracked local artifacts/logs exist:
  - `backend/local_preview.db`
  - `backend/pytest_collect.log`
  - `backend/pytest_subset.log`

Risk:

- green CI overstates confidence
- repo gets noisier and less reproducible

### 5. Config and packaging are still too light for repo scale

Signals:

- backend uses flat `requirements.txt`
- runtime/test/dev concerns are not cleanly separated
- structural budgets are not enforced automatically

Risk:

- setup and upgrade drift
- weak dependency hygiene
- no pressure against growing monoliths

### 6. Architecture constraints are not enforced strongly enough by tooling

Signals:

- doctrine is strong, but most architectural guarantees are still doc-enforced
- scripts already exist for budgets, router inventory, and control-plane checks
- there is not yet one explicit fitness-function layer for:
  - shell convergence
  - giant file regression
  - projection registry discipline
  - compatibility surface growth

Risk:

- the repo can drift structurally while still "passing"
- discipline depends too much on reviewer memory

### 7. Dependency, security, and release posture are under-governed

Signals:

- CI does not currently run dependency/vulnerability checks by default
- backend and frontend dependency governance are not first-class in the recovery plan yet
- release parity and environment ownership are discussed in docs, but not yet centralized as a hard repo-quality concern

Risk:

- silent dependency drift
- security regressions caught late
- environment mismatch continues to weaken confidence

### 8. Migration and backfill safety are not elevated enough

Signals:

- the repo is adding many new models and surfaces quickly
- build-order and migration discipline appear in docs, but not yet as a core repo-quality workstream

Risk:

- growth outpaces migration safety conventions
- backfills become ad hoc
- "fast product progress" creates future upgrade fragility

### 9. Ownership and review topology are still implicit

Signals:

- many files are high-churn or high-centrality
- repo docs define roles, but ownership of hot spots and review-critical zones is still mostly social, not explicit

Risk:

- bus-factor concentration
- weak review routing
- hardening work lands slower because hot spots are not clearly governed

---

## Fix Now

These are the highest-leverage actions to prepare immediately and execute first when safe.

### A. Repo hygiene cleanup pack

Prepare a tiny cleanup pass to:

- remove repo-tracked local DB/log artifacts from Git
- extend `.gitignore` for local preview DBs, pytest logs, and similar noise
- verify no other generated/local-only artifacts are meant to stay versioned

Acceptance:

- the repo no longer tracks local SQLite/log byproducts
- working tree noise drops

### B. CI confidence hardening plan

Prepare one CI upgrade brief that adds:

- repo guardrails:
  - `npm run lead:check`
  - `npm run router:check`
- backend seed/inventory verification where cheap enough
- clearer separation between:
  - fast green path
  - confidence path
  - expensive full path

Acceptance:

- CI green means more than lint + partial tests
- repo-specific integrity checks stop being optional local discipline

### C. Doc and control-plane lifecycle registry

Prepare a lightweight status registry for docs:

- `canonical`
- `active`
- `archived`
- `superseded`

Do not rewrite 150 docs now.
Start with the highest-value layer:

- `MEMORY.md`
- `ORCHESTRATOR.md`
- V3 doctrine stack
- moonshot stack
- major active project docs

Acceptance:

- an engineer can tell which docs matter now without scanning everything

### D. Architecture fitness-function brief

Prepare one repo-integrity brief that turns major architecture invariants into machine-checkable gates.

First targets:

- giant file growth guard
- route-shell drift guard
- hub-vs-specialist route inventory
- compatibility-surface expansion guard
- doc/control-plane size guard

Acceptance:

- structural drift becomes visible in CI or local guardrails, not only in review comments

### E. Dependency and vulnerability governance brief

Prepare one dependency-quality brief that covers:

- JS audit path
- Python dependency audit path
- stale dependency review cadence
- exception policy for known issues
- CI gating posture for critical findings

Acceptance:

- dependency hygiene stops being a side concern

---

## Fix This Week

These should be the first structural recovery wave once it is safe to mutate repo code/docs more broadly.

### A. Control-plane split

Refactor the control plane into:

- `ORCHESTRATOR.md` = live board only
- one archived wave history file
- one machine-readable counters file (`json` or `yaml`)

Rules:

- keep `ORCHESTRATOR.md` under a hard size target
- no historical validation baselines in the active board
- no long archived task tables in the live file

Acceptance:

- active board becomes fast to scan again
- counters are easier to update mechanically

### B. Shell convergence inventory to action

Take the route/page sprawl and classify every standalone page as:

- `hub`
- `contextual workspace`
- `bounded specialist route`
- `deprecated`

Prioritize the obvious doctrinal stragglers:

- change/safe-to-x/decision/readiness specialist centers
- duplicated portfolio surfaces
- old building specialist routes that should become Building Home tabs/panels

Acceptance:

- route map starts visibly converging toward the shell doctrine

### C. Structural budget guardrails

Introduce repo-level budgets for:

- service file size
- page file size
- seed module size
- router size
- control-plane doc size

Implementation posture:

- warn first
- then enforce on new regressions
- allow explicit exceptions only with named justification

Acceptance:

- the repo stops quietly normalizing giant files

### D. Release and environment parity pass

Add one repo-quality stream for:

- real e2e environment ownership
- seed/runtime parity
- local/staging/prod config shape review
- generated artifact ownership and cleanup

Acceptance:

- environment mismatch is treated as repo debt, not as operational bad luck

### E. Ownership and review-topology map

Create a lightweight map for:

- high-centrality files
- hot review zones
- hub files
- giant monolith candidates
- wave-conflict zones

Acceptance:

- future hardening and wave planning have an explicit topology instead of intuition only

---

## Fix Before V1 Closeout

These are deeper remediations that should happen before claiming the repo is healthy enough for V2.

### A. Decompose the enrichment monolith

Refactor `building_enrichment_service.py` into:

- provider adapters
- identity/geocoding
- context overlays
- scoring
- narrative generation
- finance/subsidy estimation
- orchestration entrypoint

Goal:

- keep one facade if useful
- remove the single 4k-line service blob

### B. Decompose the seed monolith

Refactor `seed_data.py` into:

- scenario packs
- seed factories
- modular seed steps
- clearer seed verification contracts

Goal:

- seeded truth becomes composable and lower-conflict

### C. Move Swiss rules toward declarative substrate

Begin extracting large inline builders into:

- profile/config files
- registries
- smaller loaders/builders

Goal:

- less imperative doctrine encoded directly in giant Python functions

### D. Route and page contraction

Reduce the number of de facto product centers by:

- absorbing obvious specialist pages into hubs/contextual workspaces
- shrinking giant page components into shell + sections + hooks
- making `App.tsx` more obviously shell-driven rather than route-zoo-driven

Acceptance for this whole bucket:

- repo structure no longer visibly contradicts the doctrine

### E. Migration and backfill safety program

Before V1 closeout, formalize:

- migration naming and scope conventions
- backfill strategy
- rollback posture
- seed/migration compatibility checks
- high-risk schema evolution review path

Goal:

- fast model growth no longer implies fragile upgrades

### F. API/schema registry discipline

Add a stronger registry for:

- canonical APIs
- compatibility APIs
- projection APIs
- exchange/transfer contracts
- schema versions

Goal:

- API and schema growth become more governable and easier to review

### G. Performance and bundle-budget enforcement

Formalize budgets for:

- frontend bundle size
- route-level chunk growth
- critical query fan-out
- expensive pages
- heavyweight seed/build/test flows where measurable

Goal:

- scale friction is caught early, not after the shell is already bloated

---

## Acceptable Debt

These may remain for now without blocking V1 closeout, as long as they are logged explicitly.

### 1. Partial documentation supersession

Not every old project doc needs cleanup immediately.
It is acceptable if a status registry clearly marks what is active vs stale.

### 2. Bounded specialist pages

Some specialist routes may survive temporarily if they are explicitly classified as:

- bounded
- non-canonical
- destined for absorption or retirement later

### 3. Transitional config shape

Moving backend packaging from `requirements.txt` to a more structured setup can wait slightly if:

- dependency hygiene is otherwise stable
- CI and local setup remain deterministic

### 4. Non-critical service family overlap

Not every duplicate service family needs immediate consolidation.
Priority stays on the largest or most conflict-prone families first.

### 5. Transitional ownership formalization

Explicit ownership maps may remain light for now if:

- hot spots are at least known
- wave scopes stay disciplined
- review routing remains workable

---

## Recommended Execution Order

When it is safe to act, the order should be:

1. repo hygiene cleanup
2. CI confidence hardening
3. control-plane split
4. doc lifecycle registry
5. shell convergence inventory to action
6. structural budget guardrails
7. enrichment monolith decomposition
8. seed monolith decomposition
9. rules substrate declarativization
10. migration/backfill safety program
11. API/schema registry discipline
12. performance/bundle budget enforcement
13. ownership/review topology hardening
14. broader service-family consolidation

This order maximizes signal and reduces future refactor cost.

---

## Test and Acceptance

### Immediate review checks

- repo no longer tracks obvious local-only artifacts
- CI plan covers repo-specific guardrails
- live control-plane content becomes distinguishable from archive/history
- shell convergence inventory can classify every current page

### Structural acceptance checks

- no active service or page file quietly grows past agreed budget without explicit exception
- no active board or memory file becomes a mixed archive again
- giant files start shrinking at the top of the size distribution
- route topology starts matching the doctrine in practice, not just in docs
- architecture invariants start becoming machine-checkable
- dependency/security/release drift become visible earlier

### V1-closeout quality gate

Before declaring repo quality healthy enough for a V2 jump, require:

- active board is lean again
- docs have clear lifecycle status
- CI checks repo integrity, not just code style and partial tests
- at least the top enrichment and seed monoliths have a decomposition path implemented or nearly complete
- shell convergence is visibly real in runtime topology
- migration/backfill discipline is explicit and enforceable
- dependency and vulnerability posture is not guesswork
- API/schema growth is registered and reviewable

---

## Assumptions and Defaults

- This plan is intentionally stricter than the existing coherence programs.
- It is meant to run in parallel as planning/prep while Claude focuses on Moonshot V1 implementation.
- It avoids risky overlapping edits now and defers structural mutations until they are safe.
- The target is not "clean repo aesthetics"; the target is keeping SwissBuilding governable at its current ambition level.
- The "best repo possible" for SwissBuilding means not only clearer docs and smaller files, but also enforceable structural quality, safer evolution, and infrastructure-grade operability.
