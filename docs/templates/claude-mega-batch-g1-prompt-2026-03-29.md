# Claude Mega Batch Prompt — G1 Wedge Closeout

Use with:
- `docs/projects/remaining-work-master-backlog-2026-03-29.md`
- `docs/market/baticonnect-board-investor-memo-2026-03-28.md`
- `docs/projects/baticonnect-ultimate-product-manifesto-2026-03-28.md`
- `docs/projects/swissbuilding-moonshot-v2-autonomous-market-infrastructure-plan-2026-03-28.md`
- `AGENTS.md`
- `MEMORY.md`
- `ORCHESTRATOR.md`

---

## Full Prompt

```md
G1 starts now.

Do not start another generic moonshot.
Do not start another doctrine sprint.
Do not switch context every hour.

We are now doing one large coherent lot:
`G1 — Safe-to-Start Dossier Vertical Closeout`

Assume the following are already true and must not be reopened:
- canonical doctrine is settled
- the repo is stable and clean
- C1-C3 decomposition work is closed
- source reliability Rail 3 batch 1 is closed
- validation baseline is materially cleaner
- the current benchmark state is B+

Read and use as active references:
- `docs/projects/remaining-work-master-backlog-2026-03-29.md`
- `docs/market/baticonnect-board-investor-memo-2026-03-28.md`
- `docs/projects/baticonnect-ultimate-product-manifesto-2026-03-28.md`
- `docs/projects/swissbuilding-moonshot-v2-autonomous-market-infrastructure-plan-2026-03-28.md`
- `AGENTS.md`
- `MEMORY.md`
- `ORCHESTRATOR.md`

Mission:
close one sellable, demoable, end-to-end wedge flow for the Swiss `VD/GE` regulated pre-work pollutant dossier.

The product promise to embody is:
"Before work starts, the client can know what is proven, what is missing, and whether the dossier is actually ready to move forward."

This lot must feel like one coherent user-visible workflow, not 6 mini-projects.

## Desired End State

For one seeded building/case flow, the system should support:

1. initial dossier state
2. visible proof / unknown / missing / contradiction posture
3. readiness verdict in canonical surfaces
4. missing dossier elements turned into actions/review/tasks
5. authority-ready pack generation with conformance visible
6. pack delivery/submission/receipt state
7. complement/return feedback reopens the correct blockers/actions
8. the dossier visibly moves toward authority-ready

## Canonical Surfaces That Must Feel Coherent

- `Today`
- `Building Home`
- `Case Room`
- `Pack Builder`
- a minimal portfolio/readiness summary only if it directly supports the flow

## Non-Negotiable Functional Outcomes

- one explicit canonical readiness state for the wedge scenario
- one visible missing-proof / blocker loop
- one user-visible action or review queue path from missing evidence to next step
- one authority-ready pack path
- one complement or return path that invalidates/reopens correctly
- one real proof path:
  - seeded scenario
  - and/or integration/e2e proof

## Allowed Internal Shape

You may decompose implementation into at most 3 internal sublots if needed, for example:
- readiness and blocker loop
- pack + submission/receipt loop
- proof/demo/e2e closeout

But do not turn those into separate strategy sessions.
This remains one giant lot with one closeout.

## Hard Rules

- no new top-level product centers
- no doctrine reopening
- no broad new frontier expansion
- no unrelated infra sprints
- no abstract refactor unless strictly needed by this flow
- no parallel truths
- no doc-heavy progress without product leverage
- no splitting this into 5-6 mini-sessions

## What You May Pull In If Needed

You may include narrowly-scoped support work only if it directly strengthens G1:
- remaining Rail 3 adapter work that the dossier flow actually consumes
- small procedure/rules tightening for `VD/GE`
- small partner/exchange glue if needed for the submission/receipt path
- small frontend/runtime fixes required to make the flow coherent

## What You Must Not Pull In

- broad market infrastructure work
- a new Grade A push for its own sake
- a second vertical slice (transaction/insurance/finance or renovation/subsidy)
- broad repo cleanup unrelated to this wedge
- new moonshot docs

## Execution Style

- optimize for one giant coherent closeout
- use at most 3 disjoint internal lots if needed
- keep commits bounded and reviewable
- use targeted validation during work
- use one meaningful closeout report at the end
- update `ORCHESTRATOR.md` only for real execution truth

## Return Before Coding

Return only:
- the 2-3 internal sublots you will use
- the exact user-visible end state you are closing
- the files/surfaces you expect to touch
- the validation strategy

Then execute directly.

## Final Return Format

- what user-visible flow is now closed
- what surfaces became coherent
- what validations ran
- what tests/e2e prove the flow
- what remains outside G1
- whether G1 is commercially demoable now

Do not optimize for elegance of planning.
Optimize for one giant leap in the actual sellable wedge.
```

---

## Compact Prompt

```md
G1 starts now.

Use:
- `docs/projects/remaining-work-master-backlog-2026-03-29.md`
- `docs/market/baticonnect-board-investor-memo-2026-03-28.md`
- `AGENTS.md`
- `MEMORY.md`
- `ORCHESTRATOR.md`

Mission:
close one giant coherent wedge lot:
`Safe-to-Start Dossier Vertical Closeout`

End state:
- one seeded building/case shows:
  - proof / unknown / missing posture
  - readiness verdict
  - missing proof -> actions/review
  - authority-ready pack generation
  - submission/receipt/complement loop
  - visible progress toward readiness

Canonical surfaces:
- Today
- Building Home
- Case Room
- Pack Builder

Rules:
- no doctrine reopening
- no new top-level surfaces
- no broad expansion
- no splitting into 5-6 mini-sessions
- max 3 internal sublots
- only pull in extra infra if it directly supports this wedge flow

Return first:
- internal sublots
- end state
- files touched
- validation strategy

Then implement directly and close the lot.
```
