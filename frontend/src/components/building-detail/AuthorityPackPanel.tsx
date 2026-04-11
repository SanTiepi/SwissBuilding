import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authorityPacksApi } from '@/api/authorityPacks';
import { useTranslation } from '@/i18n';
import { cn, formatDateTime } from '@/utils/formatters';
import type { AuthorityPackResult, AuthorityPackListItem } from '@/types';
import {
  Shield,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Download,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  FileCheck,
  Clock,
  Hash,
  EyeOff,
  Info,
} from 'lucide-react';

interface AuthorityPackPanelProps {
  buildingId: string;
}

type PackState = 'idle' | 'generating' | 'ready' | 'error';

function CompletenessBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
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

export default function AuthorityPackPanel({ buildingId }: AuthorityPackPanelProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [showSections, setShowSections] = useState(false);
  const [redactFinancials, setRedactFinancials] = useState(false);

  // Fetch latest pack list
  const { data: packs, isLoading: packsLoading } = useQuery({
    queryKey: ['authority-packs-panel', buildingId],
    queryFn: () => authorityPacksApi.list(buildingId),
    staleTime: 60_000,
  });

  const latestPack: AuthorityPackListItem | undefined = packs?.[0];

  // Fetch full pack details when expanded
  const { data: packDetail, isLoading: detailLoading } = useQuery({
    queryKey: ['authority-pack-detail-panel', latestPack?.pack_id],
    queryFn: () => authorityPacksApi.get(latestPack!.pack_id),
    enabled: !!latestPack?.pack_id && expanded,
    staleTime: 60_000,
  });

  // Generate mutation
  const generateMutation = useMutation({
    mutationFn: () => authorityPacksApi.generate(buildingId, { redact_financials: redactFinancials }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['authority-packs-panel', buildingId] });
    },
  });

  const packState: PackState = generateMutation.isPending
    ? 'generating'
    : generateMutation.isError
      ? 'error'
      : latestPack
        ? 'ready'
        : 'idle';

  const handleDownload = (pack: AuthorityPackResult) => {
    const blob = new Blob([JSON.stringify(pack, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `authority-pack-${pack.canton}-${new Date(pack.generated_at).toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (packsLoading) {
    return null; // silent loading — don't flash
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'w-10 h-10 rounded-lg flex items-center justify-center',
              packState === 'ready'
                ? 'bg-green-100 dark:bg-green-900/30'
                : packState === 'generating'
                  ? 'bg-amber-100 dark:bg-amber-900/30'
                  : 'bg-gray-100 dark:bg-slate-700',
            )}
          >
            <Shield
              className={cn(
                'w-5 h-5',
                packState === 'ready'
                  ? 'text-green-600 dark:text-green-400'
                  : packState === 'generating'
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-gray-400 dark:text-slate-500',
              )}
            />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              {t('authority_packs.panel_title') || 'Pack autorite'}
            </h3>
            <p className="text-xs text-gray-500 dark:text-slate-400">
              {packState === 'ready'
                ? t('authority_packs.pack_ready') || 'Pack genere'
                : packState === 'generating'
                  ? t('authority_packs.generating') || 'Generation en cours...'
                  : t('authority_packs.not_generated') || 'Aucun pack genere'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Generate / Regenerate button */}
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
              latestPack
                ? 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 hover:bg-gray-200 dark:hover:bg-slate-600'
                : 'bg-red-600 text-white hover:bg-red-700',
              'disabled:opacity-50 disabled:cursor-not-allowed',
            )}
          >
            {generateMutation.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : latestPack ? (
              <RefreshCw className="w-3.5 h-3.5" />
            ) : (
              <Shield className="w-3.5 h-3.5" />
            )}
            {latestPack
              ? t('authority_packs.regenerate') || 'Regenerer'
              : t('authority_packs.generate') || 'Generer le pack autorite'}
          </button>

          {/* Expand toggle */}
          {latestPack && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 dark:text-slate-500 transition-colors"
            >
              {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
          )}
        </div>
      </div>

      {/* Financial redaction option */}
      <div className="px-5 pb-2">
        <label className="flex items-start gap-2.5 cursor-pointer">
          <input
            type="checkbox"
            checked={redactFinancials}
            onChange={(e) => setRedactFinancials(e.target.checked)}
            className="mt-0.5 h-3.5 w-3.5 rounded border-gray-300 dark:border-slate-500 text-red-600 focus:ring-red-500 dark:bg-slate-600"
          />
          <div>
            <span className="text-xs text-gray-700 dark:text-slate-200">Masquer les montants financiers</span>
            <div className="flex items-start gap-1 mt-0.5">
              <Info className="w-2.5 h-2.5 text-gray-400 dark:text-slate-500 mt-0.5 flex-shrink-0" />
              <span className="text-[10px] text-gray-500 dark:text-slate-400 leading-tight">
                Les documents techniques et attestations restent visibles. Seuls les montants, devis et conditions
                financieres sont masques.
              </span>
            </div>
          </div>
        </label>
      </div>

      {/* Error state */}
      {generateMutation.isError && (
        <div className="px-5 pb-4">
          <div className="flex items-center gap-2 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
            <span className="text-xs text-red-700 dark:text-red-300">
              {t('app.error') || 'Erreur lors de la generation'}
            </span>
          </div>
        </div>
      )}

      {/* Summary row when pack exists but not expanded */}
      {latestPack && !expanded && (
        <div className="px-5 pb-4 flex flex-wrap items-center gap-4 text-xs text-gray-500 dark:text-slate-400">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
            <span>{Math.round(latestPack.overall_completeness * 100)}% completude</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            <span>{formatDateTime(latestPack.generated_at)}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <FileCheck className="w-3.5 h-3.5" />
            <span>{latestPack.canton}</span>
          </div>
        </div>
      )}

      {/* Expanded detail view */}
      {expanded && latestPack && (
        <div className="border-t border-gray-200 dark:border-slate-700 px-5 py-4 space-y-4">
          {detailLoading && (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          )}

          {packDetail && (
            <>
              {/* Key metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1">
                    Completude
                  </p>
                  <CompletenessBar value={packDetail.overall_completeness} />
                </div>
                <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1">
                    Sections
                  </p>
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">{packDetail.total_sections}</p>
                </div>
                <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1">
                    Reserves
                  </p>
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">{packDetail.caveats_count}</p>
                </div>
                <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1">Version</p>
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">v{packDetail.pack_version}</p>
                </div>
              </div>

              {/* Readiness verdict quick summary */}
              {(() => {
                const readinessSection = packDetail.sections.find((s) => s.section_type === 'readiness_verdict');
                if (!readinessSection || readinessSection.items.length === 0) return null;
                const readyCount = readinessSection.items.filter(
                  (i: Record<string, unknown>) => i.status === 'ready',
                ).length;
                const blockedCount = readinessSection.items.filter(
                  (i: Record<string, unknown>) => i.status === 'blocked',
                ).length;
                return (
                  <div
                    className={cn(
                      'flex items-center gap-3 px-4 py-3 rounded-lg border',
                      blockedCount > 0
                        ? 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20'
                        : 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20',
                    )}
                  >
                    {blockedCount > 0 ? (
                      <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0" />
                    ) : (
                      <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                    )}
                    <div>
                      <p
                        className={cn(
                          'text-sm font-medium',
                          blockedCount > 0 ? 'text-red-700 dark:text-red-300' : 'text-green-700 dark:text-green-300',
                        )}
                      >
                        {readyCount}/{readinessSection.items.length} readiness checks prets
                      </p>
                      {blockedCount > 0 && (
                        <p className="text-xs text-red-600 dark:text-red-400">
                          {blockedCount} bloque(s) — des actions sont requises avant soumission
                        </p>
                      )}
                    </div>
                  </div>
                );
              })()}

              {/* Warnings */}
              {packDetail.warnings.length > 0 && (
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                    <span className="text-xs font-medium text-amber-700 dark:text-amber-300">
                      {packDetail.warnings.length} avertissement(s)
                    </span>
                  </div>
                  <ul className="space-y-0.5">
                    {packDetail.warnings.map((w, i) => (
                      <li key={i} className="text-xs text-amber-600 dark:text-amber-400">
                        {w}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Sections toggle */}
              <button
                onClick={() => setShowSections(!showSections)}
                className="flex items-center gap-2 text-xs font-medium text-gray-600 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                {showSections ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                {showSections ? 'Masquer les sections' : 'Voir les sections du pack'}
              </button>

              {showSections && (
                <div className="space-y-1.5">
                  {packDetail.sections.map((section, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-slate-700/50 rounded-lg"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className={cn(
                            'w-2 h-2 rounded-full flex-shrink-0',
                            section.completeness >= 0.8
                              ? 'bg-green-500'
                              : section.completeness >= 0.5
                                ? 'bg-yellow-500'
                                : 'bg-red-500',
                          )}
                        />
                        <span className="text-xs text-gray-700 dark:text-slate-200 truncate">
                          {section.section_name}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className="text-[10px] text-gray-500 dark:text-slate-400">
                          {section.items.length} items
                        </span>
                        <span className="text-[10px] font-medium text-gray-600 dark:text-slate-300">
                          {Math.round(section.completeness * 100)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Financials redacted badge */}
              {packDetail.financials_redacted && (
                <div className="flex items-center gap-2 px-3 py-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                  <EyeOff className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                  <span className="text-xs text-amber-700 dark:text-amber-300">Montants masques</span>
                </div>
              )}

              {/* SHA-256 hash */}
              {packDetail.sha256_hash && (
                <div className="flex items-center gap-2 text-[10px] text-gray-400 dark:text-slate-500 font-mono">
                  <Hash className="w-3 h-3" />
                  <span className="truncate">{packDetail.sha256_hash}</span>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-3 pt-1">
                <button
                  onClick={() => handleDownload(packDetail)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  Telecharger (JSON)
                </button>
                <span className="text-[10px] text-gray-400 dark:text-slate-500">
                  Genere le {formatDateTime(packDetail.generated_at)}
                </span>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
