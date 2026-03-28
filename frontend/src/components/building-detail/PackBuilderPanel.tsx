import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { packBuilderApi } from '@/api/packBuilder';
import type { PackResult, PackTypeInfo, PackConformanceResult } from '@/api/packBuilder';
import { useTranslation } from '@/i18n';
import { cn, formatDateTime } from '@/utils/formatters';
import {
  Shield,
  User,
  ShieldPlus,
  Wrench,
  FileText,
  ArrowRightLeft,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Download,
  ChevronDown,
  ChevronRight,
  Hash,
  Lock,
  Eye,
  X,
  EyeOff,
  Info,
} from 'lucide-react';

interface PackBuilderPanelProps {
  buildingId: string;
}

const PACK_ICONS: Record<string, typeof Shield> = {
  authority: Shield,
  owner: User,
  insurer: ShieldPlus,
  contractor: Wrench,
  notary: FileText,
  transfer: ArrowRightLeft,
};

const PACK_COLORS: Record<string, { bg: string; text: string; darkBg: string; darkText: string }> = {
  authority: {
    bg: 'bg-red-100',
    text: 'text-red-600',
    darkBg: 'dark:bg-red-900/30',
    darkText: 'dark:text-red-400',
  },
  owner: {
    bg: 'bg-blue-100',
    text: 'text-blue-600',
    darkBg: 'dark:bg-blue-900/30',
    darkText: 'dark:text-blue-400',
  },
  insurer: {
    bg: 'bg-purple-100',
    text: 'text-purple-600',
    darkBg: 'dark:bg-purple-900/30',
    darkText: 'dark:text-purple-400',
  },
  contractor: {
    bg: 'bg-amber-100',
    text: 'text-amber-600',
    darkBg: 'dark:bg-amber-900/30',
    darkText: 'dark:text-amber-400',
  },
  notary: {
    bg: 'bg-emerald-100',
    text: 'text-emerald-600',
    darkBg: 'dark:bg-emerald-900/30',
    darkText: 'dark:text-emerald-400',
  },
  transfer: {
    bg: 'bg-slate-100',
    text: 'text-slate-600',
    darkBg: 'dark:bg-slate-700',
    darkText: 'dark:text-slate-400',
  },
};

function ReadinessIndicator({ readiness, score }: { readiness: string; score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div className="flex items-center gap-1.5">
      <span
        className={cn(
          'w-2 h-2 rounded-full',
          readiness === 'ready'
            ? 'bg-green-500'
            : readiness === 'partial'
              ? 'bg-yellow-500'
              : 'bg-red-500',
        )}
      />
      <span className="text-[10px] text-gray-500 dark:text-slate-400">{pct}%</span>
    </div>
  );
}

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
      <span className="text-xs font-medium text-gray-600 dark:text-slate-300 w-10 text-right">
        {pct}%
      </span>
    </div>
  );
}

function PackCard({
  pack,
  onGenerate,
  isGenerating,
}: {
  pack: PackTypeInfo;
  onGenerate: (packType: string) => void;
  isGenerating: boolean;
}) {
  const Icon = PACK_ICONS[pack.pack_type] || FileText;
  const colors = PACK_COLORS[pack.pack_type] || PACK_COLORS.transfer;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-4 flex flex-col gap-3 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'w-10 h-10 rounded-lg flex items-center justify-center',
              colors.bg,
              colors.darkBg,
            )}
          >
            <Icon className={cn('w-5 h-5', colors.text, colors.darkText)} />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{pack.name}</h4>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-gray-500 dark:text-slate-400">
                {pack.section_count} sections
              </span>
              {pack.includes_trust && (
                <span className="inline-flex items-center gap-0.5 text-[10px] text-gray-400 dark:text-slate-500">
                  <Lock className="w-2.5 h-2.5" />
                  Trust
                </span>
              )}
              {pack.includes_provenance && (
                <span className="inline-flex items-center gap-0.5 text-[10px] text-gray-400 dark:text-slate-500">
                  <Eye className="w-2.5 h-2.5" />
                  Provenance
                </span>
              )}
            </div>
          </div>
        </div>
        <ReadinessIndicator readiness={pack.readiness} score={pack.readiness_score} />
      </div>

      {/* Generate button */}
      <button
        onClick={() => onGenerate(pack.pack_type)}
        disabled={isGenerating}
        className={cn(
          'w-full mt-auto inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors',
          pack.readiness === 'not_ready'
            ? 'bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-slate-500 cursor-not-allowed'
            : 'bg-red-600 text-white hover:bg-red-700',
          'disabled:opacity-50 disabled:cursor-not-allowed',
        )}
      >
        {isGenerating ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <Icon className="w-3.5 h-3.5" />
        )}
        {isGenerating ? 'Generation...' : 'Generer'}
      </button>
    </div>
  );
}

function ConformanceBadge({ conformance }: { conformance: PackConformanceResult }) {
  const label =
    conformance.result === 'pass'
      ? 'Conforme'
      : conformance.result === 'partial'
        ? 'Partiel'
        : 'Non conforme';
  const bgColor =
    conformance.result === 'pass'
      ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
      : conformance.result === 'partial'
        ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
        : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300';
  const IconEl =
    conformance.result === 'pass'
      ? CheckCircle2
      : conformance.result === 'partial'
        ? AlertTriangle
        : AlertTriangle;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            'inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium',
            bgColor,
          )}
        >
          <IconEl className="w-3 h-3" />
          {label} ({Math.round(conformance.score * 100)}%)
        </span>
        <span className="text-[10px] text-gray-400 dark:text-slate-500">
          Profil: {conformance.profile}
        </span>
      </div>
      {conformance.failed_checks.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="w-3.5 h-3.5 text-red-500" />
            <span className="text-xs font-medium text-red-700 dark:text-red-300">
              {conformance.failed_checks.length} verification(s) echouee(s)
            </span>
          </div>
          <ul className="space-y-0.5">
            {conformance.failed_checks.map((fc, i) => (
              <li key={i} className="text-xs text-red-600 dark:text-red-400">
                {fc.reason || fc.check}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function PackResultView({
  result,
  onClose,
  onDownload,
}: {
  result: PackResult;
  onClose: () => void;
  onDownload: () => void;
}) {
  const [showSections, setShowSections] = useState(false);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 flex items-center justify-between border-b border-gray-200 dark:border-slate-700">
        <div className="flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-green-500" />
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              {result.pack_name}
            </h3>
            <p className="text-xs text-gray-500 dark:text-slate-400">
              Pack genere le {formatDateTime(result.generated_at)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {result.financials_redacted && (
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">
              <EyeOff className="w-3 h-3" />
              Montants masques
            </span>
          )}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Key metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1">
              Completude
            </p>
            <CompletenessBar value={result.overall_completeness} />
          </div>
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1">
              Sections
            </p>
            <p className="text-sm font-semibold text-gray-900 dark:text-white">
              {result.total_sections}
            </p>
          </div>
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1">
              Reserves
            </p>
            <p className="text-sm font-semibold text-gray-900 dark:text-white">
              {result.caveats_count}
            </p>
          </div>
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
            <p className="text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1">
              Version
            </p>
            <p className="text-sm font-semibold text-gray-900 dark:text-white">
              v{result.pack_version}
            </p>
          </div>
        </div>

        {/* Conformance result */}
        {result.conformance && <ConformanceBadge conformance={result.conformance} />}

        {/* Warnings */}
        {result.warnings.length > 0 && (
          <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              <span className="text-xs font-medium text-amber-700 dark:text-amber-300">
                {result.warnings.length} avertissement(s)
              </span>
            </div>
            <ul className="space-y-0.5">
              {result.warnings.map((w, i) => (
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
          {showSections ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5" />
          )}
          {showSections ? 'Masquer les sections' : 'Voir les sections du pack'}
        </button>

        {showSections && (
          <div className="space-y-1.5">
            {result.sections.map((section, idx) => (
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

        {/* SHA-256 hash */}
        {result.sha256_hash && (
          <div className="flex items-center gap-2 text-[10px] text-gray-400 dark:text-slate-500 font-mono">
            <Hash className="w-3 h-3" />
            <span className="truncate">{result.sha256_hash}</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={onDownload}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Telecharger (JSON)
          </button>
        </div>
      </div>
    </div>
  );
}

export default function PackBuilderPanel({ buildingId }: PackBuilderPanelProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [generatedPack, setGeneratedPack] = useState<PackResult | null>(null);
  const [generatingType, setGeneratingType] = useState<string | null>(null);
  const [redactFinancials, setRedactFinancials] = useState(false);

  // Fetch available packs
  const { data: availablePacks, isLoading } = useQuery({
    queryKey: ['pack-builder-available', buildingId],
    queryFn: () => packBuilderApi.listAvailable(buildingId),
    staleTime: 60_000,
  });

  // Generate mutation
  const generateMutation = useMutation({
    mutationFn: (packType: string) =>
      packBuilderApi.generate(buildingId, packType, {
        redact_financials: redactFinancials,
      }),
    onSuccess: (result) => {
      setGeneratedPack(result);
      setGeneratingType(null);
      queryClient.invalidateQueries({ queryKey: ['pack-builder-available', buildingId] });
    },
    onError: () => {
      setGeneratingType(null);
    },
  });

  const handleGenerate = (packType: string) => {
    setGeneratingType(packType);
    generateMutation.mutate(packType);
  };

  const handleDownload = () => {
    if (!generatedPack) return;
    const blob = new Blob([JSON.stringify(generatedPack, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pack-${generatedPack.pack_type}-${new Date(generatedPack.generated_at).toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return null; // silent loading
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
          <Shield className="w-5 h-5 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            {t('pack_builder.title') || 'Pack Builder'}
          </h3>
          <p className="text-xs text-gray-500 dark:text-slate-400">
            {t('pack_builder.subtitle') ||
              'Generez des packs adaptes a chaque audience depuis la meme base de verite'}
          </p>
        </div>
      </div>

      {/* Error state */}
      {generateMutation.isError && (
        <div className="flex items-center gap-2 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
          <span className="text-xs text-red-700 dark:text-red-300">
            Erreur lors de la generation du pack
          </span>
        </div>
      )}

      {/* Generated pack result */}
      {generatedPack && (
        <PackResultView
          result={generatedPack}
          onClose={() => setGeneratedPack(null)}
          onDownload={handleDownload}
        />
      )}

      {/* Financial redaction option */}
      <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-4 py-3">
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={redactFinancials}
            onChange={(e) => setRedactFinancials(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-gray-300 dark:border-slate-500 text-red-600 focus:ring-red-500 dark:bg-slate-600"
          />
          <div>
            <span className="text-xs font-medium text-gray-700 dark:text-slate-200">
              Masquer les montants financiers
            </span>
            <div className="flex items-start gap-1 mt-0.5">
              <Info className="w-3 h-3 text-gray-400 dark:text-slate-500 mt-0.5 flex-shrink-0" />
              <span className="text-[10px] text-gray-500 dark:text-slate-400 leading-tight">
                Les documents techniques et attestations restent visibles. Seuls les montants, devis
                et conditions financieres sont masques.
              </span>
            </div>
          </div>
        </label>
      </div>

      {/* Pack type grid */}
      {availablePacks && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {availablePacks.packs.map((pack) => (
            <PackCard
              key={pack.pack_type}
              pack={pack}
              onGenerate={handleGenerate}
              isGenerating={generatingType === pack.pack_type}
            />
          ))}
        </div>
      )}
    </div>
  );
}
