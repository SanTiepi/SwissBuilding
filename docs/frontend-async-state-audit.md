# Frontend Async State Audit

- Surfaces scanned: `35`
- Explicit error state: `35`
- Review needed: `0`
- Missing error state: `0`

## Review Targets

| File | Queries | Error Vars | Status | Notes |
|------|---------|------------|--------|-------|
| _none_ | - | - | - | All query surfaces include explicit error handling patterns. |

## Raw Status

| File | Queries | Error Vars | Property Usage | Status |
|------|---------|------------|----------------|--------|
| `frontend/src/pages/BuildingExplorer.tsx` | 4 | `isError, zonesError` | `yes` | `explicit_error_state` |
| `frontend/src/pages/Campaigns.tsx` | 3 | `error` | `yes` | `explicit_error_state` |
| `frontend/src/components/NotificationBell.tsx` | 2 | `isError, notificationsError` | `no` | `explicit_error_state` |
| `frontend/src/pages/AdminJurisdictions.tsx` | 2 | `error` | `yes` | `explicit_error_state` |
| `frontend/src/pages/BuildingDetail.tsx` | 2 | `actionsError, activityError, error, isError` | `yes` | `explicit_error_state` |
| `frontend/src/pages/Dashboard.tsx` | 2 | `actionsError, buildingsError, diagnosticsError, isError` | `yes` | `explicit_error_state` |
| `frontend/src/components/BuildingTimeline.tsx` | 1 | `isError` | `no` | `explicit_error_state` |
| `frontend/src/components/ChangeSignalsFeed.tsx` | 1 | `isError` | `no` | `explicit_error_state` |
| `frontend/src/components/CompletenessGauge.tsx` | 1 | `isError` | `no` | `explicit_error_state` |
| `frontend/src/components/ContradictionCard.tsx` | 1 | `isError` | `yes` | `explicit_error_state` |
| `frontend/src/components/DataQualityScore.tsx` | 1 | `isError` | `no` | `explicit_error_state` |
| `frontend/src/components/EvidenceChain.tsx` | 1 | `isError` | `no` | `explicit_error_state` |
| `frontend/src/components/PassportCard.tsx` | 1 | `isError` | `yes` | `explicit_error_state` |
| `frontend/src/components/PortfolioSignalsFeed.tsx` | 1 | `isError` | `no` | `explicit_error_state` |
| `frontend/src/components/PostWorksDiffCard.tsx` | 1 | `isError` | `no` | `explicit_error_state` |
| `frontend/src/components/ProofHeatmapOverlay.tsx` | 1 | `isError` | `no` | `explicit_error_state` |
| `frontend/src/components/ReadinessSummary.tsx` | 1 | `isError` | `no` | `explicit_error_state` |
| `frontend/src/components/RequalificationTimeline.tsx` | 1 | `isError` | `yes` | `explicit_error_state` |
| `frontend/src/components/TimeMachinePanel.tsx` | 1 | `isError` | `yes` | `explicit_error_state` |
| `frontend/src/components/TrustScoreCard.tsx` | 1 | `isError` | `no` | `explicit_error_state` |
| `frontend/src/components/UnknownIssuesList.tsx` | 1 | `isError` | `no` | `explicit_error_state` |
| `frontend/src/pages/Actions.tsx` | 1 | `error` | `yes` | `explicit_error_state` |
| `frontend/src/pages/AdminAuditLogs.tsx` | 1 | `error` | `yes` | `explicit_error_state` |
| `frontend/src/pages/AdminInvitations.tsx` | 1 | `error` | `yes` | `explicit_error_state` |
| `frontend/src/pages/AdminOrganizations.tsx` | 1 | `error` | `yes` | `explicit_error_state` |
| `frontend/src/pages/AdminUsers.tsx` | 1 | `error` | `yes` | `explicit_error_state` |
| `frontend/src/pages/BuildingComparison.tsx` | 1 | `buildingsError, isError` | `yes` | `explicit_error_state` |
| `frontend/src/pages/BuildingInterventions.tsx` | 1 | `isError` | `yes` | `explicit_error_state` |
| `frontend/src/pages/BuildingPlans.tsx` | 1 | `isError` | `yes` | `explicit_error_state` |
| `frontend/src/pages/ExportJobs.tsx` | 1 | `isError` | `yes` | `explicit_error_state` |
| `frontend/src/pages/Portfolio.tsx` | 1 | `isError` | `yes` | `explicit_error_state` |
| `frontend/src/pages/ReadinessWallet.tsx` | 1 | `isError, readinessError` | `yes` | `explicit_error_state` |
| `frontend/src/pages/RiskSimulator.tsx` | 1 | `buildingsError, error, isError, savedSimsError` | `yes` | `explicit_error_state` |
| `frontend/src/pages/SafeToXCockpit.tsx` | 1 | `isError` | `yes` | `explicit_error_state` |
| `frontend/src/pages/Settings.tsx` | 1 | `error, isError, notifPrefsError` | `yes` | `explicit_error_state` |
