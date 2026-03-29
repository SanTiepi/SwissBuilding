import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NudgeCard } from '../NudgeCard';
import type { Nudge } from '@/api/nudges';

const baseMock: Nudge = {
  id: 'test-nudge-1',
  nudge_type: 'expiring_diagnostic',
  severity: 'critical',
  headline: 'Diagnostic expires in 45 days',
  loss_framing: 'After expiry you cannot start works legally.',
  gain_framing: 'Renewing now ensures compliance.',
  cost_of_inaction: {
    description: 'Emergency re-diagnostic surcharge',
    estimated_chf_min: 4000,
    estimated_chf_max: 16000,
    confidence: 'market_data',
  },
  deadline_pressure: 45,
  social_proof: '87% of similar buildings have up-to-date diagnostics.',
  call_to_action: 'Schedule diagnostic renewal',
  related_entity: { entity_type: 'diagnostic', entity_id: 'diag-1' },
};

describe('NudgeCard', () => {
  it('renders headline and CTA', () => {
    render(<NudgeCard nudge={baseMock} />);
    expect(screen.getByText('Diagnostic expires in 45 days')).toBeInTheDocument();
    expect(screen.getByTestId('nudge-cta-test-nudge-1')).toHaveTextContent(
      'Schedule diagnostic renewal',
    );
  });

  it('renders cost of inaction', () => {
    render(<NudgeCard nudge={baseMock} />);
    // CHF amounts should be visible
    expect(screen.getByText(/4[\s\u2019']?000/)).toBeInTheDocument();
  });

  it('renders deadline pressure', () => {
    render(<NudgeCard nudge={baseMock} />);
    const matches = screen.getAllByText(/45/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it('renders social proof', () => {
    render(<NudgeCard nudge={baseMock} />);
    expect(screen.getByText(/87%/)).toBeInTheDocument();
  });

  it('applies critical severity styling', () => {
    render(<NudgeCard nudge={baseMock} />);
    const card = screen.getByTestId('nudge-card-test-nudge-1');
    expect(card.className).toContain('bg-red-50');
    expect(card.className).toContain('border-red-300');
  });

  it('applies warning severity styling', () => {
    const warningNudge: Nudge = { ...baseMock, id: 'warn-1', severity: 'warning' };
    render(<NudgeCard nudge={warningNudge} />);
    const card = screen.getByTestId('nudge-card-warn-1');
    expect(card.className).toContain('bg-amber-50');
  });

  it('applies info severity styling', () => {
    const infoNudge: Nudge = { ...baseMock, id: 'info-1', severity: 'info' };
    render(<NudgeCard nudge={infoNudge} />);
    const card = screen.getByTestId('nudge-card-info-1');
    expect(card.className).toContain('bg-blue-50');
  });

  it('calls onDismiss when dismiss button clicked', () => {
    const onDismiss = vi.fn();
    render(<NudgeCard nudge={baseMock} onDismiss={onDismiss} />);
    const dismissBtn = screen.getByTestId('nudge-dismiss-test-nudge-1');
    fireEvent.click(dismissBtn);
    expect(onDismiss).toHaveBeenCalledWith('test-nudge-1');
  });

  it('does not show dismiss button when onDismiss not provided', () => {
    render(<NudgeCard nudge={baseMock} />);
    expect(screen.queryByTestId('nudge-dismiss-test-nudge-1')).not.toBeInTheDocument();
  });

  it('calls onAction when CTA clicked', () => {
    const onAction = vi.fn();
    render(<NudgeCard nudge={baseMock} onAction={onAction} />);
    fireEvent.click(screen.getByTestId('nudge-cta-test-nudge-1'));
    expect(onAction).toHaveBeenCalledWith(baseMock);
  });

  it('renders without cost_of_inaction', () => {
    const nudge: Nudge = { ...baseMock, cost_of_inaction: null };
    render(<NudgeCard nudge={nudge} />);
    expect(screen.getByText('Diagnostic expires in 45 days')).toBeInTheDocument();
  });

  it('renders without deadline_pressure', () => {
    const nudge: Nudge = { ...baseMock, deadline_pressure: null };
    render(<NudgeCard nudge={nudge} />);
    expect(screen.getByText('Diagnostic expires in 45 days')).toBeInTheDocument();
  });
});
