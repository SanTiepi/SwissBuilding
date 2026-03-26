import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/utils/formatters';
import { intelligenceApi } from '@/api/intelligence';
import {
  Shield,
  Loader2,
  AlertTriangle,
  Link2,
  Clock,
  CheckCircle2,
  ArrowRight,
  Building2,
  TrendingUp,
  TrendingDown,
  Minus,
  Download,
  DollarSign,
  CalendarDays,
} from 'lucide-react';

// --- Score color helpers ---

function fragmentationColor(score: number): string {
  if (score < 30) return 'text-emerald-600 dark:text-emerald-400';
  if (score < 60) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

function fragmentationBg(score: number): string {
  if (score < 30) return 'bg-emerald-100 dark:bg-emerald-900/30';
  if (score < 60) return 'bg-yellow-100 dark:bg-yellow-900/30';
  return 'bg-red-100 dark:bg-red-900/30';
}

function defensibilityColor(score: number): string {
  if (score >= 70) return 'text-emerald-600 dark:text-emerald-400';
  if (score >= 40) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

function defensibilityBg(score: number): string {
  if (score >= 70) return 'bg-emerald-100 dark:bg-emerald-900/30';
  if (score >= 40) return 'bg-yellow-100 dark:bg-yellow-900/30';
  return 'bg-red-100 dark:bg-red-900/30';
}

// --- KPI card ---

function KpiCard({
  label,
  value,
  icon,
  colorClass,
  bgClass,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  colorClass: string;
  bgClass: string;
}) {
  return (
    <div
      className="flex flex-col items-center gap-2 p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
      data-testid="indispensability-kpi"
    >
      <div className={cn('p-2 rounded-lg', bgClass, colorClass)}>{icon}</div>
      <span className={cn('text-2xl font-black', colorClass)}>{value}</span>
      <span className="text-[11px] text-slate-500 dark:text-slate-400 text-center leading-tight">{label}</span>
    </div>
  );
}

// --- Main page ---

export default function IndispensabilityDashboard() {
  const { t } = useTranslation();
  useAuth();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const orgId = user?.organization_id;

  const { data, isLoading, isError } = useQuery({
    queryKey: ['portfolio-indispensability', orgId],
    queryFn: () => intelligenceApi.getPortfolioIndispensability(orgId!),
    enabled: !!orgId,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const { data: ledger } = useQuery({
    queryKey: ['value-ledger', orgId],
    queryFn: () => intelligenceApi.getValueLedger(orgId!),
    enabled: !!orgId,
    retry: false,
    staleTime: 60 * 1000,
  });

  const { data: valueEvents } = useQuery({
    queryKey: ['value-events', orgId, 20],
    queryFn: () => intelligenceApi.getValueEvents(orgId!, 20),
    enabled: !!orgId,
    retry: false,
    staleTime: 60 * 1000,
  });

  const handleExport = () => {
    if (!orgId) return;
    // Navigate to a portfolio-level export; building-level uses /indispensability-export/:buildingId
    window.open(`/indispensability-export/${orgId}`, '_blank');
  };

  if (!orgId) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-slate-500 dark:text-slate-400 text-sm">
          {t('triage.no_org') || 'Aucune organisation associee'}
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2.5 rounded-xl bg-red-600 text-white shadow-lg">
          <Shield className="w-6 h-6" />
        </div>
        <div className="flex-1">
          <h1
            className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white"
            data-testid="indispensability-title"
          >
            {t('indispensability.dashboard_title') || 'Indispensabilite'}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t('indispensability.dashboard_subtitle') || 'Preuve de valeur de SwissBuilding pour votre portefeuille'}
          </p>
        </div>
        <button
          onClick={handleExport}
          className="hidden sm:flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors shadow-sm shrink-0"
        >
          <Download className="w-4 h-4" />
          {t('indispensability.export_button') || 'Exporter le rapport'}
        </button>
      </div>

      {/* Value Ledger */}
      {ledger && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6" data-testid="value-ledger">
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 text-center">
            <DollarSign className="w-5 h-5 text-red-500 mx-auto mb-1" />
            <p className="text-3xl font-black text-red-600 dark:text-red-400">
              {ledger.value_chf_estimate.toLocaleString('ch')}
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
              {t('value.estimated_value') || 'Valeur estimee'} (CHF)
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 text-center">
            <Clock className="w-5 h-5 text-blue-500 mx-auto mb-1" />
            <p className="text-3xl font-black text-blue-600 dark:text-blue-400">{ledger.hours_saved_estimate}h</p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
              {t('value.hours_saved') || 'Heures economisees'}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 text-center">
            <CalendarDays className="w-5 h-5 text-emerald-500 mx-auto mb-1" />
            <p className="text-3xl font-black text-emerald-600 dark:text-emerald-400">
              {Math.round(ledger.value_per_day)}
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
              {t('value.value_per_day') || 'Valeur / jour'} (CHF)
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              {ledger.trend === 'growing' && <TrendingUp className="w-5 h-5 text-emerald-500" />}
              {ledger.trend === 'stable' && <Minus className="w-5 h-5 text-slate-400" />}
              {ledger.trend === 'declining' && <TrendingDown className="w-5 h-5 text-red-500" />}
            </div>
            <p
              className={cn(
                'text-xl font-bold',
                ledger.trend === 'growing'
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : ledger.trend === 'declining'
                    ? 'text-red-600 dark:text-red-400'
                    : 'text-slate-600 dark:text-slate-400',
              )}
            >
              {t(`value.trend_${ledger.trend}`) || ledger.trend}
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
              {ledger.days_active} {t('value.days_active') || 'Jours actifs'}
            </p>
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20" data-testid="indispensability-loading">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div
          className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm"
          data-testid="indispensability-error"
        >
          {t('indispensability.error') || "Erreur lors du chargement de l'indispensabilite"}
        </div>
      )}

      {data && (
        <>
          {/* Key message */}
          <div
            className="p-5 rounded-xl bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 border border-red-200 dark:border-red-800 mb-6"
            data-testid="portfolio-headline"
          >
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200 leading-relaxed">
              {t('indispensability.portfolio_message') ||
                'SwissBuilding unifie {sources} sources, resout {contradictions} contradictions et economise {hours} heures de travail manuel pour votre portefeuille.'}{' '}
              <span className="font-black text-red-600 dark:text-red-400">
                {data.total_proof_chains} {t('indispensability.proof_chains_label') || 'chaines de preuve'}
              </span>{' '}
              {t('indispensability.protect_portfolio') || 'protegent votre portefeuille.'}
            </p>
          </div>

          {/* Summary KPI cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-8" data-testid="portfolio-kpis">
            <KpiCard
              label={t('indispensability.avg_fragmentation') || 'Fragmentation moy.'}
              value={`${Math.round(data.avg_fragmentation_score)}%`}
              icon={<AlertTriangle className="w-4 h-4" />}
              colorClass={fragmentationColor(data.avg_fragmentation_score)}
              bgClass={fragmentationBg(data.avg_fragmentation_score)}
            />
            <KpiCard
              label={t('indispensability.avg_defensibility') || 'Defensibilite moy.'}
              value={`${Math.round(data.avg_defensibility_score * 100)}%`}
              icon={<Shield className="w-4 h-4" />}
              colorClass={defensibilityColor(data.avg_defensibility_score * 100)}
              bgClass={defensibilityBg(data.avg_defensibility_score * 100)}
            />
            <KpiCard
              label={t('indispensability.total_contradictions') || 'Contradictions resolues'}
              value={String(data.total_contradictions_resolved)}
              icon={<CheckCircle2 className="w-4 h-4" />}
              colorClass="text-emerald-600 dark:text-emerald-400"
              bgClass="bg-emerald-100 dark:bg-emerald-900/30"
            />
            <KpiCard
              label={t('indispensability.total_proof_chains') || 'Chaines de preuve'}
              value={String(data.total_proof_chains)}
              icon={<Link2 className="w-4 h-4" />}
              colorClass="text-blue-600 dark:text-blue-400"
              bgClass="bg-blue-100 dark:bg-blue-900/30"
            />
            <KpiCard
              label={t('indispensability.total_hours_saved') || 'Heures economisees'}
              value={`${data.total_cost_of_fragmentation_hours}h`}
              icon={<Clock className="w-4 h-4" />}
              colorClass="text-red-600 dark:text-red-400"
              bgClass="bg-red-100 dark:bg-red-900/30"
            />
          </div>

          {/* Cost of fragmentation banner */}
          <div
            className="rounded-xl border border-red-200 dark:border-red-800 bg-red-50/50 dark:bg-red-900/10 p-6 text-center mb-8"
            data-testid="portfolio-fragmentation-cost"
          >
            <Clock className="w-8 h-8 text-red-500 mx-auto mb-2" />
            <p className="text-5xl font-black text-red-600 dark:text-red-400">
              {data.total_cost_of_fragmentation_hours}h
            </p>
            <p className="text-sm text-red-700 dark:text-red-300 mt-2">
              {t('indispensability.portfolio_hours_saved') ||
                "heures de travail manuel economisees sur l'ensemble du portefeuille"}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              {data.buildings_count} {t('indispensability.buildings_covered') || 'batiments couverts'}
            </p>
          </div>

          {/* Worst buildings */}
          {data.worst_buildings.length > 0 && (
            <div data-testid="worst-buildings">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                {t('indispensability.worst_buildings') || 'Batiments les plus fragiles (fragmentation elevee)'}
              </h2>
              <div className="space-y-2">
                {data.worst_buildings.map((b) => (
                  <button
                    key={b.building_id}
                    type="button"
                    onClick={() => navigate(`/buildings/${b.building_id}`)}
                    className="w-full flex items-center gap-4 px-4 py-3.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-all text-left group"
                    data-testid="worst-building-row"
                  >
                    <Building2 className="w-5 h-5 text-slate-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">{b.address}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={cn(
                          'inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-bold',
                          fragmentationColor(b.fragmentation_score),
                          fragmentationBg(b.fragmentation_score),
                        )}
                      >
                        {Math.round(b.fragmentation_score)}%
                      </span>
                      <span className="text-[11px] text-slate-500 dark:text-slate-400">
                        {t('indispensability.fragmentation_label') || 'fragmentation'}
                      </span>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300 shrink-0 transition-colors" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Value timeline */}
          {valueEvents && valueEvents.length > 0 && (
            <div className="mt-8" data-testid="value-timeline">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-blue-500" />
                {t('value.timeline_title') || 'Evenements de valeur recents'}
              </h2>
              <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 divide-y divide-slate-100 dark:divide-slate-800 max-h-80 overflow-y-auto">
                {valueEvents.map((evt, i) => (
                  <div key={i} className="flex items-center gap-3 px-4 py-3 text-sm">
                    <span className="relative flex h-2.5 w-2.5 shrink-0">
                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
                    </span>
                    <span className="flex-1 text-slate-700 dark:text-slate-300 min-w-0 truncate">
                      {evt.delta_description}
                    </span>
                    <span className="text-[11px] text-slate-400 dark:text-slate-500 shrink-0">
                      {new Date(evt.created_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Mobile export button */}
          <div className="mt-6 sm:hidden">
            <button
              onClick={handleExport}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
            >
              <Download className="w-4 h-4" />
              {t('indispensability.export_button') || 'Exporter le rapport'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
