import { useTranslation } from '@/i18n';
import { Scale } from 'lucide-react';
import { SectionHeader, EditableText, EditableSelect, WORK_CATEGORIES } from './shared';
import type { SectionProps } from './shared';

export function RegulatorySection({ extracted, original, onFieldChange }: SectionProps) {
  const { t } = useTranslation();

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
      <SectionHeader icon={Scale} title={t('extraction.section_regulatory') || 'Contexte reglementaire'} />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
            Reference reglementaire
          </label>
          <EditableText
            value={extracted.regulatory_context.regulation_ref}
            originalValue={original?.regulatory_context.regulation_ref ?? null}
            onChange={(v) => onFieldChange('regulatory_context.regulation_ref', v)}
            placeholder="Ex: OTConst Art. 60a"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Seuil applique</label>
          <EditableText
            value={extracted.regulatory_context.threshold_applied}
            originalValue={original?.regulatory_context.threshold_applied ?? null}
            onChange={(v) => onFieldChange('regulatory_context.threshold_applied', v)}
            placeholder="Ex: 50.0 mg/kg"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
            Categorie de travaux
          </label>
          <EditableSelect
            value={extracted.regulatory_context.work_category ?? ''}
            originalValue={original?.regulatory_context.work_category ?? ''}
            options={WORK_CATEGORIES}
            onChange={(v) => onFieldChange('regulatory_context.work_category', v || null)}
          />
        </div>
      </div>
    </div>
  );
}
