import { useQuery } from '@tanstack/react-query';
import { buildingReportsApi } from '@/api/buildingReports';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  Shield,
  Eye,
  Target,
  Leaf,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2,
  BarChart3,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ScoreCardData {
  key: string;
  label: string;
  score: number | string;
  grade?: string;
  trend?: string | null;
  icon: typeof Shield;
  format?: 'percent' | 'grade' | 'level';
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const GRADE_BADGE: Record<string, string> = {
  A: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  B: 'bg-lime-100 text-lime-800 dark:bg-lime-900/40 dark:text-lime-300',
  C: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  D: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  E: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  F: 'bg-red-200 text-red-900 dark:bg-red-900/50 dark:text-red-200',
};

const LEVEL_COLORS: Record<string, string> = {
  low: 'text-green-600 dark:text-green-400',
  medium: 'text-amber-600 dark:text-amber-400',
  high: 'text-red-600 dark:text-red-400',
  critical: 'text-red-700 dark:text-red-300',
  unknown: 'text-gray-500 dark:text-gray-400',
  compliant: 'text-green-600 dark:text-green-400',
  non_compliant: 'text-red-600 dark:text-red-400',
};

function TrendArrow({ trend }: { trend: string | null | undefined }) {
  if (!trend) return null;
  if (trend === 'improving') {
    return <TrendingUp className="h-3.5 w-3.5 text-green-500" />;
  }
  if (trend === 'declining') {
    return <TrendingDown className="h-3.5 w-3.5 text-red-500" />;
  }
  return <Minus className="h-3.5 w-3.5 text-gray-400" />;
}

/* ------------------------------------------------------------------ */
/*  Score card                                                         */
/* ------------------------------------------------------------------ */

function ScoreCard({ card }: { card: ScoreCardData }) {
  const Icon = card.icon;

  const renderScore = () => {
    if (card.format === 'percent') {
      return <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">{card.score}%</span>;
    }
    if (card.format === 'grade' && typeof card.score === 'string') {
      return (
        <span className={cn('inline-block rounded px-2 py-0.5 text-xl font-bold', GRADE_BADGE[card.score] || '')}>
          {card.score}
        </span>
      );
    }
    if (card.format === 'level' && typeof card.score === 'string') {
      const displayText = card.score.replace('_', ' ');
      return (
        <span
          className={cn(
            'text-lg font-semibold capitalize',
            LEVEL_COLORS[card.score] || 'text-gray-700 dark:text-gray-300'
          )}
        >
          {displayText}
        </span>
      );
    }
    return <span className="text-2xl font-bold text-gray-900 dark:text-gray-100">{card.score}</span>;
  };

  return (
    <div className="flex flex-col rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="mb-2 flex items-center justify-between">
        <Icon className="h-5 w-5 text-gray-400 dark:text-gray-500" />
        {card.grade && (
          <span className={cn('rounded px-1.5 py-0.5 text-xs font-bold', GRADE_BADGE[card.grade] || '')}>
            {card.grade}
          </span>
        )}
      </div>
      <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">{card.label}</p>
      <div className="flex items-center gap-2">
        {renderScore()}
        <TrendArrow trend={card.trend} />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

interface Props {
  buildingId: string;
}

export default function BuildingScoreCards({ buildingId }: Props) {
  const { t } = useTranslation();

  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: ['building-report', buildingId],
    queryFn: () => buildingReportsApi.getFullReport(buildingId),
    staleTime: 60_000,
  });

  const { data: radar, isLoading: radarLoading } = useQuery({
    queryKey: ['readiness-radar', buildingId],
    queryFn: () => buildingReportsApi.getReadinessRadar(buildingId),
    staleTime: 60_000,
  });

  if (reportLoading || radarLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">{t('app.loading')}</span>
      </div>
    );
  }

  const cards: ScoreCardData[] = [];

  if (report) {
    cards.push({
      key: 'passport',
      label: t('scores.title') || 'Passport Grade',
      score: report.passport.grade,
      format: 'grade',
      icon: Shield,
      trend: report.passport.trust_trend,
    });
    cards.push({
      key: 'trust',
      label: 'Trust Score',
      score: report.passport.trust_score,
      format: 'percent',
      grade: report.passport.grade,
      icon: Eye,
      trend: report.passport.trust_trend,
    });
    cards.push({
      key: 'completeness',
      label: 'Completeness',
      score: report.passport.completeness_pct,
      format: 'percent',
      icon: Target,
    });
    cards.push({
      key: 'risk',
      label: 'Overall Risk',
      score: report.risks.overall_grade,
      format: 'level',
      icon: AlertTriangle,
    });
    cards.push({
      key: 'compliance',
      label: 'Compliance',
      score: report.compliance.status,
      format: 'level',
      icon: Leaf,
    });
  }

  if (radar) {
    cards.push({
      key: 'readiness',
      label: 'Readiness',
      score: radar.overall_score,
      format: 'percent',
      grade: radar.overall_grade,
      icon: BarChart3,
    });
  }

  if (cards.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center text-sm text-gray-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
        {t('app.loading')}
      </div>
    );
  }

  return (
    <div>
      <h3 className="mb-3 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
        <BarChart3 className="h-5 w-5 text-gray-500 dark:text-gray-400" />
        {t('scores.title')}
      </h3>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {cards.map((card) => (
          <ScoreCard key={card.key} card={card} />
        ))}
      </div>
    </div>
  );
}
