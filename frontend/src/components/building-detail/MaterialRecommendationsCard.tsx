import { useState } from 'react';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { ChevronDown, ChevronRight, FlaskConical, AlertTriangle, FileCheck, Shield } from 'lucide-react';

export interface EvidenceRequirement {
  document_type: string;
  description: string;
  mandatory: boolean;
  legal_ref?: string | null;
}

export interface MaterialRecommendation {
  original_material_type: string;
  original_pollutant: string;
  recommended_material: string;
  recommended_material_type: string;
  reason: string;
  risk_level: string;
  evidence_requirements: EvidenceRequirement[];
  risk_flags: string[];
}

const RISK_STYLES: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  unknown: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
};

const RISK_BORDER: Record<string, string> = {
  critical: 'border-red-200 dark:border-red-900/50',
  high: 'border-orange-200 dark:border-orange-900/50',
  medium: 'border-yellow-200 dark:border-yellow-900/50',
  low: 'border-green-200 dark:border-green-900/50',
  unknown: 'border-gray-200 dark:border-gray-700',
};

interface MaterialRecommendationsCardProps {
  recommendations: MaterialRecommendation[];
}

export function MaterialRecommendationsCard({ recommendations }: MaterialRecommendationsCardProps) {
  const { t } = useTranslation();
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6">
        <div className="flex items-center gap-2 mb-3">
          <FlaskConical className="w-5 h-5 text-indigo-500" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('material_rec.title') || 'Material Recommendations'}
          </h2>
        </div>
        <p className="text-sm text-gray-500 dark:text-slate-400">
          {t('material_rec.empty') || 'No material recommendations available.'}
        </p>
      </div>
    );
  }

  const toggleExpand = (index: number) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6 space-y-4">
      <div className="flex items-center gap-2">
        <FlaskConical className="w-5 h-5 text-indigo-500" />
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('material_rec.title') || 'Material Recommendations'}
        </h2>
        <span className="ml-auto text-sm text-gray-500 dark:text-slate-400">
          {recommendations.length} {t('material_rec.count') || 'recommendation(s)'}
        </span>
      </div>

      <div className="space-y-3">
        {recommendations.map((rec, i) => {
          const isExpanded = expandedIndex === i;
          const riskStyle = RISK_STYLES[rec.risk_level] || RISK_STYLES.unknown;
          const borderStyle = RISK_BORDER[rec.risk_level] || RISK_BORDER.unknown;

          return (
            <div
              key={`${rec.original_material_type}-${rec.original_pollutant}-${i}`}
              className={cn('rounded-lg border', borderStyle, 'bg-gray-50 dark:bg-slate-700/30')}
            >
              <button
                type="button"
                onClick={() => toggleExpand(i)}
                className="w-full flex items-start gap-3 p-3 text-left"
                aria-expanded={isExpanded}
              >
                <div className="flex-shrink-0 mt-0.5 text-gray-400 dark:text-slate-500">
                  {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={cn('inline-block px-2 py-0.5 text-xs font-medium rounded-full', riskStyle)}>
                      {rec.risk_level}
                    </span>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {rec.original_material_type}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-slate-400">({rec.original_pollutant})</span>
                  </div>
                  <p className="mt-1 text-sm text-gray-700 dark:text-slate-300">
                    <span className="font-medium">{t('material_rec.suggested') || 'Suggested'}:</span>{' '}
                    {rec.recommended_material}
                  </p>
                </div>
              </button>

              {isExpanded && (
                <div className="px-3 pb-3 pl-10 space-y-3">
                  {/* Reason */}
                  <div>
                    <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      {t('material_rec.reason') || 'Reason'}
                    </p>
                    <p className="text-sm text-gray-700 dark:text-slate-300">{rec.reason}</p>
                  </div>

                  {/* Replacement type */}
                  <div>
                    <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                      {t('material_rec.replacement_type') || 'Replacement Type'}
                    </p>
                    <p className="text-sm text-gray-700 dark:text-slate-300">{rec.recommended_material_type}</p>
                  </div>

                  {/* Risk flags */}
                  {(rec.risk_flags || []).length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                        <AlertTriangle className="w-3 h-3 inline mr-1" />
                        {t('material_rec.risk_flags') || 'Risk Flags'}
                      </p>
                      <ul className="space-y-1">
                        {(rec.risk_flags || []).map((flag, fi) => (
                          <li key={fi} className="text-sm text-amber-700 dark:text-amber-400 flex items-start gap-1.5">
                            <Shield className="w-3 h-3 mt-0.5 flex-shrink-0" />
                            {flag}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Evidence requirements */}
                  {(rec.evidence_requirements || []).length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                        <FileCheck className="w-3 h-3 inline mr-1" />
                        {t('material_rec.evidence_requirements') || 'Evidence Requirements'}
                      </p>
                      <ul className="space-y-1.5">
                        {(rec.evidence_requirements || []).map((ev, ei) => (
                          <li key={ei} className="text-sm text-gray-700 dark:text-slate-300 flex items-start gap-2">
                            <span
                              className={cn(
                                'mt-0.5 flex-shrink-0 w-2 h-2 rounded-full',
                                ev.mandatory ? 'bg-red-400 dark:bg-red-500' : 'bg-gray-300 dark:bg-slate-500',
                              )}
                            />
                            <div>
                              <span className="font-medium">{ev.document_type}</span>
                              {' — '}
                              {ev.description}
                              {ev.legal_ref && (
                                <span className="ml-1 text-xs text-gray-400 dark:text-slate-500">[{ev.legal_ref}]</span>
                              )}
                              {ev.mandatory && (
                                <span className="ml-1 text-xs text-red-500 dark:text-red-400">
                                  ({t('material_rec.mandatory') || 'mandatory'})
                                </span>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
