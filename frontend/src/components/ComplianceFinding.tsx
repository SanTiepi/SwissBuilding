import type { ComplianceFindingData } from '@/api/complianceScan';
import { AlertTriangle, XCircle, HelpCircle, Clock, ExternalLink } from 'lucide-react';

const SEVERITY_CONFIG: Record<string, { bg: string; border: string; text: string; icon: typeof XCircle }> = {
  critical: { bg: 'bg-red-50 dark:bg-red-950', border: 'border-red-300 dark:border-red-700', text: 'text-red-700 dark:text-red-300', icon: XCircle },
  high: { bg: 'bg-orange-50 dark:bg-orange-950', border: 'border-orange-300 dark:border-orange-700', text: 'text-orange-700 dark:text-orange-300', icon: AlertTriangle },
  medium: { bg: 'bg-yellow-50 dark:bg-yellow-950', border: 'border-yellow-300 dark:border-yellow-700', text: 'text-yellow-700 dark:text-yellow-300', icon: AlertTriangle },
  low: { bg: 'bg-blue-50 dark:bg-blue-950', border: 'border-blue-300 dark:border-blue-700', text: 'text-blue-700 dark:text-blue-300', icon: HelpCircle },
};

const TYPE_LABELS: Record<string, string> = {
  non_conformity: 'Non-conformity',
  warning: 'Warning',
  unknown: 'Data gap',
};

interface ComplianceFindingProps {
  finding: ComplianceFindingData;
}

export default function ComplianceFinding({ finding }: ComplianceFindingProps) {
  const config = SEVERITY_CONFIG[finding.severity] || SEVERITY_CONFIG.medium;
  const Icon = config.icon;

  return (
    <div className={`rounded-lg border p-4 ${config.bg} ${config.border}`} data-testid="compliance-finding">
      <div className="flex items-start gap-3">
        <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${config.text}`} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-sm font-semibold ${config.text}`}>{finding.rule}</span>
            <span className="rounded-full bg-gray-200 dark:bg-gray-700 px-2 py-0.5 text-xs font-medium text-gray-600 dark:text-gray-300">
              {TYPE_LABELS[finding.type] || finding.type}
            </span>
            <span className={`rounded-full px-2 py-0.5 text-xs font-bold uppercase ${config.text}`}>
              {finding.severity}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">{finding.description}</p>
          {finding.deadline && (
            <div className="mt-2 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="h-3.5 w-3.5" />
              <span>Deadline: {finding.deadline}</span>
            </div>
          )}
          {finding.references.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {finding.references.map((ref) => (
                <span
                  key={ref}
                  className="inline-flex items-center gap-0.5 rounded bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 text-xs text-gray-600 dark:text-gray-400"
                >
                  <ExternalLink className="h-3 w-3" />
                  {ref}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
