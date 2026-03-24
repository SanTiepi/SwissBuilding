export const RISK_COLORS: Record<string, string> = {
  low: '#22c55e',
  medium: '#f59e0b',
  high: '#f97316',
  critical: '#ef4444',
  unknown: '#6b7280',
};

export const POLLUTANT_COLORS: Record<string, string> = {
  asbestos: '#8b5cf6',
  pcb: '#3b82f6',
  lead: '#f59e0b',
  hap: '#ec4899',
  radon: '#14b8a6',
  pfas: '#ef4444',
};

export const SWISS_CANTONS = [
  'AG',
  'AI',
  'AR',
  'BE',
  'BL',
  'BS',
  'FR',
  'GE',
  'GL',
  'GR',
  'JU',
  'LU',
  'NE',
  'NW',
  'OW',
  'SG',
  'SH',
  'SO',
  'SZ',
  'TG',
  'TI',
  'UR',
  'VD',
  'VS',
  'ZG',
  'ZH',
];

export const BUILDING_TYPES = ['residential', 'commercial', 'industrial', 'public', 'mixed'];

export const ROLES: string[] = ['admin', 'owner', 'diagnostician', 'architect', 'authority', 'contractor'];

export const POLLUTANT_TYPES = ['asbestos', 'pcb', 'lead', 'hap', 'radon', 'pfas'] as const;

export const RISK_LEVELS = ['low', 'medium', 'high', 'critical', 'unknown'] as const;

export const DIAGNOSTIC_STATUSES = ['draft', 'in_progress', 'completed', 'validated'] as const;

export const DIAGNOSTIC_CONTEXTS = ['UN', 'AvT', 'ApT'] as const;

export const MATERIAL_CATEGORIES = [
  'coating',
  'insulation',
  'flooring',
  'sealant',
  'adhesive',
  'mortar',
  'paint',
  'plaster',
  'roofing',
  'piping',
  'electrical',
  'ventilation',
  'facade',
  'window',
  'door',
  'other',
] as const;

export const CFST_WORK_CATEGORIES = ['cat_1', 'cat_2', 'cat_3', 'cat_4'] as const;

export const WASTE_DISPOSAL_TYPES = ['normal', 'controlled', 'special', 'hazardous'] as const;

export const SUPPORTED_LANGUAGES = [
  { code: 'fr', label: 'Francais' },
  { code: 'de', label: 'Deutsch' },
  { code: 'it', label: 'Italiano' },
  { code: 'en', label: 'English' },
] as const;

export const API_BASE_URL = '/api/v1';

export const MAPBOX_STYLE = 'mapbox://styles/mapbox/light-v11';

export const SWITZERLAND_CENTER: [number, number] = [8.2275, 46.8182];
export const SWITZERLAND_ZOOM = 7.5;
