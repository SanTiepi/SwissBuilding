import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { certificateApi, type CertificateContent } from '@/api/certificates';
import { proofOfStateApi } from '@/api/proofOfState';

interface CertificateGeneratorProps {
  buildingId: string;
  onGenerated?: (certificate: CertificateContent) => void;
}

const CERTIFICATE_TYPES = ['standard', 'authority', 'transaction'] as const;
type CertificateType = (typeof CERTIFICATE_TYPES)[number];

export function CertificateGenerator({ buildingId, onGenerated }: CertificateGeneratorProps) {
  const { t } = useTranslation();
  const [selectedType, setSelectedType] = useState<CertificateType>('standard');

  // Preview: fetch current scores
  const { data: preview } = useQuery({
    queryKey: ['proof-of-state-summary', buildingId],
    queryFn: () => proofOfStateApi.getProofOfStateSummary(buildingId),
  });

  const mutation = useMutation({
    mutationFn: () => certificateApi.generate(buildingId, selectedType),
    onSuccess: (data) => {
      onGenerated?.(data);
    },
  });

  const typeDescriptions: Record<CertificateType, string> = {
    standard: t('certificate.type_standard_desc') || 'General building state certification',
    authority:
      t('certificate.type_authority_desc') || 'Formatted for cantonal authority submission',
    transaction:
      t('certificate.type_transaction_desc') ||
      'Complete dossier for sale, insurance, or financing',
  };

  const evidenceScore = preview?.evidence_score as { score?: number; grade?: string } | null;
  const passportGrade = (preview?.passport as { passport_grade?: string } | null)?.passport_grade;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
        {t('certificate.generate') || 'Generate BatiConnect Certificate'}
      </h3>

      {/* Type selector */}
      <div className="mb-4 space-y-2">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          {t('certificate.type') || 'Certificate Type'}
        </label>
        <div className="space-y-2">
          {CERTIFICATE_TYPES.map((type) => (
            <label
              key={type}
              className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors ${
                selectedType === type
                  ? 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-900/20'
                  : 'border-gray-200 hover:border-gray-300 dark:border-gray-600 dark:hover:border-gray-500'
              }`}
            >
              <input
                type="radio"
                name="certificateType"
                value={type}
                checked={selectedType === type}
                onChange={() => setSelectedType(type)}
                className="mt-1"
              />
              <div>
                <span className="block font-medium text-gray-900 dark:text-white">
                  {t(`certificate.type_${type}`) || type}
                </span>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {typeDescriptions[type]}
                </span>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Preview scores */}
      {preview && (
        <div className="mb-4 rounded-lg bg-gray-50 p-4 dark:bg-gray-700/50">
          <h4 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
            {t('certificate.preview') || 'Current Building State'}
          </h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-gray-500 dark:text-gray-400">
                {t('certificate.evidence') || 'Evidence Score'}:
              </span>{' '}
              <span className="font-medium text-gray-900 dark:text-white">
                {evidenceScore?.score ?? '--'} ({evidenceScore?.grade ?? '--'})
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">
                {t('certificate.passport') || 'Passport Grade'}:
              </span>{' '}
              <span className="font-medium text-gray-900 dark:text-white">
                {passportGrade ?? '--'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {mutation.isError && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">
          {t('app.error') || 'An error occurred'}
        </div>
      )}

      {/* Generate button */}
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="w-full rounded-lg bg-blue-600 px-4 py-3 font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
      >
        {mutation.isPending
          ? (t('certificate.generating') || 'Generating...')
          : (t('certificate.generate') || 'Generate BatiConnect Certificate')}
      </button>
    </div>
  );
}
