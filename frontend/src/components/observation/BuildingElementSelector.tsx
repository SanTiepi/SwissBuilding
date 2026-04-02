import { memo } from 'react';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';

const BUILDING_ELEMENTS = [
  { id: 'roof', icon: '🏠', labelKey: 'observation.element_roof' },
  { id: 'facade', icon: '🧱', labelKey: 'observation.element_facade' },
  { id: 'walls', icon: '🪨', labelKey: 'observation.element_walls' },
  { id: 'basement', icon: '⬇️', labelKey: 'observation.element_basement' },
  { id: 'floor', icon: '🔲', labelKey: 'observation.element_floor' },
  { id: 'ceiling', icon: '⬆️', labelKey: 'observation.element_ceiling' },
  { id: 'pipe', icon: '🔧', labelKey: 'observation.element_pipe' },
  { id: 'insulation', icon: '🧤', labelKey: 'observation.element_insulation' },
  { id: 'window', icon: '🪟', labelKey: 'observation.element_window' },
  { id: 'door', icon: '🚪', labelKey: 'observation.element_door' },
  { id: 'staircase', icon: '🪜', labelKey: 'observation.element_staircase' },
  { id: 'other', icon: '📋', labelKey: 'observation.element_other' },
] as const;

interface BuildingElementSelectorProps {
  value: string;
  onChange: (elementId: string) => void;
}

export const BuildingElementSelector = memo(function BuildingElementSelector({
  value,
  onChange,
}: BuildingElementSelectorProps) {
  const { t } = useTranslation();

  return (
    <div data-testid="building-element-selector">
      <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
        {t('observation.building_element') || 'Building element'}
      </label>
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {BUILDING_ELEMENTS.map((el) => (
          <button
            key={el.id}
            type="button"
            data-testid={`element-${el.id}`}
            onClick={() => onChange(el.id)}
            className={cn(
              'flex flex-col items-center gap-1 rounded-xl border-2 p-3 text-center transition-all',
              'min-h-[72px] touch-manipulation',
              value === el.id
                ? 'border-indigo-500 bg-indigo-50 text-indigo-700 dark:border-indigo-400 dark:bg-indigo-900/30 dark:text-indigo-300'
                : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300',
            )}
          >
            <span className="text-2xl" role="img" aria-label={el.id}>
              {el.icon}
            </span>
            <span className="text-xs font-medium leading-tight">{t(el.labelKey) || el.id}</span>
          </button>
        ))}
      </div>
    </div>
  );
});
