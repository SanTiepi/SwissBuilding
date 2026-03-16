import { useEffect, useState, useCallback } from 'react';
import { WifiOff, Wifi } from 'lucide-react';
import { useTranslation } from '@/i18n';

type Status = 'online' | 'offline' | 'back-online';

export function PwaStatusIndicator() {
  const { t } = useTranslation();

  // Graceful degradation: if navigator.onLine is undefined, render nothing
  if (typeof navigator === 'undefined' || typeof navigator.onLine !== 'boolean') {
    return null;
  }

  return <PwaStatusIndicatorInner t={t} />;
}

function PwaStatusIndicatorInner({ t }: { t: (key: string) => string }) {
  const [status, setStatus] = useState<Status>(navigator.onLine ? 'online' : 'offline');

  const handleOffline = useCallback(() => setStatus('offline'), []);
  const handleOnline = useCallback(() => setStatus('back-online'), []);

  useEffect(() => {
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [handleOnline, handleOffline]);

  useEffect(() => {
    if (status !== 'back-online') return;
    const timer = setTimeout(() => setStatus('online'), 3000);
    return () => clearTimeout(timer);
  }, [status]);

  if (status === 'online') return null;

  const isOffline = status === 'offline';

  return (
    <div
      data-testid="pwa-status-indicator"
      role="status"
      className={`fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-full px-4 py-2 text-sm font-medium shadow-lg transition-all duration-300 flex items-center gap-2 ${
        isOffline
          ? 'bg-amber-100 text-amber-900 dark:bg-amber-900 dark:text-amber-100'
          : 'bg-green-100 text-green-900 dark:bg-green-900 dark:text-green-100'
      }`}
    >
      {isOffline ? <WifiOff className="h-4 w-4" /> : <Wifi className="h-4 w-4" />}
      <span>
        {isOffline
          ? t('pwa.offline') || 'You are offline — some features may be unavailable'
          : t('pwa.back_online') || 'Connection restored'}
      </span>
    </div>
  );
}
