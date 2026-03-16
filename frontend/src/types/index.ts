// User roles
export type UserRole = 'admin' | 'owner' | 'diagnostician' | 'architect' | 'authority' | 'contractor';
export type PollutantType = 'asbestos' | 'pcb' | 'lead' | 'hap' | 'radon';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical' | 'unknown';
export type DiagnosticStatus = 'draft' | 'in_progress' | 'completed' | 'validated';
export type DiagnosticContext = 'UN' | 'AvT' | 'ApT';
export type Language = 'fr' | 'de' | 'it' | 'en';
export const SAMPLE_UNIT_VALUES = [
  'percent_weight',
  'fibers_per_m3',
  'mg_per_kg',
  'ng_per_m3',
  'ug_per_l',
  'bq_per_m3',
] as const;
export type SampleUnit = (typeof SAMPLE_UNIT_VALUES)[number];

// Auth
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  organization_id: string | null;
  language: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Building
export interface Building {
  id: string;
  egid: number | null;
  egrid: string | null;
  official_id: string | null;
  address: string;
  postal_code: string;
  city: string;
  canton: string;
  latitude: number | null;
  longitude: number | null;
  parcel_number: string | null;
  construction_year: number | null;
  renovation_year: number | null;
  building_type: string;
  floors_above: number | null;
  floors_below: number | null;
  surface_area_m2: number | null;
  volume_m3: number | null;
  owner_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  risk_scores?: BuildingRiskScore;
}

// Diagnostic
export interface Diagnostic {
  id: string;
  building_id: string;
  diagnostic_type: PollutantType | 'full';
  diagnostic_context: DiagnosticContext;
  status: DiagnosticStatus;
  diagnostician_id: string;
  laboratory: string | null;
  laboratory_report_number: string | null;
  date_inspection: string;
  date_report: string | null;
  summary: string | null;
  conclusion: string | null;
  methodology: string | null;
  suva_notification_required: boolean;
  suva_notification_date: string | null;
  canton_notification_date: string | null;
  report_file_path: string | null;
  created_at: string;
  updated_at: string;
  samples?: Sample[];
  generated_actions_count?: number | null;
}

// Sample
export interface Sample {
  id: string;
  diagnostic_id: string;
  sample_number: string;
  location_floor: string | null;
  location_room: string | null;
  location_detail: string | null;
  material_category: string;
  material_description: string | null;
  material_state: string | null;
  pollutant_type: PollutantType;
  pollutant_subtype: string | null;
  concentration: number | null;
  unit: SampleUnit | string;
  threshold_exceeded: boolean;
  risk_level: RiskLevel | null;
  cfst_work_category: string | null;
  action_required: string | null;
  waste_disposal_type: string | null;
  notes: string | null;
  created_at: string;
}

// Risk
export interface BuildingRiskScore {
  id: string;
  building_id: string;
  asbestos_probability: number;
  pcb_probability: number;
  lead_probability: number;
  hap_probability: number;
  radon_probability: number;
  overall_risk_level: RiskLevel;
  confidence: number;
  factors_json: Record<string, unknown> | null;
  data_source: string;
  last_updated: string;
}

export interface RenovationSimulation {
  renovation_type: string;
  building_id: string;
  pollutant_risks: PollutantRisk[];
  total_estimated_cost_chf: number;
  required_diagnostics: string[];
  compliance_requirements: ComplianceRequirement[];
  timeline_weeks: number;
}

export interface PollutantRisk {
  pollutant: PollutantType;
  probability: number;
  risk_level: RiskLevel;
  exposure_factor: number;
  materials_at_risk: string[];
  estimated_cost_chf: number;
}

export interface ComplianceRequirement {
  requirement: string;
  legal_reference: string;
  mandatory: boolean;
  deadline_days: number | null;
}

// Event
export interface BuildingEvent {
  id: string;
  building_id: string;
  event_type: string;
  date: string;
  title: string;
  description: string | null;
  created_by: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
}

// Document processing metadata
export interface DocumentProcessingMetadata {
  virus_scan?: { clean: boolean; message: string };
  ocr?: { applied: boolean; language: string | null };
}

// Document
export interface Document {
  id: string;
  building_id: string;
  file_path: string;
  file_name: string;
  file_size_bytes: number | null;
  mime_type: string | null;
  document_type: string;
  description: string | null;
  uploaded_by: string;
  processing_metadata: DocumentProcessingMetadata | null;
  created_at: string;
}

// Action Item
export type ActionSourceType = 'risk' | 'diagnostic' | 'document' | 'compliance' | 'simulation' | 'manual' | 'system';
export type ActionPriority = 'low' | 'medium' | 'high' | 'critical';
export type ActionStatus = 'open' | 'in_progress' | 'blocked' | 'done' | 'dismissed';

export interface ActionItem {
  id: string;
  building_id: string;
  diagnostic_id: string | null;
  sample_id: string | null;
  campaign_id: string | null;
  source_type: ActionSourceType;
  action_type: string;
  title: string;
  description: string | null;
  priority: ActionPriority;
  status: ActionStatus;
  due_date: string | null;
  assigned_to: string | null;
  created_by: string | null;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

// Activity Timeline
export type ActivityKind = 'diagnostic' | 'document' | 'event' | 'action';

export interface ActivityItem {
  id: string;
  kind: ActivityKind;
  source_id: string;
  building_id: string;
  occurred_at: string;
  title: string;
  description: string | null;
  status: string | null;
  actor_id: string | null;
  linked_object_type: string | null;
  linked_object_id: string | null;
  metadata_json: Record<string, unknown> | null;
}

// Timeline
export interface TimelineEntry {
  id: string;
  date: string;
  event_type: string;
  title: string;
  description: string | null;
  icon_hint: string;
  metadata: Record<string, unknown> | null;
  source_id: string | null;
  source_type: string | null;
}

export type LifecyclePhase = 'discovery' | 'assessment' | 'remediation' | 'verification' | 'closed';
export type ImportanceLevel = 'low' | 'medium' | 'high' | 'critical';

export interface TimelineLink {
  from_id: string;
  to_id: string;
  relationship: string;
}

export interface EnrichedTimelineEntry extends TimelineEntry {
  lifecycle_phase: LifecyclePhase;
  importance: ImportanceLevel;
}

export interface EnrichedTimeline {
  entries: EnrichedTimelineEntry[];
  causal_links: TimelineLink[];
  lifecycle_summary: Record<string, number>;
}

// Parsed Report (parse → review → apply flow)
export interface ParsedSampleData {
  sample_number: string | null;
  location: string | null;
  material: string | null;
  pollutant_type: string | null;
  pollutant_subtype: string | null;
  concentration: number | null;
  unit: string | null;
}

export interface ParseReportResponse {
  diagnostic_id: string;
  metadata: Record<string, unknown>;
  samples: ParsedSampleData[];
  warnings: string[];
  text_length: number;
}

// Pagination
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Map GeoJSON
export interface MapBuilding {
  type: 'Feature';
  geometry: {
    type: 'Point';
    coordinates: [number, number];
  };
  properties: {
    id: string;
    address: string;
    city: string;
    canton: string;
    construction_year: number | null;
    overall_risk_level: RiskLevel;
    pollutants: PollutantType[];
  };
}

export interface MapBuildingsResponse {
  type: 'FeatureCollection';
  features: MapBuilding[];
}

// Organization
export type OrganizationType =
  | 'diagnostic_lab'
  | 'architecture_firm'
  | 'property_management'
  | 'authority'
  | 'contractor';

export interface Organization {
  id: string;
  name: string;
  type: OrganizationType;
  address: string | null;
  postal_code: string | null;
  city: string | null;
  canton: string | null;
  phone: string | null;
  email: string | null;
  suva_recognized: boolean;
  fach_approved: boolean;
  created_at: string;
  member_count: number;
}

// Invitation
export type InvitationStatus = 'pending' | 'accepted' | 'expired' | 'revoked';

export interface Invitation {
  id: string;
  email: string;
  role: UserRole;
  organization_id: string | null;
  status: InvitationStatus;
  token: string;
  invited_by: string;
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
}

// Notification
export type NotificationType = 'action' | 'invitation' | 'export' | 'system';
export type NotificationStatus = 'unread' | 'read';

export interface Notification {
  id: string;
  user_id: string;
  type: NotificationType;
  title: string;
  body: string | null;
  link: string | null;
  status: NotificationStatus;
  created_at: string;
  read_at: string | null;
}

export interface NotificationPreference {
  in_app_actions: boolean;
  in_app_invitations: boolean;
  in_app_exports: boolean;
  digest_enabled: boolean;
}

// Full Notification Preferences (extended)
export type NotificationChannel = 'in_app' | 'email' | 'digest';
export type DigestFrequency = 'daily' | 'weekly' | 'never';

export interface NotificationTypePreference {
  type: string;
  channels: NotificationChannel[];
  enabled: boolean;
}

export interface QuietHours {
  enabled: boolean;
  start_hour: number;
  end_hour: number;
  timezone: string;
}

export interface FullNotificationPreferences {
  user_id: string;
  type_preferences: NotificationTypePreference[];
  quiet_hours: QuietHours;
  digest_frequency: DigestFrequency;
  updated_at: string;
}

// Export Job
export type ExportJobType = 'building_dossier' | 'handoff_pack' | 'audit_pack';
export type ExportJobStatus = 'queued' | 'processing' | 'completed' | 'failed';

export interface ExportJob {
  id: string;
  type: ExportJobType;
  building_id: string | null;
  organization_id: string | null;
  status: ExportJobStatus;
  requested_by: string;
  file_path: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

// Background Job
export type BackgroundJobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface BackgroundJob {
  id: string;
  job_type: string;
  status: BackgroundJobStatus;
  building_id?: string;
  progress_pct?: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

// Assignment
export type AssignmentRole = 'responsible' | 'owner_contact' | 'diagnostician' | 'reviewer' | 'contractor_contact';

export interface Assignment {
  id: string;
  target_type: string;
  target_id: string;
  user_id: string;
  role: AssignmentRole;
  created_by: string;
  created_at: string;
}

// Zone
export type ZoneType =
  | 'floor'
  | 'room'
  | 'facade'
  | 'roof'
  | 'basement'
  | 'staircase'
  | 'technical_room'
  | 'parking'
  | 'other';

export interface Zone {
  id: string;
  building_id: string;
  parent_zone_id: string | null;
  zone_type: ZoneType;
  name: string;
  description: string | null;
  floor_number: number | null;
  surface_area_m2: number | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  children_count: number;
  elements_count: number;
}

// Building Element
export type ElementType =
  | 'wall'
  | 'floor'
  | 'ceiling'
  | 'pipe'
  | 'insulation'
  | 'coating'
  | 'window'
  | 'door'
  | 'duct'
  | 'structural'
  | 'other';
export type ElementCondition = 'good' | 'fair' | 'poor' | 'critical' | 'unknown';

export interface BuildingElement {
  id: string;
  zone_id: string;
  element_type: ElementType;
  name: string;
  description: string | null;
  condition: ElementCondition | null;
  installation_year: number | null;
  last_inspected_at: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  materials_count: number;
}

// Material
export type MaterialType =
  | 'concrete'
  | 'fiber_cement'
  | 'plaster'
  | 'paint'
  | 'adhesive'
  | 'insulation_material'
  | 'sealant'
  | 'flooring'
  | 'tile'
  | 'wood'
  | 'metal'
  | 'glass'
  | 'bitumen'
  | 'mortar'
  | 'other';
export type MaterialSource = 'diagnostic' | 'visual_inspection' | 'documentation' | 'owner_declaration' | 'import';

export interface Material {
  id: string;
  element_id: string;
  material_type: MaterialType;
  name: string;
  description: string | null;
  manufacturer: string | null;
  installation_year: number | null;
  contains_pollutant: boolean;
  pollutant_type: PollutantType | null;
  pollutant_confirmed: boolean;
  sample_id: string | null;
  source: MaterialSource | null;
  notes: string | null;
  created_by: string | null;
  created_at: string;
}

// Intervention
export type InterventionType =
  | 'renovation'
  | 'maintenance'
  | 'repair'
  | 'demolition'
  | 'installation'
  | 'inspection'
  | 'diagnostic'
  | 'asbestos_removal'
  | 'decontamination'
  | 'other';
export type InterventionStatus = 'planned' | 'in_progress' | 'completed' | 'cancelled';

export interface Intervention {
  id: string;
  building_id: string;
  intervention_type: InterventionType;
  title: string;
  description: string | null;
  status: InterventionStatus;
  date_start: string | null;
  date_end: string | null;
  contractor_name: string | null;
  contractor_id: string | null;
  cost_chf: number | null;
  zones_affected: string[] | null;
  materials_used: string[] | null;
  diagnostic_id: string | null;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

// Technical Plan
export type PlanType =
  | 'floor_plan'
  | 'cross_section'
  | 'elevation'
  | 'technical_schema'
  | 'site_plan'
  | 'detail'
  | 'annotation'
  | 'other';

export interface TechnicalPlan {
  id: string;
  building_id: string;
  plan_type: PlanType;
  title: string;
  description: string | null;
  floor_number: number | null;
  version: string | null;
  file_path: string;
  file_name: string;
  mime_type: string | null;
  file_size_bytes: number | null;
  zone_id: string | null;
  uploaded_by: string | null;
  created_at: string;
}

// Plan Annotation
export type PlanAnnotationType =
  | 'marker'
  | 'zone_reference'
  | 'sample_location'
  | 'observation'
  | 'hazard_zone'
  | 'measurement_point';

export interface PlanAnnotation {
  id: string;
  plan_id: string;
  building_id: string;
  annotation_type: PlanAnnotationType;
  label: string;
  x: number;
  y: number;
  description?: string;
  zone_id?: string;
  sample_id?: string;
  element_id?: string;
  color?: string;
  icon?: string;
  metadata_json?: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface PlanAnnotationCreate {
  annotation_type: PlanAnnotationType;
  label: string;
  x: number;
  y: number;
  description?: string;
  zone_id?: string;
  sample_id?: string;
  element_id?: string;
  color?: string;
  icon?: string;
}

// Evidence Link
export type EvidenceSourceType =
  | 'sample'
  | 'diagnostic'
  | 'document'
  | 'pollutant_rule'
  | 'observation'
  | 'material'
  | 'intervention'
  | 'import'
  | 'manual';
export type EvidenceTargetType = 'risk_score' | 'action_item' | 'recommendation' | 'compliance_result';
export type EvidenceRelationship = 'proves' | 'supports' | 'contradicts' | 'requires' | 'triggers' | 'supersedes';

export interface EvidenceLink {
  id: string;
  source_type: EvidenceSourceType;
  source_id: string;
  target_type: EvidenceTargetType;
  target_id: string;
  relationship: EvidenceRelationship;
  confidence: number | null;
  legal_reference: string | null;
  explanation: string | null;
  created_by: string | null;
  created_at: string;
}

// Building Quality
export interface QualitySection {
  score: number;
  details: string;
}

export interface BuildingQuality {
  overall_score: number;
  sections: Record<string, QualitySection>;
  missing: string[];
}

// Jurisdiction
export type JurisdictionLevel = 'supranational' | 'country' | 'region' | 'commune';

export interface Jurisdiction {
  id: string;
  code: string;
  name: string;
  parent_id: string | null;
  level: JurisdictionLevel;
  country_code: string | null;
  is_active: boolean;
  metadata_json: Record<string, unknown> | null;
  created_at: string;
  regulatory_packs?: RegulatoryPack[];
}

export interface RegulatoryPack {
  id: string;
  jurisdiction_id: string;
  pollutant_type: string;
  version: string;
  is_active: boolean;
  threshold_value: number | null;
  threshold_unit: string | null;
  threshold_action: string | null;
  risk_year_start: number | null;
  risk_year_end: number | null;
  base_probability: number | null;
  work_categories_json: Record<string, unknown> | null;
  waste_classification_json: Record<string, unknown> | null;
  legal_reference: string | null;
  legal_url: string | null;
  description_fr: string | null;
  description_de: string | null;
  notification_required: boolean;
  notification_authority: string | null;
  notification_delay_days: number | null;
  created_at: string;
  updated_at: string;
}

// Portfolio
export interface PortfolioMetrics {
  total_buildings: number;
  risk_distribution: Record<string, number>;
  completeness_avg: number;
  buildings_ready: number;
  buildings_not_ready: number;
  pollutant_prevalence: Record<string, number>;
  actions_pending: number;
  actions_critical: number;
  recent_diagnostics: number;
  interventions_in_progress: number;
}

export interface PortfolioOverview {
  total_buildings: number;
  total_diagnostics: number;
  total_interventions: number;
  total_documents: number;
  active_campaigns: number;
  avg_completeness: number | null;
  avg_trust: number | null;
}

export interface PortfolioRiskDistribution {
  by_level: Record<string, number>;
  avg_risk_score: number | null;
  buildings_above_threshold: number;
}

export interface PortfolioComplianceOverview {
  compliant_count: number;
  non_compliant_count: number;
  partially_compliant_count: number;
  unknown_count: number;
  total_overdue_deadlines: number;
}

export interface PortfolioReadinessOverview {
  ready_count: number;
  partially_ready_count: number;
  not_ready_count: number;
  unknown_count: number;
}

export interface PortfolioGradeDistribution {
  by_grade: Record<string, number>;
}

export interface PortfolioActionSummary {
  total_open: number;
  total_in_progress: number;
  total_completed: number;
  by_priority: Record<string, number>;
  overdue_count: number;
}

export interface PortfolioAlertSummary {
  total_weak_signals: number;
  buildings_on_critical_path: number;
  total_constraint_blockers: number;
  buildings_with_stale_diagnostics: number;
}

export interface PortfolioSummary {
  overview: PortfolioOverview;
  risk: PortfolioRiskDistribution;
  compliance: PortfolioComplianceOverview;
  readiness: PortfolioReadinessOverview;
  grades: PortfolioGradeDistribution;
  actions: PortfolioActionSummary;
  alerts: PortfolioAlertSummary;
  generated_at: string;
  organization_id: string | null;
}

export interface PortfolioHealthScore {
  score: number;
  breakdown: Record<string, { score: number; weight: number }>;
  total_buildings: number;
  organization_id: string | null;
}

// Audit Log
export interface AuditLog {
  id: string;
  user_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  timestamp: string;
  user_email: string | null;
  user_name: string | null;
}

// Completeness
export type CompletenessStatus = 'complete' | 'missing' | 'partial' | 'not_applicable';

export interface CompletenessCheck {
  id: string;
  category: string;
  label_key: string;
  status: CompletenessStatus;
  weight: number;
  details: string | null;
}

export interface CompletenessResult {
  building_id: string;
  workflow_stage: string;
  overall_score: number;
  checks: CompletenessCheck[];
  missing_items: string[];
  ready_to_proceed: boolean;
  evaluated_at: string;
}

// Campaign
export type CampaignType = 'diagnostic' | 'remediation' | 'inspection' | 'maintenance' | 'documentation' | 'other';
export type CampaignStatus = 'draft' | 'active' | 'paused' | 'completed' | 'cancelled';

export interface Campaign {
  id: string;
  title: string;
  description: string | null;
  campaign_type: CampaignType;
  status: CampaignStatus;
  priority: 'low' | 'medium' | 'high' | 'critical';
  organization_id: string | null;
  building_ids: string[] | null;
  target_count: number;
  completed_count: number;
  date_start: string | null;
  date_end: string | null;
  budget_chf: number | null;
  spent_chf: number | null;
  criteria_json: Record<string, unknown> | null;
  notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  progress_pct: number;
}

// Campaign Tracking
export type CampaignTrackingStatus = 'not_started' | 'in_progress' | 'blocked' | 'completed' | 'skipped';

export interface CampaignTracking {
  campaign_id: string;
  building_id: string;
  building_address?: string;
  status: CampaignTrackingStatus;
  progress_pct: number;
  blocker_reason: string | null;
  notes: string | null;
  updated_at: string;
}

export interface CampaignTrackingProgress {
  total: number;
  by_status: Record<CampaignTrackingStatus, number>;
  overall_progress_pct: number;
}

export interface CampaignRecommendation {
  title: string;
  description: string;
  campaign_type: CampaignType;
  priority: 'low' | 'medium' | 'high' | 'critical';
  rationale: string;
  impact_score: number;
  building_count: number;
  building_ids: string[];
  criteria_json: Record<string, unknown> | null;
}

// Search
export interface SearchResult {
  index: 'buildings' | 'diagnostics' | 'documents';
  id: string;
  title: string;
  subtitle: string;
  url: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

// Readiness Assessment
export type ReadinessType = 'safe_to_start' | 'safe_to_tender' | 'safe_to_reopen' | 'safe_to_requalify';
export type ReadinessStatus = 'ready' | 'not_ready' | 'conditionally_ready' | 'blocked';

export interface ReadinessCheck {
  label: string;
  passed: boolean;
  details: string | null;
}

export interface ReadinessBlocker {
  label: string;
  severity: string;
  details: string | null;
}

export interface ReadinessCondition {
  label: string;
  details: string | null;
}

export interface ReadinessAssessment {
  id: string;
  building_id: string;
  readiness_type: ReadinessType;
  status: ReadinessStatus;
  score: number | null;
  checks_json: ReadinessCheck[] | null;
  blockers_json: ReadinessBlocker[] | null;
  conditions_json: ReadinessCondition[] | null;
  prework_triggers?: PreworkTrigger[];
  assessed_at: string;
  valid_until: string | null;
  assessed_by: string | null;
  notes: string | null;
}

// Building Trust Score
export type TrustTrend = 'improving' | 'stable' | 'declining';

export interface BuildingTrustScore {
  id: string;
  building_id: string;
  overall_score: number;
  percent_proven: number | null;
  percent_inferred: number | null;
  percent_declared: number | null;
  percent_obsolete: number | null;
  percent_contradictory: number | null;
  total_data_points: number;
  proven_count: number;
  inferred_count: number;
  declared_count: number;
  obsolete_count: number;
  contradictory_count: number;
  trend: TrustTrend | null;
  previous_score: number | null;
  assessed_at: string;
  assessed_by: string | null;
  notes: string | null;
}

// Unknown Issue
export type UnknownType =
  | 'missing_diagnostic'
  | 'missing_pollutant_evaluation'
  | 'uninspected_zone'
  | 'unconfirmed_material'
  | 'missing_plan'
  | 'undocumented_intervention'
  | 'missing_lab_results'
  | 'incomplete_diagnostic'
  | 'missing_sample'
  | 'unverified_source'
  | 'accessibility_unknown';
export type UnknownSeverity = 'low' | 'medium' | 'high' | 'critical';
export type UnknownStatus = 'open' | 'acknowledged' | 'resolved' | 'accepted_risk';

export interface UnknownIssue {
  id: string;
  building_id: string;
  unknown_type: UnknownType;
  severity: UnknownSeverity;
  status: UnknownStatus;
  title: string;
  description: string | null;
  entity_type: string | null;
  entity_id: string | null;
  blocks_readiness: boolean;
  readiness_types_affected: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  resolution_notes: string | null;
  detected_by: string | null;
  created_at: string;
}

// Saved Simulation
export interface SavedSimulation {
  id: string;
  building_id: string;
  title: string;
  description: string | null;
  simulation_type: string;
  parameters_json: Record<string, unknown> | null;
  results_json: Record<string, unknown> | null;
  total_cost_chf: number | null;
  total_duration_weeks: number | null;
  risk_level_before: string | null;
  risk_level_after: string | null;
  created_by: string | null;
  created_at: string;
}

// Authority Pack
export type AuthorityPackStatus = 'draft' | 'ready' | 'submitted' | 'acknowledged';

export interface AuthorityPackListItem {
  pack_id: string;
  building_id: string;
  canton: string;
  overall_completeness: number;
  generated_at: string;
  status: AuthorityPackStatus;
}

export interface AuthorityPackSection {
  section_name: string;
  section_type: string;
  items: Record<string, unknown>[];
  completeness: number;
  notes: string | null;
}

export interface AuthorityPackResult {
  pack_id: string;
  building_id: string;
  canton: string;
  sections: AuthorityPackSection[];
  total_sections: number;
  overall_completeness: number;
  generated_at: string;
  warnings: string[];
}

// Evidence Summary (facade)
export interface SamplesByPollutant {
  positive: number;
  negative: number;
  total: number;
}

export interface EvidenceSummary {
  building_id: string;
  diagnostics_count: number;
  diagnostics_by_status: Record<string, number>;
  samples_count: number;
  samples_positive: number;
  samples_negative: number;
  samples_by_pollutant: Record<string, SamplesByPollutant>;
  documents_count: number;
  evidence_links_count: number;
  coverage_ratio: number;
}

// Remediation Summary (facade)
export interface RemediationActions {
  total: number;
  open: number;
  done: number;
  blocked: number;
  by_priority: Record<string, number>;
}

export interface RemediationInterventions {
  total: number;
  by_status: Record<string, number>;
}

export interface RemediationSummary {
  building_id: string;
  actions: RemediationActions;
  interventions: RemediationInterventions;
  post_works_states_count: number;
  has_completed_remediation: boolean;
}

// Compliance Summary (facade)
export interface ComplianceArtefacts {
  total: number;
  by_status: Record<string, number>;
  pending_submissions: number;
}

export interface ReadinessGate {
  status: string;
  score: number;
  blockers_count: number;
}

export interface RegulatoryCheckCategory {
  total: number;
  complete: number;
  missing: number;
}

export interface ComplianceSummary {
  building_id: string;
  completeness_score: number;
  completeness_ready: boolean;
  missing_items: string[];
  artefacts: ComplianceArtefacts;
  readiness: Record<string, ReadinessGate>;
  regulatory_checks: Record<string, RegulatoryCheckCategory>;
}

// Field Observation
export type ObservationType = 'visual_inspection' | 'safety_hazard' | 'material_condition' | 'general_note';
export type ObservationSeverity = 'info' | 'minor' | 'moderate' | 'major' | 'critical';

export interface FieldObservation {
  id: string;
  building_id: string;
  zone_id?: string;
  element_id?: string;
  observer_id: string;
  observer_name?: string;
  observation_type: ObservationType;
  severity: ObservationSeverity;
  title: string;
  description?: string;
  location_description?: string;
  observed_at: string;
  photo_reference?: string;
  verified: boolean;
  verified_by_id?: string;
  verified_at?: string;
  status?: string;
  metadata_json?: string;
  created_at: string;
  updated_at: string;
}

export interface FieldObservationCreate {
  building_id: string;
  observation_type: ObservationType;
  severity: ObservationSeverity;
  title: string;
  description?: string;
  zone_id?: string;
  element_id?: string;
  location_description?: string;
  observed_at?: string;
  photo_reference?: string;
}

export interface FieldObservationSummary {
  total_observations: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  unverified_count: number;
  latest_observation_at?: string;
}

// Compliance Artefact
export type ComplianceArtefactStatus = 'draft' | 'submitted' | 'acknowledged' | 'rejected';
export type ComplianceArtefactType =
  | 'suva_notification'
  | 'post_remediation_report'
  | 'disposal_record'
  | 'authority_submission'
  | 'compliance_certificate'
  | 'canton_notification'
  | 'air_measurement_report'
  | 'other';

export interface ComplianceArtefact {
  id: string;
  building_id: string;
  artefact_type: string;
  status: ComplianceArtefactStatus;
  title: string;
  description: string | null;
  reference_number: string | null;
  diagnostic_id: string | null;
  intervention_id: string | null;
  document_id: string | null;
  authority_name: string | null;
  authority_type: string | null;
  submitted_at: string | null;
  acknowledged_at: string | null;
  expires_at: string | null;
  legal_basis: string | null;
  metadata_json: Record<string, unknown> | null;
  created_by: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ComplianceArtefactCreate {
  artefact_type: string;
  title: string;
  description?: string;
  reference_number?: string;
  diagnostic_id?: string;
  intervention_id?: string;
  document_id?: string;
  authority_name?: string;
  authority_type?: string;
  expires_at?: string;
  legal_basis?: string;
  metadata_json?: Record<string, unknown>;
}

export interface ComplianceArtefactUpdate {
  artefact_type?: string;
  title?: string;
  description?: string;
  status?: string;
  reference_number?: string;
  diagnostic_id?: string;
  intervention_id?: string;
  document_id?: string;
  authority_name?: string;
  authority_type?: string;
  expires_at?: string;
  legal_basis?: string;
  metadata_json?: Record<string, unknown>;
}

export interface ComplianceRequiredArtefact {
  artefact_type: string;
  reason: string;
  legal_basis?: string;
}

// Prework Diagnostic Trigger
export type PreworkTriggerUrgency = 'low' | 'medium' | 'high';

export interface PreworkTrigger {
  trigger_type: string;
  reason: string;
  urgency: PreworkTriggerUrgency;
  source_check: string;
}
