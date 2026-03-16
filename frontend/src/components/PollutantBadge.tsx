import { POLLUTANT_COLORS } from '@/utils/constants';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import type { PollutantType } from '@/types';

interface PollutantBadgeProps {
  type: PollutantType;
  size?: 'sm' | 'md';
}

export function PollutantBadge({ type, size = 'md' }: PollutantBadgeProps) {
  const { t } = useTranslation();

  const color = POLLUTANT_COLORS[type] || '#6b7280';
  const label = t(`pollutant.short.${type}`);

  return (
    <span
      className={cn(
        'inline-flex items-center font-semibold rounded-full whitespace-nowrap',
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs',
      )}
      style={{
        backgroundColor: `${color}18`,
        color: color,
      }}
    >
      <span
        className={cn('rounded-full flex-shrink-0 mr-1.5', size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2')}
        style={{ backgroundColor: color }}
      />
      {label}
    </span>
  );
}
