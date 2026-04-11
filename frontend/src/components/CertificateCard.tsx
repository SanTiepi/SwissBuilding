import { useTranslation } from '@/i18n';
import { certificateApi, type CertificateContent } from '@/api/certificates';

interface CertificateCardProps {
  certificate: CertificateContent;
}

function isExpired(validUntil: string): boolean {
  return new Date(validUntil) < new Date();
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

export function CertificateCard({ certificate }: CertificateCardProps) {
  const { t } = useTranslation();
  const expired = isExpired(certificate.valid_until);

  const handleCopyLink = () => {
    const url = `${window.location.origin}/verify/${certificate.certificate_id}`;
    navigator.clipboard.writeText(url);
  };

  const handleDownload = () => {
    certificateApi.downloadJson(certificate);
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      {/* Header */}
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">
            {certificate.certificate_number}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {certificate.issuer}
          </p>
        </div>
        <span
          data-testid="status-badge"
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
            expired
              ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
              : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
          }`}
        >
          {expired
            ? (t('certificate.expired') || 'Expired')
            : (t('certificate.active') || 'Active')}
        </span>
      </div>

      {/* Building info */}
      {certificate.building && (
        <div className="mb-3 text-sm text-gray-600 dark:text-gray-400">
          {(certificate.building as { address?: string }).address},{' '}
          {(certificate.building as { city?: string }).city}
        </div>
      )}

      {/* Scores grid */}
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg bg-gray-50 p-3 text-center dark:bg-gray-700/50">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {certificate.evidence_score?.score ?? '--'}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {t('certificate.evidence') || 'Evidence'} ({certificate.evidence_score?.grade ?? '--'})
          </div>
        </div>
        <div className="rounded-lg bg-gray-50 p-3 text-center dark:bg-gray-700/50">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {certificate.passport_grade ?? '--'}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {t('certificate.passport') || 'Passport'}
          </div>
        </div>
        <div className="rounded-lg bg-gray-50 p-3 text-center dark:bg-gray-700/50">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {certificate.completeness != null ? `${certificate.completeness}%` : '--'}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {t('certificate.completeness') || 'Completeness'}
          </div>
        </div>
        <div className="rounded-lg bg-gray-50 p-3 text-center dark:bg-gray-700/50">
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {certificate.trust_score != null
              ? `${Math.round(certificate.trust_score * 100)}%`
              : '--'}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {t('certificate.trust') || 'Trust'}
          </div>
        </div>
      </div>

      {/* Key findings */}
      {certificate.key_findings && certificate.key_findings.length > 0 && (
        <div className="mb-4">
          <h4 className="mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">
            {t('certificate.findings') || 'Key Findings'}
          </h4>
          <ul className="space-y-1">
            {certificate.key_findings.map((finding, i) => (
              <li key={i} className="flex items-start gap-1.5 text-sm text-gray-600 dark:text-gray-400">
                <span className="mt-0.5 text-amber-500">&#x26a0;</span>
                {finding}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Valid until */}
      <div className="mb-4 text-sm">
        <span className="text-gray-500 dark:text-gray-400">
          {t('certificate.valid_until') || 'Valid until'}:
        </span>{' '}
        <span
          className={`font-medium ${expired ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white'}`}
        >
          {formatDate(certificate.valid_until)}
        </span>
        {expired && (
          <span className="ml-2 text-xs text-red-500">
            ({t('certificate.expired') || 'Expired'})
          </span>
        )}
      </div>

      {/* Verification URL */}
      <div className="mb-4 rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
        <div className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">
          {t('certificate.verify') || 'Verification'}
        </div>
        <code className="break-all text-xs text-gray-700 dark:text-gray-300">
          {certificate.verification_url}
        </code>
      </div>

      {/* Disclaimer */}
      <p className="mb-4 text-xs italic text-gray-400 dark:text-gray-500">
        {certificate.disclaimer}
      </p>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleDownload}
          data-testid="download-btn"
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
        >
          {t('certificate.download') || 'Download JSON'}
        </button>
        <button
          onClick={handleCopyLink}
          data-testid="share-btn"
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
        >
          {t('certificate.share') || 'Share Link'}
        </button>
      </div>
    </div>
  );
}
