import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { ErrorBoundary, PageErrorBoundary } from '@/components/ErrorBoundary';
import { ProtectedRoute } from '@/components/ProtectedRoute';

const Login = lazy(() => import('@/pages/Login'));
const Dashboard = lazy(() => import('@/pages/Dashboard'));
const BuildingsList = lazy(() => import('@/pages/BuildingsList'));
const BuildingDetail = lazy(() => import('@/pages/BuildingDetail'));
const DiagnosticView = lazy(() => import('@/pages/DiagnosticView'));
const Settings = lazy(() => import('@/pages/Settings'));
const NotFound = lazy(() => import('@/pages/NotFound'));

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
const Documents = lazy(() => import('@/pages/Documents'));
const Actions = lazy(() => import('@/pages/Actions'));
const BuildingExplorer = lazy(() => import('@/pages/BuildingExplorer'));
const BuildingInterventions = lazy(() => import('@/pages/BuildingInterventions'));
const BuildingPlans = lazy(() => import('@/pages/BuildingPlans'));
const BuildingTimelinePage = lazy(() => import('@/pages/BuildingTimeline'));
const Portfolio = lazy(() => import('@/pages/Portfolio'));
const Campaigns = lazy(() => import('@/pages/Campaigns'));
const ExportJobs = lazy(() => import('@/pages/ExportJobs'));
const ReadinessWallet = lazy(() => import('@/pages/ReadinessWallet'));
const InterventionSimulator = lazy(() => import('@/pages/InterventionSimulator'));
const SafeToXCockpit = lazy(() => import('@/pages/SafeToXCockpit'));
const BuildingComparison = lazy(() => import('@/pages/BuildingComparison'));
const AuthorityPacks = lazy(() => import('@/pages/AuthorityPacks'));
const SharedView = lazy(() => import('@/pages/SharedView'));
const PublicIntake = lazy(() => import('@/pages/PublicIntake'));
const FieldObservations = lazy(() => import('@/pages/FieldObservations'));
const ControlTower = lazy(() => import('@/pages/ControlTower'));
const AuthoritySubmissionRoom = lazy(() => import('@/pages/AuthoritySubmissionRoom'));
const DemoRunbook = lazy(() => import('@/pages/DemoRunbook'));
const PilotDashboard = lazy(() => import('@/pages/PilotDashboard'));
const AdminRollout = lazy(() => import('@/pages/AdminRollout'));
const AdminExpansion = lazy(() => import('@/pages/AdminExpansion'));
const AdminCustomerSuccess = lazy(() => import('@/pages/AdminCustomerSuccess'));

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
          path="/intake"
          element={
            <Suspense fallback={<LoadingSpinner />}>
              <PublicIntake />
            </Suspense>
          }
        />
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route
              path="/dashboard"
              element={
                <PageErrorBoundary pageName="Dashboard">
                  <Suspense fallback={<LoadingSpinner />}>
                    <Dashboard />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
            <Route
              path="/control-tower"
              element={
                <PageErrorBoundary pageName="Control Tower">
                  <Suspense fallback={<LoadingSpinner />}>
                    <ControlTower />
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
            <Route
              path="/portfolio"
              element={
                <PageErrorBoundary pageName="Portfolio">
                  <Suspense fallback={<LoadingSpinner />}>
                    <Portfolio />
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
            <Route
              path="/actions"
              element={
                <PageErrorBoundary pageName="Actions">
                  <Suspense fallback={<LoadingSpinner />}>
                    <Actions />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
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
            <Route
              path="/documents"
              element={
                <PageErrorBoundary pageName="Documents">
                  <Suspense fallback={<LoadingSpinner />}>
                    <Documents />
                  </Suspense>
                </PageErrorBoundary>
              }
            />
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
