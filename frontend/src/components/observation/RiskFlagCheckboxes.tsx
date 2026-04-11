import { memo } from 'react';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import type { RiskFlag } from '@/types';

const RISK_FLAGS: { value: RiskFlag; icon: string; labelKey: string }[] = [
  { value: 'water_stain', icon: '💧', labelKey: 'observation.flag_water_stain' },
  { value: 'crack', icon: '⚡', labelKey: 'observation.flag_crack' },
  { value: 'mold', icon: '🟢', labelKey: 'observation.flag_mold' },
  { value: 'rust', icon: '🟤', labelKey: 'observation.flag_rust' },
  { value: 'deformation', icon: '〰️', labelKey: 'observation.flag_deformation' },
];

interface RiskFlagCheckboxesProps {
  value: RiskFlag[];
  onChange: (flags: RiskFlag[]) => void;
}

export const RiskFlagCheckboxes = memo(function RiskFlagCheckboxes({
  value,
  onChange,
}: RiskFlagCheckboxesProps) {
  const { t } = useTranslation();

  const toggle = (flag: RiskFlag) => {
    if (value.includes(flag)) {
      onChange(value.filter((f) => f !== flag));
    } else {
      onChange([...value, flag]);
    }
  };

  return (
    <div data-testid="risk-flag-checkboxes">
      <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
        {t('observation.risk_flags') || 'Risk flags'}
      </label>
      <div className="flex flex-wrap gap-2">
        {RISK_FLAGS.map((flag) => {
          const active = value.includes(flag.value);
          return (
            <button
              key={flag.value}
              type="button"
              data-testid={`flag-${flag.value}`}
              onClick={() => toggle(flag.value)}
              className={cn(
                'inline-flex items-center gap-2 rounded-xl border-2 px-4 py-3 text-sm font-medium transition-all',
                'touch-manipulation active:scale-95',
                active
                  ? 'border-red-400 bg-red-50 text-red-700 dark:border-red-500 dark:bg-red-900/30 dark:text-red-300'
                  : 'border-gray-200 bg-white text-gray-600 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-400',
              )}
            >
              <span role="img" aria-label={flag.value}>
                {flag.icon}
              </span>
              <span>{t(flag.labelKey) || flag.value}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
});
