import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { qualityApi } from '@/api/quality';
import { AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import { AsyncStateWrapper } from './AsyncStateWrapper';

interface DataQualityScoreProps {
  buildingId: string;
}

export function DataQualityScore({ buildingId }: DataQualityScoreProps) {
  const {
    data: quality,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['building-quality', buildingId],
    queryFn: () => qualityApi.get(buildingId),
  });

  if (!isLoading && !isError && !quality) return null;

  return (
    <AsyncStateWrapper
      isLoading={isLoading}
      isError={isError}
      data={quality}
      variant="inline"
      loadingType="skeleton"
      isEmpty={false}
      className="p-0"
    >
      {quality && <DataQualityContent quality={quality} />}
    </AsyncStateWrapper>
  );
}

function DataQualityContent({ quality }: { quality: any }) {
  const { t } = useTranslation();
  const score = Math.round(quality.overall_score * 100);
  const color = score >= 80 ? 'text-green-600' : score >= 50 ? 'text-yellow-600' : 'text-red-600';
  const bgColor = score >= 80 ? 'bg-green-50' : score >= 50 ? 'bg-yellow-50' : 'bg-red-50';

  // SVG circular progress
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - quality.overall_score * circumference;

  return (
    <div className={`rounded-lg p-4 ${bgColor}`}>
      <div className="flex items-center gap-4">
        <div className="relative w-24 h-24 flex-shrink-0">
          <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
            <circle cx="50" cy="50" r={radius} fill="none" stroke="#e5e7eb" strokeWidth="8" />
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke="currentColor"
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className={color}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`text-xl font-bold ${color}`}>{score}%</span>
          </div>
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-gray-900">{t('quality.title')}</h3>
          {Object.entries(quality.sections).map(([key, section]) => (
            <div key={key} className="mt-1 flex items-center gap-2 text-sm">
              {(section as { score: number }).score >= 0.8 ? (
                <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0 text-green-500" />
              ) : (section as { score: number }).score >= 0.5 ? (
                <Info className="h-3.5 w-3.5 flex-shrink-0 text-yellow-500" />
              ) : (
                <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 text-red-500" />
              )}
              <span className="truncate text-gray-700">{t(`quality.section.${key}`) || key}</span>
              <span className="ml-auto text-gray-500">{Math.round((section as { score: number }).score * 100)}%</span>
            </div>
          ))}
          {quality.missing.length > 0 && (
            <p className="mt-2 text-xs text-gray-500">
              {t('quality.missing')}:{' '}
              {quality.missing
                .slice(0, 3)
                .map((k: string) => t(`quality.missing_item.${k}`) || k)
                .join(', ')}
              {quality.missing.length > 3 && ` +${quality.missing.length - 3}`}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
