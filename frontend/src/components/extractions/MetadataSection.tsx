import { useTranslation } from '@/i18n';
import { FileText } from 'lucide-react';
import { SectionHeader, EditableSelect, EditableText, EditableDate, REPORT_TYPES } from './shared';
import type { SectionProps } from './shared';

export function MetadataSection({ extracted, original, onFieldChange }: SectionProps) {
  const { t } = useTranslation();

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
      <SectionHeader icon={FileText} title={t('extraction.section_metadata') || 'Metadonnees du rapport'} />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Type de rapport</label>
          <EditableSelect
            value={extracted.report_type}
            originalValue={original?.report_type ?? null}
            options={REPORT_TYPES}
            onChange={(v) => onFieldChange('report_type', v)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Laboratoire</label>
          <EditableText
            value={extracted.lab_name}
            originalValue={original?.lab_name ?? null}
            onChange={(v) => onFieldChange('lab_name', v)}
            placeholder="Nom du laboratoire"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Reference</label>
          <EditableText
            value={extracted.lab_reference}
            originalValue={original?.lab_reference ?? null}
            onChange={(v) => onFieldChange('lab_reference', v)}
            placeholder="Numero de reference"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Date du rapport</label>
          <EditableDate
            value={extracted.report_date}
            originalValue={original?.report_date ?? null}
            onChange={(v) => onFieldChange('report_date', v)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Date de validite</label>
          <EditableDate
            value={extracted.validity_date}
            originalValue={original?.validity_date ?? null}
            onChange={(v) => onFieldChange('validity_date', v)}
          />
        </div>
      </div>
    </div>
  );
}
