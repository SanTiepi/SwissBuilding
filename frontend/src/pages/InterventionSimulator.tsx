import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { simulatorApi, type SimulationInput, type SimulationResult } from '@/api/simulator';
import { toast } from '@/store/toastStore';
import { BuildingSubNav } from '@/components/BuildingSubNav';
import {
  ArrowLeft,
  Plus,
  Trash2,
  Play,
  Loader2,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  Save,
  FolderOpen,
  BarChart3,
  Clock,
  Award,
  Zap,
  Star,
  ChevronDown,
  ChevronUp,
  Shield,
  Beaker,
  Wind,
  Hammer,
  Eye,
  Layers,
  Droplets,
  Sparkles,
  Copy,
  GripVertical,
  Target,
  Info,
  ArrowUpRight,
  Minus,
} from 'lucide-react';

// ── Constants ──────────────────────────────────────────────────────

const INTERVENTION_TYPES = [
  'removal',
  'encapsulation',
  'remediation',
  'monitoring',
  'demolition',
  'sealing',
  'ventilation',
  'cleaning',
  'stabilization',
  'containment',
] as const;

const POLLUTANT_TYPES = ['asbestos', 'pcb', 'lead', 'hap', 'radon'] as const;

const STORAGE_KEY = 'swissbuild_sim_scenarios';

const GRADE_ORDER: Record<string, number> = { A: 5, B: 4, C: 3, D: 2, E: 1, F: 0 };

const INTERVENTION_ICONS: Record<string, typeof Shield> = {
  removal: Trash2,
  encapsulation: Shield,
  remediation: Beaker,
  monitoring: Eye,
  demolition: Hammer,
  sealing: Layers,
  ventilation: Wind,
  cleaning: Droplets,
  stabilization: Target,
  containment: Shield,
};

// ── Extended input with scope/timeline ──────────────────────────────

interface ExtendedSimulationInput extends SimulationInput {
  scope?: string;
  timeline_weeks?: number | null;
}

// ── Saved scenario ──────────────────────────────────────────────────

interface SavedScenario {
  id: string;
  name: string;
  savedAt: string;
  interventions: ExtendedSimulationInput[];
  result: SimulationResult | null;
}

// ── Helpers ──────────────────────────────────────────────────────────

function gradeColor(grade: string): string {
  switch (grade) {
    case 'A':
      return 'text-green-600 dark:text-green-400';
    case 'B':
      return 'text-blue-600 dark:text-blue-400';
    case 'C':
      return 'text-yellow-600 dark:text-yellow-400';
    case 'D':
      return 'text-orange-600 dark:text-orange-400';
    default:
      return 'text-red-600 dark:text-red-400';
  }
}

function gradeBgColor(grade: string): string {
  switch (grade) {
    case 'A':
      return 'bg-green-100 dark:bg-green-900/30';
    case 'B':
      return 'bg-blue-100 dark:bg-blue-900/30';
    case 'C':
      return 'bg-yellow-100 dark:bg-yellow-900/30';
    case 'D':
      return 'bg-orange-100 dark:bg-orange-900/30';
    default:
      return 'bg-red-100 dark:bg-red-900/30';
  }
}

function gradeRingColor(grade: string): string {
  switch (grade) {
    case 'A':
      return 'ring-green-300 dark:ring-green-700';
    case 'B':
      return 'ring-blue-300 dark:ring-blue-700';
    case 'C':
      return 'ring-yellow-300 dark:ring-yellow-700';
    case 'D':
      return 'ring-orange-300 dark:ring-orange-700';
    default:
      return 'ring-red-300 dark:ring-red-700';
  }
}

function deltaArrow(delta: number): React.ReactNode {
  if (delta > 0) return <TrendingUp className="w-4 h-4 text-green-500" />;
  if (delta < 0) return <TrendingDown className="w-4 h-4 text-red-500" />;
  return <Minus className="w-4 h-4 text-gray-400 dark:text-slate-500" />;
}

function gradeNumericDelta(from: string, to: string): number {
  return (GRADE_ORDER[to] ?? 0) - (GRADE_ORDER[from] ?? 0);
}

function loadScenariosFromStorage(buildingId: string): SavedScenario[] {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY}_${buildingId}`);
    return raw ? (JSON.parse(raw) as SavedScenario[]) : [];
  } catch {
    return [];
  }
}

function saveScenariosToStorage(buildingId: string, scenarios: SavedScenario[]) {
  localStorage.setItem(`${STORAGE_KEY}_${buildingId}`, JSON.stringify(scenarios));
}

function getInterventionIcon(type: string) {
  return INTERVENTION_ICONS[type] ?? Hammer;
}

// ── Animated number hook ──────────────────────────────────────────

function useAnimatedNumber(target: number, duration = 800): number {
  const [current, setCurrent] = useState(target);
  const prevRef = useRef(target);

  /* eslint-disable react-hooks/set-state-in-effect -- animation driven by rAF */
  useEffect(() => {
    const from = prevRef.current;
    const diff = target - from;
    if (Math.abs(diff) < 0.001) {
      setCurrent(target);
      prevRef.current = target;
      return;
    }
    const startTime = performance.now();
    let raf: number;
    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
      setCurrent(from + diff * eased);
      if (progress < 1) {
        raf = requestAnimationFrame(animate);
      } else {
        prevRef.current = target;
      }
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  /* eslint-enable react-hooks/set-state-in-effect */

  return current;
}

// ── Main component ──────────────────────────────────────────────────

export default function InterventionSimulator() {
  const { buildingId } = useParams<{ buildingId: string }>();
  const { t } = useTranslation();
  const [interventions, setInterventions] = useState<ExtendedSimulationInput[]>([]);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [scenarioName, setScenarioName] = useState('');
  const [savedScenarios, setSavedScenarios] = useState<SavedScenario[]>(() =>
    buildingId ? loadScenariosFromStorage(buildingId) : [],
  );
  const [showScenarioPanel, setShowScenarioPanel] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [gradeAnimating, setGradeAnimating] = useState(false);
  const [expandedInterventions, setExpandedInterventions] = useState<Set<number>>(new Set());
  const [resultsVisible, setResultsVisible] = useState(false);

  // Reload saved scenarios when buildingId changes (reads from localStorage)
  /* eslint-disable react-hooks/set-state-in-effect -- reading external storage on param change */
  useEffect(() => {
    if (buildingId) {
      setSavedScenarios(loadScenariosFromStorage(buildingId));
    }
  }, [buildingId]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // Grade animation timer ref
  const gradeTimerRef = useRef<ReturnType<typeof setTimeout>>();

  // Staggered results appearance — reset handled in mutation callbacks
  const resultsTimerRef = useRef<ReturnType<typeof setTimeout>>();

  const mutation = useMutation({
    mutationFn: () => {
      const apiInputs: SimulationInput[] = interventions.map(({ scope: _s, timeline_weeks: _tw, ...rest }) => rest);
      return simulatorApi.simulate(buildingId!, apiInputs);
    },
    onMutate: () => {
      setResultsVisible(false);
      setGradeAnimating(false);
      clearTimeout(resultsTimerRef.current);
      clearTimeout(gradeTimerRef.current);
    },
    onSuccess: (data) => {
      setResult(data);
      resultsTimerRef.current = setTimeout(() => setResultsVisible(true), 100);
      if (data.impact_summary.grade_change) {
        setGradeAnimating(true);
        gradeTimerRef.current = setTimeout(() => setGradeAnimating(false), 1200);
      }
    },
    onError: () => toast(t('app.error') || 'An error occurred', 'error'),
  });

  const addIntervention = useCallback(() => {
    setInterventions((prev) => [
      ...prev,
      {
        intervention_type: 'removal',
        target_pollutant: null,
        target_zone_id: null,
        estimated_cost: null,
        scope: '',
        timeline_weeks: null,
      },
    ]);
  }, []);

  const duplicateIntervention = useCallback((index: number) => {
    setInterventions((prev) => {
      const copy = { ...prev[index] };
      return [...prev.slice(0, index + 1), copy, ...prev.slice(index + 1)];
    });
  }, []);

  const removeIntervention = useCallback((index: number) => {
    setInterventions((prev) => prev.filter((_, i) => i !== index));
    setResult(null);
  }, []);

  const updateIntervention = useCallback(
    (index: number, field: keyof ExtendedSimulationInput, value: string | number | null) => {
      setInterventions((prev) => prev.map((item, i) => (i === index ? { ...item, [field]: value } : item)));
      setResult(null);
    },
    [],
  );

  const toggleExpanded = useCallback((index: number) => {
    setExpandedInterventions((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  }, []);

  const totalCost = useMemo(() => interventions.reduce((sum, i) => sum + (i.estimated_cost ?? 0), 0), [interventions]);
  const totalWeeks = useMemo(() => Math.max(0, ...interventions.map((i) => i.timeline_weeks ?? 0)), [interventions]);

  // ── Scenario management ──────────────────────────────────────────

  const saveScenario = useCallback(() => {
    if (!buildingId || !scenarioName.trim()) return;
    const scenario: SavedScenario = {
      id: crypto.randomUUID(),
      name: scenarioName.trim(),
      savedAt: new Date().toISOString(),
      interventions: [...interventions],
      result,
    };
    const updated = [...savedScenarios, scenario];
    setSavedScenarios(updated);
    saveScenariosToStorage(buildingId, updated);
    setScenarioName('');
    toast(t('simulator.scenario_saved') || 'Scenario saved', 'success');
  }, [buildingId, scenarioName, interventions, result, savedScenarios, t]);

  const loadScenario = useCallback(
    (scenario: SavedScenario) => {
      setInterventions(scenario.interventions);
      setResult(scenario.result);
      setScenarioName(scenario.name);
      toast(t('simulator.scenario_loaded') || 'Scenario loaded', 'success');
    },
    [t],
  );

  const deleteScenario = useCallback(
    (id: string) => {
      if (!buildingId) return;
      const updated = savedScenarios.filter((s) => s.id !== id);
      setSavedScenarios(updated);
      saveScenariosToStorage(buildingId, updated);
      setSelectedForCompare((prev) => prev.filter((sid) => sid !== id));
      toast(t('simulator.scenario_deleted') || 'Scenario deleted', 'success');
    },
    [buildingId, savedScenarios, t],
  );

  const toggleCompareSelect = useCallback((id: string) => {
    setSelectedForCompare((prev) => {
      if (prev.includes(id)) return prev.filter((sid) => sid !== id);
      if (prev.length >= 3) return prev;
      return [...prev, id];
    });
  }, []);

  const scenariosForCompare = useMemo(
    () => savedScenarios.filter((s) => selectedForCompare.includes(s.id) && s.result),
    [savedScenarios, selectedForCompare],
  );

  // Find the "best" scenario by highest projected grade then trust
  const bestScenarioId = useMemo(() => {
    if (scenariosForCompare.length === 0) return null;
    let best = scenariosForCompare[0];
    for (const s of scenariosForCompare) {
      if (!s.result || !best.result) continue;
      const sGrade = GRADE_ORDER[s.result.projected_state.passport_grade] ?? 0;
      const bGrade = GRADE_ORDER[best.result.projected_state.passport_grade] ?? 0;
      if (
        sGrade > bGrade ||
        (sGrade === bGrade && s.result.projected_state.trust_score > best.result.projected_state.trust_score)
      ) {
        best = s;
      }
    }
    return best.id;
  }, [scenariosForCompare]);

  // ── Cost breakdown per intervention type ──────────────────────────

  const costBreakdown = useMemo(() => {
    const map: Record<string, number> = {};
    for (const i of interventions) {
      if (i.estimated_cost && i.estimated_cost > 0) {
        map[i.intervention_type] = (map[i.intervention_type] ?? 0) + i.estimated_cost;
      }
    }
    return Object.entries(map).sort((a, b) => b[1] - a[1]);
  }, [interventions]);

  const maxCostEntry = useMemo(() => Math.max(1, ...costBreakdown.map(([, v]) => v)), [costBreakdown]);

  // ── Intervention summary counts ──────────────────────────────────

  const interventionSummary = useMemo(() => {
    const byType: Record<string, number> = {};
    const byPollutant: Record<string, number> = {};
    for (const i of interventions) {
      byType[i.intervention_type] = (byType[i.intervention_type] ?? 0) + 1;
      if (i.target_pollutant) {
        byPollutant[i.target_pollutant] = (byPollutant[i.target_pollutant] ?? 0) + 1;
      }
    }
    return { byType, byPollutant };
  }, [interventions]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-4">
        <Link
          to={`/buildings/${buildingId}`}
          className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-slate-300" />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
            {t('simulator.title') || 'Intervention Simulator'}
          </h1>
          <p className="text-sm text-gray-500 dark:text-slate-400">
            {t('simulator.subtitle') || 'Simulate the impact of planned interventions'}
          </p>
        </div>
        {/* Scenario toggle */}
        <button
          onClick={() => setShowScenarioPanel(!showScenarioPanel)}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors min-h-[44px]"
        >
          <FolderOpen className="w-4 h-4" />
          {t('simulator.load_scenario') || 'Load Scenario'}
          {savedScenarios.length > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-xs font-semibold rounded-full bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-slate-300">
              {savedScenarios.length}
            </span>
          )}
          {showScenarioPanel ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      </div>

      <BuildingSubNav buildingId={buildingId!} />

      {/* Scenario management panel */}
      {showScenarioPanel && (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-gray-500" />
              {t('simulator.saved_scenarios_title') || 'Saved Scenarios'}
            </h2>
            <button
              onClick={() => setCompareMode(!compareMode)}
              disabled={savedScenarios.filter((s) => s.result).length < 2}
              className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                compareMode
                  ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                  : 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/50'
              } disabled:opacity-40 disabled:cursor-not-allowed`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              {t('simulator.compare_scenarios') || 'Compare'}
              {compareMode && selectedForCompare.length > 0 && (
                <span className="px-1.5 py-0.5 text-xs rounded-full bg-white/20">{selectedForCompare.length}/3</span>
              )}
            </button>
          </div>
          {savedScenarios.length === 0 ? (
            <div className="text-center py-8">
              <FolderOpen className="w-10 h-10 mx-auto mb-3 text-gray-300 dark:text-slate-600" />
              <p className="text-sm text-gray-500 dark:text-slate-400">
                {t('simulator.no_saved_scenarios') || 'No saved scenarios yet.'}
              </p>
              <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
                {t('simulator.save_hint') || 'Run a simulation and save it to compare later.'}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {savedScenarios.map((scenario) => (
                <div
                  key={scenario.id}
                  className={`flex items-center gap-3 p-3 rounded-lg border transition-all duration-200 ${
                    compareMode && selectedForCompare.includes(scenario.id)
                      ? 'border-indigo-400 dark:border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 shadow-sm'
                      : 'border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700/50'
                  }`}
                >
                  {compareMode && (
                    <input
                      type="checkbox"
                      checked={selectedForCompare.includes(scenario.id)}
                      onChange={() => toggleCompareSelect(scenario.id)}
                      disabled={!scenario.result && !selectedForCompare.includes(scenario.id)}
                      className="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                  )}
                  {/* Scenario grade badge */}
                  {scenario.result && (
                    <div
                      className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${gradeBgColor(scenario.result.projected_state.passport_grade)}`}
                    >
                      <span
                        className={`text-lg font-black ${gradeColor(scenario.result.projected_state.passport_grade)}`}
                      >
                        {scenario.result.projected_state.passport_grade}
                      </span>
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{scenario.name}</p>
                    <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-slate-400">
                      <span>
                        {scenario.interventions.length} {t('simulator.interventions').toLowerCase()}
                      </span>
                      {scenario.result && (
                        <>
                          <span>&middot;</span>
                          <span className={gradeColor(scenario.result.current_state.passport_grade)}>
                            {scenario.result.current_state.passport_grade}
                          </span>
                          <ArrowRight className="w-3 h-3" />
                          <span className={gradeColor(scenario.result.projected_state.passport_grade)}>
                            {scenario.result.projected_state.passport_grade}
                          </span>
                        </>
                      )}
                      <span>&middot;</span>
                      <span>{new Date(scenario.savedAt).toLocaleDateString()}</span>
                    </div>
                  </div>
                  {!compareMode && (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => loadScenario(scenario)}
                        className="px-2.5 py-1 text-xs font-medium text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/30 rounded hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
                      >
                        {t('simulator.load_scenario') || 'Load'}
                      </button>
                      <button
                        onClick={() => deleteScenario(scenario.id)}
                        className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                        title={t('simulator.delete_scenario') || 'Delete'}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Scenario comparison */}
          {compareMode && scenariosForCompare.length >= 2 && (
            <ScenarioComparison scenarios={scenariosForCompare} bestId={bestScenarioId} />
          )}
        </div>
      )}

      {/* Intervention summary badges */}
      {interventions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(interventionSummary.byType).map(([type, count]) => {
            const Icon = getInterventionIcon(type);
            return (
              <span
                key={type}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300"
              >
                <Icon className="w-3 h-3" />
                {type.charAt(0).toUpperCase() + type.slice(1)}
                {count > 1 && (
                  <span className="px-1 py-0.5 text-[10px] font-bold rounded-full bg-gray-200 dark:bg-slate-600 leading-none">
                    {count}
                  </span>
                )}
              </span>
            );
          })}
          {Object.entries(interventionSummary.byPollutant).map(([pollutant, count]) => (
            <span
              key={pollutant}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300"
            >
              <AlertTriangle className="w-3 h-3" />
              {pollutant.toUpperCase()}
              {count > 1 && (
                <span className="px-1 py-0.5 text-[10px] font-bold rounded-full bg-red-100 dark:bg-red-900/40 leading-none">
                  {count}
                </span>
              )}
            </span>
          ))}
          {totalCost > 0 && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300">
              CHF {totalCost.toLocaleString('de-CH')}
            </span>
          )}
          {totalWeeks > 0 && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300">
              <Clock className="w-3 h-3" />
              {totalWeeks} {t('simulator.weeks') || 'weeks'}
            </span>
          )}
        </div>
      )}

      {/* Interventions builder */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-red-500" />
            {t('simulator.interventions') || 'Interventions'}
            {interventions.length > 0 && (
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300">
                {interventions.length}
              </span>
            )}
          </h2>
          <button
            onClick={addIntervention}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors shadow-sm min-h-[44px]"
          >
            <Plus className="w-4 h-4" />
            {t('simulator.add_intervention') || 'Add Intervention'}
          </button>
        </div>

        {interventions.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 dark:bg-slate-700 flex items-center justify-center">
              <Sparkles className="w-8 h-8 text-gray-400 dark:text-slate-500" />
            </div>
            <p className="text-sm text-gray-500 dark:text-slate-400 mb-1">
              {t('simulator.no_interventions') || 'No interventions added yet.'}
            </p>
            <p className="text-xs text-gray-400 dark:text-slate-500">
              {t('simulator.empty_hint') || 'Add interventions to simulate their impact on the building.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {interventions.map((intervention, index) => {
              const Icon = getInterventionIcon(intervention.intervention_type);
              const isExpanded = expandedInterventions.has(index);
              return (
                <div
                  key={index}
                  className="group bg-gray-50 dark:bg-slate-700/50 rounded-lg border border-gray-200 dark:border-slate-600 transition-all duration-200 hover:border-gray-300 dark:hover:border-slate-500"
                >
                  {/* Compact header row */}
                  <div className="flex items-center gap-3 p-3">
                    <div className="flex-shrink-0 text-gray-300 dark:text-slate-600">
                      <GripVertical className="w-4 h-4" />
                    </div>
                    <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-white dark:bg-slate-600 border border-gray-200 dark:border-slate-500 flex items-center justify-center">
                      <Icon className="w-4 h-4 text-gray-600 dark:text-slate-300" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                          {intervention.intervention_type}
                        </span>
                        {intervention.target_pollutant && (
                          <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 uppercase">
                            {intervention.target_pollutant}
                          </span>
                        )}
                        {intervention.estimated_cost && intervention.estimated_cost > 0 && (
                          <span className="text-xs text-gray-500 dark:text-slate-400">
                            CHF {intervention.estimated_cost.toLocaleString('de-CH')}
                          </span>
                        )}
                        {intervention.scope && (
                          <span className="text-xs text-gray-400 dark:text-slate-500 truncate max-w-[120px]">
                            {intervention.scope}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => duplicateIntervention(index)}
                        className="p-2 sm:p-1.5 min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 flex items-center justify-center text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors sm:opacity-0 sm:group-hover:opacity-100"
                        title={t('simulator.duplicate_intervention') || 'Duplicate'}
                      >
                        <Copy className="w-4 h-4 sm:w-3.5 sm:h-3.5" />
                      </button>
                      <button
                        onClick={() => removeIntervention(index)}
                        className="p-2 sm:p-1.5 min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 flex items-center justify-center text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors sm:opacity-0 sm:group-hover:opacity-100"
                        title={t('simulator.remove_intervention') || 'Remove'}
                      >
                        <Trash2 className="w-4 h-4 sm:w-3.5 sm:h-3.5" />
                      </button>
                      <button
                        onClick={() => toggleExpanded(index)}
                        className="p-2 sm:p-1.5 min-h-[44px] min-w-[44px] sm:min-h-0 sm:min-w-0 flex items-center justify-center text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 transition-colors"
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Expanded edit fields */}
                  {isExpanded && (
                    <div className="px-3 pb-4 pt-1 border-t border-gray-200 dark:border-slate-600">
                      <div className="flex flex-col sm:flex-row gap-3 mt-3">
                        {/* Type */}
                        <div className="flex-1 min-w-0">
                          <label className="block text-xs font-medium text-gray-600 dark:text-slate-400 mb-1">
                            {t('simulator.intervention_type') || 'Type'}
                          </label>
                          <select
                            value={intervention.intervention_type}
                            onChange={(e) => updateIntervention(index, 'intervention_type', e.target.value)}
                            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent min-h-[44px]"
                          >
                            {INTERVENTION_TYPES.map((type) => (
                              <option key={type} value={type}>
                                {type.charAt(0).toUpperCase() + type.slice(1)}
                              </option>
                            ))}
                          </select>
                        </div>

                        {/* Pollutant */}
                        <div className="flex-1 min-w-0">
                          <label className="block text-xs font-medium text-gray-600 dark:text-slate-400 mb-1">
                            {t('simulator.target_pollutant') || 'Pollutant'}
                          </label>
                          <select
                            value={intervention.target_pollutant ?? ''}
                            onChange={(e) => updateIntervention(index, 'target_pollutant', e.target.value || null)}
                            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent min-h-[44px]"
                          >
                            <option value="">--</option>
                            {POLLUTANT_TYPES.map((p) => (
                              <option key={p} value={p}>
                                {p.charAt(0).toUpperCase() + p.slice(1)}
                              </option>
                            ))}
                          </select>
                        </div>

                        {/* Cost */}
                        <div className="flex-1 min-w-0">
                          <label className="block text-xs font-medium text-gray-600 dark:text-slate-400 mb-1">
                            {t('simulator.estimated_cost') || 'Estimated Cost (CHF)'}
                          </label>
                          <input
                            type="number"
                            min="0"
                            step="100"
                            value={intervention.estimated_cost ?? ''}
                            onChange={(e) =>
                              updateIntervention(
                                index,
                                'estimated_cost',
                                e.target.value ? Number(e.target.value) : null,
                              )
                            }
                            placeholder="0"
                            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent min-h-[44px]"
                          />
                        </div>
                      </div>
                      {/* Second row: scope + timeline */}
                      <div className="flex flex-col sm:flex-row gap-3 mt-3">
                        <div className="flex-1 min-w-0">
                          <label className="block text-xs font-medium text-gray-600 dark:text-slate-400 mb-1">
                            {t('simulator.scope') || 'Scope'}
                          </label>
                          <input
                            type="text"
                            value={intervention.scope ?? ''}
                            onChange={(e) => updateIntervention(index, 'scope', e.target.value || null)}
                            placeholder={t('simulator.scope_placeholder') || 'e.g. 2nd floor, facade...'}
                            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent min-h-[44px]"
                          />
                        </div>
                        <div className="w-full sm:w-40">
                          <label className="block text-xs font-medium text-gray-600 dark:text-slate-400 mb-1">
                            {t('simulator.timeline') || 'Timeline (weeks)'}
                          </label>
                          <input
                            type="number"
                            min="0"
                            step="1"
                            value={intervention.timeline_weeks ?? ''}
                            onChange={(e) =>
                              updateIntervention(
                                index,
                                'timeline_weeks',
                                e.target.value ? Number(e.target.value) : null,
                              )
                            }
                            placeholder="0"
                            className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent min-h-[44px]"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Run button + total cost + save */}
        {interventions.length > 0 && (
          <div className="mt-6 pt-4 border-t border-gray-200 dark:border-slate-600 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex flex-col sm:flex-row items-center gap-3">
              {totalCost > 0 && (
                <p className="text-sm text-gray-600 dark:text-slate-400">
                  {t('simulator.total_cost') || 'Total estimated cost'}:{' '}
                  <span className="font-semibold text-gray-900 dark:text-white">
                    CHF {totalCost.toLocaleString('de-CH')}
                  </span>
                </p>
              )}
              {totalWeeks > 0 && (
                <p className="text-sm text-gray-600 dark:text-slate-400">
                  <Clock className="w-3.5 h-3.5 inline-block mr-1" />
                  {t('simulator.total_duration') || 'Total Duration'}:{' '}
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {totalWeeks} {t('simulator.weeks') || 'weeks'}
                  </span>
                </p>
              )}
            </div>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full sm:w-auto">
              {/* Save scenario */}
              <div className="flex items-center gap-1">
                <input
                  type="text"
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                  placeholder={t('simulator.scenario_name') || 'Scenario name'}
                  className="flex-1 sm:w-40 px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent min-h-[44px]"
                />
                <button
                  onClick={saveScenario}
                  disabled={!scenarioName.trim() || interventions.length === 0}
                  className="flex items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium rounded-lg border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors min-h-[44px] min-w-[44px]"
                  title={t('simulator.save_scenario') || 'Save'}
                >
                  <Save className="w-4 h-4" />
                </button>
              </div>
              <button
                onClick={() => mutation.mutate()}
                disabled={interventions.length === 0 || mutation.isPending}
                className="flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow-md min-h-[44px] w-full sm:w-auto"
              >
                {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {t('simulator.run_simulation') || 'Run Simulation'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* No results placeholder */}
      {!result && interventions.length > 0 && !mutation.isPending && (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-dashed border-gray-300 dark:border-slate-600 p-8 text-center">
          <Play className="w-10 h-10 mx-auto mb-3 text-gray-300 dark:text-slate-600" />
          <p className="text-sm text-gray-500 dark:text-slate-400">
            {t('simulator.no_results_yet') || 'Run a simulation to see results'}
          </p>
        </div>
      )}

      {/* Loading state */}
      {mutation.isPending && (
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-12 text-center">
          <Loader2 className="w-10 h-10 mx-auto mb-3 text-red-500 animate-spin" />
          <p className="text-sm font-medium text-gray-700 dark:text-slate-300">
            {t('simulator.running') || 'Running simulation...'}
          </p>
          <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
            {t('simulator.running_hint') || 'Analyzing interventions and projecting building state'}
          </p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div
          className={`space-y-6 transition-all duration-500 ${resultsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
        >
          {/* Before/After comparison with grade animation */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Current state */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6">
              <h3 className="text-sm font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-gray-400 dark:bg-slate-500" />
                {t('simulator.before') || 'Before'}
              </h3>
              <StateCard state={result.current_state} variant="before" />
            </div>

            {/* Grade transition visual */}
            <div className="flex flex-col items-center justify-center">
              <GradeTransition
                from={result.current_state.passport_grade}
                to={result.projected_state.passport_grade}
                animating={gradeAnimating}
              />
              {/* Delta summary */}
              <div className="mt-4 space-y-2 w-full max-w-xs">
                <DeltaRow
                  label={t('passport.trust') || 'Trust'}
                  delta={result.impact_summary.trust_delta}
                  format="percent"
                />
                <DeltaRow
                  label={t('passport.completeness') || 'Completeness'}
                  delta={result.impact_summary.completeness_delta}
                  format="percent"
                />
                <DeltaRow
                  label={t('simulator.blockers_resolved') || 'Blockers Resolved'}
                  delta={result.current_state.blocker_count - result.projected_state.blocker_count}
                  format="integer"
                />
                <DeltaRow
                  label={t('simulator.actions_resolved') || 'Actions Resolved'}
                  delta={result.impact_summary.actions_resolved}
                  format="integer"
                />
              </div>
            </div>

            {/* Projected state */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-green-200 dark:border-green-800/50 p-6">
              <h3 className="text-sm font-semibold text-green-600 dark:text-green-400 uppercase tracking-wide mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500 dark:bg-green-400" />
                {t('simulator.after') || 'After'}
              </h3>
              <StateCard state={result.projected_state} variant="after" />
            </div>
          </div>

          {/* Impact details row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Cost-Benefit summary */}
            <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-blue-500" />
                {t('simulator.cost_benefit') || 'Cost-Benefit'}
              </h3>
              <CostBenefitSummary result={result} totalCost={totalCost} />
            </div>

            {/* Cost breakdown chart */}
            {costBreakdown.length > 0 && (
              <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-purple-500" />
                  {t('simulator.cost_breakdown') || 'Cost Breakdown'}
                </h3>
                <div className="space-y-3">
                  {costBreakdown.map(([type, cost]) => {
                    const CostIcon = getInterventionIcon(type);
                    return (
                      <div key={type}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-700 dark:text-slate-300 capitalize flex items-center gap-1.5">
                            <CostIcon className="w-3.5 h-3.5 text-gray-400 dark:text-slate-500" />
                            {type}
                          </span>
                          <span className="text-sm font-medium text-gray-900 dark:text-white">
                            CHF {cost.toLocaleString('de-CH')}
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-slate-600 rounded-full h-2.5 overflow-hidden">
                          <div
                            className="bg-gradient-to-r from-purple-500 to-purple-400 dark:from-purple-500 dark:to-purple-300 h-2.5 rounded-full transition-all duration-700"
                            style={{ width: `${(cost / maxCostEntry) * 100}%` }}
                          />
                        </div>
                        {totalCost > 0 && (
                          <p className="text-[10px] text-gray-400 dark:text-slate-500 mt-0.5 text-right">
                            {((cost / totalCost) * 100).toFixed(0)}%
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Risk reduction + timeline */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Risk reduction */}
            {Object.keys(result.impact_summary.risk_reduction).length > 0 && (
              <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-green-500" />
                  {t('simulator.risk_reduction') || 'Risk Reduction'}
                </h3>
                <div className="space-y-3">
                  {Object.entries(result.impact_summary.risk_reduction).map(([pollutant, change]) => (
                    <div
                      key={pollutant}
                      className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-100 dark:border-green-900/40"
                    >
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-900/40 flex items-center justify-center">
                          <AlertTriangle className="w-4 h-4 text-green-600 dark:text-green-400" />
                        </div>
                        <span className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                          {pollutant}
                        </span>
                      </div>
                      <span className="text-sm font-semibold text-green-700 dark:text-green-300 flex items-center gap-1">
                        <ArrowUpRight className="w-3.5 h-3.5" />
                        {change}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Timeline projection */}
            {totalWeeks > 0 && (
              <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <Clock className="w-5 h-5 text-blue-500" />
                  {t('simulator.timeline_projection') || 'Timeline Projection'}
                </h3>
                <TimelineProjection interventions={interventions} />
              </div>
            )}
          </div>

          {/* Recommendations panel */}
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-yellow-500" />
              {t('simulator.recommendations') || 'Recommendations'}
              {result.recommendations.length > 0 && (
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300">
                  {result.recommendations.length}
                </span>
              )}
            </h3>
            {result.recommendations.length === 0 ? (
              <div className="text-center py-6">
                <CheckCircle2 className="w-10 h-10 mx-auto mb-2 text-green-300 dark:text-green-700" />
                <p className="text-sm text-gray-500 dark:text-slate-400">
                  {t('simulator.no_recommendations') || 'No additional recommendations.'}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {result.recommendations.map((rec, i) => (
                  <RecommendationCard key={i} text={rec} index={i} total={result.recommendations.length} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────

function StateCard({ state, variant }: { state: SimulationResult['current_state']; variant: 'before' | 'after' }) {
  const { t } = useTranslation();
  const trustPct = useAnimatedNumber(state.trust_score * 100, variant === 'after' ? 800 : 0);
  const completePct = useAnimatedNumber(state.completeness_score * 100, variant === 'after' ? 800 : 0);

  return (
    <div className="space-y-4">
      {/* Grade - large centered */}
      <div className="flex items-center justify-center">
        <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${gradeBgColor(state.passport_grade)}`}>
          <span className={`text-3xl font-black ${gradeColor(state.passport_grade)}`}>{state.passport_grade}</span>
        </div>
      </div>

      {/* Trust */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-gray-600 dark:text-slate-400">
            {t('passport.trust') || 'Trust'}
          </span>
          <span className="text-sm font-semibold text-gray-900 dark:text-white">{trustPct.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-slate-600 rounded-full h-2.5 overflow-hidden">
          <div
            className={`h-2.5 rounded-full transition-all duration-700 ${
              variant === 'after' ? 'bg-gradient-to-r from-blue-500 to-blue-400' : 'bg-blue-400 dark:bg-blue-600'
            }`}
            style={{ width: `${state.trust_score * 100}%` }}
          />
        </div>
      </div>

      {/* Completeness */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-gray-600 dark:text-slate-400">
            {t('passport.completeness') || 'Completeness'}
          </span>
          <span className="text-sm font-semibold text-gray-900 dark:text-white">{completePct.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-slate-600 rounded-full h-2.5 overflow-hidden">
          <div
            className={`h-2.5 rounded-full transition-all duration-700 ${
              variant === 'after' ? 'bg-gradient-to-r from-green-500 to-green-400' : 'bg-green-400 dark:bg-green-600'
            }`}
            style={{ width: `${state.completeness_score * 100}%` }}
          />
        </div>
      </div>

      {/* Blockers + Open Actions */}
      <div className="grid grid-cols-2 gap-3 pt-2">
        <div className="text-center p-2 rounded-lg bg-gray-50 dark:bg-slate-700/50">
          <p className="text-lg font-bold text-gray-900 dark:text-white">{state.blocker_count}</p>
          <p className="text-[10px] text-gray-500 dark:text-slate-400 uppercase tracking-wide">
            {t('readiness.blockers') || 'Blockers'}
          </p>
        </div>
        <div className="text-center p-2 rounded-lg bg-gray-50 dark:bg-slate-700/50">
          <p className="text-lg font-bold text-gray-900 dark:text-white">{state.open_actions_count}</p>
          <p className="text-[10px] text-gray-500 dark:text-slate-400 uppercase tracking-wide">
            {t('action.open_count') || 'Open Actions'}
          </p>
        </div>
      </div>
    </div>
  );
}

function GradeTransition({ from, to, animating }: { from: string; to: string; animating: boolean }) {
  const { t } = useTranslation();
  const improved = gradeNumericDelta(from, to) > 0;
  const delta = gradeNumericDelta(from, to);

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="flex items-center gap-4">
        <div
          className={`w-20 h-20 rounded-2xl flex items-center justify-center ${gradeBgColor(from)} transition-all duration-500 ${animating ? 'scale-90 opacity-60' : ''}`}
        >
          <span className={`text-4xl font-black ${gradeColor(from)}`}>{from}</span>
        </div>
        <div className="flex flex-col items-center gap-1">
          <ArrowRight
            className={`w-8 h-8 transition-all duration-700 ${improved ? 'text-green-500' : 'text-gray-400 dark:text-slate-500'} ${animating ? 'translate-x-2' : ''}`}
          />
          {delta !== 0 && (
            <span
              className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                improved
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                  : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
              }`}
            >
              {delta > 0 ? '+' : ''}
              {delta}
            </span>
          )}
        </div>
        <div
          className={`w-20 h-20 rounded-2xl flex items-center justify-center ${gradeBgColor(to)} transition-all duration-500 ${animating ? `scale-110 ring-4 ${gradeRingColor(to)}` : ''}`}
        >
          <span className={`text-4xl font-black ${gradeColor(to)}`}>{to}</span>
        </div>
      </div>
      {improved && (
        <p className="text-xs text-green-600 dark:text-green-400 font-medium flex items-center gap-1">
          <TrendingUp className="w-3 h-3" />
          {t('simulator.improvement') || 'Improvement'}
        </p>
      )}
    </div>
  );
}

function DeltaRow({ label, delta, format }: { label: string; delta: number; format: 'percent' | 'integer' }) {
  const positive = delta > 0;
  const displayValue =
    format === 'percent' ? `${positive ? '+' : ''}${(delta * 100).toFixed(1)}%` : `${positive ? '+' : ''}${delta}`;

  return (
    <div className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700/30 transition-colors">
      <span className="text-xs text-gray-600 dark:text-slate-400">{label}</span>
      <div className="flex items-center gap-1.5">
        {deltaArrow(delta)}
        <span
          className={`text-sm font-semibold ${positive ? 'text-green-600 dark:text-green-400' : delta < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-500 dark:text-slate-400'}`}
        >
          {displayValue}
        </span>
      </div>
    </div>
  );
}

function CostBenefitSummary({ result, totalCost }: { result: SimulationResult; totalCost: number }) {
  const { t } = useTranslation();
  const gradeDelta = gradeNumericDelta(result.current_state.passport_grade, result.projected_state.passport_grade);
  const costPerGradePoint = gradeDelta > 0 && totalCost > 0 ? totalCost / gradeDelta : null;
  const trustGain = result.impact_summary.trust_delta;
  const estimatedCost = result.impact_summary.estimated_total_cost ?? totalCost;

  return (
    <div className="space-y-4">
      {/* Total cost */}
      <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg border border-blue-100 dark:border-blue-900/40">
        <p className="text-xs text-blue-700 dark:text-blue-300 mb-1 font-medium">
          {t('simulator.total_cost') || 'Total Cost'}
        </p>
        <p className="text-2xl font-bold text-blue-900 dark:text-blue-100">
          CHF {estimatedCost.toLocaleString('de-CH')}
        </p>
      </div>

      {/* Grade improvement + cost per grade point */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg text-center border border-gray-100 dark:border-slate-600">
          <Award className="w-5 h-5 mx-auto mb-1 text-yellow-500" />
          <p
            className={`text-lg font-bold ${gradeDelta > 0 ? 'text-green-600 dark:text-green-400' : 'text-gray-900 dark:text-white'}`}
          >
            {gradeDelta > 0 ? `+${gradeDelta}` : gradeDelta === 0 ? '0' : gradeDelta}
          </p>
          <p className="text-xs text-gray-500 dark:text-slate-400">{t('simulator.grade_change') || 'Grade Change'}</p>
        </div>
        <div className="p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg text-center border border-gray-100 dark:border-slate-600">
          <BarChart3 className="w-5 h-5 mx-auto mb-1 text-indigo-500" />
          <p className="text-lg font-bold text-gray-900 dark:text-white">
            {costPerGradePoint ? `CHF ${Math.round(costPerGradePoint).toLocaleString('de-CH')}` : '--'}
          </p>
          <p className="text-xs text-gray-500 dark:text-slate-400">
            {t('simulator.cost_per_grade_point') || 'Cost / Grade Point'}
          </p>
        </div>
      </div>

      {/* Readiness improvement */}
      <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg border border-gray-100 dark:border-slate-600">
        <span className="text-sm text-gray-600 dark:text-slate-400 flex items-center gap-1.5">
          <CheckCircle2 className="w-4 h-4 text-green-500" />
          {t('simulator.readiness_improvement') || 'Readiness'}
        </span>
        <span className="text-sm font-semibold text-gray-900 dark:text-white">
          {result.impact_summary.readiness_improvement}
        </span>
      </div>

      {/* Trust delta bar */}
      {trustGain !== 0 && (
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-600 dark:text-slate-400 w-16">{t('passport.trust') || 'Trust'}</span>
          <div className="flex-1 bg-gray-200 dark:bg-slate-600 rounded-full h-3 relative overflow-hidden">
            <div
              className="absolute left-0 top-0 h-3 bg-blue-200 dark:bg-blue-800 rounded-full"
              style={{ width: `${result.current_state.trust_score * 100}%` }}
            />
            <div
              className="absolute left-0 top-0 h-3 bg-gradient-to-r from-blue-500 to-blue-400 dark:from-blue-500 dark:to-blue-300 rounded-full transition-all duration-700"
              style={{ width: `${result.projected_state.trust_score * 100}%` }}
            />
          </div>
          <span
            className={`text-xs font-medium ${trustGain > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}
          >
            {trustGain > 0 ? '+' : ''}
            {(trustGain * 100).toFixed(1)}%
          </span>
        </div>
      )}
    </div>
  );
}

function TimelineProjection({ interventions }: { interventions: ExtendedSimulationInput[] }) {
  const { t } = useTranslation();
  const items = interventions.filter((i) => (i.timeline_weeks ?? 0) > 0);
  const maxWeeks = Math.max(1, ...items.map((i) => i.timeline_weeks ?? 0));

  return (
    <div className="space-y-3">
      {items.map((intervention, i) => {
        const weeks = intervention.timeline_weeks ?? 0;
        const pct = (weeks / maxWeeks) * 100;
        const Icon = getInterventionIcon(intervention.intervention_type);
        return (
          <div key={i}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-gray-700 dark:text-slate-300 capitalize flex items-center gap-1.5">
                <Icon className="w-3.5 h-3.5 text-gray-400 dark:text-slate-500" />
                {intervention.intervention_type}
                {intervention.scope ? ` (${intervention.scope})` : ''}
              </span>
              <span className="text-xs font-medium text-gray-500 dark:text-slate-400">
                {weeks} {t('simulator.weeks') || 'weeks'}
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-slate-600 rounded-full h-3 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-500 to-blue-400 dark:from-blue-500 dark:to-blue-300 h-3 rounded-full transition-all duration-700"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
      <div className="pt-2 border-t border-gray-200 dark:border-slate-600">
        <p className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-1.5">
          <Clock className="w-4 h-4 text-blue-500" />
          {t('simulator.total_duration') || 'Total Duration'}:{' '}
          <span className="text-blue-600 dark:text-blue-400">
            {maxWeeks} {t('simulator.weeks') || 'weeks'}
          </span>
        </p>
      </div>
    </div>
  );
}

function RecommendationCard({ text, index, total }: { text: string; index: number; total: number }) {
  const { t } = useTranslation();
  const [added, setAdded] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const impactLevel =
    index === 0
      ? 'high'
      : index < Math.ceil(total / 3)
        ? 'high'
        : index < Math.ceil((total * 2) / 3)
          ? 'medium'
          : 'low';
  const impactColors = {
    high: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-200 dark:border-red-900/40',
    medium:
      'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 border-yellow-200 dark:border-yellow-900/40',
    low: 'bg-gray-100 dark:bg-gray-700/50 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-600',
  };
  const impactLabels = {
    high: t('simulator.high_impact') || 'High Impact',
    medium: t('simulator.medium_impact') || 'Medium Impact',
    low: t('simulator.low_impact') || 'Low Impact',
  };
  const impactIcons = {
    high: <Zap className="w-3 h-3" />,
    medium: <TrendingUp className="w-3 h-3" />,
    low: <Info className="w-3 h-3" />,
  };

  // Estimate effort based on position
  const effortLabels: Record<string, string> = {
    high: t('simulator.effort_high') || '4-8 weeks',
    medium: t('simulator.effort_medium') || '2-4 weeks',
    low: t('simulator.effort_low') || '1-2 weeks',
  };

  return (
    <div
      className={`p-4 rounded-lg border transition-all duration-200 ${
        impactLevel === 'high'
          ? 'bg-red-50/50 dark:bg-red-900/10 border-red-100 dark:border-red-900/30'
          : impactLevel === 'medium'
            ? 'bg-yellow-50/50 dark:bg-yellow-900/10 border-yellow-100 dark:border-yellow-900/30'
            : 'bg-gray-50 dark:bg-slate-700/50 border-gray-200 dark:border-slate-600'
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            impactLevel === 'high'
              ? 'bg-red-100 dark:bg-red-900/30'
              : impactLevel === 'medium'
                ? 'bg-yellow-100 dark:bg-yellow-900/30'
                : 'bg-gray-100 dark:bg-gray-700'
          }`}
        >
          <span
            className={`text-sm font-bold ${
              impactLevel === 'high'
                ? 'text-red-700 dark:text-red-300'
                : impactLevel === 'medium'
                  ? 'text-yellow-700 dark:text-yellow-300'
                  : 'text-gray-600 dark:text-gray-400'
            }`}
          >
            {index + 1}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <p className={`text-sm text-gray-800 dark:text-slate-200 ${expanded ? '' : 'line-clamp-2'}`}>{text}</p>
          {text.length > 120 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-blue-600 dark:text-blue-400 hover:underline mt-1"
            >
              {expanded ? t('simulator.show_less') || 'Show less' : t('simulator.show_more') || 'Show more'}
            </button>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full border ${impactColors[impactLevel]}`}
            >
              {impactIcons[impactLevel]}
              {impactLabels[impactLevel]}
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-100 dark:border-blue-900/40">
              <Clock className="w-3 h-3" />
              {effortLabels[impactLevel]}
            </span>
          </div>
        </div>
        <button
          onClick={() => {
            setAdded(true);
            toast(t('simulator.add_to_plan') || 'Added to plan', 'success');
          }}
          disabled={added}
          className={`flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 ${
            added
              ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 cursor-default scale-95'
              : 'bg-white dark:bg-slate-600 text-gray-700 dark:text-slate-200 border border-gray-300 dark:border-slate-500 hover:bg-gray-50 dark:hover:bg-slate-500 hover:shadow-sm'
          }`}
        >
          {added ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5" />
              {t('app.done') || 'Done'}
            </>
          ) : (
            <>
              <Plus className="w-3.5 h-3.5" />
              {t('simulator.add_to_plan') || 'Add to Plan'}
            </>
          )}
        </button>
      </div>
    </div>
  );
}

function ScenarioComparison({ scenarios, bestId }: { scenarios: SavedScenario[]; bestId: string | null }) {
  const { t } = useTranslation();

  // Compute normalized values for visual bars
  const maxTrust = Math.max(...scenarios.map((s) => s.result!.projected_state.trust_score));
  const maxComplete = Math.max(...scenarios.map((s) => s.result!.projected_state.completeness_score));

  return (
    <div className="mt-6 border-t border-gray-200 dark:border-slate-600 pt-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-indigo-500" />
        {t('simulator.scenario_comparison') || 'Scenario Comparison'}
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-slate-600">
              <th className="text-left py-2 pr-4 text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">
                {t('simulator.scenario_name') || 'Scenario'}
              </th>
              {scenarios.map((s) => (
                <th key={s.id} className="text-center py-2 px-3 min-w-[140px]">
                  <div className="flex items-center justify-center gap-1">
                    <span className="text-xs font-semibold text-gray-900 dark:text-white truncate max-w-[100px]">
                      {s.name}
                    </span>
                    {s.id === bestId && (
                      <Star className="w-3.5 h-3.5 text-yellow-500 flex-shrink-0" fill="currentColor" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
            <ComparisonRow
              label={t('passport.grade') || 'Grade'}
              values={scenarios.map((s) => s.result!.projected_state.passport_grade)}
              render={(v) => (
                <span
                  className={`inline-flex items-center justify-center w-8 h-8 rounded-lg font-bold ${gradeBgColor(v)} ${gradeColor(v)}`}
                >
                  {v}
                </span>
              )}
            />
            <ComparisonRowWithBar
              label={t('passport.trust') || 'Trust'}
              values={scenarios.map((s) => s.result!.projected_state.trust_score)}
              maxValue={maxTrust}
              format={(v) => `${(v * 100).toFixed(1)}%`}
              barColor="bg-blue-400 dark:bg-blue-500"
            />
            <ComparisonRowWithBar
              label={t('passport.completeness') || 'Completeness'}
              values={scenarios.map((s) => s.result!.projected_state.completeness_score)}
              maxValue={maxComplete}
              format={(v) => `${(v * 100).toFixed(1)}%`}
              barColor="bg-green-400 dark:bg-green-500"
            />
            <ComparisonRow
              label={t('simulator.total_cost') || 'Cost'}
              values={scenarios.map(
                (s) => 'CHF ' + (s.result!.impact_summary.estimated_total_cost ?? 0).toLocaleString('de-CH'),
              )}
            />
            <ComparisonRow
              label={t('simulator.actions_resolved') || 'Actions Resolved'}
              values={scenarios.map((s) => String(s.result!.impact_summary.actions_resolved))}
            />
            <ComparisonRow
              label={t('readiness.blockers') || 'Remaining Blockers'}
              values={scenarios.map((s) => String(s.result!.projected_state.blocker_count))}
            />
          </tbody>
        </table>
      </div>
      {bestId && (
        <div className="mt-3 px-3 py-2 rounded-lg bg-yellow-50 dark:bg-yellow-900/10 border border-yellow-100 dark:border-yellow-900/30">
          <p className="text-xs text-yellow-800 dark:text-yellow-300 flex items-center gap-1.5 font-medium">
            <Star className="w-3.5 h-3.5 text-yellow-500" fill="currentColor" />
            {t('simulator.best_scenario') || 'Best'}: {scenarios.find((s) => s.id === bestId)?.name}
          </p>
        </div>
      )}
    </div>
  );
}

function ComparisonRow({
  label,
  values,
  render,
}: {
  label: string;
  values: string[];
  render?: (value: string) => React.ReactNode;
}) {
  return (
    <tr>
      <td className="py-2.5 pr-4 text-xs text-gray-600 dark:text-slate-400 whitespace-nowrap">{label}</td>
      {values.map((v, i) => (
        <td key={i} className="py-2.5 px-3 text-center text-sm font-medium text-gray-900 dark:text-white">
          {render ? render(v) : v}
        </td>
      ))}
    </tr>
  );
}

function ComparisonRowWithBar({
  label,
  values,
  maxValue,
  format,
  barColor,
}: {
  label: string;
  values: number[];
  maxValue: number;
  format: (v: number) => string;
  barColor: string;
}) {
  return (
    <tr>
      <td className="py-2.5 pr-4 text-xs text-gray-600 dark:text-slate-400 whitespace-nowrap">{label}</td>
      {values.map((v, i) => (
        <td key={i} className="py-2.5 px-3">
          <div className="flex flex-col items-center gap-1">
            <span className="text-sm font-medium text-gray-900 dark:text-white">{format(v)}</span>
            <div className="w-full bg-gray-200 dark:bg-slate-600 rounded-full h-1.5 overflow-hidden">
              <div
                className={`${barColor} h-1.5 rounded-full transition-all duration-500`}
                style={{ width: `${maxValue > 0 ? (v / maxValue) * 100 : 0}%` }}
              />
            </div>
          </div>
        </td>
      ))}
    </tr>
  );
}
