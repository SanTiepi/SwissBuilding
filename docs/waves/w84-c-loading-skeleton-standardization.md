# W84-C Loading Skeleton Standardization

## Mission

- business outcome: make loading UX consistent across major screens via shared skeleton patterns.
- user/problem context: loading states are mixed (spinners + partial skeletons), reducing perceived quality.
- visible consumer window (`<=2 waves`): immediate; this closes the remaining hardening item from current Next 10.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour harmoniser Skeleton/AsyncStateWrapper et les tests frontend.`

## Scope

- in scope:
  - standardize shared skeleton usage and variants
  - align page-level loading fallbacks with shared components
  - add targeted tests for skeleton rendering contracts
- out of scope:
  - redesign of full page layouts
  - backend/API changes

## Target files

- primary file(s):
  - `frontend/src/components/Skeleton.tsx` (modify)
- satellites (tests/schemas/routes):
  - `frontend/src/components/AsyncStateWrapper.tsx` (modify)
  - `frontend/src/components/__tests__/AsyncStateWrapper.test.tsx` (modify)
  - `frontend/src/components/__tests__/SkeletonLoadingStates.test.tsx` (new)
- change mode:
  - `new`:
    - `frontend/src/components/__tests__/SkeletonLoadingStates.test.tsx`
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
  - loading components must not alter data contracts or query behavior
- technical constraints:
  - preserve accessibility semantics in loading states
  - keep loading transitions lightweight (no heavy animation debt)
- repo conventions to preserve:
  - favor reusable skeleton components over ad-hoc per-page loaders

## Validation

- validation type:
  - `canonical_integration`: shared loading wrappers render expected skeleton variants
  - `targeted_unit_api`: skeleton and wrapper tests
- commands to run:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- AsyncStateWrapper SkeletonLoadingStates`
- required test level:
  - targeted unit coverage on loading states
- acceptance evidence to report:
  - list of standardized loading patterns now in use
  - test output summary

## Exit criteria

- functional:
  - loading states are consistent on targeted surfaces
- quality/reliability:
  - shared wrappers/components are tested and regression-safe
- docs/control-plane updates:
  - mark W84-C status in `ORCHESTRATOR.md` and add debrief lines

## Non-goals

- explicitly not part of this brief:
  - broad page redesign work
  - i18n hub merge work

## Deliverables

- code:
  - standardized skeleton components and wrapper behavior
- tests:
  - targeted skeleton/loading tests
- docs:
  - none mandatory

## Wave closeout (required in ORCHESTRATOR.md)

- clear:
- fuzzy:
- missing:

