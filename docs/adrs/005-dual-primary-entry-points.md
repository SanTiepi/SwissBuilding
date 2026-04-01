# ADR-005: Dual Primary Entry Points (Today + Building Home)

Status: Accepted
Date: 2026-03-28

## Decision

SwissBuilding has exactly 2 primary entry points:
- **Today** (`/today`): daily operational start — what needs action now
- **Building Home** (`/buildings/:id`): durable memory/truth start — what is this building

## Allowed

- Today aggregates cross-portfolio actions, deadlines, alerts, signals
- Building Home aggregates building-level truth, readiness, cases, changes, packs
- Case Room, Finance, Transfer, Portfolio Command as secondary workspaces
- Bounded specialist views under master workspaces

## Forbidden

- A third primary entry point
- Standalone pages that compete with Today or Building Home as daily start
- Workspace duplication where both Building Home and Case Room own canonical truth

## UX Rule

- Today is where you START your day
- Building Home is where you UNDERSTAND a building
- Case Room is where you EXECUTE a bounded episode
- Everything else is a projection or bounded specialist view
