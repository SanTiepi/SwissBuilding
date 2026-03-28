import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { invalidationsApi } from '@/api/invalidations';
import type { InvalidationEvent } from '@/api/invalidations';
import { cn } from '@/utils/formatters';
import { ShieldAlert, CheckCircle2, Play } from 'lucide-react';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SEVERITY_CONFIG: Record<string, { dot: string; bg: string; label: string }> = {
  critical: {
    dot: 'bg-red-600',
    bg: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
    label: 'Critique',
  },
  warning: {
    dot: 'bg-amber-500',
    bg: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
    label: 'Attention',
  },
  info: {
    dot: 'bg-blue-500',
    bg: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800',
    label: 'Info',
  },
};

const REACTION_LABELS: Record<string, string> = {
  review_required: 'Revue requise',
  republish: 'Republier',
  reopen_case: 'Rouvrir le dossier',
  refresh_safe_to_x: 'Re-evaluer SafeToX',
  update_template: 'Mettre a jour le template',
  supersede: 'Remplacer',
  notify_only: 'Notification',
};

const AFFECTED_TYPE_LABELS: Record<string, string> = {
  pack: 'Pack de preuves',
  passport: 'Passeport batiment',
  form_template: 'Template de formulaire',
  form_instance: 'Formulaire',
  safe_to_x_state: 'Etat SafeToX',
  publication: 'Publication',
  claim: 'Assertion',
  procedure_step: 'Etape de procedure',
};

// ---------------------------------------------------------------------------
// Badge count (for use in headers)
// ---------------------------------------------------------------------------

export function InvalidationBadge({ buildingId }: { buildingId?: string }) {
  const { data: buildingData } = useQuery({
    queryKey: ['invalidations', buildingId, 'count'],
    queryFn: () => invalidationsApi.getForBuilding(buildingId!, { status: 'detected', limit: 1 }),
    enabled: !!buildingId,
    refetchInterval: 60_000,
  });

  const { data: pendingData } = useQuery({
    queryKey: ['invalidations', 'pending', 'count'],
    queryFn: () => invalidationsApi.getPending({ status: 'detected', limit: 1 }),
    enabled: !buildingId,
    refetchInterval: 60_000,
  });

  const displayCount = buildingId ? (buildingData?.length ?? 0) : (pendingData?.total ?? 0);

  if (displayCount === 0) return null;

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 text-[10px] font-bold rounded-full',
        'bg-red-600 text-white',
      )}
    >
      {displayCount > 99 ? '99+' : displayCount}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Single invalidation card
// ---------------------------------------------------------------------------

function InvalidationCard({
  event,
  onResolve,
  onExecute,
}: {
  event: InvalidationEvent;
  onResolve: (id: string) => void;
  onExecute: (id: string) => void;
}) {
  const cfg = SEVERITY_CONFIG[event.severity] ?? SEVERITY_CONFIG.info;

  return (
    <div className={cn('border rounded-lg p-3 transition-colors', cfg.bg)}>
      <div className="flex items-start gap-2">
        <div className={cn('w-2 h-2 rounded-full mt-1.5 flex-shrink-0', cfg.dot)} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-slate-900 dark:text-white">
              {AFFECTED_TYPE_LABELS[event.affected_type] ?? event.affected_type}
            </span>
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300">
              {cfg.label}
            </span>
          </div>
          <p className="text-xs text-slate-700 dark:text-slate-300 mt-1">{event.trigger_description}</p>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">{event.impact_reason}</p>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-[10px] font-medium text-slate-500 dark:text-slate-400">
              {REACTION_LABELS[event.required_reaction] ?? event.required_reaction}
            </span>
            <div className="flex-1" />
            {event.status === 'detected' && (
              <>
                <button
                  onClick={() => onExecute(event.id)}
                  className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                >
                  <Play className="w-3 h-3" />
                  Executer
                </button>
                <button
                  onClick={() => onResolve(event.id)}
                  className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
                >
                  <CheckCircle2 className="w-3 h-3" />
                  Resoudre
                </button>
              </>
            )}
            {event.status === 'acknowledged' && (
              <button
                onClick={() => onResolve(event.id)}
                className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
              >
                <CheckCircle2 className="w-3 h-3" />
                Resoudre
              </button>
            )}
            {event.status === 'resolved' && (
              <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">Resolu</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Resolve modal (simple inline)
// ---------------------------------------------------------------------------

function ResolveForm({
  eventId,
  onCancel,
  onSubmit,
}: {
  eventId: string;
  onCancel: () => void;
  onSubmit: (id: string, note: string) => void;
}) {
  const [note, setNote] = useState('');

  return (
    <div className="mt-2 p-3 rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800">
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Note de resolution..."
        className="w-full text-xs p-2 border border-slate-200 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white resize-none"
        rows={2}
      />
      <div className="flex justify-end gap-2 mt-2">
        <button
          onClick={onCancel}
          className="text-[10px] font-medium px-3 py-1 rounded border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700"
        >
          Annuler
        </button>
        <button
          onClick={() => onSubmit(eventId, note)}
          disabled={!note.trim()}
          className="text-[10px] font-medium px-3 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50"
        >
          Confirmer
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main panel: for building detail or Today page
// ---------------------------------------------------------------------------

export default function InvalidationAlerts({ buildingId }: { buildingId?: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const { data, isLoading } = useQuery<InvalidationEvent[]>({
    queryKey: ['invalidations', buildingId],
    queryFn: async (): Promise<InvalidationEvent[]> => {
      if (buildingId) {
        return invalidationsApi.getForBuilding(buildingId, { status: 'detected' });
      }
      const resp = await invalidationsApi.getPending({ status: 'detected', limit: 20 });
      return resp.items;
    },
    refetchInterval: 60_000,
  });

  const events = data ?? [];

  const resolveMutation = useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) => invalidationsApi.resolve(id, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invalidations'] });
      setResolvingId(null);
    },
  });

  const executeMutation = useMutation({
    mutationFn: (id: string) => invalidationsApi.executeReaction(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invalidations'] });
    },
  });

  if (isLoading) {
    return <div className="animate-pulse h-20 rounded-xl bg-slate-200 dark:bg-slate-700" />;
  }

  if (events.length === 0) return null;

  const criticalCount = events.filter((e) => e.severity === 'critical').length;
  const warningCount = events.filter((e) => e.severity === 'warning').length;

  return (
    <div className="rounded-xl border bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100 dark:border-slate-700">
        <ShieldAlert className="w-4 h-4 text-red-500" />
        <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
          {t('invalidation.title') || 'Invalidations detectees'}
        </h2>
        <div className="flex items-center gap-1.5 ml-auto">
          {criticalCount > 0 && (
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-600 text-white">
              {criticalCount} {t('invalidation.critical') || 'critique(s)'}
            </span>
          )}
          {warningCount > 0 && (
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500 text-white">
              {warningCount} {t('invalidation.warning') || 'attention'}
            </span>
          )}
        </div>
      </div>

      {/* List */}
      <div className="p-3 space-y-2 max-h-[400px] overflow-y-auto">
        {events.map((event) => (
          <div key={event.id}>
            <InvalidationCard
              event={event}
              onResolve={(id) => setResolvingId(id)}
              onExecute={(id) => executeMutation.mutate(id)}
            />
            {resolvingId === event.id && (
              <ResolveForm
                eventId={event.id}
                onCancel={() => setResolvingId(null)}
                onSubmit={(id, note) => resolveMutation.mutate({ id, note })}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
