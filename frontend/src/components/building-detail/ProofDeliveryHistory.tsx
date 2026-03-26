import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { proofDeliveryApi, type ProofDelivery, type DeliveryStatus } from '@/api/proofDelivery';
import { Send, Eye, ShieldCheck, Clock, Package, FileText, Inbox } from 'lucide-react';

const STATUS_STEPS: DeliveryStatus[] = ['queued', 'sent', 'delivered', 'viewed', 'acknowledged'];

const STATUS_CONFIG: Record<DeliveryStatus, { icon: React.ElementType; color: string }> = {
  queued: { icon: Clock, color: 'text-gray-400 dark:text-gray-500' },
  sent: { icon: Send, color: 'text-blue-500 dark:text-blue-400' },
  delivered: { icon: Inbox, color: 'text-green-500 dark:text-green-400' },
  viewed: { icon: Eye, color: 'text-purple-500 dark:text-purple-400' },
  acknowledged: { icon: ShieldCheck, color: 'text-emerald-600 dark:text-emerald-400' },
};

const AUDIENCE_COLORS: Record<string, string> = {
  owner: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
  authority: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
  contractor: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  tenant: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
};

interface ProofDeliveryHistoryProps {
  buildingId: string;
}

export default function ProofDeliveryHistory({ buildingId }: ProofDeliveryHistoryProps) {
  const { t } = useTranslation();

  const { data: deliveries, isLoading } = useQuery({
    queryKey: ['proof-deliveries', buildingId],
    queryFn: () => proofDeliveryApi.listByBuilding(buildingId),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div
        className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6"
        data-testid="proof-delivery-loading"
      >
        <div className="animate-pulse space-y-3">
          <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-40" />
          <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      </div>
    );
  }

  const items = deliveries ?? [];

  // Group by target
  const grouped = new Map<string, ProofDelivery[]>();
  for (const d of items) {
    const key = `${d.target_type}:${d.target_id}`;
    const list = grouped.get(key) ?? [];
    list.push(d);
    grouped.set(key, list);
  }

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6"
      data-testid="proof-delivery-history"
    >
      <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
        <Package className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        {t('proof_delivery.title')}
      </h3>

      {items.length === 0 ? (
        <div className="text-center py-8" data-testid="proof-delivery-empty">
          <FileText className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
          <p className="text-sm text-gray-500 dark:text-gray-400">{t('proof_delivery.empty')}</p>
        </div>
      ) : (
        <div className="space-y-5" data-testid="proof-delivery-list">
          {Array.from(grouped.entries()).map(([groupKey, groupItems]) => {
            const first = groupItems[0];
            const TargetIcon = first.target_type === 'pack' ? Package : FileText;
            return (
              <div key={groupKey} data-testid={`delivery-group-${groupKey}`}>
                <div className="flex items-center gap-2 mb-2">
                  <TargetIcon className="w-4 h-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{first.target_name}</span>
                </div>
                <div className="space-y-2 ml-6">
                  {groupItems.map((delivery) => (
                    <DeliveryRow key={delivery.id} delivery={delivery} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function DeliveryRow({ delivery }: { delivery: ProofDelivery }) {
  const { t } = useTranslation();
  const statusIdx = STATUS_STEPS.indexOf(delivery.status);
  const statusConf = STATUS_CONFIG[delivery.status];
  const StatusIcon = statusConf.icon;

  return (
    <div
      className="flex items-center gap-3 py-2 px-3 rounded-lg bg-gray-50 dark:bg-gray-750 dark:bg-gray-900/30"
      data-testid={`delivery-row-${delivery.id}`}
    >
      {/* Status icon */}
      <StatusIcon className={cn('w-4 h-4 flex-shrink-0', statusConf.color)} />

      {/* Audience badge */}
      <span
        className={cn(
          'inline-block px-2 py-0.5 rounded text-xs font-medium',
          AUDIENCE_COLORS[delivery.audience] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
        )}
        data-testid={`audience-badge-${delivery.id}`}
      >
        {delivery.audience}
      </span>

      {/* Method */}
      <span className="text-xs text-gray-500 dark:text-gray-400">{delivery.method}</span>

      {/* Status lifecycle */}
      <div className="flex items-center gap-0.5 flex-1" data-testid={`status-steps-${delivery.id}`}>
        {STATUS_STEPS.map((step, idx) => (
          <div
            key={step}
            className={cn(
              'h-1.5 flex-1 rounded-full',
              idx <= statusIdx ? 'bg-emerald-500 dark:bg-emerald-400' : 'bg-gray-200 dark:bg-gray-700',
            )}
            title={t(`proof_delivery.status_${step}`)}
          />
        ))}
      </div>

      {/* Status label */}
      <span className={cn('text-xs font-medium whitespace-nowrap', statusConf.color)}>
        {t(`proof_delivery.status_${delivery.status}`)}
      </span>

      {/* Hash + version */}
      <div className="hidden sm:flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
        {delivery.content_hash && (
          <span title={delivery.content_hash} data-testid={`hash-${delivery.id}`}>
            #{delivery.content_hash.slice(0, 8)}
          </span>
        )}
        <span data-testid={`version-${delivery.id}`}>v{delivery.version}</span>
      </div>
    </div>
  );
}
