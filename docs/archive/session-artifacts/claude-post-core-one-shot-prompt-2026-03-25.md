# Claude Post-Core One-Shot Prompt

Use this prompt when the current core macro-slice is closed and the goal is to
ship the next major product jump in one pass.

```text
Claude,

The current core macro-slice is assumed closed.

Do not reopen planning drift.
Do not break this into many small waves.

You are now shipping the next one-shot macro-slice:
regulatory freshness + local honesty + exchange backbone + trust signals +
pilot proof.

Read in this order:
1. `docs/projects/claude-post-core-one-shot-pack-2026-03-25.md`
2. `docs/projects/swissrules-watch-priority-backlog-2026-03-25.md`
3. `docs/projects/pilot-communes-pack-2026-03-25.md`
4. `docs/projects/passport-exchange-network-foundation-pack-2026-03-25.md`
5. `docs/projects/partner-trust-operating-pack-2026-03-25.md`
6. `docs/projects/public-authority-trust-signal-pack-2026-03-25.md`
7. `docs/projects/killer-demo-operating-pack-2026-03-25.md`
8. `docs/projects/pilot-scorecard-and-exit-criteria-pack-2026-03-25.md`
9. `docs/projects/claude-wave-brief-kit-2026-03-25.md`

This one-shot combines:
- `5` SwissRules Watch Foundations
- `8` Passport Exchange Network Foundations
- `9` Partner Trust Signals
- `15` Pilot Communes Foundations
- `16` Killer Demo Foundations
- `46` Procurement Evidence Ladder Surfaces
- `47` Public Authority Trust Signal Surfaces
- `50` Ecosystem Partner API Contract Foundations
- `52` ROI Proof Calculator Foundations
- `53` Pilot Design Cookbook Surfaces
- `54` Pilot Scorecard and Exit Logic
- `55` Case Study Proof Story Templates

Non-negotiable rules:
- no second rules universe outside the existing `SwissRules` spine
- no fake nationwide commune automation
- no second passport core
- no second pack engine
- no public partner star-rating system
- no marketplace behavior
- no demo-only branches
- no ROI claims without workflow-event grounding
- no trust claim without evidence trace

Implementation order:
1. regulatory watch and local honesty
2. exchange and contract backbone
3. partner and authority trust signals
4. pilot/demo proof
5. final coherence pass

Required product result:
- rules are visibly current or stale
- commune-specific caveats are explicit
- packs can be published and received under versioned contracts
- trust signals are explainable for partners and authorities
- one pilot/demo path proves workflow lift with evidence
- one case-study proof story can be generated from real product truth

Validation discipline:
- during work: changed-file loops only
- before closeout:
  - `cd backend && ruff check app/ tests/`
  - `cd backend && ruff format --check app/ tests/`
  - `cd backend && python scripts/run_local_test_loop.py changed`
  - `cd backend && python scripts/run_local_test_loop.py confidence`
  - `cd frontend && npm run validate`
  - `cd frontend && npm run test:changed:strict`
- full backend or frontend suites only once at the end

Acceptance story:
1. rule freshness and procedural implications are visible
2. commune overrides or review requirements are honest and bounded
3. an exchange publication and receipt can be traced
4. trust signals are visible and explainable
5. one seeded demo and one pilot scorecard prove value
6. one evidence-backed proof story is reusable for buyers

Finish the macro-slice, then report:
- what shipped
- what remains intentionally deferred
- what was validated
```
