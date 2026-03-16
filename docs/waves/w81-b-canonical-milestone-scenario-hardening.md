# W81-B Canonical Milestone Scenario Hardening

## Mission

- business outcome: guarantee one canonical seeded building path from raw to complete dossier in real e2e.
- user/problem context: external gate credibility depends on a deterministic end-to-end proof chain.
- visible consumer window (`<=2 waves`): immediate; this is rank #2 in current Next 10 and supports external milestone proof.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour durcir le scenario real e2e, preflight, et runbook.`

## Scope

- in scope:
  - harden canonical real e2e smoke scenario assertions for dossier progression
  - tighten real e2e preflight checks tied to this scenario
  - sync safe-to-start runbook steps with the hardened scenario
- out of scope:
  - broad visual regression snapshot maintenance
  - unrelated frontend page feature work

## Target files

- primary file(s):
  - `frontend/e2e-real/smoke.spec.ts` (modify)
- satellites (tests/schemas/routes):
  - `frontend/e2e-real/helpers.ts` (modify)
  - `frontend/scripts/e2e_real_preflight.mjs` (modify)
  - `docs/safe-to-start-gate-runbook.md` (modify)
- change mode:
  - `new`:
    - none required
  - `modify`:
    - files listed above only
- hub-file ownership:
  - `supervisor_merge`:
    - `frontend/src/i18n/en.ts`
    - `frontend/src/i18n/fr.ts`
    - `frontend/src/i18n/de.ts`
    - `frontend/src/i18n/it.ts`
  - `agent_allowed`:
    - files listed in scope
- do-not-touch (hub files reserved to supervisor merge):
  - `frontend/src/i18n/en.ts`
  - `frontend/src/i18n/fr.ts`
  - `frontend/src/i18n/de.ts`
  - `frontend/src/i18n/it.ts`

## Non-negotiable constraints

- data/model constraints:
  - scenario must stay on seeded data, no mock-path claims
- technical constraints:
  - preflight must fail fast with actionable reason if environment drifts
  - keep scenario deterministic (no random selectors, no hidden sleeps)
- repo conventions to preserve:
  - explicit separation of real e2e vs mock e2e claims

## Validation

- validation type:
  - `canonical_integration`: real e2e smoke scenario + preflight are green
  - `targeted_unit_api`: not applicable
- commands to run:
  - `cd frontend && npm run test:e2e:real:preflight`
  - `cd frontend && npx playwright test -c playwright.real.config.ts e2e-real/smoke.spec.ts`
- required test level:
  - targeted real e2e scenario proof
- acceptance evidence to report:
  - preflight summary
  - smoke scenario pass summary
  - runbook section updated paths/commands

## Exit criteria

- functional:
  - canonical scenario verifies dossier progression end to end in real environment
- quality/reliability:
  - preflight catches known drift classes before test execution
- docs/control-plane updates:
  - mark W81-B status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - new product features
  - full safe-to-start proof bundle regeneration (that remains a closeout gate task)

## Deliverables

- code:
  - hardened real e2e smoke + preflight checks
- tests:
  - targeted real e2e smoke proof
- docs:
  - runbook sync update

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:
