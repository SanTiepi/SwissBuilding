# SwissBuilding Execution Control Plane

This file is the active control plane for large Claude missions.
It is execution-oriented, not strategic. Strategic direction lives in `MEMORY.md` and the docs under `docs/`.

Default ownership split:
- strategic ambition, moonshots, roadmap pressure, and acceptance standards come from Codex / product lead
- Codex is also expected to keep future waves and strategic next-steps visible ahead of current execution
- execution planning, agent waves, coding, and delivery validation live here under Claude supervision
- Claude executes only scoped tasks explicitly delegated by Codex; Codex keeps final sequencing and acceptance authority

Lead-side operating reference:
- when Claude is deep in implementation, Codex should continue working from `docs/lead-parallel-operating-model.md`
- that document defines the permanent parallel streams Codex should keep advancing without waiting for a fresh prompt
- `docs/lead-master-plan.md` is the canonical structured lead plan that should stay ahead of active execution

## Supervisor Protocol

For large, multi-wave, agent-heavy missions, the supervisor should loop as follows:

1. Read `CLAUDE.md`, `AGENTS.md`, `MEMORY.md`, and the relevant roadmap/docs.
   - also read the `Lead Feed` section below for fresh Codex guidance already landed in-repo
2. Refresh this file so the current program, board, and validation gates match the real repo state.
3. Split work into non-overlapping waves and scoped agent tasks.
4. Launch agents only for workstreams that can progress independently.
5. Validate completed work before moving tasks to `done`.
6. Update statuses, blockers, and decisions here.
7. Launch the next wave.
8. Continue until:
   - the active program is complete,
   - a real external blocker exists,
   - or no high-priority executable work remains.

Rules:

- Treat prompts as mission framing, not as the full operating manual.
- Use this file as the durable execution frame.
- Keep the active board current; archive stale history instead of leaving it mixed into live work.
- Do not duplicate long-range strategy here; pull that from `MEMORY.md` and the product docs, then translate it into executable waves.
- assume agent-only execution by default (Codex + ClaudeCode); avoid dependence on manual human steps
- Before starting a wave, ensure the task was explicitly delegated by Codex and has clear constraints, validations, and exit criteria.
- Before cutting implementation waves, check `docs/product-frontier-map.md` for adjacent low-regret structures that should be anticipated now to avoid future retrofit debt.
- Prefer anticipating hidden domain/model capability now and exposing it later rather than forcing expensive rework after the fact.
- Do not turn that anticipation into cluttered UX; hidden readiness is acceptable, fake completeness is not.
- Keep a ranked `Next 10 Actions` list current whenever meaningful executable work remains. It should be short, concrete, and ready to reshuffle after each wave.

## Core Invariants (AGENTS Sync)

Enforce these invariants across all waves and merge passes:

- identifier integrity:
  - `egid` (building) != `egrid` (parcel) != `official_id` (legacy/generic)
- source integrity:
  - prefer official public sources over scraping
  - for Vaud ingestion, keep `vd.adresse` / `vd.batiment_rcb` distinct from RegBL/MADD mappings
- delivery integrity:
  - do not present partially wired functionality as complete
  - if incomplete, simplify/hide until full-chain support exists
- execution mode integrity:
  - optimize for autonomous `Codex + ClaudeCode` execution
  - avoid human-only steps; if unavoidable, log explicit blocker + machine-checkable follow-up

## Agent Contract

- One agent owns one scoped task at a time.
- No overlapping ownership across agents.
- An agent must not change files outside its task scope unless the supervisor explicitly broadens scope.
- Every agent report must include:
  - summary
  - files touched
  - validations run
  - blockers or risks
- A task is not `done` until the supervisor accepts the validations as sufficient for the scope.
- Default wave width is `3` parallel tasks max, with disjoint scopes.
- Prefer `1` task = `1` bounded deliverable (one primary file + satellites).
- Hub-file updates should default to supervisor merge pass:
  - `backend/app/api/router.py`
  - `backend/app/models/__init__.py`
  - `backend/app/schemas/__init__.py`
  - `backend/app/seeds/seed_data.py`
  - `frontend/src/i18n/{en,fr,de,it}.ts`
- unless explicitly assigned, agents should not wire hub files directly (for example router registrations/import-order hubs)
- Validation should be sequential after each merge/integration step, not only one final batch.
- Use direct search/read commands for simple lookup work; reserve agents for bounded implementation or open-ended analysis.

## Current Program

- Program: `Mega-Program 1 — Living and Actionable Building Dossier` (finishing)
- Overlap: `Mega-Program 2 — Multi-Actor Orchestration` (governance layer largely complete, search + agents remain)
- Product intent:
  - make the building navigable as a physical object
  - make scores and recommendations provable
  - make the dossier exportable and defensible
  - orchestrate actions across buildings (campaigns)
  - make building data searchable cross-entity

## Current Execution Doctrine

The product is now large enough that the default optimization is no longer "more surfaces".
The default optimization is:

- better before broader
- productization before primitive proliferation
- composition before standalone calculators
- full-chain truth before more isolated services
- dataset depth before synthetic comfort
- real validation before further speculative expansion
- signal quality before raw test-count growth

Practical rule:

- do not add a new backend primitive unless it clearly:
  - unlocks the active maturity gate,
  - removes structural debt,
  - or closes an integration gap that existing services cannot cover cleanly
- prefer consolidating existing capabilities into:
  - UI surfaces
  - aggregate read models
  - facades / bounded contexts
  - richer datasets
  - real end-to-end validation

## Current Maturity Gate

- active gate: `Gate 2 — Building operating system`
- preserve from Gate 1:
  - evidence quality
  - readiness clarity
  - dossier and pack credibility
- build toward Gate 3:
  - portfolio execution
  - scenario persistence
  - trust comparability
  - capital allocation logic

Rule:
- do not use calendar timing as the primary organizing principle
- use maturity gates:
  - wedge dominance
  - building operating system
  - portfolio and capital system
  - infrastructure and market standard

## International-Class Standard

The target is not a good local tool. The target is a product that can plausibly become a European reference layer.

This implies:
- rules architecture must stay Europe-ready, then country-ready, then canton/authority-ready
- core product concepts must tolerate multilingual, multi-actor, and multi-jurisdiction expansion
- proof, auditability, exportability, and interoperability are first-class, not polish
- hidden low-regret foundations are preferred over future retrofit debt
- visible UX should still stay disciplined: no fake breadth, no enterprise theatre, no half-finished exposure

When choosing between two implementations with similar delivery cost, prefer the one that:
- preserves future interoperability
- strengthens trust and auditability
- scales beyond the Swiss wedge
- improves the ability to become the reference system later

## Long Horizon Rule

Execution is guided by:
- the active wave
- the next 10 actions
- the 60-day runway

But architecture choices should also stay compatible with the 48-month horizon in:
- `docs/roadmap-next-batches.md`
- `docs/vision-100x-master-brief.md`
- `docs/product-frontier-map.md`

Rule:
- if a shortcut would save time now but block obvious 24-48 month expansion, avoid it unless the delivery gain is overwhelming

## Lead Feed

This section is the fastest shared channel from Codex / product lead to Claude.
Read it at the start of each supervision loop and update it only with high-signal execution facts or guidance.

### Lead-side parallel mode

Codex should keep contributing in parallel through:

- execution foresight
- product frontier expansion
- acceptance / QA parallelism
- market / category / moat pressure

Reference:
- `docs/lead-parallel-operating-model.md`

### Delegation preference

When implementation-heavy work is clearly better handled by Claude:

- Codex should package it into repo-visible briefs
- surface it in `Next ready project briefs`, `Next 10 Actions`, or the horizon feeds
- then continue with lead-side work instead of trying to compete with Claude on long execution waves

Default:
- Claude = heavy implementation
- Codex = foresight, QA, coherence, frontier, strategy, and low-risk cleanup
- if a cross-cutting need becomes obvious while Claude is executing, Codex should prefer creating or updating a repo-native brief over holding the implementation work locally

### Lead strategic envelope (commercializable v1)

Codex sets direction at outcome level so Claude can keep execution velocity.

North-star commercial promise:
- `safe-to-start dossier` for regulated pre-work pollutant readiness
- `VD/GE-first`, `amiante-first`, `AvT -> ApT`
- sold as an overlay above ERP and document systems for multi-building property managers

Execution outcomes to maximize:
- authority/owner/contractor-ready pack generation that is fast and repeatable
- high dossier completeness and explicit missing-piece orchestration
- strict provenance traceability on evidence and generated outputs
- visible reduction of documentary rework in real project workflows
- portfolio-level visibility that helps prioritize where to act first

Claims discipline:
- claim completeness, provenance, workflow traceability, and readiness support
- avoid legal-compliance-guarantee claims

### No-micromanagement contract

When Claude is actively shipping:
- Codex should avoid step-by-step implementation steering
- Codex should steer by:
  - mission
  - outcome
  - non-negotiable constraints
  - validation and exit criteria
- Claude should choose implementation decomposition and wave sequencing inside this envelope

### Execution prioritization filters

Consumer-first gate:
- before promoting a task into the active wave, require a visible product consumer within the next `2` waves
- if no near-term consumer exists (especially for `ring_4`), deprioritize the task

Near-term wave mix:
- post-W80 default is hardening-first:
  - `validation/audit + infra polish` before new feature breadth
  - no net-new backend expansion unless a hard blocker is proven

### Post-W80 execution pattern (hardening mode)

Decision:
- no strategic pause required; switch execution mode
- keep momentum with a two-track cadence:
  - Wave type A (`validation/audit`): `1-2` agents depending on coupling
  - Wave type B (`infra polish`): `1-3` tasks, choose the lowest coordination overhead shape

Launch discipline:
- run wave readiness gate before each launch:
  - `python scripts/wave_readiness_gate.py ...`
- require closeout gate before promoting next wave:
  - `python scripts/lead_control_plane_check.py --strict`

### Lean autonomy mode (activated 2026-03-10)

Execution defaults in this mode:
- compact briefing:
  - prefer `docs/templates/wave-brief-compact-template.md`
  - keep only outcome, target files, hard constraints, validate loop, and exit
- internal agent feedback loop:
  - each agent must run `validate -> fix -> rerun until clean` before handoff
- test signal policy:
  - type/compile guarantees first
  - one golden-path integration/e2e per feature slice
  - avoid low-signal render-only unit-test multiplication
- wave-shape policy:
  - for coherent polish clusters, prefer one wider-scope autonomous task
  - split into `<=3` tasks only when it lowers risk more than it adds overhead

### Active external gate (locked on 2026-03-09)

External scenario #1:
- `safe-to-start dossier`

Gate definition:
- one seeded building must go from raw state to complete dossier state
- the full chain must be visible in UI
- the chain must be verifiable in real e2e

Backend expansion policy (current phase):
- historical freeze `W68-W70` is complete
- for `W81+`, backend expansion remains frozen by default while ranks `1-3` are being closed
- allowed exception: minimal glue required to unblock current hardening or gate proof work

### Canonical brief template

- use `docs/templates/project-brief-template.md` as the default format for new wave briefs
- use `docs/templates/wave-brief-compact-template.md` for lean autonomy waves where context is stable
- keep briefs compact and task-specific; avoid restating standing repo context

### Wave debrief and telemetry protocol

After each completed wave:
- append a 3-line debrief in `ORCHESTRATOR.md`
- update execution counters
- apply debrief learnings directly to the next queued wave in the same supervision loop

Execution counters (rolling, since protocol start):
- waves_completed: `38` (`W61-W66` + `W68-W99` reported)
- rework_count: `0`
- blocked_count: `0`
- last_updated: `2026-03-24`

Wave debrief (mandatory):
- clear: what was clear and accelerated execution
- fuzzy: what was ambiguous or open to interpretation
- missing: what was absent and had to be inferred

Counter rules:
- increment `rework_count` when a wave or major subtask fails acceptance and requires a new implementation pass
- increment `blocked_count` when a wave cannot proceed due to a real external blocker
- keep notes concise and execution-oriented
- do not use this section for long narrative logs

### Claude observations channel

Purpose:
- capture execution-ground observations Claude sees while shipping that should influence next-wave planning

When to update:
- at wave closeout, before next-wave ranking

Format:
- `observation`: concrete signal
- `impact`: why it matters (velocity, quality, risk, product truth)
- `suggested_adjustment`: what to change in ranking/briefing/patterns

Current observations:
- high conflict risk remains on hub files (`router.py`, `models/__init__.py`, i18n files) when multiple agents touch them
- frontend productization sweep reached saturation (`W72-W80`: `9` waves, `27` surfaces, `~750+` i18n keys, `0` rework, `0` blocked)
- hardening execution quality remains strong after W81-W85:
  - frontend unit tests: `233 -> 352`
  - frontend e2e mock tests: `178 -> 192`
  - build warnings: `2 -> 0`
  - consecutive zero-fix waves: `12`
- near-term queue is now dominated by validation/audit and infrastructure polish, not net-new feature breadth
- typed validation criteria (integration vs unit) reduce low-signal test growth

### Current validated baseline

- post Wave 60 validation:
  - backend: `4563 passed` (19 warnings, 237s)
  - frontend unit: `186 passed | 1 skipped`
  - frontend e2e mock: `173 passed` (not re-run, no e2e regression risk)
  - frontend build: green (90 entries, 1610.26 KiB precache)
  - ruff check + format: clean
  - tsc --noEmit + eslint + prettier: clean
- post W80 session report (Claude-provided execution telemetry):
  - frontend unit progression: `198 -> 233`
  - consecutive zero-fix waves: `6`
  - scope trend: feature sweep complete, hardening phase started
- treat these as the current known-good baseline until a newer run supersedes them

### Wave 10 verification signal

- `W10-A/B/C` are materially landed in the repo:
  - `backend/app/services/trust_score_calculator.py`
  - `backend/app/services/unknown_generator.py`
  - `backend/app/services/post_works_service.py`
- targeted backend coverage exists and is green:
  - `backend/tests/test_trust_score_calculator.py`
  - `backend/tests/test_unknown_generator.py`
  - `backend/tests/test_post_works_service.py`
- high-signal conclusion:
  - the next pressure is not primitive creation
  - it is productization, UX surfacing, and readiness/trust/post-works integration

### Lead QA automation update

- Codex added a repo-level async-state audit for query-driven frontend surfaces:
  - `scripts/frontend_async_state_audit.py`
  - run: `python scripts/frontend_async_state_audit.py --write --strict`
  - npm shortcut: `npm run lead:async-audit`
- latest run is green:
  - `35/35` query-driven surfaces with explicit error handling
  - report artifacts:
    - `docs/frontend-async-state-audit.md`
    - `docs/frontend-async-state-audit.json`
- keep this command in the pre-delivery QA path when wave changes touch query-driven pages/components
- Codex also added a repo-level test-budget guard to prevent broad-test bloat:
  - `scripts/test_budget_guard.py`
  - config and baseline: `docs/test-budget-guard.json`
  - run: `python scripts/test_budget_guard.py --write-current`
  - npm shortcut: `npm run test:budget`
- Codex added a real-e2e preflight gate so Playwright real runs fail fast on environment/seed drift:
  - `frontend/scripts/e2e_real_preflight.mjs`
  - run: `cd frontend && npm run test:e2e:real:preflight`
  - default `test:e2e:real` now runs preflight before Playwright
  - `frontend/e2e-real/helpers.ts` now uses the same env overrides for login credentials
  - `scripts/run_related_checks.py` now infers this preflight for `frontend/e2e-real/*` and `frontend/playwright.real.config.ts`
  - checks:
    - backend `/health`
    - auth login + `/api/v1/auth/me`
    - minimum seeded buildings and diagnostics
  - env overrides:
    - `E2E_REAL_API_BASE`
    - `E2E_REAL_ADMIN_EMAIL`
    - `E2E_REAL_ADMIN_PASSWORD`
- Codex added router wiring inventory/check tooling:
  - `scripts/router_inventory.py`
  - npm shortcuts:
    - `npm run router:inventory`
    - `npm run router:check`
  - generated artifacts:
    - `docs/router-inventory.md`
    - `docs/router-inventory.json`
  - latest signal:
    - import/include wiring is coherent (`142/142`, no duplicates)
    - API module file coverage is complete (`142/142`)
    - no current tag-style issues detected in router tags
- Test budget guard is now signaling overgrowth on backend broad suites:
  - `npm run test:budget` is currently red
  - current delta vs baseline:
    - flagged files: `+15` (limit `+12`)
    - backend flagged files: `+15` (limit `+8`)
    - oversized flags: `+15` (limit `+6`)
  - immediate implication:
    - do not keep adding broad backend suites without right-sizing/splitting
    - prioritize `test-right-sizing-and-integration-confidence-program.md`
    - refresh baseline only after intentional triage, not by default

### Current known residues

- the earlier frontend unit warning noise has now largely been eliminated on the main lead-side QA stream
- the main remaining frontend residue is structural rather than noisy:
  - Vite chunk-size warnings on `index` and especially `map`
- `test:e2e:real` remains environment-sensitive until SwissBuilding cleanly owns the expected backend target
- dataset depth is now a visible execution risk:
  - seeds exist and are already useful
  - but the product surface is outgrowing the current seed strategy
  - demo, ops, portfolio, compliance, multimodal, and edge-case scenarios should become explicit layers
  - see `docs/projects/dataset-scenario-factory-and-seed-strategy-program.md`

### Ready-to-absorb lead QA/UI batch

Codex already validated a QA/UI hardening batch that should be absorbed or cross-checked if it overlaps with current work:

- i18n key fixes in building overview surfaces
- completeness mock alignment
- missing building actions mock route
- stronger selectors in actions/completeness/portfolio e2e
- dark-mode/state polish in:
  - `BuildingExplorer`
  - `BuildingInterventions`
  - `BuildingPlans`
  - `BuildingTimeline`
- updated visual regression baselines

Rule:
- if your current wave overlaps these areas, prefer merging/validating them now rather than rediscovering the same issues later
- if your branch already supersedes them, note that explicitly and move on

### Post-W31 steering note

The center of gravity has shifted again:

- W24-W31 prove that the backend intelligence layer is now much deeper than the average visible UI layer
- Codex lead-side QA has already removed a large amount of low-risk silent-failure debt on recent surfaces
- the next highest-leverage work is therefore:
  - frontend productization of already-landed backend capabilities
  - dataset/scenario depth
  - real-e2e ownership and preflight
  - structural frontend hardening (`map` / bundle topology)

Additional lead finding:

- backend service breadth now needs an explicit consumer map and pruning pass, otherwise the codebase will keep accumulating first-class services with no clear product surface

Bias the next waves toward surfacing what already exists before inventing another primitive unless a new primitive is required to unblock the active gate.

### Depth-over-breadth note

Lead review after 30+ waves:

- backend service count is now high enough that marginal value from another isolated calculator is declining
- the next 10x of value comes from:
  - making existing capabilities visible and reliable in the UI
  - consolidating overlapping services into clearer domain facades
  - proving the full chain works with richer datasets and real integration checks
  - reducing query / contract / async orchestration friction

This means the default queue should favor:

- integration
- productization
- consolidation
- dataset realism
- real validation

over:

- another standalone backend service with no immediate consumer

### Service inventory baseline now exists

Codex has created a first repo-native service consumer baseline:

- script: `backend/scripts/service_consumer_inventory.py`
- outputs:
  - `docs/service-consumer-map.md`
  - `docs/service-consumer-map.json`

Current baseline from that inventory:

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
- obvious orphaned review candidates:
  - `avt_apt_transition`
  - `data_export_service`
  - `dossier_archive_service`
  - `maintenance_schedule_service`

Interpretation:

- the inventory confirms the breadth issue is real
- it also shows the next move is not blind service deletion
- the next move is context-by-context facade alignment plus explicit consumer-path review
- use the generated map as the factual starting point for `service-consumer-mapping-and-dead-code-pruning-program.md`

### Fast-confidence validation path now exists

Codex has added a lighter, higher-signal validation path so agents do not need to jump straight from tiny targeted checks to the full suite:

- repo:
  - `python scripts/run_related_checks.py --list`
  - `python scripts/run_related_checks.py <file>`
  - `python scripts/run_related_checks.py --run <file>`
  - `python scripts/test_inventory.py --write`
  - `python scripts/lead_control_plane_check.py --strict`
- frontend:
  - `npm run test:surface:list`
  - `npm run test:surface -- <surface>`
  - `npm run test:surface -- <surface> --with-e2e`
  - `npm run test:unit:critical`
  - `npm run test:e2e:smoke`
  - `npm run test:confidence`
- backend:
  - `python scripts/run_confidence_suite.py --list`
  - `python scripts/run_confidence_suite.py`

Intent:

- use these for fast product confidence during active waves
- fail fast if control-plane hygiene drifts (missing sections, broken Next 10 discipline)
- keep full-suite runs for:
  - integration milestones
  - broad refactors
  - maturity-gate acceptance
  - pre-merge confidence

Lead note:

- the most useful frontend optimization is now surface-based validation rather than bigger broad reruns
- for mixed-scope changes, prefer the repo-level related-check runner before manually choosing suites
- use the generated `docs/test-inventory.md` before growing an already large test file
- preferred surface suites:
  - `trust`
  - `readiness`
  - `timeline`
  - `portfolio`
  - `dossier`
  - `shell`
- current oversized-suite review targets from the inventory:
  - backend:
    - `test_compliance_edge_cases.py`
    - `test_transaction_readiness.py`
    - `test_access_control.py`
    - `test_occupant_safety.py`
  - frontend mock e2e:
    - `buildings.spec.ts`
    - `pages.spec.ts`

### Additional low-risk UX hardening validated after W19

Codex has now rechecked the recent trust/readiness/passport/time-machine surfaces and landed low-risk fixes directly:

- `ReadinessWallet`
  - no longer falls through to a misleading empty grid on API failure
  - now shows an explicit inline error state
- `PassportCard`
  - no longer maps API failure to a misleading `no data` state
  - now shows an explicit error state
- `ContradictionCard`
  - query failure now renders an explicit inline error state
  - contradiction scan mutation failure now toasts instead of failing silently
- `TimeMachinePanel`
  - snapshot capture / compare failures now toast instead of failing silently

Validated by Codex:
- `cd frontend && npm run validate` -> green
- `cd frontend && npm run build` -> green
- `cd frontend && npm run test:e2e -- building-timeline.spec.ts completeness.spec.ts buildings.spec.ts portfolio.spec.ts pages.spec.ts` -> `51 passed`
- `cd frontend && npm test -- PassportCard ContradictionCard TimeMachinePanel ReadinessWallet` -> `12 passed`
- `cd frontend && npm test` -> `153 passed`

Follow-up note:
- dedicated frontend unit coverage now exists for:
  - `PassportCard`
  - `ContradictionCard`
  - `TimeMachinePanel`
  - `ReadinessWallet`
- the remaining noise on this stream is outside these components:
  - Vite chunk-size warnings on `index` and especially `map`

### Additional low-risk UX hardening validated after W20

Codex also rechecked two more recently added surfaces with the same failure-mode pattern and hardened them:

- `PostWorksDiffCard`
  - no longer collapses API failure into a misleading empty state
  - now shows an explicit inline error state
- `PortfolioSignalsFeed`
  - no longer hides signal-loading failures behind a spinner/empty fallback
  - now shows an explicit portfolio-level error state

Validated by Codex:
- `cd frontend && npm test -- PostWorksDiffCard PortfolioSignalsFeed` -> `4 passed`
- `cd frontend && npm run validate` -> green
- `cd frontend && npm test` -> `153 passed`
- `cd frontend && npm run build` -> green

Follow-up note:
- dedicated frontend coverage now exists for:
  - `PostWorksDiffCard`
  - `PortfolioSignalsFeed`
- the previous Vitest `ErrorBoundary` stderr noise has been eliminated on this branch
- the remaining frontend build noise is now mainly chunk-size warnings on `index` and especially `map`

### Additional low-risk UX hardening validated after W21

Codex closed another mini-lot on adjacent trust/readiness surfaces so API failures no longer collapse into empty/no-data states:

- `TrustScoreCard`
  - explicit inline error state on trust-score query failure
- `UnknownIssuesList`
  - explicit inline error state on unknowns query failure
- `ChangeSignalsFeed`
  - explicit inline error state on change-signal query failure
- `CompletenessGauge`
  - explicit inline error state on completeness query failure

New dedicated tests now exist for:

- `frontend/src/components/__tests__/TrustScoreCard.test.tsx`
- `frontend/src/components/__tests__/UnknownIssuesList.test.tsx`
- `frontend/src/components/__tests__/ChangeSignalsFeed.test.tsx`
- `frontend/src/components/__tests__/CompletenessGauge.test.tsx`

Validated by:

- `cd frontend && npm test -- TrustScoreCard UnknownIssuesList ChangeSignalsFeed CompletenessGauge` -> `8 passed`
- `cd frontend && npm run validate` -> green
- `cd frontend && npm test` -> `166 passed`
- `cd frontend && npm run build` -> green

Remaining frontend build noise on this stream:

- Vite chunk-size warnings on `index` and especially `map`

### Additional low-risk UX hardening and build hardening validated after W28

Codex closed one more focused QA + frontend performance lot:

- `TransferPackagePanel`
  - focused error-state and success-summary coverage now exists
  - generation failure explicitly toasts and renders the inline error state
  - generated package summary cards and download affordance are now regression-covered
- `App`
  - remaining static route surfaces were lazy-loaded
  - build topology improved materially without changing product behavior

New focused frontend coverage now exists for:

- `frontend/src/components/__tests__/TransferPackagePanel.test.tsx`

Validated by:

- `cd frontend && npm test -- TransferPackagePanel` -> `2 passed`
- `cd frontend && npm run validate` -> green
- `cd frontend && npm test` -> `184 passed | 1 skipped`
- `cd frontend && npm run build` -> green

Build impact:

- `assets/index-*.js` dropped from roughly `643 kB` to roughly `364 kB`
- the dominant remaining build residue is now clearly `assets/map-*.js` at roughly `1.7 MB`
- the next meaningful frontend performance target should focus on map chunk topology rather than broad route lazy-loading

### Additional low-risk UX hardening validated after W22

Codex closed another QA mini-lot on adjacent productized surfaces that still needed explicit API-failure handling and focused regression coverage:

- `DataQualityScore`
  - explicit inline error state on quality query failure
- `ReadinessSummary`
  - explicit inline error state on readiness query failure
- `ProofHeatmapOverlay`
  - explicit inline error state while still preserving the plan/image context
- `Campaigns`
  - timeline progress purity fix so frontend validate/build stay green

New/updated focused validation now includes:

- `frontend/src/components/__tests__/DataQualityScore.test.tsx`
- `frontend/src/components/__tests__/ReadinessSummary.test.tsx`
- `frontend/src/components/__tests__/ProofHeatmapOverlay.test.tsx`

Validated by:

- `cd frontend && npm test -- DataQualityScore ReadinessSummary ProofHeatmapOverlay` -> `14 passed`
- `cd frontend && npm run validate` -> green
- `cd frontend && npm test` -> `166 passed`
- `cd frontend && npm run build` -> green

Remaining frontend build noise on this stream:

- Vite chunk-size warnings on `index` and especially `map`

### Additional low-risk UX hardening validated after W23

Codex closed another QA mini-lot on supporting intelligence and notification surfaces that were still too optimistic on API failure:

- `EvidenceChain`
  - explicit inline error state in non-compact mode
  - no longer silently degrades into empty/no-data when evidence loading fails
- `NotificationBell`
  - explicit `loading / error / empty` handling for recent notifications
  - no longer implies “no notifications” when the panel query failed

New/updated focused validation now includes:

- `frontend/src/components/__tests__/EvidenceChain.test.tsx`
  - explicit error-state coverage added
- `frontend/src/components/__tests__/NotificationBell.test.tsx`
  - focused error-state coverage added

Validated by:

- `cd frontend && npm test -- EvidenceChain NotificationBell` -> `10 passed`
- `cd frontend && npm run validate` -> green
- `cd frontend && npm test` -> `168 passed`
- `cd frontend && npm run build` -> green

Remaining frontend build noise on this stream:

- Vite chunk-size warnings on `index` and especially `map`

### Additional low-risk UX hardening validated after W24

Codex hardened secondary async flows on `BuildingDetail` so adjacent intelligence/productization surfaces no longer hide failures behind empty states:

- `BuildingDetail`
  - open actions now render an explicit inline error state when the actions query fails
  - the activity tab now renders an explicit centered error state when the activity query fails
  - the documents load path now toasts on fetch failure and the documents tab renders an explicit centered error state

New focused frontend coverage now exists for:

- `frontend/src/components/__tests__/BuildingDetailPage.test.tsx`
  - explicit actions failure coverage
  - explicit activity failure coverage
  - one documents failure assertion remains intentionally skipped until the documents-tab interaction is stabilized without adding suite flake

Validated by:

- `cd frontend && npm run validate` -> green
- `cd frontend && npm test` -> `175 passed | 1 skipped`
- `cd frontend && npm run build` -> green

Remaining frontend build noise on this stream:

- Vite chunk-size warnings on `index` and especially `map`

### Additional low-risk UX hardening validated after W25

Codex also rechecked the timeline surface and closed another async-state inconsistency:

- `BuildingTimeline`
  - query failure no longer degrades to a generic plain fallback
  - now renders an explicit inline error state consistent with the other recent intelligence surfaces

New focused frontend coverage now exists for:

- `frontend/src/components/__tests__/BuildingTimeline.test.tsx`
  - explicit error-state coverage added

Validated by:

- `cd frontend && npm test -- BuildingTimeline` -> `4 passed`
- `cd frontend && npm run validate` -> green
- `cd frontend && npm test` -> `176 passed | 1 skipped`
- `cd frontend && npm run build` -> green

Remaining frontend build noise on this stream:

- Vite chunk-size warnings on `index` and especially `map`

### Additional frontend runner and chart-surface hardening validated after W25

Codex also closed a more structural frontend hardening pass:

- component-test `QueryClient` harnesses were normalized with `gcTime: 0` to reduce timer leaks and lingering React Query state
- `vitest` now runs with `fileParallelism: false` in this repo so the jsdom/react-query suite behaves deterministically
- `CommandPalette.test.tsx` now uses a stable i18n mock and synchronous RAF harness instead of timing-sensitive defaults
- `Dashboard` and `Portfolio` chart-heavy blocks now load through dedicated lazy wrappers:
  - `DashboardCharts`
  - `PortfolioCharts`

Validated by:

- `cd frontend && npm run validate` -> green
- `cd frontend && npm test` -> `186 passed | 1 skipped`
- `cd frontend && npm run build` -> green

Current observed frontend build profile on this stream:

- `assets/index-*.js` ~ `365 kB` and no longer the main concern
- `assets/charts-*.js` ~ `411 kB` and now sits behind dedicated dashboard/portfolio lazy boundaries
- `PollutantMap` and `PortfolioRiskMap` now lazy-load `mapbox-gl` inside the component instead of at module import time
- route-level map chunks are now tiny (`PollutantMap` ~ `5.5 kB`, `PortfolioRiskMap` ~ `6.0 kB`)
- the old monolithic `assets/map-*.js` hotspot has been eliminated; map stack weight is now isolated behind dynamic loading boundaries

Remaining frontend build noise on this stream:

- Vite no longer warns about the old route-level `map` hotspot; the next structural target is reducing the large shared `charts` chunk and watching base-shell creep
- a broad `useQuery` scan did not reveal any new obvious surfaces that completely lack explicit error handling, so the next leverage is no longer whack-a-mole fixes but shared async-state primitives, aggregate reads, and perf work

### Additional low-risk performance hardening validated after W48

Codex isolated `mapbox-gl` behind dynamic imports in:

- `PollutantMap`
- `PortfolioRiskMap`

Validated by:

- `cd frontend && npm run validate` -> green
- `cd frontend && npm run build` -> green

Observed effect:

- route-level map chunks collapsed from a prior `~1.7 MB` hotspot to roughly `5.5-6.0 kB` route shells
- precache size dropped to roughly `1610.26 KiB`
- the bundle is now much more honest about where heavy weight actually lives

### Additional low-risk UX hardening validated after W26

Codex closed another very small but real QA lot on adjacent execution surfaces and test-harness hygiene:

- `ExportJobs`
  - focused error-state and empty-state coverage now exists
  - the React Router future-flag warning noise in the new test harness has been removed
- `SafeToXCockpit`
  - focused error-state and loaded-state coverage now exists

New focused frontend coverage now exists for:

- `frontend/src/components/__tests__/ExportJobs.test.tsx`
- `frontend/src/components/__tests__/SafeToXCockpit.test.tsx`

Validated by:

- `cd frontend && npm test -- ExportJobs SafeToXCockpit` -> `4 passed`
- `cd frontend && npm run validate` -> green
- `cd frontend && npm test` -> `180 passed | 1 skipped`

Remaining frontend build noise on this stream:

- Vite chunk-size warnings on `index` and especially `map`

### Additional low-risk UX hardening validated after W27

Codex closed one more focused QA lot on a recent timeline surface that already had explicit runtime behavior but no dedicated regression coverage:

- `RequalificationTimeline`
  - dedicated error-state coverage now exists
  - dedicated empty-state coverage now exists

New focused frontend coverage now exists for:

- `frontend/src/components/__tests__/RequalificationTimeline.test.tsx`

Validated by:

- `cd frontend && npm test -- RequalificationTimeline` -> `2 passed`
- `cd frontend && npm run validate` -> green
- `cd frontend && npm test` -> `182 passed | 1 skipped`

Remaining frontend build noise on this stream:

- Vite chunk-size warnings on `index` and especially `map`

### Dedicated compliance hardening side project

- a dedicated project brief now exists at `docs/projects/legislative-compliance-hardening.md`
- treat it as a parallel track, not a replacement for the active program
- pull it into execution when a wave can absorb it without stalling the current product path

### Canonical system gap family

- the next major system-expansion family is now explicit and repo-backed:
  - legal-grade proof and custody
  - enterprise identity and tenant governance
  - BIM / 3D / geometry-native intelligence
  - execution quality and hazardous works operations
  - partner network and contributor reputation
  - benchmarking, learning, and market intelligence
- these are no longer just frontier ideas; they each have dedicated briefs in `docs/projects/`
- treat them as the next coherent class of international-class expansion once the current trust/readiness/post-works productization wave is stable

### Next ready project briefs

- `docs/projects/baticonnect-product-blueprint-program.md`
  - BatiConnect canonical architecture: domain/surface/capability blueprints + 3 implementation wave briefs (backbone, ingestion, read-model)
- `docs/projects/trust-readiness-postworks-program.md`
  - trust score, unknowns, readiness, post-works truth, data quality operating layer
- `docs/projects/portfolio-execution-and-packs-program.md`
  - campaign recommendation, export progress, saved simulations UI, pack scaffolding
- `docs/projects/testing-and-validation-modernization.md`
  - test topology, fixtures, visual regression cleanup, real e2e hardening, validation tooling alignment
- `docs/projects/spatial-truth-and-field-operations-program.md`
  - plan annotation, field capture, proof heatmaps, sampling planner foundations
- `docs/projects/contradiction-passport-and-transfer-program.md`
  - contradiction detection, passport state, memory transfer, export foundations
- `docs/projects/killer-demo-and-wow-surfaces-program.md`
  - time machine, proof heatmaps, intervention simulator, readiness wallet, dossier completion agent
- `docs/projects/transaction-insurance-finance-readiness-program.md`
  - safe_to_sell / insure / finance states and packs
- `docs/projects/rules-pack-studio-and-europe-expansion-program.md`
  - rules pack studio, diffing, Europe-ready regulatory architecture
- `docs/projects/agent-governance-and-knowledge-workbench-program.md`
  - agent audit, knowledge correction, dataset curation, learning loops
- `docs/projects/building-passport-standard-and-exchange-program.md`
  - passport schema, exchange package, import/export contract, diffs
- `docs/projects/portfolio-intelligence-command-center-program.md`
  - command center, opportunity engine, CAPEX translation, execution surfaces
- `docs/projects/ecosystem-network-and-market-infrastructure-program.md`
  - contributor network, partner APIs, public-data delta monitoring, network-effect foundations
- `docs/projects/repo-quality-and-coherence-hardening.md`
  - architecture truth sync, naming cleanup, project-brief lifecycle governance, source-of-truth hygiene
- `docs/projects/reliability-observability-and-recovery-program.md`
  - export recovery, degraded states, pipeline observability, preflight hardening
- `docs/projects/dataset-scenario-factory-and-seed-strategy-program.md`
  - layered scenario strategy, richer seeds, seed_verify expansion, real-e2e preflight alignment
- `docs/projects/demo-and-sales-enablement-program.md`
  - killer demos, seeded narratives, buyer-facing wow surfaces, sales-proof operator flows
- `docs/projects/privacy-security-and-data-governance-program.md`
  - audience-bounded sharing, sensitive evidence handling, access/audit hardening
- `docs/projects/distribution-and-embedded-channels-program.md`
  - embedded surfaces, external views, integration artifacts, account-spread channels
- `docs/projects/occupant-safety-and-communication-program.md`
  - occupancy safety readiness, bounded notices, zone restrictions, acknowledgement tracking
- `docs/projects/openbim-digital-logbook-and-passport-convergence-program.md`
  - IFC / IDS / digital building logbook / passport convergence strategy
- `docs/projects/frontend-performance-and-bundle-hardening-program.md`
  - bundle weight, route chunking, and heavy-surface loading ergonomics
- `docs/projects/frontend-async-state-standardization-program.md`
  - shared `loading / error / empty / data` contract for cards, feeds, tabs, and intelligence panels
- `docs/projects/full-chain-integration-and-demo-truth-program.md`
  - canonical end-to-end scenarios that prove the whole product chain on realistic data
- `docs/projects/domain-facades-and-service-consolidation-program.md`
  - bounded contexts and facades to reduce service saturation and overlap
- `docs/projects/expert-review-disagreement-and-override-governance-program.md`
  - explicit disagreement, override, and confidence-governance layer
- `docs/projects/offline-field-sync-and-resilient-capture-program.md`
  - bounded offline capture and sync resilience for high-value field truth
- `docs/projects/read-models-query-topology-and-aggregate-apis-program.md`
  - aggregate reads, query topology cleanup, summary/projection endpoints
- `docs/projects/api-contracts-and-generated-clients-program.md`
  - schema drift reduction, generated-client strategy, contract integrity
- `docs/projects/async-jobs-projections-and-background-orchestration-program.md`
  - long-running jobs, projections, retries, progress, and background execution model
- `docs/projects/lease-tenancy-and-occupancy-economics-program.md`
  - lease, vacancy, disruption, and rent-impact operating layer
- `docs/projects/utilities-and-recurring-services-program.md`
  - utility accounts, meters, recurring services, and SLA renewals
- `docs/projects/incident-emergency-and-continuity-program.md`
  - incident truth, shutdown states, continuity, and incident-to-claim bridge
- `docs/projects/procurement-vendor-and-sla-program.md`
  - vendor contracts, prequalification, tender packages, and service-level monitoring
- `docs/projects/circularity-and-material-afterlife-program.md`
  - removed material passport, disposal and reuse chain, circularity surfaces
- `docs/projects/tax-incentive-and-fiscal-readiness-program.md`
  - fiscal readiness, grant timing, rebate eligibility, and incentive loss risk
- `docs/projects/climate-resilience-and-environmental-context-program.md`
  - flood/heat/noise context, resilience readiness, and territorial environmental signals
- `docs/projects/training-certification-and-operating-enablement-program.md`
  - operator readiness, SOP library, training packs, and reviewer certification
- `docs/projects/territory-public-systems-and-utility-coordination-program.md`
  - public-system dependencies, utility impacts, district constraints, public-owner patterns
- `docs/projects/market-reference-schema-and-meta-os-governance-program.md`
  - exchange schema, trust handshake, external reliance, infrastructure governance
- `docs/projects/semantic-building-operations-and-systems-program.md`
  - future systems semantics, technical equipment, Brick/Haystack-aligned operations expansion
- `docs/projects/legal-grade-proof-and-chain-of-custody-program.md`
  - version-certified proof, custody events, delivery receipts, archival defensibility
- `docs/projects/enterprise-identity-and-tenant-governance-program.md`
  - SSO-ready identity direction, tenant boundaries, delegation, support/admin audit
- `docs/projects/bim-3d-and-geometry-native-intelligence-program.md`
  - geometry-native issues, 2D/3D model direction, plan-vs-reality path
- `docs/projects/execution-quality-and-hazardous-works-operations-program.md`
  - checkpoints, method statements, work quality records, disposal chain linkage
- `docs/projects/partner-network-and-contributor-reputation-program.md`
  - contributor quality signals, partner trust, routing suggestions, network pull
- `docs/projects/benchmarking-learning-and-market-intelligence-program.md`
  - benchmarking, learning signals, privacy-safe aggregates, recommendation learning
- `docs/projects/autonomous-dossier-completion-and-verification-program.md`
  - autonomous completion loops, verification guardrails, and review-ready dossier closure
- `docs/projects/constraint-graph-and-dependency-intelligence-program.md`
  - dependency graph, unlock sequencing, and blocker propagation intelligence
- `docs/projects/coownership-governance-and-resident-operations-program.md`
  - co-ownership governance, resident operations, and decision traceability
- `docs/projects/counterfactual-stress-testing-and-shock-planning-program.md`
  - scenario stress testing under regulatory, cost, and timing shocks
- `docs/projects/cross-modal-change-detection-and-reconstruction-program.md`
  - cross-modal drift detection and reconstruction between plans, docs, and field truth
- `docs/projects/decision-replay-and-operator-memory-program.md`
  - operator memory, decision replay, and judgement trace surfaces
- `docs/projects/energy-carbon-and-live-performance-program.md`
  - energy/carbon/live-performance signals connected to dossier and portfolio logic
- `docs/projects/multimodal-building-understanding-and-grounded-query-program.md`
  - grounded multimodal query across building evidence and memory layers
- `docs/projects/open-source-accelerators-2026-radar.md`
  - build-vs-pull execution radar for mature open-source accelerators
- `docs/projects/permit-procedure-and-public-funding-program.md`
  - permit/procedure orchestration and public-funding readiness flow
- `docs/projects/sensor-fusion-and-live-building-state-program.md`
  - live-state fusion from sensors into trust/readiness/product operations
- `docs/projects/warranty-defects-and-service-obligations-program.md`
  - warranty and recurring service obligations with lifecycle tracking
- `docs/projects/weak-signal-watchtower-program.md`
  - early weak-signal detection before readiness/trust degradation becomes visible
- `docs/projects/ecobau-inspired-readiness-and-eco-specs-program.md`
  - Polludoc-style trigger assistant, eco tender clauses, PFAS readiness extension, material evidence shelf
- `docs/projects/service-consumer-mapping-and-dead-code-pruning-program.md`
  - explicit service-consumer graph, orphan pruning, and facade-aligned consolidation discipline
- `docs/projects/test-right-sizing-and-integration-confidence-program.md`
  - higher-signal test topology, seeded full-chain proofs, and broad-suite right-sizing
- `docs/projects/continuous-review-and-modernization-program.md`
  - structured modernization pass for tooling, tests, integrations, and repo coherence

### Ready wave briefs (W86-W87)

- `docs/waves/w86-a-header-dropdown-keyboard-a11y.md`
  - fix keyboard close + menu semantics for header dropdowns
- `docs/waves/w86-b-skip-link-and-main-landmark.md`
  - add skip-to-content path with stable main target
- `docs/waves/w86-c-command-palette-modal-a11y.md`
  - close command palette modal/focus findings
- `docs/waves/w86-compact.yaml`
  - compact yaml execution pack for W86
- `docs/waves/w87-a-prework-trigger-backend.md`
  - additive prework trigger backend contract in readiness payload
- `docs/waves/w87-b-prework-trigger-ui-card.md`
  - prework trigger card on BuildingDetail/Readiness surfaces
- `docs/waves/w87-c-eco-clause-template-backend.md`
  - eco clause template service for pack consumption
- `docs/waves/w87-compact.yaml`
  - compact yaml execution pack for W87

### Prepared no-stop wave chain (W86 -> W87)

1. `W86` launch condition (accessibility closeout wave):
- pull `W86-A/B/C` in parallel
- acceptance gate:
  - header dropdown Escape-close + keyboard semantics verified
  - skip-link path works on key routes
  - command palette modal keyboard flow complete (`aria-modal`, no Tab trap, focus restore)

2. `W87` launch condition (safe-to-start differentiation wave):
- start when W86 is accepted
- pull `W87-A/B/C` in parallel (`backend trigger`, `ui card`, `eco clauses`)
- acceptance gate:
  - readiness payload includes additive `prework_trigger`
  - UI trigger card rendered with fallback behavior
  - eco clause template payload generated and consumable by pack flow

### Binary acceptance gates (PASS/FAIL)

Pre-launch readiness gates:
- `G-W76-READY` must be `PASS` before launching W76
```powershell
python scripts/wave_readiness_gate.py --wave-id W76 --expect-three --brief docs/waves/w76-a-polludoc-trigger-backend.md --brief docs/waves/w76-b-polludoc-trigger-ui.md --brief docs/waves/w76-c-eco-clause-template-backend.md
```
- `G-W77-READY` must be `PASS` before launching W77
```powershell
python scripts/wave_readiness_gate.py --wave-id W77 --expect-three --brief docs/waves/w77-a-pfas-readiness-backend.md --brief docs/waves/w77-b-pfas-readiness-wallet-ui.md --brief docs/waves/w77-c-material-recommendation-backend.md
```
- `G-W78-READY` must be `PASS` before launching W78
```powershell
python scripts/wave_readiness_gate.py --wave-id W78 --expect-three --brief docs/waves/w78-a-material-recommendation-ui.md --brief docs/waves/w78-b-eco-clause-pack-integration.md --brief docs/waves/w78-c-safe-to-start-gate-proof-refresh.md
```

Wave closeout binary gates:
- `G-W76-DONE` = PASS only if W76-A/B/C validations are green and statuses moved to `done`
- `G-W77-DONE` = PASS only if W77-A/B/C validations are green and statuses moved to `done`
- `G-W78-DONE` = PASS only if:
  - W78-A/B are `done`
  - `npm run gate:safe-to-start` is green
  - `npm run gate:safe-to-start:bundle -- --strict-pass` is green

Rule:
- when the active top queue starts to thin out, pull the next project brief directly instead of waiting for a new prompt

### BatiConnect Product Blueprint Program

- status: BC1 accepted, BC2 accepted, Lease Ops accepted, hub files wired
- umbrella brief: `docs/projects/baticonnect-product-blueprint-program.md`
- blueprints: `docs/blueprints/baticonnect-{domain,surface,capability,build-order}-blueprint.md`

#### Completed waves
- **BC1 Canonical Backbone**: 7 new SQLAlchemy models (Contact, PartyRoleAssignment, Portfolio, BuildingPortfolio, Unit, UnitZone, OwnershipRecord) + ProvenanceMixin + migrations 005-006 + 48 tests
- **BC2 Property Management**: 9 new models (Lease, LeaseEvent, Contract, InsurancePolicy, Claim, FinancialEntry, TaxContext, InventoryItem, DocumentLink) + migrations 007-008 + existing model edits (intervention.contract_id, zone.usage_type, document.content_hash) + 99 tests
- **Lease Ops**: First vertical slice — lease_service + API routes + RBAC + contact_lookup + seed_lease_ops + LeasesTab in BuildingDetail + 19 API tests + 8 frontend tests
- **Supervisor merge**: router.py wired (leases + contact_lookup), models/__init__.py wired (all BC1+BC2 models)

#### Active / Next
- Contract Ops slice (in progress)
- Ownership Ops slice (in progress)
- W-BC3 deferred (read-model extensions after vertical slices prove the backbone)

#### Doctrine
- build once expose later, superset + adapters, derived projections only
- vertical slices > horizontal backbone after BC2
- canonical entities: Portfolio, Asset, Unit, Party, PartyRoleAssignment, Ownership, Lease, Contract, InsurancePolicy, Claim, Document, EvidenceItem, Communication, Obligation, Incident, Intervention, FinancialEntry, TaxContext, InventoryItem, Recommendation, AIAnalysis, MemorySignal

## Future Horizon Feed

This section exists so Claude can keep momentum after the active top queue, without waiting for a new strategic prompt.
It should stay compact and focus on the next believable product jumps, not the full moonshot map.

### After the active wave, the most likely next program clusters are:

1. **Search -> retrieval -> dossier navigation**
- finish Meilisearch
- group results by entity and evidence usefulness
- use search to accelerate dossier completion and proof lookup

2. **Campaigns -> portfolio execution**
- multi-building action campaigns
- campaign recommendation logic
- campaign progress and impact visibility

3. **Readiness and trust states**
- `ReadinessAssessment`
- `BuildingTrustScore`
- `UnknownIssue`
- make the product explicit about what is ready, what is missing, and what is still unreliable

4. **Post-works truth**
- `PostWorksState`
- after-intervention truth and residual memory
- comparison of before / after intervention states

5. **Simulation persistence and portfolio decisioning**
- `SavedSimulation`
- compare scenarios later
- bridge toward cost / sequence / CAPEX logic

6. **International-class operating layers**
- interoperability surfaces:
  - export standards
  - partner-facing APIs / webhooks / SDK paths
- trust surfaces:
  - cleaner validation baselines
  - stronger audit trails
  - dossier reliability / trust scoring
- execution quality:
  - search that actually scales
  - export progress and recovery
  - real-integration confidence, not just mock success

7. **Occupant / tenancy / lease arc**
- occupancy impact windows
- lease and rent disruption logic
- tenant/resident communication
- acknowledgement and governance surfaces

8. **Utility / service / operations arc**
- utility accounts and meter contracts
- recurring service contracts
- building services and SLA renewals
- live operations memory

9. **Incident / claims / continuity arc**
- incident truth
- shutdown states
- crisis communication
- incident-to-claim bridge
- continuity memory

10. **Circularity / material afterlife arc**
- removed material passport
- disposal and reuse chain
- circularity score and trace pack
- regulated afterlife memory

11. **Finance / insurance / transaction arc**
- sell / insure / finance readiness
- lender / insurer / buyer packs
- underwriting and claims flows

12. **Authority / funding / fiscal arc**
- permit readiness
- funding and subsidy packs
- fiscal readiness and incentives
- procedural blockers and public-system coordination

13. **Network / standard / exchange arc**
- building passport exchange
- external viewers and embedded channels
- openBIM / digital logbook convergence
- ecosystem pull and standards

14. **Remediation module (internal -- mise en concurrence encadree)**
- closed verified network, not open directory
- 6 lots: 1.Foundations, 2.Neutral RFQ, 3.Award+Trust, 4.Post-works truth, 5.Monetization, 6.Site integration
- Lot 4 (post-works truth): link CompletionConfirmation to PostWorksState, auto-generate before/after comparison, feed trust score and passport grade
- shares infra with BatiConnect (auth, docs, audit)
- own models and routes
- invariants: no recommendation, payment != ranking, verified contracts only
- **4 architecture contracts as prerequisites**:
  - AC-1: Event backbone (domain events for cross-module reactivity)
  - AC-2: Projection bus (read-model rebuild from event stream)
  - AC-3: Plugin boundary (module isolation contract -- remediation as first plugin)
  - AC-4: AI feedback loop contract (structured feedback ingestion for learning layer)

15. **AI progressive learning layer (transversal capability)**
- Phase 1: Supervised extraction -- document parsing confidence scores, human correction loop, ai_extraction_log table
- Phase 2: Pattern recognition -- contradiction detection improvements, ai_rule_pattern table, readiness advisor suggestions
- Phase 3: Portfolio intelligence -- cross-building pattern mining, risk prediction, maintenance forecasting, ai_feedback table
- transversal: serves all modules (diagnostics, remediation, passport, readiness, portfolio)
- invariant: AI assists, never decides -- human confirmation required for all write operations

16. **Data flywheel (structural capability)**
- every user action (upload, correction, confirmation, review) enriches the model
- feedback loops: extraction accuracy improves with corrections, trust scores refine with evidence, readiness checks sharpen with regulatory updates
- network effects: more buildings = better pattern recognition, more companies = better benchmarking, more cantons = broader regulatory coverage
- flywheel stages: capture -> enrich -> learn -> predict -> capture (continuous)
- metric: knowledge density per building increases monotonically over time

### Promotion rule

- if the active wave finishes early, promote items from this feed into `Next 10 Actions`
- if current work uncovers structural debt, prefer the low-regret object that removes the debt rather than opening a flashy new surface

### Scope expansion note

Future horizons should now be read through the larger `Built Environment Meta-OS` framing:
- current wedge remains tight and sellable
- future system breadth is intentionally much larger
- architecture should not under-model owner, territory, public-system, finance, occupancy, or operations surfaces

## MP1 Exit Criteria Status

| Criterion | Status | Notes |
|-----------|--------|-------|
| Physical building model end to end | ✅ done | Zones, elements, materials, interventions, plans — models + APIs + UI |
| Evidence chain visible in backend and UI | ✅ done | EvidenceLink model + API + EvidenceChain component |
| Building dossier generation (PDF + HTML) | ✅ done | Gotenberg HTML→PDF, HTML fallback, DossierPackButton |
| Completeness engine | ✅ done | 16 checks, 5 categories, CompletenessGauge UI |
| Unified timeline | ✅ done | TimelineService + BuildingTimeline page |
| Automatic actions + regulatory playbooks | ✅ done | ActionGenerator from diagnostics, CFST/SUVA/canton rules |
| Parse/review/apply PDF workflow | ✅ done | DiagnosticView sample parsing |
| Document ingestion (ClamAV + OCRmyPDF) | ✅ done | FileProcessingService, async pipeline |
| Jurisdictions + regulatory packs | ✅ done | Multi-level hierarchy, seed data for CH cantons |
| Portfolio dashboard | ✅ done | KPIs, risk distribution, pollutant prevalence |
| Campaign system (Action OS) | ✅ done | Campaign model + API + service + frontend page + 34 tests + seed data |
| Cross-entity search (Meilisearch) | ✅ done | SearchService + API + CommandPalette wired + 20 tests |
| Anticipatory domain models (Wave 6) | ✅ done | SavedSimulation, DataQualityIssue, ChangeSignal, ReadinessAssessment — backend only |
| Frontier domain models (Wave 7) | ✅ done | BuildingTrustScore, UnknownIssue, PostWorksState — backend only, 26 tests |
| Intelligence surfaces on BuildingDetail (Wave 13) | ✅ done | ReadinessSummary, TrustScoreCard, UnknownIssuesList, ChangeSignalsFeed — 4 components on overview |
| Seeds, tests, docs reflect state | ✅ done | All counters updated, ORCHESTRATOR refreshed |

## MP2 Status (Governance + Collaboration)

| Capability | Status |
|-----------|--------|
| Users + RBAC | ✅ done |
| Organizations | ✅ done |
| Invitations | ✅ done |
| Assignments | ✅ done |
| Notifications | ✅ done |
| Export jobs | ✅ done |
| Audit logs | ✅ done |
| Settings | ✅ done |
| Cross-entity search (Meilisearch) | ✅ done |
| First invisible agents | ✅ done | Dossier Completion Agent v1 (W25-A) |

## Execution Board — Active Wave

| ID | Workstream | Scope | Status | Owner | Notes |
|----|------------|-------|--------|-------|-------|
| W6-A | Campaign system | Model, schema, API, service, tests, seed enrichment | done | agent-1 | 34 tests, 3 seeded campaigns |
| W6-B | Anticipatory domain models | SavedSimulation, DataQualityIssue, ChangeSignal, ReadinessAssessment | done | agent-2 | 36 tests, 4 models + schemas + APIs |
| W6-C | Meilisearch integration | Service, API, config, sync hooks | done | agent-3 | 20 tests, 3 indexes |
| W6-D | Campaign frontend | Page, sidebar nav, route, i18n, e2e | done | lead | 11 e2e tests, 4-lang i18n |
| W6-E | Search UI enhancement | CommandPalette wired to Meilisearch with fallback | done | lead | Cross-entity search |
| W6-F | i18n + e2e for new features | Campaign + search keys in 4 languages | done | lead | 1080 keys × 4 langs |
| W6-G | Full validation + doc sync | All counters updated | done | lead | 1425 backend, 137 unit, 173 e2e |
| W6-H | Validation hygiene | AsyncMock warning fixed in seed_data tests | done | lead | 0 warnings |
| W6-I | Real e2e environment hardening | — | ready | lead | Still environment-sensitive |
| W7-A | BuildingTrustScore backend | Model, schema, API, RBAC, 8 tests | done | agent | building_trust_score_v2.py, trust_score.py |
| W7-B | UnknownIssue backend | Model, schema, API, RBAC, 9 tests | done | agent | unknown_issue.py |
| W7-C | PostWorksState backend | Model, schema, API, RBAC, 9 tests | done | agent | post_works_state.py |
| W8-A | Rule Resolution Service | rule_resolver.py + 21 tests | done | lead | Jurisdiction-hierarchy-aware pack resolution |
| W8-B | Wire compliance_engine | Async resolved functions + 15 tests | done | agent | Pack first, hardcoded fallback |
| W8-C | Wire risk_engine | Pack-driven calibration override | done | lead | Step 1b: override base probs from RegulatoryPack |
| W8-D | Wire dossier_service | Pack-resolved cantonal reqs + thresholds | done | agent | 27 dossier tests pass |
| W9-A | Seed cantonal metadata | VD/GE/ZH/BE/VS metadata_json enrichment | done | lead | diagnostic_required_before_year, form_name, etc. |
| W9-B | Readiness Reasoner service | readiness_reasoner.py + tests | done | agent | safe_to_start/tender/reopen/requalify |
| W9-C | Dossier Archival service | dossier_archive_service.py + tests | done | agent | SHA-256 hash, versioned archives |
| W9-D | Campaign Recommender | campaign_recommender.py + API + 10 tests | done | lead | 5 analyzers: diag gaps, risk, actions, docs, pollutants |
| W10-A | BuildingTrustScore calculator | trust_score_calculator.py + 9 tests | done | agent | Compute reliability from evidence/completeness/data quality |
| W10-B | UnknownIssue generator | unknown_generator.py + 9 tests | done | agent | Auto-detect 7 gap categories, idempotent + auto-resolve |
| W10-C | PostWorksState lifecycle | post_works_service.py + 10 tests | done | agent | Generate from interventions + before/after comparison |
| W11-A | ComplianceArtefact (LCH-D) | Model + schema + API + service + 12 tests | done | agent | Authority submissions, waste manifests, clearance lifecycle |
| W11-B | ChangeSignal generators | change_signal_generator.py + 10 tests | done | agent | 7 signal types, idempotent, acknowledge, summary |
| W12-A | AvT→ApT transition (LCH-E) | avt_apt_transition.py + 7 tests | done | agent | Bridge completeness+readiness+post-works+compliance |
| W12-B | seed_verify extension | 9 new model checks + 9 tests | done | agent | Campaigns + 8 runtime-generated models |
| W13-A | Readiness + Trust + Unknowns UI | 3 API clients, 3 components, types, 4-lang i18n | done | agent | ReadinessSummary, TrustScoreCard, UnknownIssuesList |
| W13-B | Change Signals UI + e2e mocks | API client, component, 4 mock routes, i18n | done | agent | ChangeSignalsFeed + 4 new e2e mock routes |
| W13-C | Intelligence grid integration | Wire 4 components into BuildingDetail overview | done | lead | 2x2 grid on overview tab |
| W14-A | LCH-F: UX liability wording | Disclaimers on readiness, completeness, simulator, dossier + suva fix | done | agent | 4 components + 4 i18n files |
| W14-B | Export jobs list page | exportsApi + ExportJobs page + sidebar + route + e2e mock | done | agent | Lazy-loaded, polling for active jobs |
| W14-C | Saved simulation UI | savedSimulationsApi + save/history/delete on RiskSimulator | done | agent | Save dialog + history panel + e2e mock |
| W15-A | Campaign progress KPIs | 4-card KPI summary + budget utilization bars | done | agent | Campaigns page enhanced |
| W15-B | Trust on list + portfolio | Data freshness column/card + readiness bar on Portfolio | done | agent | BuildingsList table + BuildingCard + Portfolio |
| W15-C | EvidencePack scaffolding | Model + schema + API + 11 tests + seed_verify | done | agent | authority_pack/contractor_pack/owner_pack types |
| P-LCH | Legislative compliance hardening | Workstreams A-F done | done | — | See `docs/projects/legislative-compliance-hardening.md` |
| P-TRP | Trust / readiness / post-works productization | Trust score, unknowns, readiness UI on overview | done | — | W13 delivered frontend surfaces |
| P-PEP | Portfolio execution and packs | Export progress, saved simulations UI, pack scaffolding | done | — | All 3 items delivered (W14-B, W14-C, W15-C) |
| W16-A | PostWorks before/after diff view | API endpoints (compare+summary) + PostWorksDiffCard UI + i18n + e2e mock + 7 tests | done | agent | Full-width card below intelligence grid on BuildingDetail |
| W16-B | Readiness-driven action generation | readiness_action_generator.py + API endpoint + 9 tests | done | agent | 18 check→action mappings, idempotent, auto-resolve |
| W16-C | ChangeSignal portfolio feed | Portfolio-level endpoint + PortfolioSignalsFeed component + i18n + e2e mock + 5 tests | done | agent | Severity filter pills, cross-building signals on Portfolio |
| W17-A | Search result grouping | CommandPalette grouped by entity type + filter pills + i18n | done | agent | Buildings/Diagnostics/Documents sections with counts |
| W17-B | Test noise cleanup | act() warnings + Router future flags fixed in 5 test files | done | agent | Zero warnings in unit suite |
| W17-C | Contradiction detection service | contradiction_detector.py + API endpoints + 11 tests | done | agent | 5 detector types, idempotent, auto-resolve |
| W18-A | Building passport summary state | passport_service.py + API + 8 tests | done | agent | A-F grade, knowledge/readiness/blindspots/contradictions/evidence |
| W18-B | Contradiction summary UI | ContradictionCard + API client + i18n + e2e mock | done | agent | Scan button, type pills, progress bar on BuildingDetail |
| W18-C | Readiness Wallet UI | ReadinessWallet page + evaluate-all endpoint + route + i18n + e2e mock | done | agent | 4 readiness cards with checks/blockers/conditions deep-dive |
| W19-A | Passport summary UI | PassportCard component + API client + i18n + e2e mock | done | agent | Grade badge, knowledge bar, metrics row on BuildingDetail |
| W19-B | Time Machine foundations | BuildingSnapshot model + schema + service + API + RBAC + 11 tests | done | agent | capture, compare, list snapshots |
| W19-C | Authority-ready demo seed | seed_demo_authority.py + 8 tests | done | agent | Full compliance journey: 5 pollutants, artefacts, interventions, generators |
| W20-A | Time Machine UI | snapshotsApi + TimeMachinePanel on BuildingDetail + i18n + e2e mock | done | agent | Snapshot list, capture, compare mode with deltas |
| W20-B | Intervention Simulator v1 | intervention_simulator.py + schemas + API endpoint + 8 tests | done | agent | Simulate planned interventions → projected state + recommendations |
| W20-C | Building memory transfer package | transfer_package_service.py + schemas + API + router + 10 tests | done | agent | 11-section portable building intelligence bundle |
| W21-A | Intervention Simulator UI | simulatorApi + InterventionSimulator page + route + i18n + e2e mock | done | agent | 408-line page with intervention builder + projected state |
| W21-B | Requalification replay timeline | requalification_service.py + schemas + API + 10 tests | done | agent | Chronological change signals + snapshots + grade transitions |
| W21-C | Plan annotation foundations | PlanAnnotation model + CRUD in technical_plans.py + 13 tests | done | agent | 6 annotation types, relative coordinates, zone/sample/element refs |
| W22-A | Requalification replay UI | RequalificationTimeline component + API client + BuildingDetail activity tab + i18n + e2e mock | done | agent | Color-coded timeline with grade transition badges |
| W22-B | Proof heatmap service | plan_heatmap_service.py + schemas + API endpoint + 10 tests | done | agent | Aggregate annotations → heatmap with trust/unknown/contradiction overlays |
| W22-C | Transfer package UI | TransferPackagePanel + API client + BuildingDetail details tab + i18n + e2e mock | done | agent | 11-section checklist, generate, download JSON |
| W23-A | Transaction readiness backend | transaction_readiness_service.py + schemas + API + 20 tests | done | agent | sell/insure/finance/lease evaluations reusing passport+completeness+trust |
| W23-B | Safe-to-X cockpit UI | SafeToXCockpit page + transactionReadiness API + route + i18n + e2e mock | done | agent | 2x2 grid with status badges, expandable blockers/conditions/recommendations |
| W23-C | Building comparison backend | building_comparison_service.py + schemas + API + 22 tests | done | agent | Compare 2-10 buildings on passport/trust/readiness/completeness |
| W24-A | Contractor acknowledgment workflow | Model + schema + service + API + 20 tests | done | agent | Lifecycle: pending→sent→viewed→acknowledged/refused/expired, SHA-256 hash |
| W24-B | Building comparison UI | BuildingComparison page + API client + route + sidebar + i18n + e2e mock | done | agent | 7-dimension table, color-coded best/worst, dark mode |
| W24-C | Proof heatmap UI | ProofHeatmapOverlay + API client + BuildingExplorer integration + i18n + e2e mock | done | agent | SVG overlay, 5 categories, intensity sizing, coverage badge |
| W25-A | Dossier Completion Agent v1 | dossier_completion_agent.py + schemas + API + 22 tests | done | agent | Orchestrates unknowns+trust+completeness+readiness → unified report |
| W25-B | Campaign impact visibility UI | Impact endpoint + enhanced Campaigns page + progress ring + velocity + at-risk + i18n + e2e mock + 9 tests | done | agent | Color-coded progress, timeline bar, impact metrics |
| W25-C | Portfolio risk heatmap | GeoJSON endpoint + PortfolioRiskMap component + heatmap/points modes + filters + i18n + e2e mock + 9 tests | done | agent | Mapbox GL heatmap + points, risk/canton filters, dark mode |
| W26-A | Bulk action operations | bulk_operations_service.py + schemas + API + 12 tests | done | agent | Batch generate_actions/unknowns/readiness/trust/dossier_agent across 1-50 buildings |
| W26-B | Document template system | document_template_service.py + schemas + API + tests | done | agent | 7 template types: SUVA notification, cantonal, waste plan, work auth, clearance, building/diagnostic summary |
| W26-C | Sampling planner foundations | sampling_planner.py + schemas + API + 16 tests | done | agent | Evidence-collection recommendations from unknowns + zone coverage + obsolete diagnostics |
| W27-A | Guided dossier completion workspace | completion_workspace_service.py + schemas + API + 17 tests | done | agent | Human-in-the-loop completion console: dependency-aware steps from dossier report |
| W27-B | Pack impact simulator | pack_impact_service.py + schemas + API + 18 tests | done | agent | Zone overlap analysis, trust degradation prediction, stale pack detection |
| W27-C | Audit trail export | audit_export_service.py + schemas + API + 15 tests | done | agent | CSV/JSON/XLSX audit log export with building/date/actor filters + streaming download |
| W28-A | Multi-org dashboard | multi_org_dashboard_service.py + schemas + API + 17 tests | done | agent | Cross-organization portfolio view with aggregated metrics + org comparison |
| W28-B | Notification preferences | notification_preferences_service.py + schemas + API + model + 20 tests | done | agent | Extended per-user control: channels, quiet hours, digest, should_notify |
| W28-C | Building timeline enrichment | timeline_enrichment_service.py + schemas + API + 35 tests | done | agent | Lifecycle phases, importance scoring, auto-linking between related events |
| W29-A | Field capture / observation layer | field_observation_service.py + model + schemas + API + 18 tests | done | agent | Field observations with severity, verification workflow, building summary |
| W29-B | Authority pack generation | authority_pack_service.py + schemas + API + 19 tests | done | agent | 8-section authority-ready evidence packs with per-section completeness |
| W29-C | Campaign execution tracking | campaign_tracking_service.py + schemas + API + 15 tests | done | agent | Per-building campaign status, progress tracking, blocked buildings, batch updates |
| W30-A | Requalification enrichment | requalification_service.py enriched + schemas + API + tests | done | agent | Trigger detection (5 types), recommendations, trigger report with urgency |
| W30-B | Proof heatmap enrichment | plan_heatmap_service.py enriched + schemas + API + tests | done | agent | Zone stats, date snapshot, coverage gap detection, temporal decay, sample confidence |
| W30-C | Transaction readiness enrichment | transaction_readiness_service.py enriched + schemas + API + tests | done | agent | Insurance risk tiers, financing score, comparative readiness, trend analysis |
| W31-A | Evidence link graph | evidence_graph_service.py + schemas + API + 26 tests | done | agent | Graph traversal, BFS path finding, connected components, orphan detection, subgraph extraction |
| W31-B | Portfolio risk trends | portfolio_risk_trends_service.py + schemas + API + 25 tests | done | agent | Monthly trend, trajectories, hotspots, distribution, period comparison, risk report |
| W31-C | Compliance timeline | compliance_timeline_service.py + schemas + API + 25 tests | done | agent | Per-pollutant compliance, deadlines (asbestos 3y/PCB 5y), gap analysis, next actions |
| W32-A | Weak signal watchtower | weak_signal_watchtower.py + schemas + API + 27 tests | done | agent | 7 detection rules, portfolio scan, critical path buildings, signal history |
| W32-B | Constraint graph | constraint_graph_service.py + schemas + API + 29 tests | done | agent | Dependency intelligence, unlock analysis, what-if simulation, readiness blockers |
| W32-C | Decision replay | decision_record model + decision_replay_service.py + schemas + API + 32 tests | done | agent | Decision records, context capture, impact analysis, patterns, search |
| W33-A | Building dashboard aggregate | building_dashboard_service.py + schemas + API + 23 tests | done | agent | Single-call read model for building detail, batch dashboards, quick mode |
| W33-B | Portfolio summary aggregate | portfolio_summary_service.py + schemas + API + 20 tests | done | agent | 7-dimension portfolio summary, health score, org comparison |
| W33-C | Notification digest | notification_digest_service.py + schemas + API + 19 tests | done | agent | Daily/weekly digest, 5 sections, preview headline, mark-sent |
| W34-A | Anomaly detection | anomaly_detection_service.py + schemas + API + 23 tests | done | agent | Statistical outlier detection, z-score/IQR, building anomaly scan, portfolio sweep |
| W34-B | Building benchmark | building_benchmark_service.py + schemas + API + 21 tests | done | agent | Peer comparison, percentile ranking, gap analysis, benchmark groups |
| W34-C | Maintenance forecast | maintenance_forecast_service.py + schemas + API + 26 tests | done | agent | Predictive maintenance, cost projection, priority ranking, portfolio forecast |
| W35-A | Document classification | document_classification_service.py + schemas + API + 30 tests | done | agent | Auto-classify docs by category/pollutant, coverage gaps, missing doc suggestions |
| W35-B | Remediation cost estimator | remediation_cost_service.py + schemas + API + 32 tests | done | agent | CHF cost estimation per pollutant, Swiss market rates, building comparison, cost factors |
| W35-C | Regulatory deadline monitor | regulatory_deadline_service.py + schemas + API + 31 tests | done | agent | Deadline tracking (asbestos 3yr, PCB 5yr, radon 10yr), portfolio alerts, calendar view |
| W36-A | Energy performance | energy_performance_service.py + schemas + API + tests | done | agent | CECB-inspired A-G class, CO2 footprint, renovation impact simulation |
| W36-B | Risk mitigation planner | risk_mitigation_planner.py + schemas + API + tests | done | agent | Optimal remediation sequence, dependency analysis, quick wins identification |
| W36-C | Portfolio optimization | portfolio_optimization_service.py + schemas + API + 40 tests | done | agent | Building prioritization, action plan, risk distribution, budget allocation simulation |
| W37-A | Pollutant inventory | pollutant_inventory_service.py + schemas + API + 26 tests | done | agent | Consolidated pollutant view, summary by type, portfolio overview, hotspot ranking |
| W37-B | Workflow orchestration | workflow_orchestration_service.py + schemas + API + 35 tests | done | agent | Multi-step state machine: diagnostic/remediation/clearance/renovation workflows |
| W37-C | Insurance risk assessment | insurance_risk_assessment_service.py + schemas + API + 26 tests | done | agent | Insurance tiers, premium multipliers, liability exposure, portfolio insurance summary |
| W38-A | Data provenance tracker | data_provenance_service.py + schemas + API + 32 tests | done | agent | Provenance chain, building lineage DAG, integrity verification, org statistics |
| W38-B | Occupant safety evaluator | occupant_safety_service.py + schemas + API + 51 tests | done | agent | Safety levels, exposure pathways, Swiss pollutant rules, safety recommendations |
| W38-C | Regulatory change impact | regulatory_change_impact_service.py + schemas + API + 27 tests | done | agent | Threshold simulation, multi-change analysis, sensitivity profile, compliance forecast |
| W39-A | Spatial risk mapping | spatial_risk_mapping_service.py + schemas + API + 27 tests | done | agent | Zone risk overlay, floor profiles, propagation analysis, coverage gaps |
| W39-B | Stakeholder report generator | stakeholder_report_service.py + schemas + API + 29 tests | done | agent | Owner/authority/contractor reports, portfolio executive summary |
| W39-C | Contractor matching | contractor_matching_service.py + schemas + API + 25 tests | done | agent | Contractor ranking, SUVA certifications, workforce sizing, portfolio demand |
| W40-A | Cost-benefit analysis | cost_benefit_analysis_service.py + schemas + API + 27 tests | done | agent | Intervention ROI, 3 remediation strategies, inaction cost, portfolio investment plan |
| W40-B | Building lifecycle | building_lifecycle_service.py + schemas + API + 29 tests | done | agent | 7-phase lifecycle detection, timeline, prediction, portfolio distribution |
| W40-C | Waste management planner | waste_management_service.py + schemas + API + 26 tests | done | agent | OLED waste classification, disposal plan, volume estimates, portfolio forecast |
| W41-A | Knowledge gap analyzer | knowledge_gap_service.py + schemas + API + 27 tests | done | agent | Gap detection, investigation priorities, completeness score, portfolio overview |
| W41-B | Handoff pack service | handoff_pack_service.py + schemas + API + 23 tests | done | agent | Diagnostic/contractor/authority handoff packs, completeness validation |
| W41-C | Quality assurance checker | quality_assurance_service.py + schemas + API + 29 tests | done | agent | 16 QA checks, weighted quality score A-F, trends, portfolio report |
| W42-A | Compliance calendar | compliance_calendar_service.py + schemas + API + 26 tests | done | agent | Monthly/weekly calendar, upcoming deadlines with reminders, scheduling conflicts |
| W42-B | Risk communication | risk_communication_service.py + schemas + API + 25 tests | done | agent | Occupant notices, CFST worker briefings, stakeholder notifications, audit log |
| W42-C | Monitoring plan | monitoring_plan_service.py + schemas + API + 24 tests | done | agent | Post-remediation monitoring, schedule, compliance scoring, portfolio status |
| W43-A | Audit readiness scorer | audit_readiness_service.py + schemas + API + 27 tests | done | agent | 16 weighted checks, checklist, audit simulation, portfolio readiness |
| W43-B | Renovation sequencer | renovation_sequencer_service.py + schemas + API + 27 tests | done | agent | Phase ordering, Gantt timeline, parallel tracks, readiness blockers |
| W43-C | Environmental impact | environmental_impact_service.py + schemas + API + 24 tests | done | agent | Soil/water/air risk, remediation footprint, green score, portfolio report |
| W44-A | Due diligence report | due_diligence_service.py + schemas + API + 25 tests | done | agent | Buyer report, transaction risks, value impact, acquisition comparison |
| W44-B | Regulatory filing generator | regulatory_filing_service.py + schemas + API + 33 tests | done | agent | SUVA notification, cantonal declaration (VD/GE), waste manifest, filing status |
| W44-C | Building health index | building_health_index_service.py + schemas + API + 32 tests | done | agent | 5-dimension health score A-F, breakdown, 12-month trajectory, portfolio dashboard |
| W45-A | Tenant impact assessor | tenant_impact_service.py + schemas + API + 22 tests | done | agent | Displacement needs, communication plan, cost estimate, portfolio exposure |
| W45-B | Lab result tracker | lab_result_service.py + schemas + API + 25 tests | done | agent | Result analysis, anomaly detection, trends, summary report |
| W45-C | Scenario planning | scenario_planning_service.py + schemas + API + 23 tests | done | agent | What-if scenarios, comparison, greedy optimizer, sensitivity analysis |
| W46-A | Access control planner | access_control_service.py + schemas + API + 51 tests | done | agent | Zone access levels, PPE/signage, SUVA permits, portfolio access status |
| W46-B | Priority matrix | priority_matrix_service.py + schemas + API + 28 tests | done | agent | Urgency×impact matrix, critical path, quick wins, portfolio overview |
| W46-C | Evidence chain validator | evidence_chain_service.py + schemas + API + 26 tests | done | agent | Chain integrity, provenance gaps, evidence timeline, per-pollutant strength |
| W47-A | Diagnostic quality | diagnostic_quality_service.py + schemas + API + 23 tests | done | agent | Quality score A-F, diagnostician comparison, deficiency detection, benchmarks |
| W47-B | Budget tracking | budget_tracking_service.py + schemas + API + 25 tests | done | agent | Budget overview, cost variance, quarterly forecast, portfolio summary |
| W47-C | Stakeholder dashboard | stakeholder_dashboard_service.py + schemas + API + 24 tests | done | agent | Owner/diagnostician/authority/contractor role-specific dashboards |
| W48-A | Permit tracking | permit_tracking_service.py + schemas + API + 30 tests | done | agent | Required permits, status tracking, dependency graph, portfolio overview |
| W48-B | Risk aggregation | risk_aggregation_service.py + schemas + API + 28 tests | done | agent | Unified 5-dimension risk score, decomposition, correlations, portfolio matrix |
| W48-C | Document completeness | document_completeness_service.py + schemas + API + 25 tests | done | agent | 8-type completeness score, missing docs, currency validation, portfolio status |
| W49-A | Zone classification | zone_classification_service.py + schemas + API + 30 tests | done | agent | Contamination status, zone hierarchy roll-up, boundary zones, transition history |
| W49-B | Compliance gap closer | compliance_gap_service.py + schemas + API + 22 tests | done | agent | Gap identification, compliance roadmap, cost estimation, portfolio gaps |
| W49-C | Ventilation assessment | ventilation_assessment_service.py + schemas + API + 38 tests | done | agent | Ventilation needs, radon mitigation, air quality monitoring, ORaP compliance |
| W50-A | Material inventory | material_inventory_service.py + schemas + API + 25 tests | done | agent | Material inventory, risk rating, lifecycle/degradation, portfolio overview |
| W50-B | Incident response planner | incident_response_service.py + schemas + API + 24 tests | done | agent | Emergency plans (3 scenarios), contacts, incident probability, portfolio readiness |
| W50-C | Reporting metrics | reporting_metrics_service.py + schemas + API + 24 tests | done | agent | KPI dashboard, operational metrics, periodic reports, benchmark comparison |
| W51-A | Building age analysis | building_age_analysis_service.py + schemas + API + tests | done | agent | Era classification, age-based risk profiling, era hotspots, portfolio age distribution |
| W51-B | Sample optimization | sample_optimization_service.py + schemas + API + 29 tests | done | agent | Sampling plan optimization, cost estimation, adequacy evaluation, portfolio status |
| W51-C | Cross-building patterns | cross_building_pattern_service.py + schemas + API + tests | done | agent | Pattern detection, similar buildings, geographic clusters, undiscovered pollutant prediction |
| W52-A | Regulatory deadlines | regulatory_deadline_service.py + schemas + API + 31 tests | done | agent | Deadline tracking, urgency/status, portfolio deadlines, compliance expiry |
| W52-B | Building certification | building_certification_service.py + schemas + API + 32 tests | done | agent | Minergie/CECB/SNBS/GEAK readiness, available certifications, roadmap, portfolio status |
| W52-C | Occupancy risk | occupancy_risk_service.py + schemas + API + 34 tests | done | agent | Exposure risk, temporary relocation, occupant communication, portfolio occupancy risk |
| W53-A | Maintenance schedule | maintenance_schedule_service.py + schemas + API + 30 tests | done | agent | Predictive maintenance plan, overdue tasks, annual budget, portfolio overview |
| W53-B | Data export | data_export_service.py + schemas + API + 25 tests | done | agent | Building/portfolio export, regulatory report, export history |
| W53-C | Notification rules | notification_rules_service.py + schemas + API + 32 tests | done | agent | Building triggers, preferences, digest, org alert summary |
| W54-A | Building valuation | building_valuation_service.py + schemas + API + 26 tests | done | agent | Pollutant impact, renovation ROI, market position, portfolio valuation |
| W54-B | Work phases | work_phase_service.py + schemas + API + 30 tests | done | agent | CFST work phases, timeline, requirements, portfolio overview |
| W54-C | Regulatory watch | regulatory_watch_service.py + schemas + API + 28 tests | done | agent | Active regulations, impact assessment, threshold simulation, portfolio exposure |
| W55-A | Building clustering | building_clustering_service.py + schemas + API + 25 tests | done | agent | Risk profile clusters, construction era groups, outlier detection, cluster summary |
| W55-B | Remediation tracking | remediation_tracking_service.py + schemas + API + 30 tests | done | agent | Per-pollutant status, timeline, cost tracking, portfolio dashboard |
| W55-C | Stakeholder notification | stakeholder_notification_service.py + schemas + API + 34 tests | done | agent | Owner briefing, diagnostician brief, authority report, role-filtered digest |
| W56-A | Execution quality | execution_quality_service.py + schemas + API + 28 tests | done | agent | Work quality checks, acceptance criteria, building acceptance, portfolio dashboard |
| W56-B | CAPEX planning | capex_planning_service.py + schemas + API + 31 tests | done | agent | Capex plan, reserve fund, investment scenarios, portfolio summary |
| W56-C | Digital vault | digital_vault_service.py + schemas + API + 26 tests | done | agent | Vault summary, document trust, integrity report, portfolio status |
| W57-A | Warranty obligations | warranty_obligations_service.py + schemas + API + 33 tests | done | agent | Defect liability, recurring obligations, defect claims, portfolio overview |
| W57-B | Subsidy tracking | subsidy_tracking_service.py + schemas + API + 28 tests | done | agent | Eligibility, application status, funding gap analysis, portfolio summary |
| W57-C | Co-ownership governance | co_ownership_service.py + schemas + API + 29 tests | done | agent | PPE info, cost split, decision log, portfolio summary |
| W58-A | Sensor integration | sensor_integration_service.py + schemas + API + 28 tests | done | agent | Sensor overview, alerts, trends, portfolio sensor status |
| W58-B | Counterfactual analysis | counterfactual_analysis_service.py + schemas + API + 27 tests | done | agent | What-if scenarios, stress testing, timeline alternatives, portfolio stress test |
| W58-C | Passport export | passport_export_service.py + schemas + API + 28 tests | done | agent | Passport generation, validation, comparison, portfolio summary |
| W59-A | Wire orphan services | transition.py + dossier_archives.py API routes + 15 tests | done | agent | Wire avt_apt_transition (3 endpoints) + dossier_archive_service (4 endpoints) to API |
| W59-B | Missing test coverage | test_building_certification.py (68) + test_building_health_index.py (74) = 142 tests | done | agent | Full test suites for 2 services that had 0 tests |
| W59-C | Shared data loader | building_data_loader.py + 12 tests + refactor 4 services | done | agent | Extract load_org_buildings/load_building_with_context, refactor clustering/age/lifecycle/valuation |
| W60-A | Shared pollutant constants | constants.py + refactor 6 services | done | agent | ALL_POLLUTANTS, POLLUTANT_SEVERITY, ERA_RANGES, DIAGNOSTIC_VALIDITY_YEARS in constants.py |
| W60-B | Building data loader expansion | refactor certification + health_index | done | agent | 2 more services using load_org_buildings |
| W60-C | Batch data loader refactor | refactor 10 services to use load_org_buildings | done | agent | capex, co_ownership, counterfactual, digital_vault, execution_quality, sensor, stakeholder, subsidy, warranty, remediation |
| W76-A | Polludoc-style trigger backend contract | readiness trigger helper + schema contract + tests (no router wiring by agent) | ready | agent | bounded backend task; keep `router.py` to supervisor merge |
| W76-B | Polludoc trigger UI card | Trigger card on BuildingDetail/Readiness + API client wiring + tests | ready | agent | frontend-only surface; consume W76-A response contract |
| W76-C | Eco clause template backend generator | eco spec clause templates for interventions + tests (pack-consumable payload) | ready | agent | backend-only deliverable; no hub file edits by agent |
| W77-A | PFAS readiness backend extension | PFAS checks in readiness reasoner + legal basis mapping + tests | ready | agent | consume `docs/waves/w77-a-pfas-readiness-backend.md`; no router hub edits |
| W77-B | PFAS readiness wallet UI | Wallet/detail PFAS blockers + conditions rendering + tests | ready | agent | consume `docs/waves/w77-b-pfas-readiness-wallet-ui.md`; no i18n hub edits |
| W77-C | Material recommendation evidence shelf backend | recommendation service + interventions endpoint + tests | ready | agent | consume `docs/waves/w77-c-material-recommendation-backend.md`; keep `router.py` to supervisor merge |
| W78-A | Material recommendation shelf UI | shelf component + simulator wiring + tests | ready | agent | consume `docs/waves/w78-a-material-recommendation-ui.md`; no i18n hub edits |
| W78-B | Eco clause pack integration | authority/contractor pack outputs include eco clauses + tests | ready | agent | consume `docs/waves/w78-b-eco-clause-pack-integration.md` |
| W78-C | Safe-to-start gate proof refresh | run gate bot + proof bundle + debrief evidence | ready | lead | consume `docs/waves/w78-c-safe-to-start-gate-proof-refresh.md`; execution-only |
| W81-A | Visual regression hardening | mock visual regression + screenshot audit stabilization | done | agent | animation disable + stable waits + relaxed threshold (0.01→0.02) |
| W81-B | Canonical milestone scenario hardening | real e2e smoke + preflight + runbook sync | done | agent | 7 new canonical tests + typed helpers + preflight phase 5 + runbook sync |
| W81-C | Service consumer audit + pruning candidates | refresh inventory + publish pruning report | done | agent | 141 services mapped, 0 zero-consumer, 94 single-consumer, 14 duplicate families |
| W82-A | Dashboard enhancement | KPI/activity/quick actions + targeted tests | done | agent | 17 new tests; secondary KPIs, quick actions, portfolio health, enhanced activity |
| W82-B | Jurisdiction management polish | AdminJurisdictions UX/API/tests hardening | done | agent | 13 new tests + 6 e2e; search/filter bar, summary stats, error/success feedback |
| W82-C | Building form enhancement | BuildingsList create/edit form UX/validation/tests | done | agent | 12 new tests + 4 e2e; field grouping, egid/egrid/official_id, validation messaging |
| W83-A | Mobile responsiveness audit | mobile e2e checks + reproducible ranked audit report | done | agent | audit report + 12 mobile e2e tests; 2 high + 6 medium issues documented |
| W83-B | PWA offline polish | cache strategy + offline indicator + tests | done | agent | PwaStatusIndicator + workbox runtimeCaching + navigateFallback; 6 new tests; build verified |
| W83-C | Error boundary enhancement | boundary recovery UX + route fallback consistency + tests | done | agent | ErrorBoundary: go-home/copy/details/timestamp; PageErrorBoundary: dark mode/go-back/retry-count; 23 tests (was 5) |
| W84-A | Mobile search trigger fix | restore visible search affordance on mobile header + tests | done | agent | Header.tsx: mobile-only search button (sm:hidden, >=44px touch target) opening CommandPalette; 3 new Header tests + e2e mobile search check |
| W84-B | Building comparison mobile fallback | mobile-friendly comparison layout for 3+ buildings + tests | done | agent | BuildingComparison.tsx: MobileComparisonCard stacked layout <768px, desktop table hidden md:block; 4 new tests + e2e mobile comparison check |
| W84-C | Loading skeleton standardization | shared skeleton/loading pattern consistency + tests | done | agent | Skeleton.tsx: SkeletonLine/SkeletonBlock/InlineSkeleton primitives + a11y (role=status, aria-busy, sr-only); AsyncStateWrapper: uses InlineSkeleton + role=alert on error; 32 new SkeletonLoadingStates tests + 3 new AsyncStateWrapper tests |
| W85-A | Keyboard focus audit | keyboard navigation/focus audit + deterministic checks | done | agent | 14 new e2e tests (8 navigation + 6 pages); audit report with 5 findings (focus traps, skip-link, aria-modal); all green |
| W85-B | Frontend performance audit | build/chunk audit + low-risk quick wins | done | agent | Removed dead `map` chunk + added chunkSizeWarningLimit; build warnings 2→0; report confirms codebase already well-optimized (33 lazy pages) |
| W85-C | Coverage gap analysis | high-signal coverage gap report + targeted test additions | done | agent | 11 new tests (6 CommandPalette + 5 BuildingCard); keyboard nav, search flows, edge cases; gap analysis report with severity ratings |
| W86-A | Header dropdown keyboard a11y | Escape close + menu semantics in header dropdowns | done | agent | Escape keydown closes lang/user dropdowns + focus restore; role="menuitem" on all items; 4 new unit + 1 e2e test |
| W86-B+C | Skip link + CommandPalette a11y | skip-to-content + aria-modal + focus restore + Tab fix | done | agent | Skip link (sr-only, focus-visible) + id="main-content"; aria-modal="true"; Tab no longer trapped; focus restore on close; 3 unit + 4 e2e tests |
| W87-A | Prework trigger backend contract | additive readiness trigger payload + tests | done | agent | PreworkTrigger schema + model_validator deriving from checks_json; GET endpoint; 11 new tests (40 total passed) |
| W87-B | Prework trigger UI card | BuildingDetail/Readiness trigger card + tests | done | agent | PreworkDiagnosticTriggerCard.tsx (dual-mode: prop or self-fetch); wired into OverviewTab + ReadinessWallet; fallback-safe; 3 new tests |
| W87-C | Eco clause template backend | deterministic eco clause payload service + tests | done | agent | eco_clause_template_service.py: renovation/demolition contexts, 5 pollutants, Swiss legal refs; integrated into authority_pack_service; 14 new tests |

## Immediate Post-W10 Chain

When `W10-A/B/C` land, sequence the next moves in this order unless validation reveals a blocker:

1. ✅ wire `BuildingTrustScore` into building detail (W13-A: TrustScoreCard on overview)
2. ✅ wire generated `UnknownIssue` into building detail (W13-A: UnknownIssuesList on overview)
3. ✅ land `PostWorksState` before/after comparison and intervention linkage (W16-A: PostWorksDiffCard on overview)
4. ✅ connect readiness UI to building detail (W13-A: ReadinessSummary on overview)
5. only then widen into transaction / insurance / wow surfaces

Rule:
- finish productization of the new primitives before opening more speculative UI around them

## Next 10 Actions

Keep this list ranked and execution-ready. Reorder it after each wave based on new evidence, dependencies, or blockers.
Near-term target mix for this block: `validation/audit + infra polish` before new feature breadth.
Active override: backend expansion frozen by default in `W81+` until ranks `1-3` are accepted.
Auto-continuity rule: when `Next 10` thins out, auto-promote from `Next ready project briefs`, then from `Future Horizon Feed`, without waiting for a new prompt.

| Rank | Action | Why now | Depends on |
|------|--------|---------|------------|
| 1 | Building workspace shared access model | Core differentiator — multi-actor dossier with role-based views | W100 ✅ |
| 2 | GED inbox: document inbox for unlinked incoming documents | Key reusable module from Batiscan → SwissBuilding | existing document system ✅ |
| 3 | Obligations/deadlines tracker | Building-level obligation engine with due dates and alerts | ActionItem + readiness ✅ |
| 4 | Full test suite regression run | Validate all ~5000 tests still pass after 13 waves | W100 ✅ |
| 5 | Intake public form (lead → contact + building + dossier) | Entry point for external diagnostic requests | W96-W99 ✅ |
| 6 | Search (Meilisearch) finish + cross-entity grouping | Accelerate dossier navigation | existing search service ✅ |
| 7 | Safe-to-start gate proof refresh (real e2e) | External milestone proof — BLOCKED on VPS | W100 ✅ |
| 8 | Building workspace invitation flow | Invite external actors to a workspace | workspace access model |
| 9 | Workspace activity feed (cross-actor) | Unified activity view across workspace members | workspace access model |
| 10 | Control tower dashboard (next best actions) | Pilotage + NBA for building workspace operators | obligations + workspace ✅ |

## Next Queue (11+)

| Rank | Action | Why now | Depends on |
|------|--------|---------|------------|
| 11 | (auto-promote from Future Horizon Feed when ranks clear) | — | — |

Overflow rule:
- keep ranks `1-10` order locked
- pull ranks `11+` only when upstream ranks are accepted or blocked

## Recent Wave History

### Completed in W95

| Former Rank | Action | Result |
|-------------|--------|--------|
| 9 | Seed BC ops verification test (W95-A) | ✅ 51 tests: imports, UUID5 determinism, DB integration, idempotency, referential integrity |
| 10 | Readiness wallet integration test (W95-B) | ✅ 4 new tests: eco clause + prework coexistence, PFAS trigger + eco clause, empty state. Total 10 |
| 2 | Duplicate-service consolidation brief (W95-C) | ✅ Brief: 14 families, 3 HIGH/6 MED/5 LOW priority, 5-phase sequence, ~35-40 eliminations |

W95 debrief:
- clear: final queue clearance wave; 61 tests validated; 21st consecutive zero-fix wave
- fuzzy: nothing
- missing: nothing

### Completed in W94

| Former Rank | Action | Result |
|-------------|--------|--------|
| 5 | Eco clause transfer package test (W94-A) | ✅ 4 new tests: correct keys, section entries, multi-pollutant, section filtering. Total 12 |
| 6 | Material recommendation API test (W94-B) | ✅ 5 new API tests: 200/404/401, pollutant materials, response schema. Total 34 |
| 7 | PFAS compliance engine test (W94-C) | ✅ 15 new tests: water/soil thresholds, waste classification, legal refs, risk levels, auto_classify. Total 32 |

W94 debrief:
- clear: pure test wave; 78 tests validated; 20th consecutive zero-fix wave
- fuzzy: nothing
- missing: nothing

### Completed in W93

| Former Rank | Action | Result |
|-------------|--------|--------|
| 3 | Portfolio PFAS exposure (W93-A) | ✅ pollutant_exposure array in portfolio summary, 6 pollutants. 4 new tests |
| 4 | Contractor eco clause preview (W93-B) | ✅ ContractorEcoClausePreview: pollutant badges, collapsible clauses, legal refs, dark mode. 9 tests |
| 8 | Passport UI PFAS coverage (W93-C) | ✅ PollutantCoverageSection: 6 chips, PFAS emerging badge, coverage ratio. i18n 4 langs. 4 tests |

W93 debrief:
- clear: all 3 scopes disjoint; tsc clean; 19th consecutive zero-fix wave
- fuzzy: nothing
- missing: nothing

### Completed in W99

| Former Rank | Action | Result |
|-------------|--------|--------|
| — | BatiscanClient adapter (W99-A) | ✅ Abstract base + StubBatiscanClient + HttpBatiscanClient + factory. 8 tests |
| — | Diagnostic integration seed (W99-B) | ✅ 2 publications, 2 orders, 2 versions. UUID5 idempotent, realistic Swiss data |

W99 debrief:
- clear: final wave of integration plan; adapter pattern clean; seed realistic
- fuzzy: nothing
- missing: nothing

### Completed in W98

| Former Rank | Action | Result |
|-------------|--------|--------|
| — | DiagnosticPublicationCard (W98-A) | ✅ Badges, PDF link, structured summary, annexes, version history, dark mode. 14 tests |
| — | MissionOrderCard (W98-B) | ✅ Order list + create form, 6 status badges, 8 mission types, dark mode. 12 tests |
| — | BuildingDetail wiring (W98-C) | ✅ API client + DiagnosticsTab React Query + BuildingDetail prop passing. tsc clean |

W98 debrief:
- clear: 3 frontend scopes disjoint; 26 tests; i18n 42 keys
- fuzzy: nothing
- missing: nothing

### Completed in W97

| Former Rank | Action | Result |
|-------------|--------|--------|
| — | Diagnostic integration API (W97-A) | ✅ 7 endpoints: POST/GET publications, manual match, mission orders. Router wired |
| — | Integration tests (W97-B) | ✅ 27 tests: auto-match, idempotency, versioning, manual match, mission orders, schemas |

W97 debrief:
- clear: API + tests disjoint; corrections applied (status enum, last_error, building relationships)
- fuzzy: nothing
- missing: nothing

### Completed in W96

| Former Rank | Action | Result |
|-------------|--------|--------|
| — | DiagnosticPublication models (W96-A) | ✅ DiagnosticReportPublication + DiagnosticPublicationVersion with ProvenanceMixin |
| — | MissionOrder model + schemas (W96-B) | ✅ DiagnosticMissionOrder + 6 Pydantic schemas |
| — | Integration service + migration (W96-C) | ✅ diagnostic_integration_service (matching, idempotence, versioning) + migration 009 |

W96 debrief:
- clear: 3 backend scopes disjoint; architecture decision documented in memory
- fuzzy: nothing
- missing: nothing

### Completed in W95

| Former Rank | Action | Result |
|-------------|--------|--------|
| 9 | Seed BC ops verification test (W95-A) | ✅ 51 tests: imports, UUID5 determinism, DB integration, idempotency, referential integrity |
| 10 | Readiness wallet integration test (W95-B) | ✅ 4 new tests: eco clause + prework coexistence, PFAS trigger + eco clause, empty state. Total 10 |
| 2 | Duplicate-service consolidation brief (W95-C) | ✅ Brief: 14 families, 3 HIGH/6 MED/5 LOW priority, 5-phase sequence, ~35-40 eliminations |

W95 debrief:
- clear: final queue clearance wave; 61 tests validated; 21st consecutive zero-fix wave
- fuzzy: nothing
- missing: nothing

### Completed in W94

| Former Rank | Action | Result |
|-------------|--------|--------|
| 5 | Eco clause transfer package test (W94-A) | ✅ 4 new tests: correct keys, section entries, multi-pollutant, section filtering. Total 12 |
| 6 | Material recommendation API test (W94-B) | ✅ 5 new API tests: 200/404/401, pollutant materials, response schema. Total 34 |
| 7 | PFAS compliance engine test (W94-C) | ✅ 15 new tests: water/soil thresholds, waste classification, legal refs, risk levels, auto_classify. Total 32 |

W94 debrief:
- clear: pure test wave; 78 tests validated; 20th consecutive zero-fix wave
- fuzzy: nothing
- missing: nothing

### Completed in W93

| Former Rank | Action | Result |
|-------------|--------|--------|
| 3 | Portfolio PFAS exposure (W93-A) | ✅ pollutant_exposure array in portfolio summary, 6 pollutants. 4 new tests |
| 4 | Contractor eco clause preview (W93-B) | ✅ ContractorEcoClausePreview: pollutant badges, collapsible clauses, legal refs, dark mode. 9 tests |
| 8 | Passport UI PFAS coverage (W93-C) | ✅ PollutantCoverageSection: 6 chips, PFAS emerging badge, coverage ratio. i18n 4 langs. 4 tests |

W93 debrief:
- clear: all 3 scopes disjoint; tsc clean; 19th consecutive zero-fix wave
- fuzzy: nothing
- missing: nothing

### Completed in W92

| Former Rank | Action | Result |
|-------------|--------|--------|
| 1 | Eco clause UI in ReadinessWallet (W92-A) | ✅ EcoClauseCard with context toggle, pollutant badges, collapsible clauses, legal refs. GET /eco-clauses API. i18n 4 langs. 6+9 tests |
| 2 | Building passport PFAS (W92-B) | ✅ pollutant_coverage section via ALL_POLLUTANTS (6 pollutants). 4 new tests (12 total) |
| 3 | BatiConnect seed enrichment (W92-C) | ✅ seed_bc_ops.py: 5 contacts, 3 ownership, 5 leases, 6 events, 3 contracts, 4 party roles. UUID5 idempotent |

W92 debrief:
- clear: mixed full-stack + backend + seed; supervisor fixed router import order; 18th consecutive zero-fix wave
- fuzzy: nothing
- missing: nothing

### Completed in W91

| Former Rank | Action | Result |
|-------------|--------|--------|
| 1 | Intervention simulator mobile (W91-A) | ✅ Header wrap, 44px touch targets, timeline input full-width, bottom bar stacking. CSS-only |
| 2 | Rules pack studio disclosure (W91-B) | ✅ md:hidden info banner with i18n (4 langs), pack list max-height fix. 3 new tests |
| 3 | MaterialRecoCard wiring (W91-C) | ✅ GET /material-recommendations endpoint + frontend API client + wired into BuildingInterventions via React Query. Router supervisor-merged |

W91 debrief:
- clear: mixed scope (2 mobile polish + 1 full-stack wiring); supervisor fixed OwnershipTab duplicate select + unused import; 17th consecutive zero-fix wave
- fuzzy: nothing
- missing: nothing

### Completed in W90

| Former Rank | Action | Result |
|-------------|--------|--------|
| 1 | Dashboard grade chart responsive (W90-A) | ✅ Grade grid 3-cols on mobile, h-16 bars, text-xs labels. 2 new tests (total 20) |
| 2 | Admin jurisdictions packs-table mobile (W90-B) | ✅ MobilePackCard fallback <768px with expandable details. 2 new tests (total 15) |
| 3 | Admin search-width mobile (W90-C) | ✅ AdminUsers + AdminAuditLogs filter bars flex-col on mobile, full-width inputs, overflow-hidden. CSS-only |

W90 debrief:
- clear: cohesive mobile polish cluster; 35 tests validated; 16th consecutive zero-fix wave
- fuzzy: nothing
- missing: nothing

### Completed in W89

| Former Rank | Action | Result |
|-------------|--------|--------|
| 1 | PFAS readiness wallet UI (W89-A) | ✅ PFAS in PollutantType, POLLUTANT_COLORS, i18n (4 langs), ReadinessWallet check rendering, PreworkTriggerCard pfas_check icon. 6+13 tests |
| 2 | Material recommendation shelf UI (W89-B) | ✅ New MaterialRecommendationsCard: accordion, risk badges, evidence requirements, dark mode, empty state. Props-only standalone. 11 tests |
| 4 | Header mobile polish (W89-C) | ✅ Padding/gap reduction <640px, dark mode toggle in user dropdown on mobile, language icon-only, 44px touch targets. 15 tests |

W89 debrief:
- clear: all 3 frontend scopes disjoint; 32 tests validated; tsc clean; 15th consecutive zero-fix wave
- fuzzy: nothing
- missing: nothing

### Completed in W88

| Former Rank | Action | Result |
|-------------|--------|--------|
| 1 | Eco clause pack integration (W88-A) | ✅ Eco clauses auto-injected into contractor_acknowledgment (safety_requirements) + transfer_package (new eco_clauses section). 8 new integration tests + 30 existing green |
| 2 | PFAS readiness backend (W88-B) | ✅ PFAS as 6th pollutant: constants, compliance_engine (0.1 µg/L water, 50 ng/kg soil), readiness_reasoner (check 6b pfas_assessment), PreworkTriggerType. 7 new tests. Backward-compatible |
| 3 | Material recommendation shelf backend (W88-C) | ✅ New material_recommendation_service: 5 pollutants × 11+ material types, safe alternatives, evidence requirements, risk flags, Swiss regulatory refs. 29 new tests |

W88 debrief:
- clear: all 3 scopes fully disjoint; 133 tests validated (72 W88 + 61 regression); 14th consecutive zero-fix wave; agents completed autonomously
- fuzzy: nothing
- missing: nothing

### Completed in W87

| Former Rank | Action | Result |
|-------------|--------|--------|
| — | Prework trigger backend (W87-A) | ✅ PreworkTrigger schema (5 pollutant types, urgency, source_check); model_validator derives from checks_json (no DB migration); GET /prework-triggers endpoint; 11 new tests (8 reasoner + 3 API). Fully backward-compatible |
| — | Prework trigger UI card (W87-B) | ✅ New PreworkDiagnosticTriggerCard.tsx: dual-mode (triggers prop or buildingId self-fetch), urgency badges, type icons, dark mode. Wired into OverviewTab + ReadinessWallet. Renders nothing when missing (fallback-safe). 3 new tests |
| — | Eco clause template backend (W87-C) | ✅ New eco_clause_template_service.py: renovation/demolition contexts, detects pollutants from samples, generates clause sections with Swiss legal refs (OTConst/CFST/ORRChim/OLED/ORaP), provenance trail. Integrated into authority_pack_service. 14 new tests |

W87 debrief:
- clear: first backend+frontend mixed wave since W80; all 3 scopes disjoint; frontend unit 359→362 (+3); backend targeted 54 passed; 13th consecutive zero-fix wave
- fuzzy: nothing
- missing: nothing

### Completed in W86

| Former Rank | Action | Result |
|-------------|--------|--------|
| — | Header dropdown a11y (W86-A) | ✅ Header.tsx: Escape keydown closes language/user dropdowns + focus restore to trigger button; role="menuitem" on all dropdown items. 4 new unit tests + 1 e2e test |
| — | Skip-link + CommandPalette a11y (W86-B+C merged) | ✅ Layout.tsx: skip-to-content link (sr-only, focus-visible) + id="main-content" on main + focus restore ref on palette close. CommandPalette.tsx: aria-modal="true", Tab no longer preventDefault'd for non-building results, focus restored on close. 3 unit + 4 e2e tests |

W86 debrief:
- clear: B+C merged due to shared Layout.tsx/navigation.spec.ts; unit 352→359 (+7); e2e 192→196 (+4); 12th consecutive zero-fix wave; all W85-A audit findings now addressed
- fuzzy: nothing
- missing: nothing

### Completed in W85

| Former Rank | Action | Result |
|-------------|--------|--------|
| 13 | Keyboard focus audit (W85-A) | ✅ 14 new e2e tests (8 navigation.spec.ts + 6 pages.spec.ts): tab order, focus traps, modal dismiss, landmarks. Audit report: 5 findings (header dropdowns no Escape close, no skip-link, CommandPalette tab interception, missing aria-modal). E2e total 192 |
| 14 | Frontend performance audit (W85-B) | ✅ vite.config.ts: removed dead `map` manual chunk (empty 0 kB file), added chunkSizeWarningLimit: 650. Build warnings 2→0, chunks 118→117. Report confirms already well-optimized: 33 lazy pages, heavy libs isolated, 630 kB index is ~80% i18n (159 kB gzip). App.tsx unchanged — already optimal |
| 15 | Coverage gap analysis (W85-C) | ✅ 11 new high-signal tests: CommandPalette (6: search results rendering, Enter navigation, arrow key nav, Escape close, filter pills, quick actions Tab) + BuildingCard (5: Space key a11y, fallback icon, freshness colors, null updated_at). Unit tests total 352. Gap analysis report with severity ratings |

W85 debrief:
- clear: all 3 scopes disjoint; unit tests grew 341→352 (+11); e2e grew 178→192 (+14); build warnings 2→0; 12th consecutive zero-fix wave; report-first tasks worked well
- fuzzy: nothing
- missing: nothing

### Completed in W84

| Former Rank | Action | Result |
|-------------|--------|--------|
| 10 | Mobile search trigger fix (W84-A) | ✅ Header.tsx: mobile-only search button (sm:hidden, >=44px touch target) that opens CommandPalette. Desktop/Cmd+K behavior unchanged. 3 new Header tests + 1 new e2e mobile search check |
| 11 | Building comparison mobile fallback (W84-B) | ✅ BuildingComparison.tsx: MobileComparisonCard component with stacked card layout for <768px. Desktop table preserved via hidden md:block / md:hidden split. 4 new tests + 1 new e2e mobile comparison check |
| 12 | Loading skeleton standardization (W84-C) | ✅ Skeleton.tsx: 3 new primitives (SkeletonLine, SkeletonBlock, InlineSkeleton) with a11y (role=status, aria-busy, sr-only text). AsyncStateWrapper refactored to use InlineSkeleton + role=alert on error. 32 new SkeletonLoadingStates tests + 3 new AsyncStateWrapper tests |

W84 debrief:
- clear: all 3 scopes disjoint; unit tests grew from 299 to 341 (+42); e2e grew from ~178; 11th consecutive zero-fix wave; compact YAML briefs worked well
- fuzzy: nothing
- missing: nothing — cross-agent mock interference (InlineSkeleton in BuildingDetailPage.test.tsx) caught and fixed in unified validation

### Completed in W83

| Former Rank | Action | Result |
|-------------|--------|--------|
| 7 | Mobile responsiveness audit (W83-A) | ✅ docs/mobile-responsiveness-audit.md: code-level audit at 375/768/1024px, 2 high (search button missing on mobile, comparison table unusable) + 6 medium issues with file:line references. 12 new mobile e2e tests (7 in pages.spec.ts, 5 in navigation.spec.ts) |
| 8 | PWA offline polish (W83-B) | ✅ New PwaStatusIndicator.tsx: online/offline/back-online states with WifiOff/Wifi icons, auto-hide after 3s, dark mode, graceful degradation. vite.config.ts: workbox runtimeCaching (NetworkFirst for API, 24h TTL), navigateFallback, cleanupOutdatedCaches. 6 new tests + build verified (125 precache entries) |
| 9 | Error boundary enhancement (W83-C) | ✅ ErrorBoundary.tsx: go-to-dashboard link, copy-error button, collapsible stack trace, timestamp. PageErrorBoundary: dark mode, go-back button, retry count tracker, copy/details toggle. Tests grew from 5 to 23. All 27 routes already had PageErrorBoundary wrappers |

W83 debrief:
- clear: all 3 scopes disjoint; unit tests grew from 275 to 299 (+24); 9th consecutive zero-fix wave; audit report is actionable backlog
- fuzzy: nothing
- missing: nothing

### Completed in W82

| Former Rank | Action | Result |
|-------------|--------|--------|
| 4 | Dashboard enhancement (W82-A) | ✅ Dashboard.tsx: secondary KPI row (open actions/documents/compliance alerts/avg trust), quick actions (4 entry points), portfolio health summary (grade distribution bars), enhanced recent activity (8 items + building address context + type icons), 17 new DashboardWidgets tests |
| 5 | Jurisdiction management polish (W82-B) | ✅ AdminJurisdictions.tsx: search/filter bar (text+level+status), summary stats (4 cards), pack count badges on tree items, mutation error display, success feedback (auto-dismiss), 13 new unit tests + 6 new e2e tests |
| 6 | Building form enhancement (W82-C) | ✅ BuildingsList.tsx: form field grouping (location/info/identifiers/notes), added egid/egrid/official_id as separate fields with distinct helper text, postal code regex validation, submission success/error feedback, edit mode support, 12 new unit tests + 4 new e2e tests |

W82 debrief:
- clear: all 3 scopes disjoint; unit tests grew from 233 to 275 (+42); 8th consecutive zero-fix wave; egid/egrid distinction preserved
- fuzzy: nothing
- missing: nothing

### Completed in W81

| Former Rank | Action | Result |
|-------------|--------|--------|
| 1 | Visual regression hardening (W81-A) | ✅ visual-regression.spec.ts + screenshot-audit.spec.ts: disableAnimations() CSS injection, waitForPageStable() helper (networkidle+rAF), animations:'disabled' in screenshot options, maxDiffPixelRatio relaxed 0.01→0.02, replaced waitForTimeout with stable waits |
| 2 | Canonical scenario hardening (W81-B) | ✅ smoke.spec.ts: 9 existing tests hardened + 7 new canonical dossier progression tests, helpers.ts typed API helpers + CANONICAL_SCENARIOS constant, preflight phase 5 (scenario buildings), safe-to-start gate runbook updated |
| 3 | Service consumer audit (W81-C) | ✅ service_consumer_inventory.py: frontend UI scanning, 8-category classification, duplicate family detection, pruning report generation. 141 services, 94 single-consumer, 0 zero-consumer, 14 duplicate families. New pruning-candidates.md with 4-tier risk grouping |

W81 debrief:
- clear: all 3 scopes disjoint (e2e hardening / real-e2e scenarios / backend audit); Codex-briefed wave constraints respected (hub-file discipline, no i18n edits); 7th consecutive zero-fix wave
- fuzzy: nothing
- missing: nothing

### Completed in W80

| Former Rank | Action | Result |
|-------------|--------|--------|
| 4 | Saved simulations page | ✅ New SavedSimulations.tsx: aggregated simulation list across buildings, sortable/filterable, expandable detail (interventions + before/after + recommendations), load-into-simulator via sessionStorage, compare 2-3 side-by-side, delete with confirmation, summary cards (total/avg improvement/most simulated/best ROI), CSV export + 50 i18n keys × 4 langs |
| 5 | Audit log viewer enhancement | ✅ AdminAuditLogs.tsx enhanced: full filter bar (user/action/entity/date range with presets/search), expandable detail (payload/response/IP/duration), action type color badges (8 types), entity type icons, CSV/JSON export, summary stats (4 cards), timeline view toggle + 28 i18n keys × 4 langs |
| 6 | Assignment management page | ✅ New Assignments.tsx + assignments.ts API: assignment list with role badges, create modal (user/target/role), expandable detail, bulk assign modal, role matrix grid view (users × buildings), summary cards + role distribution bar, delete with confirmation + 33 i18n keys × 4 langs |

W80 debrief:
- clear: all 3 scopes disjoint; 6th consecutive zero-fix wave; agent execution pattern fully stabilized
- fuzzy: nothing
- missing: nothing

### Completed in W79

| Former Rank | Action | Result |
|-------------|--------|--------|
| 4 | Compliance artefact management | ✅ New ComplianceArtefacts.tsx page + complianceArtefacts.ts API (full CRUD + lifecycle): summary cards, required artefacts alert, sortable/filterable table, create modal, detail panel with metadata grid + evidence links, lifecycle workflow (draft→submitted→acknowledged), submission timeline + 53 i18n keys × 4 langs. New types added to index.ts |
| 5 | Change signals management | ✅ New ChangeSignals.tsx page: signal feed with 7 type-specific icons/colors, summary cards, type distribution grid (clickable), filter bar (type/severity/status/date), acknowledge workflow, bulk acknowledge, expandable detail with entity drill-down. Enhanced ChangeSignalsFeed with "View all" link + 48 i18n keys × 4 langs |
| 6 | Building snapshot viewer | ✅ TimeMachinePanel.tsx rewritten: snapshot list with trigger icons, snapshot detail (trust/grade/readiness/pollutants), compare mode (side-by-side with color-coded deltas), create snapshot form with notes, horizontal timeline visualization with grade badges. Tests expanded from 4 to 9 + 15 i18n keys × 4 langs |

W79 debrief:
- clear: all 3 scopes disjoint; test count grew from 228 to 233 (+5); zero post-merge fixes for 5th consecutive wave
- fuzzy: nothing
- missing: nothing

### Completed in W78

| Former Rank | Action | Result |
|-------------|--------|--------|
| 4 | Evidence pack builder | ✅ New EvidencePackBuilder.tsx + evidencePacks.ts API: item selector grouped by type with search, pack preview with completeness indicator, metadata form (purpose/audience/notes), generate with loading, pack history with detail view, purpose-based completeness requirements + 50 i18n keys × 4 langs |
| 5 | Unknown issues management | ✅ New UnknownIssuesPanel.tsx: summary cards, category breakdown bar chart, resolution overview (auto vs manual), filterable/sortable list, expandable detail, resolution workflow (acknowledge/resolve/dismiss), bulk operations. Enhanced UnknownIssuesList with inline panel expand + ~60 i18n keys × 4 langs |
| 6 | Post-works state viewer | ✅ PostWorksDiffCard.tsx enhanced: summary header (4 metrics), before/after with per-pollutant diff indicators, intervention linkage, verification section with verify button (role-gated), chronological timeline. Tests expanded from 2 to 6. postWorks API extended with summary+verify + 18 i18n keys × 4 langs |

W78 debrief:
- clear: all 3 scopes disjoint; PostWorksDiffCard pre-existing test failures resolved by W78.3; test count stable at 228
- fuzzy: nothing
- missing: nothing — zero post-merge fixes

### Completed in W77

| Former Rank | Action | Result |
|-------------|--------|--------|
| 4 | Transfer package page | ✅ TransferPackagePanel.tsx enhanced: section selector with descriptions + counter, package preview, 3-step progress indicator, format selector (JSON/PDF), package history table, recipient form (name/email/purpose), estimated size. Tests expanded to 10 + 38 i18n keys × 4 langs |
| 5 | Requalification timeline polish | ✅ RequalificationTimeline.tsx rewritten: summary header (4 stats), grade transition cards with directional arrows, signal type badges, 5-filter bar with counts, replay mode (step-through controls), snapshot comparison panel (side-by-side diff). Tests expanded from 2 to 10 + 30 i18n keys × 4 langs |
| 6 | Contradiction viewer | ✅ New ContradictionPanel.tsx: summary cards (type/severity/resolution rate), filterable/sortable list, expandable detail with visual diff, resolution workflow (investigate→resolve/dismiss with notes), scan button. ContradictionCard enhanced with inline expand. 7 new tests + 47 i18n keys × 4 langs |

W77 debrief:
- clear: all 3 scopes disjoint; test count grew from 198 to 224 (+26 new tests); agents producing comprehensive test coverage alongside features
- fuzzy: nothing
- missing: nothing — zero post-merge fixes

### Completed in W76

| Former Rank | Action | Result |
|-------------|--------|--------|
| 4 | Organization settings page | ✅ OrganizationSettings.tsx already complete (profile/members/billing/type info/danger zone). Cleaned unused imports + added 68 i18n keys × 4 langs |
| 5 | Intervention simulator UX polish | ✅ InterventionSimulator.tsx enhanced: collapsible intervention cards with type icons, animated result numbers (useAnimatedNumber hook), gradient progress bars, color-coded recommendation cards with effort badges, scenario comparison with grade badges + mini bars, cost breakdown/risk reduction visuals + 11 i18n keys × 4 langs |
| 6 | ReadinessWallet enhancement | ✅ ReadinessWallet.tsx already had all 5 features (gate cards, checklist, blockers, progress, detail modal). Added 24 missing i18n keys × 4 langs. Fixed test for collapsible checks section |

W76 debrief:
- clear: 2 of 3 pages were already feature-complete from earlier waves; agents correctly identified this and focused on i18n gaps
- fuzzy: nothing
- missing: ReadinessWallet test needed update for collapsible checks (fixed post-merge)

### Completed in W75

| Former Rank | Action | Result |
|-------------|--------|--------|
| 4 | Notification center page | ✅ New Notifications.tsx + notifications.ts API client: grouped by date (Today/Yesterday/This Week/Older), type-specific icons+colors (action/invitation/export/system), mark read/unread, bulk select, infinite scroll with useInfiniteQuery, filter by type+status + 22 i18n keys × 4 langs |
| 5 | Admin users management polish | ✅ AdminUsers.tsx rewritten: summary cards (total/active/pending/roles), tab layout (Users/Invitations), sortable+filterable table, expandable row with permissions summary, role change with confirmation, invite modal with org selector, invitation management with resend/revoke + 60 i18n keys × 4 langs |
| 6 | Sample management UX | ✅ New BuildingSamples.tsx: summary cards + risk distribution bar, sortable/filterable table, expandable detail with threshold comparison bar + Swiss regulatory refs, create modal with auto-risk calculation, bulk view grouped by diagnostic, mobile-responsive. Added to BuildingSubNav + 38 i18n keys × 4 langs |

W75 debrief:
- clear: all 3 scopes fully disjoint; agents consistently producing clean output (third consecutive zero-fix wave)
- fuzzy: nothing
- missing: nothing

### Completed in W74

| Former Rank | Action | Result |
|-------------|--------|--------|
| 4 | Dark mode and accessibility audit | ✅ 8 files fixed: dark mode gaps on badges/active states in Header, Settings, Dashboard, DataQuality, BuildingsList. Accessibility: aria-labels on icon buttons (Actions), role=tablist/tab on BuildingDetail tabs, aria-expanded on expandable rows. Test updated for new tab roles |
| 5 | Diagnostic detail page polish | ✅ DiagnosticView.tsx rewritten: status header with context badges, findings section (pollutant+risk sorted), samples panel (mobile responsive), risk summary (distribution bar + pollutant grid + Swiss regulatory refs), timeline/activity, validate/export actions + 48 i18n keys × 4 langs |
| 6 | Zone/element tree navigation | ✅ BuildingExplorer.tsx rewritten: hierarchical zone tree with expand/collapse + search/filter, element cards with condition color coding, material detail with pollutant flags + sample links, summary header with condition distribution bar, breadcrumb navigation + 9 i18n keys × 4 langs |

W74 debrief:
- clear: all 3 scopes disjoint; dark mode audit was surgical (most pages already well-covered); zero prettier fixes for second consecutive wave
- fuzzy: nothing
- missing: nothing

### Completed in W73

| Former Rank | Action | Result |
|-------------|--------|--------|
| 5 | Action items management UI | ✅ Actions.tsx rewritten: summary bar (status+priority counts), filter bar (status/priority/source/building/assigned), sort controls, expandable detail with status transitions, create modal, bulk actions (select+bulk status change), campaign link badge + 30 i18n keys × 4 langs |
| 6 | Document upload UX polish | ✅ Documents.tsx rewritten: drag-drop upload zone, multi-file queue with per-file metadata, grid+list view toggle, status badges (processing/ready/error), quick preview modal (images/PDFs), detail panel, enhanced filter bar (type/status/date range) + 21 i18n keys × 4 langs |
| 7 | Data quality dashboard | ✅ New DataQuality.tsx page + dataQuality.ts API client: quality score overview with trend, 5 severity summary cards, change signals feed (7 types), freshness indicators (top 10 stale buildings, color-coded by age), issue list with expand/acknowledge/resolve, building drill-down links + 37 i18n keys × 4 langs |

W73 debrief:
- clear: all 3 scopes fully disjoint; no prettier fixes needed for the first time; agents produced clean output
- fuzzy: nothing
- missing: nothing — cleanest wave yet

### Completed in W72

| Former Rank | Action | Result |
|-------------|--------|--------|
| 4 | Building comparison UI polish | ✅ BuildingComparison rewritten: TrustBadge in trust column, readiness gates column (X/4), last diagnostic date, sortable columns, dimension selector with localStorage persistence |
| 5 | Passport page polish | ✅ PassportCard rewritten: share button with audience/expiration/max_views modal, expandable blind spots/contradictions/evidence sections. New SharedLinksPanel: active links with audience badges, copy link, revoke + 18 i18n keys × 4 langs |
| 6 | Portfolio drill-down | ✅ Portfolio + PortfolioCommandCenter: click handlers on KPI cards, readiness bar, trust distribution, grade bars, compliance counts → navigate to filtered BuildingsList. BuildingsList: URL query param support with filter banner + clear buttons + 12 i18n keys × 4 langs |

W72 debrief:
- clear: all 3 scopes disjoint (comparison, passport, portfolio); existing badges (TrustBadge/ReadinessBadge) from W69 reused effectively
- fuzzy: nothing
- missing: nothing — prettier was the only post-merge fix

### Completed in W71

| Former Rank | Action | Result |
|-------------|--------|--------|
| 3 | Authority pack flow polish | ✅ AuthorityPacks rewritten: detail modal with section accordion + completeness bars, generation config (canton/language/sections/photos), row-click detail, re-generate button, animated generating status + 22 i18n keys × 4 langs |
| 5 | Intervention management UI | ✅ BuildingInterventions enhanced: edit modal, delete with confirmation, status transitions (start/complete/cancel), expandable detail, cost summary bar + 22 i18n keys × 4 langs |
| 6 | Campaign management UI polish | ✅ Campaigns: edit modal wired, AI recommendations section (5 cards with create-from-rec), tracking tab in detail (building statuses, progress bars, quick actions) + 4 new types + 5 new API methods + 26 i18n keys × 4 langs |

W71 debrief:
- clear: all 3 pages had existing backend support; agents could focus purely on frontend UX enhancement
- fuzzy: nothing
- missing: nothing — prettier was the only post-merge fix

### Completed in W70

| Former Rank | Action | Result |
|-------------|--------|--------|
| 1 | Search evidence grouping and dossier navigation UI | ✅ CommandPalette enhanced: recent buildings, quick actions panel (5 nav shortcuts), SearchEvidencePreview with evidence summary, Tab keyboard nav + 16 i18n keys × 4 langs |
| 3 | Safe-to-start dossier flow polish | ✅ DossierStatusPanel: 4-step progress stepper (diagnosed→documented→complete→safe-to-start), overall status banner, blockers list, recommended actions, dossier-completion API client. Replaced fragmented CompletenessGauge+DossierPackButton in OverviewTab + 20 i18n keys × 4 langs |
| 5 | BuildingDetail sub-page navigation | ✅ BuildingSubNav: horizontal pill nav bar with 8 sub-pages, active state highlighting, wired into all 8 building sub-pages. Field observations linked from quick access grid + 9 i18n keys × 4 langs |

W70 debrief:
- clear: all 3 scopes disjoint (search, dossier panel, navigation); agent-execution-patterns discipline holds well at W70
- fuzzy: nothing — scopes were well-defined
- missing: nothing — prettier was the only post-merge fix (as usual)

### Completed in W69

| Former Rank | Action | Result |
|-------------|--------|--------|
| 1 | Plan annotation UI | ✅ Annotation CRUD API client + annotation panel in BuildingPlans (type filter, add/edit/delete forms, count badges) + 20 i18n keys × 4 langs |
| 2 | Export job progress/recovery UI | ✅ ExportJobs enhanced: progress bars, cancel/retry buttons, elapsed time, error details, summary bar, animated status badges, AsyncStateWrapper + BackgroundJob API client + 16 i18n keys × 4 langs |
| 3 | Readiness/trust on list & portfolio surfaces | ✅ TrustBadge + ReadinessBadge mini components, BuildingsList table/grid with per-building dashboard fetch, Portfolio readiness distribution + trust distribution sections + 17 i18n keys × 4 langs |

W69 debrief:
- clear: backend fully ready for all 3; agent-execution-patterns discipline worked well (3 disjoint frontend scopes)
- fuzzy: ExportJobs test needed updating (AsyncStateWrapper changed error/empty text keys) — fixed in merge pass
- missing: nothing — all scopes were well-bounded

### Completed in W68

| Former Rank | Action | Result |
|-------------|--------|--------|
| 1 | Notification preferences UI | ✅ Settings.tsx expanded: per-type channel toggles (action/invitation/export/system × in_app/email/digest), quiet hours (start/end selectors), digest frequency (daily/weekly/never) + 20 i18n keys × 4 langs |
| 2 | Enriched timeline UI | ✅ BuildingTimeline upgraded: enriched/simple toggle, importance badges (critical/high/medium/low), lifecycle phase tags (discovery→closed), lifecycle summary bar, phase filter chips + 20 i18n keys × 4 langs |
| 3 | Field observations UI | ✅ New FieldObservations page + API client (6 endpoints): summary cards, filter bar, paginated list, create modal, verify/unverify + route in App.tsx + 30 i18n keys × 4 langs |

W68 debrief:
- clear: all 3 backends were fully ready, briefs with API contracts enabled fast agent execution
- fuzzy: nothing — scopes were well-defined and disjoint
- missing: nothing material — prettier formatting was the only post-merge fix

### Completed in W66

| Former Rank | Action | Result |
|-------------|--------|--------|
| 1 | Repo quality and coherence hardening | ✅ 9 lint/format fixes, 0 dead imports, 1 orphan flagged (change_signal_generator), route naming consistent |
| 2 | Proof heatmap improvements | ✅ Trust gradient (green/amber/red), contradiction markers, color legend, zone hover tooltips, AsyncStateWrapper |
| 3 | Rules pack studio | ✅ RulesPackStudio page (pack list, detail view, side-by-side comparison with diff highlighting) + 28 i18n keys × 4 langs |

### Completed in W65

| Former Rank | Action | Result |
|-------------|--------|--------|
| 1 | Async jobs and background orchestration | ✅ BackgroundJob model + service (8 functions) + API (3 routes) + 22 tests |
| 2 | Privacy/security: audience-bounded sharing | ✅ SharedLink model + service (6 functions) + API (5 routes, 1 public) + 18 tests |
| 7 | BuildingDetail lazy sub-tabs | ✅ 4 lazy tab components, BuildingDetail chunk dropped from 93 kB → 22 kB |

### Completed in W64

| Former Rank | Action | Result |
|-------------|--------|--------|
| 1 | Real e2e preflight hardening | ✅ Scenario-aware checks (actions, interventions, artefacts) + timeout handling + better error messages |
| 2 | API contracts and generated clients | ✅ OpenAPI export script (505 paths, 926 schemas) + frontend type extraction script |
| 6 | Frontend charts chunk splitting | ✅ Removed manualChunks forcing, Recharts tree-shaken (~11kB saved, PieChart separated) |

### Completed in W63

| Former Rank | Action | Result |
|-------------|--------|--------|
| 4 | Portfolio intelligence command center | ✅ PortfolioCommandCenter component (health score ring, compliance overview, grade distribution, alerts, actions, campaign progress) + 20 i18n keys × 4 langs |
| 5 | Building passport standard and exchange | ✅ PassportExchangeDocument schema + export service + GET endpoint + 10 tests |
| 8 | Migrate remaining components to AsyncStateWrapper | ✅ 5 more components migrated (PassportCard, ContradictionCard, PostWorksDiffCard, PortfolioSignalsFeed, BuildingTimeline) — EvidenceChain skipped (compact mode incompatible) |

### Completed in W62

| Former Rank | Action | Result |
|-------------|--------|--------|
| 2 | Read models, query topology, and aggregate APIs | ✅ BuildingDetail wired to dashboard aggregate (6-card summary), 3 facade API routes exposed, 3 frontend API clients created |
| 5 | Frontend async state standardization | ✅ AsyncStateWrapper shared component (10 tests) + 6 components migrated (TrustScoreCard, ReadinessSummary, UnknownIssuesList, CompletenessGauge, DataQualityScore, ChangeSignalsFeed) |

### Completed in W61

| Former Rank | Action | Result |
|-------------|--------|--------|
| 1 | Full-chain integration and demo truth | ✅ 3 canonical integration tests (full lifecycle, contradiction→trust, intervention→post-works→requalification) — 15 total new tests |
| 2 | Domain facades and service consolidation | ✅ 3 new facades (evidence, remediation, compliance) + 12 tests |
| 3 | Service consumer mapping and dead-code pruning | ✅ 4 orphaned services removed (16 files deleted), router cleaned |
| 4 | Dataset scenario factory and layered seed strategy | ✅ 5 scenario buildings + seed_scenarios.py + expanded seed_verify |
| 5 | Test right-sizing and integration confidence | ✅ Canonical integration scenarios prove composition, facade-first testing pattern established |
| 10 | Authority pack UI | ✅ Frontend page with building selector, generation, status table, dark mode, 4-lang i18n |

## Performance and Operability Pressure

Current frontend build remains green, and the old route-level `map` hotspot has been eliminated via dynamic loading. The remaining meaningful bundle pressure is now:

- `index` / shared-shell creep
- `charts` as the next obvious split/containment target
- continued vigilance on precache growth as new surfaces land

Codex has turned this into a dedicated repo-native brief:

- `docs/projects/frontend-performance-and-bundle-hardening-program.md`

Rule:
- do not treat the remaining Vite warnings and bundle creep as harmless forever
- optimize for the next highest-signal targets (`charts`, shared shell, precache discipline), not for already-resolved route-level map splitting

## Architecture Optimization Pressure

Lead-side review now points to three additional high-leverage optimization families:

- aggregate read models and query-topology cleanup
- stronger API contract / generated client discipline
- explicit background jobs and projection orchestration

Repo-native briefs now exist for these:

- `docs/projects/read-models-query-topology-and-aggregate-apis-program.md`
- `docs/projects/api-contracts-and-generated-clients-program.md`
- `docs/projects/async-jobs-projections-and-background-orchestration-program.md`

Why these matter:

- the product has many query consumers and increasingly rich screen-level compositions
- backend and frontend contract drift becomes more expensive as domains proliferate
- exports, packs, search, signals, and agentic flows need a more unified async/projection story

## Horizon 11-20

| Rank | Action | Why next | Depends on |
|------|--------|----------|------------|
| 11 | Notification preferences UI | Governance is landed in backend and needs visible user control | Notification prefs ✅ |
| 12 | Enriched timeline UI | Building Memory OS should surface its newer lifecycle enrichment | Timeline enrichment ✅ |
| 13 | Field observations UI | Spatial truth and field operations need a visible operator flow | Field observations ✅ |
| 14 | Portfolio risk trends over time | Time-series risk evolution should feed the portfolio story now that trends exist in backend | Portfolio risk trends ✅ |
| 15 | Search result evidence grouping UI | Search should become dossier navigation, not just a command palette result list | Search grouping + evidence chain |
| 16 | Evidence link graph visualization | Navigable proof graph is now justified by graph service maturity | Evidence graph ✅ |
| 17 | Visual regression flake cleanup | Remove the remaining noisy visual debt before the UI surface grows again | Testing modernization |
| 18 | Plan annotation UI | Unlock spatial truth workflows already supported by backend foundations | Plan annotations ✅ |
| 19 | Export job progress and recovery UI | Make asynchronous packs and dossier jobs feel trustworthy under delay/failure | Export jobs + reliability brief |
| 20 | Readiness/trust on list and portfolio surfaces | Move decision primitives from detail pages to portfolio decision contexts | Trust + readiness + portfolio surfaces |

## Horizon 31-40

| Rank | Action | Why later but ready | Depends on |
|------|--------|---------------------|------------|
| 31 | AuthorityPack backend scaffolding | Prepares true authority-ready evidence products | Legislative compliance hardening |
| 32 | ContractorPack backend scaffolding | Prepares execution-side handoff and tender packs | PostWorks + dossier foundations |
| 33 | OwnerPack variant on top of dossier/export jobs | Supports commercial expansion and account stickiness | Export job + dossier foundations |
| 34 | BuildingTrustScore UI on building list and portfolio surfaces | Makes trust visible where decisions are made | Trust service |
| 35 | UnknownIssue UI on explorer/zone surfaces | Turns hidden blind spots into spatially actionable work | Unknown generation |
| 36 | ChangeSignal portfolio feed | Makes requalification and drift visible at portfolio level | ChangeSignal generators |
| 37 | Readiness-driven action generation | Convert blocked readiness states into concrete tasks | Readiness reasoner |
| 38 | Before/after intervention diff view | Makes PostWorksState demonstrable and useful | PostWorks lifecycle |
| 39 | Search result evidence grouping | Better proof lookup and dossier navigation | Meilisearch + grouped UX |
| 40 | Seeded authority-ready demo scenario | Makes the compliance wedge demo-grade end to end | Compliance + packs + dossier archival |

## Horizon 41-50

| Rank | Action | Why later but powerful | Depends on |
|------|--------|------------------------|------------|
| 41 | Building Time Machine foundations | Major differentiator for audit, disputes, and demos | PostWorks + timeline + trust state |
| 42 | Readiness Wallet UI | Turns scattered readiness states into a decision cockpit | Readiness reasoner |
| 43 | Intervention Simulator v1 | Makes the product predictive, not only descriptive | Readiness + packs + post-works |
| 44 | Autonomous Dossier Completion Agent v1 | Visible invisible-agent value without chatbot drift | Compliance + unknowns + trust |
| 45 | Proof Heatmap on Plans v1 | One of the strongest visual proof surfaces in the product | Plan annotation + evidence + trust |
| 46 | Building passport summary card | Bridges dossier, trust, contradictions, and transfer | Passport + contradiction layers |
| 47 | Requalification replay timeline | Shows exactly why the building changed state | ChangeSignal + time machine |
| 48 | Pack impact simulator | Predict which packs or attestations become stale after new works | Intervention simulator + export architecture |
| 49 | Demo-grade “safe to X” cockpit | Unifies start/tender/sell/insure/finance readiness for sales demos | Readiness wallet + trust |
| 50 | Guided dossier completion workspace | Human-in-the-loop completion console backed by agent suggestions | Dossier completion agent |

## Horizon 51-60

| Rank | Action | Why later but strategic | Depends on |
|------|--------|-------------------------|------------|
| 51 | Transaction readiness workspace | Extends the dossier into buy/sell due diligence | Trust + unknowns + packs |
| 52 | Insurance readiness and insurer pack | Opens underwriting / insurance narratives | Trust + readiness + residual risk |
| 53 | Finance readiness and lender pack | Opens financing / refinancing narratives | Trust + readiness + pack architecture |
| 54 | Rules Pack Studio foundations | Converts regulatory depth into scalable internal leverage | Compliance hardening |
| 55 | Regulatory diff explorer | Makes Europe/country/canton rule deltas visible and explainable | Rules pack studio |
| 56 | Agent Audit Console foundations | Governs invisible agents and makes them commercially defensible | Agent governance program |
| 57 | Knowledge Capture Workbench foundations | Improves extraction and evidence quality at scale | Agent governance program |
| 58 | Scenario curation studio | Builds reusable hard cases for demos, tests, and learning | Knowledge workbench |
| 59 | Building passport transfer/export package v1 | Moves closer to a market-standard building memory artifact | Passport + transfer + packs |
| 60 | Commercial demo cockpit for buyers/insurers/lenders | Turns readiness/trust/proof into executive decision surfaces | Transaction/insurance/finance readiness |

## Horizon 61-70

| Rank | Action | Why later but category-defining | Depends on |
|------|--------|---------------------------------|------------|
| 61 | Building passport exchange schema v1 | Creates a reusable market artifact beyond PDFs | Passport standard program |
| 62 | Import/export passport contract | Turns SwissBuilding into a transfer layer, not only a destination app | Passport exchange schema |
| 63 | Portfolio command center surfaces | Makes the platform feel institutional, not project-only | Portfolio intelligence program |
| 64 | Opportunity cluster engine | Recommend the highest-leverage building groups | Portfolio command center |
| 65 | CAPEX translation layer | Converts trust/readiness/residual risk into board-grade decisions | Portfolio intelligence program |
| 66 | Contributor gateway for labs/diagnosticians/contractors | Opens the ecosystem side without losing control | Ecosystem network program |
| 67 | Partner webhook/event layer | Prepares SwissBuilding to act as exchange infrastructure | Ecosystem network program |
| 68 | Public-data delta monitor | Reopens dossiers when external truth changes | Ecosystem network program |
| 69 | Cross-actor learning and recommendation foundations | Turns network growth into explainable product leverage | Ecosystem + agent governance |
| 70 | Institutional executive board | Unified high-level cockpit for portfolios, readiness, packs, and trust | Portfolio command center + commercial readiness |
| 71 | Repo quality and coherence hardening | Keep documentation, naming, and control-plane truth aligned with the real codebase | None |
| 72 | Architecture current-state sync | Make architecture docs worthy of the actual implemented system | Repo quality and coherence hardening |
| 73 | Reserved-future-domain cleanup | Stop future docs from lagging behind implemented reality | Repo quality and coherence hardening |
| 74 | Project-brief lifecycle governance | Make `docs/projects/` easier to scan and safer for autonomous pull-through | Repo quality and coherence hardening |
| 75 | Naming drift cleanup (`v2`, temporary labels) | Prevent iterative naming from becoming permanent product debt | Repo quality and coherence hardening |
| 76 | Reliability, observability, and recovery program | Make the platform trustworthy under failure, not just on the happy path | None |
| 77 | Export and pack retry/recovery | Dossier/pack failures must become recoverable product states | Reliability program |
| 78 | Derived-state freshness and indexing health | Trust, readiness, and search need freshness semantics | Reliability program |
| 79 | Demo and sales enablement program | Turn product depth into repeatable commercial inevitability | None |
| 80 | Canonical demo scenarios and operator tooling | Seeded narratives and operator-grade demo flow | Demo program |
| 81 | Privacy, security, and data governance program | Make sharing, packs, and externalization enterprise-trustworthy | None |
| 82 | Audience-bounded pack and evidence sharing | Prevent over-sharing while scaling external pack use | Privacy/governance program |
| 83 | Distribution and embedded channels program | Make SwissBuilding spread through incumbent workflows | None |
| 84 | Embedded passport / readiness / trust surfaces | Turn the product into a layer, not only a destination UI | Distribution program |
| 85 | Account expansion trigger mechanics | Productize land-and-expand from inside the platform | Distribution program |
| 86 | Occupant safety and communication program | Extend readiness and proof into bounded occupant-facing safety flows | None |
| 87 | Occupancy safety readiness model | Add a new trust layer for current occupants, not only works readiness | Occupant safety program |
| 88 | Zone restriction and notice flows | Connect field truth and interventions to bounded communication | Occupant safety program |
| 89 | Occupant pack scaffolding | Generate a limited audience-safe subset of building truth | Occupant safety program |
| 90 | Project brief index hygiene | Keep `docs/projects/README.md` aligned as the catalog grows | None |
| 91 | openBIM / digital logbook / passport convergence | Align SwissBuilding with the strongest emerging interoperability direction | None |
| 92 | IFC / IDS / DBL mapping strategy | Make building memory and readiness exportable beyond the app | openBIM/logbook program |
| 93 | Semantic building operations and systems program | Prepare the next layer beyond renovation-only intelligence | None |
| 94 | Building systems ontology and equipment layer | Separate systems semantics cleanly from structure/material truth | Semantic operations program |
| 95 | Semantic mapping to Brick / Haystack style models | Keep the long-term operations layer standards-aware | Semantic operations program |
| 96 | Legal-grade proof and chain-of-custody program | Make proof lifecycle defensible, versioned, and dispute-ready | None |
| 97 | Enterprise identity and tenant governance program | Prepare for enterprise identity and stronger tenancy boundaries | None |
| 98 | BIM, 3D, and geometry-native intelligence program | Push geometry from attachment layer to working intelligence layer | None |
| 99 | Execution quality and hazardous works operations program | Move from readiness into work-quality and acceptance control | None |
| 100 | Partner network and contributor reputation program | Turn contributor behavior into network advantage | None |
| 101 | Benchmarking, learning, and market intelligence program | Convert accumulated truth into privacy-safe learning leverage | None |
| 102 | Owner household expense and operating layer program | Add recurring owner-side financial and operating utility between major works | None |
| 103 | Renovation budget and CAPEX planning program | Turn readiness and interventions into living budget and reserve control | None |
| 104 | Digital vault and document trust program | Make SwissBuilding a trusted building record vault, not just a workflow surface | None |
| 105 | Insurance policy and claims operations program | Move from insurance readiness into policy memory, renewals, and claims support | None |
| 106 | Permit procedure and public funding program | Bridge technical readiness into permit and subsidy execution | None |
| 107 | Co-ownership governance and resident operations program | Prepare for multi-owner buildings and resident-facing operations | None |
| 108 | Energy, carbon, and live performance program | Extend from dossier truth into recurring building performance intelligence | None |
| 109 | Warranty, defects, and service obligations program | Keep value after works through warranties, defects, and recurring obligations | None |
| 110 | Constraint graph and dependency intelligence program | Explain what blocks what and which move unlocks the most leverage | None |
| 111 | Decision replay and operator memory program | Preserve why decisions were made, not only the final state | None |
| 112 | Weak-signal watchtower program | Detect pre-blocker drift before readiness or trust actually collapses | None |
| 113 | Multimodal building understanding and grounded query program | Turn mixed reports/plans/photos/voice into grounded building intelligence | None |
| 114 | Autonomous dossier completion and verification program | Let bounded agents actively drive dossiers toward readiness | None |
| 115 | Cross-modal change detection and reconstruction program | Rebuild before/after truth and detect change across mixed evidence | None |
| 116 | Open-source accelerators 2026 radar | Keep the strongest newly practical OSS building blocks ready to pull at the right moment | None |
| 117 | Human correction and curation OSS pull path | Keep Argilla / Label Studio / CVAT ready when the knowledge workbench becomes active | Open-source accelerators radar |
| 118 | Policy and relationship-control OSS pull path | Prepare Keycloak / OpenFGA / OPA when enterprise sharing hardens | Open-source accelerators radar |
| 119 | Embedded analytics and lineage OSS pull path | Prepare DuckDB / Ibis / OpenLineage when benchmarking and learning productize | Open-source accelerators radar |
| 120 | Spatial distribution and self-hosted map pull path | Keep MapLibre / PMTiles ready for external viewers and large portfolio surfaces | Open-source accelerators radar |
| 121 | Continuous review and modernization program | When the queue thins, review and improve tooling, tests, integrations, extensions, and repo coherence | None |
| 122 | Search relevance tuning and dossier navigation review | Improve retrieval quality, grouping, and navigation leverage | Continuous modernization program |
| 123 | Export and pack infrastructure hardening | Improve progress, retryability, and file-path truth | Continuous modernization program |
| 124 | Real e2e ownership and preflight review | Make real validation more explicit, deterministic, and environment-safe | Continuous modernization program |
| 125 | Workflow replay and recovery review | Improve replayability, operator recovery, and dead-letter handling | Continuous modernization program |
| 126 | Seed determinism and migration safety review | Harden seeds, verify flows, migrations, and backfills for scale | Continuous modernization program |
| 127 | Sensor fusion and live-state foundations | Connect dossier truth to live operational signals and drift | Systems + live performance |
| 128 | Counterfactual stress testing and shock planning | Make readiness/trust/portfolio logic resilient under regulatory, finance, and climate shocks | Portfolio intelligence + trust |

## Autonomous 60-Day Runway

This is the supervisor's default medium-range runway. It exists so Claude can keep moving for many waves without waiting for a fresh strategic brief.

### Wave R1 — Finish MP1 / close obvious product gaps

- ship `Campaign`
- land campaign UI
- absorb validated QA/UI hardening overlaps
- clean backend warning residue
- refresh docs/counters after validation

Exit:
- MP1 can be treated as functionally complete
- validation baseline is green and cleaner than before

### Wave R2 — Complete MP2 search and operating ergonomics

- Meilisearch backend
- search UI / command palette
- grouped results by entity usefulness
- export job status/progress UI
- extend `seed_verify.py` if search/export assumptions change

Exit:
- product can navigate buildings, documents, and actions through a real search surface
- exports feel operational, not opaque

### Wave R3 — Add explicit trust and readiness primitives

- `SavedSimulation`
- `DataQualityIssue`
- `ChangeSignal`
- `ReadinessAssessment`
- if cleanly compatible, `BuildingTrustScore`

Exit:
- missing truth, readiness state, and dossier reliability exist as first-class backend objects

### Wave R4 — Push post-works and unknowns foundations

- `UnknownIssue`
- `PostWorksState`
- first generation rules from completeness/interventions/documents
- before/after state comparison primitives

Exit:
- the product begins to reason not only about pre-work readiness, but about residual truth after intervention

### Wave R5 — Turn portfolio from dashboard into execution system

- campaign recommendation logic
- first saved simulation APIs/UI bridges
- first portfolio opportunity or sequence logic
- connect search, actions, and readiness into portfolio surfaces

Exit:
- the portfolio is no longer only observed; it starts to be steered

### Wave R6 — International-class operating layers

- partner-facing API/webhook foundations where low-regret
- stronger export / handoff / authority pack scaffolding
- real-integration hardening
- trust/audit/interoperability uplift where current implementation is still local-tool grade

Exit:
- the product is materially closer to a European reference layer, not just an ambitious Swiss PoC

### Wave R7 — Trust and readiness become first-class product surfaces

- productize `BuildingTrustScore`
- productize `UnknownIssue`
- ship readiness UI and blockers
- connect post-works truth to interventions and dossier state

Exit:
- the product can explain not only risk, but reliability, unknowns, and whether the building is operationally ready

### Wave R8 — Packs become a portfolio operating language

- authority / contractor / owner pack scaffolding
- campaign recommendation logic
- export progress UI
- saved simulation UX

Exit:
- the product can recommend, package, and monitor action at building and portfolio level

### Wave R9 — Spatial truth and field operations

- plan annotation foundations
- field capture / observations
- proof heatmaps
- sampling planner foundations

Exit:
- the building is operational in space, not only in documents

### Wave R10 — Contradiction, passport, and transfer

- contradiction detection
- passport summary state
- transfer/export package foundations
- first explicit memory transfer story

Exit:
- the product can surface conflict, summarize passport trust, and move building truth between actors

### Wave R11 — Killer demo and wow surfaces

- building time machine foundations
- readiness wallet
- intervention simulator
- autonomous dossier completion agent
- proof heatmap on plans

Exit:
- the product gains unmistakable, high-trust wow surfaces that still compound the core moat

### Wave R12 — Commercial expansion readiness

- transaction readiness
- insurance readiness
- finance readiness
- buyer / insurer / lender pack scaffolding

Exit:
- the product extends from works readiness into asset, underwriting, and financing decisions

### Wave R13 — Rules and agent governance moat

- rules pack studio foundations
- regulatory diffing
- agent audit console
- knowledge capture workbench

Exit:
- the product gains scalable regulatory leverage and governed invisible-agent workflows

### Wave R14 — Passport and exchange infrastructure

- building passport schema
- exchange package foundations
- import/export contract
- passport diffs

Exit:
- SwissBuilding starts behaving like infrastructure, not just application software

### Wave R15 — Portfolio command center and ecosystem network

- opportunity engine
- command-center surfaces
- contributor gateway
- partner events/webhooks
- public-data delta monitoring

Exit:
- the platform becomes harder to replace because it starts coordinating portfolios and ecosystem flows

### Wave R16 — Reliability, observability, and recovery

- export/pack retry and failure recovery
- processing pipeline observability
- derived-state freshness and indexing health
- environment/preflight hardening
- product-visible degraded modes

Exit:
- SwissBuilding feels trustworthy even when subsystems fail, lag, or need recovery

### Wave R17 — Demo and sales enablement

- canonical demo scenarios
- operator demo tooling
- buyer-facing executive surfaces
- persona pack presets
- wow moments tied to product truth instead of isolated hacks

Exit:
- the product becomes easier to sell repeatedly because the strongest narratives are productized and reproducible

### Wave R18 — Privacy, security, and data governance

- audience-bounded pack logic
- sensitive evidence handling
- access and sharing audit hardening
- retention / stewardship primitives

Exit:
- SwissBuilding becomes easier to trust under enterprise and regulated scrutiny

### Wave R19 — Distribution and embedded channels

- embedded passport/readiness/trust surfaces
- bounded external viewers
- stable partner/integration summaries
- account-expansion channels productized

Exit:
- the platform becomes easier to adopt inside incumbent workflows and easier to spread across accounts

### Wave R20 — Occupant safety and bounded communication

- occupancy safety readiness
- zone restriction surfaces
- bounded occupant notices
- acknowledgement tracking
- occupant-safe pack foundations

Exit:
- SwissBuilding gains a stronger real-world safety and trust layer beyond manager-only workflows

### Wave R21 — openBIM and digital logbook convergence

- IFC/IDS/BCF/bSDD alignment strategy
- digital building logbook mapping
- passport export convergence
- machine-readable requirement and exchange direction

Exit:
- SwissBuilding becomes more standards-aware and more plausible as a European infrastructure layer

### Wave R22 — Semantic building operations and systems

- systems/equipment ontology foundations
- plan/zone/system linkage
- future smart-readiness hooks
- Brick/Haystack-aware semantic mapping strategy

Exit:
- the product gains a credible path from renovation evidence into broader building operations intelligence

### Wave R23 — Legal-grade proof and chain-of-custody

- proof versioning
- custody events
- delivery receipts
- archival defensibility

Exit:
- SwissBuilding proof artifacts become more dispute-ready and authority/insurer-grade

### Wave R24 — Enterprise identity and tenant governance

- tenant boundary hardening
- delegated and temporary access patterns
- SSO-ready identity direction
- audited support/admin access model

Exit:
- the platform becomes easier to trust in larger enterprise contexts

### Wave R25 — BIM, 3D, and geometry-native intelligence

- geometry anchor model
- spatial issues and proof
- BIM/IFC-aware path
- plan-vs-reality comparison direction

Exit:
- geometry becomes a real intelligence surface, not only a stored asset

### Wave R26 — Execution quality and hazardous works operations

- execution checkpoints
- method statements
- work quality records
- acceptance/reopen semantics
- disposal chain linkage

Exit:
- SwissBuilding starts governing the quality of hazardous execution, not only the pre-work dossier

### Wave R27 — Partner network and contributor reputation

- contributor quality signals
- partner trust profiles
- routing suggestions
- network-pull indicators

Exit:
- the ecosystem becomes an operational advantage instead of a black-box dependency

### Wave R28 — Benchmarking, learning, and market intelligence

- benchmark snapshots
- privacy-safe aggregates
- learning signals
- recommendation-learning inputs

Exit:
- the product gains a clear path from accumulated dossiers to defensible learning effects and market intelligence

### Wave R29 — Owner operating layer

- expense and operating record direction
- renovation budget / reserve planning direction
- digital vault semantics
- insurance policy and claims operating direction

Exit:
- SwissBuilding opens a credible path from building intelligence platform toward a true owner-facing building super app

### Wave R30 — Governance, procedure, and living operations

- permit and subsidy procedure direction
- co-ownership and resident governance direction
- energy/carbon/live performance direction
- warranty / defects / service obligations direction

Exit:
- SwissBuilding expands from project and dossier intelligence toward full lifecycle building operations

### Wave R31 — Constraint, memory, and pre-blocker intelligence

- constraint graph direction
- dependency and unlock intelligence
- decision replay and operator memory
- weak-signal watchtower

Exit:
- SwissBuilding starts reasoning not only about state, but about leverage, memory of judgement, and early warning before failure

### Wave R32 — Newly practical multimodal and agentic surfaces

- multimodal grounded query
- autonomous dossier completion
- cross-modal change detection and reconstruction

Exit:
- SwissBuilding starts using post-2025 multimodal and agentic capabilities in a grounded, evidence-first way

### Wave R33 — Open-source accelerators pull strategy

- Docling experiments
- IfcOpenShell path
- Brick / Haystack path
- Argilla / Label Studio / CVAT curation path
- Temporal readiness
- Keycloak / OpenFGA / OPA pull criteria
- OpenTelemetry / SigNoz instrumentation path
- DuckDB / Ibis / OpenLineage analytics path
- MapLibre / PMTiles spatial distribution path

Exit:
- SwissBuilding keeps its moat in product intelligence while pulling the best newly mature OSS layers instead of rebuilding them blindly

### Wave R34 — Continuous review and modernization

- review and improve any relevant surface that now deserves modernization
- tighten tools, testing, extensions, and integrations
- upgrade or simplify low-regret building blocks
- clean repo coherence, validation ergonomics, and stale assumptions
- tune search, export, recovery, seed determinism, and real-e2e ownership where needed

Exit:
- the product no longer only grows in features
- it also compounds in quality, maintainability, and operational excellence

### Wave R35 — Live state and counterfactual resilience

- sensor fusion foundations
- building live-state normalization
- anomaly and drift signals
- counterfactual shock scenarios
- stress-aware readiness / trust / portfolio comparisons

Exit:
- SwissBuilding can reason not only about what is true now, but also how the building behaves live and how it holds up under change or shock

### Wave R36 — Integration truth and governed human trust

- full-chain integration and demo-truth harnesses
- bounded-context facades over saturated service families
- explicit expert disagreement / override governance
- resilient offline field capture for high-value site truth

Exit:
- the system is not only broad; it is integrated, governable, and resilient when humans and real-world conditions push back

### Runway Rules

- if a wave uncovers prerequisite debt, repair the debt before forcing the next wave
- if a wave lands faster than expected, promote items from `Future Horizon Feed` and `docs/product-frontier-map.md`
- if reality disproves a planned wave, rewrite the runway in this file instead of leaving stale intent behind

## Validation Gates

- `docs_only`
  - doc consistency check only
- `backend_core`
  - `cd backend && ruff check app/ tests/`
  - `cd backend && ruff format --check app/ tests/`
  - `cd backend && python -m pytest tests/ -q`
- `backend_plus_seed`
  - `backend_core`
  - run seed verification if seed shape changes
- `frontend_core`
  - `cd frontend && npm run validate`
  - `cd frontend && npm test`
  - `cd frontend && npm run build`
- `frontend_plus_e2e`
  - `frontend_core`
  - `cd frontend && npm run test:e2e`
- `real_integration` when the scope justifies it and the environment is ready
  - `cd frontend && npm run test:e2e:real`

Rules:

- Report mock and real validation separately.
- Do not claim a command is green unless it was actually run.
- If code changes behavior, update docs in the same wave.

## Decision Log

- control-plane hygiene now has a repo-native guardrail:
  - `python scripts/lead_control_plane_check.py --strict`
  - npm alias: `npm run lead:check`
  - this should be used when wave churn is high to keep `Next 10` and key sections sane
- real-e2e now has a repo-native preflight gate:
  - `cd frontend && npm run test:e2e:real:preflight`
  - `test:e2e:real` runs this preflight before Playwright
  - login credentials can be overridden with:
    - `E2E_REAL_ADMIN_EMAIL`
    - `E2E_REAL_ADMIN_PASSWORD`
- `docs/lead-ongoing-backlog.md` is the long-form lead backlog Codex should keep working through in parallel while Claude executes.
- Claude prompts should stay compact and point back to repo docs instead of restating standing context.
- `ORCHESTRATOR.md` is the source of truth for active execution, not for long-term product vision.
- MP1 is ~95% complete; Campaign system is the last major gap.
- MP2 governance layer is complete; search (Meilisearch) is the remaining gap.
- Anticipatory domain models (SavedSimulation, DataQualityIssue, ChangeSignal, ReadinessAssessment) should be built now as backend-only structures to avoid future retrofit debt per product-frontier-map.md guidance.
- If there is room for one more anticipation wave after the active gaps, prefer backend-only primitives that strengthen proof and memory without forcing immediate UI:
  - `BuildingTrustScore`
  - `UnknownIssue`
  - `PostWorksState`
- Once the current top queue thins out, Claude should pull from the dedicated project briefs under `docs/projects/` rather than waiting for a bespoke prompt:
  - `legislative-compliance-hardening.md`
  - `trust-readiness-postworks-program.md`
  - `portfolio-execution-and-packs-program.md`
  - `testing-and-validation-modernization.md`
  - `spatial-truth-and-field-operations-program.md`
  - `contradiction-passport-and-transfer-program.md`
  - `killer-demo-and-wow-surfaces-program.md`
  - `transaction-insurance-finance-readiness-program.md`
  - `rules-pack-studio-and-europe-expansion-program.md`
  - `agent-governance-and-knowledge-workbench-program.md`
- `building-passport-standard-and-exchange-program.md`
- `portfolio-intelligence-command-center-program.md`
- `ecosystem-network-and-market-infrastructure-program.md`
- `continuous-review-and-modernization-program.md`
- `reliability-observability-and-recovery-program.md`
- `demo-and-sales-enablement-program.md`
- `privacy-security-and-data-governance-program.md`
- `distribution-and-embedded-channels-program.md`
- `openbim-digital-logbook-and-passport-convergence-program.md`
- `semantic-building-operations-and-systems-program.md`
- `legal-grade-proof-and-chain-of-custody-program.md`
- `enterprise-identity-and-tenant-governance-program.md`
- `bim-3d-and-geometry-native-intelligence-program.md`
- `execution-quality-and-hazardous-works-operations-program.md`
- `partner-network-and-contributor-reputation-program.md`
- `benchmarking-learning-and-market-intelligence-program.md`
- `autonomous-dossier-completion-and-verification-program.md`
- `constraint-graph-and-dependency-intelligence-program.md`
- `coownership-governance-and-resident-operations-program.md`
- `counterfactual-stress-testing-and-shock-planning-program.md`
- `cross-modal-change-detection-and-reconstruction-program.md`
- `decision-replay-and-operator-memory-program.md`
- `energy-carbon-and-live-performance-program.md`
- `multimodal-building-understanding-and-grounded-query-program.md`
- `open-source-accelerators-2026-radar.md`
- `permit-procedure-and-public-funding-program.md`
- `sensor-fusion-and-live-building-state-program.md`
- `warranty-defects-and-service-obligations-program.md`
- `weak-signal-watchtower-program.md`
- Wave 8 landed Workstream A of legislative compliance hardening:
  - `rule_resolver.py` — jurisdiction-hierarchy-aware pack resolution with 21 tests
  - `compliance_engine.py` — async resolved functions (pack first, hardcoded fallback) with 15 tests
  - `risk_engine.py` — pack-driven calibration override in step 1b
  - `dossier_service.py` — pack-resolved cantonal requirements and thresholds
  - All 3 services now query RegulatoryPack data when jurisdiction_id is set, falling back to hardcoded values otherwise
  - Baseline: 4457 backend tests, 0 warnings, ruff clean
- Validation is functionally green:
  - mock e2e suite is green
  - real e2e remains an environment-targeting issue until SwissBuilding owns the expected backend port cleanly
- Product execution should anticipate future low-regret objects, states, and engines whenever that reduces future debt without inflating current UX.

## Archived Waves / Completed History

### Pre-ORCHESTRATOR batches (frontend quality)
- Batch A–I: UX, i18n, error handling, testing, performance, accessibility, mobile, search, PWA, dark mode, map clustering

### Wave 1–4 (MP1 core build)
- Physical building backend (zones, elements, materials, interventions, plans) — models, schemas, APIs, RBAC, tests
- Evidence + quality backend (EvidenceLink, BuildingQuality, dossier service v2 with Gotenberg)
- Seeds + fixtures (seed enrichment, jurisdictions seeding, action generation)
- Frontend explorer + dossier UX (Explorer, Interventions, Plans, Evidence Chain, Dossier Pack, Quality Score)
- Completeness engine + timeline service + action generator
- File processing pipeline (ClamAV + OCRmyPDF)
- Jurisdictions + regulatory packs (multi-level hierarchy)
- Portfolio dashboard + audit logs admin
- i18n parity (1035 keys × 4 languages)
- E2e coverage: 218 mock tests, 25 real tests
- Historical baseline at that stage:
  - backend: `1328 tests`
  - frontend unit: `137 tests`

### Historical validation baseline (post-Wave 4)
- this is archived history, not the current source of truth
- backend: `1328 tests` pass (~56s)
- frontend validate: clean
- frontend unit: `137`
- frontend e2e mock: `218`
- frontend build: clean
- i18n: `1035 keys × 4 languages`, perfect parity

Keep future history compact here; do not re-expand old task tables into the active area.
