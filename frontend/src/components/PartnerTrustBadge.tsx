import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { partnerTrustApi, type PartnerTrustProfile, type TrustLevel } from '@/api/partnerTrust';
import { Shield } from 'lucide-react';
import { useState } from 'react';

interface PartnerTrustBadgePropsWithOrg {
  orgId: string;
  trustProfile?: never;
}

interface PartnerTrustBadgePropsWithProfile {
  orgId?: never;
  trustProfile: PartnerTrustProfile;
}

type PartnerTrustBadgeProps = PartnerTrustBadgePropsWithOrg | PartnerTrustBadgePropsWithProfile;

const TRUST_LEVEL_STYLE: Record<TrustLevel, { bg: string; text: string; border: string }> = {
  strong: {
    bg: 'bg-green-100 dark:bg-green-900/40',
    text: 'text-green-700 dark:text-green-400',
    border: 'border-green-300 dark:border-green-700',
  },
  adequate: {
    bg: 'bg-blue-100 dark:bg-blue-900/40',
    text: 'text-blue-700 dark:text-blue-400',
    border: 'border-blue-300 dark:border-blue-700',
  },
  review: {
    bg: 'bg-orange-100 dark:bg-orange-900/40',
    text: 'text-orange-700 dark:text-orange-400',
    border: 'border-orange-300 dark:border-orange-700',
  },
  weak: {
    bg: 'bg-red-100 dark:bg-red-900/40',
    text: 'text-red-700 dark:text-red-400',
    border: 'border-red-300 dark:border-red-700',
  },
  unknown: {
    bg: 'bg-gray-100 dark:bg-gray-700',
    text: 'text-gray-500 dark:text-gray-400',
    border: 'border-gray-300 dark:border-gray-600',
  },
};

function formatScore(score: number | null): string {
  if (score == null) return '--';
  return `${Math.round(score * 100)}%`;
}

export function PartnerTrustBadge(props: PartnerTrustBadgeProps) {
  const { t } = useTranslation();
  const [showTooltip, setShowTooltip] = useState(false);

  const { data: fetchedProfile } = useQuery({
    queryKey: ['partner-trust', props.orgId],
    queryFn: () => partnerTrustApi.getProfile(props.orgId!),
    staleTime: 120_000,
    enabled: !!props.orgId,
  });

  const profile = props.trustProfile ?? fetchedProfile;

  if (!profile) {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
        data-testid="partner-trust-badge-loading"
      >
        <Shield className="w-3 h-3" />
        ...
      </span>
    );
  }

  const level = (profile.overall_trust_level as TrustLevel) || 'unknown';
  const style = TRUST_LEVEL_STYLE[level] ?? TRUST_LEVEL_STYLE.unknown;

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <span
        className={cn(
          'inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium cursor-default',
          style.bg,
          style.text,
          style.border,
        )}
        data-testid="partner-trust-badge"
        data-trust-level={level}
      >
        <Shield className="w-3 h-3" />
        {t(`partner_trust.level_${level}`)}
      </span>

      {/* Tooltip with sub-scores */}
      {showTooltip && (
        <div
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 bg-gray-900 dark:bg-gray-700 text-white rounded-lg p-3 text-xs shadow-lg z-50"
          data-testid="partner-trust-tooltip"
        >
          <p className="font-medium mb-2">{t('partner_trust.title')}</p>
          <div className="space-y-1">
            <div className="flex justify-between">
              <span>{t('partner_trust.delivery')}</span>
              <span className="font-medium">{formatScore(profile.delivery_reliability_score)}</span>
            </div>
            <div className="flex justify-between">
              <span>{t('partner_trust.evidence')}</span>
              <span className="font-medium">{formatScore(profile.evidence_quality_score)}</span>
            </div>
            <div className="flex justify-between">
              <span>{t('partner_trust.responsiveness')}</span>
              <span className="font-medium">{formatScore(profile.responsiveness_score)}</span>
            </div>
          </div>
          <div className="text-gray-400 mt-2 text-[10px]">
            {profile.signal_count} {t('partner_trust.signals')}
          </div>
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900 dark:border-t-gray-700" />
        </div>
      )}
    </span>
  );
}
