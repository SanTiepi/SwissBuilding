import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { CheckCircle2, FileText, AlertCircle } from 'lucide-react';

export interface ProofRequirement {
  label: string;
  document_id: string | null; // null = missing
}

interface AuthorityProofSetProps {
  requirements: ProofRequirement[];
  stepName: string;
}

export default function AuthorityProofSet({ requirements, stepName }: AuthorityProofSetProps) {
  const { t } = useTranslation();

  const linked = requirements.filter((r) => r.document_id !== null);
  const missing = requirements.filter((r) => r.document_id === null);
  const allLinked = missing.length === 0 && requirements.length > 0;

  return (
    <div
      className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-4"
      data-testid="authority-proof-set"
    >
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <FileText className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          {t('authority_room.required_proofs')}
        </h4>
        <span
          className={cn(
            'text-xs font-medium px-2 py-0.5 rounded-full',
            allLinked
              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
              : 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
          )}
          data-testid="proof-set-count"
        >
          {linked.length}/{requirements.length}
        </span>
      </div>

      <p className="text-xs text-gray-500 dark:text-slate-400 mb-3">
        {t('authority_room.proof_set_step_label')}: <span className="font-medium text-gray-700 dark:text-slate-300">{stepName}</span>
      </p>

      {requirements.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-slate-500 text-center py-4" data-testid="proof-set-empty">
          {t('authority_room.no_proofs_required')}
        </p>
      ) : (
        <ul className="space-y-2" data-testid="proof-set-list">
          {requirements.map((req, idx) => {
            const isLinked = req.document_id !== null;
            return (
              <li
                key={idx}
                className={cn(
                  'flex items-center gap-2 px-3 py-2 rounded-lg text-sm',
                  isLinked
                    ? 'bg-green-50 dark:bg-green-900/10 text-green-800 dark:text-green-300'
                    : 'bg-gray-50 dark:bg-slate-700/50 text-gray-600 dark:text-slate-400',
                )}
                data-testid={`proof-item-${idx}`}
              >
                {isLinked ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500 dark:text-green-400 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-orange-400 dark:text-orange-500 flex-shrink-0" />
                )}
                <span className="flex-1">{req.label}</span>
                {isLinked && (
                  <span className="text-xs text-green-600 dark:text-green-400 font-medium">
                    {t('authority_room.linked')}
                  </span>
                )}
                {!isLinked && (
                  <span className="text-xs text-orange-600 dark:text-orange-400 font-medium">
                    {t('authority_room.missing')}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {missing.length > 0 && (
        <div className="mt-3 p-2 bg-orange-50 dark:bg-orange-900/10 border border-orange-200 dark:border-orange-800 rounded-lg text-xs text-orange-700 dark:text-orange-400" data-testid="proof-set-warning">
          {missing.length} {t('authority_room.proofs_missing_hint')}
        </div>
      )}
    </div>
  );
}
