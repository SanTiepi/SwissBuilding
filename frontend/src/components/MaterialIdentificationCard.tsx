import { AlertTriangle, CheckCircle, FlaskConical, Info } from 'lucide-react';
import type { MaterialRecognitionResult, PollutantDetail } from '@/api/materialRecognition';

interface Props {
  result: MaterialRecognitionResult;
}

const POLLUTANT_LABELS: Record<string, string> = {
  asbestos: 'Amiante',
  pcb: 'PCB',
  lead: 'Plomb',
  hap: 'HAP',
  radon: 'Radon',
  pfas: 'PFAS',
};

function probabilityColor(p: number): string {
  if (p >= 0.7) return 'text-red-600 dark:text-red-400';
  if (p >= 0.4) return 'text-orange-500 dark:text-orange-400';
  if (p >= 0.1) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-green-600 dark:text-green-400';
}

function confidenceBadge(c: number): { label: string; color: string } {
  if (c >= 0.8) return { label: 'Haute', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' };
  if (c >= 0.5)
    return { label: 'Moyenne', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' };
  return { label: 'Faible', color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' };
}

function PollutantRow({ name, detail }: { name: string; detail: PollutantDetail }) {
  const label = POLLUTANT_LABELS[name] || name;
  const pct = Math.round(detail.probability * 100);
  if (pct === 0) return null;

  return (
    <div className="flex items-start gap-3 py-2">
      <div className="flex-shrink-0 w-24">
        <span className={`font-medium ${probabilityColor(detail.probability)}`}>
          {label} {pct}%
        </span>
      </div>
      <div className="flex-1">
        <div className="h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${detail.probability >= 0.5 ? 'bg-red-500' : 'bg-yellow-400'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{detail.reason}</p>
      </div>
    </div>
  );
}

export function MaterialIdentificationCard({ result }: Props) {
  const badge = confidenceBadge(result.confidence_overall);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FlaskConical className="w-5 h-5 text-indigo-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {result.material_name || result.material_type}
          </h3>
        </div>
        <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${badge.color}`}>
          Confiance: {badge.label} ({Math.round(result.confidence_overall * 100)}%)
        </span>
      </div>

      {/* Description */}
      {result.description && (
        <p className="text-sm text-gray-600 dark:text-slate-300">{result.description}</p>
      )}

      {/* Year + Materials */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        {result.estimated_year_range && (
          <div>
            <span className="text-gray-500 dark:text-slate-400">Période estimée</span>
            <p className="font-medium text-gray-900 dark:text-white">{result.estimated_year_range}</p>
          </div>
        )}
        {result.identified_materials.length > 0 && (
          <div>
            <span className="text-gray-500 dark:text-slate-400">Composants</span>
            <p className="font-medium text-gray-900 dark:text-white">
              {result.identified_materials.join(', ')}
            </p>
          </div>
        )}
      </div>

      {/* High risk alert */}
      {result.has_high_risk && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <span className="text-sm font-medium text-red-700 dark:text-red-300">
            Risque polluant élevé détecté — test laboratoire recommandé
          </span>
        </div>
      )}

      {/* Pollutants */}
      {Object.keys(result.likely_pollutants).length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">Polluants probables</h4>
          <div className="space-y-1">
            {Object.entries(result.likely_pollutants)
              .sort(([, a], [, b]) => b.probability - a.probability)
              .map(([name, detail]) => (
                <PollutantRow key={name} name={name} detail={detail} />
              ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {result.recommendations.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">Recommandations</h4>
          <ul className="space-y-1.5">
            {result.recommendations.map((rec, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600 dark:text-slate-300">
                {result.has_high_risk ? (
                  <Info className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                )}
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
