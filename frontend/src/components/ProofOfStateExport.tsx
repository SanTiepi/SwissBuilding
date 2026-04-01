import { useState } from 'react';
import { useTranslation } from '@/i18n';
import { proofOfStateApi, type ProofOfStateResponse, type ProofOfStateSummaryResponse } from '@/api/proofOfState';

interface ProofOfStateExportProps {
  buildingId: string;
}

type ExportMode = 'full' | 'summary';

export function ProofOfStateExport({ buildingId }: ProofOfStateExportProps) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<ExportMode>('full');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<ProofOfStateResponse | ProofOfStateSummaryResponse | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setPreview(null);
    try {
      if (mode === 'full') {
        const data = await proofOfStateApi.getProofOfState(buildingId);
        setPreview(data);
      } else {
        const data = await proofOfStateApi.getProofOfStateSummary(buildingId);
        setPreview(data);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    setLoading(true);
    try {
      await proofOfStateApi.downloadProofOfState(buildingId, mode === 'summary');
    } finally {
      setLoading(false);
    }
  };

  const evidenceScore = preview?.evidence_score as Record<string, unknown> | null;
  const passport = preview?.passport as Record<string, unknown> | null;
  const completeness =
    preview && 'completeness' in preview ? (preview.completeness as Record<string, unknown> | null) : null;
  const readiness = preview?.readiness as Record<string, unknown> | null;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        {t('proof_of_state.title') || 'Proof of State Export'}
      </h3>

      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => setMode('full')}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
            mode === 'full'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
          }`}
        >
          {t('proof_of_state.export_full') || 'Full Dossier'}
        </button>
        <button
          type="button"
          onClick={() => setMode('summary')}
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
            mode === 'summary'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
          }`}
        >
          {t('proof_of_state.export_summary') || 'Summary'}
        </button>
      </div>

      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={handleGenerate}
          disabled={loading}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? t('proof_of_state.generating') || 'Generating...' : t('proof_of_state.preview') || 'Preview'}
        </button>
        <button
          type="button"
          onClick={handleDownload}
          disabled={loading}
          className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          {t('proof_of_state.download') || 'Download'}
        </button>
      </div>

      {preview && (
        <div className="mt-4 space-y-2 rounded-md border border-gray-100 bg-gray-50 p-3 dark:border-gray-600 dark:bg-gray-900">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t('proof_of_state.format_version') || 'Format version'}: {preview.metadata.format_version}
          </p>
          {evidenceScore && (
            <p className="text-sm text-gray-700 dark:text-gray-300">
              Evidence Score: <span className="font-semibold">{String(evidenceScore.score ?? '-')}</span> (
              {String(evidenceScore.grade ?? '-')})
            </p>
          )}
          {passport && (
            <p className="text-sm text-gray-700 dark:text-gray-300">
              Passport Grade: <span className="font-semibold">{String(passport.passport_grade ?? '-')}</span>
            </p>
          )}
          {completeness && (
            <p className="text-sm text-gray-700 dark:text-gray-300">
              Completeness:{' '}
              <span className="font-semibold">{Math.round(Number(completeness.overall_score ?? 0) * 100)}%</span>
            </p>
          )}
          {readiness && (
            <p className="text-sm text-gray-700 dark:text-gray-300">
              Readiness:{' '}
              <span className="font-semibold">
                {String((readiness.safe_to_start as Record<string, unknown>)?.status ?? 'not_evaluated')}
              </span>
            </p>
          )}
          <p className="text-xs text-gray-400 dark:text-gray-500">
            {t('proof_of_state.integrity_hash') || 'Integrity hash'}: {preview.integrity.hash.substring(0, 16)}...
          </p>
        </div>
      )}
    </div>
  );
}
