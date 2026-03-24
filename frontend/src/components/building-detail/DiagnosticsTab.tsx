import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { DiagnosticTimeline } from '@/components/DiagnosticTimeline';
import { RoleGate } from '@/components/RoleGate';
import { DiagnosticPublicationCard } from '@/components/building-detail/DiagnosticPublicationCard';
import MissionOrderCard from '@/components/building-detail/MissionOrderCard';
import { diagnosticIntegrationApi } from '@/api/diagnosticIntegration';
import type { Diagnostic } from '@/types';
import { Plus, Loader2 } from 'lucide-react';

interface DiagnosticsTabProps {
  buildingId: string;
  diagnostics: Diagnostic[];
  onCreateClick: () => void;
}

export function DiagnosticsTab({ buildingId, diagnostics, onCreateClick }: DiagnosticsTabProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const {
    data: publications = [],
    isLoading: pubLoading,
    isError: pubError,
  } = useQuery({
    queryKey: ['diagnostic-publications', buildingId],
    queryFn: () => diagnosticIntegrationApi.getPublicationsForBuilding(buildingId),
    enabled: !!buildingId,
  });

  const {
    data: missionOrders = [],
    isLoading: ordersLoading,
    isError: ordersError,
  } = useQuery({
    queryKey: ['mission-orders', buildingId],
    queryFn: () => diagnosticIntegrationApi.getMissionOrdersForBuilding(buildingId),
    enabled: !!buildingId,
  });

  const createOrder = useMutation({
    mutationFn: (data: { mission_type: string; context_notes: string }) =>
      diagnosticIntegrationApi.createMissionOrder({
        building_id: buildingId,
        mission_type: data.mission_type,
        context_notes: data.context_notes || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mission-orders', buildingId] });
    },
  });

  return (
    <div className="space-y-6">
      {/* Existing diagnostics section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200">
            {t('building.diagnosticsCount', { count: diagnostics.length })}
          </h3>
          <RoleGate allowedRoles={['admin', 'diagnostician']}>
            <button
              onClick={onCreateClick}
              data-testid="building-diagnostic-create-button"
              className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
            >
              <Plus className="w-4 h-4" />
              {t('diagnostic.create')}
            </button>
          </RoleGate>
        </div>
        {diagnostics.length > 0 ? (
          <DiagnosticTimeline diagnostics={diagnostics} />
        ) : (
          <p className="text-center text-sm text-gray-500 dark:text-slate-400 py-8">{t('building.noDiagnostics')}</p>
        )}
      </div>

      {/* Diagnostic publications */}
      {pubLoading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
        </div>
      ) : pubError ? (
        <div className="text-sm text-red-600 dark:text-red-400 py-4">
          {t('app.error') || 'Failed to load publications'}
        </div>
      ) : (
        <DiagnosticPublicationCard publications={publications} />
      )}

      {/* Mission orders */}
      {ordersLoading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
        </div>
      ) : ordersError ? (
        <div className="text-sm text-red-600 dark:text-red-400 py-4">
          {t('app.error') || 'Failed to load mission orders'}
        </div>
      ) : (
        <MissionOrderCard
          orders={missionOrders}
          onSubmit={(data) => createOrder.mutate(data)}
          isSubmitting={createOrder.isPending}
        />
      )}
    </div>
  );
}

export default DiagnosticsTab;
