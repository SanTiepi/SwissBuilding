import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { intelligenceApi } from '@/api/intelligence';
import type { OperationalGate } from '@/api/intelligence';
import { Loader2, CheckCircle2, XCircle, AlertTriangle, ShieldAlert, ShieldCheck } from 'lucide-react';
import { formatDate } from '@/utils/formatters';

interface OperationalGatesViewProps {
  buildingId: string;
}

const GATE_ICONS: Record<string, string> = {
  launch_rfq: '\u{1F4CB}',
  close_lot: '\u2705',
  transfer_dossier: '\u{1F4E6}',
  start_works: '\u{1F3D7}',
  submit_authority: '\u{1F3DB}',
  sell: '\u{1F4B0}',
};

const STATUS_CONFIG: Record<string, { color: string; bg: string; border: string; label: string }> = {
  blocked: {
    color: 'text-red-700 dark:text-red-400',
    bg: 'bg-red-50 dark:bg-red-900/20',
    border: 'border-red-200 dark:border-red-800',
    label: 'operational_gates.status_blocked',
  },
  conditions_pending: {
    color: 'text-amber-700 dark:text-amber-400',
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    border: 'border-amber-200 dark:border-amber-800',
    label: 'operational_gates.status_conditions_pending',
  },
  clearable: {
    color: 'text-yellow-700 dark:text-yellow-400',
    bg: 'bg-yellow-50 dark:bg-yellow-900/20',
    border: 'border-yellow-200 dark:border-yellow-800',
    label: 'operational_gates.status_clearable',
  },
  cleared: {
    color: 'text-emerald-700 dark:text-emerald-400',
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    border: 'border-emerald-200 dark:border-emerald-800',
    label: 'operational_gates.status_cleared',
  },
  overridden: {
    color: 'text-purple-700 dark:text-purple-400',
    bg: 'bg-purple-50 dark:bg-purple-900/20',
    border: 'border-purple-200 dark:border-purple-800',
    label: 'operational_gates.status_overridden',
  },
};

function GateStatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.blocked;
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold',
        config.color,
        config.bg,
        config.border,
        'border',
      )}
    >
      {t(config.label) || status}
    </span>
  );
}

function GateCard({
  gate,
  onOverride,
  isOverriding,
}: {
  gate: OperationalGate;
  onOverride: (gateId: string, reason: string) => void;
  isOverriding: boolean;
}) {
  const { t } = useTranslation();
  const [showOverrideInput, setShowOverrideInput] = useState(false);
  const [overrideReason, setOverrideReason] = useState('');
  const icon = GATE_ICONS[gate.gate_type] || '\u{1F6AA}';
  const isCleared = gate.status === 'cleared';
  const isOverridden = gate.status === 'overridden';
  const isBlocked = gate.status === 'blocked';
  const isClearable = gate.status === 'clearable';

  return (
    <div
      className={cn(
        'rounded-xl border p-4 space-y-3 transition-all',
        isCleared
          ? 'border-emerald-200 dark:border-emerald-800 bg-emerald-50/30 dark:bg-emerald-900/10 opacity-70'
          : isOverridden
            ? 'border-purple-200 dark:border-purple-800 bg-purple-50/30 dark:bg-purple-900/10'
            : isBlocked
              ? 'border-red-200 dark:border-red-800 bg-red-50/30 dark:bg-red-900/10'
              : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900',
      )}
      data-testid={`gate-card-${gate.gate_type}`}
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-xl" role="img" aria-label={gate.gate_type}>
          {icon}
        </span>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-slate-900 dark:text-white truncate">{gate.gate_label}</h4>
        </div>
        <GateStatusBadge status={gate.status} />
      </div>

      {/* Prerequisites */}
      <ul className="space-y-1.5">
        {gate.prerequisites.map((prereq, i) => (
          <li key={i} className="flex items-center gap-2 text-xs">
            {prereq.satisfied ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
            ) : (
              <XCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />
            )}
            <span
              className={cn(
                prereq.satisfied ? 'text-slate-600 dark:text-slate-400' : 'text-red-700 dark:text-red-400 font-medium',
              )}
            >
              {prereq.label}
            </span>
          </li>
        ))}
      </ul>

      {/* Cleared date */}
      {isCleared && gate.cleared_at && (
        <p className="text-[11px] text-emerald-600 dark:text-emerald-400">
          {t('operational_gates.cleared_on') || 'Libere le'} {formatDate(gate.cleared_at)}
        </p>
      )}

      {/* Overridden info */}
      {isOverridden && gate.override_reason && (
        <div className="flex items-start gap-1.5 p-2 rounded-lg bg-purple-100/50 dark:bg-purple-900/20">
          <AlertTriangle className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400 shrink-0 mt-0.5" />
          <p className="text-[11px] text-purple-700 dark:text-purple-300">{gate.override_reason}</p>
        </div>
      )}

      {/* Actions */}
      {isClearable && (
        <button
          onClick={() => onOverride(gate.id, '__clear__')}
          disabled={isOverriding}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/30 hover:bg-emerald-200 dark:hover:bg-emerald-900/50 rounded-lg transition-colors border border-emerald-200 dark:border-emerald-800"
        >
          {isOverriding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
          {t('operational_gates.clear_button') || 'Liberer'}
        </button>
      )}

      {isBlocked && !showOverrideInput && (
        <button
          onClick={() => setShowOverrideInput(true)}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors border border-amber-200 dark:border-amber-800"
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          {t('operational_gates.override_button') || 'Forcer le passage'}
        </button>
      )}

      {showOverrideInput && (
        <div className="space-y-2">
          <textarea
            value={overrideReason}
            onChange={(e) => setOverrideReason(e.target.value)}
            placeholder={t('operational_gates.override_reason_placeholder') || 'Raison du passage force...'}
            className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 resize-none"
            rows={2}
          />
          <div className="flex gap-2">
            <button
              onClick={() => {
                if (overrideReason.trim()) {
                  onOverride(gate.id, overrideReason.trim());
                  setShowOverrideInput(false);
                  setOverrideReason('');
                }
              }}
              disabled={!overrideReason.trim() || isOverriding}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 rounded-lg transition-colors"
            >
              {isOverriding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
              {t('operational_gates.confirm_override') || 'Confirmer'}
            </button>
            <button
              onClick={() => {
                setShowOverrideInput(false);
                setOverrideReason('');
              }}
              className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            >
              {t('form.cancel') || 'Annuler'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function OperationalGatesView({ buildingId }: OperationalGatesViewProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const {
    data: gates,
    isLoading: gatesLoading,
    isError: gatesError,
  } = useQuery({
    queryKey: ['building-gates', buildingId],
    queryFn: () => intelligenceApi.getBuildingGates(buildingId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const { data: gateStatus } = useQuery({
    queryKey: ['building-gate-status', buildingId],
    queryFn: () => intelligenceApi.getBuildingGateStatus(buildingId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const overrideMutation = useMutation({
    mutationFn: ({ gateId, reason }: { gateId: string; reason: string }) =>
      intelligenceApi.overrideGate(gateId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['building-gates', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['building-gate-status', buildingId] });
    },
  });

  if (gatesLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-red-600" />
      </div>
    );
  }

  if (gatesError || !gates) return null;

  const blockedCount = gateStatus?.blocked ?? gates.filter((g) => g.status === 'blocked').length;
  const clearableCount = gateStatus?.clearable ?? gates.filter((g) => g.status === 'clearable').length;
  const clearedCount = gateStatus?.cleared ?? gates.filter((g) => g.status === 'cleared').length;
  const overriddenCount = gateStatus?.overridden ?? gates.filter((g) => g.status === 'overridden').length;

  const handleOverride = (gateId: string, reason: string) => {
    overrideMutation.mutate({ gateId, reason });
  };

  return (
    <div className="space-y-5" data-testid="operational-gates-view">
      {/* Section header */}
      <div className="flex items-center gap-2">
        <ShieldAlert className="w-5 h-5 text-red-600" />
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex-1">
          {t('operational_gates.title') || 'Portes operationnelles'}
        </h2>
      </div>

      {/* Status summary bar */}
      <div className="flex flex-wrap gap-3">
        {blockedCount > 0 && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-red-100 dark:bg-red-900/30 border border-red-200 dark:border-red-800">
            <XCircle className="w-3.5 h-3.5 text-red-600 dark:text-red-400" />
            <span className="text-xs font-semibold text-red-700 dark:text-red-400">
              {blockedCount} {t('operational_gates.blocked_label') || 'bloquees'}
            </span>
          </div>
        )}
        {clearableCount > 0 && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800">
            <AlertTriangle className="w-3.5 h-3.5 text-yellow-600 dark:text-yellow-400" />
            <span className="text-xs font-semibold text-yellow-700 dark:text-yellow-400">
              {clearableCount} {t('operational_gates.clearable_label') || 'liberables'}
            </span>
          </div>
        )}
        {clearedCount > 0 && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
              {clearedCount} {t('operational_gates.cleared_label') || 'liberees'}
            </span>
          </div>
        )}
        {overriddenCount > 0 && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-purple-100 dark:bg-purple-900/30 border border-purple-200 dark:border-purple-800">
            <ShieldAlert className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
            <span className="text-xs font-semibold text-purple-700 dark:text-purple-400">
              {overriddenCount} {t('operational_gates.overridden_label') || 'forcees'}
            </span>
          </div>
        )}
      </div>

      {/* Key message */}
      {blockedCount > 0 && (
        <div className="p-3 rounded-xl bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800">
          <p className="text-sm font-medium text-red-700 dark:text-red-400">
            {blockedCount} {t('operational_gates.blocked_message') || 'operations bloquees en attente de preuves'}
          </p>
        </div>
      )}

      {/* Gate cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {gates.map((gate) => (
          <GateCard key={gate.id} gate={gate} onOverride={handleOverride} isOverriding={overrideMutation.isPending} />
        ))}
      </div>
    </div>
  );
}
