import { useState } from 'react';
import { useComplianceScan } from '@/hooks/useComplianceScan';
import ComplianceFinding from '@/components/ComplianceFinding';
import { Loader2, RefreshCw, ShieldCheck, ShieldAlert, ShieldQuestion } from 'lucide-react';

interface ComplianceScanPanelProps {
  buildingId: string;
}

export default function ComplianceScanPanel({ buildingId }: ComplianceScanPanelProps) {
  const [force, setForce] = useState(false);
  const { data, isLoading, isError, error, refetch } = useComplianceScan(buildingId, force);

  const handleRefresh = () => {
    setForce(true);
    refetch();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 p-8 text-gray-500" data-testid="scan-loading">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span>Running compliance scan...</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300" data-testid="scan-error">
        Compliance scan failed: {error instanceof Error ? error.message : 'Unknown error'}
      </div>
    );
  }

  if (!data) return null;

  const { findings_count, findings, compliance_score, total_checks_executed, scanned_at } = data;
  const scorePercent = Math.round(compliance_score * 100);
  const scoreColor =
    scorePercent >= 80
      ? 'text-green-600 dark:text-green-400'
      : scorePercent >= 60
        ? 'text-yellow-600 dark:text-yellow-400'
        : 'text-red-600 dark:text-red-400';

  const nonConformities = findings.filter((f) => f.type === 'non_conformity');
  const warnings = findings.filter((f) => f.type === 'warning');
  const unknowns = findings.filter((f) => f.type === 'unknown');

  return (
    <div className="space-y-6" data-testid="compliance-scan-panel">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Compliance Scan</h3>
        <button
          onClick={handleRefresh}
          className="flex items-center gap-1.5 rounded-md bg-gray-100 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          data-testid="scan-refresh"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-lg border bg-white p-4 dark:bg-gray-900 dark:border-gray-700" data-testid="score-card">
          <div className={`text-3xl font-bold ${scoreColor}`}>{scorePercent}%</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">Compliance score</div>
          <div className="text-xs text-gray-400 dark:text-gray-500">{total_checks_executed} checks</div>
        </div>
        <div className="flex items-center gap-3 rounded-lg border bg-white p-4 dark:bg-gray-900 dark:border-gray-700" data-testid="nc-count">
          <ShieldAlert className="h-8 w-8 text-red-500" />
          <div>
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">{findings_count.non_conformities}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Non-conformities</div>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-lg border bg-white p-4 dark:bg-gray-900 dark:border-gray-700" data-testid="warn-count">
          <ShieldCheck className="h-8 w-8 text-orange-500" />
          <div>
            <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">{findings_count.warnings}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Warnings</div>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-lg border bg-white p-4 dark:bg-gray-900 dark:border-gray-700" data-testid="unk-count">
          <ShieldQuestion className="h-8 w-8 text-yellow-500" />
          <div>
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{findings_count.unknowns}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Data gaps</div>
          </div>
        </div>
      </div>

      {/* Findings lists */}
      {nonConformities.length > 0 && (
        <section>
          <h4 className="mb-2 text-sm font-semibold text-red-700 dark:text-red-400">
            Non-conformities ({nonConformities.length})
          </h4>
          <div className="space-y-2">
            {nonConformities.map((f, i) => (
              <ComplianceFinding key={`nc-${i}`} finding={f} />
            ))}
          </div>
        </section>
      )}

      {warnings.length > 0 && (
        <section>
          <h4 className="mb-2 text-sm font-semibold text-orange-700 dark:text-orange-400">
            Warnings ({warnings.length})
          </h4>
          <div className="space-y-2">
            {warnings.map((f, i) => (
              <ComplianceFinding key={`warn-${i}`} finding={f} />
            ))}
          </div>
        </section>
      )}

      {unknowns.length > 0 && (
        <section>
          <h4 className="mb-2 text-sm font-semibold text-yellow-700 dark:text-yellow-400">
            Data gaps ({unknowns.length})
          </h4>
          <div className="space-y-2">
            {unknowns.map((f, i) => (
              <ComplianceFinding key={`unk-${i}`} finding={f} />
            ))}
          </div>
        </section>
      )}

      {findings.length === 0 && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-6 text-center dark:border-green-800 dark:bg-green-950" data-testid="all-clear">
          <ShieldCheck className="mx-auto h-10 w-10 text-green-500" />
          <p className="mt-2 font-medium text-green-700 dark:text-green-300">All checks passed</p>
          <p className="text-sm text-green-600 dark:text-green-400">{total_checks_executed} regulatory checks executed</p>
        </div>
      )}

      {/* Footer */}
      <div className="text-xs text-gray-400 dark:text-gray-500">
        Scanned at {new Date(scanned_at).toLocaleString()} — Canton {data.canton}
      </div>
    </div>
  );
}
