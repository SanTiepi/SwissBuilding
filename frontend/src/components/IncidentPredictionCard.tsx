import { AlertTriangle, CloudRain, Shield, Wind, Thermometer } from 'lucide-react';

interface IncidentPrediction {
  type: string;
  trigger: string;
  probability: number;
  risk_level: string;
  recommended_action: string;
  forecast_day: string;
}

interface IncidentPredictionCardProps {
  prediction: IncidentPrediction;
}

const RISK_STYLES = {
  high: {
    border: 'border-red-300 dark:border-red-700',
    bg: 'bg-red-50 dark:bg-red-900/20',
    badge: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    icon: 'text-red-600 dark:text-red-400',
  },
  medium: {
    border: 'border-amber-300 dark:border-amber-700',
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    badge: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
    icon: 'text-amber-600 dark:text-amber-400',
  },
  low: {
    border: 'border-blue-300 dark:border-blue-700',
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300',
    icon: 'text-blue-600 dark:text-blue-400',
  },
} as const;

const TYPE_LABELS: Record<string, string> = {
  leak: 'Infiltration',
  flooding: 'Inondation',
  mold: 'Moisissure',
  storm_damage: 'Dommage tempete',
  movement: 'Mouvement',
  structural: 'Structural',
};

function renderTriggerIcon(trigger: string, className: string) {
  const lower = trigger.toLowerCase();
  if (lower.includes('heavy_rain')) return <CloudRain className={className} />;
  if (lower.includes('high_wind')) return <Wind className={className} />;
  if (lower.includes('freeze_thaw')) return <Thermometer className={className} />;
  return <AlertTriangle className={className} />;
}

export default function IncidentPredictionCard({ prediction }: IncidentPredictionCardProps) {
  const style = RISK_STYLES[prediction.risk_level as keyof typeof RISK_STYLES] || RISK_STYLES.low;
  const pct = Math.round(prediction.probability * 100);
  const iconClass = `mt-0.5 h-5 w-5 flex-shrink-0 ${style.icon}`;

  return (
    <div className={`rounded-lg border p-4 ${style.border} ${style.bg}`} data-testid="prediction-card">
      <div className="flex items-start gap-3">
        {renderTriggerIcon(prediction.trigger, iconClass)}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-900 dark:text-gray-100">
              {TYPE_LABELS[prediction.type] || prediction.type}
            </span>
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style.badge}`}>
              {pct}%
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{prediction.trigger}</p>
          <div className="mt-2 flex items-center gap-1.5">
            <Shield className="h-3.5 w-3.5 text-gray-400" />
            <p className="text-xs text-gray-500 dark:text-gray-400">{prediction.recommended_action}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
