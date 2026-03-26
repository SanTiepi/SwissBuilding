import { useState } from 'react';
import { useTranslation } from '@/i18n';
import { ChevronDown, ChevronUp, Leaf, Scale, AlertTriangle, FileText, ShieldCheck } from 'lucide-react';

const POLLUTANT_COLORS: Record<string, string> = {
  asbestos: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  pcb: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  lead: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  hap: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  radon: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
};

export interface EcoClausePreviewClause {
  clause_id: string;
  title: string;
  body: string;
  legal_references: string[];
}

export interface EcoClausePreviewSection {
  section_id: string;
  title: string;
  clauses: EcoClausePreviewClause[];
}

export interface EcoClauseSummary {
  total_clauses: number;
  detected_pollutants: string[];
  sections: EcoClausePreviewSection[];
}

interface ContractorEcoClausePreviewProps {
  ecoClauses: EcoClauseSummary;
}

export function ContractorEcoClausePreview({ ecoClauses }: ContractorEcoClausePreviewProps) {
  const { t } = useTranslation();
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  if (ecoClauses.total_clauses === 0) {
    return null;
  }

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  };

  return (
    <div
      data-testid="contractor-eco-clause-preview"
      className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-emerald-200 dark:border-emerald-900/50 p-6 space-y-4"
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <Leaf className="w-5 h-5 text-emerald-500" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('eco_clause.contractor_preview_title') || 'Environmental Safety Clauses'}
        </h3>
        <span className="text-sm text-gray-500 dark:text-slate-400">
          {ecoClauses.total_clauses} {t('eco_clause.clauses_count') || 'clause(s)'}
        </span>
      </div>

      {/* Notice banner */}
      <div className="flex items-start gap-2 p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg border border-emerald-200 dark:border-emerald-800/50">
        <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 mt-0.5 flex-shrink-0" />
        <p className="text-sm text-emerald-800 dark:text-emerald-300">
          {t('eco_clause.contractor_notice') ||
            'The following environmental clauses apply to this intervention. By acknowledging, you confirm awareness of these requirements.'}
        </p>
      </div>

      {/* Detected pollutants */}
      {(ecoClauses.detected_pollutants || []).length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
          <span className="text-sm text-gray-600 dark:text-slate-400">
            {t('eco_clause.detected_pollutants') || 'Detected pollutants'}:
          </span>
          {(ecoClauses.detected_pollutants || []).map((p) => (
            <span
              key={p}
              className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${POLLUTANT_COLORS[p] || 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300'}`}
            >
              {t(`pollutant.${p}`) || p}
            </span>
          ))}
        </div>
      )}

      {/* Sections */}
      <div className="space-y-3">
        {(ecoClauses.sections || []).map((section) => (
          <PreviewSectionCard
            key={section.section_id}
            section={section}
            isExpanded={expandedSections.has(section.section_id)}
            onToggle={() => toggleSection(section.section_id)}
            t={t}
          />
        ))}
      </div>
    </div>
  );
}

function PreviewSectionCard({
  section,
  isExpanded,
  onToggle,
  t,
}: {
  section: EcoClausePreviewSection;
  isExpanded: boolean;
  onToggle: () => void;
  t: (key: string) => string;
}) {
  return (
    <div className="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">
      {/* Section header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <span className="text-sm font-medium text-gray-900 dark:text-white">{section.title}</span>
          <span className="text-xs text-gray-500 dark:text-slate-400">
            ({(section.clauses || []).length} {t('eco_clause.clauses_count') || 'clause(s)'})
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {/* Clauses */}
      {isExpanded && (
        <div className="divide-y divide-gray-100 dark:divide-slate-700">
          {(section.clauses || []).map((clause) => (
            <div key={clause.clause_id} className="p-4 space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-gray-400 dark:text-slate-500">{clause.clause_id}</span>
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">{clause.title}</h4>
              </div>

              <p className="text-sm text-gray-700 dark:text-slate-300 leading-relaxed">{clause.body}</p>

              {/* Legal references */}
              {(clause.legal_references || []).length > 0 && (
                <div className="flex items-center gap-2 flex-wrap">
                  <FileText className="w-3.5 h-3.5 text-blue-500 flex-shrink-0" />
                  {(clause.legal_references || []).map((ref, i) => (
                    <span
                      key={i}
                      className="inline-block px-2 py-0.5 text-xs rounded bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400"
                    >
                      {ref}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
