# ChangeSignal Consumer Inventory (2026-03-28)

Per ADR-004, ChangeSignal is a compatibility surface. BuildingSignal is canonical.
This document inventories every consumer and classifies migration priority.

## Bridge Status

`change_tracker_service.detect_signals()` already bridges:
1. Calls `generate_signals_for_building()` (creates ChangeSignal records)
2. Converts each new ChangeSignal into a BuildingSignal record
3. Both tables populated when called through the bridge

**Gap**: ~~Seeds (`seed_scenarios.py`, `seed_demo_authority.py`) call `generate_signals_for_building()` directly, bypassing the bridge.~~ **MIGRATED 2026-03-28**: Both seeds now call `detect_signals()` via the bridge.

## Backend Consumers

### Model & Schema (keep indefinitely until table retirement)

| File | Usage | Classification |
|---|---|---|
| `backend/app/models/change_signal.py` | Model definition | Keep (compatibility surface, labeled) |
| `backend/app/schemas/change_signal.py` | Pydantic schemas (Create/Update/Read) | Keep (compatibility surface, labeled) |
| `backend/app/models/__init__.py` | Hub import of ChangeSignal | Keep (required while model exists) |

### API Layer (keep temporarily)

| File | Usage | Classification |
|---|---|---|
| `backend/app/api/change_signals.py` | CRUD routes for ChangeSignal (list, create, get, update, delete) | Keep temporarily (labeled). Migrate frontend to building_changes API, then retire. |
| `backend/app/api/router.py` | Includes change_signals router | Keep temporarily (remove when API retired) |
| `backend/app/dependencies.py` | RBAC permissions for `change_signals` resource | Keep temporarily (remove when API retired) |

### Service Layer

| File | Usage | Classification |
|---|---|---|
| `backend/app/services/change_signal_generator.py` | Creates ChangeSignal records (7 detectors) | Keep as detection engine (labeled). Bridge in change_tracker_service ensures BuildingSignal also created. |
| `backend/app/services/change_tracker_service.py` | Bridge: calls generator, converts to BuildingSignal + portfolio signals query | Keep (this IS the bridge) |
| `backend/app/services/requalification_service.py` | ~~Reads ChangeSignal for timeline entries (3 queries)~~ | **MIGRATED 2026-03-28** -- now reads from BuildingSignal |
| `backend/app/services/weak_signal_watchtower.py` | ~~Reads ChangeSignal for weak signal detection~~ | **MIGRATED 2026-03-28** -- now reads from BuildingSignal |
| `backend/app/services/notification_digest_service.py` | ~~Reads ChangeSignal for digest sections + metrics~~ | **MIGRATED 2026-03-28** -- now reads from BuildingSignal |
| `backend/app/services/portfolio_summary_service.py` | ~~COUNT query on ChangeSignal for portfolio alerts~~ | **MIGRATED 2026-03-28** -- now reads from BuildingSignal |
| `backend/app/services/portfolio_risk_trends_service.py` | ~~COUNT query on ChangeSignal for risk trend signals~~ | **MIGRATED 2026-03-28** -- now reads from BuildingSignal |

### Seeds & Verification

| File | Usage | Classification |
|---|---|---|
| `backend/app/seeds/seed_scenarios.py` | Calls `detect_signals()` via bridge | **MIGRATED 2026-03-28** -- now uses `change_tracker_service.detect_signals()` (populates both tables) |
| `backend/app/seeds/seed_demo_authority.py` | Calls `detect_signals()` via bridge | **MIGRATED 2026-03-28** -- now uses `change_tracker_service.detect_signals()` (populates both tables) |
| `backend/app/seeds/seed_verify.py` | Checks ChangeSignal table count | Keep temporarily (remove when table retired) |

### Tests

| File | Usage | Classification |
|---|---|---|
| `backend/tests/test_change_signal_generator.py` | Unit tests for generator | Keep (tests the detection engine) |
| `backend/tests/test_change_signals.py` | API route tests | Keep temporarily (remove with API) |
| `backend/tests/test_portfolio_change_signals.py` | Portfolio signal endpoint tests | Keep temporarily |
| `backend/tests/test_portfolio_summary.py` | ~~References ChangeSignal in portfolio tests~~ | **MIGRATED 2026-03-28** -- now uses BuildingSignal |
| `backend/tests/test_notification_digest.py` | ~~References ChangeSignal in digest tests~~ | **MIGRATED 2026-03-28** -- now uses BuildingSignal |
| `backend/tests/test_portfolio_risk_trends.py` | ~~References ChangeSignal in risk trend tests~~ | **MIGRATED 2026-03-28** -- now uses BuildingSignal |
| `backend/tests/test_weak_signal_watchtower.py` | ~~References ChangeSignal in watchtower tests~~ | **MIGRATED 2026-03-28** -- now uses BuildingSignal |
| `backend/tests/test_requalification_service.py` | ~~References ChangeSignal in requalification tests~~ | **MIGRATED 2026-03-28** -- now uses BuildingSignal |

## Frontend Consumers

| File | Usage | Classification |
|---|---|---|
| `frontend/src/api/changeSignals.ts` | API client (list, listPortfolio, get, acknowledge, resolve) | Keep temporarily -- still used by deprecated ChangeSignals page |
| `frontend/src/api/buildingSignals.ts` | **Canonical** API client (listActive, listPortfolio, acknowledge, resolve) | Canonical -- used by ChangeSignalsFeed + PortfolioSignalsFeed + DataQuality |
| `frontend/src/components/ChangeSignalsFeed.tsx` | Building overview feed widget | **MIGRATED 2026-03-28** -- now reads from canonical `/buildings/{id}/signals` via `buildingSignalsApi` |
| `frontend/src/pages/ChangeSignals.tsx` | Full change signals page (filter, bulk ack) | **DEPRECATED 2026-03-28** -- deprecation banner added, still functional via legacy API |
| `frontend/src/components/PortfolioSignalsFeed.tsx` | Portfolio-level signals feed | **MIGRATED 2026-03-28** -- now reads from canonical `/portfolio/signals` via `buildingSignalsApi` |
| `frontend/src/pages/DataQuality.tsx` | ~~Uses changeSignalsApi.listPortfolio() for signal section~~ | **MIGRATED 2026-03-28** -- now reads from canonical `/portfolio/signals` via `buildingSignalsApi` |
| `frontend/src/components/building-detail/OverviewTab.tsx` | Imports ChangeSignalsFeed component | No change needed -- ChangeSignalsFeed already migrated to canonical API |

### Frontend Tests

| File | Usage | Classification |
|---|---|---|
| `frontend/src/components/__tests__/ChangeSignalsFeed.test.tsx` | Unit test for feed component | **MIGRATED 2026-03-28** -- now mocks `buildingSignalsApi` |
| `frontend/src/components/__tests__/PortfolioSignalsFeed.test.tsx` | Unit test for portfolio feed | **MIGRATED 2026-03-28** -- now mocks `buildingSignalsApi` |
| `frontend/src/components/__tests__/BuildingDetailPage.test.tsx` | Mocks ChangeSignalsFeed component | No change needed -- mocks the component by name, component itself is migrated |
| `frontend/src/components/__tests__/BuildingDetailLeases.test.tsx` | Mocks ChangeSignalsFeed component | No change needed -- mocks the component by name, component itself is migrated |

## Migration Priority

### P1 -- Frontend (do first, highest user impact)
Switch all frontend consumers from `/change-signals` API to `/building-changes` API.
**Effort**: 1 wave (4-6 files, mostly API client swap + type updates)
**Status**: **DONE (2026-03-28)**. All frontend consumers migrated. ChangeSignals page remains as deprecated compatibility surface.

### P2 -- Backend read services (do second)
Switch 5 backend services from ChangeSignal reads to BuildingSignal reads:
- requalification_service.py
- weak_signal_watchtower.py
- notification_digest_service.py
- portfolio_summary_service.py
- portfolio_risk_trends_service.py

**Effort**: 1 wave (query rewrites, same shape data)
**Status**: **DONE (2026-03-28)**. All 5 services migrated + 5 test files updated.

### P3 -- Seeds (do third)
Switch seeds from `generate_signals_for_building()` to `detect_signals()` so both tables are populated.
**Effort**: Trivial (2 files, 1-line change each)
**Status**: **DONE (2026-03-28)**. Both seed_scenarios.py and seed_demo_authority.py migrated.

### P4 -- API retirement (do last)
Remove `change_signals.py` API routes, router inclusion, RBAC entries.
**Effort**: Small but requires P1 complete first.
**Status**: Ready to execute. All consumers migrated. Only the deprecated ChangeSignals.tsx page still uses the legacy API.

### P5 -- Table retirement (future)
Migrate historical data if needed, drop `change_signals` table, remove model.
**Effort**: Data migration + Alembic, do when consumer count = 0.

## New Canonical Endpoints Added (2026-03-28)

| Endpoint | Service | Purpose |
|---|---|---|
| `GET /portfolio/signals` | `change_tracker_service.get_portfolio_signals()` | Portfolio-level signal listing (replaces `/portfolio/change-signals`) |

## Retirement Timeline

| Phase | Description | Status | Target |
|---|---|---|---|
| Phase 1 | Freeze semantics (ADR-004, compatibility labels) | Done | 2026-03-28 |
| Phase 2 | Migrate all consumers to BuildingSignal | Done | 2026-03-28 |
| Phase 3 | Add API deprecation headers (RFC 8594 Deprecation + Sunset) | Done | 2026-03-28 |
| Phase 4 | Remove compatibility API endpoints (`change_signals.py`, router entry, RBAC) | Planned | 2026-09 |
| Phase 5 | Remove model/schema/generator + drop `change_signals` table after data migration | Planned | 2026-12 |

**Deprecation headers active on all 6 endpoints**:
- `Deprecation: true`
- `Sunset: 2026-09-30`
- `Link: </api/v1/buildings/{id}/signals>; rel="successor-version"`

**Phase 4 prerequisites**: All frontend/backend consumers already migrated. Only the deprecated `ChangeSignals.tsx` page still calls the legacy API (shows deprecation banner).

**Phase 5 prerequisites**: Phase 4 complete + historical ChangeSignal data migrated to BuildingSignal table (or confirmed expendable).

## Summary

- **Total consumers**: 29 files (14 backend, 9 frontend, 6 tests) + 1 new canonical API client
- **Already bridged**: Yes (change_tracker_service.detect_signals())
- **Compatibility labels added**: 8 files (4 backend, 4 frontend)
- **Migrated (2026-03-28 Rail 1)**: 4 consumers (ChangeSignalsFeed, ChangeSignals page deprecated, seed_scenarios, seed_demo_authority) + 1 test
- **Migrated (2026-03-28 Rail 2)**: 12 consumers (5 backend services + 5 backend tests + 2 frontend components + 1 frontend test + 1 new portfolio endpoint)
- **Migrated (2026-03-28 Rail 3)**: API deprecation headers added to all 6 endpoints + retirement timeline documented
- **Total migrated**: 16 consumers + 1 new canonical endpoint
- **Remaining compatibility-only references**: 12 files (model, schema, API, generator, bridge, hub import, router, dependencies, seed_verify, 3 compatibility tests)
- **Non-compatibility ChangeSignal consumers remaining**: **0**
- **No breaking changes**: All existing reads continue to work (deprecation headers inform clients of sunset)
