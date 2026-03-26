import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp } from 'lucide-react';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { intelligenceApi } from '@/api/intelligence';
import { cn } from '@/utils/formatters';

function AnimatedNumber({ value, duration = 800 }: { value: number; duration?: number }) {
  const [display, setDisplay] = useState(value);
  const prevRef = useRef(value);

  useEffect(() => {
    const prev = prevRef.current;
    if (prev === value) return;
    prevRef.current = value;

    const start = performance.now();
    const from = prev;
    const to = value;

    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(from + (to - from) * eased));
      if (progress < 1) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);
  }, [value, duration]);

  return <>{display.toLocaleString('ch')}</>;
}

function TrendIcon({ trend }: { trend: 'growing' | 'stable' | 'declining' }) {
  if (trend === 'growing') return <TrendingUp className="w-4 h-4 text-emerald-500" aria-label="growing" />;
  if (trend === 'declining') return <TrendingDown className="w-4 h-4 text-red-500" aria-label="declining" />;
  return <Minus className="w-4 h-4 text-slate-400" aria-label="stable" />;
}

export function ValueBanner() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const orgId = user?.organization_id;
  const [collapsed, setCollapsed] = useState(false);

  const { data } = useQuery({
    queryKey: ['value-ledger', orgId],
    queryFn: () => intelligenceApi.getValueLedger(orgId!),
    enabled: !!orgId,
    retry: false,
    staleTime: 60 * 1000,
    refetchInterval: 120 * 1000,
  });

  if (!orgId || !data) return null;

  if (collapsed) {
    return (
      <div className="bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 border-b border-red-200 dark:border-red-800">
        <div className="max-w-7xl mx-auto px-4 py-1 flex items-center justify-between">
          <button
            onClick={() => setCollapsed(false)}
            className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors"
          >
            <ChevronDown className="w-3.5 h-3.5" />
            <span className="font-bold text-red-600 dark:text-red-400">
              <AnimatedNumber value={data.value_chf_estimate} /> CHF
            </span>
            <TrendIcon trend={data.trend} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/20 border-b border-red-200 dark:border-red-800">
      <div className="max-w-7xl mx-auto px-4 py-2 flex items-center justify-between gap-3">
        <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 flex-1 min-w-0 truncate">
          {t('value.banner_text', {
            sources: data.sources_unified_total,
            contradictions: data.contradictions_resolved_total,
            proofs: data.proof_chains_created_total,
            chf: data.value_chf_estimate.toLocaleString('ch'),
          })}
        </p>
        <div className="flex items-center gap-2 shrink-0">
          <TrendIcon trend={data.trend} />
          <span
            className={cn(
              'text-[10px] font-medium',
              data.trend === 'growing'
                ? 'text-emerald-600 dark:text-emerald-400'
                : data.trend === 'declining'
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-slate-500 dark:text-slate-400',
            )}
          >
            {t(`value.trend_${data.trend}`)}
          </span>
          <button
            onClick={() => setCollapsed(true)}
            className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors text-slate-500 dark:text-slate-400"
            aria-label="Collapse"
          >
            <ChevronUp className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
