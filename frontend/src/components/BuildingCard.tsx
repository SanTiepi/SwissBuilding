import { memo, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Home, Factory, Landmark, Store, Layers, MapPin, Calendar, Clock } from 'lucide-react';
import { useTranslation } from '@/i18n';
// formatters not needed here
import { RISK_COLORS } from '@/utils/constants';
import type { Building, RiskLevel } from '@/types';

function getFreshnessColor(updatedAt: string): string {
  const diffDays = Math.floor((Date.now() - new Date(updatedAt).getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays <= 7) return 'text-green-600 dark:text-green-400';
  if (diffDays <= 30) return 'text-yellow-600 dark:text-yellow-400';
  if (diffDays <= 90) return 'text-orange-600 dark:text-orange-400';
  return 'text-red-600 dark:text-red-400';
}

interface BuildingCardProps {
  building: Building;
  onClick?: () => void;
}

const typeIcons: Record<string, React.ElementType> = {
  residential: Home,
  commercial: Store,
  industrial: Factory,
  public: Landmark,
  mixed: Layers,
};

const riskLabels: Record<RiskLevel, string> = {
  low: 'risk.low',
  medium: 'risk.medium',
  high: 'risk.high',
  critical: 'risk.critical',
  unknown: 'risk.unknown',
};

export const BuildingCard = memo(function BuildingCard({ building, onClick }: BuildingCardProps) {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const TypeIcon = typeIcons[building.building_type] || Building2;
  const riskLevel = building.risk_scores?.overall_risk_level || 'unknown';
  const riskColor = RISK_COLORS[riskLevel] || RISK_COLORS.unknown;
  const freshnessColor = useMemo(
    () => (building.updated_at ? getFreshnessColor(building.updated_at) : ''),
    [building.updated_at],
  );

  function handleClick() {
    if (onClick) {
      onClick();
    } else {
      navigate(`/buildings/${building.id}`);
    }
  }

  return (
    <div
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleClick();
        }
      }}
      role="article"
      tabIndex={0}
      aria-label={`${t(`building_type.${building.building_type}`)} - ${building.address}, ${building.postal_code} ${building.city}`}
      className="group bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 cursor-pointer hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600 transition-all duration-200"
    >
      {/* Top row: type icon + risk badge */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 flex items-center justify-center group-hover:bg-slate-200 dark:group-hover:bg-slate-600 transition-colors">
            <TypeIcon className="w-5 h-5" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-900 dark:text-white leading-tight">
              {t(`building_type.${building.building_type}`)}
            </p>
            <span className="inline-flex items-center mt-0.5 px-2 py-0.5 rounded text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
              {building.canton}
            </span>
          </div>
        </div>

        {/* Risk indicator */}
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: riskColor }} />
          <span className="text-xs font-semibold" style={{ color: riskColor }}>
            {t(riskLabels[riskLevel])}
          </span>
        </div>
      </div>

      {/* Address */}
      <div className="mb-3">
        <div className="flex items-start gap-1.5 text-slate-700 dark:text-slate-200">
          <MapPin className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-slate-400 dark:text-slate-500" />
          <div>
            <p className="text-sm font-medium leading-snug">{building.address}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {building.postal_code} {building.city}
            </p>
          </div>
        </div>
      </div>

      {/* Bottom row: construction year + freshness */}
      <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-700">
        {building.construction_year ? (
          <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
            <Calendar className="w-3.5 h-3.5" />
            <span>{building.construction_year}</span>
          </div>
        ) : (
          <span className="text-xs text-slate-500 dark:text-slate-400">--</span>
        )}

        {building.updated_at ? (
          <div
            className={`flex items-center gap-1 text-xs ${freshnessColor}`}
            title={t('building.data_freshness') || 'Last updated'}
          >
            <Clock className="w-3 h-3" />
            <span>
              {new Date(building.updated_at).toLocaleDateString('fr-CH', {
                day: '2-digit',
                month: '2-digit',
                year: '2-digit',
              })}
            </span>
          </div>
        ) : (
          building.surface_area_m2 && (
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {building.surface_area_m2.toLocaleString('de-CH')} m&sup2;
            </span>
          )
        )}
      </div>
    </div>
  );
});
