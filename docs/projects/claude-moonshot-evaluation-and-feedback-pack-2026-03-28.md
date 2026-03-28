# Claude Moonshot Evaluation and Feedback Pack

Date: 28 mars 2026
Scope: Evaluation pack for Moonshot V1 execution and the Moonshot V2 infrastructure-volume benchmark
Depends on:
- `docs/projects/v3-master-future-steps-plan-2026-03-28.md`
- `docs/projects/v3-master-plan-addendum-frontier-layers-2026-03-28.md`
- `docs/projects/v3-meta-layers-plan-2026-03-28.md`
- `docs/projects/swissbuilding-moonshot-v2-autonomous-market-infrastructure-plan-2026-03-28.md`
- `docs/projects/claude-validation-matrix-2026-03-25.md`
- `docs/projects/pilot-scorecard-and-exit-criteria-pack-2026-03-25.md`

---

## Purpose

This pack exists to evaluate Claude on the moonshot program with a standard stricter than:

- "a lot of code was added"
- "tests are green"
- "the docs look ambitious"

The correct question is:

- did Claude strengthen the canonical system,
- preserve doctrinal severity,
- increase usable product depth,
- keep the repo governable,
- and move the capacity experiment forward with measurable throughput?

This pack should be used:

- after each major wave
- after each multi-block implementation batch
- before accepting any claim that a block is "done"
- as the scoring reference for Moonshot V2 capability closure

---

## Review Inputs Required

Do not review from vibes. Require this evidence bundle first:

- Claude summary of what changed
- touched files grouped by area
- validations actually run
- tests actually run
- relevant diffs or screenshots for user-facing changes
- `ORCHESTRATOR.md` delta when wave work was done
- updated counters:
  - `waves_completed`
  - `rework_count`
  - `blocked_count`
  - `tests_green_ratio`
  - `frontier_layers_closed`
  - `meta_layers_closed`
  - `legacy_surfaces_retired`
  - `new canonical projections shipped`
  - `source families operationalized`

If this bundle is incomplete, the review is automatically incomplete.

---

## Moonshot V2 Benchmark Overlay

Use this overlay whenever Moonshot V2 is active.

V2 must not be scored primarily by:

- number of ideas touched
- number of files changed
- narrative breadth
- apparent "months of work"

V2 must be scored by:

- `CapabilityUnit`
- `QualityGate`
- `BenchmarkScore`
- `BenchmarkGrade`

### Capability Unit Fields

Every V2 capability unit must declare:

- `name`
- `rail`
- `status`
- `quality_gates`
- `evidence`
- `canonical_surfaces_touched`
- `legacy_surfaces_reduced`
- `debt_classification`
- `next_closure_step`

### Capability Status

Allowed values:

- `closed`
- `partial`
- `compat-only`
- `doc-only`
- `not-started`

### Quality Gates

Every unit uses 5 binary gates:

- `implemented`
- `integrated`
- `tested`
- `converged`
- `operationalized`

Rule:

- a unit may not be marked `closed` unless all 5 gates are true

### Scoring Weights

- `closed` = `1.0`
- `partial` = `0.35`
- `compat-only` = `0.2`
- `doc-only` = `0.05`
- `not-started` = `0`

### Benchmark Rails

Moonshot V2 should group units under:

- `Canonical Integrity`
- `Infrastructure Excellence`
- `Source and Connector Reliability`
- `Exchange and Conformance`
- `Procedure and Operational Depth`
- `Market Infrastructure Readiness`

### Benchmark Grades

- `Grade D — Wide but soft`
- `Grade C — Strong nucleus`
- `Grade B — Infrastructure-grade system`
- `Grade A — Market infrastructure candidate`

### V2 Anti-Fake-Progress Rule

These may be tracked, but must score weakly:

- doc-only layers
- new routes without shell convergence
- new models/services without canonical destination
- compatibility bridges without retirement plan
- APIs without contract tests
- seeds without repeatable validation
- extractors without consequence wiring
- dashboards without operational reactions
- pages that duplicate master workspaces

### V2 Review Output

When reviewing V2, require:

- per-unit status
- per-unit gate state
- per-rail summary
- aggregate `BenchmarkScore`
- explicit `BenchmarkGrade`
- accepted debt vs blocking debt

---

## Hard Fail Gates

Any `FAIL` below means:

- do not accept the wave as complete
- ask for corrective work before the next broadening step

### Doctrine Integrity

- `FAIL` if a new root was introduced outside canonical families
- `FAIL` if a new top-level product center was created outside:
  - `Today`
  - `Buildings`
  - `Cases`
  - `Finance`
  - `Portfolio`
- `FAIL` if a projection became de facto canonical truth
- `FAIL` if a role-specific truth store or dossier copy was introduced

### Transition Integrity

- `FAIL` if truth/publication/transfer transitions were implemented outside `ritual_service`
- `FAIL` if a new status machine appeared without base-grammar alignment
- `FAIL` if invalidation logic exists in hidden side paths without canonical trace

### Compatibility Integrity

- `FAIL` if new business meaning was added in legacy compatibility surfaces
- `FAIL` if `ChangeSignal` or equivalent compatibility bridges were expanded as if canonical
- `FAIL` if the repo moved toward parallel truths instead of progressive canonicalization

### Product Integrity

- `FAIL` if partially wired work is visible to users
- `FAIL` if frontend breadth increased but core spine clarity regressed
- `FAIL` if new backend primitives were added without clearly unlocking:
  - active maturity gate
  - structural debt removal
  - or a real integration gap

### AI / Source Integrity

- `FAIL` if AI-produced outputs lack `ai_generated` semantics where required
- `FAIL` if source-backed features hide provenance/freshness
- `FAIL` if external-write behavior bypasses cases, validation, provenance, or rituals

---

## Binary Acceptance by Moonshot Block

Use these as pass/fail tests before scoring nuance.

### Block 0 — Harness

Pass only if:

- the moonshot work is visibly organized into:
  - `core spine`
  - `source/procedure os`
  - `document/genealogy os`
  - `exchange/trust infrastructure`
  - `operations/economic os`
  - `network/autonomous market os`
- throughput counters are actually tracked
- wave closeouts produce a single checkpoint, not scattered micro-updates

### Block 1 — Spine Absolue

Pass only if:

- canonical / subordinate / compatibility / deprecated classification is legible
- workspace convergence reduced page sprawl instead of adding more centers
- projection registry exists and is used
- role-native views do not duplicate truth
- temporal semantics are applied to important new objects
- Trust Ops / review flows are operational, not just named
- invalidation exists beyond a vague staleness note
- Truth API posture is clearly `read-first`

### Block 2 — Total Source OS

Pass only if:

- the `3 circles` source model is explicit
- identity backbone is coherent:
  - address -> EGID -> EGRID -> RDPPF
- source registry includes provenance, freshness, and workspace destination
- source health / fallback / drift handling exist or are concretely staged
- public context is consumed in product surfaces, not just imported in backend

### Block 3 — Procedure OS

Pass only if:

- procedure grammar is explicit and reusable
- procedures are attached to `BuildingCase`
- at least one non-trivial procedure chain is explainable end-to-end
- work-family mapping has operational meaning beyond enums
- procedure deltas can affect blockers, forms, packs, or readiness

### Block 4 — Document Intelligence OS

Pass only if:

- documents are transformed into canonical information, not just stored
- extraction output distinguishes:
  - document
  - evidence
  - claim
  - decision
  - publication
- consequences exist:
  - action
  - blocker
  - contradiction
  - validation task
  - pack/passport effect
- raw document remains source, not overwritten by normalized truth

### Block 5 — Building Genealogy OS

Pass only if:

- historical sources are connected to canonical change semantics
- the system can express:
  - observed state
  - declared state
  - authorized state
- transformation history is more than a flat timeline
- evidence windows and historical claims keep trust semantics

### Block 6 — Climate / Exposure / Opportunity

Pass only if:

- climate/exposure is modeled as context, not fake causality
- long-horizon weather or exposure data can affect actions or signals
- opportunity windows are visible in at least one canonical workspace
- planning/maintenance/claims relevance is explicit

### Block 7 — Exchange / Transfer / Conformance

Pass only if:

- passport sovereignty is preserved
- transfer includes receipt/acknowledgement/version semantics
- import/re-import is bounded and explainable
- conformance checks are explicit enough to support machine-readable evaluation
- rights/license/externalization rules are becoming concrete, not hand-wavy

### Block 8 — Finance / Insurance / Transaction / Caveat

Pass only if:

- finance remains building-rooted and case-linked
- safe-to-sell / insure / finance consume truth, unknowns, caveats, and procedure
- caveats/commitments are explicit objects, not loose notes
- insurer/lender/transaction outputs stay bounded projections, not separate products

### Block 9 — Operations / Owner / Utility Twin

Pass only if:

- utility/service truth is tied to building operations
- recurring service memory closes the loop with finance/incidents/truth
- owner ops stay building-rooted and evidence-linked
- the system moves from project-only toward live building operation

### Block 10 — Material / System / Circularity

Pass only if:

- material/system passports are tied to interventions and post-works truth
- circularity remains useful and concrete
- no generic product-catalog drift appears

### Block 11 — Counterfactual / Scenario / Portfolio

Pass only if:

- scenarios consume canonical truth, unknowns, caveats, cost, and procedure
- do-nothing / phase / delay / widen-reduce logic is explainable
- portfolio arbitration improves because of the model, not because of decorative charts

### Block 12 — Network / Autonomous Market OS

Pass only if:

- partner trust and exchange boundaries stay explicit
- partner APIs respect the truth API doctrine
- ecosystem additions strengthen canonical roots instead of creating parallel domains
- agentic coordination remains auditable and governed

---

## V2 Rail Review Questions

Use these in addition to the block tests when V2 is active.

### Canonical Integrity

- Did the work reduce parallel truth risk?
- Did it reduce legacy surfaces or clearly bound compatibility?
- Did it converge runtime topology toward the hub/workspace doctrine?

### Infrastructure Excellence

- Did the repo become more machine-checked, migration-safe, and CI-trustworthy?
- Did the work add enforceable guardrails rather than aspirational docs only?

### Source and Connector Reliability

- Did the work improve source health, fallback, drift handling, or degraded-mode visibility?
- Can users tell the difference between unavailable sources and absent truth?

### Exchange and Conformance

- Did the work make contracts, manifests, imports, exports, or rights more machine-evaluable?
- Is external exchange more governed, not merely broader?

### Procedure and Operational Depth

- Did the work make procedures more executable, explainable, and reactive to change?
- Did it improve Trust Ops, invalidation, or consequence propagation in real workflows?

### Market Infrastructure Readiness

- Did the work strengthen partner interoperability, network governance, or auditable coordination?
- Is the system becoming more infrastructure-like instead of just feature-richer?

---

## Scored Scorecard

Score each category from `0` to `5`.

Interpretation:

- `0` = absent or regressed
- `1` = named only
- `2` = partial and fragile
- `3` = real and usable
- `4` = strong and well integrated
- `5` = category-shaping and hard to copy

### 1. Canonical Coherence

Questions:

- Did the work strengthen the canonical graph?
- Did it reduce ambiguity between roots, projections, compatibility, and deprecated layers?
- Did it avoid semantic duplication?

### 2. Product Operability

Questions:

- Can a user or operator actually use the new depth in `Today`, `Building Home`, `Case Room`, `Finance`, or `Portfolio`?
- Did the work improve decision quality, not just object count?

### 3. Trust and Explainability

Questions:

- Are provenance, freshness, unknowns, caveats, and review paths visible?
- Can a verdict be retraced by objects and evidence?

### 4. Integration Quality

Questions:

- Did the work connect to existing cases, rituals, projections, and workspaces?
- Or did it land as a powerful but isolated island?

### 5. Validation Signal

Questions:

- Were the right tests run?
- Is validation proportional and meaningful?
- Is there at least one full-chain confidence signal where needed?

### 6. Throughput Discipline

Questions:

- Did Claude ship a coherent wave rather than a scattered pile?
- Were counters and debriefs kept current?
- Was rework contained?

### 7. Future-Proofing

Questions:

- Did the work reduce future retrofit debt?
- Does it stay compatible with Europe-ready, multi-actor, multi-source growth?

### 8. Severity of Doctrine

Questions:

- Did the implementation preserve the restrictive edge of V3?
- Or did convenience soften the doctrine back into module sprawl?

---

## Moonshot-Specific Acceptance Tests

These are the most important high-signal questions to ask Claude after each serious wave.

### Core Spine Test

- Can another engineer classify any touched object/service/page as:
  - canonical
  - subordinate
  - compatibility-only
  - deprecated
- Can they tell which projection owns the read-side surface?
- Can they tell which ritual owns the transition?

### No Parallel Truth Test

- Did any new logic create a second truth center?
- Did any actor-specific surface become a hidden canonical source?
- Did any compatibility bridge absorb new business semantics?

### Explainability Test

- For one concrete building and one concrete case:
  - can the system explain why the current verdict exists,
  - what is missing,
  - what changed,
  - and what should happen next?

### Throughput Test

- Did the wave materially close one block, or only open more fronts?
- Did the backlog become clearer, or more fuzzy?
- Are `clear / fuzzy / missing` debrief notes good enough to improve the next wave?

### Cut-Rule Test

- If progress slows, is Claude protecting the core spine first?
- Is broadening being cut from the outside inward:
  - 12 -> 11 -> 10 -> 9 -> 8
- Is the nucleus still protected:
  - spine
  - source OS
  - procedure OS
  - document intelligence
  - genealogy/exchange core

---

## Required Validation Evidence

Use the smallest loop that gives real signal, but require real evidence.

### Docs / Control-Plane Wave

Require:

- touched docs are coherent with existing roadmap docs
- no doctrinal contradiction introduced
- relevant counters or control-plane references updated if the wave claims execution impact

### Backend Logic Wave

Require at minimum:

- `cd backend && ruff check app/ tests/`
- targeted backend tests for touched domain

Require stronger confidence when cross-cutting:

- `cd backend && python scripts/run_local_test_loop.py changed`
- `cd backend && python -m pytest tests/ -q` only when blast radius justifies it

### Frontend / Projection Wave

Require at minimum:

- `cd frontend && npm run validate`
- targeted vitest coverage for touched surfaces when behavior changed

Require stronger confidence when navigation or canonical flows changed:

- `cd frontend && npm test`
- `cd frontend && npm run test:e2e` or relevant smoke path when justified

### Full-Chain / Cross-Cutting Wave

Require:

- backend lint
- frontend validate
- targeted integration tests
- at least one golden-path scenario when the wave claims doctrinal closure

Reference:

- `docs/projects/claude-validation-matrix-2026-03-25.md`

---

## Feedback Format to Send Claude

Use this structure. Keep it strict and short.

### 1. Verdict

Choose one:

- `Promote`
- `Promote with debt logged`
- `Extend narrowly`
- `Rework before next wave`
- `Stop broadening, harden core`

### 2. What is Strong

List `1-5` genuinely strong points only.

### 3. What Fails or Risks Drift

List `1-5` concrete problems only.

Use categories like:

- canonical drift
- parallel truth
- weak projection ownership
- status sprawl
- hidden transition logic
- weak validation
- poor throughput discipline
- speculative breadth without closure

### 4. Required Corrections Before Next Wave

Each line should be imperative and bounded.

Examples:

- merge all transfer state changes into `ritual_service`
- classify touched read models in the projection registry
- stop adding semantics to compatibility bridges
- expose unknowns in `Building Home` and `SafeToX`

### 5. Debt That Can Wait

Keep this explicit so Claude does not thrash.

### 6. Next Wave Recommendation

Choose one:

- continue same block
- close core-spine gap
- integrate before broadening
- move to next block
- stop and cut outer ring

---

## Copy-Paste Review Prompt

Use this when you want Claude to self-review a wave before your own final judgment:

```md
Review your last wave against `docs/projects/claude-moonshot-evaluation-and-feedback-pack-2026-03-28.md`.

Return exactly:

1. Hard fail gates: pass/fail with evidence
2. Block(s) advanced: pass/fail with evidence
3. Scorecard (0-5) for the 8 dimensions
4. What is truly closed vs still partial
5. Rework required before the next wave
6. Debt that should be logged but not tackled now
7. Recommended next wave in one paragraph

Do not give optimistic framing where the evidence is partial.
```

---

## Acceptance

This pack succeeds only if:

- reviews become faster and stricter, not longer and softer
- feedback to Claude becomes more operational and less emotional
- block completion claims become auditable
- moonshot execution stays ambitious without losing doctrinal discipline
- the team can distinguish real category-building progress from impressive but ungoverned expansion
