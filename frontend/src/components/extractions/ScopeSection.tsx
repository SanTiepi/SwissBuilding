import { useTranslation } from '@/i18n';
import { ClipboardList, XCircle, Plus } from 'lucide-react';
import { SectionHeader } from './shared';
import type { SectionProps } from './shared';

interface ScopeSectionProps extends SectionProps {
  onScopeListChange: (field: 'zones_covered' | 'zones_excluded', index: number, value: string) => void;
  onAddScopeItem: (field: 'zones_covered' | 'zones_excluded') => void;
  onRemoveScopeItem: (field: 'zones_covered' | 'zones_excluded', index: number) => void;
}

export function ScopeSection({ extracted, onScopeListChange, onAddScopeItem, onRemoveScopeItem }: ScopeSectionProps) {
  const { t } = useTranslation();

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
      <SectionHeader icon={ClipboardList} title={t('extraction.section_scope') || 'Perimetre'} />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        {/* Zones covered */}
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">Zones couvertes</label>
          <div className="space-y-2">
            {extracted.scope.zones_covered.map((zone, i) => (
              <div key={i} className="flex items-center gap-2">
                <input
                  type="text"
                  value={zone}
                  onChange={(e) => onScopeListChange('zones_covered', i, e.target.value)}
                  className="flex-1 px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 focus:ring-2 focus:ring-red-500 outline-none"
                />
                <button
                  onClick={() => onRemoveScopeItem('zones_covered', i)}
                  className="text-gray-400 hover:text-red-500 dark:text-slate-500 dark:hover:text-red-400"
                >
                  <XCircle className="w-4 h-4" />
                </button>
              </div>
            ))}
            <button
              onClick={() => onAddScopeItem('zones_covered')}
              className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400 hover:underline"
            >
              <Plus className="w-3 h-3" /> Ajouter
            </button>
          </div>
        </div>

        {/* Zones excluded */}
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">Zones exclues</label>
          <div className="space-y-2">
            {extracted.scope.zones_excluded.map((zone, i) => (
              <div key={i} className="flex items-center gap-2">
                <input
                  type="text"
                  value={zone}
                  onChange={(e) => onScopeListChange('zones_excluded', i, e.target.value)}
                  className="flex-1 px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 focus:ring-2 focus:ring-red-500 outline-none"
                />
                <button
                  onClick={() => onRemoveScopeItem('zones_excluded', i)}
                  className="text-gray-400 hover:text-red-500 dark:text-slate-500 dark:hover:text-red-400"
                >
                  <XCircle className="w-4 h-4" />
                </button>
              </div>
            ))}
            <button
              onClick={() => onAddScopeItem('zones_excluded')}
              className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400 hover:underline"
            >
              <Plus className="w-3 h-3" /> Ajouter
            </button>
          </div>
        </div>

        {/* Counts */}
        <div className="flex gap-6">
          <div>
            <span className="text-xs text-gray-500 dark:text-slate-400">Elements echantillonnes</span>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">{extracted.scope.elements_sampled}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500 dark:text-slate-400">Elements positifs</span>
            <p className="text-lg font-semibold text-red-600 dark:text-red-400">{extracted.scope.elements_positive}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
