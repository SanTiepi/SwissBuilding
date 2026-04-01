# Page Migration Inventory — 2026-03-28

Per V3 migration plan (Pass 3). Each page is labeled with its future state.

## Legend

| Label | Meaning |
|---|---|
| CANONICAL | Master workspace — owns canonical truth for its domain |
| ABSORB INTO X | Will be folded into master workspace X |
| KEEP BOUNDED | Remains as specialist projection view — must not own canonical truth |
| DEPRECATE | Scheduled for removal — orphaned or superseded |

## Canonical Workspaces (3)

| File | Route | Label |
|---|---|---|
| Today.tsx | /today | CANONICAL — primary entry |
| BuildingDetail.tsx | /buildings/:id | CANONICAL — Building Home |
| PortfolioCommand.tsx | /portfolio-command | CANONICAL — Portfolio Command |

## Absorb Pages — 6 REDIRECTED, 3 pending

| File | Route | Target | Status |
|---|---|---|---|
| Dashboard.tsx | /dashboard | Today | REDIRECTED (2026-03-28) |
| Portfolio.tsx | /portfolio | PortfolioCommand | REDIRECTED (2026-03-28) |
| PortfolioTriage.tsx | /portfolio-triage | PortfolioCommand | REDIRECTED (2026-03-28) |
| ControlTower.tsx | /control-tower | Today | REDIRECTED (2026-03-28) |
| Actions.tsx | /actions | Today | REDIRECTED (2026-03-28) |
| Documents.tsx | /documents | Today | REDIRECTED (2026-03-28) |
| BuildingsList.tsx | /buildings | PortfolioCommand | Pending — primary hub, kept active |
| BuildingTimeline.tsx | /buildings/:id/timeline | BuildingDetail | Pending — contextual sub-page |
| ReadinessWallet.tsx | /buildings/:id/readiness | BuildingDetail | Pending — contextual sub-page |

## Keep Bounded Pages (39)

### Under BuildingDetail (Building Home)

| File | Route | Parent |
|---|---|---|
| BuildingExplorer.tsx | /buildings/:id/explorer | BuildingDetail |
| BuildingInterventions.tsx | /buildings/:id/interventions | BuildingDetail |
| BuildingPlans.tsx | /buildings/:id/plans | BuildingDetail |
| SafeToXCockpit.tsx | /buildings/:id/safe-to-x | BuildingDetail |
| InterventionSimulator.tsx | /buildings/:id/simulator | BuildingDetail |
| AuthoritySubmissionRoom.tsx | /buildings/:id/procedures/:pid/authority-room | BuildingDetail |
| FieldObservations.tsx | /buildings/:id/field-observations | BuildingDetail |
| BuildingDecisionView.tsx | /buildings/:id/decision | BuildingDetail |
| ExtractionReview.tsx | /buildings/:id/extractions/:eid | BuildingDetail |
| DiagnosticView.tsx | /diagnostics/:id | BuildingDetail |

### Under PortfolioCommand

| File | Route | Parent |
|---|---|---|
| BuildingComparison.tsx | /comparison | PortfolioCommand |
| Campaigns.tsx | /campaigns | PortfolioCommand |
| PollutantMap.tsx | /map | PortfolioCommand |

### Standalone Specialist Views

| File | Route | Domain |
|---|---|---|
| ExportJobs.tsx | /exports | Cross-cutting utility |
| RiskSimulator.tsx | /risk-simulator | Cross-cutting risk simulation |
| AuthorityPacks.tsx | /authority-packs | Transfer workspace |
| Settings.tsx | /settings | User settings |
| AddressPreview.tsx | /address-preview | Address lookup utility |
| RulesPackStudio.tsx | /rules-studio | Regulatory rules studio |
| DemoPath.tsx | /demo-path | Demo guided path |
| PilotScorecard.tsx | /pilot-scorecard | Pilot scorecard |
| IndispensabilityDashboard.tsx | /indispensability | Indispensability metrics |
| IndispensabilityExportView.tsx | /indispensability-export/:id | Indispensability export |

### Admin Pages

| File | Route |
|---|---|
| AdminUsers.tsx | /admin/users |
| AdminOrganizations.tsx | /admin/organizations |
| AdminInvitations.tsx | /admin/invitations |
| AdminJurisdictions.tsx | /admin/jurisdictions |
| AdminAuditLogs.tsx | /admin/audit-logs |
| AdminProcedures.tsx | /admin/procedures |
| AdminDiagnosticReview.tsx | /admin/diagnostic-review |
| AdminIntakeReview.tsx | /admin/intake-review |
| AdminRollout.tsx | /admin/rollout |
| AdminExpansion.tsx | /admin/expansion |
| AdminCustomerSuccess.tsx | /admin/customer-success |
| AdminGovernanceSignals.tsx | /admin/governance-signals |
| AdminContributorGateway.tsx | /admin/contributor-gateway |
| AdminImportReview.tsx | /admin/import-review |
| RemediationIntelligence.tsx | /admin/remediation-intelligence |

### Marketplace Pages

| File | Route |
|---|---|
| MarketplaceCompanies.tsx | /marketplace/companies |
| MarketplaceRFQ.tsx | /marketplace/rfq |
| MarketplaceReviews.tsx | /admin/marketplace-reviews |
| CompanyWorkspace.tsx | /marketplace/company-workspace |
| OperatorWorkspace.tsx | /marketplace/operator-workspace |

### Not Routed but Kept

| File | Route | Notes |
|---|---|---|
| Notifications.tsx | (none) | Notification center — used as component reference |
| OrganizationSettings.tsx | (none) | Org settings — used as component reference |

## Deprecate Pages (6)

| File | Route | Replacement |
|---|---|---|
| Assignments.tsx | (none — orphaned) | BuildingDetail assignments tab |
| BuildingSamples.tsx | (none — orphaned) | BuildingDetail diagnostics tab |
| ChangeSignals.tsx | (none — orphaned) | BuildingDetail activity tab + building_changes API (frozen per ADR-004) |
| ComplianceArtefacts.tsx | (none — orphaned) | AuthorityPacks + BuildingDetail |
| DataQuality.tsx | (none — orphaned) | BuildingDetail trust/quality panels |
| SavedSimulations.tsx | (none — orphaned) | InterventionSimulator |

## Auth/Shell Pages (not labeled — infrastructure)

| File | Route | Notes |
|---|---|---|
| Login.tsx | /login | Auth entry |
| SharedView.tsx | /shared/:token | Public shared view |
| PublicIntake.tsx | /intake | Public intake form |
| NotFound.tsx | * | 404 fallback |

## Summary

| Category | Count |
|---|---|
| CANONICAL | 3 |
| ABSORB — REDIRECTED | 6 |
| ABSORB — pending | 3 |
| KEEP BOUNDED | 47 |
| DEPRECATE | 6 |
| Auth/Shell (unlabeled) | 4 |
| **Total page files** | **69** |
| **Standalone routes (bounded)** | **12** (was 18, -6 absorbed) |
