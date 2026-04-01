import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { certificateApi } from '@/api/certificates';

interface CertificateVerificationProps {
  certificateId: string;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function CertificateVerification({ certificateId }: CertificateVerificationProps) {
  const { t } = useTranslation();

  const { data, isLoading, error } = useQuery({
    queryKey: ['certificate-verify', certificateId],
    queryFn: () => certificateApi.verify(certificateId),
  });

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
          <p className="text-gray-500 dark:text-gray-400">
            {t('certificate.verifying') || 'Verifying certificate...'}
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center text-red-600 dark:text-red-400">
          {t('app.error') || 'An error occurred'}
        </div>
      </div>
    );
  }

  const cert = data?.certificate as Record<string, unknown> | null;
  const building = cert?.building as Record<string, string> | null;
  const evidenceScore = cert?.evidence_score as { score?: number; grade?: string } | null;
  const isValid = data?.valid ?? false;

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4 dark:bg-gray-900">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="mb-6 text-center">
          <h1 className="mb-1 text-2xl font-bold text-gray-900 dark:text-white">
            BatiConnect {t('certificate.verify') || 'Certificate Verification'}
          </h1>
        </div>

        {/* Status */}
        <div
          className={`mb-6 rounded-xl p-6 text-center ${
            isValid
              ? 'bg-green-50 dark:bg-green-900/20'
              : 'bg-red-50 dark:bg-red-900/20'
          }`}
        >
          <div className="mb-2 text-5xl">
            {isValid ? '\u2705' : '\u274C'}
          </div>
          <h2
            className={`mb-1 text-xl font-bold ${
              isValid
                ? 'text-green-800 dark:text-green-300'
                : 'text-red-800 dark:text-red-300'
            }`}
          >
            {isValid
              ? (t('certificate.verified') || 'Certificate Valid')
              : (t('certificate.invalid') || 'Certificate Invalid')}
          </h2>
          <p
            className={`text-sm ${
              isValid
                ? 'text-green-600 dark:text-green-400'
                : 'text-red-600 dark:text-red-400'
            }`}
          >
            {data?.reason}
          </p>
        </div>

        {/* Certificate details */}
        {cert && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-4 space-y-3">
              <div>
                <span className="text-xs font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
                  {t('certificate.certificate_number') || 'Certificate Number'}
                </span>
                <p className="text-lg font-bold text-gray-900 dark:text-white">
                  {cert.certificate_number as string}
                </p>
              </div>

              {building && (
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    {t('certificate.building') || 'Building'}
                  </span>
                  <p className="text-gray-900 dark:text-white">
                    {building.address}, {building.city}
                  </p>
                  {building.egid && (
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      EGID: {building.egid}
                    </p>
                  )}
                </div>
              )}

              {/* Scores */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    {t('certificate.evidence') || 'Evidence Score'}
                  </span>
                  <p className="text-lg font-bold text-gray-900 dark:text-white">
                    {evidenceScore?.score ?? '--'}{' '}
                    <span className="text-sm font-normal text-gray-500">
                      ({evidenceScore?.grade ?? '--'})
                    </span>
                  </p>
                </div>
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    {t('certificate.passport') || 'Passport Grade'}
                  </span>
                  <p className="text-lg font-bold text-gray-900 dark:text-white">
                    {(cert.passport_grade as string) ?? '--'}
                  </p>
                </div>
              </div>

              {/* Dates */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    {t('certificate.issued') || 'Issued'}
                  </span>
                  <p className="text-sm text-gray-900 dark:text-white">
                    {formatDate(cert.issued_at as string)}
                  </p>
                </div>
                <div>
                  <span className="text-xs font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    {t('certificate.valid_until') || 'Valid Until'}
                  </span>
                  <p className="text-sm text-gray-900 dark:text-white">
                    {formatDate(cert.valid_until as string)}
                  </p>
                </div>
              </div>

              {/* Integrity */}
              <div>
                <span className="text-xs font-medium uppercase tracking-wider text-gray-400 dark:text-gray-500">
                  {t('certificate.integrity') || 'Integrity Hash'}
                </span>
                <code className="block break-all text-xs text-gray-600 dark:text-gray-400">
                  {cert.integrity_hash as string}
                </code>
              </div>
            </div>

            {/* Disclaimer */}
            <p className="mt-4 border-t border-gray-200 pt-4 text-xs italic text-gray-400 dark:border-gray-700 dark:text-gray-500">
              {(cert.disclaimer as string) || t('certificate.disclaimer')}
            </p>
          </div>
        )}

        {/* Footer */}
        <div className="mt-6 text-center text-sm text-gray-400 dark:text-gray-500">
          Powered by{' '}
          <a
            href="https://baticonnect.ch"
            className="font-medium text-blue-500 hover:text-blue-600 dark:text-blue-400"
            target="_blank"
            rel="noopener noreferrer"
          >
            BatiConnect
          </a>
        </div>
      </div>
    </div>
  );
}
