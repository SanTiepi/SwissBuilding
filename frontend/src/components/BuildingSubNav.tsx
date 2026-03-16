import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  Layers,
  Wrench,
  FileImage,
  Clock,
  ShieldCheck,
  BarChart3,
  Beaker,
  ClipboardList,
  FlaskConical,
} from 'lucide-react';

interface BuildingSubNavProps {
  buildingId: string;
}

const NAV_ITEMS = [
  { key: 'explorer', path: 'explorer', icon: Layers, labelKey: 'building.sub_nav.explorer' },
  {
    key: 'interventions',
    path: 'interventions',
    icon: Wrench,
    labelKey: 'building.sub_nav.interventions',
  },
  { key: 'plans', path: 'plans', icon: FileImage, labelKey: 'building.sub_nav.plans' },
  { key: 'timeline', path: 'timeline', icon: Clock, labelKey: 'building.sub_nav.timeline' },
  {
    key: 'readiness',
    path: 'readiness',
    icon: ShieldCheck,
    labelKey: 'building.sub_nav.readiness',
  },
  { key: 'safe-to-x', path: 'safe-to-x', icon: BarChart3, labelKey: 'building.sub_nav.safe_to_x' },
  { key: 'simulator', path: 'simulator', icon: Beaker, labelKey: 'building.sub_nav.simulator' },
  {
    key: 'samples',
    path: 'samples',
    icon: FlaskConical,
    labelKey: 'building.sub_nav.samples',
  },
  {
    key: 'field-observations',
    path: 'field-observations',
    icon: ClipboardList,
    labelKey: 'building.sub_nav.field_observations',
  },
] as const;

export function BuildingSubNav({ buildingId }: BuildingSubNavProps) {
  const { t } = useTranslation();
  const location = useLocation();

  return (
    <nav className="flex gap-1.5 overflow-x-auto pb-1 flex-wrap">
      {NAV_ITEMS.map((item) => {
        const href = `/buildings/${buildingId}/${item.path}`;
        const isActive = location.pathname === href || location.pathname.startsWith(href + '/');
        const Icon = item.icon;

        return (
          <Link
            key={item.key}
            to={href}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors',
              isActive
                ? 'bg-red-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600',
            )}
          >
            <Icon className="w-3.5 h-3.5" />
            {t(item.labelKey)}
          </Link>
        );
      })}
    </nav>
  );
}
