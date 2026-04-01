import { useQuery } from '@tanstack/react-query';
import { cn } from '@/utils/formatters';
import { proactiveAlertsApi } from '@/api/proactiveAlerts';
import { AlertTriangle } from 'lucide-react';

interface BuildingAlertBadgeProps {
  buildingId: string;
  compact?: boolean;
}

const SEVERITY_COLORS = {
  critical: 'bg-red-500 text-white',
  warning: 'bg-amber-500 text-white',
  info: 'bg-blue-500 text-white',
} as const;

/**
 * Small badge showing the alert count for a single building.
 * Color reflects the highest severity among unread alerts.
 */
export function BuildingAlertBadge({ buildingId, compact = false }: BuildingAlertBadgeProps) {
  const { data: alerts } = useQuery({
    queryKey: ['building-alerts', buildingId],
    queryFn: () => proactiveAlertsApi.scanBuilding(buildingId),
    staleTime: 5 * 60 * 1000, // 5 min — don't re-scan on every render
    enabled: !!buildingId,
  });

  if (!alerts || alerts.length === 0) return null;

  // Determine highest severity
  const hasCritical = alerts.some((a) => a.severity === 'critical');
  const hasWarning = alerts.some((a) => a.severity === 'warning');
  const highestSeverity = hasCritical ? 'critical' : hasWarning ? 'warning' : 'info';
  const colorClass = SEVERITY_COLORS[highestSeverity];

  if (compact) {
    return (
      <span
        className={cn('inline-flex h-5 min-w-5 items-center justify-center rounded-full text-xs font-bold', colorClass)}
      >
        {alerts.length}
      </span>
    );
  }

  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium', colorClass)}>
      <AlertTriangle className="h-3 w-3" />
      {alerts.length}
    </span>
  );
}
