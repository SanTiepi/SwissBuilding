import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useBuildings } from '@/hooks/useBuildings';
import { useTranslation } from '@/i18n';
import { cn, formatCHF, formatDate } from '@/utils/formatters';
import { riskApi } from '@/api/risk';
import { savedSimulationsApi } from '@/api/savedSimulations';
import { toast } from '@/store/toastStore';
import type {
  Building,
  RenovationSimulation,
  PollutantRisk,
  ComplianceRequirement,
  RiskLevel,
  SavedSimulation,
} from '@/types';
import { RiskGauge } from '@/components/RiskGauge';
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import {
  Search,
  Play,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Clock,
  DollarSign,
  FileText,
  Scale,
  Hammer,
  Save,
  History,
  Trash2,
  X,
} from 'lucide-react';

const RENOVATION_TYPES = [
  'full_renovation',
  'partial_interior',
  'roof',
  'facade',
  'bathroom',
  'kitchen',
  'flooring',
  'windows',
] as const;

type RenovationType = (typeof RENOVATION_TYPES)[number];

export default function RiskSimulator() {
  const { t } = useTranslation();
  const { data: buildingsData, isLoading: buildingsLoading, isError: buildingsError } = useBuildings();
  const buildings = buildingsData?.items ?? [];

  const [selectedBuildingId, setSelectedBuildingId] = useState('');
  const [renovationType, setRenovationType] = useState<RenovationType>('full_renovation');
  const [buildingSearch, setBuildingSearch] = useState('');
  const [showBuildingDropdown, setShowBuildingDropdown] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState<RenovationSimulation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [saveTitle, setSaveTitle] = useState('');
  const [showHistory, setShowHistory] = useState(false);
  const queryClient = useQueryClient();

  const {
    data: savedSims,
    isLoading: savedSimsLoading,
    isError: savedSimsError,
  } = useQuery({
    queryKey: ['saved-simulations', selectedBuildingId],
    queryFn: () => savedSimulationsApi.list(selectedBuildingId!),
    enabled: !!selectedBuildingId && showHistory,
  });

  const saveMutation = useMutation({
    mutationFn: (data: { title: string }) =>
      savedSimulationsApi.create(selectedBuildingId!, {
        title: data.title,
        simulation_type: 'renovation',
        parameters_json: { building_id: selectedBuildingId, renovation_type: renovationType },
        results_json: simulationResult as unknown as Record<string, unknown>,
        total_cost_chf: simulationResult?.total_estimated_cost_chf,
        total_duration_weeks: simulationResult?.timeline_weeks,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-simulations'] });
      setShowSaveDialog(false);
      setSaveTitle('');
      toast(t('simulation.saved') || 'Simulation saved');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (simId: string) => savedSimulationsApi.delete(selectedBuildingId!, simId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['saved-simulations'] });
      toast(t('simulation.deleted') || 'Simulation deleted');
    },
  });

  const filteredBuildings = Array.isArray(buildings)
    ? buildings
        .filter((b: Building) => {
          if (!buildingSearch) return true;
          const q = buildingSearch.toLowerCase();
          return b.address?.toLowerCase().includes(q) || b.city?.toLowerCase().includes(q);
        })
        .slice(0, 10)
    : [];

  const selectedBuilding = buildings.find((b: Building) => b.id === selectedBuildingId);

  const onSimulate = async () => {
    if (!selectedBuildingId || !renovationType) return;
    setIsSimulating(true);
    setError(null);
    try {
      const result = await riskApi.simulate({
        building_id: selectedBuildingId,
        renovation_type: renovationType,
      });
      setSimulationResult(result);
    } catch (err: any) {
      setError(err?.message || t('app.error'));
    } finally {
      setIsSimulating(false);
    }
  };

  const pollutantChartData = simulationResult?.pollutant_risks
    ? simulationResult.pollutant_risks.map((pr: PollutantRisk) => ({
        pollutant: t(`pollutant.${pr.pollutant}`),
        probability: (pr.probability || 0) * 100,
        key: pr.pollutant,
      }))
    : [];

  const costBreakdown = simulationResult?.pollutant_risks
    ? simulationResult.pollutant_risks.map((pr: PollutantRisk) => ({
        name: t(`pollutant.${pr.pollutant}`) || pr.pollutant,
        cost: pr.estimated_cost_chf || 0,
      }))
    : [];

  const overallRisk: RiskLevel =
    (simulationResult?.pollutant_risks?.reduce((worst: string, pr: PollutantRisk) => {
      const levels = ['low', 'medium', 'high', 'critical'];
      return levels.indexOf(pr.risk_level) > levels.indexOf(worst) ? pr.risk_level : worst;
    }, 'low') as RiskLevel) || 'medium';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('simulation.title')}</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('app.subtitle')}</p>
        </div>
        {selectedBuildingId && (
          <button
            onClick={() => setShowHistory(!showHistory)}
            className={cn(
              'inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border transition-colors',
              showHistory
                ? 'bg-red-600 text-white border-red-600'
                : 'bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200 border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700',
            )}
          >
            <History className="w-4 h-4" />
            {t('simulation.history') || 'History'}
          </button>
        )}
      </div>

      {/* Configuration Panel */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">{t('settings.general')}</h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Building Selector */}
          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1.5">
              {t('building.title')}
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-slate-500" />
              <input
                type="text"
                value={buildingSearch}
                onChange={(e) => {
                  setBuildingSearch(e.target.value);
                  setShowBuildingDropdown(true);
                }}
                onFocus={() => setShowBuildingDropdown(true)}
                placeholder={t('building.search')}
                aria-label={t('building.search')}
                className="w-full pl-9 pr-4 py-2.5 border border-gray-300 dark:border-slate-600 rounded-lg text-sm dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
              />
              {showBuildingDropdown && filteredBuildings.length > 0 && (
                <div className="absolute z-20 w-full mt-1 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                  {filteredBuildings.map((b: Building) => (
                    <button
                      key={b.id}
                      onClick={() => {
                        setSelectedBuildingId(b.id);
                        setBuildingSearch(`${b.address}, ${b.city}`);
                        setShowBuildingDropdown(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-slate-700 border-b border-gray-50 dark:border-slate-700 last:border-0"
                    >
                      <span className="font-medium text-gray-900 dark:text-white">{b.address}</span>
                      <span className="text-gray-500 dark:text-slate-400 ml-1">
                        - {b.postal_code} {b.city} ({b.canton})
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
            {buildingsLoading ? (
              <p className="mt-1.5 text-xs text-gray-500 dark:text-slate-400 flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin" />
                {t('app.loading')}
              </p>
            ) : buildingsError ? (
              <p className="mt-1.5 text-xs text-red-600 dark:text-red-400 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                {t('app.error')}
              </p>
            ) : selectedBuilding ? (
              <p className="mt-1.5 text-xs text-green-600 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                {t('form.success')}
              </p>
            ) : null}
          </div>

          {/* Renovation Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1.5">
              {t('simulation.renovation_type')}
            </label>
            <select
              value={renovationType}
              onChange={(e) => setRenovationType(e.target.value as RenovationType)}
              className="w-full px-3 py-2.5 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              {RENOVATION_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`renovation.${type}`) || type.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>

          {/* Simulate Button */}
          <div className="flex items-end gap-2">
            <button
              onClick={onSimulate}
              disabled={!selectedBuildingId || isSimulating}
              className="flex-1 inline-flex items-center justify-center gap-2 px-6 py-2.5 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              {isSimulating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t('app.loading')}
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  {t('simulation.run')}
                </>
              )}
            </button>
            {simulationResult && (
              <button
                onClick={() => setShowSaveDialog(true)}
                className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition-colors"
              >
                <Save className="w-4 h-4" />
                {t('simulation.save') || 'Save'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 rounded-xl text-red-700 text-sm">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Results */}
      {simulationResult && (
        <div className="space-y-6">
          {/* Overall Risk + Pollutant Chart */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Overall Risk */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm flex flex-col items-center justify-center">
              <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-4">{t('risk.overall')}</h3>
              <RiskGauge level={overallRisk} score={undefined} />
            </div>

            {/* Pollutant Risk Radar */}
            <div className="lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
              <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-4">
                {t('simulation.pollutant_risks')}
              </h3>
              {pollutantChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <RadarChart data={pollutantChartData}>
                    <PolarGrid stroke="#e2e8f0" />
                    <PolarAngleAxis dataKey="pollutant" tick={{ fontSize: 12 }} />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
                    <Radar
                      name={t('risk.probability')}
                      dataKey="probability"
                      stroke="#dc2626"
                      fill="#dc2626"
                      fillOpacity={0.2}
                      strokeWidth={2}
                    />
                    <Tooltip formatter={(val: number) => `${val.toFixed(1)}%`} />
                  </RadarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-center text-sm text-gray-400 dark:text-slate-500 py-8">{t('form.no_results')}</p>
              )}
            </div>
          </div>

          {/* Required Diagnostics + Compliance */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Required Diagnostics */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
              <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-4 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                {t('simulation.required_diagnostics')}
              </h3>
              {simulationResult.required_diagnostics?.length > 0 ? (
                <ul className="space-y-2">
                  {simulationResult.required_diagnostics.map((diag: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 p-3 bg-gray-50 dark:bg-slate-700 rounded-lg">
                      <CheckCircle2 className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">{diag}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-500 dark:text-slate-400">{t('form.no_results')}</p>
              )}
            </div>

            {/* Compliance Requirements */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
              <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-4 flex items-center gap-2">
                <Scale className="w-4 h-4" />
                {t('simulation.compliance')}
              </h3>
              <p className="text-xs text-gray-400 dark:text-slate-500 italic mb-3">
                {t('disclaimer.simulation') ||
                  'Indicative simulation based on available data. Actual costs and timelines may vary.'}
              </p>
              {simulationResult.compliance_requirements?.length > 0 ? (
                <ul className="space-y-2">
                  {simulationResult.compliance_requirements.map((req: ComplianceRequirement, i: number) => (
                    <li key={i} className="p-3 bg-gray-50 dark:bg-slate-700 rounded-lg">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{req.requirement}</p>
                      {req.legal_reference && (
                        <p className="text-xs text-blue-600 mt-0.5 font-mono">{req.legal_reference}</p>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-500 dark:text-slate-400">{t('form.no_results')}</p>
              )}
            </div>
          </div>

          {/* Cost Estimation */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
            <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-4 flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              {t('simulation.estimated_cost')}
            </h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {costBreakdown.length > 0 ? (
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={costBreakdown}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => formatCHF(v)} />
                    <Tooltip formatter={(val: number) => formatCHF(val)} />
                    <Bar dataKey="cost" radius={[6, 6, 0, 0]} fill="#dc2626" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-48 text-gray-500 dark:text-slate-400 text-sm">
                  {t('form.no_results')}
                </div>
              )}
              <div className="space-y-3">
                {costBreakdown.map((item: { name: string; cost: number }, i: number) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-slate-700 rounded-lg"
                  >
                    <span className="text-sm text-gray-700 dark:text-slate-200">{item.name}</span>
                    <span className="text-sm font-semibold text-gray-900 dark:text-white">{formatCHF(item.cost)}</span>
                  </div>
                ))}
                <div className="flex items-center justify-between p-3 bg-red-50 dark:bg-red-900/30 rounded-lg border border-red-100">
                  <span className="text-sm font-semibold text-red-700">{t('simulation.total_cost')}</span>
                  <span className="text-lg font-bold text-red-700">
                    {formatCHF(
                      simulationResult.total_estimated_cost_chf ||
                        costBreakdown.reduce((s: number, c: { name: string; cost: number }) => s + c.cost, 0),
                    )}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Timeline */}
          {simulationResult.timeline_weeks && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
              <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-2 flex items-center gap-2">
                <Clock className="w-4 h-4" />
                {t('simulation.timeline')}
              </h3>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {simulationResult.timeline_weeks} {t('simulation.weeks')}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!simulationResult && !isSimulating && !error && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-12 text-center shadow-sm">
          <Hammer className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-700 dark:text-slate-200 mb-1">{t('simulation.title')}</h3>
          <p className="text-sm text-gray-500 dark:text-slate-400">{t('simulation.run')}</p>
        </div>
      )}

      {/* History Panel */}
      {showHistory && selectedBuildingId && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            {t('simulation.saved_simulations') || 'Saved Simulations'}
          </h2>
          {savedSimsLoading ? (
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              {t('app.loading')}
            </div>
          ) : savedSimsError ? (
            <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
              <AlertTriangle className="w-4 h-4" />
              {t('app.error')}
            </div>
          ) : !savedSims?.items || savedSims.items.length === 0 ? (
            <p className="text-sm text-gray-500 dark:text-slate-400">
              {t('simulation.no_saved') || 'No saved simulations'}
            </p>
          ) : (
            <div className="space-y-3">
              {savedSims.items.map((sim: SavedSimulation) => (
                <div
                  key={sim.id}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg"
                >
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{sim.title}</p>
                    <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-slate-400 mt-1">
                      <span>{formatDate(sim.created_at)}</span>
                      {sim.total_cost_chf != null && <span>CHF {sim.total_cost_chf.toLocaleString()}</span>}
                      {sim.total_duration_weeks != null && (
                        <span>
                          {sim.total_duration_weeks} {t('simulation.weeks') || 'weeks'}
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => deleteMutation.mutate(sim.id)}
                    className="p-1.5 text-gray-400 hover:text-red-500 transition-colors"
                    title={t('form.delete') || 'Delete'}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Save Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-md shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {t('simulation.save_title') || 'Save Simulation'}
              </h3>
              <button onClick={() => setShowSaveDialog(false)}>
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <input
              type="text"
              value={saveTitle}
              onChange={(e) => setSaveTitle(e.target.value)}
              placeholder={t('simulation.name_placeholder') || 'Simulation name...'}
              className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-900 text-gray-900 dark:text-white mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowSaveDialog(false)}
                className="px-4 py-2 text-sm text-gray-700 dark:text-slate-200 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
              >
                {t('form.cancel') || 'Cancel'}
              </button>
              <button
                onClick={() => saveMutation.mutate({ title: saveTitle })}
                disabled={!saveTitle.trim() || saveMutation.isPending}
                className="px-4 py-2 text-sm text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {saveMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : t('form.save') || 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
