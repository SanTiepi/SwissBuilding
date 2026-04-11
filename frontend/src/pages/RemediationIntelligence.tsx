/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view under Admin (remediation intelligence).
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuth } from '@/hooks/useAuth';
import { remediationIntelligenceApi } from '@/api/remediationIntelligence';
import type {
  FlywheelTrendPoint,
  ModuleLearningOverview,
  RemediationBenchmarkSnapshot,
} from '@/api/remediationIntelligence';
import { BarChart3, TrendingUp, Brain, Activity } from 'lucide-react';

function BenchmarkCard({ benchmark }: { benchmark: RemediationBenchmarkSnapshot | undefined }) {
  if (!benchmark) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        <BarChart3 className="w-5 h-5 text-blue-600" />
        Remediation Benchmark
      </h3>
      <div className="grid grid-cols-3 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">{benchmark.overall_avg_cost_chf.toLocaleString()}</div>
          <div className="text-xs text-gray-500">Avg Cost (CHF)</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">{benchmark.overall_avg_cycle_days}</div>
          <div className="text-xs text-gray-500">Avg Cycle (days)</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-600">
            {Math.round(benchmark.overall_completion_rate * 100)}%
          </div>
          <div className="text-xs text-gray-500">Completion Rate</div>
        </div>
      </div>
      {benchmark.benchmarks.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-2">Type</th>
                <th className="text-right py-2">Avg Cost</th>
                <th className="text-right py-2">Cycle (d)</th>
                <th className="text-right py-2">Rate</th>
                <th className="text-right py-2">N</th>
              </tr>
            </thead>
            <tbody>
              {benchmark.benchmarks.map((b) => (
                <tr key={b.pollutant} className="border-b border-gray-100 dark:border-gray-800">
                  <td className="py-1.5">{b.pollutant}</td>
                  <td className="text-right">{b.avg_cost_chf.toLocaleString()}</td>
                  <td className="text-right">{b.avg_cycle_days}</td>
                  <td className="text-right">{Math.round(b.completion_rate * 100)}%</td>
                  <td className="text-right text-gray-400">{b.sample_size}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function FlywheelChart({ trends }: { trends: FlywheelTrendPoint[] }) {
  if (trends.length === 0) return null;

  const maxQuality = Math.max(...trends.map((t) => t.extraction_quality), 0.01);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        <TrendingUp className="w-5 h-5 text-green-600" />
        Flywheel Trends
      </h3>
      <div className="space-y-2">
        {trends.map((t) => (
          <div key={t.date} className="flex items-center gap-3">
            <span className="text-xs font-mono text-gray-500 w-20">{t.date}</span>
            <div className="flex-1 flex items-center gap-2">
              <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full"
                  style={{ width: `${(t.extraction_quality / maxQuality) * 100}%` }}
                />
              </div>
              <span className="text-xs text-gray-500">Q:{(t.extraction_quality * 100).toFixed(0)}%</span>
              <span className="text-xs text-gray-500">C:{(t.correction_rate * 100).toFixed(0)}%</span>
              <span className="text-xs text-gray-500">D:{(t.knowledge_density * 100).toFixed(0)}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function LearningOverviewCard({ overview }: { overview: ModuleLearningOverview | undefined }) {
  if (!overview) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        <Brain className="w-5 h-5 text-purple-600" />
        Module Learning Overview
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold">{overview.total_patterns}</div>
          <div className="text-xs text-gray-500">Patterns</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold">{Math.round(overview.extraction_success_rate * 100)}%</div>
          <div className="text-xs text-gray-500">Success Rate</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold">{Math.round(overview.avg_confidence * 100)}%</div>
          <div className="text-xs text-gray-500">Avg Confidence</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold">{overview.total_extractions}</div>
          <div className="text-xs text-gray-500">Total Extractions</div>
        </div>
      </div>
      {overview.top_correction_categories.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Top Correction Categories</h4>
          <div className="flex flex-wrap gap-2">
            {overview.top_correction_categories.map((c) => (
              <span
                key={c.category}
                className="text-xs bg-purple-50 dark:bg-purple-900 text-purple-700 dark:text-purple-300 px-2 py-1 rounded"
              >
                {c.category}: {c.count}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function RemediationIntelligence() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const orgId = user?.organization_id;

  const { data: benchmark } = useQuery({
    queryKey: ['remediation-benchmark', orgId],
    queryFn: () => remediationIntelligenceApi.getRemediationBenchmark(orgId!),
    enabled: !!orgId,
  });

  const { data: trends } = useQuery({
    queryKey: ['flywheel-trends', orgId],
    queryFn: () => remediationIntelligenceApi.getFlywheelTrends(orgId!),
    enabled: !!orgId,
  });

  const { data: learningOverview } = useQuery({
    queryKey: ['module-learning-overview'],
    queryFn: () => remediationIntelligenceApi.getModuleLearningOverview(),
    enabled: user?.role === 'admin',
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Activity className="w-6 h-6 text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          {t('intelligence.title') || 'Remediation Intelligence'}
        </h1>
      </div>

      <BenchmarkCard benchmark={benchmark} />
      <FlywheelChart trends={trends || []} />
      {user?.role === 'admin' && <LearningOverviewCard overview={learningOverview} />}
    </div>
  );
}
