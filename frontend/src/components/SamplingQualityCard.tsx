import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { samplingQualityApi, type SamplingCriterion, type SamplingQuality } from '@/api/samplingQuality';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { Beaker, ChevronDown, ChevronUp, AlertTriangle, Shield } from 'lucide-react';
import { AsyncStateWrapper } from './AsyncStateWrapper';

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  B: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  C: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  D: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  F: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
};

const CONFIDENCE_COLORS: Record<string, string> = {
  high: 'text-green-600 dark:text-green-400',
  medium: 'text-yellow-600 dark:text-yellow-400',
  low: 'text-orange-600 dark:text-orange-400',
  very_low: 'text-red-600 dark:text-red-400',
};

const CRITERIA_KEYS: Record<string, string> = {
  coverage: 'sampling_quality.criteria_coverage',
  density: 'sampling_quality.criteria_density',
  pollutant_breadth: 'sampling_quality.criteria_breadth',
  material_diversity: 'sampling_quality.criteria_diversity',
  location_spread: 'sampling_quality.criteria_spread',
  temporal_consistency: 'sampling_quality.criteria_temporal',
  lab_turnaround: 'sampling_quality.criteria_turnaround',
  documentation: 'sampling_quality.criteria_documentation',
  negative_controls: 'sampling_quality.criteria_controls',
  protocol_compliance: 'sampling_quality.criteria_compliance',
};

/** SVG radar/spider chart for 10 criteria. */
function RadarChart({ criteria }: { criteria: SamplingCriterion[] }) {
  const size = 200;
  const cx = size / 2;
  const cy = size / 2;
  const maxR = 80;
  const levels = 5;

  // Generate polygon points for each criterion
  const angleStep = (2 * Math.PI) / criteria.length;

  const pointsAt = (radius: number): string =>
    criteria
      .map((_, i) => {
        const angle = -Math.PI / 2 + i * angleStep;
        const x = cx + radius * Math.cos(angle);
        const y = cy + radius * Math.sin(angle);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');

  const dataPoints = criteria
    .map((c, i) => {
      const ratio = c.score / c.max;
      const r = ratio * maxR;
      const angle = -Math.PI / 2 + i * angleStep;
      return `${(cx + r * Math.cos(angle)).toFixed(1)},${(cy + r * Math.sin(angle)).toFixed(1)}`;
    })
    .join(' ');

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[220px] mx-auto">
      {/* Grid levels */}
      {Array.from({ length: levels }, (_, i) => {
        const r = ((i + 1) / levels) * maxR;
        return (
          <polygon
            key={i}
            points={pointsAt(r)}
            fill="none"
            stroke="currentColor"
            className="text-gray-200 dark:text-slate-600"
            strokeWidth="0.5"
          />
        );
      })}

      {/* Axis lines */}
      {criteria.map((_, i) => {
        const angle = -Math.PI / 2 + i * angleStep;
        const x2 = cx + maxR * Math.cos(angle);
        const y2 = cy + maxR * Math.sin(angle);
        return (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={x2}
            y2={y2}
            stroke="currentColor"
            className="text-gray-200 dark:text-slate-600"
            strokeWidth="0.5"
          />
        );
      })}

      {/* Data polygon */}
      <polygon
        points={dataPoints}
        fill="currentColor"
        className="text-blue-500/20 dark:text-blue-400/20"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />

      {/* Data points */}
      {criteria.map((c, i) => {
        const ratio = c.score / c.max;
        const r = ratio * maxR;
        const angle = -Math.PI / 2 + i * angleStep;
        const x = cx + r * Math.cos(angle);
        const y = cy + r * Math.sin(angle);
        return <circle key={i} cx={x} cy={y} r="2.5" fill="currentColor" className="text-blue-600 dark:text-blue-400" />;
      })}

      {/* Labels */}
      {criteria.map((c, i) => {
        const angle = -Math.PI / 2 + i * angleStep;
        const lx = cx + (maxR + 14) * Math.cos(angle);
        const ly = cy + (maxR + 14) * Math.sin(angle);
        return (
          <text
            key={i}
            x={lx}
            y={ly}
            textAnchor="middle"
            dominantBaseline="central"
            className="text-gray-500 dark:text-slate-400 fill-current"
            fontSize="6"
          >
            {c.score}
          </text>
        );
      })}
    </svg>
  );
}

function CriterionRow({ criterion }: { criterion: SamplingCriterion }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const label = t(CRITERIA_KEYS[criterion.name] ?? criterion.name) || criterion.name;
  const pct = Math.round((criterion.score / criterion.max) * 100);

  const barColor =
    pct >= 70
      ? 'bg-green-500 dark:bg-green-400'
      : pct >= 50
        ? 'bg-yellow-500 dark:bg-yellow-400'
        : 'bg-red-500 dark:bg-red-400';

  return (
    <div className="border-b border-gray-100 dark:border-slate-700 last:border-b-0">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full py-2 px-1 text-left hover:bg-gray-50 dark:hover:bg-slate-700/50 rounded"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-700 dark:text-slate-200 truncate">{label}</span>
            <span className="text-xs text-gray-400 dark:text-slate-500">
              {criterion.score}/{criterion.max}
            </span>
          </div>
          <div className="mt-1 h-1.5 w-full bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
            <div className={cn('h-full rounded-full transition-all', barColor)} style={{ width: `${pct}%` }} />
          </div>
        </div>
        <span className="ml-2 text-gray-400 dark:text-slate-500">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </span>
      </button>
      {expanded && (
        <div className="px-1 pb-2 text-xs text-gray-500 dark:text-slate-400 space-y-1">
          <p>{criterion.detail}</p>
          <p className="text-blue-600 dark:text-blue-400">{criterion.recommendation}</p>
        </div>
      )}
    </div>
  );
}

function SamplingQualityContent({ data }: { data: SamplingQuality }) {
  const { t } = useTranslation();

  return (
    <>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Beaker className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            {t('sampling_quality.title') || 'Sampling Quality'}
          </h3>
        </div>
        <span
          className={cn('text-xs font-bold px-2 py-0.5 rounded-full', GRADE_COLORS[data.grade] ?? GRADE_COLORS.F)}
        >
          {t('sampling_quality.grade') || 'Grade'}: {data.grade}
        </span>
      </div>

      {/* Overall score */}
      <div className="flex items-center gap-3 mb-4">
        <div className="text-3xl font-bold text-gray-900 dark:text-white">{data.overall_score}</div>
        <div className="text-xs text-gray-500 dark:text-slate-400">/ 100</div>
        <div className="ml-auto flex items-center gap-1">
          <Shield className="w-3.5 h-3.5" />
          <span className={cn('text-xs font-medium', CONFIDENCE_COLORS[data.confidence_level] ?? 'text-gray-500')}>
            {t('sampling_quality.confidence') || 'Confidence'}: {data.confidence_level}
          </span>
        </div>
      </div>

      {/* Radar chart */}
      <RadarChart criteria={data.criteria} />

      {/* Criteria list */}
      <div className="mt-4">
        {data.criteria.map((c) => (
          <CriterionRow key={c.name} criterion={c} />
        ))}
      </div>

      {/* Warnings */}
      {data.warnings.length > 0 && (
        <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
          <div className="flex items-center gap-1.5 text-amber-700 dark:text-amber-400 text-xs font-medium mb-1">
            <AlertTriangle className="w-3.5 h-3.5" />
            {t('sampling_quality.warnings') || 'Warnings'}
          </div>
          <ul className="text-xs text-amber-600 dark:text-amber-300 space-y-0.5 list-disc list-inside">
            {data.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

interface SamplingQualityCardProps {
  diagnosticId: string;
}

export function SamplingQualityCard({ diagnosticId }: SamplingQualityCardProps) {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['sampling-quality', diagnosticId],
    queryFn: () => samplingQualityApi.getDiagnostic(diagnosticId),
  });

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-5">
      <AsyncStateWrapper
        isLoading={isLoading}
        isError={isError}
        data={data}
        title={t('sampling_quality.title') || 'Sampling Quality'}
        errorMessage={t('app.loading_error') || 'Loading error'}
      >
        {data && <SamplingQualityContent data={data} />}
      </AsyncStateWrapper>
    </div>
  );
}
