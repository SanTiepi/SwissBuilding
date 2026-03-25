import { useTranslation } from '@/i18n';
import { ShieldCheck, CheckCircle2, XCircle } from 'lucide-react';

export interface CounterproofObjection {
  objection: string;
  workflow: string;
  proof_surface: string;
  evidence_available: boolean;
}

interface BuyerCounterproofCardProps {
  objections: CounterproofObjection[];
}

export function BuyerCounterproofCard({ objections }: BuyerCounterproofCardProps) {
  const { t } = useTranslation();

  if (objections.length === 0) return null;

  return (
    <div
      className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden"
      data-testid="buyer-counterproof-card"
    >
      <div className="px-6 py-4 border-b border-gray-200 dark:border-slate-700">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-red-600" />
          {t('counterproof.title')}
        </h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm" data-testid="counterproof-table">
          <thead className="bg-gray-50 dark:bg-slate-700/50">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                {t('counterproof.objection')}
              </th>
              <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                {t('counterproof.workflow')}
              </th>
              <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                {t('counterproof.proof_surface')}
              </th>
              <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                {t('counterproof.available')}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-slate-700">
            {objections.map((obj, idx) => (
              <tr key={idx} data-testid={`counterproof-row-${idx}`}>
                <td className="px-4 py-3 text-gray-900 dark:text-white">{obj.objection}</td>
                <td className="px-4 py-3 text-gray-700 dark:text-slate-300">{obj.workflow}</td>
                <td className="px-4 py-3 text-gray-700 dark:text-slate-300">{obj.proof_surface}</td>
                <td className="px-4 py-3">
                  {obj.evidence_available ? (
                    <CheckCircle2 className="w-5 h-5 text-green-500" data-testid="evidence-yes" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-400" data-testid="evidence-no" />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default BuyerCounterproofCard;
