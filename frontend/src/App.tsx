import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate, useParams } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { ErrorBoundary, PageErrorBoundary } from '@/components/ErrorBoundary';
import { ProtectedRoute } from '@/components/ProtectedRoute';

// Keep public entry routes eager so the app does not boot through a lazy-route
// suspense fallback on the first unauthenticated paint. In staging this path
// surfaced a root-level spinner mount/unmount race that could trip the global
// error boundary before the login page fully settled.
import Login from '@/pages/Login';
import SharedView from '@/pages/SharedView';
import SharedArtifactView from '@/pages/SharedArtifactView';
import PublicIntake from '@/pages/PublicIntake';
import NotFound from '@/pages/NotFound';

const Today = lazy(() => import('@/pages/Today'));
const BuildingsList = lazy(() => import('@/pages/BuildingsList'));
const BuildingDetail = lazy(() => import('@/pages/BuildingDetail'));
const DiagnosticView = lazy(() => import('@/pages/DiagnosticView'));
const Settings = lazy(() => import('@/pages/Settings'));

const AdminUsers = lazy(() => import('@/pages/AdminUsers'));
const AdminOrganizations = lazy(() => import('@/pages/AdminOrganizations'));
const AdminInvitations = lazy(() => import('@/pages/AdminInvitations'));
const AdminJurisdictions = lazy(() => import('@/pages/AdminJurisdictions'));
const AdminAuditLogs = lazy(() => import('@/pages/AdminAuditLogs'));
const AdminProcedures = lazy(() => import('@/pages/AdminProcedures'));
const AdminDiagnosticReview = lazy(() => import('@/pages/AdminDiagnosticReview'));
const AdminIntakeReview = lazy(() => import('@/pages/AdminIntakeReview'));
const RulesPackStudio = lazy(() => import('@/pages/RulesPackStudio'));

const PollutantMap = lazy(() => import('@/pages/PollutantMap'));
const RiskSimulator = lazy(() => import('@/pages/RiskSimulator'));
const BuildingExplorer = lazy(() => import('@/pages/BuildingExplorer'));
const BuildingInterventions = lazy(() => import('@/pages/BuildingInterventions'));
const BuildingPlans = lazy(() => import('@/pages/BuildingPlans'));
const BuildingTimelinePage = lazy(() => import('@/pages/BuildingTimeline'));
const Campaigns = lazy(() => import('@/pages/Campaigns'));
const ExportJobs = lazy(() => import('@/pages/ExportJobs'));
const ReadinessWallet = lazy(() => import('@/pages/ReadinessWallet'));
const InterventionSimulator = lazy(() => import('@/pages/InterventionSimulator'));
const SafeToXCockpit = lazy(() => import('@/pages/SafeToXCockpit'));
const BuildingComparison = lazy(() => import('@/pages/BuildingComparison'));
const AuthorityPacks = lazy(() => import('@/pages/AuthorityPacks'));
const FieldObservations = lazy(() => import('@/pages/FieldObservations'));
const AuthoritySubmissionRoom = lazy(() => import('@/pages/AuthoritySubmissionRoom'));
const DemoRunbook = lazy(() => import('@/pages/DemoRunbook'));
const PilotDashboard = lazy(() => import('@/pages/PilotDashboard'));
const AdminRollout = lazy(() => import('@/pages/AdminRollout'));
const AdminExpansion = lazy(() => import('@/pages/AdminExpansion'));
const AdminCustomerSuccess = lazy(() => import('@/pages/AdminCustomerSuccess'));
const AdminGovernanceSignals = lazy(() => import('@/pages/AdminGovernanceSignals'));
const MarketplaceCompanies = lazy(() => import('@/pages/MarketplaceCompanies'));
const MarketplaceRFQ = lazy(() => import('@/pages/MarketplaceRFQ'));
const MarketplaceReviews = lazy(() => import('@/pages/MarketplaceReviews'));
const CompanyWorkspace = lazy(() => import('@/pages/CompanyWorkspace'));
const OperatorWorkspace = lazy(() => import('@/pages/OperatorWorkspace'));
const RemediationIntelligence = lazy(() => import('@/pages/RemediationIntelligence'));
const AddressPreview = lazy(() => import('@/pages/AddressPreview'));
const AdminImportReview = lazy(() => import('@/pages/AdminImportReview'));
const AdminContributorGateway = lazy(() => import('@/pages/AdminContributorGateway'));
const AdminAIMetricsBoard = lazy(() => import('@/pages/AdminAIMetricsBoard'));
const BuildingDecisionView = lazy(() => import('@/pages/BuildingDecisionView'));
const DemoPath = lazy(() => import('@/pages/DemoPath'));
const PilotScorecard = lazy(() => import('@/pages/PilotScorecard'));
const ExtractionReview = lazy(() => import('@/pages/ExtractionReview'));
const IndispensabilityDashboard = lazy(() => import('@/pages/IndispensabilityDashboard'));
const IndispensabilityExportView = lazy(() => import('@/pages/IndispensabilityExportView'));
const PortfolioCommand = lazy(() => import('@/pages/PortfolioCommand'));
const Cases = lazy(() => import('@/pages/Cases'));
const CaseRoom = lazy(() => import('@/pages/CaseRoom'));
const Finance = lazy(() => import('@/pages/Finance'));
const SearchResults = lazy(() => import('@/pages/SearchResults'));

const CertificateVerificationLazy = lazy(() =>
  import('@/components/CertificateVerification').then((m) => ({
    default: m.CertificateVerification,
  })),
);

function CertificateVerifyRoute() {
  const { certificateId } = useParams<{ certificateId: string }>();
  if (!certificateId) return null;
  return <CertificateVerificationLazy certificateId={certificateId} />;
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600" />
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route
          path="/login"
          element={
            <Suspense fallback={<LoadingSpinner />}>
              <Login />
            </Suspense>
          }
        />
        <Route
          path="/shared/:token"
          element={
            <Suspense fallback={<LoadingSpinner />}>
              <SharedView />
            </Suspense>
          }
        />
        <Route
          path="/shared/:accessToken/artifact"
          element={
            <Suspense fallback={<LoadingSpinner />}>
              <SharedArtifactView />
            </Suspense>
          }
        />
        <Route
          path="/intake"
          element={
            <Suspense fallback={<LoadingSpinner />}>
              <PublicIntake />
            </Suspense>
          }
        />
        <Route
          path="/verify/:certificateId"
          element={
            <Suspense fallback={<LoadingSpinner />}>
              <CertificateVerifyRoute />
            </Suspense>
          }
        />
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/today" replace />} />
            <Route
              path="/today"
              element={
                <PageErrorBoundary pageName="Today">
                  <Suspense fallback={<LoadingSpinner />}>
                    <Today />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            {/* ABSORBED: /dashboard -> /today (was Dashboard.tsx) */}
            <Route path="/dashboard" element={<Navigate to="/today" replace />} />
            {/* ABSORBED: /control-tower -> /today (was ControlTower.tsx) */}
            <Route path="/control-tower" element={<Navigate to="/today" replace />} />
            <Route
              path="/search"
              element={
                <PageErrorBoundary pageName="Search">
                  <Suspense fallback={<LoadingSpinner />}>
                    <SearchResults />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/buildings"
              element={
                <PageErrorBoundary pageName="Buildings">
                  <Suspense fallback={<LoadingSpinner />}>
                    <BuildingsList />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/buildings/:id"
              element={
                <PageErrorBoundary pageName="Building Detail">
                  <Suspense fallback={<LoadingSpinner />}>
                    <BuildingDetail />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/buildings/:buildingId/explorer"
              element={
                <PageErrorBoundary pageName="Building Explorer">
                  <Suspense fallback={<LoadingSpinner />}>
                    <BuildingExplorer />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/buildings/:buildingId/interventions"
              element={
                <PageErrorBoundary pageName="Building Interventions">
                  <Suspense fallback={<LoadingSpinner />}>
                    <BuildingInterventions />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/buildings/:buildingId/plans"
              element={
                <PageErrorBoundary pageName="Building Plans">
                  <Suspense fallback={<LoadingSpinner />}>
                    <BuildingPlans />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/buildings/:buildingId/readiness"
              element={
                <PageErrorBoundary pageName="Readiness Wallet">
                  <Suspense fallback={<LoadingSpinner />}>
                    <ReadinessWallet />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/buildings/:buildingId/safe-to-x"
              element={
                <PageErrorBoundary pageName="Safe to X Cockpit">
                  <Suspense fallback={<LoadingSpinner />}>
                    <SafeToXCockpit />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/buildings/:buildingId/simulator"
              element={
                <PageErrorBoundary pageName="Intervention Simulator">
                  <Suspense fallback={<LoadingSpinner />}>
                    <InterventionSimulator />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/buildings/:buildingId/procedures/:procedureId/authority-room"
              element={
                <PageErrorBoundary pageName="Authority Submission Room">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AuthoritySubmissionRoom />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/buildings/:buildingId/decision"
              element={
                <PageErrorBoundary pageName="Building Decision View">
                  <Suspense fallback={<LoadingSpinner />}>
                    <BuildingDecisionView />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/buildings/:buildingId/extractions/:extractionId"
              element={
                <PageErrorBoundary pageName="Extraction Review">
                  <Suspense fallback={<LoadingSpinner />}>
                    <ExtractionReview />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/buildings/:buildingId/field-observations"
              element={
                <PageErrorBoundary pageName="Field Observations">
                  <Suspense fallback={<LoadingSpinner />}>
                    <FieldObservations />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/buildings/:buildingId/timeline"
              element={
                <PageErrorBoundary pageName="Building Timeline">
                  <Suspense fallback={<LoadingSpinner />}>
                    <BuildingTimelinePage />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/diagnostics/:id"
              element={
                <PageErrorBoundary pageName="Diagnostic">
                  <Suspense fallback={<LoadingSpinner />}>
                    <DiagnosticView />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            {/* ABSORBED: /portfolio -> /portfolio-command (was Portfolio.tsx) */}
            <Route path="/portfolio" element={<Navigate to="/portfolio-command" replace />} />
            <Route
              path="/portfolio-command"
              element={
                <PageErrorBoundary pageName="Portfolio Command">
                  <Suspense fallback={<LoadingSpinner />}>
                    <PortfolioCommand />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/cases"
              element={
                <PageErrorBoundary pageName="Cases">
                  <Suspense fallback={<LoadingSpinner />}>
                    <Cases />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/cases/:caseId"
              element={
                <PageErrorBoundary pageName="Case Room">
                  <Suspense fallback={<LoadingSpinner />}>
                    <CaseRoom />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/finance"
              element={
                <PageErrorBoundary pageName="Finance">
                  <Suspense fallback={<LoadingSpinner />}>
                    <Finance />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/campaigns"
              element={
                <PageErrorBoundary pageName="Campaigns">
                  <Suspense fallback={<LoadingSpinner />}>
                    <Campaigns />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/comparison"
              element={
                <PageErrorBoundary pageName="Building Comparison">
                  <Suspense fallback={<LoadingSpinner />}>
                    <BuildingComparison />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/risk-simulator"
              element={
                <PageErrorBoundary pageName="Risk Simulator">
                  <Suspense fallback={<LoadingSpinner />}>
                    <RiskSimulator />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/map"
              element={
                <PageErrorBoundary pageName="Map">
                  <Suspense fallback={<LoadingSpinner />}>
                    <PollutantMap />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            {/* ABSORBED: /actions -> /today (was Actions.tsx) */}
            <Route path="/actions" element={<Navigate to="/today" replace />} />
            <Route
              path="/exports"
              element={
                <PageErrorBoundary pageName="Export Jobs">
                  <Suspense fallback={<LoadingSpinner />}>
                    <ExportJobs />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/authority-packs"
              element={
                <PageErrorBoundary pageName="Authority Packs">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AuthorityPacks />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            {/* ABSORBED: /documents -> /today (was Documents.tsx) */}
            <Route path="/documents" element={<Navigate to="/today" replace />} />
            <Route
              path="/settings"
              element={
                <PageErrorBoundary pageName="Settings">
                  <Suspense fallback={<LoadingSpinner />}>
                    <Settings />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/users"
              element={
                <PageErrorBoundary pageName="Admin Users">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminUsers />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/organizations"
              element={
                <PageErrorBoundary pageName="Admin Organizations">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminOrganizations />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/invitations"
              element={
                <PageErrorBoundary pageName="Admin Invitations">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminInvitations />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/jurisdictions"
              element={
                <PageErrorBoundary pageName="Admin Jurisdictions">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminJurisdictions />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/audit-logs"
              element={
                <PageErrorBoundary pageName="Admin Audit Logs">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminAuditLogs />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/procedures"
              element={
                <PageErrorBoundary pageName="Admin Procedures">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminProcedures />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/diagnostic-review"
              element={
                <PageErrorBoundary pageName="Admin Diagnostic Review">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminDiagnosticReview />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/intake-review"
              element={
                <PageErrorBoundary pageName="Admin Intake Review">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminIntakeReview />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/demo-runbook"
              element={
                <PageErrorBoundary pageName="Demo Runbook">
                  <Suspense fallback={<LoadingSpinner />}>
                    <DemoRunbook />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/pilot-dashboard"
              element={
                <PageErrorBoundary pageName="Pilot Dashboard">
                  <Suspense fallback={<LoadingSpinner />}>
                    <PilotDashboard />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/rollout"
              element={
                <PageErrorBoundary pageName="Rollout">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminRollout />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/expansion"
              element={
                <PageErrorBoundary pageName="Expansion">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminExpansion />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/customer-success"
              element={
                <PageErrorBoundary pageName="Customer Success">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminCustomerSuccess />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/governance-signals"
              element={
                <PageErrorBoundary pageName="Governance Signals">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminGovernanceSignals />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/marketplace/companies"
              element={
                <PageErrorBoundary pageName="Marketplace Companies">
                  <Suspense fallback={<LoadingSpinner />}>
                    <MarketplaceCompanies />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/marketplace/rfq"
              element={
                <PageErrorBoundary pageName="Marketplace RFQ">
                  <Suspense fallback={<LoadingSpinner />}>
                    <MarketplaceRFQ />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/marketplace-reviews"
              element={
                <PageErrorBoundary pageName="Marketplace Reviews">
                  <Suspense fallback={<LoadingSpinner />}>
                    <MarketplaceReviews />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/marketplace/company-workspace"
              element={
                <PageErrorBoundary pageName="Company Workspace">
                  <Suspense fallback={<LoadingSpinner />}>
                    <CompanyWorkspace />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/marketplace/operator-workspace"
              element={
                <PageErrorBoundary pageName="Operator Workspace">
                  <Suspense fallback={<LoadingSpinner />}>
                    <OperatorWorkspace />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/remediation-intelligence"
              element={
                <PageErrorBoundary pageName="Remediation Intelligence">
                  <Suspense fallback={<LoadingSpinner />}>
                    <RemediationIntelligence />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/address-preview"
              element={
                <PageErrorBoundary pageName="Address Preview">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AddressPreview />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            {/* ABSORBED: /portfolio-triage -> /portfolio-command (was PortfolioTriage.tsx) */}
            <Route path="/portfolio-triage" element={<Navigate to="/portfolio-command" replace />} />
            <Route
              path="/admin/import-review"
              element={
                <PageErrorBoundary pageName="Import Review">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminImportReview />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/contributor-gateway"
              element={
                <PageErrorBoundary pageName="Contributor Gateway">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminContributorGateway />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/admin/ai-metrics"
              element={
                <PageErrorBoundary pageName="AI Metrics">
                  <Suspense fallback={<LoadingSpinner />}>
                    <AdminAIMetricsBoard />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/demo-path"
              element={
                <PageErrorBoundary pageName="Demo Path">
                  <Suspense fallback={<LoadingSpinner />}>
                    <DemoPath />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/pilot-scorecard"
              element={
                <PageErrorBoundary pageName="Pilot Scorecard">
                  <Suspense fallback={<LoadingSpinner />}>
                    <PilotScorecard />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/indispensability"
              element={
                <PageErrorBoundary pageName="Indispensability Dashboard">
                  <Suspense fallback={<LoadingSpinner />}>
                    <IndispensabilityDashboard />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/indispensability-export/:buildingId"
              element={
                <PageErrorBoundary pageName="Indispensability Export">
                  <Suspense fallback={<LoadingSpinner />}>
                    <IndispensabilityExportView />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/rules-studio"
              element={
                <PageErrorBoundary pageName="Rules Pack Studio">
                  <Suspense fallback={<LoadingSpinner />}>
                    <RulesPackStudio />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
          </Route>
        </Route>
        <Route
          path="*"
          element={
            <Suspense fallback={<LoadingSpinner />}>
              <NotFound />
            </Suspense>
          }
        />
      </Routes>
    </ErrorBoundary>
  );
}
