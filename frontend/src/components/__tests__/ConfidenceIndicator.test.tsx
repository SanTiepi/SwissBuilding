import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfidenceIndicator } from '../ConfidenceIndicator';

describe('ConfidenceIndicator', () => {
  it('renders red dot for value < 0.5', () => {
    const { container } = render(<ConfidenceIndicator value={0.3} showValue />);
    expect(screen.getByText('30%')).toBeInTheDocument();
    const dot = container.querySelector('span span');
    expect(dot).toHaveClass('bg-red-500');
  });

  it('renders amber dot for value between 0.5 and 0.8', () => {
    const { container } = render(<ConfidenceIndicator value={0.65} showValue />);
    expect(screen.getByText('65%')).toBeInTheDocument();
    const dot = container.querySelector('span span');
    expect(dot).toHaveClass('bg-amber-500');
  });

  it('renders green dot for value >= 0.8', () => {
    const { container } = render(<ConfidenceIndicator value={0.92} showValue />);
    expect(screen.getByText('92%')).toBeInTheDocument();
    const dot = container.querySelector('span span');
    expect(dot).toHaveClass('bg-green-500');
  });

  it('renders green for exactly 0.8 (boundary)', () => {
    render(<ConfidenceIndicator value={0.8} showValue />);
    expect(screen.getByText('80%')).toBeInTheDocument();
    const indicator = screen.getByTestId('confidence-indicator');
    expect(indicator).toHaveClass('bg-green-50');
  });

  it('renders amber for exactly 0.5 (boundary)', () => {
    render(<ConfidenceIndicator value={0.5} showValue />);
    expect(screen.getByText('50%')).toBeInTheDocument();
    const indicator = screen.getByTestId('confidence-indicator');
    expect(indicator).toHaveClass('bg-amber-50');
  });

  it('handles value of 0', () => {
    render(<ConfidenceIndicator value={0} showValue />);
    expect(screen.getByText('0%')).toBeInTheDocument();
    const indicator = screen.getByTestId('confidence-indicator');
    expect(indicator).toHaveClass('bg-red-50');
  });

  it('handles value of 1.0', () => {
    render(<ConfidenceIndicator value={1.0} showValue />);
    expect(screen.getByText('100%')).toBeInTheDocument();
    const indicator = screen.getByTestId('confidence-indicator');
    expect(indicator).toHaveClass('bg-green-50');
  });

  it('clamps negative values to 0', () => {
    render(<ConfidenceIndicator value={-0.5} showValue />);
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('clamps values above 1 to 100%', () => {
    render(<ConfidenceIndicator value={1.5} showValue />);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('shows percentage when showValue=true', () => {
    render(<ConfidenceIndicator value={0.75} showValue />);
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('hides percentage when showValue=false (dot only)', () => {
    render(<ConfidenceIndicator value={0.75} showValue={false} />);
    const indicator = screen.getByTestId('confidence-indicator');
    expect(indicator.textContent).toBe('');
    expect(indicator).toHaveClass('rounded-full');
  });

  it('md size shows value by default', () => {
    render(<ConfidenceIndicator value={0.6} size="md" />);
    expect(screen.getByText('60%')).toBeInTheDocument();
  });

  it('sm size shows dot only by default', () => {
    render(<ConfidenceIndicator value={0.6} size="sm" />);
    const indicator = screen.getByTestId('confidence-indicator');
    expect(indicator.textContent).toBe('');
  });

  it('has correct title with label and percentage', () => {
    render(<ConfidenceIndicator value={0.92} />);
    const indicator = screen.getByTestId('confidence-indicator');
    expect(indicator.getAttribute('title')).toBe('Haute confiance (92%)');
  });

  it('has correct title for low confidence', () => {
    render(<ConfidenceIndicator value={0.2} />);
    const indicator = screen.getByTestId('confidence-indicator');
    expect(indicator.getAttribute('title')).toBe('Faible confiance (20%)');
  });

  it('has correct title for medium confidence', () => {
    render(<ConfidenceIndicator value={0.65} />);
    const indicator = screen.getByTestId('confidence-indicator');
    expect(indicator.getAttribute('title')).toBe('Confiance moyenne (65%)');
  });
});
