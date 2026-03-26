import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { intelligenceApi } from '@/api/intelligence';
import { useNavigate } from 'react-router-dom';
import {
  Shield,
  ShieldOff,
  AlertTriangle,
  Link2,
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  Download,
  ListTree,
} from 'lucide-react';
import ScoreExplainabilityView from '@/components/building-detail/ScoreExplainabilityView';

interface IndispensabilityViewProps {
  buildingId: string;
}

// --- Gauge component ---

function ScoreGauge({ value, label, invert }: { value: number; label: string; invert?: boolean }) {
  // value is 0-100 for fragmentation, 0-1 for defensibility (scaled to %)
  const pct = Math.round(Math.min(100, Math.max(0, value)));
  const getColor = (v: number) => {
    if (invert) {
      // fragmentation: low is good
      if (v < 30) return 'text-emerald-500';
      if (v < 60) return 'text-yellow-500';
      return 'text-red-500';
    }
    // defensibility: high is good
    if (v >= 70) return 'text-emerald-500';
    if (v >= 40) return 'text-yellow-500';
    return 'text-red-500';
  };
  const getBg = (v: number) => {
    if (invert) {
      if (v < 30) return 'bg-emerald-500';
      if (v < 60) return 'bg-yellow-500';
      return 'bg-red-500';
    }
    if (v >= 70) return 'bg-emerald-500';
    if (v >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-24 h-24">
        {/* Background circle */}
        <svg className="w-24 h-24 -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="42"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-slate-200 dark:text-slate-700"
          />
          <circle
            cx="50"
            cy="50"
            r="42"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeDasharray={`${pct * 2.64} ${264 - pct * 2.64}`}
            strokeLinecap="round"
            className={getColor(pct)}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cn('text-xl font-black', getColor(pct))}>{pct}%</span>
        </div>
      </div>
      <span className="text-xs font-medium text-slate-600 dark:text-slate-400 text-center">{label}</span>
      <div className="w-full h-1.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-700', getBg(pct))}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

// --- System badge ---

function SystemBadge({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800">
      <XCircle className="w-3 h-3" />
      {label}
    </span>
  );
}

// --- Main component ---

export default function IndispensabilityView({ buildingId }: IndispensabilityViewProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [showExplainability, setShowExplainability] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['indispensability', buildingId],
    queryFn: () => intelligenceApi.getIndispensabilityReport(buildingId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-red-600" />
      </div>
    );
  }

  if (isError || !data) return null;

  const { fragmentation, defensibility, counterfactual } = data;
  const withP = counterfactual.with_platform;
  const withoutP = counterfactual.without_platform;

  return (
    <div className="space-y-5" data-testid="indispensability-view">
      {/* Section header */}
      <div className="flex items-center gap-2">
        <Shield className="w-5 h-5 text-red-600" />
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex-1">
          {t('indispensability.title') || 'Indispensabilite'}
        </h2>
        <button
          onClick={() => navigate(`/indispensability-export/${buildingId}`)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors border border-red-200 dark:border-red-800"
        >
          <Download className="w-3.5 h-3.5" />
          {t('indispensability.export_button') || 'Exporter'}
        </button>
      </div>

      {/* Headline */}
      <div
        className="p-4 rounded-xl bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 border border-red-200 dark:border-red-800"
        data-testid="indispensability-headline"
      >
        <p className="text-sm font-semibold text-slate-800 dark:text-slate-200 leading-relaxed">{data.headline}</p>
      </div>

      {/* Avec / Sans comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="avec-sans-comparison">
        {/* WITH platform */}
        <div className="rounded-xl border-2 border-emerald-300 dark:border-emerald-700 bg-emerald-50/50 dark:bg-emerald-900/10 p-5 space-y-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-emerald-500 text-white">
              <Shield className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-emerald-800 dark:text-emerald-300">
              {t('indispensability.with_platform') || 'Avec SwissBuilding'}
            </h3>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400">
                {t('indispensability.sources') || 'Sources unifiees'}
              </p>
              <p className="text-2xl font-black text-emerald-700 dark:text-emerald-300">{withP.sources}</p>
            </div>
            <div>
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400">
                {t('indispensability.contradictions') || 'Contradictions'}
              </p>
              <p className="text-2xl font-black text-emerald-700 dark:text-emerald-300">
                {withP.contradictions_visible}{' '}
                <span className="text-xs font-normal">{t('indispensability.resolved') || 'resolues'}</span>
              </p>
            </div>
            <div>
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400">
                {t('indispensability.proof_chains') || 'Chaines de preuve'}
              </p>
              <p className="text-2xl font-black text-emerald-700 dark:text-emerald-300">{withP.proof_chains}</p>
            </div>
            <div>
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400">
                {t('indispensability.grade') || 'Note'}
              </p>
              <p className="text-2xl font-black text-emerald-700 dark:text-emerald-300">{withP.grade || '-'}</p>
            </div>
            <div>
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400">
                {t('indispensability.trust') || 'Confiance'}
              </p>
              <p className="text-lg font-bold text-emerald-700 dark:text-emerald-300">
                {Math.round(withP.trust * 100)}%
              </p>
            </div>
            <div>
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400">
                {t('indispensability.completeness') || 'Completude'}
              </p>
              <p className="text-lg font-bold text-emerald-700 dark:text-emerald-300">
                {Math.round(withP.completeness * 100)}%
              </p>
            </div>
          </div>
        </div>

        {/* WITHOUT platform */}
        <div className="rounded-xl border-2 border-slate-300 dark:border-slate-600 bg-slate-100/50 dark:bg-slate-800/50 p-5 space-y-3 opacity-80">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-slate-400 dark:bg-slate-600 text-white">
              <ShieldOff className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-slate-600 dark:text-slate-400">
              {t('indispensability.without_platform') || 'Sans SwissBuilding'}
            </h3>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-[11px] text-slate-500 dark:text-slate-500">
                {t('indispensability.sources') || 'Sources unifiees'}
              </p>
              <p className="text-2xl font-black text-slate-500 dark:text-slate-500">{withoutP.sources}</p>
            </div>
            <div>
              <p className="text-[11px] text-slate-500 dark:text-slate-500">
                {t('indispensability.contradictions') || 'Contradictions'}
              </p>
              <p className="text-2xl font-black text-slate-500 dark:text-slate-500">
                {withoutP.contradictions_visible}{' '}
                <span className="text-xs font-normal">{t('indispensability.invisible') || 'invisibles'}</span>
              </p>
            </div>
            <div>
              <p className="text-[11px] text-slate-500 dark:text-slate-500">
                {t('indispensability.proof_chains') || 'Chaines de preuve'}
              </p>
              <p className="text-2xl font-black text-slate-500 dark:text-slate-500">{withoutP.proof_chains}</p>
            </div>
            <div>
              <p className="text-[11px] text-slate-500 dark:text-slate-500">{t('indispensability.grade') || 'Note'}</p>
              <p className="text-2xl font-black text-slate-500 dark:text-slate-500">{withoutP.grade || '?'}</p>
            </div>
            <div>
              <p className="text-[11px] text-slate-500 dark:text-slate-500">
                {t('indispensability.trust') || 'Confiance'}
              </p>
              <p className="text-lg font-bold text-slate-500 dark:text-slate-500">
                {Math.round(withoutP.trust * 100)}%
              </p>
            </div>
            <div>
              <p className="text-[11px] text-slate-500 dark:text-slate-500">
                {t('indispensability.completeness') || 'Completude'}
              </p>
              <p className="text-lg font-bold text-slate-500 dark:text-slate-500">
                {Math.round(withoutP.completeness * 100)}%
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Gauges row */}
      <div className="grid grid-cols-2 gap-4" data-testid="indispensability-gauges">
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 flex flex-col items-center">
          <ScoreGauge
            value={fragmentation.fragmentation_score}
            label={t('indispensability.fragmentation_score') || 'Score de fragmentation'}
            invert
          />
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 flex flex-col items-center">
          <ScoreGauge
            value={defensibility.defensibility_score * 100}
            label={t('indispensability.defensibility_score') || 'Score de defensibilite'}
          />
        </div>
      </div>

      {/* Cost of fragmentation */}
      <div
        className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50/50 dark:bg-red-900/10 p-6 text-center"
        data-testid="fragmentation-cost"
      >
        <Clock className="w-6 h-6 text-red-500 mx-auto mb-2" />
        <p className="text-4xl font-black text-red-600 dark:text-red-400">
          {counterfactual.cost_of_fragmentation_hours}h
        </p>
        <p className="text-sm text-red-700 dark:text-red-300 mt-1">
          {t('indispensability.hours_saved') || 'heures de travail manuel economisees'}
        </p>
      </div>

      {/* Vulnerability points */}
      {defensibility.vulnerability_points.length > 0 && (
        <div
          className="rounded-xl border border-orange-200 dark:border-orange-800 bg-orange-50/50 dark:bg-orange-900/10 p-4"
          data-testid="vulnerability-points"
        >
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-orange-600 dark:text-orange-400" />
            <h3 className="text-sm font-semibold text-orange-800 dark:text-orange-300">
              {t('indispensability.vulnerability_points') || 'Points de vulnerabilite'}
            </h3>
          </div>
          <ul className="space-y-1.5">
            {defensibility.vulnerability_points.map((point, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-red-700 dark:text-red-400">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 mt-1 shrink-0" />
                {point}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Systems replaced */}
      {fragmentation.systems_replaced.length > 0 && (
        <div
          className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4"
          data-testid="systems-replaced"
        >
          <div className="flex items-center gap-2 mb-3">
            <Link2 className="w-4 h-4 text-slate-500 dark:text-slate-400" />
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              {t('indispensability.systems_replaced') || 'Systemes remplaces'}
            </h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {fragmentation.systems_replaced.map((sys, i) => (
              <SystemBadge key={i} label={sys} />
            ))}
          </div>
        </div>
      )}

      {/* Additional stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-3 text-center">
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {t('indispensability.docs_with_provenance') || 'Docs avec provenance'}
          </p>
          <p className="text-lg font-bold text-slate-800 dark:text-slate-200">
            <span className="text-emerald-600 dark:text-emerald-400">{fragmentation.documents_with_provenance}</span>
            <span className="text-slate-400 mx-1">/</span>
            <span className="text-slate-500">
              {fragmentation.documents_with_provenance + fragmentation.documents_without_provenance}
            </span>
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-3 text-center">
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {t('indispensability.decisions_traced') || 'Decisions tracees'}
          </p>
          <p className="text-lg font-bold text-slate-800 dark:text-slate-200">
            <span className="text-emerald-600 dark:text-emerald-400">{defensibility.decisions_with_full_trace}</span>
            <span className="text-slate-400 mx-1">/</span>
            <span className="text-slate-500">
              {defensibility.decisions_with_full_trace + defensibility.decisions_without_trace}
            </span>
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-3 text-center">
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {t('indispensability.snapshots') || 'Snapshots'}
          </p>
          <p className="text-lg font-bold text-slate-800 dark:text-slate-200">{defensibility.snapshots_count}</p>
        </div>
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-3 text-center">
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {t('indispensability.time_coverage') || 'Couverture temporelle'}
          </p>
          <p className="text-lg font-bold text-slate-800 dark:text-slate-200">
            {defensibility.time_coverage_days}{' '}
            <span className="text-xs font-normal text-slate-500">{t('indispensability.days') || 'jours'}</span>
          </p>
        </div>
      </div>

      {/* Delta highlights */}
      {counterfactual.delta.length > 0 && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
          <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
            {t('indispensability.delta_highlights') || 'Ce que SwissBuilding change'}
          </h3>
          <ul className="space-y-1">
            {counterfactual.delta.map((d, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-slate-700 dark:text-slate-300">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 mt-0.5 shrink-0" />
                {d}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Score Explainability toggle */}
      <div className="flex justify-center">
        <button
          onClick={() => setShowExplainability(!showExplainability)}
          className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors border border-slate-200 dark:border-slate-700"
        >
          <ListTree className="w-4 h-4" />
          {t('score_explainability.toggle_button') || 'Detail des scores'}
        </button>
      </div>

      {showExplainability && <ScoreExplainabilityView buildingId={buildingId} />}
    </div>
  );
}
