import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { evidenceScoreApi } from '@/api/evidenceScore';
import { cn } from '@/utils/formatters';

interface EvidenceScoreWidgetProps {
  buildingId: string;
}

const GRADE_COLORS: Record<string, { ring: string; text: string; bg: string }> = {
  A: { ring: 'stroke-green-500', text: 'text-green-600 dark:text-green-400', bg: 'bg-green-50 dark:bg-green-900/20' },
  B: { ring: 'stroke-blue-500', text: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-900/20' },
  C: {
    ring: 'stroke-yellow-500',
    text: 'text-yellow-600 dark:text-yellow-400',
    bg: 'bg-yellow-50 dark:bg-yellow-900/20',
  },
  D: {
    ring: 'stroke-orange-500',
    text: 'text-orange-600 dark:text-orange-400',
    bg: 'bg-orange-50 dark:bg-orange-900/20',
  },
  F: { ring: 'stroke-red-500', text: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-900/20' },
};

function getGradeStyle(grade: string) {
  return GRADE_COLORS[grade] ?? GRADE_COLORS['F'];
}

function CircularProgress({ score, grade }: { score: number; grade: string }) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const style = getGradeStyle(grade);

  return (
    <div className="relative flex items-center justify-center">
      <svg width="100" height="100" viewBox="0 0 100 100" className="-rotate-90">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="currentColor" strokeWidth="8" className="text-gray-200 dark:text-gray-700" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className={style.ring}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={cn('text-2xl font-bold', style.text)}>{score}</span>
        <span className={cn('text-xs font-semibold', style.text)}>{grade}</span>
      </div>
    </div>
  );
}

function BreakdownBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400">
        <span>{label}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
        <div className={cn('h-2 rounded-full', color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function EvidenceScoreWidget({ buildingId }: EvidenceScoreWidgetProps) {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['evidence-score', buildingId],
    queryFn: () => evidenceScoreApi.getEvidenceScore(buildingId),
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">
          {t('evidence_score.title')}
        </h3>
        <div className="flex animate-pulse items-center justify-center py-8">
          <div className="h-24 w-24 rounded-full bg-gray-200 dark:bg-gray-700" />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">
          {t('evidence_score.title')}
        </h3>
        <p className="text-sm text-red-500 dark:text-red-400">{t('app.loading_error') || 'Failed to load'}</p>
      </div>
    );
  }

  const style = getGradeStyle(data.grade);

  return (
    <div className={cn('rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800')}>
      <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">
        {t('evidence_score.title')}
      </h3>

      <div className="flex items-center gap-4">
        <CircularProgress score={data.score} grade={data.grade} />

        <div className={cn('rounded-md px-3 py-1.5 text-xs font-medium', style.bg, style.text)}>
          {t(`evidence_score.grade_${data.grade.toLowerCase() as 'a' | 'b' | 'c' | 'd' | 'f'}`) || `Grade ${data.grade}`}
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <BreakdownBar
          label={t('evidence_score.trust')}
          value={data.trust}
          color="bg-indigo-500 dark:bg-indigo-400"
        />
        <BreakdownBar
          label={t('evidence_score.completeness')}
          value={data.completeness}
          color="bg-emerald-500 dark:bg-emerald-400"
        />
        <BreakdownBar
          label={t('evidence_score.freshness')}
          value={data.freshness}
          color="bg-amber-500 dark:bg-amber-400"
        />
        <BreakdownBar
          label={t('evidence_score.gaps')}
          value={data.gap_penalty}
          color="bg-rose-500 dark:bg-rose-400"
        />
      </div>
    </div>
  );
}
