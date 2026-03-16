# W85-C Test Coverage Gap Analysis and Targeted Additions

## Mission

- business outcome: close high-risk test blind spots introduced by recent UI and reliability hardening.
- user/problem context: total test count is growing, but coverage needs to stay signal-driven on critical paths.
- visible consumer window (`<=2 waves`): immediate; this follows W84 and informs next hardening waves.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour analyser les gaps de couverture et ajouter des tests cibles haute valeur.`

## Scope

- in scope:
  - map coverage gaps on critical post-W81/W82/W83 surfaces
  - add targeted tests for the highest-risk uncovered paths
  - produce short report explaining chosen additions and residual gaps
- out of scope:
  - broad test inflation with low-signal assertions
  - backend test expansion unrelated to current UI hardening phase

## Target files

- primary file(s):
  - `docs/test-coverage-gap-analysis.md` (new)
- satellites (tests/schemas/routes):
  - `frontend/src/components/__tests__/CommandPalette.test.tsx` (modify)
  - `frontend/src/components/__tests__/BuildingCard.test.tsx` (modify)
- change mode:
  - `new`:
    - `docs/test-coverage-gap-analysis.md`
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
  - no contract changes
- technical constraints:
  - prioritize integration-relevant coverage, not raw count growth
  - report must document why each added test is high-signal
- repo conventions to preserve:
  - keep tests deterministic and maintainable

## Validation

- validation type:
  - `canonical_integration`: critical UI behaviors covered by targeted tests
  - `targeted_unit_api`: focused component tests green
- commands to run:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- CommandPalette BuildingCard`
- required test level:
  - focused unit tests on selected high-risk paths
- acceptance evidence to report:
  - report path + gap categories
  - pass summary for newly added/updated tests

## Exit criteria

- functional:
  - high-priority coverage gaps are reduced with explicit evidence
- quality/reliability:
  - no broad low-signal test bloat
- docs/control-plane updates:
  - mark W85-C status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - full-suite coverage perfection
  - i18n hub merge work

## Deliverables

- code:
  - targeted test additions/updates
- tests:
  - focused high-signal test coverage
- docs:
  - coverage gap analysis report

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

