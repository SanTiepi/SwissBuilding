# W86-A Header Dropdown Keyboard A11y

## Task

- outcome: close keyboard accessibility gaps in header dropdowns (Escape close + menu semantics).
- visible consumer window (`<=2 waves`): immediate, fixes W85-A findings `H1/H2`.
- done definition (one line): language and user dropdowns are keyboard-closable and semantically valid.

## Agent usage

- `Tu peux utiliser tes agents si pertinent, notamment pour Header keyboard behavior et tests front.`

## Scope

- in scope:
  - add Escape-close behavior for language and user dropdowns
  - add missing menu semantics (`menuitem` or equivalent compliant pattern)
  - update focused unit/e2e coverage
- out of scope:
  - broad header redesign

## Target files

- primary file(s):
  - `frontend/src/components/Header.tsx`
- satellites:
  - `frontend/src/components/__tests__/Header.test.tsx`
  - `frontend/e2e/navigation.spec.ts`
- change mode:
  - `new`:
    - none required
  - `modify`:
    - files above only
- do-not-touch:
  - `frontend/src/i18n/en.ts`
  - `frontend/src/i18n/fr.ts`
  - `frontend/src/i18n/de.ts`
  - `frontend/src/i18n/it.ts`

## Hard constraints

- preserve existing desktop/mobile visual behavior
- keep control targets touch-safe (>=44px)
- no regression on CommandPalette trigger behavior

## Validate loop

- run -> fix -> rerun until clean:
  - yes
- commands:
  - `cd frontend && npm run validate`
  - `cd frontend && npm test -- Header`
  - `cd frontend && npm run test:e2e -- navigation.spec.ts`
- acceptance evidence:
  - test output + short note confirming Escape close and keyboard reachability

## Exit

- functional:
  - header dropdowns close via Escape and remain keyboard navigable
- validation:
  - commands green
- orchestrator updates:
  - set W86-A status + debrief lines

