import { useTranslation } from '@/i18n';
import { DiagnosticTimeline } from '@/components/DiagnosticTimeline';
import { RoleGate } from '@/components/RoleGate';
import type { Diagnostic } from '@/types';
import { Plus } from 'lucide-react';

interface DiagnosticsTabProps {
  diagnostics: Diagnostic[];
  onCreateClick: () => void;
}

export function DiagnosticsTab({ diagnostics, onCreateClick }: DiagnosticsTabProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200">
          {t('building.diagnosticsCount', { count: diagnostics.length })}
        </h3>
        <RoleGate allowedRoles={['admin', 'diagnostician']}>
          <button
            onClick={onCreateClick}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
          >
            <Plus className="w-4 h-4" />
            {t('diagnostic.create')}
          </button>
        </RoleGate>
      </div>
      {diagnostics.length > 0 ? (
        <DiagnosticTimeline diagnostics={diagnostics} />
      ) : (
        <p className="text-center text-sm text-gray-500 dark:text-slate-400 py-8">{t('building.noDiagnostics')}</p>
      )}
    </div>
  );
}

export default DiagnosticsTab;
