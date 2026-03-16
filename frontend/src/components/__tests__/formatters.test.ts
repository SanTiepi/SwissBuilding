import { describe, it, expect } from 'vitest';
import {
  formatDate,
  formatDateTime,
  formatCHF,
  formatPercentage,
  formatArea,
  formatVolume,
  riskColor,
  pollutantColor,
  formatRiskLevel,
  formatPollutant,
  cn,
  truncate,
  capitalize,
} from '@/utils/formatters';

describe('formatCHF', () => {
  it('formats zero', () => {
    expect(formatCHF(0)).toBe('CHF 0.00');
  });

  it('formats small amount', () => {
    expect(formatCHF(42.5)).toBe('CHF 42.50');
  });

  it('formats thousands with Swiss apostrophe separator', () => {
    expect(formatCHF(1234.56)).toBe("CHF 1'234.56");
  });

  it('formats large number with multiple separators', () => {
    expect(formatCHF(1234567.89)).toBe("CHF 1'234'567.89");
  });

  it('formats negative number', () => {
    expect(formatCHF(-500)).toBe('CHF -500.00');
  });
});

describe('formatDate', () => {
  it('formats a valid ISO date with default pattern', () => {
    expect(formatDate('2024-03-15')).toBe('15.03.2024');
  });

  it('returns raw string on invalid input', () => {
    expect(formatDate('not-a-date')).toBe('not-a-date');
  });

  it('accepts a custom pattern', () => {
    expect(formatDate('2024-03-15', 'yyyy/MM/dd')).toBe('2024/03/15');
  });

  it('uses fr locale by default', () => {
    // Day name in French
    const result = formatDate('2024-03-15', 'EEEE');
    expect(result).toBe('vendredi');
  });

  it('supports de locale', () => {
    const result = formatDate('2024-03-15', 'EEEE', 'de');
    expect(result).toBe('Freitag');
  });

  it('falls back to fr for unknown locale', () => {
    const result = formatDate('2024-03-15', 'EEEE', 'xx');
    expect(result).toBe('vendredi');
  });
});

describe('formatDateTime', () => {
  it('formats date with time', () => {
    expect(formatDateTime('2024-03-15T14:30:00')).toBe('15.03.2024 14:30');
  });
});

describe('formatPercentage', () => {
  it('formats zero', () => {
    expect(formatPercentage(0)).toBe('0%');
  });

  it('formats 50%', () => {
    expect(formatPercentage(0.5)).toBe('50%');
  });

  it('formats 100%', () => {
    expect(formatPercentage(1.0)).toBe('100%');
  });

  it('supports custom decimals', () => {
    expect(formatPercentage(0.1234, 2)).toBe('12.34%');
  });
});

describe('formatArea', () => {
  it('formats area with m2 superscript', () => {
    const result = formatArea(120);
    expect(result).toContain('120');
    expect(result).toContain('m\u00B2');
  });
});

describe('formatVolume', () => {
  it('formats volume with m3 superscript', () => {
    const result = formatVolume(350);
    expect(result).toContain('350');
    expect(result).toContain('m\u00B3');
  });
});

describe('riskColor', () => {
  it('returns correct color for each risk level', () => {
    expect(riskColor('low')).toBe('#22c55e');
    expect(riskColor('medium')).toBe('#f59e0b');
    expect(riskColor('high')).toBe('#f97316');
    expect(riskColor('critical')).toBe('#ef4444');
    expect(riskColor('unknown')).toBe('#6b7280');
  });

  it('returns unknown color for unrecognized level', () => {
    expect(riskColor('extreme')).toBe('#6b7280');
  });
});

describe('pollutantColor', () => {
  it('returns correct color for each pollutant', () => {
    expect(pollutantColor('asbestos')).toBe('#8b5cf6');
    expect(pollutantColor('pcb')).toBe('#3b82f6');
    expect(pollutantColor('lead')).toBe('#f59e0b');
    expect(pollutantColor('hap')).toBe('#ec4899');
    expect(pollutantColor('radon')).toBe('#14b8a6');
  });

  it('returns grey fallback for unknown type', () => {
    expect(pollutantColor('mercury')).toBe('#6b7280');
  });
});

describe('formatRiskLevel', () => {
  it('maps all 5 risk levels to French labels', () => {
    expect(formatRiskLevel('low')).toBe('Faible');
    expect(formatRiskLevel('medium')).toBe('Moyen');
    expect(formatRiskLevel('high')).toBe('Eleve');
    expect(formatRiskLevel('critical')).toBe('Critique');
    expect(formatRiskLevel('unknown')).toBe('Inconnu');
  });

  it('returns raw string for unrecognized level', () => {
    expect(formatRiskLevel('extreme')).toBe('extreme');
  });
});

describe('formatPollutant', () => {
  it('maps all 5 pollutant types to French labels', () => {
    expect(formatPollutant('asbestos')).toBe('Amiante');
    expect(formatPollutant('pcb')).toBe('PCB');
    expect(formatPollutant('lead')).toBe('Plomb');
    expect(formatPollutant('hap')).toBe('HAP');
    expect(formatPollutant('radon')).toBe('Radon');
  });

  it('returns raw string for unrecognized type', () => {
    expect(formatPollutant('mercury')).toBe('mercury');
  });
});

describe('cn', () => {
  it('joins multiple class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('filters out falsy values', () => {
    expect(cn('foo', undefined, false, null, 'bar')).toBe('foo bar');
  });

  it('returns empty string with no args', () => {
    expect(cn()).toBe('');
  });
});

describe('truncate', () => {
  it('returns short string unchanged', () => {
    expect(truncate('hello', 10)).toBe('hello');
  });

  it('truncates long string with ellipsis', () => {
    expect(truncate('hello world', 8)).toBe('hello...');
  });

  it('returns string unchanged when exactly at maxLength', () => {
    expect(truncate('hello', 5)).toBe('hello');
  });
});

describe('capitalize', () => {
  it('capitalizes first letter', () => {
    expect(capitalize('hello')).toBe('Hello');
  });

  it('returns empty string unchanged', () => {
    expect(capitalize('')).toBe('');
  });

  it('handles single character', () => {
    expect(capitalize('a')).toBe('A');
  });
});
