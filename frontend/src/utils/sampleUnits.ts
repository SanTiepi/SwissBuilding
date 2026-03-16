import { SAMPLE_UNIT_VALUES, type SampleUnit } from '@/types';

const SAMPLE_UNIT_LABELS: Record<SampleUnit, string> = {
  percent_weight: '% poids',
  fibers_per_m3: 'fibres/m3',
  mg_per_kg: 'mg/kg',
  ng_per_m3: 'ng/m3',
  ug_per_l: 'ug/l',
  bq_per_m3: 'Bq/m3',
};

const SAMPLE_UNIT_ALIASES: Record<string, SampleUnit> = {
  percent_weight: 'percent_weight',
  '%': 'percent_weight',
  percent: 'percent_weight',
  fibers_per_m3: 'fibers_per_m3',
  'fibers/m3': 'fibers_per_m3',
  'fibers/m³': 'fibers_per_m3',
  'fibres/m3': 'fibers_per_m3',
  'fibres/m³': 'fibers_per_m3',
  'f/m3': 'fibers_per_m3',
  'f/m³': 'fibers_per_m3',
  mg_per_kg: 'mg_per_kg',
  'mg/kg': 'mg_per_kg',
  ppm: 'mg_per_kg',
  ng_per_m3: 'ng_per_m3',
  'ng/m3': 'ng_per_m3',
  'ng/m³': 'ng_per_m3',
  ug_per_l: 'ug_per_l',
  'ug/l': 'ug_per_l',
  'µg/l': 'ug_per_l',
  'μg/l': 'ug_per_l',
  bq_per_m3: 'bq_per_m3',
  'bq/m3': 'bq_per_m3',
  'bq/m³': 'bq_per_m3',
};

function sampleUnitKey(unit: string): string {
  return unit.trim().toLowerCase().replace(/µ/g, 'u').replace(/μ/g, 'u').replace(/³/g, '3');
}

export const SAMPLE_UNIT_OPTIONS = SAMPLE_UNIT_VALUES.map((value) => ({
  value,
  label: SAMPLE_UNIT_LABELS[value],
}));

export function normalizeSampleUnitForDisplay(unit: string): string {
  return SAMPLE_UNIT_ALIASES[sampleUnitKey(unit)] ?? unit;
}

export function formatSampleUnit(unit: string | null | undefined): string {
  if (!unit) {
    return '-';
  }
  const normalized = normalizeSampleUnitForDisplay(unit);
  return SAMPLE_UNIT_LABELS[normalized as SampleUnit] ?? unit;
}
