import { cn } from '@/utils/formatters';

// ---------------------------------------------------------------------------
// Badge helpers
// ---------------------------------------------------------------------------

export function statusBadge(status: string): { className: string; label: string } {
  switch (status) {
    case 'draft':
      return {
        className: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
        label: 'Brouillon',
      };
    case 'reviewed':
      return {
        className: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
        label: 'Revu',
      };
    case 'applied':
      return {
        className: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
        label: 'Applique',
      };
    case 'rejected':
      return {
        className: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
        label: 'Rejete',
      };
    default:
      return {
        className: 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300',
        label: status,
      };
  }
}

export function resultBadge(result: string): { className: string; label: string } {
  switch (result) {
    case 'positive':
      return { className: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300', label: 'Positif' };
    case 'negative':
      return { className: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300', label: 'Negatif' };
    case 'trace':
      return { className: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300', label: 'Trace' };
    default:
      return { className: 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300', label: 'Non teste' };
  }
}

// ---------------------------------------------------------------------------
// Option lists
// ---------------------------------------------------------------------------

export const REPORT_TYPES = [
  { value: 'asbestos', label: 'Amiante' },
  { value: 'pcb', label: 'PCB' },
  { value: 'lead', label: 'Plomb' },
  { value: 'hap', label: 'HAP' },
  { value: 'radon', label: 'Radon' },
  { value: 'pfas', label: 'PFAS' },
  { value: 'multi', label: 'Multi-polluants' },
  { value: 'unknown', label: 'Inconnu' },
];

export const OVERALL_RESULTS = [
  { value: 'presence', label: 'Presence' },
  { value: 'absence', label: 'Absence' },
  { value: 'partial', label: 'Partiel' },
];

export const RISK_LEVELS = [
  { value: 'low', label: 'Faible' },
  { value: 'medium', label: 'Moyen' },
  { value: 'high', label: 'Eleve' },
  { value: 'critical', label: 'Critique' },
  { value: 'unknown', label: 'Inconnu' },
];

export const WORK_CATEGORIES = [
  { value: '', label: 'Non defini' },
  { value: 'minor', label: 'Mineurs' },
  { value: 'medium', label: 'Moyens' },
  { value: 'major', label: 'Majeurs' },
];

export const SAMPLE_RESULTS = [
  { value: 'positive', label: 'Positif' },
  { value: 'negative', label: 'Negatif' },
  { value: 'trace', label: 'Trace' },
  { value: 'not_tested', label: 'Non teste' },
];

// ---------------------------------------------------------------------------
// Editable field components
// ---------------------------------------------------------------------------

interface EditableTextProps {
  value: string | null;
  originalValue: string | null;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}

export function EditableText({ value, originalValue, onChange, placeholder, className }: EditableTextProps) {
  const isModified = value !== originalValue;
  return (
    <div className="relative">
      <input
        type="text"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={cn(
          'w-full px-3 py-2 text-sm rounded-lg border transition-colors',
          'bg-white dark:bg-slate-900 border-gray-200 dark:border-slate-600',
          'focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none',
          isModified && 'border-amber-400 dark:border-amber-500 ring-1 ring-amber-200 dark:ring-amber-800',
          className,
        )}
      />
      {isModified && originalValue != null && (
        <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5 line-through">{originalValue}</p>
      )}
    </div>
  );
}

interface EditableSelectProps {
  value: string | null;
  originalValue: string | null;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  className?: string;
}

export function EditableSelect({ value, originalValue, options, onChange, className }: EditableSelectProps) {
  const isModified = value !== originalValue;
  return (
    <div className="relative">
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          'w-full px-3 py-2 text-sm rounded-lg border transition-colors',
          'bg-white dark:bg-slate-900 border-gray-200 dark:border-slate-600',
          'focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none',
          isModified && 'border-amber-400 dark:border-amber-500 ring-1 ring-amber-200 dark:ring-amber-800',
          className,
        )}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {isModified && originalValue != null && (
        <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5 line-through">
          {options.find((o) => o.value === originalValue)?.label ?? originalValue}
        </p>
      )}
    </div>
  );
}

interface EditableDateProps {
  value: string | null;
  originalValue: string | null;
  onChange: (v: string) => void;
  className?: string;
}

export function EditableDate({ value, originalValue, onChange, className }: EditableDateProps) {
  const isModified = value !== originalValue;
  return (
    <div className="relative">
      <input
        type="date"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          'w-full px-3 py-2 text-sm rounded-lg border transition-colors',
          'bg-white dark:bg-slate-900 border-gray-200 dark:border-slate-600',
          'focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none',
          isModified && 'border-amber-400 dark:border-amber-500 ring-1 ring-amber-200 dark:ring-amber-800',
          className,
        )}
      />
      {isModified && originalValue != null && (
        <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5 line-through">{originalValue}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section header
// ---------------------------------------------------------------------------

export function SectionHeader({ icon: Icon, title }: { icon: React.ElementType; title: string }) {
  return (
    <h3 className="flex items-center gap-2 text-base font-semibold text-gray-800 dark:text-slate-100 mb-4">
      <Icon className="w-5 h-5 text-red-500" />
      {title}
    </h3>
  );
}

// ---------------------------------------------------------------------------
// Shared section props
// ---------------------------------------------------------------------------

export interface SectionProps {
  extracted: import('@/api/extractions').ExtractedData;
  original: import('@/api/extractions').ExtractedData | null;
  onFieldChange: (fieldPath: string, newValue: unknown) => void;
}
