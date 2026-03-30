import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { CertificateCard } from '../CertificateCard';
import type { CertificateContent } from '@/api/certificates';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/api/certificates', async () => {
  const actual = await vi.importActual('@/api/certificates');
  return {
    ...actual,
    certificateApi: {
      downloadJson: vi.fn(),
    },
  };
});

afterEach(cleanup);

function buildCertificate(overrides: Partial<CertificateContent> = {}): CertificateContent {
  return {
    certificate_id: 'cert-001',
    certificate_number: 'BC-2026-00001',
    certificate_type: 'standard',
    version: '1.0',
    issued_at: '2026-03-30T10:00:00+00:00',
    valid_until: '2026-06-28T10:00:00+00:00',
    building: { address: 'Rue Test 1', city: 'Lausanne', canton: 'VD' },
    evidence_score: { score: 72, grade: 'B' },
    passport_grade: 'C',
    completeness: 65.0,
    trust_score: 0.58,
    readiness_summary: null,
    key_findings: ['1 readiness-blocking unknown(s) detected'],
    document_coverage: { diagnostic_report: 2 },
    certification_chain: null,
    verification_url: '/verify/cert-001',
    verification_qr_data: '/verify/cert-001',
    issuer: 'BatiConnect by Batiscan Sarl',
    disclaimer: 'This certificate reflects data state at issuance.',
    integrity_hash: 'abc123',
    ...overrides,
  };
}

describe('CertificateCard', () => {
  it('renders certificate number and issuer', () => {
    render(<CertificateCard certificate={buildCertificate()} />);
    expect(screen.getByText('BC-2026-00001')).toBeDefined();
    expect(screen.getByText('BatiConnect by Batiscan Sarl')).toBeDefined();
  });

  it('shows active status for non-expired certificate', () => {
    render(<CertificateCard certificate={buildCertificate()} />);
    const badge = screen.getByTestId('status-badge');
    expect(badge.textContent).toContain('certificate.active');
  });

  it('shows expired status for expired certificate', () => {
    render(
      <CertificateCard
        certificate={buildCertificate({
          valid_until: '2020-01-01T00:00:00+00:00',
        })}
      />,
    );
    const badge = screen.getByTestId('status-badge');
    expect(badge.textContent).toContain('certificate.expired');
  });

  it('renders evidence score and passport grade', () => {
    render(<CertificateCard certificate={buildCertificate()} />);
    expect(screen.getByText('72')).toBeDefined();
    expect(screen.getByText('C')).toBeDefined();
  });

  it('renders key findings', () => {
    render(<CertificateCard certificate={buildCertificate()} />);
    expect(screen.getByText('1 readiness-blocking unknown(s) detected')).toBeDefined();
  });

  it('renders download and share buttons', () => {
    render(<CertificateCard certificate={buildCertificate()} />);
    expect(screen.getByTestId('download-btn')).toBeDefined();
    expect(screen.getByTestId('share-btn')).toBeDefined();
  });

  it('renders disclaimer', () => {
    render(<CertificateCard certificate={buildCertificate()} />);
    expect(screen.getByText('This certificate reflects data state at issuance.')).toBeDefined();
  });
});
