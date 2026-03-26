import { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { intelligenceApi } from '@/api/intelligence';
import { cn } from '@/utils/formatters';
import type { ValueEvent } from '@/api/intelligence';

const EVENT_LABELS: Record<string, string> = {
  contradiction_resolved: '+1 contradiction resolue',
  source_unified: '+1 source unifiee',
  proof_created: '+1 preuve creee',
  document_secured: '+1 document securise',
  decision_backed: '+1 decision etayee',
};

function eventLabel(evt: ValueEvent): string {
  return EVENT_LABELS[evt.event_type] || evt.delta_description;
}

export function ValuePulse() {
  const user = useAuthStore((s) => s.user);
  const orgId = user?.organization_id;
  const [dismissed, setDismissed] = useState(false);
  const [visible, setVisible] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  const { data: events } = useQuery({
    queryKey: ['value-events', orgId, 5],
    queryFn: () => intelligenceApi.getValueEvents(orgId!, 5),
    enabled: !!orgId,
    retry: false,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });

  const currentEvent = events && events.length > 0 ? events[currentIndex % events.length] : null;

  // Cycle through events
  useEffect(() => {
    if (!events || events.length <= 1) return;
    const interval = setInterval(() => {
      setVisible(false);
      setTimeout(() => {
        setCurrentIndex((prev) => (prev + 1) % events.length);
        setVisible(true);
      }, 300);
    }, 8000);
    return () => clearInterval(interval);
  }, [events]);

  // Show on data arrival — sync state from external data change
  /* eslint-disable react-hooks/set-state-in-effect -- syncing from query data arrival */
  useEffect(() => {
    if (currentEvent) {
      setVisible(true);
      setDismissed(false);
    }
  }, [currentEvent]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleDismiss = useCallback(() => {
    setDismissed(true);
    setVisible(false);
  }, []);

  if (!orgId || !currentEvent || dismissed) return null;

  return (
    <div
      className={cn(
        'fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border',
        'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700',
        'transition-all duration-300 max-w-xs',
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2 pointer-events-none',
      )}
      role="status"
      aria-live="polite"
    >
      {/* Pulse dot */}
      <span className="relative flex h-3 w-3 shrink-0">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
      </span>

      <span className="text-sm text-slate-700 dark:text-slate-200 font-medium">{eventLabel(currentEvent)}</span>

      <button
        onClick={handleDismiss}
        className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 shrink-0"
        aria-label="Dismiss"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
