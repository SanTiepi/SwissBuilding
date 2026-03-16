import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { sharedLinksApi, type SharedPassportResponse } from '@/api/sharedLinks';
import type { PassportSummary } from '@/api/passport';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  Shield,
  CheckCircle2,
  XCircle,
  Clock,
  Stethoscope,
  FlaskConical,
  FileText,
  Wrench,
  AlertTriangle,
  Loader2,
} from 'lucide-react';

const GRADE_COLORS: Record<string, { bg: string; text: string; ring: string }> = {
  A: {
    bg: 'bg-emerald-100 dark:bg-emerald-900/40',
    text: 'text-emerald-700 dark:text-emerald-300',
    ring: 'ring-emerald-500',
  },
  B: { bg: 'bg-green-100 dark:bg-green-900/40', text: 'text-green-700 dark:text-green-300', ring: 'ring-green-500' },
  C: {
    bg: 'bg-yellow-100 dark:bg-yellow-900/40',
    text: 'text-yellow-700 dark:text-yellow-300',
    ring: 'ring-yellow-500',
  },
  D: {
    bg: 'bg-orange-100 dark:bg-orange-900/40',
    text: 'text-orange-700 dark:text-orange-300',
    ring: 'ring-orange-500',
  },
  F: { bg: 'bg-red-100 dark:bg-red-900/40', text: 'text-red-700 dark:text-red-300', ring: 'ring-red-500' },
};

const READINESS_GATES = ['safe_to_start', 'safe_to_tender', 'safe_to_reopen', 'safe_to_requalify'] as const;

function GradeBadge({ grade }: { grade: string }) {
  const colors = GRADE_COLORS[grade] ?? GRADE_COLORS['F'];
  return (
    <div
      className={cn(
        'flex items-center justify-center w-20 h-20 rounded-full ring-4 text-4xl font-bold',
        colors.bg,
        colors.text,
        colors.ring,
      )}
    >
      {grade}
    </div>
  );
}

function ReadinessGate({
  gate,
  data,
}: {
  gate: string;
  data: { status: string; score: number; blockers_count: number };
}) {
  const { t } = useTranslation();
  const isReady = data.status === 'ready' || data.status === 'passed';
  const label = t(`shared_view.gate_${gate}`) || gate.replace(/_/g, ' ');
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-50 dark:bg-slate-700/50">
      {isReady ? (
        <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />
      ) : (
        <XCircle className="w-4 h-4 text-red-400 shrink-0" />
      )}
      <span className="text-sm text-gray-700 dark:text-slate-300">{label}</span>
      {data.blockers_count > 0 && (
        <span className="ml-auto text-xs text-red-500 font-medium">{data.blockers_count} blockers</span>
      )}
    </div>
  );
}

function PassportContent({ data }: { data: SharedPassportResponse }) {
  const { t } = useTranslation();
  const passport: PassportSummary = data.passport;
  const trustPct = Math.round(passport.knowledge_state.overall_trust * 100);
  const completenessPct = Math.round(passport.completeness.overall_score * 100);
  const ev = passport.evidence_coverage;
  const expiresDate = new Date(data.expires_at).toLocaleDateString();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 transition-colors">
      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Logo / Branding */}
        <div className="flex items-center gap-2 mb-8">
          <Shield className="w-6 h-6 text-red-600" />
          <span className="text-lg font-bold text-gray-900 dark:text-white">SwissBuildingOS</span>
        </div>

        {/* Building Header + Grade */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm mb-6">
          <div className="flex items-center gap-5">
            <GradeBadge grade={passport.passport_grade} />
            <div className="min-w-0">
              <h1 className="text-xl font-semibold text-gray-900 dark:text-white truncate">{data.building_address}</h1>
              <p className="text-sm text-gray-500 dark:text-slate-400">
                {data.building_postal_code} {data.building_city}, {data.building_canton}
              </p>
              <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
                {t('shared_view.passport_grade')} {passport.passport_grade}
              </p>
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm">
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-1">
              {t('passport.trust') || 'Trust'}
            </p>
            <span className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums">{trustPct}%</span>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm">
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-1">
              {t('passport.completeness') || 'Completeness'}
            </p>
            <span className="text-2xl font-bold text-gray-900 dark:text-white tabular-nums">{completenessPct}%</span>
          </div>
        </div>

        {/* Readiness Gates */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm mb-6">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            {t('shared_view.readiness') || 'Readiness'}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {READINESS_GATES.map((gate) => (
              <ReadinessGate
                key={gate}
                gate={gate}
                data={passport.readiness[gate] ?? { status: 'not_evaluated', score: 0, blockers_count: 0 }}
              />
            ))}
          </div>
        </div>

        {/* Evidence Coverage */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm mb-6">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            {t('passport.evidence') || 'Evidence Coverage'}
          </h2>
          <div className="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-slate-400">
            <span className="flex items-center gap-1.5">
              <Stethoscope className="w-4 h-4" />
              {ev.diagnostics_count} diagnostics
            </span>
            <span className="flex items-center gap-1.5">
              <FlaskConical className="w-4 h-4" />
              {ev.samples_count} samples
            </span>
            <span className="flex items-center gap-1.5">
              <FileText className="w-4 h-4" />
              {ev.documents_count} documents
            </span>
            {ev.interventions_count > 0 && (
              <span className="flex items-center gap-1.5">
                <Wrench className="w-4 h-4" />
                {ev.interventions_count} interventions
              </span>
            )}
          </div>
        </div>

        {/* Blind Spots & Contradictions */}
        {(passport.blind_spots.total_open > 0 || passport.contradictions.unresolved > 0) && (
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm mb-6">
            <div className="flex gap-6 text-sm">
              {passport.blind_spots.total_open > 0 && (
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  <span className="text-gray-700 dark:text-slate-300">
                    {passport.blind_spots.total_open} {t('passport.blind_spots') || 'blind spots'}
                    {passport.blind_spots.blocking > 0 && (
                      <span className="text-red-500 ml-1">({passport.blind_spots.blocking} blocking)</span>
                    )}
                  </span>
                </div>
              )}
              {passport.contradictions.unresolved > 0 && (
                <div className="flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-red-400" />
                  <span className="text-gray-700 dark:text-slate-300">
                    {passport.contradictions.unresolved} {t('passport.contradictions') || 'contradictions'}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center text-xs text-gray-400 dark:text-slate-500 pt-4 border-t border-gray-200 dark:border-slate-700">
          {data.shared_by_org && (
            <span>
              {t('shared_view.shared_by')} {data.shared_by_org} &middot;{' '}
            </span>
          )}
          <span>
            <Clock className="w-3 h-3 inline-block mr-0.5" />
            {t('shared_view.expires')} {expiresDate}
          </span>
          <p className="mt-2 text-gray-300 dark:text-slate-600">Powered by SwissBuildingOS</p>
        </div>
      </div>
    </div>
  );
}

export default function SharedView() {
  const { token } = useParams<{ token: string }>();
  const { t } = useTranslation();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['shared-passport', token],
    queryFn: () => sharedLinksApi.passport(token!),
    enabled: !!token,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-10 h-10 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <h1 className="text-lg font-semibold text-gray-700 dark:text-slate-300">
            {t('shared_view.invalid') || 'This link is invalid or has expired'}
          </h1>
          <p className="text-sm text-gray-400 dark:text-slate-500 mt-1">
            {t('shared_view.contact_owner') || 'Please contact the link owner for a new link.'}
          </p>
        </div>
      </div>
    );
  }

  return <PassportContent data={data} />;
}
