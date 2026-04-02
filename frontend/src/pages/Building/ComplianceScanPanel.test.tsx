import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ComplianceScanResponse } from '@/api/complianceScan';

const mockUseComplianceScan = vi.fn();
vi.mock('@/hooks/useComplianceScan', () => ({
  useComplianceScan: (...args: unknown[]) => mockUseComplianceScan(...args),
}));

import ComplianceScanPanel from './ComplianceScanPanel';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

function makeScanResult(overrides: Partial<ComplianceScanResponse> = {}): ComplianceScanResponse {
  return {
    building_id: 'b1',
    canton: 'VD',
    total_checks_executed: 341,
    findings_count: { non_conformities: 0, warnings: 0, unknowns: 0 },
    findings: [],
    compliance_score: 1.0,
    scanned_at: '2026-04-02T10:00:00Z',
    ...overrides,
  };
}

describe('ComplianceScanPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state', () => {
    mockUseComplianceScan.mockReturnValue({ isLoading: true, data: null, isError: false });
    render(<ComplianceScanPanel buildingId="b1" />, { wrapper });
    expect(screen.getByTestId('scan-loading')).toBeTruthy();
  });

  it('shows error state', () => {
    mockUseComplianceScan.mockReturnValue({
      isLoading: false,
      isError: true,
      error: new Error('fail'),
      data: null,
    });
    render(<ComplianceScanPanel buildingId="b1" />, { wrapper });
    expect(screen.getByTestId('scan-error')).toBeTruthy();
    expect(screen.getByText(/fail/)).toBeTruthy();
  });

  it('renders 0 findings — all clear', () => {
    mockUseComplianceScan.mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeScanResult(),
      refetch: vi.fn(),
    });
    render(<ComplianceScanPanel buildingId="b1" />, { wrapper });
    expect(screen.getByTestId('all-clear')).toBeTruthy();
    expect(screen.getByText('100%')).toBeTruthy();
    expect(screen.getByText('341 checks')).toBeTruthy();
  });

  it('renders 1 finding correctly', () => {
    mockUseComplianceScan.mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeScanResult({
        findings_count: { non_conformities: 1, warnings: 0, unknowns: 0 },
        findings: [
          {
            type: 'non_conformity',
            rule: 'OTConst Art. 60a',
            description: 'Pre-1990 building has no diagnostic',
            severity: 'critical',
            deadline: null,
            references: ['OTConst:60a'],
          },
        ],
        compliance_score: 0.72,
      }),
      refetch: vi.fn(),
    });
    render(<ComplianceScanPanel buildingId="b1" />, { wrapper });
    expect(screen.getByText('72%')).toBeTruthy();
    expect(screen.getByText('1')).toBeTruthy(); // non-conformity count
    expect(screen.getByText(/OTConst Art. 60a/)).toBeTruthy();
    expect(screen.getByText(/Pre-1990/)).toBeTruthy();
  });

  it('renders 3 findings with mixed types', () => {
    mockUseComplianceScan.mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeScanResult({
        findings_count: { non_conformities: 1, warnings: 1, unknowns: 1 },
        findings: [
          { type: 'non_conformity', rule: 'OTConst Art. 82', description: 'NC1', severity: 'critical', deadline: null, references: [] },
          { type: 'warning', rule: 'Cantonal', description: 'W1', severity: 'high', deadline: '2026-06-15', references: [] },
          { type: 'unknown', rule: 'ORaP', description: 'U1', severity: 'medium', deadline: null, references: [] },
        ],
        compliance_score: 0.6,
      }),
      refetch: vi.fn(),
    });
    render(<ComplianceScanPanel buildingId="b1" />, { wrapper });
    expect(screen.getByText('60%')).toBeTruthy();
    expect(screen.getByText(/Non-conformities \(1\)/)).toBeTruthy();
    expect(screen.getByText(/Warnings \(1\)/)).toBeTruthy();
    expect(screen.getByText(/Data gaps \(1\)/)).toBeTruthy();
  });

  it('renders 10+ findings', () => {
    const findings = Array.from({ length: 12 }, (_, i) => ({
      type: 'non_conformity' as const,
      rule: `Rule ${i + 1}`,
      description: `Finding ${i + 1}`,
      severity: 'high' as const,
      deadline: null,
      references: [],
    }));
    mockUseComplianceScan.mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeScanResult({
        findings_count: { non_conformities: 12, warnings: 0, unknowns: 0 },
        findings,
        compliance_score: 0.3,
      }),
      refetch: vi.fn(),
    });
    render(<ComplianceScanPanel buildingId="b1" />, { wrapper });
    const findingEls = screen.getAllByTestId('compliance-finding');
    expect(findingEls.length).toBe(12);
  });

  it('severity coloring — critical shows red', () => {
    mockUseComplianceScan.mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeScanResult({
        findings_count: { non_conformities: 1, warnings: 0, unknowns: 0 },
        findings: [
          { type: 'non_conformity', rule: 'Test', description: 'Critical finding', severity: 'critical', deadline: null, references: [] },
        ],
        compliance_score: 0.95,
      }),
      refetch: vi.fn(),
    });
    render(<ComplianceScanPanel buildingId="b1" />, { wrapper });
    const finding = screen.getByTestId('compliance-finding');
    expect(finding.className).toContain('red');
  });

  it('refresh button calls refetch', () => {
    const refetch = vi.fn();
    mockUseComplianceScan.mockReturnValue({
      isLoading: false,
      isError: false,
      data: makeScanResult(),
      refetch,
    });
    render(<ComplianceScanPanel buildingId="b1" />, { wrapper });
    fireEvent.click(screen.getByTestId('scan-refresh'));
    expect(refetch).toHaveBeenCalled();
  });
});
