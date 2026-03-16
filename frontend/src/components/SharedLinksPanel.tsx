import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sharedLinksApi, type SharedLinkRead } from '@/api/sharedLinks';
import { useTranslation } from '@/i18n';
import { cn, formatDate } from '@/utils/formatters';
import { Link2, Copy, Check, Trash2, ExternalLink, Users } from 'lucide-react';

const AUDIENCE_BADGE_COLORS: Record<string, string> = {
  buyer: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  insurer: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  lender: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  authority: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  contractor: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  tenant: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300',
};

function SharedLinkRow({ link }: { link: SharedLinkRead }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [copied, setCopied] = useState(false);
  const [confirmRevoke, setConfirmRevoke] = useState(false);

  const revokeMutation = useMutation({
    mutationFn: () => sharedLinksApi.revoke(link.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shared-links', link.resource_id] });
    },
  });

  const url = `${window.location.origin}/shared/${link.token}`;

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  }, [url]);

  const handleRevoke = useCallback(() => {
    if (!confirmRevoke) {
      setConfirmRevoke(true);
      setTimeout(() => setConfirmRevoke(false), 3000);
      return;
    }
    revokeMutation.mutate();
  }, [confirmRevoke, revokeMutation]);

  const badgeColor =
    AUDIENCE_BADGE_COLORS[link.audience_type] || 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300';

  return (
    <div className="flex items-center gap-3 py-2.5 px-3 rounded-lg bg-gray-50 dark:bg-slate-700/50">
      <span className={cn('px-2 py-0.5 text-[10px] font-semibold uppercase rounded-full', badgeColor)}>
        {t(`passport.audience_${link.audience_type}`) || link.audience_type}
      </span>
      <div className="flex-1 min-w-0 text-xs text-gray-500 dark:text-slate-400 space-y-0.5">
        <p>
          {t('shared_links.created') || 'Created'}: {formatDate(link.created_at)}
        </p>
        <p>
          {t('shared_links.expires') || 'Expires'}: {formatDate(link.expires_at)}
        </p>
      </div>
      <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400 tabular-nums shrink-0">
        <ExternalLink className="w-3 h-3" />
        {link.view_count}
        {link.max_views != null && `/${link.max_views}`} {t('shared_links.view_count') || 'views'}
      </span>
      <button
        onClick={handleCopy}
        className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-400 transition-colors shrink-0"
        title={t('passport.copy_link') || 'Copy link'}
      >
        {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
      </button>
      <button
        onClick={handleRevoke}
        disabled={revokeMutation.isPending}
        className={cn(
          'p-1.5 rounded transition-colors shrink-0',
          confirmRevoke
            ? 'bg-red-100 dark:bg-red-900/30 text-red-600 hover:bg-red-200'
            : 'hover:bg-gray-200 dark:hover:bg-slate-600 text-gray-400',
        )}
        title={
          confirmRevoke
            ? t('shared_links.revoke_confirm') || 'Click again to confirm'
            : t('shared_links.revoke') || 'Revoke'
        }
      >
        <Trash2 className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

export function SharedLinksPanel({ buildingId }: { buildingId: string }) {
  const { t } = useTranslation();

  const { data, isLoading } = useQuery({
    queryKey: ['shared-links', buildingId],
    queryFn: () => sharedLinksApi.list({ resource_id: buildingId }),
    enabled: !!buildingId,
  });

  const activeLinks = (data?.items ?? []).filter((l) => l.is_active);

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm animate-pulse">
        <div className="h-4 w-40 bg-gray-200 dark:bg-slate-600 rounded" />
      </div>
    );
  }

  if (activeLinks.length === 0) return null;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Link2 className="w-4 h-4 text-gray-500 dark:text-slate-400" />
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          {t('shared_links.manage_links') || 'Shared Links'}
        </h3>
        <span className="ml-auto flex items-center gap-1 text-xs text-gray-400 dark:text-slate-500">
          <Users className="w-3 h-3" />
          {activeLinks.length} {t('shared_links.active_links') || 'active'}
        </span>
      </div>
      <div className="space-y-2">
        {activeLinks.map((link) => (
          <SharedLinkRow key={link.id} link={link} />
        ))}
      </div>
    </div>
  );
}
