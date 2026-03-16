# Lead Ongoing Backlog

This file is the durable backlog of parallel lead work Codex should keep advancing while Claude executes implementation waves.

It is intentionally broader than the active execution board.

Planning hierarchy:
- `docs/lead-master-plan.md` = canonical lead plan
- this file = durable long-form backlog under that plan
- `ORCHESTRATOR.md` = active execution control plane

Rules:

- prefer repo-facing work that keeps Claude moving without waiting
- prefer verification, coherence, category pressure, and low-regret anticipation
- close or merge items when they are no longer distinct
- do not duplicate active execution tasks that already belong in `ORCHESTRATOR.md`
- if a task is clearly implementation-heavy and Claude can absorb it faster, convert it into a brief and delegate it instead of retaining it here

## 1. Execution Foresight

- keep `ORCHESTRATOR.md` ahead of the currently active wave
- keep `Next 10 Actions` realistic and reorder after every meaningful wave
- keep `Future Horizon Feed` grouped by macro-domain, not as a flat backlog
- keep `Autonomous 60-Day Runway` aligned with the real gate, not stale intent
- check whether newly completed waves should promote the next briefs automatically
- maintain a post-wave absorption checklist for Claude outputs:
  - baseline counters
  - docs alignment
  - productization needs
  - QA needs
- detect prerequisite debt before it blocks the next wave
- split upcoming work into:
  - immediate productization
  - low-regret primitives
  - strategic programs
- keep a rolling shortlist of the next 3 system families after the current gate
- ensure every new program in `docs/projects/` has a clear pull path from the active gate

## 2. Acceptance and QA Parallelism

### 2.1 Frontend QA

- keep closing silent-failure states on newly productized surfaces
- keep adding dedicated tests for newly visible trust/readiness/passport/time-machine surfaces
- reduce remaining Vite chunk warnings on `index` and especially `map`
- audit lazy-loading and chunk topology for new pages/components
- keep visual regression baselines fresh and low-noise
- identify surfaces still covered only indirectly through broad e2e tests
- expand targeted unit coverage for new components as they appear
- keep error states coherent:
  - loading
  - empty
  - error
  - partial data
  - fallback mode
- keep test growth bounded with budget guards:
  - `scripts/test_budget_guard.py`
  - `docs/test-budget-guard.json`
- keep dark mode parity on newly added pages
- keep mobile breakpoints honest on newly added surfaces

### 2.2 Real vs Mock Validation

- keep mock and real e2e ownership explicitly separated
- keep a known-good backend targeting note for `test:e2e:real`
- harden preflight checks before real e2e runs
- verify seeded scenarios remain aligned with the newest product layers
- keep a checklist of “real integration only” risks:
  - wrong backend target
  - wrong seed state
  - stale auth state
  - missing storage provider
  - missing Gotenberg/ClamAV/Redis/Meilisearch integrations

### 2.3 Backend Verification

- spot-check major Claude claims with real commands when the risk of drift is meaningful
- keep an eye on warnings regressing into backend tests
- audit migration safety when new models and services appear fast
- verify seed determinism after big schema extensions
- verify dossier/export flows still behave coherently when new evidence objects are added

## 3. Documentation and Repo Coherence

- keep `README.md`, `docs/vision-100x-master-brief.md`, `docs/roadmap-next-batches.md`, `MEMORY.md`, and `ORCHESTRATOR.md` aligned
- keep `docs/projects/README.md` readable as the project catalog grows
- keep “implemented vs reserved future domain” lines truthful
- keep model/service/API/page counters truthful when Claude lands waves
- keep naming drift under control:
  - avoid unnecessary `_v2`, `_new`, `_next`
  - prefer canonical names once a concept is first-class
- keep architectural docs representative of the actual system
- add missing “source of truth” notes when a new file becomes canonical
- keep prompt conventions concise and repo-first
- ensure the repo still has:
  - one bootstrap layer
  - one rules layer
  - one durable-memory layer
  - one execution-control layer

## 4. Product Frontier Expansion

### 4.1 Core engines to keep pushing

- `Building Passport Engine`
- `Evidence Graph Engine`
- `Readiness Engine`
- `Post-Works Truth Engine`
- `Unknowns Engine`
- `Contradiction Engine`
- `Portfolio Opportunity Engine`
- `Building Trust Score`
- `Decision Replay`
- `Weak-Signal Watchtower`

### 4.2 Still-underrepresented domains to watch

- tenancy and occupancy economics
- utilities and recurring services
- incident, emergency, and continuity
- procurement, vendors, and SLA control
- circularity and material afterlife
- tax, incentive, and fiscal readiness
- climate resilience and environmental context
- training, certification, and operator enablement
- territory/public systems and utility coordination
- owner/household recurring operating admin

### 4.3 Advanced future systems to keep pressure on

- legal-grade proof and chain-of-custody
- enterprise identity and tenant governance
- BIM / 3D / geometry-native intelligence
- contributor reputation and partner network
- benchmarking and market intelligence
- building passport exchange standard
- evidence exchange contract
- multimodal grounded query
- autonomous dossier completion
- cross-modal change detection and reconstruction
- open-source accelerator pull strategy

## 5. Market, Category, and Moat Pressure

- keep the current wedge explicit:
  - evidence-backed renovation readiness
  - managers first
  - overlay above ERP
- keep the category ladder coherent:
  - evidence layer now
  - lifecycle operating system next
  - built environment infrastructure later
- keep the Europe -> Switzerland -> canton execution model explicit
- keep liability posture clean:
  - completeness / provenance / workflow
  - not automatic legal guarantee
- keep “what not to claim yet” visible when the vision expands
- keep product and market docs aligned on:
  - primary buyer
  - execution wedge
  - moat now
  - moat later
- keep a live list of which new capabilities materially strengthen:
  - demo wow
  - real moat
  - distribution pull
  - institutional trust

## 6. Demo, Sales, and Category Acceleration

- keep building killer demo sequences, not just features
- maintain the list of wow surfaces that make the product feel inevitable
- define product moments that sell themselves:
  - passport grade
  - contradiction detection
  - time machine
  - readiness wallet
  - authority-ready pack
  - post-works truth
  - trust score
- keep packaging logic evolving with the product:
  - wedge
  - operating layer
  - portfolio / institutional
- keep sales-enablement outputs visible:
  - demo scripts
  - seed scenarios
  - executive summary surfaces
  - authority / owner / contractor / lender / insurer packs

## 7. Reliability, Security, and Trust

- keep reliability and recovery layers in view, not as an afterthought
- keep observability, tracing, and operator diagnostics on the near horizon
- keep privacy/security/data governance tied to product trust, not only compliance
- identify where legal-grade trust should eventually require:
  - signed artifacts
  - access ledger
  - retention policy
  - audience-bounded sharing
- keep archive trust and export provenance in focus

## 8. OSS and Tooling Radar

- keep scanning for OSS that should be pulled instead of rebuilt
- refresh the open-source accelerator radar when major capabilities mature
- keep evaluating:
  - OCR/document understanding
  - BIM/IFC tooling
  - semantics/ontologies
  - workflow/orchestration engines
  - policy/authorization layers
  - observability stacks
  - search/retrieval stacks
  - analytics/lineage layers
- convert real OSS pull opportunities into concrete project briefs when justified

## 8.1 Dataset and Scenario Pressure

- keep the dataset layer ahead of the visible product surface
- push the repo toward a layered scenario strategy instead of one giant demo seed
- make sure new engines are not designed only against clean data
- keep demo, ops, portfolio, compliance, multimodal, and edge-case datasets visible as separate needs
- promote seed/verify/preflight work into Claude's queue before scenario debt starts blocking UI and real e2e

## 9. Structural Cleanup and Hardening

- keep looking for doc/code drift before it compounds
- keep looking for low-regret model simplifications
- keep detecting duplicated concepts across briefs and the frontier map
- keep pruning stale “future” labels once a domain becomes real
- keep the backlog huge but the active board sharp

## 10. Always-On Review Triggers

Review immediately when:

- a wave adds a new model family
- a wave adds a new service that should surface in UX
- a wave changes readiness/completeness/trust logic
- a wave introduces new packs/export/document flows
- a wave adds new standards or integration dependencies
- frontend validate/build/test counts change materially
- real e2e ownership changes
- the strategic narrative drifts from the code reality

## 11. Success Condition for This Backlog

Codex is using this backlog well if:

- Claude never outruns the strategic control plane
- the repo always shows the next meaningful direction
- quality and coherence improve while features compound
- the frontier expands without turning chaotic
- the product remains category-shaping rather than merely feature-rich

## 12. 11/10 Excellence Task List

Goal:
- turn the repo from "strong and fast-moving" into "reference-grade and reliably shippable"
- remove known quality debt while keeping productization velocity

Definition of 11/10 (all must be true):
- all local validation gates pass with zero new warnings
- test budget gate passes against an intentionally refreshed baseline
- no generated/runtime artifacts are versioned by default
- CI enforces repo gates on every PR
- top oversized source/test files are reduced or split with clear ownership
- frontend accessibility and performance budgets are both enforced, not best-effort
- security and provenance checks run by default in CI

### 12.1 P0 - Immediate Must-Fix (next 2-3 waves)

- [ ] Make current frontend validation warning-free:
  - fix hook dependency warnings in `UnknownIssuesPanel.tsx` and `ReadinessWallet.tsx`
  - remove `setState` in effect anti-patterns in `InterventionSimulator.tsx`
  - resolve React Hook Form compiler warning in `BuildingSamples.tsx`
  - validate: `cd frontend && npm run validate`
- [ ] Stabilize Playwright smoke suite (mock backend) to fully green:
  - fix strict locator ambiguity on login language buttons
  - fix completeness gauge assertions coupled to fragile text/DOM assumptions
  - fix mobile backdrop-close sidebar test pointer interception
  - validate: `cd frontend && npm run test:e2e:smoke` (2 consecutive green runs)
- [ ] Remove Playwright flakiness anti-patterns:
  - replace raw `waitForTimeout` with deterministic waits
  - reduce brittle `nth()` selector usage where semantic selectors are available
  - validate: `rg -n "waitForTimeout\\(|\\.nth\\(" frontend/e2e frontend/e2e-real -S`
- [ ] Harden real-e2e boundary checks:
  - keep preflight strict on backend identity (wrong API target must fail fast)
  - keep explicit override path (`E2E_REAL_API_BASE`, proxy target) documented
  - validate: `cd frontend && npm run test:e2e:real:preflight`
- [ ] Bring test-budget guard back to green:
  - reduce flagged growth under configured limits in `docs/test-budget-guard.json`
  - prioritize reduction of `oversized`, `large`, and `high_case_count` flags
  - validate: `npm run test:budget`
- [ ] Add CI enforcement for core gates:
  - backend lint/format/tests
  - frontend validate/tests/build
  - repo policy checks (`test:budget`, `lead:check`, `router:check`)
  - exit: required checks block merge on failure
- [ ] Stop versioning generated/runtime files by default:
  - build outputs, test artifacts, caches, local DB snapshots, temporary proof bundles
  - add guard script to fail when non-allowlisted generated artifacts appear
  - validate: clean checkout + full validate/test/build still works
- [ ] Accessibility hardening from keyboard/focus audit:
  - add skip link and `main` target id
  - ensure header dropdowns close on `Escape`
  - fix command palette tab-trap behavior and focus return on close
  - add/update deterministic tests for these flows
  - validate: `cd frontend && npm run test:e2e:smoke`

### 12.2 P1 - Structural Hardening (next 30 days)

- [ ] Split oversized backend modules:
  - especially `app/seeds/seed_data.py` and 900+ line services
  - keep domain boundaries explicit (readiness, trust, packs, ingestion)
  - exit: no service file should be a multi-domain "god module"
- [ ] Split oversized frontend pages/components:
  - `InterventionSimulator`, `AdminUsers`, `Campaigns`, `DiagnosticView`, `BuildingSamples`
  - move page orchestration vs reusable logic into hooks/components
  - exit: each page has clear composition boundaries and focused tests
- [ ] Refactor test topology for signal density:
  - replace broad assertion-heavy suites with fewer integration-focused scenarios
  - create per-domain fixture builders to reduce duplication
  - exit: lower flagged count with equal or better regression detection
- [ ] Add bundle budget enforcement:
  - hard threshold for main entry chunk and total precache size
  - fail CI on unapproved regressions
  - validate: `cd frontend && npm run build`
- [ ] Add dependency and vulnerability gating:
  - JS and Python dependency audits in CI
  - lock update cadence with explicit changelog notes for risky upgrades
  - exit: no known high-severity vulns in default branch dependencies

### 12.3 P2 - Productization Excellence (next 60 days)

- [ ] Add real integration confidence lane:
  - deterministic `test:e2e:real` environment profile
  - preflight contract checks for backend target, seed state, and required services
  - exit: one stable golden path real-e2e always green on main
- [ ] Strengthen observability and recovery:
  - request correlation IDs across API + frontend
  - failure taxonomy and top-level operator runbook
  - minimal SLO/error-budget dashboard for critical flows
- [ ] Tighten provenance and trust chain:
  - explicit provenance metadata coverage checks for exports and packs
  - immutable audit-log expectations for state-changing workflows
  - exit: trust-critical flows are test-covered end-to-end
- [ ] Add architecture decision discipline:
  - ADR log for major model/service boundary decisions
  - explicit "implemented vs reserved" matrix refreshed monthly
  - exit: architecture docs stay truth-aligned with code

### 12.4 Program-Level Execution Tasks

- [ ] Convert each P0/P1 cluster into compact wave briefs under `docs/waves/`
- [ ] Keep `Next 10 Actions` mapped to this section until all P0 items are closed
- [ ] Require post-wave debrief fields (`clear`, `fuzzy`, `missing`) to update this list
- [ ] Refresh test-budget baseline only after structural reductions, not before
- [ ] Re-rate project/repo after each completed cluster with the same rubric
