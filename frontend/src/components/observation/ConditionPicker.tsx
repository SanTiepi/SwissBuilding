import { memo } from 'react';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import type { ConditionAssessment } from '@/types';

const CONDITIONS: { value: ConditionAssessment; grade: string; color: string; darkColor: string }[] = [
  {
    value: 'good',
    grade: 'A',
    color: 'border-green-500 bg-green-50 text-green-700',
    darkColor: 'dark:border-green-400 dark:bg-green-900/30 dark:text-green-300',
  },
  {
    value: 'fair',
    grade: 'B',
    color: 'border-yellow-500 bg-yellow-50 text-yellow-700',
    darkColor: 'dark:border-yellow-400 dark:bg-yellow-900/30 dark:text-yellow-300',
  },
  {
    value: 'poor',
    grade: 'C',
    color: 'border-orange-500 bg-orange-50 text-orange-700',
    darkColor: 'dark:border-orange-400 dark:bg-orange-900/30 dark:text-orange-300',
  },
  {
    value: 'critical',
    grade: 'D',
    color: 'border-red-500 bg-red-50 text-red-700',
    darkColor: 'dark:border-red-400 dark:bg-red-900/30 dark:text-red-300',
  },
];

interface ConditionPickerProps {
  value: ConditionAssessment | '';
  onChange: (condition: ConditionAssessment) => void;
}

export const ConditionPicker = memo(function ConditionPicker({ value, onChange }: ConditionPickerProps) {
  const { t } = useTranslation();

  return (
    <div data-testid="condition-picker">
      <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
        {t('observation.condition_assessment') || 'Condition'}
      </label>
      <div className="grid grid-cols-4 gap-2">
        {CONDITIONS.map((c) => (
          <button
            key={c.value}
            type="button"
            data-testid={`condition-${c.value}`}
            onClick={() => onChange(c.value)}
            className={cn(
              'flex flex-col items-center gap-1 rounded-xl border-2 p-4 transition-all',
              'min-h-[80px] touch-manipulation active:scale-95',
              value === c.value
                ? `${c.color} ${c.darkColor} border-2`
                : 'border-gray-200 bg-white text-gray-600 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400',
            )}
          >
            <span className="text-2xl font-bold">{c.grade}</span>
            <span className="text-xs font-medium">{t(`observation.condition_${c.value}`) || c.value}</span>
          </button>
        ))}
      </div>
    </div>
  );
});
