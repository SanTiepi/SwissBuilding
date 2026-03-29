import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from '@/i18n';
import { useQuery } from '@tanstack/react-query';
import { nudgesApi, type Nudge, type NudgeContext } from '@/api/nudges';
import { NudgeCard } from './NudgeCard';

interface NudgePanelProps {
  buildingId?: string;
  context?: NudgeContext;
}

const DISMISS_STORAGE_KEY = 'baticonnect_nudge_dismissed';
const DISMISS_DURATION_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

function getDismissedIds(): Record<string, number> {
  try {
    const raw = localStorage.getItem(DISMISS_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Record<string, number>;
    const now = Date.now();
    // Clean expired dismissals
    const cleaned: Record<string, number> = {};
    for (const [id, ts] of Object.entries(parsed)) {
      if (now - ts < DISMISS_DURATION_MS) {
        cleaned[id] = ts;
      }
    }
    return cleaned;
  } catch {
    return {};
  }
}

function dismissNudge(id: string): void {
  const current = getDismissedIds();
  current[id] = Date.now();
  localStorage.setItem(DISMISS_STORAGE_KEY, JSON.stringify(current));
}

export function NudgePanel({ buildingId, context = 'dashboard' }: NudgePanelProps) {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useState(false);
  const [dismissedIds, setDismissedIds] = useState<Record<string, number>>({});

  useEffect(() => {
    setDismissedIds(getDismissedIds());
  }, []);

  const { data, isLoading } = useQuery({
    queryKey: ['nudges', buildingId ?? 'portfolio', context],
    queryFn: () =>
      buildingId
        ? nudgesApi.listForBuilding(buildingId, context)
        : nudgesApi.listForPortfolio(context),
    staleTime: 60_000,
  });

  const visibleNudges = useMemo(() => {
    if (!data?.nudges) return [];
    return data.nudges.filter((n) => !dismissedIds[n.id]);
  }, [data, dismissedIds]);

  const handleDismiss = (id: string) => {
    dismissNudge(id);
    setDismissedIds((prev) => ({ ...prev, [id]: Date.now() }));
  };

  const handleAction = (_nudge: Nudge) => {
    // Future: navigate to relevant entity or open action modal
  };

  if (isLoading) return null;
  if (visibleNudges.length === 0) return null;

  return (
    <div data-testid="nudge-panel" className="mb-4">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="mb-2 flex w-full items-center justify-between text-left"
        data-testid="nudge-panel-toggle"
      >
        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          {t('nudge.title')} ({visibleNudges.length})
        </h2>
        <span className="text-xs text-gray-400">{collapsed ? '▸' : '▾'}</span>
      </button>

      {!collapsed && (
        <div className="grid gap-3 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {visibleNudges.map((nudge) => (
            <NudgeCard
              key={nudge.id}
              nudge={nudge}
              onDismiss={handleDismiss}
              onAction={handleAction}
            />
          ))}
        </div>
      )}
    </div>
  );
}
