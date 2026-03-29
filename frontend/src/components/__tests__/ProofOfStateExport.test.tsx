import { describe, expect, it, vi, beforeEach } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGetProofOfState = vi.fn();
const mockGetSummary = vi.fn();
const mockDownload = vi.fn();

vi.mock('@/api/proofOfState', () => ({
  proofOfStateApi: {
    getProofOfState: (...args: unknown[]) => mockGetProofOfState(...args),
    getProofOfStateSummary: (...args: unknown[]) => mockGetSummary(...args),
    downloadProofOfState: (...args: unknown[]) => mockDownload(...args),
  },
}));

import { ProofOfStateExport } from '@/components/ProofOfStateExport';

const MOCK_FULL_RESPONSE = {
  metadata: {
    export_id: 'exp-1',
    generated_at: '2026-03-30T00:00:00Z',
    generated_by: 'user-1',
    format_version: '1.0',
    building_id: 'b1',
  },
  building: { address: 'Rue Test 1' },
  evidence_score: { score: 72, grade: 'B' },
  passport: { passport_grade: 'B' },
  completeness: { overall_score: 0.85 },
  readiness: { safe_to_start: { status: 'ready' } },
  integrity: { algorithm: 'sha256', hash: 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890' },
};

// Summary response used in summary-mode tests
const _MOCK_SUMMARY_RESPONSE = {
  metadata: {
    export_id: 'exp-2',
    generated_at: '2026-03-30T00:00:00Z',
    generated_by: 'user-1',
    format_version: '1.0',
    building_id: 'b1',
    summary_only: true,
  },
  evidence_score: { score: 72, grade: 'B' },
  passport: { passport_grade: 'B' },
  readiness: { safe_to_start: { status: 'ready' } },
  integrity: { algorithm: 'sha256', hash: 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890' },
};

describe('ProofOfStateExport', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    cleanup();
  });

  it('renders export buttons', () => {
    render(<ProofOfStateExport buildingId="b1" />);
    expect(screen.getByText('proof_of_state.export_full')).toBeDefined();
    expect(screen.getByText('proof_of_state.export_summary')).toBeDefined();
    expect(screen.getByText('proof_of_state.preview')).toBeDefined();
    expect(screen.getByText('proof_of_state.download')).toBeDefined();
  });

  it('toggles between full and summary mode', () => {
    render(<ProofOfStateExport buildingId="b1" />);
    const summaryBtn = screen.getByText('proof_of_state.export_summary');
    fireEvent.click(summaryBtn);
    // Summary button should be active (blue bg)
    expect(summaryBtn.className).toContain('bg-blue-600');
  });

  it('shows loading state while generating', async () => {
    // Never resolve to keep loading state
    mockGetProofOfState.mockReturnValue(new Promise(() => {}));
    render(<ProofOfStateExport buildingId="b1" />);

    const previewBtn = screen.getByText('proof_of_state.preview');
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByText('proof_of_state.generating')).toBeDefined();
    });
  });

  it('shows preview after generating full export', async () => {
    mockGetProofOfState.mockResolvedValue(MOCK_FULL_RESPONSE);
    render(<ProofOfStateExport buildingId="b1" />);

    const previewBtn = screen.getByText('proof_of_state.preview');
    fireEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByText(/72/)).toBeDefined();
      expect(screen.getByText(/85%/)).toBeDefined();
    });
  });

  it('calls download api with correct mode', async () => {
    mockDownload.mockResolvedValue(undefined);
    render(<ProofOfStateExport buildingId="b1" />);

    // Switch to summary mode
    fireEvent.click(screen.getByText('proof_of_state.export_summary'));

    // Click download
    fireEvent.click(screen.getByText('proof_of_state.download'));

    await waitFor(() => {
      expect(mockDownload).toHaveBeenCalledWith('b1', true);
    });
  });

  it('generates summary when in summary mode', async () => {
    mockGetSummary.mockResolvedValue(_MOCK_SUMMARY_RESPONSE);
    render(<ProofOfStateExport buildingId="b1" />);

    // Switch to summary mode
    fireEvent.click(screen.getByText('proof_of_state.export_summary'));
    fireEvent.click(screen.getByText('proof_of_state.preview'));

    await waitFor(() => {
      expect(mockGetSummary).toHaveBeenCalledWith('b1');
    });
  });
});
