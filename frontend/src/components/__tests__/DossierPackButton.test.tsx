import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DossierPackButton } from '../DossierPackButton';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockToast = vi.fn();
vi.mock('@/store/toastStore', () => ({
  toast: (...args: unknown[]) => mockToast(...args),
}));

const mockGenerate = vi.fn();
const mockPreview = vi.fn();
vi.mock('@/api/dossier', () => ({
  dossierApi: {
    generate: (...args: unknown[]) => mockGenerate(...args),
    preview: (...args: unknown[]) => mockPreview(...args),
  },
}));

const mockEvaluate = vi.fn();
vi.mock('@/api/completeness', () => ({
  completenessApi: {
    evaluate: (...args: unknown[]) => mockEvaluate(...args),
  },
}));

describe('DossierPackButton', () => {
  beforeEach(() => {
    mockGenerate.mockReset();
    mockPreview.mockReset();
    mockToast.mockReset();
    mockEvaluate.mockReset();
    mockEvaluate.mockResolvedValue({ overall_score: 0.8, checks: [], missing_items: [], ready_to_proceed: false });
  });

  it('renders the generate button', async () => {
    render(<DossierPackButton buildingId="b1" />);
    expect(screen.getByText('dossier.generate')).toBeInTheDocument();
    // Wait for async completeness evaluation to settle
    await waitFor(() => {
      expect(mockEvaluate).toHaveBeenCalled();
    });
  });

  it('shows dropdown with PDF and preview options on click', async () => {
    render(<DossierPackButton buildingId="b1" />);
    fireEvent.click(screen.getByText('dossier.generate'));

    await waitFor(() => {
      expect(screen.getByText('dossier.download_pdf')).toBeInTheDocument();
      expect(screen.getByText('dossier.preview')).toBeInTheDocument();
    });
  });

  it('shows completeness score badge', async () => {
    render(<DossierPackButton buildingId="b1" />);

    await waitFor(() => {
      expect(screen.getByText('80%')).toBeInTheDocument();
    });
  });

  it('disables button when completeness < 50%', async () => {
    mockEvaluate.mockResolvedValue({ overall_score: 0.3, checks: [], missing_items: [], ready_to_proceed: false });

    render(<DossierPackButton buildingId="b1" />);

    await waitFor(() => {
      const btn = screen.getByText('dossier.generate').closest('button');
      expect(btn).toBeDisabled();
    });
  });

  it('calls dossierApi.generate on Download PDF click', async () => {
    mockGenerate.mockResolvedValue({ html: '<html></html>' });
    render(<DossierPackButton buildingId="b1" />);

    // Open dropdown
    fireEvent.click(screen.getByText('dossier.generate'));
    await waitFor(() => {
      expect(screen.getByText('dossier.download_pdf')).toBeInTheDocument();
    });

    // Click download PDF
    fireEvent.click(screen.getByText('dossier.download_pdf'));

    await waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledWith('b1', 'avt');
    });
  });

  it('shows toast on success', async () => {
    mockGenerate.mockResolvedValue({ html: '<html></html>' });
    render(<DossierPackButton buildingId="b1" />);

    fireEvent.click(screen.getByText('dossier.generate'));
    await waitFor(() => {
      expect(screen.getByText('dossier.download_pdf')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('dossier.download_pdf'));

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith('dossier.generated', 'success');
    });
  });

  it('shows toast on error', async () => {
    mockGenerate.mockRejectedValue(new Error('fail'));
    render(<DossierPackButton buildingId="b1" />);

    fireEvent.click(screen.getByText('dossier.generate'));
    await waitFor(() => {
      expect(screen.getByText('dossier.download_pdf')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('dossier.download_pdf'));

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith('dossier.error');
    });
  });

  it('opens preview modal with iframe', async () => {
    mockPreview.mockResolvedValue('<html><body>Preview</body></html>');
    render(<DossierPackButton buildingId="b1" />);

    // Open dropdown, click preview
    fireEvent.click(screen.getByText('dossier.generate'));
    await waitFor(() => {
      expect(screen.getByText('dossier.preview')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('dossier.preview'));

    await waitFor(() => {
      expect(screen.getByTitle('Dossier Preview')).toBeInTheDocument();
    });
    const iframe = screen.getByTitle('Dossier Preview') as HTMLIFrameElement;
    expect(iframe.getAttribute('srcdoc')).toBe('<html><body>Preview</body></html>');
  });

  it('closes preview modal on backdrop click', async () => {
    mockPreview.mockResolvedValue('<html><body>Preview</body></html>');
    render(<DossierPackButton buildingId="b1" />);

    fireEvent.click(screen.getByText('dossier.generate'));
    await waitFor(() => {
      expect(screen.getByText('dossier.preview')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('dossier.preview'));

    await waitFor(() => {
      expect(screen.getByTitle('Dossier Preview')).toBeInTheDocument();
    });

    const backdrop = screen.getByTitle('Dossier Preview').closest('.fixed');
    expect(backdrop).toBeInTheDocument();
    fireEvent.click(backdrop!);

    expect(screen.queryByTitle('Dossier Preview')).not.toBeInTheDocument();
  });

  it('passes stage parameter to API', async () => {
    mockGenerate.mockResolvedValue({ html: '<html></html>' });
    render(<DossierPackButton buildingId="b1" stage="apt" />);

    fireEvent.click(screen.getByText('dossier.generate'));
    await waitFor(() => {
      expect(screen.getByText('dossier.download_pdf')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('dossier.download_pdf'));

    await waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledWith('b1', 'apt');
    });
  });
});
