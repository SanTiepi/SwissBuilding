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

// --- Portfolio Benchmark types ---

export interface PortfolioBenchmarkBuilding {
  id: string;
  address: string;
  passport_grade: string;
  grade_rank: number;
  trust_pct: number;
  trust_percentile: number;
  completeness_pct: number;
  completeness_percentile: number;
  has_blockers: boolean;
  proof_coverage_pct: number;
  urgency_score: number;
  cluster: string;
  status: string;
}

export interface PortfolioCluster {
  key: string;
  label: string;
  building_count: number;
  avg_trust: number;
  avg_completeness: number;
  dominant_grade: string;
  building_ids: string[];
}

export interface PortfolioBenchmarkResult {
  org_id: string;
  avg_grade: string;
  avg_trust_pct: number;
  avg_completeness_pct: number;
  buildings_with_blockers_pct: number;
  proof_coverage_pct: number;
  buildings: PortfolioBenchmarkBuilding[];
  clusters: PortfolioCluster[];
}

// --- Portfolio Trends types ---

export interface BuildingTrend {
  id: string;
  address: string;
  trend: 'improved' | 'degraded' | 'stable';
  grade_delta: number;
  trust_delta: number;
  completeness_delta: number;
}

export interface PortfolioTrendsResult {
  org_id: string;
  improved_count: number;
  degraded_count: number;
  stable_count: number;
  buildings: BuildingTrend[];
}

// --- Indispensability types ---

export interface PlatformState {
  sources: number;
  contradictions_visible: number;
  proof_chains: number;
  grade: string | null;
  trust: number;
  completeness: number;
}

export interface FragmentationResult {
  sources_unified: number;
  systems_replaced: string[];
  contradictions_detected: number;
  contradictions_resolved: number;
  silent_risk: string;
  proof_chains_count: number;
  documents_with_provenance: number;
  documents_without_provenance: number;
  enrichment_fields_count: number;
  cross_source_fields: number;
  fragmentation_score: number;
}

export interface DefensibilityResult {
  decisions_with_full_trace: number;
  decisions_without_trace: number;
  defensibility_score: number;
  vulnerability_points: string[];
  snapshots_count: number;
  time_coverage_days: number;
}

export interface CounterfactualResult {
  with_platform: PlatformState;
  without_platform: PlatformState;
  delta: string[];
  cost_of_fragmentation_hours: number;
}

export interface IndispensabilityReport {
  building_id: string;
  generated_at: string;
  fragmentation: FragmentationResult;
  defensibility: DefensibilityResult;
  counterfactual: CounterfactualResult;
  headline: string;
}

export interface PortfolioIndispensabilitySummary {
  org_id: string;
  buildings_count: number;
  avg_fragmentation_score: number;
  avg_defensibility_score: number;
  total_contradictions_resolved: number;
  total_proof_chains: number;
  total_cost_of_fragmentation_hours: number;
  worst_buildings: Array<{ building_id: string; address: string; fragmentation_score: number }>;
}

// --- Value Ledger types ---

export interface ValueLedger {
  org_id: string;
  sources_unified_total: number;
  contradictions_resolved_total: number;
  proof_chains_created_total: number;
  documents_secured_total: number;
  decisions_backed_total: number;
  hours_saved_estimate: number;
  value_chf_estimate: number;
  days_active: number;
  value_per_day: number;
  trend: 'growing' | 'stable' | 'declining';
}

export interface ValueEvent {
  event_type: string;
  building_id: string;
  delta_description: string;
  created_at: string;
}

export interface IndispensabilityExport {
  title: string;
  generated_at: string;
  executive_summary: string;
  fragmentation_section: Record<string, unknown>;
  defensibility_section: Record<string, unknown>;
  counterfactual_section: Record<string, unknown>;
  value_ledger_section: Record<string, unknown>;
  recommendation: string;
}

// --- Score Explainability types ---

export interface ScoreLineItem {
  item_type: string;
  item_id: string;
  label: string;
  detail: string;
  contribution: string;
  link: string;
  source_class: string | null;
  timestamp: string | null;
}

export interface ExplainedScore {
  metric_name: string;
  metric_label: string;
  value: number;
  unit: string;
  methodology: string;
  line_items: ScoreLineItem[];
  confidence: string;
}

export interface ExplainedReport {
  building_id: string;
  generated_at: string;
  scores: ExplainedScore[];
  total_line_items: number;
  methodology_summary: string;
}

// --- Ecosystem Engagement types ---

export interface EcosystemEngagement {
  id: string;
  building_id: string;
  actor_type: string;
  actor_name: string | null;
  subject_type: string;
  subject_label: string | null;
  engagement_type: string;
  status: string;
  comment: string | null;
  engaged_at: string;
}

export interface EngagementSummary {
  building_id: string;
  total_engagements: number;
  by_actor_type: Record<string, number>;
  by_engagement_type: Record<string, number>;
  unique_actors: number;
  unique_orgs: number;
  latest_engagements: EcosystemEngagement[];
}

export interface EngagementDepth {
  building_id: string;
  depth_score: number;
  unique_actors: number;
  unique_orgs: number;
  engagement_types_used: string[];
  actor_types_represented: string[];
}

// --- Operational Gates types ---

export interface GatePrerequisite {
  type: string;
  label: string;
  satisfied: boolean;
  item_id: string | null;
}

export interface OperationalGate {
  id: string;
  building_id: string;
  gate_type: string;
  gate_label: string;
  status: string; // blocked | conditions_pending | clearable | cleared | overridden
  prerequisites: GatePrerequisite[];
  overridden_by_id: string | null;
  override_reason: string | null;
  cleared_at: string | null;
}

export interface BuildingGateStatus {
  building_id: string;
  total_gates: number;
  blocked: number;
  clearable: number;
  cleared: number;
  overridden: number;
}

// --- Transferable Memory types ---

export interface MemoryTransfer {
  id: string;
  building_id: string;
  transfer_type: string;
  transfer_label: string;
  status: string;
  from_org_id: string | null;
  to_org_id: string | null;
  sections_count: number;
  documents_count: number;
  engagements_count: number;
  timeline_events_count: number;
  integrity_verified: boolean;
  initiated_at: string;
  completed_at: string | null;
}

export interface TransferReadiness {
  building_id: string;
  ready: boolean;
  missing_sections: string[];
  open_gates: number;
  incomplete_engagements: string[];
  documents_without_hash: number;
}

export interface MemoryContinuityScore {
  building_id: string;
  score: number; // 0-100
  transfers_completed: number;
  gaps: number;
  coverage_pct: number;
  integrity_pct: number;
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

  getPortfolioBenchmark: async (orgId: string): Promise<PortfolioBenchmarkResult> => {
    const response = await apiClient.get<PortfolioBenchmarkResult>(`/organizations/${orgId}/portfolio-benchmark`);
    return response.data;
  },

  getPortfolioTrends: async (orgId: string): Promise<PortfolioTrendsResult> => {
    const response = await apiClient.get<PortfolioTrendsResult>(`/organizations/${orgId}/portfolio-trends`);
    return response.data;
  },

  getIndispensabilityReport: async (buildingId: string): Promise<IndispensabilityReport> => {
    const response = await apiClient.get<IndispensabilityReport>(`/buildings/${buildingId}/indispensability`);
    return response.data;
  },

  getPortfolioIndispensability: async (orgId: string): Promise<PortfolioIndispensabilitySummary> => {
    const response = await apiClient.get<PortfolioIndispensabilitySummary>(
      `/organizations/${orgId}/indispensability-summary`,
    );
    return response.data;
  },

  getValueLedger: async (orgId: string): Promise<ValueLedger> => {
    const response = await apiClient.get<ValueLedger>(`/organizations/${orgId}/value-ledger`);
    return response.data;
  },

  getValueEvents: async (orgId: string, limit?: number): Promise<ValueEvent[]> => {
    const params = limit ? { limit } : {};
    const response = await apiClient.get<ValueEvent[]>(`/organizations/${orgId}/value-events`, {
      params,
    });
    return response.data;
  },

  getIndispensabilityExport: async (buildingId: string): Promise<IndispensabilityExport> => {
    const response = await apiClient.get<IndispensabilityExport>(`/buildings/${buildingId}/indispensability-export`);
    return response.data;
  },

  getPortfolioIndispensabilityExport: async (orgId: string): Promise<IndispensabilityExport> => {
    const response = await apiClient.get<IndispensabilityExport>(`/organizations/${orgId}/indispensability-export`);
    return response.data;
  },

  getScoreExplainability: async (buildingId: string): Promise<ExplainedReport> => {
    const response = await apiClient.get<ExplainedReport>(`/buildings/${buildingId}/score-explainability`);
    return response.data;
  },

  getEngagementSummary: async (buildingId: string): Promise<EngagementSummary> => {
    const response = await apiClient.get<EngagementSummary>(`/buildings/${buildingId}/engagement-summary`);
    return response.data;
  },

  getEngagementTimeline: async (buildingId: string): Promise<EcosystemEngagement[]> => {
    const response = await apiClient.get<EcosystemEngagement[]>(`/buildings/${buildingId}/engagement-timeline`);
    return response.data;
  },

  getEngagementDepth: async (buildingId: string): Promise<EngagementDepth> => {
    const response = await apiClient.get<EngagementDepth>(`/buildings/${buildingId}/engagement-depth`);
    return response.data;
  },

  createEngagement: async (
    buildingId: string,
    data: { actor_type: string; subject_type: string; engagement_type: string; comment?: string },
  ): Promise<EcosystemEngagement> => {
    const response = await apiClient.post<EcosystemEngagement>(`/buildings/${buildingId}/engagements`, data);
    return response.data;
  },

  // --- Operational Gates ---

  getBuildingGates: async (buildingId: string): Promise<OperationalGate[]> => {
    const response = await apiClient.get<OperationalGate[]>(`/buildings/${buildingId}/gates/evaluate`);
    return response.data;
  },

  getBuildingGateStatus: async (buildingId: string): Promise<BuildingGateStatus> => {
    const response = await apiClient.get<BuildingGateStatus>(`/buildings/${buildingId}/gates/status`);
    return response.data;
  },

  overrideGate: async (gateId: string, reason: string): Promise<OperationalGate> => {
    const response = await apiClient.post<OperationalGate>(`/gates/${gateId}/override`, { reason });
    return response.data;
  },

  // --- Transferable Memory ---

  getTransferHistory: async (buildingId: string): Promise<MemoryTransfer[]> => {
    const response = await apiClient.get<MemoryTransfer[]>(`/buildings/${buildingId}/memory-transfers`);
    return response.data;
  },

  getTransferReadiness: async (buildingId: string): Promise<TransferReadiness> => {
    const response = await apiClient.get<TransferReadiness>(`/buildings/${buildingId}/transfer-readiness`);
    return response.data;
  },

  getContinuityScore: async (buildingId: string): Promise<MemoryContinuityScore> => {
    const response = await apiClient.get<MemoryContinuityScore>(`/buildings/${buildingId}/continuity-score`);
    return response.data;
  },

  initiateTransfer: async (
    buildingId: string,
    data: { transfer_type: string; to_org_id?: string },
  ): Promise<MemoryTransfer> => {
    const response = await apiClient.post<MemoryTransfer>(`/buildings/${buildingId}/memory-transfers`, data);
    return response.data;
  },
};
