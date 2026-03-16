import { format, parseISO, type Locale } from 'date-fns';
import { fr, de, it, enUS } from 'date-fns/locale';
import { RISK_COLORS, POLLUTANT_COLORS } from '@/utils/constants';

const localeMap: Record<string, Locale> = {
  fr,
  de,
  it,
  en: enUS,
};

export function formatDate(dateStr: string, pattern: string = 'dd.MM.yyyy', locale: string = 'fr'): string {
  try {
    const date = parseISO(dateStr);
    return format(date, pattern, { locale: localeMap[locale] || fr });
  } catch {
    return dateStr;
  }
}

export function formatDateTime(dateStr: string, locale: string = 'fr'): string {
  return formatDate(dateStr, 'dd.MM.yyyy HH:mm', locale);
}

export function formatCHF(amount: number): string {
  const formatted = amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, "'");
  return `CHF ${formatted}`;
}

export function formatPercentage(value: number, decimals: number = 0): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function formatArea(m2: number): string {
  return `${m2.toLocaleString('de-CH')} m\u00B2`;
}

export function formatVolume(m3: number): string {
  return `${m3.toLocaleString('de-CH')} m\u00B3`;
}

export function riskColor(level: string): string {
  return RISK_COLORS[level] || RISK_COLORS.unknown;
}

export function pollutantColor(type: string): string {
  return POLLUTANT_COLORS[type] || '#6b7280';
}

export function formatRiskLevel(level: string): string {
  const labels: Record<string, string> = {
    low: 'Faible',
    medium: 'Moyen',
    high: 'Eleve',
    critical: 'Critique',
    unknown: 'Inconnu',
  };
  return labels[level] || level;
}

export function formatPollutant(type: string): string {
  const labels: Record<string, string> = {
    asbestos: 'Amiante',
    pcb: 'PCB',
    lead: 'Plomb',
    hap: 'HAP',
    radon: 'Radon',
  };
  return labels[type] || type;
}

export function cn(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(' ');
}

export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 3) + '...';
}

export function capitalize(str: string): string {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}
