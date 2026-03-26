import { useTranslation } from '@/i18n';
import type { CaseStudyTemplate } from '@/api/demoPilot';
import { BookOpen, CheckCircle2, FileText } from 'lucide-react';

interface CaseStudyViewerProps {
  template: CaseStudyTemplate;
}

export function CaseStudyViewer({ template }: CaseStudyViewerProps) {
  const { t } = useTranslation();
  const narrative = template.narrative_structure;

  return (
    <div
      className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-6 space-y-5"
      data-testid="case-study-viewer"
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <BookOpen className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{template.title}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
              {template.persona_target}
            </span>
            <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full">
              {template.workflow_type}
            </span>
          </div>
        </div>
      </div>

      {/* Narrative: Before / Trigger / After */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {narrative.before && (
          <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4" data-testid="narrative-before">
            <h4 className="text-xs font-semibold text-red-700 dark:text-red-300 uppercase tracking-wider mb-2">
              {t('case_study.before')}
            </h4>
            <p className="text-sm text-red-900 dark:text-red-200">{narrative.before}</p>
          </div>
        )}
        {narrative.trigger && (
          <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4" data-testid="narrative-trigger">
            <h4 className="text-xs font-semibold text-amber-700 dark:text-amber-300 uppercase tracking-wider mb-2">
              {t('case_study.trigger')}
            </h4>
            <p className="text-sm text-amber-900 dark:text-amber-200">{narrative.trigger}</p>
          </div>
        )}
        {narrative.after && (
          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4" data-testid="narrative-after">
            <h4 className="text-xs font-semibold text-green-700 dark:text-green-300 uppercase tracking-wider mb-2">
              {t('case_study.after')}
            </h4>
            <p className="text-sm text-green-900 dark:text-green-200">{narrative.after}</p>
          </div>
        )}
      </div>

      {/* Proof Points */}
      {narrative.proof_points && narrative.proof_points.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">{t('case_study.proof_points')}</h4>
          <ul className="space-y-1.5">
            {narrative.proof_points.map((point, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-gray-700 dark:text-slate-200">
                <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Evidence Requirements */}
      {template.evidence_requirements.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
            {t('case_study.evidence_requirements')}
          </h4>
          <ul className="space-y-1.5">
            {template.evidence_requirements.map((req, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-gray-700 dark:text-slate-200">
                <FileText className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                <span>
                  <span className="font-medium">{req.label}</span>
                  {req.source && <span className="text-gray-400 dark:text-slate-500 ml-1">({req.source})</span>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default CaseStudyViewer;
