import { useState, useMemo, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuth } from '@/hooks/useAuth';
import { zonesApi } from '@/api/zones';
import { elementsApi } from '@/api/elements';
import { materialsApi } from '@/api/materials';
import { plansApi } from '@/api/plans';
import { toast } from '@/store/toastStore';
import { RoleGate } from '@/components/RoleGate';
import { PollutantBadge } from '@/components/PollutantBadge';
import { ProofHeatmapOverlay } from '@/components/ProofHeatmapOverlay';
import { BuildingSubNav } from '@/components/BuildingSubNav';
import type { Zone, ZoneType, BuildingElement, ElementType, Material, MaterialType, PollutantType } from '@/types';
import {
  ArrowLeft,
  ChevronRight,
  ChevronDown,
  Plus,
  Trash2,
  Loader2,
  Layers,
  Box,
  Droplets,
  Building2,
  Home,
  Eye,
  EyeOff,
  FileImage,
  Search,
  ChevronsDown,
  ChevronsUp,
  AlertTriangle,
  BarChart3,
  Link as LinkIcon,
  ArrowUpRight,
  PipetteIcon,
  PaintBucket,
  DoorOpen,
  Square,
  CircleDot,
  Columns,
  Minus,
  Grid3x3,
} from 'lucide-react';

/* ---------- Constants ---------- */

const ZONE_ICONS: Record<string, React.ElementType> = {
  floor: Layers,
  room: Home,
  facade: Building2,
  roof: ArrowUpRight,
  basement: Box,
  staircase: Layers,
  technical_room: Droplets,
  parking: Grid3x3,
  other: Box,
};

const ELEMENT_ICONS: Record<string, React.ElementType> = {
  wall: Square,
  floor: Layers,
  ceiling: Minus,
  pipe: PipetteIcon,
  insulation: Columns,
  coating: PaintBucket,
  window: Grid3x3,
  door: DoorOpen,
  duct: CircleDot,
  structural: Building2,
  other: Box,
};

const CONDITION_COLORS: Record<string, { bg: string; text: string; darkBg: string; darkText: string }> = {
  good: {
    bg: 'bg-emerald-100',
    text: 'text-emerald-700',
    darkBg: 'dark:bg-emerald-950/40',
    darkText: 'dark:text-emerald-300',
  },
  fair: { bg: 'bg-blue-100', text: 'text-blue-700', darkBg: 'dark:bg-blue-950/40', darkText: 'dark:text-blue-300' },
  poor: { bg: 'bg-amber-100', text: 'text-amber-700', darkBg: 'dark:bg-amber-950/40', darkText: 'dark:text-amber-300' },
  critical: { bg: 'bg-red-100', text: 'text-red-700', darkBg: 'dark:bg-red-950/40', darkText: 'dark:text-red-300' },
  unknown: { bg: 'bg-gray-100', text: 'text-gray-600', darkBg: 'dark:bg-slate-800', darkText: 'dark:text-slate-400' },
};

const CONDITION_BAR_COLORS: Record<string, string> = {
  good: 'bg-emerald-500',
  fair: 'bg-blue-500',
  poor: 'bg-amber-500',
  critical: 'bg-red-500',
  unknown: 'bg-gray-400 dark:bg-slate-600',
};

const ZONE_TYPES: ZoneType[] = [
  'floor',
  'room',
  'facade',
  'roof',
  'basement',
  'staircase',
  'technical_room',
  'parking',
  'other',
];
const ELEMENT_TYPES: ElementType[] = [
  'wall',
  'floor',
  'ceiling',
  'pipe',
  'insulation',
  'coating',
  'window',
  'door',
  'duct',
  'structural',
  'other',
];
const MATERIAL_TYPES: MaterialType[] = [
  'concrete',
  'fiber_cement',
  'plaster',
  'paint',
  'adhesive',
  'insulation_material',
  'sealant',
  'flooring',
  'tile',
  'wood',
  'metal',
  'glass',
  'bitumen',
  'mortar',
  'other',
];

/* ---------- Tree helpers ---------- */

interface ZoneTreeNode extends Zone {
  children: ZoneTreeNode[];
  depth: number;
}

function buildZoneTree(zones: Zone[]): ZoneTreeNode[] {
  const map = new Map<string, ZoneTreeNode>();
  const roots: ZoneTreeNode[] = [];

  for (const z of zones) {
    map.set(z.id, { ...z, children: [], depth: 0 });
  }

  for (const node of map.values()) {
    if (node.parent_zone_id && map.has(node.parent_zone_id)) {
      const parent = map.get(node.parent_zone_id)!;
      node.depth = parent.depth + 1;
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

function flattenTree(nodes: ZoneTreeNode[]): ZoneTreeNode[] {
  const result: ZoneTreeNode[] = [];
  function walk(list: ZoneTreeNode[]) {
    for (const n of list) {
      result.push(n);
      walk(n.children);
    }
  }
  walk(nodes);
  return result;
}

function getAncestorChain(zones: Zone[], zoneId: string): Zone[] {
  const map = new Map(zones.map((z) => [z.id, z]));
  const chain: Zone[] = [];
  let current = map.get(zoneId);
  while (current) {
    chain.unshift(current);
    current = current.parent_zone_id ? map.get(current.parent_zone_id) : undefined;
  }
  return chain;
}

function collectAllIdsWithChildren(nodes: ZoneTreeNode[]): Set<string> {
  const ids = new Set<string>();
  function walk(list: ZoneTreeNode[]) {
    for (const n of list) {
      if (n.children.length > 0) {
        ids.add(n.id);
      }
      walk(n.children);
    }
  }
  walk(nodes);
  return ids;
}

/* ---------- Main Component ---------- */

export default function BuildingExplorer() {
  const { t } = useTranslation();
  const { buildingId } = useParams<{ buildingId: string }>();
  useAuth();
  const queryClient = useQueryClient();

  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [expandedZones, setExpandedZones] = useState<Set<string>>(new Set());
  const [expandedElements, setExpandedElements] = useState<Set<string>>(new Set());
  const [showZoneForm, setShowZoneForm] = useState(false);
  const [showElementForm, setShowElementForm] = useState(false);
  const [showMaterialForm, setShowMaterialForm] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [heatmapPlanIds, setHeatmapPlanIds] = useState<Set<string>>(new Set());
  const [treeSearch, setTreeSearch] = useState('');

  const toggleHeatmap = (planId: string) => {
    setHeatmapPlanIds((prev) => {
      const next = new Set(prev);
      if (next.has(planId)) next.delete(planId);
      else next.add(planId);
      return next;
    });
  };

  // Zone form state
  const [zoneName, setZoneName] = useState('');
  const [zoneType, setZoneType] = useState<ZoneType>('room');
  const [parentZoneId, setParentZoneId] = useState<string>('');

  // Element form state
  const [elementName, setElementName] = useState('');
  const [elementType, setElementType] = useState<ElementType>('wall');

  // Material form state
  const [materialName, setMaterialName] = useState('');
  const [materialType, setMaterialType] = useState<MaterialType>('concrete');

  // Fetch zones
  const {
    data: zonesData,
    isLoading: zonesLoading,
    isError: zonesError,
  } = useQuery({
    queryKey: ['zones', buildingId],
    queryFn: () => zonesApi.list(buildingId!, { size: 200 }),
    enabled: !!buildingId,
  });
  const zones: Zone[] = useMemo(() => zonesData?.items ?? [], [zonesData]);

  // Build tree
  const zoneTree = useMemo(() => buildZoneTree(zones), [zones]);
  const allFlat = useMemo(() => flattenTree(zoneTree), [zoneTree]);
  const expandableIds = useMemo(() => collectAllIdsWithChildren(zoneTree), [zoneTree]);

  // Filter tree by search
  const filteredTree = useMemo(() => {
    if (!treeSearch.trim()) return allFlat;
    const term = treeSearch.toLowerCase();
    // Show matching nodes + their ancestors
    const matchingIds = new Set<string>();
    for (const node of allFlat) {
      if (
        node.name.toLowerCase().includes(term) ||
        (t(`zone_type.${node.zone_type}`) || node.zone_type).toLowerCase().includes(term)
      ) {
        matchingIds.add(node.id);
        // add ancestors
        const chain = getAncestorChain(zones, node.id);
        for (const a of chain) matchingIds.add(a.id);
      }
    }
    return allFlat.filter((n) => matchingIds.has(n.id));
  }, [allFlat, treeSearch, zones, t]);

  // Visible nodes: show a node if it's a root or all ancestors are expanded
  const visibleNodes = useMemo(() => {
    if (treeSearch.trim()) return filteredTree; // show all matches flat-ish but indented
    return filteredTree.filter((node) => {
      if (!node.parent_zone_id) return true;
      // Check all ancestors are expanded
      const chain = getAncestorChain(zones, node.id);
      // chain includes the node itself; check all parents
      for (let i = 0; i < chain.length - 1; i++) {
        if (!expandedZones.has(chain[i].id)) return false;
      }
      return true;
    });
  }, [filteredTree, expandedZones, zones, treeSearch]);

  const toggleZoneExpand = useCallback((zoneId: string) => {
    setExpandedZones((prev) => {
      const next = new Set(prev);
      if (next.has(zoneId)) next.delete(zoneId);
      else next.add(zoneId);
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    setExpandedZones(new Set(expandableIds));
  }, [expandableIds]);

  const collapseAll = useCallback(() => {
    setExpandedZones(new Set());
  }, []);

  // Fetch elements for selected zone
  const { data: elements, isLoading: elementsLoading } = useQuery({
    queryKey: ['elements', buildingId, selectedZoneId],
    queryFn: () => elementsApi.list(buildingId!, selectedZoneId!),
    enabled: !!buildingId && !!selectedZoneId,
  });

  // Fetch plans for building
  const { data: plans } = useQuery({
    queryKey: ['plans', buildingId],
    queryFn: () => plansApi.list(buildingId!),
    enabled: !!buildingId,
  });

  // Mutations
  const createZone = useMutation({
    mutationFn: (data: Partial<Zone>) => zonesApi.create(buildingId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones', buildingId] });
      toast(t('explorer.zone_created') || 'Zone created', 'success');
      setShowZoneForm(false);
      setZoneName('');
      setParentZoneId('');
    },
    onError: (err: any) =>
      toast(err?.response?.data?.detail || t('explorer.zone_create_error') || 'Error creating zone', 'error'),
  });

  const deleteZone = useMutation({
    mutationFn: (zoneId: string) => zonesApi.delete(buildingId!, zoneId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones', buildingId] });
      if (selectedZoneId === deleteConfirm) setSelectedZoneId(null);
      toast(t('explorer.zone_deleted') || 'Zone deleted', 'success');
      setDeleteConfirm(null);
    },
    onError: (err: any) =>
      toast(err?.response?.data?.detail || t('explorer.zone_delete_error') || 'Error deleting zone', 'error'),
  });

  const createElement = useMutation({
    mutationFn: (data: Partial<BuildingElement>) => elementsApi.create(buildingId!, selectedZoneId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['elements', buildingId, selectedZoneId] });
      queryClient.invalidateQueries({ queryKey: ['zones', buildingId] });
      toast(t('explorer.element_created') || 'Element created', 'success');
      setShowElementForm(false);
      setElementName('');
    },
    onError: (err: any) =>
      toast(err?.response?.data?.detail || t('explorer.element_create_error') || 'Error creating element', 'error'),
  });

  const deleteElement = useMutation({
    mutationFn: (elementId: string) => elementsApi.delete(buildingId!, selectedZoneId!, elementId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['elements', buildingId, selectedZoneId] });
      queryClient.invalidateQueries({ queryKey: ['zones', buildingId] });
      toast(t('explorer.element_deleted') || 'Element deleted', 'success');
      setDeleteConfirm(null);
    },
    onError: (err: any) =>
      toast(err?.response?.data?.detail || t('explorer.element_delete_error') || 'Error deleting element', 'error'),
  });

  const createMaterial = useMutation({
    mutationFn: ({ elementId, data }: { elementId: string; data: Partial<Material> }) =>
      materialsApi.create(buildingId!, selectedZoneId!, elementId, data),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['materials', buildingId, selectedZoneId, vars.elementId] });
      queryClient.invalidateQueries({ queryKey: ['elements', buildingId, selectedZoneId] });
      toast(t('explorer.material_created') || 'Material created', 'success');
      setShowMaterialForm(null);
      setMaterialName('');
    },
    onError: (err: any) =>
      toast(err?.response?.data?.detail || t('explorer.material_create_error') || 'Error creating material', 'error'),
  });

  const deleteMaterial = useMutation({
    mutationFn: ({ elementId, materialId }: { elementId: string; materialId: string }) =>
      materialsApi.delete(buildingId!, selectedZoneId!, elementId, materialId),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['materials', buildingId, selectedZoneId, vars.elementId] });
      queryClient.invalidateQueries({ queryKey: ['elements', buildingId, selectedZoneId] });
      toast(t('explorer.material_deleted') || 'Material deleted', 'success');
      setDeleteConfirm(null);
    },
    onError: (err: any) =>
      toast(err?.response?.data?.detail || t('explorer.material_delete_error') || 'Error deleting material', 'error'),
  });

  const toggleElement = (elementId: string) => {
    setExpandedElements((prev) => {
      const next = new Set(prev);
      if (next.has(elementId)) next.delete(elementId);
      else next.add(elementId);
      return next;
    });
  };

  const selectedZone = zones.find((z) => z.id === selectedZoneId);

  // Breadcrumb
  const breadcrumb = useMemo(() => {
    if (!selectedZoneId) return [];
    return getAncestorChain(zones, selectedZoneId);
  }, [zones, selectedZoneId]);

  // Summary stats
  const summaryStats = useMemo(() => {
    const totalZones = zones.length;
    const totalElements = zones.reduce((sum, z) => sum + (z.elements_count || 0), 0);
    // We can only count materials from loaded elements
    const totalMaterials = (elements ?? []).reduce((sum, e) => sum + (e.materials_count || 0), 0);
    return { totalZones, totalElements, totalMaterials };
  }, [zones, elements]);

  // Condition distribution from loaded elements
  const conditionDistribution = useMemo(() => {
    if (!elements || elements.length === 0) return null;
    const dist: Record<string, number> = { good: 0, fair: 0, poor: 0, critical: 0, unknown: 0 };
    for (const el of elements) {
      const cond = el.condition || 'unknown';
      dist[cond] = (dist[cond] || 0) + 1;
    }
    return dist;
  }, [elements]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950">
      {/* Header */}
      <div className="bg-white dark:bg-slate-900 border-b border-gray-200 dark:border-slate-800 px-6 py-4">
        <div className="flex items-center gap-4">
          <Link
            to={`/buildings/${buildingId}`}
            className="text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            {t('explorer.title') || 'Building Explorer'}
          </h1>
        </div>
        <div className="mt-3">
          <BuildingSubNav buildingId={buildingId!} />
        </div>
      </div>

      <div className="flex h-[calc(100vh-73px)]">
        {/* Left panel: Zone tree */}
        <div className="w-80 flex-shrink-0 border-r border-gray-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-y-auto flex flex-col">
          {/* Zone panel header */}
          <div className="p-4 border-b border-gray-100 dark:border-slate-800 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300 uppercase tracking-wider">
              {t('explorer.zones') || 'Zones'}
            </h2>
            <div className="flex items-center gap-1">
              <button
                onClick={expandAll}
                className="p-1 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 rounded"
                title={t('explorer.expand_all') || 'Expand all'}
              >
                <ChevronsDown className="w-4 h-4" />
              </button>
              <button
                onClick={collapseAll}
                className="p-1 text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300 rounded"
                title={t('explorer.collapse_all') || 'Collapse all'}
              >
                <ChevronsUp className="w-4 h-4" />
              </button>
              <RoleGate allowedRoles={['admin', 'diagnostician']}>
                <button
                  onClick={() => setShowZoneForm(!showZoneForm)}
                  className="p-1 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 rounded"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </RoleGate>
            </div>
          </div>

          {/* Search within tree */}
          <div className="px-3 py-2 border-b border-gray-100 dark:border-slate-800">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 dark:text-slate-500" />
              <input
                type="text"
                value={treeSearch}
                onChange={(e) => setTreeSearch(e.target.value)}
                placeholder={t('explorer.search_zones') || 'Search zones...'}
                className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 dark:border-slate-700 dark:bg-slate-800 dark:text-white rounded focus:ring-1 focus:ring-red-500 focus:border-red-500"
              />
            </div>
          </div>

          {/* Zone create form */}
          {showZoneForm && (
            <div className="p-3 border-b border-gray-100 dark:border-slate-800 bg-gray-50 dark:bg-slate-950/40 space-y-2">
              <input
                type="text"
                value={zoneName}
                onChange={(e) => setZoneName(e.target.value)}
                placeholder={t('zone.name') || 'Zone name'}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white rounded focus:ring-1 focus:ring-red-500 focus:border-red-500"
              />
              <select
                value={zoneType}
                onChange={(e) => setZoneType(e.target.value as ZoneType)}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white rounded"
              >
                {ZONE_TYPES.map((zt) => (
                  <option key={zt} value={zt}>
                    {t(`zone_type.${zt}`) || zt}
                  </option>
                ))}
              </select>
              <select
                value={parentZoneId}
                onChange={(e) => setParentZoneId(e.target.value)}
                className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white rounded"
              >
                <option value="">{t('explorer.no_parent') || 'No parent (root zone)'}</option>
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name}
                  </option>
                ))}
              </select>
              <button
                onClick={() =>
                  createZone.mutate({
                    name: zoneName,
                    zone_type: zoneType,
                    parent_zone_id: parentZoneId || null,
                  })
                }
                disabled={!zoneName.trim() || createZone.isPending}
                className="w-full px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
              >
                {createZone.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                ) : (
                  t('explorer.create') || 'Create'
                )}
              </button>
            </div>
          )}

          {/* Zone tree */}
          <div className="flex-1 overflow-y-auto">
            {zonesLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-5 h-5 animate-spin text-gray-400 dark:text-slate-500" />
              </div>
            ) : zonesError ? (
              <div className="p-4 text-sm text-red-600 dark:text-red-300 bg-red-50 dark:bg-red-950/30 rounded m-2">
                {t('app.error') || 'An error occurred'}
              </div>
            ) : zones.length === 0 ? (
              <p className="p-4 text-sm text-gray-500 dark:text-slate-400">
                {t('explorer.no_zones') || 'No zones yet.'}
              </p>
            ) : visibleNodes.length === 0 ? (
              <p className="p-4 text-sm text-gray-500 dark:text-slate-400">
                {t('explorer.no_search_results') || 'No matching zones.'}
              </p>
            ) : (
              <ul>
                {visibleNodes.map((node) => {
                  const Icon = ZONE_ICONS[node.zone_type] || Box;
                  const isSelected = node.id === selectedZoneId;
                  const hasChildren = node.children.length > 0;
                  const isExpanded = expandedZones.has(node.id);

                  return (
                    <li key={node.id}>
                      <button
                        onClick={() => {
                          setSelectedZoneId(node.id);
                          // auto-expand ancestors
                          const chain = getAncestorChain(zones, node.id);
                          setExpandedZones((prev) => {
                            const next = new Set(prev);
                            for (const a of chain) next.add(a.id);
                            return next;
                          });
                        }}
                        className={`w-full flex items-center gap-2 pr-3 py-2.5 text-left text-sm hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors ${
                          isSelected ? 'bg-red-50 dark:bg-red-950/20 border-l-2 border-red-600' : ''
                        }`}
                        style={{ paddingLeft: `${12 + node.depth * 16}px` }}
                      >
                        {/* Expand/collapse toggle */}
                        {hasChildren ? (
                          <span
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleZoneExpand(node.id);
                            }}
                            className="p-0.5 rounded hover:bg-gray-200 dark:hover:bg-slate-700 flex-shrink-0"
                          >
                            {isExpanded ? (
                              <ChevronDown className="w-3.5 h-3.5 text-gray-400 dark:text-slate-500" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5 text-gray-400 dark:text-slate-500" />
                            )}
                          </span>
                        ) : (
                          <span className="w-[22px] flex-shrink-0" />
                        )}

                        <Icon className="w-4 h-4 text-gray-400 dark:text-slate-500 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-gray-900 dark:text-white truncate">{node.name}</p>
                          <p className="text-xs text-gray-500 dark:text-slate-400">
                            {t(`zone_type.${node.zone_type}`) || node.zone_type}
                          </p>
                        </div>
                        {/* Element count badge */}
                        {node.elements_count > 0 && (
                          <span className="flex-shrink-0 px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-400">
                            {node.elements_count}
                          </span>
                        )}
                        <RoleGate allowedRoles={['admin', 'diagnostician']}>
                          <span
                            onClick={(e) => {
                              e.stopPropagation();
                              if (deleteConfirm === node.id) deleteZone.mutate(node.id);
                              else setDeleteConfirm(node.id);
                            }}
                            className={`p-1 rounded flex-shrink-0 ${
                              deleteConfirm === node.id
                                ? 'text-red-600 bg-red-100 dark:bg-red-950/40'
                                : 'text-gray-400 dark:text-slate-500 hover:text-red-500'
                            }`}
                            title={
                              deleteConfirm === node.id
                                ? t('explorer.confirm_delete') || 'Click again to confirm'
                                : t('explorer.delete') || 'Delete'
                            }
                          >
                            <Trash2 className="w-3 h-3" />
                          </span>
                        </RoleGate>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* Zone count footer */}
          {!zonesLoading && zones.length > 0 && (
            <div className="px-4 py-2 border-t border-gray-100 dark:border-slate-800 text-xs text-gray-400 dark:text-slate-500">
              {zones.length} {t('explorer.zones') || 'Zones'}
            </div>
          )}
        </div>

        {/* Right panel: Elements & Materials */}
        <div className="flex-1 overflow-y-auto">
          {!selectedZoneId ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 dark:text-slate-500">
              <Layers className="w-12 h-12 mb-3" />
              <p className="text-sm">{t('explorer.select_zone') || 'Select a zone to explore its elements'}</p>
            </div>
          ) : (
            <div className="p-6">
              {/* Breadcrumb */}
              {breadcrumb.length > 0 && (
                <nav className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-slate-400 mb-4 flex-wrap">
                  <Link to={`/buildings/${buildingId}`} className="hover:text-gray-700 dark:hover:text-slate-200">
                    {t('explorer.building') || 'Building'}
                  </Link>
                  {breadcrumb.map((z, idx) => (
                    <span key={z.id} className="flex items-center gap-1.5">
                      <ChevronRight className="w-3 h-3" />
                      <button
                        onClick={() => setSelectedZoneId(z.id)}
                        className={`hover:text-gray-700 dark:hover:text-slate-200 ${
                          idx === breadcrumb.length - 1 ? 'font-semibold text-gray-900 dark:text-white' : ''
                        }`}
                      >
                        {z.name}
                      </button>
                    </span>
                  ))}
                </nav>
              )}

              {/* Summary header */}
              <SummaryHeader
                t={t}
                totalZones={summaryStats.totalZones}
                totalElements={summaryStats.totalElements}
                totalMaterials={summaryStats.totalMaterials}
                conditionDistribution={conditionDistribution}
              />

              {/* Zone header */}
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-lg font-bold text-gray-900 dark:text-white">{selectedZone?.name}</h2>
                  <p className="text-sm text-gray-500 dark:text-slate-400">
                    {t(`zone_type.${selectedZone?.zone_type}`) || selectedZone?.zone_type}
                    {selectedZone?.floor_number != null &&
                      ` — ${t('zone.floor') || 'Floor'} ${selectedZone.floor_number}`}
                  </p>
                </div>
                <RoleGate allowedRoles={['admin', 'diagnostician']}>
                  <button
                    onClick={() => setShowElementForm(!showElementForm)}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                  >
                    <Plus className="w-4 h-4" />
                    {t('explorer.add_element') || 'Add Element'}
                  </button>
                </RoleGate>
              </div>

              {/* Element create form */}
              {showElementForm && (
                <div className="mb-4 p-4 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg space-y-3">
                  <input
                    type="text"
                    value={elementName}
                    onChange={(e) => setElementName(e.target.value)}
                    placeholder={t('element.name') || 'Element name'}
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white rounded focus:ring-1 focus:ring-red-500 focus:border-red-500"
                  />
                  <select
                    value={elementType}
                    onChange={(e) => setElementType(e.target.value as ElementType)}
                    className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white rounded"
                  >
                    {ELEMENT_TYPES.map((et) => (
                      <option key={et} value={et}>
                        {t(`element_type.${et}`) || et}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => createElement.mutate({ name: elementName, element_type: elementType })}
                    disabled={!elementName.trim() || createElement.isPending}
                    className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                  >
                    {createElement.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      t('explorer.create') || 'Create'
                    )}
                  </button>
                </div>
              )}

              {/* Elements list */}
              {elementsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-5 h-5 animate-spin text-gray-400 dark:text-slate-500" />
                </div>
              ) : !elements || elements.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-slate-400 py-8 text-center">
                  {t('explorer.no_elements') || 'No elements in this zone.'}
                </p>
              ) : (
                <div className="space-y-3">
                  {elements.map((element) => (
                    <ElementCard
                      key={element.id}
                      element={element}
                      buildingId={buildingId!}
                      zoneId={selectedZoneId}
                      expanded={expandedElements.has(element.id)}
                      onToggle={() => toggleElement(element.id)}
                      deleteConfirm={deleteConfirm}
                      setDeleteConfirm={setDeleteConfirm}
                      onDeleteElement={() => deleteElement.mutate(element.id)}
                      showMaterialForm={showMaterialForm}
                      setShowMaterialForm={setShowMaterialForm}
                      materialName={materialName}
                      setMaterialName={setMaterialName}
                      materialType={materialType}
                      setMaterialType={setMaterialType}
                      onCreateMaterial={(elementId) =>
                        createMaterial.mutate({ elementId, data: { name: materialName, material_type: materialType } })
                      }
                      onDeleteMaterial={(elementId, materialId) => deleteMaterial.mutate({ elementId, materialId })}
                      createMaterialPending={createMaterial.isPending}
                      t={t}
                    />
                  ))}
                </div>
              )}

              {/* Plans with heatmap overlay */}
              {plans && plans.length > 0 && (
                <div className="mt-8">
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300 uppercase tracking-wider mb-4">
                    {t('plan.title') || 'Technical Plans'}
                  </h3>
                  <div className="space-y-4">
                    {plans
                      .filter((plan) => !selectedZoneId || !plan.zone_id || plan.zone_id === selectedZoneId)
                      .map((plan) => {
                        const isHeatmapActive = heatmapPlanIds.has(plan.id);
                        const previewUrl = `/api/buildings/${buildingId}/plans/${plan.id}/preview`;
                        return (
                          <div
                            key={plan.id}
                            className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg overflow-hidden"
                          >
                            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100 dark:border-slate-800">
                              <div className="flex items-center gap-2">
                                <FileImage className="w-4 h-4 text-gray-400 dark:text-slate-500" />
                                <span className="text-sm font-medium text-gray-900 dark:text-white">{plan.title}</span>
                                <span className="text-xs text-gray-400 dark:text-slate-500">
                                  {t(`plan.type.${plan.plan_type}`) || plan.plan_type}
                                </span>
                              </div>
                              <button
                                onClick={() => toggleHeatmap(plan.id)}
                                className={`flex items-center gap-1.5 px-3 py-1 text-xs rounded-full border transition-colors ${
                                  isHeatmapActive
                                    ? 'bg-red-600 text-white border-red-600'
                                    : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-slate-300 border-gray-300 dark:border-slate-700 hover:border-gray-400 dark:hover:border-slate-500'
                                }`}
                              >
                                {isHeatmapActive ? (
                                  <>
                                    <EyeOff className="w-3 h-3" />
                                    {t('heatmap.hide_overlay') || 'Hide proof overlay'}
                                  </>
                                ) : (
                                  <>
                                    <Eye className="w-3 h-3" />
                                    {t('heatmap.show_overlay') || 'Show proof overlay'}
                                  </>
                                )}
                              </button>
                            </div>
                            <div className="p-2">
                              {isHeatmapActive ? (
                                <ProofHeatmapOverlay planId={plan.id} imageUrl={previewUrl} />
                              ) : (
                                <img src={previewUrl} alt={plan.title} className="w-full h-auto rounded" />
                              )}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---------- Summary Header Component ---------- */

interface SummaryHeaderProps {
  t: (key: string) => string;
  totalZones: number;
  totalElements: number;
  totalMaterials: number;
  conditionDistribution: Record<string, number> | null;
}

function SummaryHeader({ t, totalZones, totalElements, totalMaterials, conditionDistribution }: SummaryHeaderProps) {
  const total = conditionDistribution ? Object.values(conditionDistribution).reduce((s, v) => s + v, 0) : 0;

  return (
    <div className="mb-6 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg p-4">
      <div className="flex items-center gap-6 flex-wrap">
        {/* Zone count */}
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/30">
            <Layers className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <p className="text-lg font-bold text-gray-900 dark:text-white">{totalZones}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('explorer.zones') || 'Zones'}</p>
          </div>
        </div>

        {/* Element count */}
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-purple-50 dark:bg-purple-950/30">
            <Box className="w-4 h-4 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <p className="text-lg font-bold text-gray-900 dark:text-white">{totalElements}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('explorer.elements') || 'elements'}</p>
          </div>
        </div>

        {/* Material count */}
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-amber-50 dark:bg-amber-950/30">
            <BarChart3 className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <p className="text-lg font-bold text-gray-900 dark:text-white">{totalMaterials}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('explorer.materials') || 'materials'}</p>
          </div>
        </div>

        {/* Condition distribution bar */}
        {conditionDistribution && total > 0 && (
          <div className="flex-1 min-w-[200px]">
            <p className="text-xs text-gray-500 dark:text-slate-400 mb-1.5">
              {t('explorer.condition_distribution') || 'Condition'}
            </p>
            <div className="flex h-2.5 rounded-full overflow-hidden bg-gray-100 dark:bg-slate-800">
              {(['good', 'fair', 'poor', 'critical', 'unknown'] as const).map((cond) => {
                const count = conditionDistribution[cond] || 0;
                if (count === 0) return null;
                const pct = (count / total) * 100;
                return (
                  <div
                    key={cond}
                    className={`${CONDITION_BAR_COLORS[cond]} transition-all`}
                    style={{ width: `${pct}%` }}
                    title={`${t(`element_condition.${cond}`) || cond}: ${count} (${Math.round(pct)}%)`}
                  />
                );
              })}
            </div>
            <div className="flex gap-3 mt-1.5 flex-wrap">
              {(['good', 'fair', 'poor', 'critical'] as const).map((cond) => {
                const count = conditionDistribution[cond] || 0;
                if (count === 0) return null;
                return (
                  <span key={cond} className="flex items-center gap-1 text-[10px] text-gray-500 dark:text-slate-400">
                    <span className={`w-2 h-2 rounded-full ${CONDITION_BAR_COLORS[cond]}`} />
                    {t(`element_condition.${cond}`) || cond} ({count})
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------- Element Card Component ---------- */

interface ElementCardProps {
  element: BuildingElement;
  buildingId: string;
  zoneId: string;
  expanded: boolean;
  onToggle: () => void;
  deleteConfirm: string | null;
  setDeleteConfirm: (id: string | null) => void;
  onDeleteElement: () => void;
  showMaterialForm: string | null;
  setShowMaterialForm: (id: string | null) => void;
  materialName: string;
  setMaterialName: (v: string) => void;
  materialType: MaterialType;
  setMaterialType: (v: MaterialType) => void;
  onCreateMaterial: (elementId: string) => void;
  onDeleteMaterial: (elementId: string, materialId: string) => void;
  createMaterialPending: boolean;
  t: (key: string) => string;
}

function ElementCard({
  element,
  buildingId,
  zoneId,
  expanded,
  onToggle,
  deleteConfirm,
  setDeleteConfirm,
  onDeleteElement,
  showMaterialForm,
  setShowMaterialForm,
  materialName,
  setMaterialName,
  materialType,
  setMaterialType,
  onCreateMaterial,
  onDeleteMaterial,
  createMaterialPending,
  t,
}: ElementCardProps) {
  const { data: materials, isLoading: materialsLoading } = useQuery({
    queryKey: ['materials', buildingId, zoneId, element.id],
    queryFn: () => materialsApi.list(buildingId, zoneId, element.id),
    enabled: expanded,
  });

  const Chevron = expanded ? ChevronDown : ChevronRight;
  const ElementIcon = ELEMENT_ICONS[element.element_type] || Box;
  const condition = element.condition || 'unknown';
  const condColor = CONDITION_COLORS[condition] || CONDITION_COLORS.unknown;

  // Count pollutant-positive materials
  const pollutantCount = (materials ?? []).filter((m) => m.contains_pollutant).length;

  // Condition-based left border
  const condBorderColor: Record<string, string> = {
    good: 'border-l-emerald-500',
    fair: 'border-l-blue-500',
    poor: 'border-l-amber-500',
    critical: 'border-l-red-500',
    unknown: 'border-l-gray-300 dark:border-l-slate-600',
  };

  return (
    <div
      className={`bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg overflow-hidden border-l-4 ${condBorderColor[condition] || condBorderColor.unknown}`}
    >
      {/* Element header */}
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-slate-800"
        onClick={onToggle}
      >
        <Chevron className="w-4 h-4 text-gray-400 dark:text-slate-500 flex-shrink-0" />
        <ElementIcon className="w-4 h-4 text-gray-400 dark:text-slate-500 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-medium text-sm text-gray-900 dark:text-white">{element.name}</p>
            {/* Condition badge */}
            <span
              className={`px-2 py-0.5 text-[10px] font-semibold rounded-full ${condColor.bg} ${condColor.text} ${condColor.darkBg} ${condColor.darkText}`}
            >
              {t(`element_condition.${condition}`) || condition}
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-slate-400">
            {t(`element_type.${element.element_type}`) || element.element_type}
            {' · '}
            {element.materials_count} {t('explorer.materials') || 'materials'}
            {pollutantCount > 0 && expanded && (
              <span className="ml-2 text-red-600 dark:text-red-400 font-medium">
                <AlertTriangle className="w-3 h-3 inline -mt-0.5 mr-0.5" />
                {pollutantCount} {t('explorer.pollutant_positive') || 'pollutant+'}
              </span>
            )}
          </p>
        </div>
        <RoleGate allowedRoles={['admin', 'diagnostician']}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowMaterialForm(showMaterialForm === element.id ? null : element.id);
            }}
            className="p-1 text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 rounded"
            title={t('explorer.add_material') || 'Add material'}
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (deleteConfirm === element.id) onDeleteElement();
              else setDeleteConfirm(element.id);
            }}
            className={`p-1 rounded ${
              deleteConfirm === element.id
                ? 'text-red-600 bg-red-100 dark:bg-red-950/40'
                : 'text-gray-400 dark:text-slate-500 hover:text-red-500'
            }`}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </RoleGate>
      </div>

      {/* Materials */}
      {expanded && (
        <div className="border-t border-gray-100 dark:border-slate-800">
          {/* Material create form */}
          {showMaterialForm === element.id && (
            <div className="p-3 bg-gray-50 dark:bg-slate-950/40 border-b border-gray-100 dark:border-slate-800 flex gap-2 items-end">
              <input
                type="text"
                value={materialName}
                onChange={(e) => setMaterialName(e.target.value)}
                placeholder={t('material.name') || 'Material name'}
                className="flex-1 px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white rounded focus:ring-1 focus:ring-red-500 focus:border-red-500"
              />
              <select
                value={materialType}
                onChange={(e) => setMaterialType(e.target.value as MaterialType)}
                className="px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white rounded"
              >
                {MATERIAL_TYPES.map((mt) => (
                  <option key={mt} value={mt}>
                    {t(`material_type.${mt}`) || mt}
                  </option>
                ))}
              </select>
              <button
                onClick={() => onCreateMaterial(element.id)}
                disabled={!materialName.trim() || createMaterialPending}
                className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
              >
                {createMaterialPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  t('explorer.create') || 'Create'
                )}
              </button>
            </div>
          )}

          {materialsLoading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="w-4 h-4 animate-spin text-gray-400 dark:text-slate-500" />
            </div>
          ) : !materials || materials.length === 0 ? (
            <p className="px-4 py-3 text-xs text-gray-400 dark:text-slate-500">
              {t('explorer.no_materials') || 'No materials.'}
            </p>
          ) : (
            <ul className="divide-y divide-gray-50 dark:divide-slate-800">
              {materials.map((material) => (
                <MaterialRow
                  key={material.id}
                  material={material}
                  elementId={element.id}
                  buildingId={buildingId}
                  deleteConfirm={deleteConfirm}
                  setDeleteConfirm={setDeleteConfirm}
                  onDeleteMaterial={onDeleteMaterial}
                  t={t}
                />
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

/* ---------- Material Row Component ---------- */

interface MaterialRowProps {
  material: Material;
  elementId: string;
  buildingId: string;
  deleteConfirm: string | null;
  setDeleteConfirm: (id: string | null) => void;
  onDeleteMaterial: (elementId: string, materialId: string) => void;
  t: (key: string) => string;
}

function MaterialRow({
  material,
  elementId,
  buildingId,
  deleteConfirm,
  setDeleteConfirm,
  onDeleteMaterial,
  t,
}: MaterialRowProps) {
  return (
    <li className="flex items-center gap-3 px-4 py-2.5 pl-10">
      {/* Pollutant indicator dot */}
      {material.contains_pollutant ? (
        <AlertTriangle className="w-3.5 h-3.5 text-red-500 dark:text-red-400 flex-shrink-0" />
      ) : (
        <span className="w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-slate-600 flex-shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-800 dark:text-slate-100">{material.name}</span>
          <span className="text-xs text-gray-400 dark:text-slate-500">
            {t(`material_type.${material.material_type}`) || material.material_type}
          </span>
        </div>
        {/* Extra detail row for pollutant materials */}
        {material.contains_pollutant && (
          <div className="flex items-center gap-2 mt-0.5">
            {material.pollutant_type && <PollutantBadge type={material.pollutant_type as PollutantType} size="sm" />}
            {material.source && (
              <span className="text-[10px] text-gray-400 dark:text-slate-500">
                {t(`material_source.${material.source}`) || material.source}
              </span>
            )}
          </div>
        )}
        {/* Sample link */}
        {material.sample_id && (
          <Link
            to={`/buildings/${buildingId}/diagnostics`}
            className="inline-flex items-center gap-1 mt-0.5 text-[10px] text-red-600 dark:text-red-400 hover:underline"
          >
            <LinkIcon className="w-2.5 h-2.5" />
            {t('explorer.view_sample') || 'View linked sample'}
          </Link>
        )}
      </div>
      <RoleGate allowedRoles={['admin', 'diagnostician']}>
        <button
          onClick={() => {
            if (deleteConfirm === material.id) onDeleteMaterial(elementId, material.id);
            else setDeleteConfirm(material.id);
          }}
          className={`p-1 rounded ${
            deleteConfirm === material.id
              ? 'text-red-600 bg-red-100 dark:bg-red-950/40'
              : 'text-gray-400 dark:text-slate-500 hover:text-red-500'
          }`}
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </RoleGate>
    </li>
  );
}
