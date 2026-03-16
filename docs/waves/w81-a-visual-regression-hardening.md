# W81-A Visual Regression Hardening

## Mission

- business outcome: stabilize visual regression checks so UI confidence stays high before external walkthroughs.
- user/problem context: flaky screenshot comparisons create noise and hide real regressions.
- visible consumer window (`<=2 waves`): immediate; this unblocks rank #1 acceptance in current Next 10.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour stabiliser le spec visuel, snapshots, et assertions Playwright.`

## Scope

- in scope:
  - harden `visual-regression` mock e2e spec assertions and waits
  - refresh only truly changed baseline snapshots
  - reduce deterministic flake sources (timing, animation, unstable selectors)
- out of scope:
  - real e2e scenario logic (`frontend/e2e-real/*`)
  - business feature changes in app pages/components

## Target files

- primary file(s):
  - `frontend/e2e/visual-regression.spec.ts` (modify)
- satellites (tests/schemas/routes):
  - `frontend/e2e/screenshot-audit.spec.ts` (modify)
  - `frontend/e2e/visual-regression.spec.ts-snapshots/dashboard-chromium-win32.png` (modify only if expected)
  - `frontend/e2e/visual-regression.spec.ts-snapshots/buildings-list-chromium-win32.png` (modify only if expected)
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
  - no change to backend contracts or payload assumptions
- technical constraints:
  - avoid broad timeout inflation; prefer deterministic waits/selectors
  - keep test runtime disciplined (no blanket retries hiding issues)
- repo conventions to preserve:
  - keep mock e2e and real e2e concerns separated

## Validation

- validation type:
  - `canonical_integration`: visual regression and screenshot audit run clean in mock e2e path
  - `targeted_unit_api`: not applicable
- commands to run:
  - `cd frontend && npm run test:e2e -- visual-regression.spec.ts screenshot-audit.spec.ts`
- required test level:
  - targeted Playwright mock specs green
- acceptance evidence to report:
  - spec output summary (pass count)
  - list of snapshot files changed with rationale

## Exit criteria

- functional:
  - visual regression and screenshot audit specs are stable and green
- quality/reliability:
  - no new flaky waits or broad retry hacks
- docs/control-plane updates:
  - mark W81-A status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - redesign of pages
  - new feature work

## Deliverables

- code:
  - hardened visual regression specs and approved baseline updates
- tests:
  - targeted mock e2e specs passing
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:
