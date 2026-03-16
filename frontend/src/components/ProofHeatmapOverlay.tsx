import { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { planHeatmapApi } from '@/api/planHeatmap';
import type { HeatmapPoint, PlanHeatmap } from '@/api/planHeatmap';
import { AsyncStateWrapper } from './AsyncStateWrapper';

const CATEGORY_COLORS: Record<string, string> = {
  trust: '#22c55e',
  unknown: '#f59e0b',
  contradiction: '#ef4444',
  hazard: '#a855f7',
  sample: '#3b82f6',
};

function trustColor(intensity: number): string {
  if (intensity >= 0.7) return '#22c55e';
  if (intensity >= 0.4) return '#f59e0b';
  return '#ef4444';
}

const TRUST_LEVELS = [
  { cls: 'bg-green-500', key: 'heatmap.high_trust', fallback: 'High trust' },
  { cls: 'bg-amber-500', key: 'heatmap.medium_trust', fallback: 'Medium trust' },
  { cls: 'bg-red-500', key: 'heatmap.low_trust', fallback: 'Low trust' },
] as const;

function HeatmapLegend({ heatmap }: { heatmap: PlanHeatmap }) {
  const { t } = useTranslation();
  return (
    <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg px-4 py-2.5">
      <p className="text-xs font-semibold text-gray-700 dark:text-slate-300 uppercase tracking-wider mb-2">
        {t('heatmap.legend_title') || 'Proof legend'}
      </p>
      <div className="flex items-center gap-3 mb-1.5">
        {TRUST_LEVELS.map(({ cls, key, fallback }) => (
          <div key={key} className="flex items-center gap-1">
            <span className={`w-3 h-3 rounded-full ${cls}`} />
            <span className="text-xs text-gray-600 dark:text-slate-300">{t(key) || fallback}</span>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-4 flex-wrap">
        {Object.entries(CATEGORY_COLORS)
          .filter(([cat]) => cat !== 'trust')
          .map(([category, color]) => {
            const count = heatmap.summary[category] ?? 0;
            if (count === 0) return null;
            return (
              <div key={category} className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
                <span className="text-xs text-gray-600 dark:text-slate-300">
                  {t(`heatmap.${category}`) || category}
                </span>
                <span className="text-xs text-gray-400 dark:text-slate-500">({count})</span>
              </div>
            );
          })}
      </div>
    </div>
  );
}

export function ProofHeatmapOverlay({ planId, imageUrl }: { planId: string; imageUrl: string }) {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 0, height: 0 });
  type HP = HeatmapPoint & { cx: number; cy: number };
  const [hover, setHover] = useState<HP | null>(null);

  const {
    data: heatmap,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['planHeatmap', planId],
    queryFn: () => planHeatmapApi.getHeatmap(planId),
    enabled: !!planId,
  });

  const measure = useCallback(() => {
    if (containerRef.current) {
      const r = containerRef.current.getBoundingClientRect();
      setDims({ width: r.width, height: r.height });
    }
  }, []);

  useEffect(() => {
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, [measure]);

  const rad = (i: number) => Math.max(6, 8 + i * 16);
  const opa = (i: number) => 0.3 + i * 0.5;
  const hasPoints = (heatmap?.points.length ?? 0) > 0;

  return (
    <AsyncStateWrapper
      isLoading={isLoading}
      isError={isError}
      data={heatmap?.points}
      variant="inline"
      isEmpty={!hasPoints}
      emptyMessage={t('heatmap.no_data') || 'No proof data for this plan'}
    >
      <div className="space-y-2">
        <div ref={containerRef} className="relative inline-block w-full">
          <img src={imageUrl} alt="Plan" className="w-full h-auto block" onLoad={measure} />
          {heatmap && (
            <div className="absolute top-2 right-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-1.5 shadow-sm">
              <span className="text-xs font-medium text-gray-500 dark:text-slate-400">
                {t('heatmap.coverage_score') || 'Coverage'}
              </span>
              <span className="ml-2 text-sm font-bold text-gray-900 dark:text-white">
                {Math.round(heatmap.coverage_score * 100)}%
              </span>
            </div>
          )}
          {heatmap && hasPoints && dims.width > 0 && (
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              viewBox={`0 0 ${dims.width} ${dims.height}`}
              preserveAspectRatio="none"
            >
              {heatmap.points.map((pt, idx) => {
                const cx = pt.x * dims.width;
                const cy = pt.y * dims.height;
                const r = rad(pt.intensity);
                const color =
                  pt.category === 'trust' ? trustColor(pt.intensity) : CATEGORY_COLORS[pt.category] || '#6b7280';
                const op = opa(pt.intensity);
                return (
                  <g key={idx}>
                    <circle
                      cx={cx}
                      cy={cy}
                      r={r}
                      fill={color}
                      fillOpacity={op}
                      stroke={color}
                      strokeWidth={1.5}
                      strokeOpacity={0.8}
                      className="pointer-events-auto cursor-pointer"
                      onMouseEnter={() => setHover({ ...pt, cx, cy })}
                      onMouseLeave={() => setHover(null)}
                    />
                    {pt.category === 'contradiction' && (
                      <text
                        x={cx}
                        y={cy + 4}
                        textAnchor="middle"
                        fontSize={r}
                        fill="white"
                        className="pointer-events-none select-none"
                      >
                        !
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>
          )}
          {hover && (
            <div
              className="absolute z-10 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 shadow-lg pointer-events-none text-xs max-w-[200px]"
              style={{
                left: Math.min(hover.cx + 12, dims.width - 180),
                top: Math.max(hover.cy - 10, 4),
              }}
            >
              {hover.label && <p className="font-medium text-gray-900 dark:text-white mb-1 truncate">{hover.label}</p>}
              <p className="text-gray-600 dark:text-slate-300">
                <span
                  className="inline-block w-2 h-2 rounded-full mr-1 align-middle"
                  style={{ backgroundColor: CATEGORY_COLORS[hover.category] || '#6b7280' }}
                />
                {t(`heatmap.${hover.category}`) || hover.category}
              </p>
              <p className="text-gray-500 dark:text-slate-400">
                {t('heatmap.points_count') || 'Intensity'}: {Math.round(hover.intensity * 100)}%
              </p>
            </div>
          )}
        </div>
        {heatmap && hasPoints && <HeatmapLegend heatmap={heatmap} />}
      </div>
    </AsyncStateWrapper>
  );
}
