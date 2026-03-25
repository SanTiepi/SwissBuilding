from fastapi import APIRouter

from app.api import (
    access_control,
    actions,
    anomaly_detection,
    assignments,
    audience_packs,
    audit_export,
    audit_logs,
    audit_readiness,
    auth,
    authority_packs,
    background_jobs,
    budget_tracking,
    building_age_analysis,
    building_benchmark,
    building_certifications,
    building_clustering,
    building_comparison,
    building_dashboard,
    building_elements,
    building_health_index,
    building_lifecycle,
    building_quality,
    building_snapshots,
    building_valuations,
    buildings,
    bulk_operations,
    campaign_tracking,
    campaigns,
    capex_planning,
    change_signals,
    co_ownership,
    completeness,
    completion_workspace,
    compliance_artefacts,
    compliance_calendar,
    compliance_gap,
    compliance_summary,
    compliance_timeline,
    constraint_graph,
    contact_lookup,
    contractor_acknowledgment,
    contractor_matching,
    contracts,
    control_tower_v2,
    cost_benefit_analysis,
    counterfactual_analysis,
    cross_building_pattern,
    data_provenance,
    data_quality,
    decision_replay,
    demo_pilot,
    diagnostic_integration,
    diagnostic_quality,
    diagnostics,
    digital_vault,
    document_classification,
    document_completeness,
    document_inbox,
    document_templates,
    documents,
    dossier,
    dossier_completion,
    due_diligence,
    eco_clauses,
    energy_performance,
    environmental_impact,
    events,
    evidence,
    evidence_chain,
    evidence_graph,
    evidence_packs,
    evidence_summary,
    exchange,
    execution_quality,
    expansion,
    expert_reviews,
    exports,
    field_observations,
    gdpr,
    handoff_pack,
    incident_response,
    insurance_risk_assessment,
    intake,
    interventions,
    invitations,
    jurisdictions,
    knowledge_gap,
    lab_result,
    leases,
    maintenance_forecast,
    marketplace,
    marketplace_rfq,
    marketplace_trust,
    material_inventory,
    material_recommendations,
    materials,
    monitoring_plan,
    multi_org_dashboard,
    notification_digest,
    notification_preferences,
    notification_rules,
    notifications,
    obligations,
    occupancy_risks,
    occupant_safety,
    organizations,
    ownership,
    pack_impact,
    package_presets,
    partner_trust,
    passport,
    passport_export,
    permit_procedures,
    permit_tracking,
    pollutant_inventory,
    pollutant_map,
    portfolio,
    portfolio_optimization,
    portfolio_summary,
    portfolio_trends,
    post_works,
    priority_matrix,
    proof_delivery,
    public_sector,
    quality_assurance,
    readiness,
    regulatory_change_impact,
    regulatory_deadlines,
    regulatory_filing,
    regulatory_watch,
    remediation_costs,
    remediation_intelligence,
    remediation_post_works,
    remediation_summary,
    remediation_tracking,
    remediation_workspace,
    renovation_sequencer,
    reporting_metrics,
    requalification,
    risk_aggregation,
    risk_analysis,
    risk_communication,
    risk_mitigation,
    rollout,
    sample_optimization,
    samples,
    sampling_planner,
    saved_simulations,
    scenario_planning,
    search,
    sensor_integration,
    shared_links,
    spatial_risk_mapping,
    stakeholder_dashboard,
    stakeholder_notifications,
    stakeholder_report,
    subsidy_tracking,
    swiss_rules_watch,
    technical_plans,
    tenant_impact,
    timeline,
    timeline_enrichment,
    transaction_readiness,
    transfer,
    trust_scores,
    unknowns,
    users,
    ventilation_assessment,
    warranty_obligations,
    waste_management,
    weak_signals,
    work_phases,
    workflow_orchestration,
    workspace,
    zone_classification,
    zone_safety,
    zones,
)

api_router = APIRouter()
api_router.include_router(background_jobs.router, prefix="", tags=["Background Jobs"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(buildings.router, prefix="/buildings", tags=["Buildings"])
api_router.include_router(diagnostics.router, prefix="", tags=["Diagnostics"])
api_router.include_router(samples.router, prefix="", tags=["Samples"])
api_router.include_router(events.router, prefix="", tags=["Events"])
api_router.include_router(documents.router, prefix="", tags=["Documents"])
api_router.include_router(document_inbox.router, prefix="", tags=["Document Inbox"])
api_router.include_router(risk_analysis.router, prefix="/risk-analysis", tags=["Risk Analysis"])
api_router.include_router(pollutant_inventory.router, prefix="", tags=["Pollutant Inventory"])
api_router.include_router(pollutant_map.router, prefix="/pollutant-map", tags=["Pollutant Map"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(actions.router, prefix="", tags=["Actions"])
api_router.include_router(exports.router, prefix="/exports", tags=["Exports"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["Invitations"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(assignments.router, prefix="", tags=["Assignments"])
api_router.include_router(notification_digest.router, prefix="", tags=["Notification Digest"])
api_router.include_router(notifications.router, prefix="", tags=["Notifications"])
api_router.include_router(notification_preferences.router, prefix="", tags=["Notification Preferences"])
api_router.include_router(obligations.router, prefix="", tags=["Obligations"])
api_router.include_router(workspace.router, prefix="", tags=["Workspace"])
api_router.include_router(zones.router, prefix="", tags=["Zones"])
api_router.include_router(zone_classification.router, prefix="", tags=["Zone Classification"])
api_router.include_router(building_elements.router, prefix="", tags=["Building Elements"])
api_router.include_router(materials.router, prefix="", tags=["Materials"])
api_router.include_router(material_inventory.router, prefix="", tags=["Material Inventory"])
api_router.include_router(material_recommendations.router, prefix="", tags=["Material Recommendations"])
api_router.include_router(intake.router, prefix="", tags=["Intake"])
api_router.include_router(interventions.router, prefix="", tags=["Interventions"])
api_router.include_router(leases.router, prefix="", tags=["Leases"])
api_router.include_router(contact_lookup.router, prefix="", tags=["Contacts"])
api_router.include_router(contracts.router, prefix="", tags=["Contracts"])
api_router.include_router(ownership.router, prefix="", tags=["Ownership"])
api_router.include_router(technical_plans.router, prefix="", tags=["Technical Plans"])
api_router.include_router(evidence.router, prefix="", tags=["Evidence"])
api_router.include_router(evidence_chain.router, prefix="", tags=["Evidence Chain"])
api_router.include_router(evidence_graph.router, prefix="", tags=["Evidence Graph"])
api_router.include_router(evidence_packs.router, prefix="", tags=["Evidence Packs"])
api_router.include_router(expert_reviews.router, prefix="", tags=["Expert Reviews"])
api_router.include_router(execution_quality.router, prefix="", tags=["Execution Quality"])
api_router.include_router(dossier.router, prefix="", tags=["Dossier"])
api_router.include_router(building_lifecycle.router, prefix="", tags=["Building Lifecycle"])
api_router.include_router(building_health_index.router, prefix="", tags=["Building Health Index"])
api_router.include_router(building_quality.router, prefix="", tags=["Building Quality"])
api_router.include_router(completeness.router, prefix="", tags=["Completeness"])
api_router.include_router(jurisdictions.router, prefix="", tags=["Jurisdictions"])
api_router.include_router(timeline.router, prefix="", tags=["Timeline"])
api_router.include_router(timeline_enrichment.router, prefix="", tags=["Timeline Enrichment"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
api_router.include_router(audit_logs.router, prefix="", tags=["Audit Logs"])
api_router.include_router(audit_export.router, prefix="", tags=["Audit Export"])
api_router.include_router(audit_readiness.router, prefix="", tags=["Audit Readiness"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(campaigns.router, prefix="", tags=["Campaigns"])
api_router.include_router(campaign_tracking.router, prefix="", tags=["Campaign Tracking"])
api_router.include_router(capex_planning.router, prefix="", tags=["CAPEX Planning"])
api_router.include_router(compliance_artefacts.router, prefix="", tags=["Compliance Artefacts"])
api_router.include_router(control_tower_v2.router, prefix="", tags=["Control Tower v2"])
api_router.include_router(permit_procedures.router, prefix="", tags=["Permit Procedures"])
api_router.include_router(proof_delivery.router, prefix="", tags=["Proof Delivery"])
api_router.include_router(demo_pilot.router, prefix="", tags=["Demo Pilot"])
api_router.include_router(exchange.router, prefix="", tags=["Exchange"])
api_router.include_router(expansion.router, prefix="", tags=["Expansion"])
api_router.include_router(package_presets.router, prefix="", tags=["Package Presets"])
api_router.include_router(audience_packs.router, prefix="", tags=["Audience Packs"])
api_router.include_router(marketplace.router, prefix="", tags=["Marketplace"])
api_router.include_router(marketplace_rfq.router, prefix="", tags=["Marketplace RFQ"])
api_router.include_router(marketplace_trust.router, prefix="", tags=["Marketplace Trust"])
api_router.include_router(remediation_intelligence.router, prefix="", tags=["Remediation Intelligence"])
api_router.include_router(remediation_post_works.router, prefix="", tags=["Remediation Post-Works"])
api_router.include_router(remediation_workspace.router, prefix="", tags=["Remediation Workspace"])
api_router.include_router(rollout.router, prefix="", tags=["Rollout"])
api_router.include_router(public_sector.router, prefix="", tags=["Public Sector"])
api_router.include_router(partner_trust.router, prefix="", tags=["Partner Trust"])
api_router.include_router(swiss_rules_watch.router, prefix="", tags=["Swiss Rules Watch"])
api_router.include_router(compliance_calendar.router, prefix="", tags=["Compliance Calendar"])
api_router.include_router(compliance_gap.router, prefix="", tags=["Compliance Gap"])
api_router.include_router(saved_simulations.router, prefix="", tags=["Saved Simulations"])
api_router.include_router(data_provenance.router, prefix="", tags=["Data Provenance"])
api_router.include_router(data_quality.router, prefix="", tags=["Data Quality"])
api_router.include_router(change_signals.router, prefix="", tags=["Change Signals"])
api_router.include_router(co_ownership.router, prefix="", tags=["Co Ownership"])
api_router.include_router(readiness.router, prefix="", tags=["Readiness"])
api_router.include_router(trust_scores.router, prefix="", tags=["Trust Scores"])
api_router.include_router(unknowns.router, prefix="", tags=["Unknowns"])
api_router.include_router(passport.router, prefix="", tags=["Passport"])
api_router.include_router(evidence_summary.router, prefix="", tags=["Evidence Summary"])
api_router.include_router(remediation_summary.router, prefix="", tags=["Remediation Summary"])
api_router.include_router(compliance_summary.router, prefix="", tags=["Compliance Summary"])
api_router.include_router(passport_export.router, prefix="", tags=["Passport Export"])
api_router.include_router(post_works.router, prefix="", tags=["Post Works"])
api_router.include_router(building_snapshots.router, prefix="", tags=["Building Snapshots"])
api_router.include_router(transfer.router, prefix="", tags=["Transfer Package"])
api_router.include_router(requalification.router, prefix="", tags=["Requalification"])
api_router.include_router(building_comparison.router, prefix="", tags=["Building Comparison"])
api_router.include_router(transaction_readiness.router, prefix="", tags=["Transaction Readiness"])
api_router.include_router(contractor_acknowledgment.router, prefix="", tags=["Contractor Acknowledgments"])
api_router.include_router(contractor_matching.router, prefix="", tags=["Contractor Matching"])
api_router.include_router(dossier_completion.router, prefix="", tags=["Dossier Completion"])
api_router.include_router(energy_performance.router, prefix="", tags=["Energy Performance"])
api_router.include_router(environmental_impact.router, prefix="", tags=["Environmental Impact"])
api_router.include_router(bulk_operations.router, prefix="", tags=["Bulk Operations"])
api_router.include_router(sample_optimization.router, prefix="", tags=["Sample Optimization"])
api_router.include_router(sampling_planner.router, prefix="", tags=["Sampling Planner"])
api_router.include_router(document_templates.router, prefix="", tags=["Document Templates"])
api_router.include_router(completion_workspace.router, prefix="", tags=["Completion Workspace"])
api_router.include_router(multi_org_dashboard.router, prefix="/multi-org", tags=["Multi Org Dashboard"])
api_router.include_router(pack_impact.router, prefix="", tags=["Pack Impact"])
api_router.include_router(field_observations.router, prefix="", tags=["Field Observations"])
api_router.include_router(authority_packs.router, prefix="", tags=["Authority Packs"])
api_router.include_router(portfolio_summary.router, prefix="", tags=["Portfolio Summary"])
api_router.include_router(portfolio_trends.router, prefix="", tags=["Portfolio Trends"])
api_router.include_router(weak_signals.router, prefix="", tags=["Weak Signals"])
api_router.include_router(compliance_timeline.router, prefix="", tags=["Compliance Timeline"])
api_router.include_router(decision_replay.router, prefix="", tags=["Decision Replay"])
api_router.include_router(constraint_graph.router, prefix="", tags=["Constraint Graph"])
api_router.include_router(building_dashboard.router, prefix="", tags=["Building Dashboard"])
api_router.include_router(anomaly_detection.router, prefix="", tags=["Anomaly Detection"])
api_router.include_router(building_age_analysis.router, prefix="", tags=["Building Age Analysis"])
api_router.include_router(building_benchmark.router, prefix="", tags=["Building Benchmark"])
api_router.include_router(maintenance_forecast.router, prefix="", tags=["Maintenance Forecast"])
api_router.include_router(monitoring_plan.router, prefix="", tags=["Monitoring Plan"])
api_router.include_router(regulatory_deadlines.router, prefix="", tags=["Regulatory Deadlines"])
api_router.include_router(remediation_costs.router, prefix="", tags=["Remediation Costs"])
api_router.include_router(remediation_tracking.router, prefix="", tags=["Remediation Tracking"])
api_router.include_router(document_classification.router, prefix="", tags=["Document Classification"])
api_router.include_router(document_completeness.router, prefix="", tags=["Document Completeness"])
api_router.include_router(risk_mitigation.router, prefix="", tags=["Risk Mitigation"])
api_router.include_router(portfolio_optimization.router, prefix="", tags=["Portfolio Optimization"])
api_router.include_router(workflow_orchestration.router, prefix="", tags=["Workflow Orchestration"])
api_router.include_router(insurance_risk_assessment.router, prefix="", tags=["Insurance Risk Assessment"])
api_router.include_router(knowledge_gap.router, prefix="", tags=["Knowledge Gap"])
api_router.include_router(lab_result.router, prefix="", tags=["Lab Results"])
api_router.include_router(regulatory_change_impact.router, prefix="", tags=["Regulatory Change Impact"])
api_router.include_router(regulatory_filing.router, prefix="", tags=["Regulatory Filing"])
api_router.include_router(regulatory_watch.router, prefix="", tags=["Regulatory Watch"])
api_router.include_router(occupant_safety.router, prefix="", tags=["Occupant Safety"])
api_router.include_router(occupancy_risks.router, prefix="/occupancy-risks", tags=["Occupancy Risks"])
api_router.include_router(permit_tracking.router, prefix="", tags=["Permit Tracking"])
api_router.include_router(spatial_risk_mapping.router, prefix="", tags=["Spatial Risk Mapping"])
api_router.include_router(stakeholder_dashboard.router, prefix="", tags=["Stakeholder Dashboard"])
api_router.include_router(stakeholder_notifications.router, prefix="", tags=["Stakeholder Notifications"])
api_router.include_router(stakeholder_report.router, prefix="", tags=["Stakeholder Reports"])
api_router.include_router(waste_management.router, prefix="", tags=["Waste Management"])
api_router.include_router(cost_benefit_analysis.router, prefix="", tags=["Cost Benefit Analysis"])
api_router.include_router(counterfactual_analysis.router, prefix="", tags=["Counterfactual Analysis"])
api_router.include_router(due_diligence.router, prefix="", tags=["Due Diligence"])
api_router.include_router(handoff_pack.router, prefix="", tags=["Handoff Pack"])
api_router.include_router(quality_assurance.router, prefix="", tags=["Quality Assurance"])
api_router.include_router(renovation_sequencer.router, prefix="", tags=["Renovation Sequencer"])
api_router.include_router(risk_communication.router, prefix="", tags=["Risk Communication"])
api_router.include_router(scenario_planning.router, prefix="", tags=["Scenario Planning"])
api_router.include_router(tenant_impact.router, prefix="", tags=["Tenant Impact"])
api_router.include_router(access_control.router, prefix="", tags=["Access Control"])
api_router.include_router(priority_matrix.router, prefix="", tags=["Priority Matrix"])
api_router.include_router(risk_aggregation.router, prefix="", tags=["Risk Aggregation"])
api_router.include_router(diagnostic_integration.router, prefix="", tags=["Diagnostic Integration"])
api_router.include_router(diagnostic_quality.router, prefix="", tags=["Diagnostic Quality"])
api_router.include_router(digital_vault.router, prefix="", tags=["Digital Vault"])
api_router.include_router(budget_tracking.router, prefix="", tags=["Budget Tracking"])
api_router.include_router(ventilation_assessment.router, prefix="", tags=["Ventilation Assessment"])
api_router.include_router(incident_response.router, prefix="", tags=["Incident Response"])
api_router.include_router(reporting_metrics.router, prefix="", tags=["Reporting Metrics"])
api_router.include_router(cross_building_pattern.router, prefix="", tags=["Cross Building Patterns"])
api_router.include_router(eco_clauses.router, prefix="", tags=["Eco Clauses"])
api_router.include_router(
    building_certifications.router, prefix="/building-certifications", tags=["Building Certifications"]
)
api_router.include_router(notification_rules.router, prefix="/notification-rules", tags=["Notification Rules"])
api_router.include_router(building_valuations.router, prefix="", tags=["Building Valuations"])
api_router.include_router(work_phases.router, prefix="", tags=["Work Phases"])
api_router.include_router(building_clustering.router, prefix="", tags=["Building Clustering"])
api_router.include_router(warranty_obligations.router, prefix="", tags=["Warranty Obligations"])
api_router.include_router(subsidy_tracking.router, prefix="", tags=["Subsidy Tracking"])
api_router.include_router(sensor_integration.router, prefix="", tags=["Sensor Integration"])
api_router.include_router(zone_safety.router, prefix="", tags=["Zone Safety"])
api_router.include_router(shared_links.router, prefix="", tags=["Shared Links"])
api_router.include_router(gdpr.router, prefix="", tags=["GDPR"])
