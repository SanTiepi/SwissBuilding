import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { audiencePacksApi, type CaveatEvaluation } from '@/api/audiencePacks';
import { AlertTriangle, Info, ShieldAlert, Loader2 } from 'lucide-react';

const SEVERITY_STYLES: Record<string, string> = {
  high: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  medium: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  low: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  info: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
};

const SEVERITY_ICONS: Record<string, typeof AlertTriangle> = {
  high: ShieldAlert,
  medium: AlertTriangle,
  low: Info,
  info: Info,
};

const TYPE_ORDER = [
  'freshness_warning',
  'confidence_caveat',
  'unknown_disclosure',
  'contradiction_warning',
  'redaction_notice',
  'residual_risk',
];

function groupByType(caveats: CaveatEvaluation[]): Record<string, CaveatEvaluation[]> {
  const grouped: Record<string, CaveatEvaluation[]> = {};
  for (const caveat of caveats) {
    const key = caveat.caveat_type;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(caveat);
  }
  // Sort by TYPE_ORDER
  const sorted: Record<string, CaveatEvaluation[]> = {};
  for (const type of TYPE_ORDER) {
    if (grouped[type]) sorted[type] = grouped[type];
  }
  // Add any remaining types
  for (const [key, value] of Object.entries(grouped)) {
    if (!sorted[key]) sorted[key] = value;
  }
  return sorted;
}

interface CaveatSummaryProps {
  buildingId: string;
  audienceType: string;
}

export function CaveatSummary({ buildingId, audienceType }: CaveatSummaryProps) {
  const { t } = useTranslation();

  const {
    data: caveats = [],
    isLoading,
    isError,
  } = useQuery<CaveatEvaluation[]>({
    queryKey: ['caveats', buildingId, audienceType],
    queryFn: () => audiencePacksApi.getCaveats(buildingId, audienceType),
    enabled: !!buildingId && !!audienceType,
    retry: false,
  });

  if (isError) return null;

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-gray-500 dark:text-slate-400 py-2" data-testid="caveat-loading">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span className="text-xs">{t('app.loading')}</span>
      </div>
    );
  }

  if (caveats.length === 0) {
    return (
      <p className="text-xs text-gray-500 dark:text-slate-400 py-2" data-testid="caveat-empty">
        {t('audience_pack.no_caveats')}
      </p>
    );
  }

  const grouped = groupByType(caveats);

  return (
    <div className="space-y-3" data-testid="caveat-summary">
      {Object.entries(grouped).map(([type, items]) => (
        <div key={type}>
          <p className="text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">
            {t(`audience_pack.caveat_type.${type}`) || type.replace(/_/g, ' ')}
          </p>
          <div className="space-y-1">
            {items.map((caveat, idx) => {
              const Icon = SEVERITY_ICONS[caveat.severity] || Info;
              return (
                <div
                  key={`${caveat.caveat_type}-${idx}`}
                  className="flex items-start gap-2 text-xs"
                  data-testid="caveat-item"
                >
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-medium flex-shrink-0',
                      SEVERITY_STYLES[caveat.severity] || SEVERITY_STYLES.info,
                    )}
                    data-testid="caveat-severity"
                  >
                    <Icon className="w-3 h-3" />
                    {caveat.severity}
                  </span>
                  <span className="text-gray-700 dark:text-slate-300">{caveat.message}</span>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

export default CaveatSummary;
