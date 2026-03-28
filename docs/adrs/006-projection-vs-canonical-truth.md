# ADR-006: Projection vs Canonical Truth Rules

Status: Accepted
Date: 2026-03-28

## Decision

Pages and components are **projections**. Only models and services are **canonical truth**. No page may own truth behavior.

## Definitions

- **Canonical truth**: a model or service that is the authoritative source of state and meaning (e.g., BuildingCase, SafeToXState, TruthRitual)
- **Projection**: a read-side view that assembles and displays canonical truth for a specific audience or purpose (e.g., DossierJourney, Today feed, Portfolio Command)

## Allowed

- Projections that read from canonical sources and render for a specific context
- Projections that aggregate multiple canonical sources into a composite view
- Projections that filter, sort, or format canonical data

## Forbidden

- A page that introduces state not tracked in a canonical model
- A component that makes decisions not governed by a canonical service
- A projection that becomes "the place where this truth lives" instead of the model
- Frontend-only state that should be a model (e.g., a page-level "readiness override" not recorded in SafeToXState)

## Test

For any page or component, ask: "if this page disappeared, would we lose any truth?" If yes, that truth must be moved to a canonical model.
