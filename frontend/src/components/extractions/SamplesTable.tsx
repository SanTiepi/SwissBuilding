import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { Beaker, Plus } from 'lucide-react';
import { ConfidenceIndicator } from '@/components/ConfidenceIndicator';
import { SectionHeader, resultBadge, SAMPLE_RESULTS } from './shared';
import type { ExtractedData, ExtractedSample } from '@/api/extractions';

interface SamplesTableProps {
  extracted: ExtractedData;
  onSampleChange: (index: number, field: keyof ExtractedSample, newValue: unknown) => void;
  onAddSample: () => void;
  canEdit: boolean;
}

export function SamplesTable({ extracted, onSampleChange, onAddSample, canEdit }: SamplesTableProps) {
  const { t } = useTranslation();

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
      <SectionHeader icon={Beaker} title={t('extraction.section_samples') || 'Echantillons'} />
      {extracted.samples.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-slate-700">
                <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">ID</th>
                <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                  Localisation
                </th>
                <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">Materiau</th>
                <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">Resultat</th>
                <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                  Concentration
                </th>
                <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">Unite</th>
                <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                  Seuil depasse
                </th>
                <th className="text-center py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                  Confiance
                </th>
              </tr>
            </thead>
            <tbody>
              {extracted.samples.map((sample, idx) => {
                const rb = resultBadge(sample.result);
                return (
                  <tr
                    key={idx}
                    className="border-b border-gray-100 dark:border-slate-700/50 hover:bg-gray-50 dark:hover:bg-slate-700/30"
                  >
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={sample.sample_id}
                        onChange={(e) => onSampleChange(idx, 'sample_id', e.target.value)}
                        className="w-24 px-2 py-1 text-xs rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:ring-1 focus:ring-red-500"
                      />
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={sample.location ?? ''}
                        onChange={(e) => onSampleChange(idx, 'location', e.target.value || null)}
                        className="w-32 px-2 py-1 text-xs rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:ring-1 focus:ring-red-500"
                        placeholder="-"
                      />
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={sample.material_type ?? ''}
                        onChange={(e) => onSampleChange(idx, 'material_type', e.target.value || null)}
                        className="w-32 px-2 py-1 text-xs rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:ring-1 focus:ring-red-500"
                        placeholder="-"
                      />
                    </td>
                    <td className="py-2 px-2">
                      <select
                        value={sample.result}
                        onChange={(e) => onSampleChange(idx, 'result', e.target.value)}
                        className={cn(
                          'px-2 py-1 text-xs rounded font-medium border-0 outline-none focus:ring-1 focus:ring-red-500',
                          rb.className,
                        )}
                      >
                        {SAMPLE_RESULTS.map((r) => (
                          <option key={r.value} value={r.value}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="number"
                        step="any"
                        value={sample.concentration ?? ''}
                        onChange={(e) =>
                          onSampleChange(idx, 'concentration', e.target.value ? parseFloat(e.target.value) : null)
                        }
                        className="w-24 px-2 py-1 text-xs rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:ring-1 focus:ring-red-500"
                        placeholder="-"
                      />
                    </td>
                    <td className="py-2 px-2">
                      <input
                        type="text"
                        value={sample.unit ?? ''}
                        onChange={(e) => onSampleChange(idx, 'unit', e.target.value || null)}
                        className="w-20 px-2 py-1 text-xs rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:ring-1 focus:ring-red-500"
                        placeholder="-"
                      />
                    </td>
                    <td className="py-2 px-2 text-center">
                      <select
                        value={sample.threshold_exceeded === null ? '' : sample.threshold_exceeded ? 'true' : 'false'}
                        onChange={(e) =>
                          onSampleChange(
                            idx,
                            'threshold_exceeded',
                            e.target.value === '' ? null : e.target.value === 'true',
                          )
                        }
                        className="px-2 py-1 text-xs rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:ring-1 focus:ring-red-500"
                      >
                        <option value="">-</option>
                        <option value="true">Oui</option>
                        <option value="false">Non</option>
                      </select>
                    </td>
                    <td className="py-2 px-2 text-center">
                      <div className="flex items-center justify-center">
                        <ConfidenceIndicator value={sample.confidence} size="sm" showValue />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-gray-500 dark:text-slate-400 text-center py-4">Aucun echantillon extrait</p>
      )}
      {canEdit && (
        <button
          onClick={onAddSample}
          className="mt-3 flex items-center gap-1 text-sm text-red-600 dark:text-red-400 hover:underline"
        >
          <Plus className="w-4 h-4" /> Ajouter un echantillon
        </button>
      )}
    </div>
  );
}
