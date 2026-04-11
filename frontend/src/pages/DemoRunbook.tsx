/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view under Admin (demo tooling).
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { demoPilotApi } from '@/api/demoPilot';
import type { DemoScenarioWithRunbook } from '@/api/demoPilot';
import { ChevronDown, ChevronRight, Play, Loader2, AlertTriangle } from 'lucide-react';

export default function DemoRunbook() {
  const { t } = useTranslation();
  const [expandedCode, setExpandedCode] = useState<string | null>(null);

  const {
    data: scenarios = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['demo-scenarios'],
    queryFn: demoPilotApi.listScenarios,
  });

  const {
    data: runbook,
    isLoading: runbookLoading,
    isError: runbookError,
  } = useQuery<DemoScenarioWithRunbook>({
    queryKey: ['demo-runbook', expandedCode],
    queryFn: () => demoPilotApi.getRunbook(expandedCode!),
    enabled: !!expandedCode,
  });

  const toggleScenario = (code: string) => {
    setExpandedCode((prev) => (prev === code ? null : code));
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('demo_runbook.title')}</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('demo_runbook.description')}</p>
      </div>

      {scenarios.length === 0 ? (
        <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-8 text-center">
          <p className="text-gray-500 dark:text-slate-400">{t('demo_runbook.empty')}</p>
        </div>
      ) : (
        <div className="space-y-3" data-testid="demo-scenario-list">
          {scenarios.map((scenario) => {
            const isExpanded = expandedCode === scenario.scenario_code;
            return (
              <div
                key={scenario.id}
                className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl overflow-hidden"
              >
                {/* Scenario Header */}
                <button
                  onClick={() => toggleScenario(scenario.scenario_code)}
                  className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
                  data-testid={`demo-scenario-${scenario.scenario_code}`}
                >
                  {isExpanded ? (
                    <ChevronDown className="w-5 h-5 text-gray-400 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900 dark:text-white truncate">{scenario.title}</h3>
                      <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
                        {scenario.persona_target}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-slate-400 mt-0.5 truncate">
                      {scenario.starting_state_description}
                    </p>
                  </div>
                </button>

                {/* Expanded Runbook */}
                {isExpanded && (
                  <div className="border-t border-gray-200 dark:border-slate-700 px-5 py-4">
                    {runbookLoading ? (
                      <div className="flex items-center justify-center py-6">
                        <Loader2 className="w-6 h-6 animate-spin text-red-600" />
                      </div>
                    ) : runbookError ? (
                      <p className="text-sm text-red-600 dark:text-red-400">{t('app.error')}</p>
                    ) : runbook ? (
                      <div className="space-y-4">
                        {/* Reveal surfaces */}
                        {runbook.reveal_surfaces.length > 0 && (
                          <div>
                            <h4 className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                              {t('demo_runbook.reveal_surfaces')}
                            </h4>
                            <div className="flex flex-wrap gap-1">
                              {runbook.reveal_surfaces.map((s) => (
                                <span
                                  key={s}
                                  className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300 rounded"
                                >
                                  {s}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Proof & Action moments */}
                        {(runbook.proof_moment || runbook.action_moment) && (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {runbook.proof_moment && (
                              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
                                <p className="text-xs font-medium text-green-700 dark:text-green-400 mb-1">
                                  {t('demo_runbook.proof_moment')}
                                </p>
                                <p className="text-sm text-green-900 dark:text-green-200">{runbook.proof_moment}</p>
                              </div>
                            )}
                            {runbook.action_moment && (
                              <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3">
                                <p className="text-xs font-medium text-amber-700 dark:text-amber-400 mb-1">
                                  {t('demo_runbook.action_moment')}
                                </p>
                                <p className="text-sm text-amber-900 dark:text-amber-200">{runbook.action_moment}</p>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Runbook Steps */}
                        {runbook.runbook_steps.length > 0 && (
                          <div>
                            <h4 className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                              {t('demo_runbook.steps')}
                            </h4>
                            <ol className="space-y-2">
                              {runbook.runbook_steps
                                .sort((a, b) => a.step_order - b.step_order)
                                .map((step) => (
                                  <li
                                    key={step.id}
                                    className="flex gap-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3"
                                    data-testid={`runbook-step-${step.step_order}`}
                                  >
                                    <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-xs font-bold">
                                      {step.step_order}
                                    </span>
                                    <div className="min-w-0">
                                      <p className="font-medium text-gray-900 dark:text-white text-sm">{step.title}</p>
                                      {step.description && (
                                        <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                                          {step.description}
                                        </p>
                                      )}
                                      {step.expected_ui_state && (
                                        <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                                          {t('demo_runbook.expected_state')}: {step.expected_ui_state}
                                        </p>
                                      )}
                                    </div>
                                  </li>
                                ))}
                            </ol>
                          </div>
                        )}

                        {/* Start Demo Link */}
                        {runbook.seed_key && (
                          <Link
                            to={`/buildings/1`}
                            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
                            data-testid="start-demo-link"
                          >
                            <Play className="w-4 h-4" />
                            {t('demo_runbook.start_demo')}
                          </Link>
                        )}
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
