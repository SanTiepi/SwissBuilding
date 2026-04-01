import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MaterialRecognitionForm } from '../MaterialRecognitionForm';

// Mock the API module
vi.mock('@/api/materialRecognition', () => ({
  materialRecognitionApi: {
    recognize: vi.fn(),
  },
}));

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('MaterialRecognitionForm', () => {
  it('renders upload zone initially', () => {
    renderWithQuery(<MaterialRecognitionForm buildingId="test-123" />);
    expect(screen.getByText(/Glissez une photo/)).toBeInTheDocument();
  });

  it('renders file input with correct accept types', () => {
    renderWithQuery(<MaterialRecognitionForm buildingId="test-123" />);
    const input = document.querySelector('input[type="file"]');
    expect(input).toBeTruthy();
    expect(input?.getAttribute('accept')).toBe('image/jpeg,image/png,image/webp');
  });

  it('shows preview after file selection', async () => {
    // Mock FileReader as a class
    let capturedOnload: ((e: ProgressEvent<FileReader>) => void) | null = null;
    const MockFileReader = vi.fn().mockImplementation(function (this: Partial<FileReader>) {
      this.readAsDataURL = vi.fn().mockImplementation(() => {
        if (capturedOnload) {
          capturedOnload({ target: { result: 'data:image/jpeg;base64,test' } } as ProgressEvent<FileReader>);
        }
      });
      Object.defineProperty(this, 'onload', {
        set(fn: (e: ProgressEvent<FileReader>) => void) {
          capturedOnload = fn;
        },
        get() {
          return capturedOnload;
        },
      });
    });
    vi.stubGlobal('FileReader', MockFileReader);

    renderWithQuery(<MaterialRecognitionForm buildingId="test-123" />);

    const file = new File(['test'], 'photo.jpg', { type: 'image/jpeg' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText('Identifier le matériau')).toBeInTheDocument();
    });

    vi.unstubAllGlobals();
  });

  it('rejects files over 5 MB', () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
    renderWithQuery(<MaterialRecognitionForm buildingId="test-123" />);

    const bigFile = new File(['x'.repeat(6 * 1024 * 1024)], 'big.jpg', { type: 'image/jpeg' });
    Object.defineProperty(bigFile, 'size', { value: 6 * 1024 * 1024 });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [bigFile] } });

    expect(alertSpy).toHaveBeenCalledWith('Fichier trop volumineux (max 5 MB)');
    alertSpy.mockRestore();
  });

  it('rejects non-image files', () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});
    renderWithQuery(<MaterialRecognitionForm buildingId="test-123" />);

    const pdfFile = new File(['test'], 'doc.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [pdfFile] } });

    expect(alertSpy).toHaveBeenCalledWith('Format non supporté. Utilisez JPG, PNG ou WebP.');
    alertSpy.mockRestore();
  });

  it('shows save button only when elementId is provided and result exists', async () => {
    const { rerender } = renderWithQuery(
      <MaterialRecognitionForm buildingId="test-123" />,
    );
    expect(screen.queryByText(/Sauvegarder/)).not.toBeInTheDocument();

    rerender(
      <QueryClientProvider client={new QueryClient()}>
        <MaterialRecognitionForm buildingId="test-123" elementId="elem-456" />
      </QueryClientProvider>,
    );
    expect(screen.queryByText(/Sauvegarder/)).not.toBeInTheDocument();
  });
});
