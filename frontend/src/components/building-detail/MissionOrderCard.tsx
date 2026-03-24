import { useState } from 'react';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { Plus, X, Loader2, Send, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';

export interface DiagnosticMissionOrder {
  id: string;
  building_id: string;
  mission_type: string;
  status: 'draft' | 'queued' | 'sent' | 'acknowledged' | 'failed' | 'cancelled';
  external_mission_id?: string | null;
  context_notes?: string | null;
  last_error?: string | null;
  created_at: string;
}

export interface MissionOrderCardProps {
  orders: DiagnosticMissionOrder[];
  onSubmit?: (data: { mission_type: string; context_notes: string }) => void;
  isSubmitting?: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  queued: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  sent: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  acknowledged: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  cancelled: 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
};

const MISSION_TYPES = [
  'asbestos_full',
  'asbestos_complement',
  'pcb',
  'lead',
  'hap',
  'radon',
  'pfas',
  'multi',
] as const;

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  return (
    <span
      className={cn(
        'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
        STATUS_COLORS[status] || STATUS_COLORS.draft,
      )}
      data-testid="mission-status-badge"
    >
      {t(`mission_order.status.${status}`) || status}
    </span>
  );
}

function ExpandableNotes({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const truncated = text.length > 120;

  return (
    <div className="text-xs text-gray-500 dark:text-slate-400 mt-1">
      <span>{expanded || !truncated ? text : `${text.slice(0, 120)}...`}</span>
      {truncated && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="ml-1 text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 inline-flex items-center"
          data-testid="toggle-notes"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      )}
    </div>
  );
}

export default function MissionOrderCard({ orders, onSubmit, isSubmitting }: MissionOrderCardProps) {
  const { t } = useTranslation();
  const [showForm, setShowForm] = useState(false);
  const [missionType, setMissionType] = useState<string>(MISSION_TYPES[0]);
  const [contextNotes, setContextNotes] = useState('');

  const handleSubmit = () => {
    if (onSubmit) {
      onSubmit({ mission_type: missionType, context_notes: contextNotes });
      setMissionType(MISSION_TYPES[0]);
      setContextNotes('');
      setShowForm(false);
    }
  };

  const handleCancel = () => {
    setMissionType(MISSION_TYPES[0]);
    setContextNotes('');
    setShowForm(false);
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4 sm:p-6" data-testid="mission-order-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('mission_order.title') || 'Ordres de mission'}
        </h3>
        {!showForm && onSubmit && (
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 transition-colors"
            data-testid="create-mission-btn"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">{t('mission_order.create') || 'Commander un diagnostic'}</span>
            <span className="sm:hidden">{t('mission_order.create_short') || 'Commander'}</span>
          </button>
        )}
      </div>

      {/* Create form */}
      {showForm && (
        <div
          className="mb-4 p-4 border border-blue-200 dark:border-blue-800 rounded-lg bg-blue-50 dark:bg-blue-900/20"
          data-testid="mission-create-form"
        >
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('mission_order.field.mission_type') || 'Type de mission'}
              </label>
              <select
                value={missionType}
                onChange={(e) => setMissionType(e.target.value)}
                className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                data-testid="mission-type-select"
              >
                {MISSION_TYPES.map((mt) => (
                  <option key={mt} value={mt}>
                    {t(`mission_order.type.${mt}`) || mt}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('mission_order.field.context_notes') || 'Notes de contexte'}
              </label>
              <textarea
                value={contextNotes}
                onChange={(e) => setContextNotes(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                placeholder={t('mission_order.field.context_placeholder') || 'Informations complementaires...'}
                data-testid="mission-context-textarea"
              />
            </div>
            <div className="flex items-center gap-2 justify-end">
              <button
                onClick={handleCancel}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
                data-testid="mission-cancel-btn"
              >
                <X className="w-4 h-4" />
                {t('common.cancel') || 'Annuler'}
              </button>
              <button
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-testid="mission-submit-btn"
              >
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                {t('mission_order.submit') || 'Envoyer'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Order list */}
      {orders.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-slate-400" data-testid="mission-empty-state">
          <Send className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">{t('mission_order.empty') || 'Aucun ordre de mission'}</p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="mission-order-list">
          {orders.map((order) => (
            <div
              key={order.id}
              className="p-3 rounded-lg border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50"
              data-testid="mission-order-item"
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <StatusBadge status={order.status} />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {t(`mission_order.type.${order.mission_type}`) || order.mission_type}
                  </span>
                </div>
                <div className="text-xs text-gray-500 dark:text-slate-400">
                  {new Date(order.created_at).toLocaleDateString('fr-CH')}
                </div>
              </div>

              {order.external_mission_id && (
                <div className="mt-1 text-xs text-gray-500 dark:text-slate-400">
                  <span className="font-medium">{t('mission_order.field.external_id') || 'Ref. externe'}:</span>{' '}
                  <span data-testid="mission-external-id">{order.external_mission_id}</span>
                </div>
              )}

              {order.status === 'failed' && order.last_error && (
                <div
                  className="mt-2 flex items-start gap-1.5 text-xs text-red-600 dark:text-red-400"
                  data-testid="mission-error"
                >
                  <AlertTriangle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                  <span>{order.last_error}</span>
                </div>
              )}

              {order.context_notes && <ExpandableNotes text={order.context_notes} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
