import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  renovationReadinessApi,
  type RenovationReadinessAssessment,
  type RenovationOption,
} from '@/api/renovationReadiness';
import {
  HardHat,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  FileDown,
  Info,
  Banknote,
  ClipboardList,
  HelpCircle,
  ShieldAlert,
  ArrowRight,
} from 'lucide-react';

interface RenovationReadinessPanelProps {
  buildingId: string;
}

function VerdictBadge({ verdict }: { verdict: string }) {
  if (verdict === 'ready') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">
        <CheckCircle2 className="w-3.5 h-3.5" />
        Pret
      </span>
    );
  }
  if (verdict === 'partially_ready') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
        <AlertTriangle className="w-3.5 h-3.5" />
        Partiellement pret
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">
      <XCircle className="w-3.5 h-3.5" />
      Pas pret
    </span>
  );
}

function CompletenessBar({ pct }: { pct: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full transition-all',
            pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500',
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-medium text-gray-600 dark:text-slate-300 w-10 text-right">{pct}%</span>
    </div>
  );
}

export default function RenovationReadinessPanel({ buildingId }: RenovationReadinessPanelProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [selectedWorkType, setSelectedWorkType] = useState<string>('');

  // Fetch available work types
  const { data: options } = useQuery({
    queryKey: ['renovation-options', buildingId],
    queryFn: () => renovationReadinessApi.listOptions(buildingId),
    enabled: expanded,
  });

  // Fetch assessment for selected work type
  const {
    data: assessment,
    isLoading: assessmentLoading,
    error: assessmentError,
  } = useQuery({
    queryKey: ['renovation-readiness', buildingId, selectedWorkType],
    queryFn: () => renovationReadinessApi.assess(buildingId, selectedWorkType),
    enabled: !!selectedWorkType && expanded,
  });

  // Pack generation
  const packMutation = useMutation({
    mutationFn: () => renovationReadinessApi.generatePack(buildingId, selectedWorkType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['renovation-readiness', buildingId] });
    },
  });

  const title = t('renovation_readiness.title') || 'Preparation renovation';

  // Determine collapsed quick indicator
  const quickStatus = assessment
    ? assessment.readiness?.verdict === 'ready'
      ? 'ready'
      : assessment.readiness?.verdict === 'partially_ready'
        ? 'partial'
        : 'not_ready'
    : 'not_evaluated';

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-600 overflow-hidden">
      {/* Collapsed header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-orange-100 dark:bg-orange-900/40 flex items-center justify-center">
            <HardHat className="w-5 h-5 text-orange-600 dark:text-orange-400" />
          </div>
          <div className="text-left">
            <p className="text-sm font-semibold text-gray-900 dark:text-white">{title}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">
              {quickStatus === 'ready'
                ? 'Pret pour les travaux'
                : quickStatus === 'partial'
                  ? 'Partiellement pret'
                  : quickStatus === 'not_ready'
                    ? 'Actions requises'
                    : t('renovation_readiness.not_evaluated') || 'Non evalue'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {quickStatus === 'ready' && (
            <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
          )}
          {quickStatus === 'partial' && (
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          )}
          {quickStatus === 'not_ready' && (
            <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
          )}
          {expanded ? (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t border-gray-100 dark:border-slate-700">
          {/* Work type selector */}
          <div className="pt-4">
            <label className="block text-xs font-medium text-gray-600 dark:text-slate-400 mb-1.5">
              Type de travaux
            </label>
            <select
              value={selectedWorkType}
              onChange={(e) => setSelectedWorkType(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-slate-500 bg-white dark:bg-slate-700 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500 focus:border-orange-500"
            >
              <option value="">
                {t('renovation_readiness.assess') || 'Selectionner un type...'}
              </option>
              {(options || []).map((opt: RenovationOption) => (
                <option key={opt.work_type} value={opt.work_type}>
                  {opt.label_fr}
                  {opt.pollutant ? ` (${opt.pollutant})` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Loading */}
          {assessmentLoading && selectedWorkType && (
            <div className="flex items-center justify-center py-6 text-gray-400 dark:text-slate-500">
              <Loader2 className="w-5 h-5 animate-spin mr-2" />
              <span className="text-sm">Evaluation en cours...</span>
            </div>
          )}

          {/* Error */}
          {assessmentError && (
            <div className="text-sm text-red-600 dark:text-red-400 py-2">
              Erreur lors de l&apos;evaluation.
            </div>
          )}

          {/* Assessment results */}
          {assessment && !assessment.error && !assessmentLoading && (
            <AssessmentResults
              assessment={assessment}
              onGeneratePack={() => packMutation.mutate()}
              packLoading={packMutation.isPending}
              packResult={packMutation.data}
            />
          )}
        </div>
      )}
    </div>
  );
}

function AssessmentResults({
  assessment,
  onGeneratePack,
  packLoading,
  packResult,
}: {
  assessment: RenovationReadinessAssessment;
  onGeneratePack: () => void;
  packLoading: boolean;
  packResult?: { pack?: { pack_id: string; sections_count?: number }; error?: string } | null;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      {/* Readiness verdict */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
            Verdict
          </p>
          <VerdictBadge verdict={assessment.readiness.verdict} />
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500 dark:text-slate-400">Note passeport</p>
          <span
            className={cn(
              'text-lg font-bold',
              assessment.passport_grade <= 'B'
                ? 'text-green-600 dark:text-green-400'
                : assessment.passport_grade <= 'D'
                  ? 'text-amber-600 dark:text-amber-400'
                  : 'text-red-600 dark:text-red-400',
            )}
          >
            {assessment.passport_grade}
          </span>
        </div>
      </div>

      {/* Completeness */}
      <div>
        <div className="flex items-center gap-1.5 mb-1.5">
          <ClipboardList className="w-3.5 h-3.5 text-gray-400" />
          <p className="text-xs font-medium text-gray-600 dark:text-slate-400">
            Completude du dossier
          </p>
        </div>
        <CompletenessBar pct={assessment.completeness.score_pct} />
        {assessment.completeness.missing.length > 0 && (
          <ul className="mt-2 space-y-1">
            {assessment.completeness.missing.slice(0, 4).map((item, i) => (
              <li
                key={i}
                className="flex items-start gap-1.5 text-xs text-red-600 dark:text-red-400"
              >
                <XCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                <span>{item.details || item.label}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Subsidies */}
      {assessment.subsidies.eligible.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-1.5">
            <Banknote className="w-3.5 h-3.5 text-green-500" />
            <p className="text-xs font-medium text-gray-600 dark:text-slate-400">
              Subventions disponibles
            </p>
          </div>
          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 space-y-1.5">
            {assessment.subsidies.eligible.map((sub, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-green-800 dark:text-green-300">{sub.name}</span>
                {sub.max_amount > 0 && (
                  <span className="font-semibold text-green-700 dark:text-green-200">
                    max. {typeof sub.max_amount === 'number' ? sub.max_amount.toLocaleString('fr-CH') : sub.max_amount}{' '}
                    CHF
                  </span>
                )}
              </div>
            ))}
            {assessment.subsidies.total_potential_chf > 0 && (
              <div className="pt-1 border-t border-green-200 dark:border-green-800 flex justify-between text-xs font-semibold text-green-800 dark:text-green-200">
                <span>Total potentiel</span>
                <span>{assessment.subsidies.total_potential_chf.toLocaleString('fr-CH')} CHF</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Procedures */}
      {assessment.procedures.forms_needed.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-1.5">
            <Info className="w-3.5 h-3.5 text-blue-500" />
            <p className="text-xs font-medium text-gray-600 dark:text-slate-400">
              Procedures requises
            </p>
          </div>
          <ul className="space-y-1">
            {assessment.procedures.forms_needed.map((form, i) => (
              <li key={i} className="flex items-center gap-1.5 text-xs text-gray-700 dark:text-slate-300">
                <ArrowRight className="w-3 h-3 text-gray-400 flex-shrink-0" />
                {form}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Unknowns */}
      {assessment.unknowns.count > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-1.5">
            <HelpCircle className="w-3.5 h-3.5 text-amber-500" />
            <p className="text-xs font-medium text-gray-600 dark:text-slate-400">
              Inconnues ({assessment.unknowns.count})
            </p>
          </div>
          {assessment.unknowns.critical.length > 0 && (
            <ul className="space-y-1">
              {assessment.unknowns.critical.slice(0, 3).map((unk, i) => (
                <li key={i} className="flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-300">
                  <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                  {unk.subject}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Caveats */}
      {assessment.caveats.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-gray-500" />
            <p className="text-xs font-medium text-gray-600 dark:text-slate-400">
              Reserves
            </p>
          </div>
          <ul className="space-y-1">
            {assessment.caveats.slice(0, 3).map((cav, i) => (
              <li key={i} className="text-xs text-gray-600 dark:text-slate-400">
                {cav.title}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Next actions */}
      {assessment.next_actions.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-600 dark:text-slate-400 mb-1.5">
            Prochaines actions
          </p>
          <ul className="space-y-1.5">
            {assessment.next_actions.slice(0, 5).map((action, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <span
                  className={cn(
                    'mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0',
                    action.priority === 'high'
                      ? 'bg-red-500'
                      : action.priority === 'medium'
                        ? 'bg-amber-500'
                        : 'bg-gray-400',
                  )}
                />
                <span className="text-gray-700 dark:text-slate-300">{action.title}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Generate pack button */}
      <div className="pt-2 border-t border-gray-100 dark:border-slate-700">
        {assessment.pack_ready ? (
          <button
            onClick={onGeneratePack}
            disabled={packLoading}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-orange-600 hover:bg-orange-700 disabled:opacity-50 rounded-lg transition-colors"
          >
            {packLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generation en cours...
              </>
            ) : (
              <>
                <FileDown className="w-4 h-4" />
                {packResult?.pack
                  ? 'Pack genere'
                  : 'Generer le pack'}
              </>
            )}
          </button>
        ) : (
          <div>
            <button
              disabled
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-gray-400 dark:text-slate-500 bg-gray-100 dark:bg-slate-700 rounded-lg cursor-not-allowed"
              title={assessment.pack_blockers.join(', ')}
            >
              <FileDown className="w-4 h-4" />
              {t('renovation_readiness.generate_pack') || 'Generer le pack'}
            </button>
            {assessment.pack_blockers.length > 0 && (
              <ul className="mt-2 space-y-1">
                {assessment.pack_blockers.map((blocker, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-red-500 dark:text-red-400">
                    <XCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                    {blocker}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Pack result */}
        {packResult?.pack && (
          <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
            <div className="flex items-center gap-2 text-sm text-green-700 dark:text-green-300">
              <CheckCircle2 className="w-4 h-4" />
              <span className="font-medium">Pack genere avec succes</span>
            </div>
            <p className="text-xs text-green-600 dark:text-green-400 mt-1">
              {packResult.pack.sections_count} sections
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
