# Remaining Work Master Backlog

Date: 29 mars 2026  
Status: Active master backlog  
Purpose: replace repeated micro-session framing with one merged view of the remaining known work

Depends on:
- `MEMORY.md`
- `ORCHESTRATOR.md`
- `docs/projects/swissbuilding-moonshot-v2-autonomous-market-infrastructure-plan-2026-03-28.md`
- `docs/projects/repo-excellence-brief-2026-03-28.md`
- `docs/projects/consolidation-hotspot-brief-2026-03-28.md`
- `docs/market/baticonnect-board-investor-memo-2026-03-28.md`
- `docs/projects/baticonnect-ultimate-product-manifesto-2026-03-28.md`
- `docs/product-frontier-map.md`

---

## Summary

The repo is no longer in the phase where the main problem is "not enough architecture".

It now has:

- a strong canonical spine
- a credible `B+` benchmark state
- a much cleaner validation baseline
- several major god-file decompositions already completed
- real infra, exchange, readiness, and source-reliability layers

The next problem is not inventing more.
The next problem is **closing the right remaining work in the right order**.

This document exists to stop the pattern of:

- 5 small sessions for one coherent outcome
- repeated reframing of already-decided strategy
- context switching between wedge, infra, debt, and category work

The right default from here is:

- one large coherent lot
- one closeout
- one bounded next lot

---

## Current State

What is already materially true:

- Moonshot V1 delivered the doctrinal/product spine
- Moonshot V2 reached a credible `B+` state
- stabilization `S1-S6` is closed
- the validation baseline is materially cleaner
- C1-C3 god-file decomposition wave is closed
- frontend validate is green
- pre-commit / guardrails are green
- source reliability `Rail 3 batch 1` is closed for:
  - identity
  - geo context
  - subsidy sources

What this means:

- the repo no longer needs another broad stabilization sprint right now
- the highest leverage is now **wedge-first product closure**, with selective infra/debt support only when it directly helps that wedge

---

## Organizing Principle

There are many remaining ideas.
There are far fewer remaining tasks that should be done **now**.

The remaining work is organized into 4 horizons:

1. `Now` — directly increases wedge value or closes a near-term benchmark gap
2. `Next` — important follow-up after the current wedge lot closes
3. `Later` — real remaining work, but should not interrupt the current wedge push
4. `Not now` — attractive, but harmful if pulled in too early

---

## Horizon 1 — Do Now

These are the highest-leverage remaining tasks.

### A. Giant Lot G1 — Safe-to-Start Dossier Vertical Closeout

This is the best remaining "do a giant leap in one go" lot.

Commercial shape:
- the `VD/GE` regulated pre-work pollutant dossier workflow
- sold as a readiness layer + proof engine

The lot should close one coherent user-visible flow:

1. a building or case has an initial dossier state
2. the system shows what is proven, missing, contradictory, stale, or unknown
3. missing pieces become actions/review/tasks
4. readiness is visible in canonical surfaces
5. an authority-ready pack can be generated
6. pack delivery/submission state is visible
7. complement or return reopens the right actions and invalidations
8. the user can see the dossier move closer to authority-ready

Minimum surfaces that should feel coherent after G1:
- `Today`
- `Building Home`
- `Case Room`
- `Pack Builder`
- minimal portfolio/readiness summary where it directly supports the workflow

Non-negotiable capabilities inside G1:
- canonical `safe_to_start` / readiness state
- explicit missing proof / evidence gaps
- visible blocker / caveat / unknown handling
- action loop from missing dossier piece to next task
- authority-ready pack generation with conformance visible
- re-open path when authority/complement feedback arrives
- one real seeded or e2e proof of the full loop

This is the best candidate for doing more in one session instead of five.

---

### B. Remaining Rail 3 Batch 2

These adapters should still be upgraded to reliability-grade, but only if they support the chosen wedge lot or help move toward `Grade A` without distracting from it:

1. `spatial_enrichment_service.py`
2. `cantonal_procedure_source_service.py`
3. clarify climate dependency posture if it is still only transitively covered

Done criteria per adapter:
- health
- fallback/degraded path
- freshness/watch semantics
- schema-drift handling where relevant
- contract tests

Rule:
- do not do this as an abstract infra sprint if G1 is not actively using it

---

### C. Rules/Procedure Depth for the Wedge

Still-remaining work that directly strengthens the first commercial promise:

1. tighter `VD`/`GE` dossier requirements by workflow trigger
2. clearer authority-ready vs not-ready criteria by case type
3. stronger complement/return handling
4. work-family/procedure mapping where it changes actual dossier readiness
5. clearer audience packs for authority / owner / contractor where used in the wedge

Rule:
- procedure depth is justified only when it changes the actual dossier flow

---

### D. Paid-Pilot Readiness Layer

The product is ahead of its commercial proof.
Remaining tasks that directly help the first paid pilots:

1. one end-to-end demoable dossier scenario
2. one pilot scorecard tied to a real dossier flow
3. one clean explanation of:
   - what is proven
   - what is missing
   - what changed
   - what is ready next
4. minimal operator/reporting surface to support pilot review

Rule:
- this should stay product-linked, not become a broad sales collateral sprint

---

## Horizon 2 — Do Next

These are important, but should generally wait until G1 is closed.

### E. Rail 4 / Exchange Deepening

Important remaining exchange substrate work:

1. machine-readable exchange manifests
2. stronger import/export validation
3. re-import symmetry hardening
4. rights/license/externalization governance where actually exercised
5. clearer transfer/share boundaries by audience/domain

This matters for `Grade A`, but should not outrun the wedge loop.

---

### F. Rail 6 / Market Infrastructure Deepening

Important remaining market-readiness work:

1. partner-facing API depth
2. partner webhooks/events
3. contributor quality / partner trust deepening
4. bounded autonomous coordination where auditable and reversible
5. exchange protocol governance beyond one contract surface

This is real remaining work.
It is not the next best lot unless the wedge specifically needs it.

---

### G. Consolidation Hotspots Still Left

Known remaining structural debt after C1-C3:

1. `swiss_rules_spine_service.py`
2. `enrichment/orchestrator.py` if further split is needed later
3. other large coherent services only when they start slowing real work

Rule:
- do not run another wide decomposition wave just because hotspots exist
- decompose only when it increases leverage on active product work

---

### H. Frontend/Runtime Quality Follow-Through

Remaining likely cleanup items that matter but are not urgent:

1. React Router v7 deprecation warnings
2. residual CRLF/LF hygiene when worth touching
3. further high-signal tests for critical V2 surfaces if the wedge uses them
4. reduce page/runtime drift only if it simplifies the chosen vertical slice

---

## Horizon 3 — Do Later

These are still real remaining tasks, but should not interrupt the wedge-first path right now.

### I. Renovation / Subsidy Readiness Vertical Slice

A likely second strong product lot after G1:

1. subsidy readiness
2. renovation readiness
3. actionable capex / readiness delta
4. building-to-case-to-pack flow for renovation decisions

Strong candidate once the first dossier wedge is tighter.

---

### J. Transaction / Insurance / Finance Readiness

Still explicitly part of the imagined product, but not the best immediate focus:

1. `safe_to_sell`
2. `safe_to_insure`
3. `safe_to_finance`
4. buyer/seller proof packs
5. insurer/lender-specific readiness rules

These should follow the core dossier wedge, not precede it.

---

### K. Owner Ops / Utility / Incident Deepening

Real remaining work, mostly valuable after the proof/readiness wedge is stronger:

1. owner ops
2. recurring services
3. warranties
4. incidents/claims/continuity
5. utility/service twin depth

Important for the long run, not the current giant lot.

---

### L. Material / Circularity / Post-Works Depth

Still part of the broader vision:

1. material/system passports
2. circularity outputs
3. richer post-works truth
4. component lifecycle depth

This should stay out of the immediate wedge closeout unless directly needed.

---

## Horizon 4 — Not Now

These should remain explicitly deferred for now:

1. new moonshot planning
2. broad category re-framing
3. marketplace-style expansion
4. generic “AI layer” enlargement without a direct product consumer
5. giant new document/doctrine packs
6. broad Europe-wide expansion work not anchored to the current wedge
7. new top-level UI centers
8. network effects work without real partner pull

---

## Recommended Big-Batch Order

If the goal is to stop doing 5-6 sessions for one outcome, the best sequence is:

### Batch 1 — G1 Wedge Closeout

One giant coherent lot:
- safe-to-start dossier flow
- readiness
- missing proof -> actions
- authority-ready pack
- feedback/complement reopen loop
- demoable end-to-end proof

### Batch 2 — Rail 3 Batch 2 + Rules/Procedure Support

Only the remaining infra and procedure depth that strengthens the first wedge lot:
- spatial enrichment reliability
- cantonal procedure reliability
- any required dossier-rule tightening

### Batch 3 — Rail 4 / 6 Market-Readiness Step

Only after the wedge feels genuinely closed:
- manifest / import-export / partner API / exchange protocol depth

### Batch 4 — Second Vertical Slice

Choose one only:
- renovation/subsidy readiness
- transaction/insurance/finance readiness

---

## What “All Remaining Tasks” Really Means Here

This backlog is intentionally not:

- every speculative idea in `docs/product-frontier-map.md`
- every imaginable layer from the full 48-month horizon
- every low-priority cleanup item

It is:

- the merged list of the remaining known work that still matters
- structured so execution can move in large, coherent, high-leverage lots

For speculative or far-horizon additions:
- keep using `docs/product-frontier-map.md`

For active execution:
- use this backlog and choose one coherent batch

---

## Recommended Default Decision Rule

Before starting the next session, require that the chosen lot answers at least one of these:

1. does it make the wedge more sellable?
2. does it close a benchmark gap that blocks `Grade A` in a way the wedge can use?
3. does it reduce debt that is already slowing active product work?

If not:
- defer it

The default answer from this backlog should currently be:

- `Batch 1 — G1 Safe-to-Start Dossier Vertical Closeout`
