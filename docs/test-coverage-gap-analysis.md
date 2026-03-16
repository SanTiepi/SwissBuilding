# Test Coverage Gap Analysis — W85-C

> Date: 2026-03-10
> Scope: `CommandPalette.tsx`, `BuildingCard.tsx`

## CommandPalette.tsx

### Current inventory (2 tests)

| Test | Signal |
|------|--------|
| Fallback to building search when cross-entity unavailable | Error recovery path |
| Error state when search and fallback both fail | Double-failure path |

### Gaps identified

| Gap | Severity | Added? | Rationale |
|-----|----------|--------|-----------|
| Keyboard nav (ArrowDown/ArrowUp/Enter) through results | HIGH | YES | Core a11y + UX flow |
| Escape key closes palette | HIGH | YES | Primary dismiss path |
| Successful cross-entity search renders grouped results | HIGH | YES | Happy path was untested |
| Type filter pills change search scope | MEDIUM | YES | Branch coverage for filter state |
| Quick actions panel opens via Tab on building result | MEDIUM | YES | Integration-relevant keyboard flow |
| Navigate to result on Enter | HIGH | YES | Core interaction |
| Returns null when open=false | LOW | NO | Trivial guard, low signal |
| Recent buildings from localStorage | MEDIUM | NO | Would require localStorage mock, moderate signal but complex setup for limited branch coverage |
| Backdrop click calls onClose | LOW | NO | Simple onClick passthrough |
| onClose called from close button | LOW | NO | Simple button click |

## BuildingCard.tsx

### Current inventory (10 tests)

| Test | Signal |
|------|--------|
| Renders address and city | Basic render |
| Renders canton badge | Basic render |
| Renders construction year | Basic render |
| Renders "--" when construction_year null | Branch |
| Displays risk level key | Basic render |
| Displays unknown risk when no risk_scores | Branch |
| Navigates on click | Core interaction |
| Custom onClick overrides navigate | Branch |
| Renders building type key | Basic render |
| Keyboard accessible via Enter | a11y |

### Gaps identified

| Gap | Severity | Added? | Rationale |
|-----|----------|--------|-----------|
| Space key triggers handleClick | HIGH | YES | a11y spec: space + enter both trigger action elements |
| Fallback icon for unknown building_type | MEDIUM | YES | Branch in typeIcons lookup |
| Freshness color logic (recent/stale/old) | MEDIUM | YES | 4 time-based branches in getFreshnessColor |
| Surface area shown when no updated_at | MEDIUM | YES | Conditional render branch |
| Neither updated_at nor surface_area renders nothing extra | LOW | YES | Edge case branch |
| aria-label composition | LOW | NO | String interpolation, low defect risk |
| Risk color styling applied correctly | LOW | NO | Testing inline styles = brittle, low signal |

## Design decisions

- **No label-text assertions**: testing `t(key)` output is low signal since the mock returns the key.
- **Freshness test uses Date mocking**: necessary to exercise all 4 time brackets deterministically.
- **Quick actions test exercises keyboard flow end-to-end**: Tab -> ArrowDown -> Enter, not just isolated state.
- **Test count discipline**: added 6 tests to CommandPalette and 4 to BuildingCard — each exercises a distinct branch or interaction path.
