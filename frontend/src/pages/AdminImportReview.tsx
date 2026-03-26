import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { exchangeHardeningApi, type ExchangeValidationReport } from '@/api/exchangeHardening';
import { cn } from '@/utils/formatters';
import { Shield, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

const STATUS_STYLE: Record<string, string> = {
  passed: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
  review_required: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400',
  received: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400',
  validated: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
  rejected: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
  integrated: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-400',
};

export default function AdminImportReview() {
  const [validationReport, setValidationReport] = useState<ExchangeValidationReport | null>(null);

  // We don't have a global list endpoint — this page is for building-specific review
  // For now, show the validation UI when a receipt ID is provided
  const [receiptId, setReceiptId] = useState('');

  const validateMutation = useMutation({
    mutationFn: (id: string) => exchangeHardeningApi.validateImport(id),
    onSuccess: (report) => {
      setValidationReport(report);
    },
  });

  const reviewMutation = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: string }) => exchangeHardeningApi.reviewImport(id, decision),
  });

  const integrateMutation = useMutation({
    mutationFn: (id: string) => exchangeHardeningApi.integrateImport(id),
  });

  return (
    <div className="space-y-6" data-testid="admin-import-review">
      <div className="flex items-center gap-3">
        <Shield className="w-6 h-6 text-indigo-500" />
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">{'Import Validation & Review'}</h1>
      </div>

      {/* Receipt ID input */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">{'Validate Import Receipt'}</h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={receiptId}
            onChange={(e) => setReceiptId(e.target.value)}
            placeholder="Import receipt UUID"
            className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
            data-testid="receipt-id-input"
          />
          <button
            onClick={() => {
              if (receiptId) validateMutation.mutate(receiptId);
            }}
            disabled={!receiptId || validateMutation.isPending}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            data-testid="validate-btn"
          >
            {validateMutation.isPending ? 'Validating...' : 'Validate'}
          </button>
        </div>
      </div>

      {/* Validation Report */}
      {validationReport && (
        <div
          className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6"
          data-testid="validation-report"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">{'Validation Report'}</h2>
            <span
              className={cn(
                'px-2.5 py-1 rounded-full text-xs font-medium',
                STATUS_STYLE[validationReport.overall_status] ?? 'bg-gray-100 text-gray-600',
              )}
              data-testid="validation-status"
            >
              {validationReport.overall_status}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-4">
            {[
              { label: 'Schema', value: validationReport.schema_valid },
              { label: 'Contract', value: validationReport.contract_valid },
              { label: 'Version', value: validationReport.version_valid },
              { label: 'Hash', value: validationReport.hash_valid },
              { label: 'Identity', value: validationReport.identity_safe },
            ].map(({ label, value }) => (
              <div
                key={label}
                className="flex items-center gap-1.5 text-sm"
                data-testid={`check-${label.toLowerCase()}`}
              >
                {value ? (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                ) : value === false ? (
                  <XCircle className="w-4 h-4 text-red-500" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-yellow-500" />
                )}
                <span className="text-gray-700 dark:text-gray-300">{label}</span>
              </div>
            ))}
          </div>

          {validationReport.validation_errors && validationReport.validation_errors.length > 0 && (
            <div className="mb-4" data-testid="validation-errors">
              <h3 className="text-xs font-medium text-gray-500 mb-1">{'Errors'}</h3>
              {validationReport.validation_errors.map((err, i) => (
                <div key={i} className="text-xs text-red-600 dark:text-red-400 flex items-center gap-1">
                  <span className="font-medium">[{err.check}]</span>
                  <span>{err.message}</span>
                </div>
              ))}
            </div>
          )}

          {/* Review Actions */}
          <div className="flex gap-2 pt-3 border-t border-gray-100 dark:border-gray-700">
            <button
              onClick={() => reviewMutation.mutate({ id: validationReport.import_receipt_id, decision: 'validated' })}
              className="px-3 py-1.5 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700"
              data-testid="approve-btn"
            >
              {'Approve'}
            </button>
            <button
              onClick={() => reviewMutation.mutate({ id: validationReport.import_receipt_id, decision: 'rejected' })}
              className="px-3 py-1.5 bg-red-600 text-white rounded text-xs font-medium hover:bg-red-700"
              data-testid="reject-btn"
            >
              {'Reject'}
            </button>
            <button
              onClick={() => integrateMutation.mutate(validationReport.import_receipt_id)}
              disabled={validationReport.overall_status !== 'passed'}
              className="px-3 py-1.5 bg-indigo-600 text-white rounded text-xs font-medium hover:bg-indigo-700 disabled:opacity-50"
              data-testid="integrate-btn"
            >
              {'Integrate'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
