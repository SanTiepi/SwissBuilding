import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { defectTimelineApi, type DefectTimeline, type DefectCreatePayload } from '@/api/defectTimeline';
import { toast } from '@/store/toastStore';
import { Plus, X, Loader2, ShieldAlert, Clock, AlertTriangle } from 'lucide-react';

const DEFECT_TYPES = ['construction', 'pollutant', 'structural', 'installation', 'other'] as const;

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  notified: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  expired: 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
  resolved: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

function urgencyColor(daysRemaining: number | undefined): string {
  if (daysRemaining === undefined || daysRemaining < 0)
    return 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400';
  if (daysRemaining < 15) return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
  if (daysRemaining < 30) return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400';
  if (daysRemaining < 45) return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
  return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
}

function urgencyDot(daysRemaining: number | undefined): string {
  if (daysRemaining === undefined || daysRemaining < 0) return 'bg-gray-400';
  if (daysRemaining < 15) return 'bg-red-500';
  if (daysRemaining < 30) return 'bg-orange-500';
  if (daysRemaining < 45) return 'bg-yellow-500';
  return 'bg-green-500';
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  return (
    <span
      className={cn(
        'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
        STATUS_COLORS[status] || STATUS_COLORS.active,
      )}
      data-testid="defect-status-badge"
    >
      {t(`defect.status_${status}`) || status}
    </span>
  );
}

function CountdownBadge({ daysRemaining }: { daysRemaining: number | undefined }) {
  const { t } = useTranslation();
  if (daysRemaining === undefined) return null;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full',
        urgencyColor(daysRemaining),
      )}
      data-testid="defect-countdown-badge"
    >
      <Clock className="w-3 h-3" />
      {daysRemaining > 0
        ? `${daysRemaining} ${t('defect.days_remaining') || 'j'}`
        : t('defect.status_expired') || 'Expire'}
    </span>
  );
}

interface Props {
  buildingId: string;
}

export default function DefectTimelineWidget({ buildingId }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [formType, setFormType] = useState<string>(DEFECT_TYPES[0]);
  const [formDescription, setFormDescription] = useState('');
  const [formDiscoveryDate, setFormDiscoveryDate] = useState('');
  const [formPurchaseDate, setFormPurchaseDate] = useState('');

  const {
    data: defects = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['defect-timeline', buildingId],
    queryFn: () => defectTimelineApi.list(buildingId),
    enabled: !!buildingId,
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (data: DefectCreatePayload) => defectTimelineApi.create(buildingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['defect-timeline', buildingId] });
      toast(t('defect.add') || 'Defect reported', 'success');
      resetForm();
    },
    onError: () => {
      toast(t('app.error') || 'An error occurred', 'error');
    },
  });

  const resetForm = () => {
    setShowForm(false);
    setFormType(DEFECT_TYPES[0]);
    setFormDescription('');
    setFormDiscoveryDate('');
    setFormPurchaseDate('');
  };

  const handleSubmit = () => {
    if (!formDescription || !formDiscoveryDate || !formPurchaseDate) return;
    createMutation.mutate({
      defect_type: formType,
      description: formDescription,
      discovery_date: formDiscoveryDate,
      purchase_date: formPurchaseDate,
    });
  };

  const { activeDefects, resolvedDefects } = useMemo(() => {
    const active = defects.filter((d: DefectTimeline) => d.status === 'active' || d.status === 'notified');
    const resolved = defects.filter((d: DefectTimeline) => d.status === 'expired' || d.status === 'resolved');
    return { activeDefects: active, resolvedDefects: resolved };
  }, [defects]);

  const urgentCount = activeDefects.filter(
    (d: DefectTimeline) => d.days_remaining !== undefined && d.days_remaining < 30,
  ).length;

  const renderDefect = (item: DefectTimeline) => (
    <div
      key={item.id}
      className="p-3 rounded-lg border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50"
      data-testid="defect-item"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={cn('w-2 h-2 rounded-full flex-shrink-0', urgencyDot(item.days_remaining))}
              title={item.days_remaining !== undefined ? `${item.days_remaining}j` : ''}
            />
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {t(`defect.type_${item.defect_type}`) || item.defect_type}
            </span>
            <StatusBadge status={item.status} />
            <CountdownBadge daysRemaining={item.days_remaining} />
          </div>
          <p className="text-xs text-gray-500 dark:text-slate-400 mt-1 line-clamp-2">{item.description}</p>
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-400 dark:text-slate-500">
            {item.notification_deadline && (
              <span>
                {t('defect.deadline') || 'Echeance'}: {new Date(item.notification_deadline).toLocaleDateString('fr-CH')}
              </span>
            )}
            {item.guarantee_type === 'new_build_rectification' && (
              <span className="text-blue-500 dark:text-blue-400">
                {t('defect.guarantee_new_build') || 'Garantie bien neuf'}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4 sm:p-6" data-testid="defect-timeline-widget">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('defect.title') || 'Echeances defauts'}
          </h3>
          {urgentCount > 0 && (
            <span
              className="px-1.5 py-0.5 text-xs font-medium rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
              data-testid="defect-urgent-count"
            >
              {urgentCount}
            </span>
          )}
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 transition-colors"
            data-testid="defect-add-btn"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">{t('defect.add') || 'Signaler un defaut'}</span>
          </button>
        )}
      </div>

      {/* Create form */}
      {showForm && (
        <div
          className="mb-4 p-4 border border-blue-200 dark:border-blue-800 rounded-lg bg-blue-50 dark:bg-blue-900/20"
          data-testid="defect-add-form"
        >
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('defect.form_type') || 'Type de defaut'}
              </label>
              <select
                value={formType}
                onChange={(e) => setFormType(e.target.value)}
                className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                data-testid="defect-type-select"
              >
                {DEFECT_TYPES.map((dt) => (
                  <option key={dt} value={dt}>
                    {t(`defect.type_${dt}`) || dt}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('defect.form_description') || 'Description du defaut'}
              </label>
              <textarea
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                rows={2}
                className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                placeholder={t('defect.form_description') || 'Description du defaut'}
                data-testid="defect-description-input"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  {t('defect.form_discovery_date') || 'Date de decouverte'}
                </label>
                <input
                  type="date"
                  value={formDiscoveryDate}
                  onChange={(e) => setFormDiscoveryDate(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid="defect-discovery-date-input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  {t('defect.form_purchase_date') || "Date d'achat du bien"}
                </label>
                <input
                  type="date"
                  value={formPurchaseDate}
                  onChange={(e) => setFormPurchaseDate(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid="defect-purchase-date-input"
                />
              </div>
            </div>
            <div className="flex items-center gap-2 justify-end">
              <button
                onClick={resetForm}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
                data-testid="defect-cancel-btn"
              >
                <X className="w-4 h-4" />
                {t('common.cancel') || 'Annuler'}
              </button>
              <button
                onClick={handleSubmit}
                disabled={createMutation.isPending || !formDescription || !formDiscoveryDate || !formPurchaseDate}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-testid="defect-submit-btn"
              >
                {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                {t('defect.add') || 'Signaler un defaut'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-8" data-testid="defect-loading">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="text-center py-8 text-red-600 dark:text-red-400" data-testid="defect-error">
          <p className="text-sm">{t('app.error') || 'Une erreur est survenue'}</p>
        </div>
      )}

      {/* Empty */}
      {!isLoading && !isError && defects.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-slate-400" data-testid="defect-empty">
          <ShieldAlert className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm font-medium">{t('defect.empty') || 'Aucun defaut actif'}</p>
          <p className="text-xs mt-1">
            {t('defect.empty_description') || 'Surveillez les delais de notification de defauts (art. 367 CO)'}
          </p>
        </div>
      )}

      {/* Active defects */}
      {activeDefects.length > 0 && (
        <div className="mb-4" data-testid="defect-active-section">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-orange-500" />
            <h4 className="text-sm font-semibold text-gray-700 dark:text-slate-300">
              {t('defect.status_active') || 'Actif'} ({activeDefects.length})
            </h4>
          </div>
          <div className="space-y-2">{activeDefects.map(renderDefect)}</div>
        </div>
      )}

      {/* Resolved / expired */}
      {resolvedDefects.length > 0 && (
        <div data-testid="defect-resolved-section">
          <p className="text-xs text-gray-400 dark:text-slate-500 mb-2">
            {resolvedDefects.length} {t('defect.status_resolved') || 'resolus'} /{' '}
            {t('defect.status_expired') || 'expires'}
          </p>
        </div>
      )}
    </div>
  );
}
