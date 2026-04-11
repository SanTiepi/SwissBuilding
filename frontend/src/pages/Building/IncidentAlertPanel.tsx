import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle, Loader2 } from 'lucide-react';

import IncidentPredictionCard from '@/components/IncidentPredictionCard';
import { apiClient } from '@/api/client';

interface IncidentAlertPanelProps {
  buildingId: string;
}

interface PredictionResponse {
  building_id: string;
  building_risk_level: string;
  predicted_incidents: Array<{
    type: string;
    trigger: string;
    probability: number;
    risk_level: string;
    recommended_action: string;
    forecast_day: string;
  }>;
  forecast_available: boolean;
  correlation_data: string;
}

function useIncidentPredictions(buildingId: string) {
  return useQuery<PredictionResponse>({
    queryKey: ['incident-predictions', buildingId],
    queryFn: () => apiClient.get(`/buildings/${buildingId}/incident-predictions`).then((r) => r.data),
    staleTime: 30 * 60 * 1000, // 30 min
    enabled: !!buildingId,
  });
}

const RISK_BANNER = {
  high: {
    bg: 'bg-red-50 dark:bg-red-900/20',
    border: 'border-red-200 dark:border-red-800',
    text: 'text-red-800 dark:text-red-200',
    icon: 'text-red-600 dark:text-red-400',
    label: 'Risque eleve',
  },
  medium: {
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    border: 'border-amber-200 dark:border-amber-800',
    text: 'text-amber-800 dark:text-amber-200',
    icon: 'text-amber-600 dark:text-amber-400',
    label: 'Risque modere',
  },
  none: null,
  low: null,
  unknown: null,
} as const;

export default function IncidentAlertPanel({ buildingId }: IncidentAlertPanelProps) {
  const { data, isLoading, isError, error } = useIncidentPredictions(buildingId);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-4 text-sm text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Analyse des correlations meteo/incidents...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
        Erreur: {error instanceof Error ? error.message : 'Impossible de charger les predictions'}
      </div>
    );
  }

  if (!data) return null;

  const predictions = data.predicted_incidents || [];
  const riskLevel = data.building_risk_level;
  const banner = RISK_BANNER[riskLevel as keyof typeof RISK_BANNER];

  return (
    <div className="space-y-3" data-testid="incident-alert-panel">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
        Alertes meteo predictives
      </h3>

      {banner && (
        <div
          className={`flex items-center gap-2 rounded-lg border p-3 ${banner.bg} ${banner.border}`}
          data-testid="risk-banner"
        >
          <AlertTriangle className={`h-5 w-5 ${banner.icon}`} />
          <span className={`text-sm font-medium ${banner.text}`}>{banner.label}</span>
        </div>
      )}

      {predictions.length > 0 ? (
        <div className="space-y-2">
          {predictions.map((p, i) => (
            <IncidentPredictionCard key={`${p.type}-${i}`} prediction={p} />
          ))}
        </div>
      ) : (
        <div
          className="flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-300"
          data-testid="no-alerts"
        >
          <CheckCircle className="h-4 w-4" />
          Aucune alerte meteo pertinente pour ce batiment
        </div>
      )}

      {data.correlation_data === 'no_history' && (
        <p className="text-xs text-gray-400">
          Pas d&apos;historique d&apos;incidents — les predictions s&apos;ameliorent avec les donnees
        </p>
      )}
    </div>
  );
}
