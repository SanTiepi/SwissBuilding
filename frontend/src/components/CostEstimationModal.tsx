import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { costPredictionApi } from '@/api/costPrediction';
import type { CostPredictionRequest, CostPredictionResponse } from '@/api/costPrediction';
import { formatCHF } from '@/utils/formatters';
import { toast } from '@/store/toastStore';
import { X, Loader2, Calculator, Clock, Gauge, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/utils/formatters';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const POLLUTANT_OPTIONS = ['asbestos', 'pcb', 'lead', 'hap', 'radon', 'pfas'] as const;

const MATERIAL_OPTIONS = [
  'flocage',
  'faux_plafond',
  'colle_carrelage',
  'joint',
  'peinture',
  'enduit',
  'isolation',
  'conduit',
  'revetement_sol',
  'toiture',
] as const;

const CONDITION_OPTIONS = ['bon', 'degrade', 'friable'] as const;

const CANTON_OPTIONS = ['VD', 'GE', 'ZH', 'BE', 'VS'] as const;

const ACCESSIBILITY_OPTIONS = ['facile', 'normal', 'difficile', 'tres_difficile'] as const;

const COMPLEXITY_COLORS: Record<string, string> = {
  simple: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  moyenne: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  complexe: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function costBarPosition(min: number, median: number, max: number) {
  if (max === min) return { leftPct: 0, medianPct: 50, widthPct: 100 };
  const range = max - min;
  const medianPct = ((median - min) / range) * 100;
  return { leftPct: 0, medianPct, widthPct: 100 };
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SelectField({
  label,
  value,
  onChange,
  options,
  renderLabel,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: readonly string[];
  renderLabel: (v: string) => string;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-gray-700 dark:text-slate-300">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {renderLabel(opt)}
          </option>
        ))}
      </select>
    </label>
  );
}

function CostRangeBar({ min, median, max }: { min: number; median: number; max: number }) {
  const { medianPct } = costBarPosition(min, median, max);
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-slate-400">
        <span>{formatCHF(min)}</span>
        <span className="font-semibold text-blue-600 dark:text-blue-400">{formatCHF(median)}</span>
        <span>{formatCHF(max)}</span>
      </div>
      <div className="relative h-3 w-full rounded-full bg-gray-200 dark:bg-slate-600 overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-green-400 via-blue-500 to-orange-400"
          style={{ width: '100%' }}
        />
        <div
          className="absolute top-0 h-full w-0.5 bg-blue-800 dark:bg-blue-200"
          style={{ left: `${medianPct}%` }}
          title={`Median: ${formatCHF(median)}`}
        />
      </div>
      <div className="flex items-center justify-between text-[10px] text-gray-400 dark:text-slate-500">
        <span>Min</span>
        <span>Median</span>
        <span>Max</span>
      </div>
    </div>
  );
}

function BreakdownTable({
  items,
  t,
}: {
  items: CostPredictionResponse['breakdown'];
  t: (key: string) => string;
}) {
  const [expanded, setExpanded] = useState(false);
  if (!items.length) return null;

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
      >
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        {t('cost_prediction.breakdown') || 'Detail des postes'}
      </button>
      {expanded && (
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-slate-600">
                <th className="text-left py-1.5 pr-3 font-medium text-gray-600 dark:text-slate-400">Poste</th>
                <th className="text-right py-1.5 px-2 font-medium text-gray-600 dark:text-slate-400">%</th>
                <th className="text-right py-1.5 px-2 font-medium text-gray-600 dark:text-slate-400">Min</th>
                <th className="text-right py-1.5 px-2 font-medium text-gray-600 dark:text-slate-400">Median</th>
                <th className="text-right py-1.5 pl-2 font-medium text-gray-600 dark:text-slate-400">Max</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr
                  key={idx}
                  className="border-b border-gray-100 dark:border-slate-700 last:border-0"
                >
                  <td className="py-1.5 pr-3 text-gray-800 dark:text-slate-200">{item.label}</td>
                  <td className="py-1.5 px-2 text-right text-gray-600 dark:text-slate-400">
                    {item.percentage}%
                  </td>
                  <td className="py-1.5 px-2 text-right text-gray-600 dark:text-slate-400">
                    {formatCHF(item.amount_min)}
                  </td>
                  <td className="py-1.5 px-2 text-right font-medium text-gray-800 dark:text-slate-200">
                    {formatCHF(item.amount_median)}
                  </td>
                  <td className="py-1.5 pl-2 text-right text-gray-600 dark:text-slate-400">
                    {formatCHF(item.amount_max)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export interface CostEstimationModalProps {
  open: boolean;
  onClose: () => void;
  /** Pre-fill pollutant from diagnostic context */
  defaultPollutant?: string;
  /** Pre-fill canton from building context */
  defaultCanton?: string;
}

export function CostEstimationModal({
  open,
  onClose,
  defaultPollutant,
  defaultCanton,
}: CostEstimationModalProps) {
  const { t } = useTranslation();

  // Form state
  const [pollutantType, setPollutantType] = useState(defaultPollutant || 'asbestos');
  const [materialType, setMaterialType] = useState<string>('flocage');
  const [condition, setCondition] = useState<string>('bon');
  const [surfaceM2, setSurfaceM2] = useState<number>(50);
  const [canton, setCanton] = useState(defaultCanton || 'VD');
  const [accessibility, setAccessibility] = useState<string>('normal');

  // Result
  const [result, setResult] = useState<CostPredictionResponse | null>(null);

  const mutation = useMutation({
    mutationFn: (data: CostPredictionRequest) => costPredictionApi.predict(data),
    onSuccess: (data) => {
      setResult(data);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail || err?.message || t('app.error') || 'An error occurred';
      toast(msg, 'error');
    },
  });

  const handleEstimate = () => {
    mutation.mutate({
      pollutant_type: pollutantType,
      material_type: materialType,
      condition,
      surface_m2: surfaceM2,
      canton,
      accessibility,
    });
  };

  // Label helpers
  const conditionLabel = (v: string) =>
    t(`cost_prediction.condition_${v}`) || v;

  const accessibilityLabel = (v: string) =>
    t(`cost_prediction.accessibility_${v}`) || v;

  const complexityLabel = (v: string) =>
    t(`cost_prediction.complexity_${v}`) || v;

  const pollutantLabel = (v: string) => {
    const key = `pollutant.${v}`;
    return t(key) || v;
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 dark:bg-black/60" onClick={onClose} />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl bg-white shadow-2xl dark:bg-slate-800 mx-4">
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-800 rounded-t-xl">
          <div className="flex items-center gap-2">
            <Calculator className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {t('cost_prediction.title') || 'Estimation des couts de remediation'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-6">
          {/* Form */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <SelectField
              label={t('cost_prediction.pollutant') || 'Type de polluant'}
              value={pollutantType}
              onChange={setPollutantType}
              options={POLLUTANT_OPTIONS}
              renderLabel={pollutantLabel}
            />
            <SelectField
              label={t('cost_prediction.material') || 'Materiau'}
              value={materialType}
              onChange={setMaterialType}
              options={MATERIAL_OPTIONS}
              renderLabel={(v) => v.replace(/_/g, ' ')}
            />
            <SelectField
              label={t('cost_prediction.condition') || 'Etat'}
              value={condition}
              onChange={setCondition}
              options={CONDITION_OPTIONS}
              renderLabel={conditionLabel}
            />
            <div>
              <label className="block">
                <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
                  {t('cost_prediction.surface') || 'Surface (m2)'}
                </span>
                <input
                  type="number"
                  min={1}
                  max={100000}
                  value={surfaceM2}
                  onChange={(e) => setSurfaceM2(Math.max(1, Number(e.target.value)))}
                  className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                />
              </label>
            </div>
            <SelectField
              label={t('cost_prediction.canton') || 'Canton'}
              value={canton}
              onChange={setCanton}
              options={CANTON_OPTIONS}
              renderLabel={(v) => v}
            />
            <SelectField
              label={t('cost_prediction.accessibility') || 'Accessibilite'}
              value={accessibility}
              onChange={setAccessibility}
              options={ACCESSIBILITY_OPTIONS}
              renderLabel={accessibilityLabel}
            />
          </div>

          {/* Estimate Button */}
          <button
            onClick={handleEstimate}
            disabled={mutation.isPending}
            className={cn(
              'w-full flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors',
              mutation.isPending
                ? 'bg-blue-400 cursor-not-allowed dark:bg-blue-500/50'
                : 'bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600',
            )}
          >
            {mutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Calculator className="w-4 h-4" />
            )}
            {t('cost_prediction.estimate') || 'Estimer le cout'}
          </button>

          {/* Results */}
          {result && (
            <div className="space-y-5 border-t border-gray-200 pt-5 dark:border-slate-700">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                {t('cost_prediction.result') || 'Estimation'}
              </h3>

              {/* Cost Range */}
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">
                  {t('cost_prediction.range') || 'Fourchette de cout'}
                </p>
                <CostRangeBar min={result.cost_min} median={result.cost_median} max={result.cost_max} />
              </div>

              {/* Duration + Complexity + Method */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="rounded-lg border border-gray-200 p-3 dark:border-slate-700">
                  <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-slate-400 mb-1">
                    <Clock className="w-3.5 h-3.5" />
                    {t('cost_prediction.duration') || 'Delai estime'}
                  </div>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">
                    {result.duration_days}{' '}
                    <span className="text-sm font-normal text-gray-500 dark:text-slate-400">
                      {t('cost_prediction.days') || 'jours'}
                    </span>
                  </p>
                </div>
                <div className="rounded-lg border border-gray-200 p-3 dark:border-slate-700">
                  <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-slate-400 mb-1">
                    <Gauge className="w-3.5 h-3.5" />
                    {t('cost_prediction.complexity') || 'Complexite'}
                  </div>
                  <span
                    className={cn(
                      'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                      COMPLEXITY_COLORS[result.complexity] ||
                        'bg-gray-100 text-gray-800 dark:bg-slate-700 dark:text-slate-300',
                    )}
                  >
                    {complexityLabel(result.complexity)}
                  </span>
                </div>
                <div className="rounded-lg border border-gray-200 p-3 dark:border-slate-700 col-span-2 sm:col-span-1">
                  <div className="text-xs text-gray-500 dark:text-slate-400 mb-1">Methode</div>
                  <p className="text-sm font-medium text-gray-800 dark:text-slate-200">{result.method}</p>
                </div>
              </div>

              {/* Coefficients */}
              <div className="flex gap-4 text-xs text-gray-500 dark:text-slate-400">
                <span>
                  Coeff. canton:{' '}
                  <span className="font-medium text-gray-700 dark:text-slate-300">
                    {result.canton_coefficient.toFixed(2)}
                  </span>
                </span>
                <span>
                  Coeff. acces:{' '}
                  <span className="font-medium text-gray-700 dark:text-slate-300">
                    {result.accessibility_coefficient.toFixed(2)}
                  </span>
                </span>
              </div>

              {/* Breakdown */}
              <BreakdownTable items={result.breakdown} t={t} />

              {/* Disclaimer */}
              <div className="flex items-start gap-2 rounded-lg bg-amber-50 p-3 dark:bg-amber-900/20">
                <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
                <p className="text-xs italic text-amber-700 dark:text-amber-300">
                  {result.disclaimer ||
                    t('cost_prediction.disclaimer') ||
                    'Estimation indicative basee sur des donnees statistiques. Ne constitue pas un devis.'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
