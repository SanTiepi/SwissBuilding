import { cn } from '@/utils/formatters';
import { Footprints, Bike, Car } from 'lucide-react';

export type IsochroneProfile = 'walking' | 'cycling' | 'driving';

interface IsochroneControlsProps {
  profile: IsochroneProfile;
  onProfileChange: (p: IsochroneProfile) => void;
  visibleMinutes: Set<number>;
  onToggleMinutes: (m: number) => void;
}

const PROFILES: { key: IsochroneProfile; icon: typeof Footprints; label: string }[] = [
  { key: 'walking', icon: Footprints, label: 'A pied' },
  { key: 'cycling', icon: Bike, label: 'Vélo' },
  { key: 'driving', icon: Car, label: 'Voiture' },
];

const CONTOURS: { minutes: number; color: string; label: string }[] = [
  { minutes: 5, color: 'bg-green-500', label: '5 min' },
  { minutes: 10, color: 'bg-amber-500', label: '10 min' },
  { minutes: 15, color: 'bg-red-500', label: '15 min' },
];

export function IsochroneControls({ profile, onProfileChange, visibleMinutes, onToggleMinutes }: IsochroneControlsProps) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      {/* Profile selector */}
      <div className="flex rounded-lg border border-gray-200 dark:border-slate-700 overflow-hidden">
        {PROFILES.map(({ key, icon: Icon, label }) => (
          <button
            key={key}
            onClick={() => onProfileChange(key)}
            title={label}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 text-sm transition-colors',
              profile === key
                ? 'bg-blue-600 text-white'
                : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-700',
            )}
          >
            <Icon className="w-4 h-4" />
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      {/* Contour toggles */}
      <div className="flex items-center gap-2">
        {CONTOURS.map(({ minutes, color, label }) => (
          <button
            key={minutes}
            onClick={() => onToggleMinutes(minutes)}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-opacity',
              visibleMinutes.has(minutes) ? 'opacity-100' : 'opacity-40',
            )}
          >
            <span className={cn('w-2.5 h-2.5 rounded-full', color)} />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
