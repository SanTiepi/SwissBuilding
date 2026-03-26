import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/utils/formatters';
import { useAuthStore } from '@/store/authStore';
import { intelligenceApi, type PortfolioTriageBuilding } from '@/api/intelligence';
import {
  AlertTriangle,
  AlertCircle,
  Eye,
  CheckCircle2,
  MapPin,
  ArrowRight,
  Loader2,
  Filter,
  Building2,
} from 'lucide-react';

// --- Status config ---

type TriageStatus = 'critical' | 'action_needed' | 'monitored' | 'under_control';

interface StatusConfig {
  label: string;
  icon: React.ReactNode;
  bgCard: string;
  bgBadge: string;
  textBadge: string;
  ringColor: string;
}

function useStatusConfig(): Record<TriageStatus, StatusConfig> {
  const { t } = useTranslation();
  return {
    critical: {
      label: t('triage.critical') || 'Critique',
      icon: <AlertTriangle className="w-5 h-5" />,
      bgCard: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
      bgBadge: 'bg-red-100 dark:bg-red-900/40',
      textBadge: 'text-red-700 dark:text-red-400',
      ringColor: 'ring-red-500/30',
    },
    action_needed: {
      label: t('triage.action_needed') || 'Action requise',
      icon: <AlertCircle className="w-5 h-5" />,
      bgCard: 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800',
      bgBadge: 'bg-orange-100 dark:bg-orange-900/40',
      textBadge: 'text-orange-700 dark:text-orange-400',
      ringColor: 'ring-orange-500/30',
    },
    monitored: {
      label: t('triage.monitored') || 'Surveille',
      icon: <Eye className="w-5 h-5" />,
      bgCard: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
      bgBadge: 'bg-yellow-100 dark:bg-yellow-900/40',
      textBadge: 'text-yellow-700 dark:text-yellow-400',
      ringColor: 'ring-yellow-500/30',
    },
    under_control: {
      label: t('triage.under_control') || 'Sous controle',
      icon: <CheckCircle2 className="w-5 h-5" />,
      bgCard: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800',
      bgBadge: 'bg-green-100 dark:bg-green-900/40',
      textBadge: 'text-green-700 dark:text-green-400',
      ringColor: 'ring-green-500/30',
    },
  };
}

// --- Grade badge ---

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-emerald-500',
  B: 'bg-green-500',
  C: 'bg-yellow-500',
  D: 'bg-orange-500',
  E: 'bg-red-500',
  F: 'bg-red-700',
};

function MiniGradeBadge({ grade }: { grade: string }) {
  const g = (grade || 'F').toUpperCase();
  return (
    <span
      className={cn(
        'inline-flex items-center justify-center w-7 h-7 rounded-lg text-xs font-black text-white',
        GRADE_COLORS[g] || GRADE_COLORS.F,
      )}
      data-testid="mini-grade-badge"
    >
      {g}
    </span>
  );
}

// --- Summary card ---

interface SummaryCardProps {
  config: StatusConfig;
  count: number;
  status: TriageStatus;
  isActive: boolean;
  onClick: () => void;
}

function SummaryCard({ config, count, status, isActive, onClick }: SummaryCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex flex-col items-center gap-1.5 p-4 rounded-xl border transition-all text-center',
        config.bgCard,
        isActive && `ring-2 ${config.ringColor} shadow-md`,
        'hover:shadow-md cursor-pointer',
      )}
      data-testid={`summary-card-${status}`}
    >
      <div className={cn('p-2 rounded-lg', config.bgBadge, config.textBadge)}>{config.icon}</div>
      <p className="text-2xl font-bold text-slate-800 dark:text-slate-200">{count}</p>
      <p className={cn('text-xs font-medium', config.textBadge)}>{config.label}</p>
    </button>
  );
}

// --- Building row ---

interface BuildingRowProps {
  building: PortfolioTriageBuilding;
  config: StatusConfig;
  onClick: () => void;
}

function BuildingRow({ building, config, onClick }: BuildingRowProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center gap-4 px-4 py-3.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-all text-left group"
      data-testid="building-row"
    >
      <MiniGradeBadge grade={building.passport_grade} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">{building.address}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <span
            className={cn(
              'inline-block px-2 py-0.5 text-[10px] font-semibold rounded-full uppercase',
              config.bgBadge,
              config.textBadge,
            )}
          >
            {config.label}
          </span>
          {building.top_blocker && (
            <span className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
              {building.top_blocker}
            </span>
          )}
        </div>
      </div>
      <div className="text-right shrink-0">
        {building.risk_score > 0 && (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Risque: {Math.round(building.risk_score * 100)}%
          </p>
        )}
        {building.next_action && (
          <p className="text-[11px] text-blue-600 dark:text-blue-400 truncate max-w-[180px]">
            {building.next_action}
          </p>
        )}
      </div>
      <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300 shrink-0 transition-colors" />
    </button>
  );
}


// --- Main page ---

export default function PortfolioTriage() {
  const { t } = useTranslation();
  useAuth();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  const orgId = user?.organization_id;

  const { data, isLoading, isError } = useQuery({
    queryKey: ['portfolio-triage', orgId],
    queryFn: () => intelligenceApi.getPortfolioTriage(orgId!),
    enabled: !!orgId,
  });

  const statusConfig = useStatusConfig();
  const [filter, setFilter] = useState<TriageStatus | 'all'>('all');

  const filteredBuildings = useMemo(() => {
    if (!data) return [];
    if (filter === 'all') return data.buildings;
    return data.buildings.filter((b) => b.status === filter);
  }, [data, filter]);

  const statusOrder: TriageStatus[] = ['critical', 'action_needed', 'monitored', 'under_control'];

  const sortedBuildings = useMemo(() => {
    return [...filteredBuildings].sort((a, b) => {
      const ai = statusOrder.indexOf(a.status as TriageStatus);
      const bi = statusOrder.indexOf(b.status as TriageStatus);
      if (ai !== bi) return ai - bi;
      return b.risk_score - a.risk_score;
    });
  }, [filteredBuildings]);

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
      <div className="flex items-center gap-3 mb-8">
        <div className="p-2.5 rounded-xl bg-red-600 text-white shadow-lg">
          <Building2 className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white" data-testid="triage-title">
            {t('triage.title') || 'Triage du portefeuille'}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t('triage.subtitle') || 'Vue evidence de vos immeubles par urgence'}
          </p>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-20" data-testid="triage-loading">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm" data-testid="triage-error">
          {t('triage.error') || 'Erreur lors du chargement du triage'}
        </div>
      )}

      {/* Data */}
      {data && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8" data-testid="summary-cards">
            <SummaryCard
              config={statusConfig.critical}
              count={data.critical_count}
              status="critical"
              isActive={filter === 'critical'}
              onClick={() => setFilter(filter === 'critical' ? 'all' : 'critical')}
            />
            <SummaryCard
              config={statusConfig.action_needed}
              count={data.action_needed_count}
              status="action_needed"
              isActive={filter === 'action_needed'}
              onClick={() => setFilter(filter === 'action_needed' ? 'all' : 'action_needed')}
            />
            <SummaryCard
              config={statusConfig.monitored}
              count={data.monitored_count}
              status="monitored"
              isActive={filter === 'monitored'}
              onClick={() => setFilter(filter === 'monitored' ? 'all' : 'monitored')}
            />
            <SummaryCard
              config={statusConfig.under_control}
              count={data.under_control_count}
              status="under_control"
              isActive={filter === 'under_control'}
              onClick={() => setFilter(filter === 'under_control' ? 'all' : 'under_control')}
            />
          </div>

          {/* Filter indicator */}
          {filter !== 'all' && (
            <div className="flex items-center gap-2 mb-4">
              <Filter className="w-4 h-4 text-slate-400" />
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {t('triage.filtering') || 'Filtre'}: {statusConfig[filter].label}
              </span>
              <button
                type="button"
                onClick={() => setFilter('all')}
                className="text-xs text-red-600 hover:text-red-700 dark:text-red-400 underline"
                data-testid="clear-filter"
              >
                {t('triage.clear_filter') || 'Effacer'}
              </button>
            </div>
          )}

          {/* Building list */}
          <div className="space-y-2" data-testid="building-list">
            {sortedBuildings.length === 0 ? (
              <div className="text-center py-12 text-slate-500 dark:text-slate-400 text-sm">
                <MapPin className="w-8 h-8 mx-auto mb-2 opacity-40" />
                {t('triage.no_buildings') || 'Aucun batiment dans cette categorie'}
              </div>
            ) : (
              sortedBuildings.map((b) => (
                <BuildingRow
                  key={b.id}
                  building={b}
                  config={statusConfig[b.status as TriageStatus] || statusConfig.under_control}
                  onClick={() => navigate(`/buildings/${b.id}`)}
                />
              ))
            )}
          </div>

          {/* Total count */}
          <p className="text-center text-xs text-slate-400 dark:text-slate-500 mt-6">
            {sortedBuildings.length} / {data.buildings.length} {t('triage.buildings') || 'batiments'}
          </p>
        </>
      )}
    </div>
  );
}
