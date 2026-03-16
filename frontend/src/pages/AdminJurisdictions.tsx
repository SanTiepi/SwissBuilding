import { useState, useMemo, useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { jurisdictionsApi } from '@/api/jurisdictions';
import { cn } from '@/utils/formatters';
import type { Jurisdiction, RegulatoryPack, JurisdictionLevel } from '@/types';
import {
  Globe,
  Flag,
  MapPin,
  Building2,
  ChevronRight,
  ChevronDown,
  Loader2,
  AlertTriangle,
  Scale,
  Plus,
  X,
  Pencil,
  Trash2,
  Bell,
  ExternalLink,
  Search,
  CheckCircle2,
  Package,
} from 'lucide-react';

const LEVELS: JurisdictionLevel[] = ['supranational', 'country', 'region', 'commune'];

const levelIcons: Record<JurisdictionLevel, React.ElementType> = {
  supranational: Globe,
  country: Flag,
  region: MapPin,
  commune: Building2,
};

const pollutantColors: Record<string, string> = {
  asbestos: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  pcb: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  lead: 'bg-gray-200 text-gray-700 dark:bg-gray-700/50 dark:text-gray-300',
  hap: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  radon: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

const pollutantBorderColors: Record<string, string> = {
  asbestos: 'border-l-blue-500',
  pcb: 'border-l-orange-500',
  lead: 'border-l-gray-500',
  hap: 'border-l-purple-500',
  radon: 'border-l-green-500',
};

interface TreeNode {
  jurisdiction: Jurisdiction;
  children: TreeNode[];
}

function buildTree(jurisdictions: Jurisdiction[]): TreeNode[] {
  const map = new Map<string, TreeNode>();
  const roots: TreeNode[] = [];

  for (const j of jurisdictions) {
    map.set(j.id, { jurisdiction: j, children: [] });
  }

  for (const j of jurisdictions) {
    const node = map.get(j.id)!;
    if (j.parent_id && map.has(j.parent_id)) {
      map.get(j.parent_id)!.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

function JurisdictionTreeItem({
  node,
  selectedId,
  onSelect,
  depth = 0,
}: {
  node: TreeNode;
  selectedId: string | null;
  onSelect: (j: Jurisdiction) => void;
  depth?: number;
}) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(depth < 2);
  const j = node.jurisdiction;
  const Icon = levelIcons[j.level as JurisdictionLevel] || MapPin;
  const hasChildren = node.children.length > 0;
  const isSelected = selectedId === j.id;
  const packCount = j.regulatory_packs?.length ?? 0;

  return (
    <div>
      <button
        onClick={() => {
          onSelect(j);
          if (hasChildren) setExpanded(!expanded);
        }}
        className={cn(
          'w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors text-left',
          isSelected
            ? 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400 font-medium'
            : 'text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700/50',
        )}
        style={{ paddingLeft: `${depth * 16 + 12}px` }}
        title={j.name}
      >
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="w-4 h-4 flex-shrink-0 text-gray-400 dark:text-slate-500" />
          ) : (
            <ChevronRight className="w-4 h-4 flex-shrink-0 text-gray-400 dark:text-slate-500" />
          )
        ) : (
          <span className="w-4" />
        )}
        <Icon className="w-4 h-4 flex-shrink-0" />
        <span className="truncate">{j.name}</span>
        {packCount > 0 && (
          <span
            className="px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400 flex-shrink-0"
            title={`${packCount} ${t('jurisdiction.regulatory_packs') || 'packs'}`}
          >
            {packCount}
          </span>
        )}
        <span className="ml-auto text-xs text-gray-400 dark:text-slate-500 flex-shrink-0">{j.code}</span>
        {!j.is_active && (
          <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400 flex-shrink-0">
            {t('admin.inactive') || 'Inactive'}
          </span>
        )}
      </button>
      {expanded &&
        hasChildren &&
        node.children.map((child) => (
          <JurisdictionTreeItem
            key={child.jurisdiction.id}
            node={child}
            selectedId={selectedId}
            onSelect={onSelect}
            depth={depth + 1}
          />
        ))}
    </div>
  );
}

function PackRow({ pack }: { pack: RegulatoryPack }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const colorClass = pollutantColors[pack.pollutant_type] || 'bg-gray-100 text-gray-700';
  const borderClass = pollutantBorderColors[pack.pollutant_type] || 'border-l-gray-400';

  return (
    <>
      <tr
        className={cn(
          'border-l-4 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer',
          borderClass,
        )}
        onClick={() => setExpanded(!expanded)}
      >
        <td className="px-4 py-3 whitespace-nowrap">
          <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', colorClass)}>
            {t(`pollutant.${pack.pollutant_type}`) || pack.pollutant_type}
          </span>
        </td>
        <td className="px-4 py-3 text-sm text-gray-700 dark:text-slate-300 whitespace-nowrap">
          {pack.threshold_value != null ? pack.threshold_value : '-'}
        </td>
        <td className="px-4 py-3 text-sm text-gray-500 dark:text-slate-400 whitespace-nowrap">
          {pack.threshold_unit || '-'}
        </td>
        <td className="px-4 py-3 text-sm text-gray-500 dark:text-slate-400 whitespace-nowrap">
          {pack.threshold_action ? t(`regulatory_pack.action.${pack.threshold_action}`) || pack.threshold_action : '-'}
        </td>
        <td className="px-4 py-3 text-sm text-gray-500 dark:text-slate-400 whitespace-nowrap">
          {pack.risk_year_start || pack.risk_year_end
            ? `${pack.risk_year_start ?? '...'} - ${pack.risk_year_end ?? '...'}`
            : '-'}
        </td>
        <td className="px-4 py-3 text-sm text-gray-500 dark:text-slate-400 whitespace-nowrap">
          {pack.legal_reference ? (
            pack.legal_url ? (
              <a
                href={pack.legal_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                {pack.legal_reference}
                <ExternalLink className="w-3 h-3" />
              </a>
            ) : (
              pack.legal_reference
            )
          ) : (
            '-'
          )}
        </td>
        <td className="px-4 py-3 whitespace-nowrap">
          {pack.notification_required ? (
            <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
              <Bell className="w-3.5 h-3.5" />
              <span className="text-xs">
                {pack.notification_authority || ''}{' '}
                {pack.notification_delay_days != null ? `(${pack.notification_delay_days}j)` : ''}
              </span>
            </span>
          ) : (
            <span className="text-gray-400 dark:text-slate-500 text-xs">-</span>
          )}
        </td>
      </tr>
      {expanded && (
        <tr className={cn('border-l-4', borderClass)}>
          <td colSpan={7} className="px-6 py-4 bg-gray-50/50 dark:bg-slate-800/50">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <p className="font-medium text-gray-700 dark:text-slate-300 mb-1">
                  {t('regulatory_pack.version') || 'Version'}: {pack.version || '-'}
                </p>
                {pack.base_probability != null && (
                  <p className="text-gray-500 dark:text-slate-400">
                    {t('regulatory_pack.base_probability') || 'Base probability'}:{' '}
                    {(pack.base_probability * 100).toFixed(0)}%
                  </p>
                )}
                {pack.description_fr && <p className="text-gray-500 dark:text-slate-400 mt-1">{pack.description_fr}</p>}
              </div>
              <div className="space-y-2">
                {pack.work_categories_json && (
                  <div>
                    <p className="font-medium text-gray-700 dark:text-slate-300 text-xs uppercase tracking-wider mb-1">
                      {t('regulatory_pack.work_categories') || 'Work categories'}
                    </p>
                    <pre className="text-xs bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded p-2 overflow-x-auto">
                      {JSON.stringify(pack.work_categories_json, null, 2)}
                    </pre>
                  </div>
                )}
                {pack.waste_classification_json && (
                  <div>
                    <p className="font-medium text-gray-700 dark:text-slate-300 text-xs uppercase tracking-wider mb-1">
                      {t('regulatory_pack.waste_classification') || 'Waste classification'}
                    </p>
                    <pre className="text-xs bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded p-2 overflow-x-auto">
                      {JSON.stringify(pack.waste_classification_json, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

/** Auto-dismissing success toast */
function SuccessBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 3000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div className="flex items-center gap-2 px-4 py-2.5 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 rounded-lg text-sm">
      <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
      <span>{message}</span>
      <button onClick={onDismiss} className="ml-auto p-0.5 hover:bg-green-100 dark:hover:bg-green-900/40 rounded">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

export default function AdminJurisdictions() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingJurisdiction, setEditingJurisdiction] = useState<Jurisdiction | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<Jurisdiction | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    level: 'region' as JurisdictionLevel,
    parent_id: '' as string,
    country_code: '',
    is_active: true,
  });

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [levelFilter, setLevelFilter] = useState<JurisdictionLevel | ''>('');
  const [activeFilter, setActiveFilter] = useState<'all' | 'active' | 'inactive'>('all');

  // Fetch all jurisdictions (no pagination for tree view)
  const {
    data: jurisdictionsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['admin-jurisdictions'],
    queryFn: () => jurisdictionsApi.list({ size: 100 }),
  });

  const jurisdictions = useMemo(() => jurisdictionsData?.items ?? [], [jurisdictionsData]);

  // Filtered jurisdictions for the tree
  const filteredJurisdictions = useMemo(() => {
    let items = jurisdictions;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      items = items.filter((j) => j.name.toLowerCase().includes(q) || j.code.toLowerCase().includes(q));
    }
    if (levelFilter) {
      items = items.filter((j) => j.level === levelFilter);
    }
    if (activeFilter === 'active') {
      items = items.filter((j) => j.is_active);
    } else if (activeFilter === 'inactive') {
      items = items.filter((j) => !j.is_active);
    }
    return items;
  }, [jurisdictions, searchQuery, levelFilter, activeFilter]);

  const tree = useMemo(() => buildTree(filteredJurisdictions), [filteredJurisdictions]);

  // Summary stats
  const stats = useMemo(() => {
    const total = jurisdictions.length;
    const active = jurisdictions.filter((j) => j.is_active).length;
    const inactive = total - active;
    const totalPacks = jurisdictions.reduce((sum, j) => sum + (j.regulatory_packs?.length ?? 0), 0);
    return { total, active, inactive, totalPacks };
  }, [jurisdictions]);

  // Fetch selected jurisdiction detail with packs
  const { data: selectedJurisdiction } = useQuery({
    queryKey: ['admin-jurisdiction-detail', selectedId],
    queryFn: () => jurisdictionsApi.get(selectedId!),
    enabled: !!selectedId,
  });

  const dismissSuccess = useCallback(() => setSuccessMessage(null), []);

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) =>
      jurisdictionsApi.create({
        ...data,
        parent_id: data.parent_id || null,
        country_code: data.country_code || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-jurisdictions'] });
      setSuccessMessage(t('jurisdiction.created_success') || 'Jurisdiction created successfully');
      closeModal();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: typeof formData }) =>
      jurisdictionsApi.update(id, {
        ...data,
        parent_id: data.parent_id || null,
        country_code: data.country_code || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-jurisdictions'] });
      if (selectedId) queryClient.invalidateQueries({ queryKey: ['admin-jurisdiction-detail', selectedId] });
      setSuccessMessage(t('jurisdiction.updated_success') || 'Jurisdiction updated successfully');
      closeModal();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => jurisdictionsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-jurisdictions'] });
      if (deleteConfirm?.id === selectedId) setSelectedId(null);
      setDeleteConfirm(null);
      setSuccessMessage(t('jurisdiction.deleted_success') || 'Jurisdiction deleted successfully');
    },
  });

  const closeModal = () => {
    setShowCreateModal(false);
    setEditingJurisdiction(null);
    setFormData({ code: '', name: '', level: 'region', parent_id: '', country_code: '', is_active: true });
    createMutation.reset();
    updateMutation.reset();
  };

  const openCreate = () => {
    setFormData({
      code: '',
      name: '',
      level: 'region',
      parent_id: selectedId || '',
      country_code: '',
      is_active: true,
    });
    setEditingJurisdiction(null);
    setShowCreateModal(true);
  };

  const openEdit = (j: Jurisdiction) => {
    setEditingJurisdiction(j);
    setFormData({
      code: j.code,
      name: j.name,
      level: j.level,
      parent_id: j.parent_id || '',
      country_code: j.country_code || '',
      is_active: j.is_active,
    });
    setShowCreateModal(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingJurisdiction) {
      updateMutation.mutate({ id: editingJurisdiction.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const mutationError = createMutation.error || updateMutation.error;
  const hasActiveFilters = searchQuery.trim() !== '' || levelFilter !== '' || activeFilter !== 'all';

  if (user?.role !== 'admin') {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-500 dark:text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('admin.access_denied') || 'Access denied'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('jurisdiction.title') || 'Jurisdictions & Regulatory Packs'}
          </h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {jurisdictionsData?.total ?? 0} {t('jurisdiction.total') || 'jurisdictions'}
          </p>
        </div>
        <button
          onClick={openCreate}
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          {t('jurisdiction.add') || 'Add jurisdiction'}
        </button>
      </div>

      {/* Success banner */}
      {successMessage && <SuccessBanner message={successMessage} onDismiss={dismissSuccess} />}

      {/* Summary stats bar */}
      {!isLoading && !error && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3" data-testid="stats-bar">
          <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-3">
            <p className="text-xs text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {t('jurisdiction.stats.total') || 'Total'}
            </p>
            <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">{stats.total}</p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-3">
            <p className="text-xs text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {t('admin.active') || 'Active'}
            </p>
            <p className="text-xl font-bold text-green-600 dark:text-green-400 mt-1">{stats.active}</p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-3">
            <p className="text-xs text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {t('admin.inactive') || 'Inactive'}
            </p>
            <p className="text-xl font-bold text-gray-500 dark:text-slate-400 mt-1">{stats.inactive}</p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 px-4 py-3">
            <p className="text-xs text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {t('jurisdiction.stats.packs') || 'Reg. Packs'}
            </p>
            <p className="text-xl font-bold text-blue-600 dark:text-blue-400 mt-1">{stats.totalPacks}</p>
          </div>
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      ) : error ? (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
          <AlertTriangle className="w-8 h-8 text-red-500 dark:text-red-400 mx-auto mb-2" />
          <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left panel - Tree */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50">
                <h2 className="text-sm font-medium text-gray-700 dark:text-slate-300">
                  {t('jurisdiction.hierarchy') || 'Hierarchy'}
                </h2>
              </div>

              {/* Search & filter bar */}
              <div className="px-3 py-3 border-b border-gray-100 dark:border-slate-700/50 space-y-2">
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-slate-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder={t('jurisdiction.search_placeholder') || 'Search name or code...'}
                    className="w-full pl-8 pr-3 py-1.5 border border-gray-200 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-red-500"
                    data-testid="jurisdiction-search"
                  />
                </div>
                <div className="flex gap-2">
                  <select
                    value={levelFilter}
                    onChange={(e) => setLevelFilter(e.target.value as JurisdictionLevel | '')}
                    className="flex-1 px-2 py-1.5 border border-gray-200 dark:border-slate-600 rounded-lg text-xs bg-white dark:bg-slate-700 text-gray-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-red-500"
                    data-testid="level-filter"
                  >
                    <option value="">{t('jurisdiction.all_levels') || 'All levels'}</option>
                    {LEVELS.map((l) => (
                      <option key={l} value={l}>
                        {t(`jurisdiction.level.${l}`) || l}
                      </option>
                    ))}
                  </select>
                  <select
                    value={activeFilter}
                    onChange={(e) => setActiveFilter(e.target.value as 'all' | 'active' | 'inactive')}
                    className="flex-1 px-2 py-1.5 border border-gray-200 dark:border-slate-600 rounded-lg text-xs bg-white dark:bg-slate-700 text-gray-700 dark:text-slate-300 focus:outline-none focus:ring-2 focus:ring-red-500"
                    data-testid="active-filter"
                  >
                    <option value="all">{t('jurisdiction.all_statuses') || 'All statuses'}</option>
                    <option value="active">{t('admin.active') || 'Active'}</option>
                    <option value="inactive">{t('admin.inactive') || 'Inactive'}</option>
                  </select>
                </div>
                {hasActiveFilters && (
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {filteredJurisdictions.length} / {jurisdictions.length}{' '}
                    {t('jurisdiction.filtered_count') || 'shown'}
                  </p>
                )}
              </div>

              <div className="p-2 max-h-[calc(100vh-380px)] overflow-y-auto">
                {tree.length === 0 ? (
                  <div className="text-center py-8">
                    <Scale className="w-10 h-10 text-gray-300 dark:text-slate-600 mx-auto mb-2" />
                    <p className="text-sm text-gray-500 dark:text-slate-400">
                      {hasActiveFilters
                        ? t('jurisdiction.no_results') || 'No jurisdictions match your filters'
                        : t('jurisdiction.empty') || 'No jurisdictions yet'}
                    </p>
                  </div>
                ) : (
                  tree.map((node) => (
                    <JurisdictionTreeItem
                      key={node.jurisdiction.id}
                      node={node}
                      selectedId={selectedId}
                      onSelect={(j) => setSelectedId(j.id)}
                    />
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Right panel - Detail */}
          <div className="lg:col-span-2">
            {selectedJurisdiction ? (
              <div className="space-y-6">
                {/* Jurisdiction info card */}
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <h2 className="text-lg font-bold text-gray-900 dark:text-white">{selectedJurisdiction.name}</h2>
                      <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-gray-500 dark:text-slate-400">
                        <span>
                          {t('jurisdiction.field.code') || 'Code'}: {selectedJurisdiction.code}
                        </span>
                        <span>
                          {t('jurisdiction.field.level') || 'Level'}:{' '}
                          {t(`jurisdiction.level.${selectedJurisdiction.level}`) || selectedJurisdiction.level}
                        </span>
                        {selectedJurisdiction.country_code && (
                          <span>
                            {t('jurisdiction.field.country_code') || 'Country'}: {selectedJurisdiction.country_code}
                          </span>
                        )}
                        <span
                          className={cn(
                            'px-2 py-0.5 text-xs font-medium rounded-full',
                            selectedJurisdiction.is_active
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                              : 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
                          )}
                        >
                          {selectedJurisdiction.is_active
                            ? t('admin.active') || 'Active'
                            : t('admin.inactive') || 'Inactive'}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => openEdit(selectedJurisdiction)}
                        title={t('jurisdiction.edit') || 'Edit'}
                        className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(selectedJurisdiction)}
                        title={t('jurisdiction.delete') || 'Delete'}
                        className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Regulatory packs table */}
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50 flex items-center justify-between">
                    <h3 className="text-sm font-medium text-gray-700 dark:text-slate-300 flex items-center gap-2">
                      <Package className="w-4 h-4" />
                      {t('jurisdiction.regulatory_packs') || 'Regulatory Packs'} (
                      {selectedJurisdiction.regulatory_packs?.length ?? 0})
                    </h3>
                  </div>
                  {selectedJurisdiction.regulatory_packs && selectedJurisdiction.regulatory_packs.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-200 dark:border-slate-700 bg-gray-50/50 dark:bg-slate-800/30">
                            <th className="text-left px-4 py-2.5 font-medium text-gray-500 dark:text-slate-400">
                              {t('pollutant.label') || 'Pollutant'}
                            </th>
                            <th className="text-left px-4 py-2.5 font-medium text-gray-500 dark:text-slate-400">
                              {t('regulatory_pack.threshold') || 'Threshold'}
                            </th>
                            <th className="text-left px-4 py-2.5 font-medium text-gray-500 dark:text-slate-400">
                              {t('regulatory_pack.unit') || 'Unit'}
                            </th>
                            <th className="text-left px-4 py-2.5 font-medium text-gray-500 dark:text-slate-400">
                              {t('regulatory_pack.action') || 'Action'}
                            </th>
                            <th className="text-left px-4 py-2.5 font-medium text-gray-500 dark:text-slate-400">
                              {t('regulatory_pack.risk_years') || 'Risk Years'}
                            </th>
                            <th className="text-left px-4 py-2.5 font-medium text-gray-500 dark:text-slate-400">
                              {t('regulatory_pack.legal_reference') || 'Legal Ref'}
                            </th>
                            <th className="text-left px-4 py-2.5 font-medium text-gray-500 dark:text-slate-400">
                              {t('regulatory_pack.notification') || 'Notification'}
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                          {selectedJurisdiction.regulatory_packs.map((pack) => (
                            <PackRow key={pack.id} pack={pack} />
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-8 text-center">
                      <Scale className="w-10 h-10 text-gray-300 dark:text-slate-600 mx-auto mb-2" />
                      <p className="text-sm text-gray-500 dark:text-slate-400">
                        {t('regulatory_pack.empty') || 'No regulatory packs'}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-12 text-center">
                <Scale className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
                <p className="text-gray-500 dark:text-slate-400 text-sm">
                  {t('jurisdiction.select_prompt') ||
                    'Select a jurisdiction from the tree to view its regulatory packs'}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create/Edit Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                {editingJurisdiction
                  ? t('jurisdiction.edit') || 'Edit jurisdiction'
                  : t('jurisdiction.add') || 'Add jurisdiction'}
              </h2>
              <button
                onClick={closeModal}
                className="p-1 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
                aria-label={t('form.close')}
              >
                <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
              </button>
            </div>

            {/* Mutation error */}
            {mutationError && (
              <div className="mb-4 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-400 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{(mutationError as Error).message || t('app.error') || 'An error occurred'}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('jurisdiction.field.code') || 'Code'} *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                    placeholder="CH-VD"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('jurisdiction.field.name') || 'Name'} *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Canton de Vaud"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('jurisdiction.field.level') || 'Level'} *
                  </label>
                  <select
                    required
                    value={formData.level}
                    onChange={(e) => setFormData({ ...formData, level: e.target.value as JurisdictionLevel })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    {LEVELS.map((l) => (
                      <option key={l} value={l}>
                        {t(`jurisdiction.level.${l}`) || l}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('jurisdiction.field.country_code') || 'Country code'}
                  </label>
                  <input
                    type="text"
                    value={formData.country_code}
                    onChange={(e) => setFormData({ ...formData, country_code: e.target.value })}
                    placeholder="CH"
                    maxLength={5}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('jurisdiction.field.parent') || 'Parent jurisdiction'}
                  </label>
                  <select
                    value={formData.parent_id}
                    onChange={(e) => setFormData({ ...formData, parent_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    <option value="">{t('jurisdiction.no_parent') || '-- No parent --'}</option>
                    {jurisdictions.map((j) => (
                      <option key={j.id} value={j.id}>
                        {j.name} ({j.code})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label className="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={formData.is_active}
                      onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                      className="w-4 h-4 rounded border-gray-300 dark:border-slate-600 text-red-600 focus:ring-red-500 dark:bg-slate-700"
                    />
                    {t('jurisdiction.field.is_active') || 'Active'}
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
                >
                  {t('form.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
                >
                  {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                  {editingJurisdiction ? t('form.save') || 'Save' : t('form.create') || 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-sm mx-4 p-6">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
              {t('jurisdiction.delete') || 'Delete jurisdiction'}
            </h2>
            <p className="text-sm text-gray-600 dark:text-slate-300 mb-4">
              {t('jurisdiction.confirm_delete') || 'Are you sure you want to delete'}{' '}
              <span className="font-semibold">{deleteConfirm.name}</span>?
            </p>
            {/* Delete mutation error */}
            {deleteMutation.error && (
              <div className="mb-4 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-400 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{(deleteMutation.error as Error).message || t('app.error') || 'An error occurred'}</span>
              </div>
            )}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
              >
                {t('form.cancel')}
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteConfirm.id)}
                disabled={deleteMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
              >
                {deleteMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                {t('form.delete') || 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
