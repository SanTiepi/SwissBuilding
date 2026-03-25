import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { publicSectorApi, type PublicOwnerModeData } from '@/api/publicSector';
import { Landmark, ShieldCheck, Users, FileText, Loader2 } from 'lucide-react';

const MODE_COLORS: Record<string, string> = {
  municipal: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  cantonal: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  federal: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  public_foundation: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
};

const GOVERNANCE_COLORS: Record<string, string> = {
  standard: 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
  enhanced: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  strict: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

interface PublicOwnerModePanelProps {
  orgId: string;
}

export function PublicOwnerModePanel({ orgId }: PublicOwnerModePanelProps) {
  const { t } = useTranslation();

  const {
    data: mode,
    isLoading,
    isError,
  } = useQuery<PublicOwnerModeData>({
    queryKey: ['public-owner-mode', orgId],
    queryFn: () => publicSectorApi.getPublicOwnerMode(orgId),
    enabled: !!orgId,
    retry: false,
  });

  // Don't render anything if no public mode configured (404)
  if (isError || (!isLoading && !mode)) return null;

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5" data-testid="public-owner-mode-loading">
        <div className="flex items-center gap-2 text-gray-500 dark:text-slate-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          {t('app.loading')}
        </div>
      </div>
    );
  }

  if (!mode) return null;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5" data-testid="public-owner-mode-panel">
      <div className="flex items-center gap-2 mb-4">
        <Landmark className="w-5 h-5 text-gray-500 dark:text-slate-400" />
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          {t('public_sector.owner_mode_title')}
        </h3>
      </div>

      <div className="space-y-3">
        {/* Mode badge */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 dark:text-slate-400">{t('public_sector.mode_type')}:</span>
          <span
            className={cn('inline-block px-2 py-0.5 text-xs font-medium rounded-full', MODE_COLORS[mode.mode_type] || MODE_COLORS.municipal)}
            data-testid="public-owner-mode-badge"
          >
            {t(`public_sector.mode.${mode.mode_type}`) || mode.mode_type}
          </span>
        </div>

        {/* Governance level */}
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-gray-400 dark:text-slate-500" />
          <span className="text-xs text-gray-500 dark:text-slate-400">{t('public_sector.governance_level')}:</span>
          <span
            className={cn('inline-block px-2 py-0.5 text-xs font-medium rounded-full', GOVERNANCE_COLORS[mode.governance_level] || GOVERNANCE_COLORS.standard)}
            data-testid="governance-level-badge"
          >
            {t(`public_sector.governance.${mode.governance_level}`) || mode.governance_level}
          </span>
        </div>

        {/* Requirements */}
        <div className="flex flex-wrap gap-3 text-xs text-gray-600 dark:text-slate-300">
          {mode.requires_committee_review && (
            <span className="flex items-center gap-1" data-testid="requires-committee-review">
              <Users className="w-3.5 h-3.5" />
              {t('public_sector.requires_committee')}
            </span>
          )}
          {mode.requires_review_pack && (
            <span className="flex items-center gap-1" data-testid="requires-review-pack">
              <FileText className="w-3.5 h-3.5" />
              {t('public_sector.requires_review_pack')}
            </span>
          )}
        </div>

        {/* Default review audience */}
        {mode.default_review_audience && mode.default_review_audience.length > 0 && (
          <div data-testid="review-audience">
            <span className="text-xs text-gray-500 dark:text-slate-400 block mb-1">
              {t('public_sector.default_audience')}:
            </span>
            <div className="flex flex-wrap gap-1">
              {mode.default_review_audience.map((aud, i) => (
                <span key={i} className="inline-block px-2 py-0.5 text-xs bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300 rounded">
                  {aud}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default PublicOwnerModePanel;
