import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authorityPacksApi } from '@/api/authorityPacks';
import type { GenerateAuthorityPackParams } from '@/api/authorityPacks';
import { buildingsApi } from '@/api/buildings';
import { useAuth } from '@/hooks/useAuth';
import { useTranslation } from '@/i18n';
import { formatDateTime, cn } from '@/utils/formatters';
import type { AuthorityPackListItem, AuthorityPackSection, Building } from '@/types';
import {
  Shield,
  Loader2,
  AlertTriangle,
  FileCheck,
  ChevronDown,
  ChevronRight,
  Plus,
  Eye,
  CheckCircle2,
  Clock,
  Send,
  FileText,
  X,
  RefreshCw,
} from 'lucide-react';

const STATUS_CONFIG: Record<string, { icon: typeof Clock; color: string; bgColor: string }> = {
  draft: { icon: FileText, color: 'text-gray-500', bgColor: 'bg-gray-100 dark:bg-slate-700' },
  ready: {
    icon: CheckCircle2,
    color: 'text-green-500',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
  },
  submitted: { icon: Send, color: 'text-blue-500', bgColor: 'bg-blue-100 dark:bg-blue-900/30' },
  acknowledged: {
    icon: Shield,
    color: 'text-purple-500',
    bgColor: 'bg-purple-100 dark:bg-purple-900/30',
  },
  generating: {
    icon: Loader2,
    color: 'text-amber-500',
    bgColor: 'bg-amber-100 dark:bg-amber-900/30',
  },
};

const ALL_SECTIONS = [
  'building_identity',
  'diagnostic_summary',
  'sample_results',
  'compliance_status',
  'action_plan',
  'risk_assessment',
  'intervention_history',
  'document_inventory',
] as const;

const LANGUAGES = ['fr', 'de', 'it', 'en'] as const;

function CompletenessBar({ value, className }: { value: number; className?: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="w-20 h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full transition-all',
            pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500',
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 dark:text-slate-400">{pct}%</span>
    </div>
  );
}

function SectionTypeBadge({ sectionType, t }: { sectionType: string; t: (key: string) => string }) {
  const key = `authority_packs.section_${sectionType}`;
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300">
      {t(key) || sectionType.replace(/_/g, ' ')}
    </span>
  );
}

// ---------- Detail Modal ----------

function PackDetailModal({
  packId,
  building,
  onClose,
}: {
  packId: string;
  building: Building | undefined;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set());

  const { data: pack, isLoading } = useQuery({
    queryKey: ['authority-pack-detail', packId],
    queryFn: () => authorityPacksApi.get(packId),
  });

  const toggleSection = (idx: number) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-xl bg-white dark:bg-slate-800 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('authority_packs.detail') || 'Pack Details'}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-slate-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
          </div>
        )}

        {pack && (
          <div className="p-6 space-y-5">
            {/* Pack header info */}
            <div className="space-y-3">
              {building && (
                <p className="text-sm text-gray-700 dark:text-slate-200">
                  {building.address}, {building.postal_code} {building.city}
                </p>
              )}
              <div className="flex flex-wrap items-center gap-4 text-sm">
                <span className="text-gray-500 dark:text-slate-400">
                  {t('authority_packs.canton') || 'Canton'}: <strong>{pack.canton}</strong>
                </span>
                <span className="text-gray-500 dark:text-slate-400">
                  {t('authority_packs.generated_at') || 'Generated'}: {formatDateTime(pack.generated_at)}
                </span>
              </div>
              <div>
                <span className="text-xs text-gray-500 dark:text-slate-400 mb-1 block">
                  {t('authority_packs.completeness') || 'Completeness'}
                </span>
                <CompletenessBar value={pack.overall_completeness} className="w-full [&>div:first-child]:w-full" />
              </div>
            </div>

            {/* Warnings */}
            {pack.warnings.length > 0 ? (
              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                  <span className="text-sm font-medium text-amber-700 dark:text-amber-300">
                    {t('authority_packs.warnings') || 'Warnings'}
                  </span>
                </div>
                <ul className="space-y-1">
                  {pack.warnings.map((w, i) => (
                    <li key={i} className="text-sm text-amber-600 dark:text-amber-400">
                      {w}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  <span className="text-sm text-green-700 dark:text-green-300">
                    {t('authority_packs.no_warnings') || 'No warnings'}
                  </span>
                </div>
              </div>
            )}

            {/* Sections */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-3">
                {t('authority_packs.sections') || 'Sections'} ({pack.total_sections})
              </h3>
              <div className="space-y-2">
                {pack.sections.map((section: AuthorityPackSection, idx: number) => {
                  const isExpanded = expandedSections.has(idx);
                  return (
                    <div key={idx} className="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden">
                      <button
                        onClick={() => toggleSection(idx)}
                        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors text-left"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
                          )}
                          <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                            {section.section_name}
                          </span>
                          <SectionTypeBadge sectionType={section.section_type} t={t} />
                        </div>
                        <div className="flex items-center gap-3 flex-shrink-0 ml-2">
                          <span className="text-xs text-gray-500 dark:text-slate-400">
                            {section.items.length} {t('authority_packs.items') || 'items'}
                          </span>
                          <CompletenessBar value={section.completeness} />
                        </div>
                      </button>
                      {isExpanded && (
                        <div className="px-4 pb-3 border-t border-gray-100 dark:border-slate-700">
                          {section.notes && (
                            <p className="text-sm text-gray-600 dark:text-slate-300 mt-3 italic">{section.notes}</p>
                          )}
                          {section.items.length > 0 && (
                            <div className="mt-3 space-y-1">
                              {section.items.map((item, iIdx) => (
                                <div
                                  key={iIdx}
                                  className="text-xs text-gray-600 dark:text-slate-400 bg-gray-50 dark:bg-slate-900/50 rounded px-3 py-2 font-mono break-all"
                                >
                                  {JSON.stringify(item)}
                                </div>
                              ))}
                            </div>
                          )}
                          {section.items.length === 0 && !section.notes && (
                            <p className="text-xs text-gray-400 dark:text-slate-500 mt-3">—</p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="sticky bottom-0 bg-white dark:bg-slate-800 border-t border-gray-200 dark:border-slate-700 px-6 py-3 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
          >
            {t('authority_packs.close') || 'Close'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------- Generate Options Modal ----------

function GenerateOptionsModal({
  buildingCanton,
  onGenerate,
  onClose,
  isPending,
}: {
  buildingCanton: string;
  onGenerate: (params: GenerateAuthorityPackParams) => void;
  onClose: () => void;
  isPending: boolean;
}) {
  const { t } = useTranslation();
  const [canton, setCanton] = useState(buildingCanton);
  const [language, setLanguage] = useState<string>('fr');
  const [includePhotos, setIncludePhotos] = useState(true);
  const [selectedSections, setSelectedSections] = useState<Set<string>>(new Set(ALL_SECTIONS));

  const toggleSectionSelection = (section: string) => {
    setSelectedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) next.delete(section);
      else next.add(section);
      return next;
    });
  };

  const handleSubmit = () => {
    const params: GenerateAuthorityPackParams = {};
    if (canton.trim()) params.canton = canton.trim();
    params.language = language;
    params.include_photos = includePhotos;
    if (selectedSections.size < ALL_SECTIONS.length) {
      params.include_sections = Array.from(selectedSections);
    }
    onGenerate(params);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-xl bg-white dark:bg-slate-800 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-gray-200 dark:border-slate-700 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('authority_packs.generate_options') || 'Generation Options'}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-slate-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {/* Canton */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('authority_packs.canton') || 'Canton'}
            </label>
            <input
              type="text"
              value={canton}
              onChange={(e) => setCanton(e.target.value)}
              placeholder="VD"
              className={cn(
                'w-full rounded-lg border px-3 py-2 text-sm',
                'bg-white dark:bg-slate-900 text-gray-700 dark:text-slate-200',
                'border-gray-300 dark:border-slate-600',
                'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500',
              )}
            />
          </div>

          {/* Language */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('authority_packs.language') || 'Language'}
            </label>
            <div className="relative">
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className={cn(
                  'w-full appearance-none rounded-lg border px-3 py-2 pr-10 text-sm',
                  'bg-white dark:bg-slate-900 text-gray-700 dark:text-slate-200',
                  'border-gray-300 dark:border-slate-600',
                  'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500',
                )}
              >
                {LANGUAGES.map((lang) => (
                  <option key={lang} value={lang}>
                    {lang.toUpperCase()}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {/* Include photos */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includePhotos}
              onChange={(e) => setIncludePhotos(e.target.checked)}
              className="rounded border-gray-300 dark:border-slate-600 text-red-600 focus:ring-red-500"
            />
            <span className="text-sm text-gray-700 dark:text-slate-200">
              {t('authority_packs.include_photos') || 'Include photos'}
            </span>
          </label>

          {/* Sections */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-2">
              {t('authority_packs.select_sections') || 'Select sections'}
            </label>
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {ALL_SECTIONS.map((section) => (
                <label key={section} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedSections.has(section)}
                    onChange={() => toggleSectionSelection(section)}
                    className="rounded border-gray-300 dark:border-slate-600 text-red-600 focus:ring-red-500"
                  />
                  <span className="text-sm text-gray-700 dark:text-slate-200">
                    {t(`authority_packs.section_${section}`) || section.replace(/_/g, ' ')}
                  </span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 dark:border-slate-700 px-6 py-3 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
          >
            {t('authority_packs.cancel') || 'Cancel'}
          </button>
          <button
            onClick={handleSubmit}
            disabled={isPending || selectedSections.size === 0}
            className={cn(
              'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              'bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed',
            )}
          >
            {isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            {isPending
              ? t('authority_packs.generating') || 'Generating...'
              : t('authority_packs.generate') || 'Generate Pack'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------- Main Page ----------

export default function AuthorityPacks() {
  const { t } = useTranslation();
  useAuth();
  const queryClient = useQueryClient();
  const [selectedBuildingId, setSelectedBuildingId] = useState<string>('');
  const [detailPackId, setDetailPackId] = useState<string | null>(null);
  const [showGenerateOptions, setShowGenerateOptions] = useState(false);

  const { data: buildingsData, isLoading: buildingsLoading } = useQuery({
    queryKey: ['buildings-for-authority-packs'],
    queryFn: () => buildingsApi.list({ size: 200 }),
  });

  const buildings: Building[] = buildingsData?.items ?? [];
  const selectedBuilding = buildings.find((b) => b.id === selectedBuildingId);

  const {
    data: packs,
    isLoading: packsLoading,
    isError: packsError,
  } = useQuery({
    queryKey: ['authority-packs', selectedBuildingId],
    queryFn: () => authorityPacksApi.list(selectedBuildingId),
    enabled: !!selectedBuildingId,
  });

  const generateMutation = useMutation({
    mutationFn: (params?: GenerateAuthorityPackParams) => authorityPacksApi.generate(selectedBuildingId, params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['authority-packs', selectedBuildingId] });
      setShowGenerateOptions(false);
    },
  });

  const regenerateMutation = useMutation({
    mutationFn: (buildingId: string) => authorityPacksApi.generate(buildingId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['authority-packs', selectedBuildingId] });
    },
  });

  const isLoading = buildingsLoading || (!!selectedBuildingId && packsLoading);
  const packList: AuthorityPackListItem[] = packs ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('authority_packs.title') || 'Authority Packs'}
          </h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {t('authority_packs.description') || 'Authority-ready evidence dossiers for submission'}
          </p>
        </div>
        <Shield className="w-8 h-8 text-gray-300 dark:text-slate-600" />
      </div>

      {/* Building selector + generate button */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <select
            value={selectedBuildingId}
            onChange={(e) => setSelectedBuildingId(e.target.value)}
            className={cn(
              'w-full appearance-none rounded-lg border px-4 py-2.5 pr-10 text-sm',
              'bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200',
              'border-gray-300 dark:border-slate-600',
              'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500',
            )}
          >
            <option value="">{t('authority_packs.select_building') || 'Select a building...'}</option>
            {buildings.map((b) => (
              <option key={b.id} value={b.id}>
                {b.address}, {b.postal_code} {b.city}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
        <button
          onClick={() => setShowGenerateOptions(true)}
          disabled={!selectedBuildingId || generateMutation.isPending}
          className={cn(
            'inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
            'bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed',
          )}
        >
          {generateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          {t('authority_packs.generate') || 'Generate Pack'}
        </button>
      </div>

      {/* Generate error */}
      {generateMutation.isError && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-4 text-sm text-red-700 dark:text-red-300">
          {t('app.error') || 'An error occurred'}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      )}

      {/* Error */}
      {packsError && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-red-700 dark:text-red-300">{t('app.error') || 'Error loading data'}</p>
        </div>
      )}

      {/* No building selected */}
      {!selectedBuildingId && !isLoading && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-12 text-center">
          <FileCheck className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-slate-400">
            {t('authority_packs.select_building_hint') || 'Select a building to view its authority packs'}
          </p>
        </div>
      )}

      {/* Empty */}
      {selectedBuildingId && !isLoading && !packsError && packList.length === 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-12 text-center">
          <FileCheck className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-slate-400">
            {t('authority_packs.empty') || 'No authority packs generated yet'}
          </p>
        </div>
      )}

      {/* Packs table */}
      {!isLoading && packList.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-900/50">
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('authority_packs.status') || 'Status'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('authority_packs.canton') || 'Canton'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('authority_packs.completeness') || 'Completeness'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('authority_packs.generated_at') || 'Generated'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('authority_packs.actions') || 'Actions'}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-slate-700">
                {packList.map((pack: AuthorityPackListItem) => {
                  const config = STATUS_CONFIG[pack.status] ?? STATUS_CONFIG.draft;
                  const Icon = config.icon;
                  const isGenerating = (pack.status as string) === 'generating';
                  return (
                    <tr
                      key={pack.pack_id}
                      className="hover:bg-gray-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors"
                      onClick={() => setDetailPackId(pack.pack_id)}
                    >
                      <td className="px-4 py-3">
                        <span
                          className={cn(
                            'inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium',
                            config.bgColor,
                            config.color,
                            isGenerating && 'animate-pulse',
                          )}
                        >
                          <Icon className={cn('w-3 h-3', isGenerating && 'animate-spin')} />
                          {t(`authority_packs.status_${pack.status}`) ||
                            (isGenerating ? t('authority_packs.generating') || 'Generating...' : pack.status)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-700 dark:text-slate-200">{pack.canton}</td>
                      <td className="px-4 py-3">
                        <CompletenessBar value={pack.overall_completeness} />
                      </td>
                      <td className="px-4 py-3 text-gray-500 dark:text-slate-400">
                        {formatDateTime(pack.generated_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setDetailPackId(pack.pack_id);
                            }}
                            className="inline-flex items-center gap-1 text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-medium"
                            title={t('authority_packs.view') || 'View'}
                          >
                            <Eye className="w-3.5 h-3.5" />
                            {t('authority_packs.view') || 'View'}
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              regenerateMutation.mutate(pack.building_id);
                            }}
                            disabled={regenerateMutation.isPending}
                            className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:text-slate-400 dark:hover:text-slate-200 font-medium"
                            title={t('authority_packs.regenerate') || 'Re-generate'}
                          >
                            <RefreshCw className={cn('w-3.5 h-3.5', regenerateMutation.isPending && 'animate-spin')} />
                            {t('authority_packs.regenerate') || 'Re-generate'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {detailPackId && (
        <PackDetailModal packId={detailPackId} building={selectedBuilding} onClose={() => setDetailPackId(null)} />
      )}

      {/* Generate Options Modal */}
      {showGenerateOptions && (
        <GenerateOptionsModal
          buildingCanton={selectedBuilding?.canton ?? ''}
          onGenerate={(params) => generateMutation.mutate(params)}
          onClose={() => setShowGenerateOptions(false)}
          isPending={generateMutation.isPending}
        />
      )}
    </div>
  );
}
