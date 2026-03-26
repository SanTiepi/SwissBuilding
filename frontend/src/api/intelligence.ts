import { apiClient } from '@/api/client';

// --- Address Preview types (flat sections from address-preview endpoint) ---

export interface IdentitySection {
  egid: number | null;
  egrid: string | null;
  parcel: string | null;
  address_normalized: string | null;
  lat: number | null;
  lon: number | null;
}

export interface PhysicalSection {
  construction_year: number | null;
  floors: number | null;
  dwellings: number | null;
  surface_m2: number | null;
  heating_type: string | null;
}

export interface EnvironmentSection {
  radon: Record<string, unknown> | null;
  noise: Record<string, unknown> | null;
  hazards: Record<string, unknown> | null;
  seismic: Record<string, unknown> | null;
}

export interface EnergySection {
  solar_potential: Record<string, unknown> | null;
  heating_type: string | null;
  district_heating_available: boolean | null;
}

export interface TransportSection {
  quality_class: string | null;
  nearest_stops: Record<string, unknown>[];
  ev_charging: Record<string, unknown> | null;
}

export interface RiskSection {
  pollutant_prediction: Record<string, unknown> | null;
  environmental_score: number | null;
}

export interface ScoresSection {
  neighborhood: number | null;
  livability: number | null;
  connectivity: number | null;
  overall_grade: string | null;
}

export interface LifecycleSection {
  components: Record<string, unknown>[];
  critical_count: number;
  urgent_count: number;
}

export interface RenovationSection {
  plan_summary: string | null;
  total_cost: number | null;
  total_subsidy: number | null;
  roi_years: number | null;
}

export interface ComplianceSection {
  checks_count: number;
  non_compliant_count: number;
  summary: string | null;
}

export interface FinancialSection {
  cost_of_inaction: number | null;
  energy_savings: number | null;
  value_increase: number | null;
}

export interface NarrativeSection {
  summary_fr: string | null;
}

export interface MetadataSection {
  sources_used: string[];
  freshness: string;
  run_id: string | null;
}

export interface AddressPreviewResult {
  identity: IdentitySection;
  physical: PhysicalSection;
  environment: EnvironmentSection;
  energy: EnergySection;
  transport: TransportSection;
  risk: RiskSection;
  scores: ScoresSection;
  lifecycle: LifecycleSection;
  renovation: RenovationSection;
  compliance: ComplianceSection;
  financial: FinancialSection;
  narrative: NarrativeSection;
  metadata: MetadataSection;
}

// --- Instant Card types (5-question structure for existing buildings) ---

export interface ResidualMaterial {
  material_type: string;
  location: string | null;
  status: string;
  last_verified: string | null;
  source: string | null;
}

export interface WhatWeKnow {
  identity: Record<string, unknown>;
  physical: Record<string, unknown>;
  environment: Record<string, unknown>;
  energy: Record<string, unknown>;
  diagnostics: Record<string, unknown>;
  residual_materials: ResidualMaterial[];
}

export interface WhatIsRisky {
  pollutant_risk: Record<string, unknown>;
  environmental_risk: Record<string, unknown>;
  compliance_gaps: Record<string, unknown>[];
}

export interface WhatBlocks {
  procedural_blockers: Record<string, unknown>[];
  missing_proof: Record<string, unknown>[];
  overdue_obligations: Record<string, unknown>[];
}

export interface NextActionItem {
  action: string;
  priority: string;
  estimated_cost: number | null;
  evidence_needed: string | null;
}

export interface WhatToDoNext {
  top_3_actions: NextActionItem[];
}

export interface WhatIsReusable {
  diagnostic_publications: Record<string, unknown>[];
  packs_generated: Record<string, unknown>[];
  proof_deliveries: Record<string, unknown>[];
}

export interface ExecutionSection {
  renovation_plan_10y: Record<string, unknown>;
  subsidies: { program: string; amount: number; requirements: string[] }[];
  roi_renovation: Record<string, unknown>;
  insurance_impact: Record<string, unknown>;
  co2_impact: Record<string, unknown>;
  energy_savings: Record<string, unknown>;
  sequence_recommendation: Record<string, unknown>;
  next_concrete_step: Record<string, unknown>;
}

export interface TrustMeta {
  freshness: string;
  confidence: string;
  overall_trust: number;
  trend: string | null;
}

export interface InstantCardResult {
  building_id: string;
  passport_grade: string;
  what_we_know: WhatWeKnow;
  what_is_risky: WhatIsRisky;
  what_blocks: WhatBlocks;
  what_to_do_next: WhatToDoNext;
  what_is_reusable: WhatIsReusable;
  execution: ExecutionSection;
  trust: TrustMeta;
  neighbor_signals: Record<string, unknown>[];
}

// --- Portfolio Triage types ---

export interface PortfolioTriageBuilding {
  id: string;
  address: string;
  status: string; // critical | action_needed | monitored | under_control
  top_blocker: string | null;
  risk_score: number;
  next_action: string | null;
  passport_grade: string;
}

export interface PortfolioTriageResult {
  org_id: string;
  critical_count: number;
  action_needed_count: number;
  monitored_count: number;
  under_control_count: number;
  buildings: PortfolioTriageBuilding[];
}

// --- Source Snapshot types ---

export interface SourceSnapshot {
  id: string;
  building_id: string | null;
  enrichment_run_id: string | null;
  source_name: string;
  source_category: string;
  normalized_data: Record<string, unknown> | null;
  fetched_at: string | null;
  freshness_state: string;
  confidence: string;
}

// --- API client ---

export const intelligenceApi = {
  postAddressPreview: async (data: {
    address: string;
    postal_code?: string;
    city?: string;
  }): Promise<AddressPreviewResult> => {
    const response = await apiClient.post<AddressPreviewResult>('/intelligence/address-preview', data);
    return response.data;
  },

  getInstantCard: async (buildingId: string): Promise<InstantCardResult> => {
    const response = await apiClient.get<InstantCardResult>(`/buildings/${buildingId}/instant-card`);
    return response.data;
  },

  getPortfolioTriage: async (orgId: string): Promise<PortfolioTriageResult> => {
    const response = await apiClient.get<PortfolioTriageResult>(`/organizations/${orgId}/portfolio-triage`);
    return response.data;
  },

  getSourceSnapshots: async (buildingId: string): Promise<SourceSnapshot[]> => {
    const response = await apiClient.get<SourceSnapshot[]>(`/buildings/${buildingId}/source-snapshots`);
    return response.data;
  },
};
