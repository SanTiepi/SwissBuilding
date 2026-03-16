import { RISK_COLORS } from '@/utils/constants';
import { useTranslation } from '@/i18n';
import type { RiskLevel } from '@/types';

interface RiskGaugeProps {
  score?: number; // 0 to 1
  level: RiskLevel;
  label?: string;
}

const riskLabelKeys: Record<RiskLevel, string> = {
  low: 'risk.low',
  medium: 'risk.medium',
  high: 'risk.high',
  critical: 'risk.critical',
  unknown: 'risk.unknown',
};

export function RiskGauge({ score, level, label }: RiskGaugeProps) {
  const { t } = useTranslation();
  const isDark = typeof document !== 'undefined' && document.documentElement.classList.contains('dark');

  const color = RISK_COLORS[level] || RISK_COLORS.unknown;
  const safeScore =
    typeof score === 'number' && !isNaN(score)
      ? score
      : level === 'critical'
        ? 0.9
        : level === 'high'
          ? 0.7
          : level === 'medium'
            ? 0.45
            : level === 'low'
              ? 0.15
              : 0;
  const percentage = Math.round(safeScore * 100);

  // SVG semi-circle gauge parameters
  const size = 180;
  const strokeWidth = 14;
  const cx = size / 2;
  const cy = size / 2 + 10; // shift center down a bit for semi-circle
  const radius = (size - strokeWidth) / 2 - 4;

  // Arc from 180 degrees (left) to 0 degrees (right) = semi-circle
  const startAngle = Math.PI; // 180 degrees
  const endAngle = 0; // 0 degrees
  const totalArc = Math.PI; // 180 degrees

  // Background arc path (full semi-circle)
  const bgStartX = cx + radius * Math.cos(startAngle);
  const bgStartY = cy - radius * Math.sin(startAngle);
  const bgEndX = cx + radius * Math.cos(endAngle);
  const bgEndY = cy - radius * Math.sin(endAngle);
  const bgPath = `M ${bgStartX} ${bgStartY} A ${radius} ${radius} 0 0 1 ${bgEndX} ${bgEndY}`;

  // Value arc path
  const clampedScore = Math.max(0, Math.min(1, safeScore));
  const valueAngle = startAngle - clampedScore * totalArc;
  const valueEndX = cx + radius * Math.cos(valueAngle);
  const valueEndY = cy - radius * Math.sin(valueAngle);
  const largeArcFlag = clampedScore > 0.5 ? 1 : 0;
  const valuePath =
    clampedScore > 0
      ? `M ${bgStartX} ${bgStartY} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${valueEndX} ${valueEndY}`
      : '';

  return (
    <div className="flex flex-col items-center">
      {label && <p className="text-sm font-medium text-slate-600 dark:text-slate-300 mb-2">{label}</p>}

      <svg
        width={size}
        height={size / 2 + 30}
        viewBox={`0 0 ${size} ${size / 2 + 30}`}
        className="overflow-hidden"
        role="img"
        aria-label={`${label || t(riskLabelKeys[level])}: ${percentage}%`}
      >
        {/* Background arc */}
        <path
          d={bgPath}
          fill="none"
          stroke={isDark ? '#334155' : '#e2e8f0'}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />

        {/* Value arc */}
        {clampedScore > 0 && (
          <path d={valuePath} fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
        )}

        {/* Score percentage text */}
        <text
          x={cx}
          y={cy - 10}
          textAnchor="middle"
          className="text-3xl font-bold"
          fill={color}
          style={{ fontSize: '36px', fontWeight: 700 }}
        >
          {percentage}%
        </text>

        {/* Risk level label */}
        <text
          x={cx}
          y={cy + 16}
          textAnchor="middle"
          className="text-sm"
          fill={isDark ? '#94a3b8' : '#64748b'}
          style={{ fontSize: '14px', fontWeight: 500 }}
        >
          {t(riskLabelKeys[level])}
        </text>
      </svg>
    </div>
  );
}
