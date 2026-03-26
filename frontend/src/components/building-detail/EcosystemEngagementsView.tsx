import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { intelligenceApi } from '@/api/intelligence';
import type { EcosystemEngagement } from '@/api/intelligence';
import { useAuthStore } from '@/store/authStore';
import {
  Loader2,
  Users,
  Plus,
  X,
  MessageSquare,
  Clock,
  CheckCircle2,
  XCircle,
  Eye,
  ShieldCheck,
  AlertTriangle,
  Bookmark,
} from 'lucide-react';

interface EcosystemEngagementsViewProps {
  buildingId: string;
}

const ENGAGEMENT_TYPE_STYLES: Record<string, { color: string; icon: typeof Eye }> = {
  seen: { color: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400', icon: Eye },
  accepted: {
    color: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    icon: CheckCircle2,
  },
  contested: { color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400', icon: AlertTriangle },
  confirmed: { color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400', icon: ShieldCheck },
  reserved: { color: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400', icon: Bookmark },
  refused: { color: 'bg-red-200 text-red-800 dark:bg-red-900/50 dark:text-red-300', icon: XCircle },
};

const ACTOR_TYPES = ['diagnostician', 'contractor', 'authority', 'owner', 'architect', 'admin'];
const ENGAGEMENT_TYPES = ['seen', 'accepted', 'contested', 'confirmed', 'reserved', 'refused'];
const SUBJECT_TYPES = ['diagnostic', 'document', 'action', 'evidence', 'building', 'intervention'];

function EngagementTypeBadge({ type }: { type: string }) {
  const { t } = useTranslation();
  const style = ENGAGEMENT_TYPE_STYLES[type] || ENGAGEMENT_TYPE_STYLES.seen;
  const Icon = style.icon;

  return (
    <span
      className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold', style.color)}
    >
      <Icon className="w-3 h-3" />
      {t(`ecosystem_engagement.type_${type}`) || type}
    </span>
  );
}

function DepthGauge({ score }: { score: number }) {
  const pct = Math.round(Math.min(100, Math.max(0, score)));
  const getColor = (v: number) => {
    if (v >= 70) return 'text-emerald-500';
    if (v >= 40) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-20 h-20">
        <svg className="w-20 h-20 -rotate-90" viewBox="0 0 100 100">
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
          <span className={cn('text-lg font-black', getColor(pct))}>{pct}</span>
        </div>
      </div>
    </div>
  );
}

function ActorParticipationGrid({ represented }: { represented: string[] }) {
  const { t } = useTranslation();
  const representedSet = new Set(represented);

  return (
    <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
      {ACTOR_TYPES.map((actor) => {
        const present = representedSet.has(actor);
        return (
          <div
            key={actor}
            className={cn(
              'flex flex-col items-center gap-1 p-2 rounded-lg border text-center',
              present
                ? 'border-emerald-200 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-900/10'
                : 'border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 opacity-50',
            )}
          >
            <div
              className={cn('w-3 h-3 rounded-full', present ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600')}
            />
            <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400">
              {t(`ecosystem_engagement.actor_${actor}`) || actor}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function EngagementTimelineItem({ engagement }: { engagement: EcosystemEngagement }) {
  const { t } = useTranslation();

  return (
    <div className="flex gap-3">
      {/* Timeline dot + line */}
      <div className="flex flex-col items-center">
        <div className="w-2.5 h-2.5 rounded-full bg-blue-500 dark:bg-blue-400 mt-1.5 shrink-0" />
        <div className="w-px flex-1 bg-slate-200 dark:bg-slate-700" />
      </div>

      {/* Card */}
      <div className="pb-4 flex-1 min-w-0">
        <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
              {engagement.actor_name ||
                t(`ecosystem_engagement.actor_${engagement.actor_type}`) ||
                engagement.actor_type}
            </span>
            <EngagementTypeBadge type={engagement.engagement_type} />
          </div>
          <p className="text-[11px] text-slate-600 dark:text-slate-400 mt-1">
            {engagement.subject_label ||
              t(`ecosystem_engagement.subject_${engagement.subject_type}`) ||
              engagement.subject_type}
          </p>
          {engagement.comment && (
            <div className="flex items-start gap-1.5 mt-2">
              <MessageSquare className="w-3 h-3 text-slate-400 mt-0.5 shrink-0" />
              <p className="text-[11px] text-slate-500 dark:text-slate-400 italic">{engagement.comment}</p>
            </div>
          )}
          <div className="flex items-center gap-1 mt-2">
            <Clock className="w-3 h-3 text-slate-400" />
            <span className="text-[10px] text-slate-400 dark:text-slate-500">
              {new Date(engagement.engaged_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function AddEngagementModal({ buildingId, onClose }: { buildingId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [actorType, setActorType] = useState('');
  const [subjectType, setSubjectType] = useState('');
  const [engagementType, setEngagementType] = useState('');
  const [comment, setComment] = useState('');

  const mutation = useMutation({
    mutationFn: (data: { actor_type: string; subject_type: string; engagement_type: string; comment?: string }) =>
      intelligenceApi.createEngagement(buildingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['engagement-summary', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['engagement-timeline', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['engagement-depth', buildingId] });
      onClose();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!actorType || !subjectType || !engagementType) return;
    mutation.mutate({
      actor_type: actorType,
      subject_type: subjectType,
      engagement_type: engagementType,
      comment: comment || undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">
            {t('ecosystem_engagement.add_title') || 'Ajouter un engagement'}
          </h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
            aria-label={t('form.close') || 'Close'}
          >
            <X className="w-5 h-5 text-slate-500 dark:text-slate-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
              {t('ecosystem_engagement.actor_type_label') || "Type d'acteur"}
            </label>
            <select
              value={actorType}
              onChange={(e) => setActorType(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              <option value="">{t('form.select') || 'Selectionner...'}</option>
              {ACTOR_TYPES.map((a) => (
                <option key={a} value={a}>
                  {t(`ecosystem_engagement.actor_${a}`) || a}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
              {t('ecosystem_engagement.subject_type_label') || 'Objet'}
            </label>
            <select
              value={subjectType}
              onChange={(e) => setSubjectType(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              <option value="">{t('form.select') || 'Selectionner...'}</option>
              {SUBJECT_TYPES.map((s) => (
                <option key={s} value={s}>
                  {t(`ecosystem_engagement.subject_${s}`) || s}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
              {t('ecosystem_engagement.engagement_type_label') || "Type d'engagement"}
            </label>
            <select
              value={engagementType}
              onChange={(e) => setEngagementType(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              <option value="">{t('form.select') || 'Selectionner...'}</option>
              {ENGAGEMENT_TYPES.map((et) => (
                <option key={et} value={et}>
                  {t(`ecosystem_engagement.type_${et}`) || et}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-200 mb-1">
              {t('ecosystem_engagement.comment_label') || 'Commentaire (optionnel)'}
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
              placeholder={t('ecosystem_engagement.comment_placeholder') || 'Ajouter un commentaire...'}
            />
          </div>

          <div className="flex justify-end gap-3 pt-2 border-t border-slate-100 dark:border-slate-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700"
            >
              {t('form.cancel') || 'Annuler'}
            </button>
            <button
              type="submit"
              disabled={!actorType || !subjectType || !engagementType || mutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
            >
              {mutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              {t('form.create') || 'Creer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function EcosystemEngagementsView({ buildingId }: EcosystemEngagementsViewProps) {
  const { t } = useTranslation();
  const currentUser = useAuthStore((s) => s.user);
  const [showAddModal, setShowAddModal] = useState(false);

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['engagement-summary', buildingId],
    queryFn: () => intelligenceApi.getEngagementSummary(buildingId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const { data: depth, isLoading: depthLoading } = useQuery({
    queryKey: ['engagement-depth', buildingId],
    queryFn: () => intelligenceApi.getEngagementDepth(buildingId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const { data: timeline } = useQuery({
    queryKey: ['engagement-timeline', buildingId],
    queryFn: () => intelligenceApi.getEngagementTimeline(buildingId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const isLoading = summaryLoading || depthLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-red-600" />
      </div>
    );
  }

  if (!summary && !depth) return null;

  const canAdd =
    currentUser &&
    ['admin', 'owner', 'diagnostician', 'architect', 'contractor', 'authority'].includes(currentUser.role);

  return (
    <div className="space-y-4" data-testid="ecosystem-engagements-view">
      {/* Section header */}
      <div className="flex items-center gap-2">
        <Users className="w-5 h-5 text-blue-600" />
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex-1">
          {t('ecosystem_engagement.title') || "Engagements de l'ecosysteme"}
        </h2>
        {canAdd && (
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors border border-blue-200 dark:border-blue-800"
          >
            <Plus className="w-3.5 h-3.5" />
            {t('ecosystem_engagement.add_button') || 'Ajouter'}
          </button>
        )}
      </div>

      {/* Top row: Depth gauge + Actor grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Depth gauge */}
        {depth && (
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 flex flex-col items-center gap-3">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              {t('ecosystem_engagement.depth_label') || "Profondeur d'engagement"}
            </p>
            <DepthGauge score={depth.depth_score} />
            <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
              <span>
                <strong className="text-slate-700 dark:text-slate-300">{depth.unique_actors}</strong>{' '}
                {t('ecosystem_engagement.actors') || 'acteurs'}
              </span>
              <span>
                <strong className="text-slate-700 dark:text-slate-300">{depth.unique_orgs}</strong>{' '}
                {t('ecosystem_engagement.orgs') || 'organisations'}
              </span>
            </div>
          </div>
        )}

        {/* Actor participation grid */}
        {depth && (
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
              {t('ecosystem_engagement.participation') || 'Participation des acteurs'}
            </p>
            <ActorParticipationGrid represented={depth.actor_types_represented} />
          </div>
        )}
      </div>

      {/* Engagement timeline */}
      {timeline && timeline.length > 0 && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">
            {t('ecosystem_engagement.latest') || 'Derniers engagements'}
          </p>
          <div className="max-h-80 overflow-y-auto">
            {timeline.slice(0, 10).map((eng) => (
              <EngagementTimelineItem key={eng.id} engagement={eng} />
            ))}
          </div>
        </div>
      )}

      {/* Footer message */}
      {summary && (
        <div className="text-center pt-1">
          <p className="text-xs text-slate-500 dark:text-slate-400">
            <span className="font-bold text-slate-700 dark:text-slate-300">{summary.unique_actors}</span>{' '}
            {t('ecosystem_engagement.footer_message') ||
              "acteurs de l'ecosysteme ont engage leur responsabilite dans ce dossier"}
          </p>
        </div>
      )}

      {/* Add modal */}
      {showAddModal && <AddEngagementModal buildingId={buildingId} onClose={() => setShowAddModal(false)} />}
    </div>
  );
}
