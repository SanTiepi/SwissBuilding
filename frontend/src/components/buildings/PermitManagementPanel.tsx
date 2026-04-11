import React, { memo, useState } from 'react';
import { cn } from '@/utils/formatters';
import { usePermits } from '@/hooks/usePermits';
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import { FileCheck, AlertCircle, Plus, Trash2 } from 'lucide-react';
import { useTranslation } from '@/i18n';
import { format, isBefore, addDays } from 'date-fns';
import type { Permit, PermitCreate } from '@/types';
import { permitsApi } from '@/api/permits';

interface Props {
  buildingId: string;
}

const getSeverityColor = (daysUntilExpiry: number) => {
  if (daysUntilExpiry < 0) return 'border-red-300 bg-red-50 dark:bg-red-950/30';
  if (daysUntilExpiry < 30) return 'border-amber-300 bg-amber-50 dark:bg-amber-950/30';
  return 'border-green-300 bg-green-50 dark:bg-green-950/30';
};

const getSeverityIcon = (daysUntilExpiry: number) => {
  if (daysUntilExpiry < 0) return '❌';
  if (daysUntilExpiry < 30) return '🚩';
  return '✅';
};

const getStatusBadgeColor = (status: string) => {
  switch (status) {
    case 'approved':
      return 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300';
    case 'submitted':
      return 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';
    case 'rejected':
      return 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300';
    case 'pending':
      return 'bg-gray-100 text-gray-700 dark:bg-gray-700/40 dark:text-gray-300';
    case 'expired':
      return 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300';
    default:
      return 'bg-gray-100 text-gray-700 dark:bg-gray-700/40 dark:text-gray-300';
  }
};

const calculateDaysUntilExpiry = (expiryDate: string | Date): number => {
  const expiry = typeof expiryDate === 'string' ? new Date(expiryDate) : expiryDate;
  const today = new Date();
  const diffMs = expiry.getTime() - today.getTime();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
};

export const PermitManagementPanel = memo(({ buildingId }: Props) => {
  const { t } = useTranslation();
  const { permits, alerts, isLoading, isError, refetch } = usePermits(buildingId);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newPermit, setNewPermit] = useState<Partial<PermitCreate>>({
    permit_type: 'renovation',
    status: 'pending',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleAddPermit = async () => {
    if (!newPermit.permit_type || !newPermit.expiry_date) {
      alert('Please fill all required fields');
      return;
    }

    try {
      setIsSubmitting(true);
      await permitsApi.create(buildingId, newPermit as PermitCreate);
      setNewPermit({ permit_type: 'renovation', status: 'pending' });
      setShowAddForm(false);
      await refetch();
    } catch (error) {
      console.error('Failed to create permit:', error);
      alert('Failed to create permit');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeletePermit = async (permitId: string) => {
    if (!window.confirm('Delete this permit?')) return;
    try {
      await permitsApi.delete(buildingId, permitId);
      await refetch();
    } catch (error) {
      console.error('Failed to delete permit:', error);
      alert('Failed to delete permit');
    }
  };

  return (
    <AsyncStateWrapper
      isLoading={isLoading}
      isError={isError}
      data={permits}
      variant="card"
      title={t('permits.title') || 'Permis & Deadlines'}
      icon={<FileCheck className="w-5 h-5" />}
      emptyMessage={t('permits.no_permits') || 'Aucun permis enregistré'}
    >
      <div className="p-6 border rounded-lg bg-white dark:bg-gray-900">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {t('permits.title') || 'Permis & Deadlines'}
          </h3>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Ajouter permis
          </button>
        </div>

        {/* Add Permit Form */}
        {showAddForm && (
          <div className="mb-6 p-4 border border-blue-300 rounded-lg bg-blue-50 dark:bg-blue-950/30 dark:border-blue-700">
            <h4 className="font-semibold text-sm text-gray-900 dark:text-gray-100 mb-3">
              Nouveau permis
            </h4>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Type
                </label>
                <select
                  value={newPermit.permit_type || 'renovation'}
                  onChange={(e) => setNewPermit({ ...newPermit, permit_type: e.target.value })}
                  className="w-full px-3 py-2 border rounded text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
                >
                  <option value="renovation">Renovation</option>
                  <option value="subsidy">Subsidy</option>
                  <option value="declaration">Declaration</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Expiry Date *
                </label>
                <input
                  type="date"
                  value={newPermit.expiry_date ? new Date(newPermit.expiry_date).toISOString().split('T')[0] : ''}
                  onChange={(e) => setNewPermit({ ...newPermit, expiry_date: new Date(e.target.value) })}
                  className="w-full px-3 py-2 border rounded text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Notes
                </label>
                <textarea
                  value={newPermit.notes || ''}
                  onChange={(e) => setNewPermit({ ...newPermit, notes: e.target.value })}
                  className="w-full px-3 py-2 border rounded text-sm dark:bg-gray-800 dark:border-gray-600 dark:text-gray-100"
                  rows={2}
                />
              </div>

              <div className="flex gap-2">
                <button
                  onClick={handleAddPermit}
                  disabled={isSubmitting}
                  className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white px-3 py-2 rounded text-sm font-medium transition-colors"
                >
                  {isSubmitting ? 'Creating...' : 'Create'}
                </button>
                <button
                  onClick={() => setShowAddForm(false)}
                  className="flex-1 bg-gray-300 hover:bg-gray-400 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-gray-100 px-3 py-2 rounded text-sm font-medium transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Alerts */}
        {alerts.length > 0 && (
          <div className="mb-6 space-y-2">
            {alerts.map((alert) => (
              <div
                key={alert.permit_id}
                className={cn(
                  'p-3 rounded border flex items-start gap-3',
                  alert.severity === 'critical'
                    ? 'border-red-300 bg-red-50 dark:bg-red-950/30 dark:border-red-700'
                    : 'border-amber-300 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-700'
                )}
              >
                <AlertCircle
                  className={cn(
                    'w-5 h-5 flex-shrink-0 mt-0.5',
                    alert.severity === 'critical' ? 'text-red-600 dark:text-red-400' : 'text-amber-600 dark:text-amber-400'
                  )}
                />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{alert.message}</p>
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{alert.action}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Permits List */}
        <div className="space-y-3">
          {permits.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <FileCheck className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No permits recorded yet</p>
            </div>
          ) : (
            permits.map((permit) => {
              const daysUntilExpiry = calculateDaysUntilExpiry(permit.expiry_date);
              return (
                <div
                  key={permit.id}
                  className={cn(
                    'p-4 rounded-lg border',
                    getSeverityColor(daysUntilExpiry)
                  )}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="font-semibold text-sm text-gray-900 dark:text-gray-100">
                        {getSeverityIcon(daysUntilExpiry)} {permit.permit_type} — {permit.id.slice(0, 8)}
                      </div>
                      <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                        Authority: {permit.notes || 'N/A'}
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeletePermit(permit.id)}
                      className="ml-2 p-2 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 transition-colors"
                      title="Delete permit"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <span
                        className={cn(
                          'inline-block text-xs font-bold px-2.5 py-1 rounded',
                          getStatusBadgeColor(permit.status)
                        )}
                      >
                        {permit.status}
                      </span>
                      <div className="text-xs text-gray-600 dark:text-gray-400 mt-2">
                        Expiry: {format(new Date(permit.expiry_date), 'dd.MM.yyyy')}
                        {daysUntilExpiry < 0
                          ? ` (EXPIRED ${Math.abs(daysUntilExpiry)} days ago)`
                          : daysUntilExpiry < 30
                            ? ` (in ${daysUntilExpiry} days)`
                            : ` (in ${daysUntilExpiry} days)`}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </AsyncStateWrapper>
  );
});

PermitManagementPanel.displayName = 'PermitManagementPanel';
