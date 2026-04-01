# Post-Session Stabilization Program

Date: 28 mars 2026  
Status: Active execution program  
Primary executor: `Claude Code`  
Commit baseline: `6650d68`  
Depends on:
- `AGENTS.md`
- `MEMORY.md`
- `docs/projects/swissbuilding-moonshot-v2-autonomous-market-infrastructure-plan-2026-03-28.md`
- `docs/projects/claude-moonshot-evaluation-and-feedback-pack-2026-03-28.md`
- `docs/projects/repo-excellence-brief-2026-03-28.md`
- `docs/projects/repo-quality-recovery-plan-2026-03-28.md`

---

## Summary

The repo just absorbed an unusually large amount of real product, infrastructure, tests, and doctrine in one session.

That is a strength.
It is also now the main risk.

The next mission is **not expansion**.
It is **absorption**.

This program exists to turn a massive, credible burst of output into a repo that is:

- safe
- rerunnable
- testable end-to-end
- operationally explainable
- less dependent on a single giant working session
- ready for deeper V2 benchmark work without hidden fragility

The benchmark question is no longer:

- "How much more can we add?"

The benchmark question is now:

- "Can we absorb this volume without degrading structural quality?"

---

## Operating Posture

From this point until the stabilization gates close:

- no major new product surfaces
- no new large frontier layer unless it directly closes an already-open V2 capability unit
- no opportunistic broadening because a new idea is attractive
- closure, verification, convergence, and debt reduction outrank expansion

Preferred optimization order:

1. rerunnable validation truth
2. runtime confidence
3. control-plane and benchmark sync
4. compatibility retirement
5. frontend confidence for newly exposed surfaces
6. partner/market infra completion already in-flight
7. monolith containment and decomposition planning

---

## Why This Program Exists

The post-session state has strong signals of real quality:

- a committed baseline now exists
- large backend and frontend surfaces were added
- many backend tests were added
- pre-commit and registry guards exist
- V2 benchmark rails materially advanced

But it also has clear fragility signals:

- the commit is enormous and not realistically human-reviewable as one unit
- full backend validation is not yet trustworthy while `test_seed_demo.py` remains broken
- the shell restructure lacks a dedicated e2e smoke path
- `ORCHESTRATOR.md` is stale relative to the actual repo state
- hub-file discipline was breached during wave execution
- several newly added services/pages are already large enough to become the next debt cluster

This means the repo is **credible** but not yet **fully absorbed**.

---

## Hard Non-Negotiables

1. Do not reopen settled doctrine.
2. Do not create new top-level product centers.
3. Do not expand the route surface unless it strictly reduces debt.
4. Do not claim closure without rerunnable validation evidence.
5. Do not leave broken full-suite validation unresolved while continuing major expansion.
6. Do not leave `ORCHESTRATOR.md` materially behind the executed state.
7. Do not normalize wave-time hub-file discipline breaches by repeating them.
8. Do not let V2 become a second expansion sprint before this stabilization program closes.

---

## Priority Stack

### Priority 0 — Protect and Freeze the Baseline

Goal:
- ensure the committed baseline is the explicit stabilization starting point

Actions:
- treat commit `6650d68` as the stabilization anchor
- avoid rebasing/restructuring that obscures what changed unless necessary
- keep a clean checkpoint cadence from here forward
- record any follow-up commits with narrow, reviewable scopes

Done when:
- the working tree is recoverable at every stabilization step
- each stabilization wave produces a bounded commit
- no new mega-commit is created

---

### Priority 1 — Restore Full Validation Truth

Goal:
- make backend and frontend validation claims trustworthy again

Immediate target:
- fix `backend/tests/test_seed_demo.py`

Required actions:
- isolate the exact failing assertion or outdated seed contract
- fix the underlying seed behavior or update the test only if behavior is intentionally changed
- rerun the affected seed tests
- rerun a full backend `pytest tests/ -q`
- rerun frontend `npm run validate`
- rerun frontend unit tests relevant to the newly exposed shell and V2 surfaces

Hard rule:
- do not keep using partial test subsets as the main truth signal once the seed failure is fixable

Done when:
- full backend `pytest tests/ -q` passes
- backend lint/format checks pass
- frontend validate passes
- any residual test exclusions are explicit and justified

If blocked:
- document the blocker as `external`, `infra`, or `pre-existing debt`
- provide exact failing command and failure signature

---

### Priority 2 — Add Real Runtime Confidence for the New Shell

Goal:
- prove that the new shell actually works as a user flow, not only as isolated components

Minimum required e2e smoke coverage:
- shell boots successfully
- top-level navigation works for:
  - `Today`
  - `Buildings`
  - `Cases`
  - `Finance`
  - `Portfolio`
- at least one representative building opens
- `Building Home` renders its canonical shell and key tabs
- `Case Room` renders its canonical shell and key tabs
- at least one absorbed legacy route redirects correctly into the bounded shell

Good candidates:
- extend or replace the current real e2e demo workspace flow
- prefer one strong smoke path over many fragile cosmetic checks

Hard rule:
- this is not a screenshot exercise
- validate navigation, loading, and canonical surface wiring

Done when:
- at least one meaningful e2e smoke test passes against the post-session shell
- redirects and canonical workspace entry points are proven

---

### Priority 3 — Sync the Control Plane

Goal:
- make repo-visible execution truth match what was actually shipped

Actions:
- update `ORCHESTRATOR.md` with the real wave outcomes
- capture:
  - what actually closed
  - what is still partial
  - validation status
  - blockers
  - accepted debt
  - counters (`waves_completed`, `rework_count`, `blocked_count`)

Hard rule:
- do not rewrite history
- do not inflate completion claims
- mark shorthand claims precisely if the repo object names differ from the checkpoint wording

Done when:
- the control plane can be read without relying on chat history
- another operator can tell what is real, what is partial, and what is next

---

### Priority 4 — Reconcile Hub-File Discipline

Goal:
- resolve the mismatch between `AGENTS.md` execution rules and actual wave behavior

Problem:
- wave execution touched hub files that are explicitly guarded during waves

Actions:
- identify exactly which protected hub files changed
- classify each change:
  - unavoidable and correct
  - should be moved elsewhere
  - should be reverted/refactored out
- if the rule is too strict for reality, propose a rule refinement
- if the rule is correct, restore discipline and document the exception

Done when:
- there is no silent contradiction between execution doctrine and actual repo practice
- the next wave can follow a clearer rule set

---

### Priority 5 — Finish Compatibility Cleanup Around ChangeSignal

Goal:
- convert the strong migration progress into a cleaner retirement posture

Actions:
- verify remaining `ChangeSignal` surfaces are truly compatibility-only
- remove or tighten stale comments, labels, and inventory drift
- ensure compatibility guards and inventories reflect reality
- confirm no non-compat runtime consumers remain
- define retirement conditions for the remaining compatibility layer

Done when:
- `ChangeSignal` is clearly bounded to explicit compatibility files only
- inventories and guard scripts align with actual usage
- the repo has a visible retirement plan instead of an indefinite frozen layer

---

### Priority 6 — Finish the In-Flight Market Infrastructure Lot

Goal:
- close the currently active partner/market lot before opening a new one

Primary focus:
- `partner-submissions`

Actions:
- finish the in-progress partner-submissions implementation
- ensure partner exchange contracts, trust checks, and conformance are wired together coherently
- add or tighten contract and permission tests where needed
- verify that partner flows are governed, bounded, and not creating a second truth path

Done when:
- the in-flight lot has a final checkpoint
- partner submission flows are not left half-open
- V2 `Rail 6` has coherent governance, not just initial artifacts

---

### Priority 7 — Densify Frontend Confidence Where the New Value Lives

Goal:
- raise confidence on the newly exposed V1/V2 surfaces that matter most

Current problem:
- backend test density is much stronger than frontend test density
- several important V2 UI surfaces are exposed without equivalent test depth

Priority surfaces:
- `PackBuilderPanel`
- `CaseRoom`
- `FormsWorkspace`
- `Today`
- `PortfolioCommand`
- `InvalidationAlerts`
- `ReviewQueuePanel`
- any shell navigation component materially changed this session

Testing doctrine:
- prefer fewer, higher-signal tests
- focus on behavior and state transitions
- avoid snapshot-heavy or label-fragile tests

Minimum target:
- add targeted tests for the most operationally important new UI surfaces
- ensure conformance badges, invalidation notices, queue rendering, and critical panel states are covered

Done when:
- frontend confidence better matches the importance of the newly exposed workflows
- the most valuable V2 UI surfaces are not effectively untested

---

### Priority 8 — Convert Validation Scripts into Trusted Gates

Goal:
- make the new repo guards part of the normal truth loop, not one-off demo evidence

Scripts/gates to reinforce:
- `pre_commit_check.py`
- `check_route_shell.py`
- `check_canonical_registry.py`
- `check_compatibility.py`
- `check_file_sizes.py`
- `test_budget_guard.py`
- `check_repo_health.py`

Actions:
- verify outputs are stable and understandable
- ensure failure messages are actionable
- tighten any misleading timing or benchmark claims
- integrate the gates into a consistent local run order
- make it obvious which gates are fast, which are full, and which are advisory

Done when:
- operators can trust the gates
- the repo has fewer “claimed guardrails” and more actually used guardrails

---

### Priority 9 — Triage the New Monoliths Before They Harden

Goal:
- stop the latest big files from becoming the next frozen debt wall

Immediate hotspots:
- large extraction services
- large pack/passport services
- large scenario and climate services
- large pages like `CaseRoom` and `PortfolioCommand`
- large extraction review surfaces

Actions:
- inventory the top new file-size hotspots
- classify each:
  - acceptable for now
  - must split soon
  - dangerous now
- identify obvious extraction points:
  - adapters
  - orchestration
  - policy/decision logic
  - mapping/serialization
  - UI shell vs panel content

Hard rule:
- this priority is initially a containment + decomposition plan, not a blind rewrite

Done when:
- the repo has an explicit post-session monolith map
- future decomposition can happen intentionally instead of reactively

---

### Priority 10 — Normalize Docs and Evidence After the Burst

Goal:
- reduce mismatch between what the docs imply and what the repo actually proved

Actions:
- align checkpoint wording with literal repo evidence where needed
- clean up stale or over-broad status claims
- ensure the benchmark docs distinguish:
  - closed
  - partial
  - compat-only
  - doc-only
- tighten references so another operator can verify claims quickly

Done when:
- the doc layer supports verification instead of inflating it

---

### Priority 11 — Prepare the First Real Consolidation Wave

Goal:
- define the first non-trivial decomposition and cleanup wave that should follow stabilization

Candidates:
- extraction service split
- shell page slimming
- docs/control-plane trimming
- remaining compat retirement
- stronger source reliability depth

Hard rule:
- do not start this wave until Priorities 1 through 6 are materially closed

Done when:
- the repo has a reviewable, bounded consolidation roadmap
- the next wave is driven by structural leverage, not by adrenaline

---

## Suggested Execution Waves

### Stabilization Wave S1 — Validation Truth

Scope:
- Priority 1

Exit:
- full backend suite passes
- frontend validate passes
- failure inventory is explicit if not green

### Stabilization Wave S2 — Runtime Confidence

Scope:
- Priority 2
- any small fixes strictly required by the new e2e smoke path

Exit:
- one real shell smoke path passes

### Stabilization Wave S3 — Control-Plane and Doctrine Reconciliation

Scope:
- Priority 3
- Priority 4
- Priority 5

Exit:
- `ORCHESTRATOR.md` reflects reality
- hub-file discipline mismatch is resolved or explicitly redefined
- `ChangeSignal` compatibility posture is cleanly bounded

### Stabilization Wave S4 — Finish the In-Flight Rail 6 Lot

Scope:
- Priority 6

Exit:
- partner-submissions lot is no longer "in progress"
- partner exchange governance is coherent and tested

### Stabilization Wave S5 — Confidence and Containment

Scope:
- Priority 7
- Priority 8
- Priority 9

Exit:
- meaningful frontend confidence exists on high-value surfaces
- guard scripts are trustworthy
- new monoliths are inventoried and classified

### Stabilization Wave S6 — Documentation and Next-Wave Prep

Scope:
- Priority 10
- Priority 11

Exit:
- docs are aligned with reality
- the first consolidation wave is ready

---

## What Does Not Count as Progress Here

These should receive little or no credit during this stabilization program:

- adding new product centers
- adding new big services/pages just because the architecture can support them
- writing strategy docs without changing validation truth
- broadening market infrastructure while `partner-submissions` is still open
- adding many frontend tests that do not cover new operational risk
- renaming or relocating files without reducing real debt
- claiming “green” while full-suite truth is still missing

---

## Acceptance Gates

The stabilization program is materially successful only if:

1. commit `6650d68` is followed by smaller, reviewable stabilization commits
2. `backend/tests/test_seed_demo.py` no longer blocks full backend validation
3. full backend `pytest tests/ -q` is green, or remaining failure is explicitly isolated and accepted
4. frontend validate is green
5. at least one shell e2e smoke path is green
6. `ORCHESTRATOR.md` is current
7. the `ChangeSignal` compatibility boundary is explicit and credible
8. the partner-submissions lot is closed or explicitly blocked
9. benchmark evidence remains machine-checkable, not just narrated
10. the repo has an explicit monolith containment plan for the biggest new files

Stretch success:

- frontend confidence materially improves on V2 surfaces
- guard scripts become part of routine truth
- the first consolidation wave is fully briefed and ready

---

## Recommended Return Format for Claude

At the end of each stabilization wave, return:

- `wave`
- `priorities advanced`
- `what is now truly closed`
- `what remains partial`
- `validations run`
- `tests run`
- `failures fixed`
- `blocking debt`
- `accepted debt`
- `repo-quality risk reduced`
- `next best wave`

If a claimed checkpoint uses shorthand naming, also return:

- `repo object names`

So the evidence remains directly checkable.

---

## Final Instruction

Do not try to be impressive by adding more.

Be impressive by making the current repo:

- safer
- truer
- more rerunnable
- more bounded
- more reviewable
- more operationally honest

That is the real benchmark now.
