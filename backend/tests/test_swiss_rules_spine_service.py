from __future__ import annotations

from app.schemas.swiss_rules import ApplicabilityStatus, BuildingContext, ProjectContext
from app.services.swiss_rules_spine_service import (
    build_core_swiss_rules_enablement_pack,
    create_impact_review,
    detect_legal_change,
    evaluate_enablement_pack,
    evaluate_rule_applicability,
    snapshot_rule_source,
)


def test_enablement_pack_contains_expected_guardrails_and_targets():
    pack = build_core_swiss_rules_enablement_pack()

    target_codes = {target.code for target in pack.integration_targets}
    guardrail_codes = {guardrail.code for guardrail in pack.guardrails}

    assert "permit_tracking" in target_codes
    assert "obligation" in target_codes
    assert "control_tower" in target_codes
    assert "no_parallel_permit_logic" in guardrail_codes
    assert "no_second_obligation_entity" in guardrail_codes


def test_enablement_pack_contains_seed_official_sources():
    pack = build_core_swiss_rules_enablement_pack()
    source_map = {source.source_id: source.url for source in pack.sources}

    assert source_map["vd_camac"] == "https://www.vd.ch/territoire-et-construction/permis-de-construire"
    assert source_map["ge_building_auth"] == "https://www.ge.ch/demander-autorisation-construire"
    assert source_map["bafu_oled"] == "https://www.bafu.admin.ch/fr/oled"
    assert source_map["suva_asbestos"] == "https://www.suva.ch/fr-ch/prevention/matieres-substances/amiante"
    assert source_map["cadastre_rdppf"] == "https://www.cadastre.ch/fr/cadastre-rdppf"
    assert source_map["ebgb_lhand"] == "https://www.ebgb.admin.ch/fr/loi-sur-legalite-pour-les-personnes-handicapees-lhand"


def test_snapshot_change_detection_returns_event():
    pack = build_core_swiss_rules_enablement_pack()
    source = next(item for item in pack.sources if item.source_id == "vd_camac")

    previous = snapshot_rule_source(source, "version 1 permit guidance")
    current = snapshot_rule_source(source, "version 2 permit guidance")

    event = detect_legal_change(previous, current, impacted_rule_codes=["permit_gatekeeping"])

    assert event is not None
    assert event.source_id == "vd_camac"
    assert event.impacted_rule_codes == ["permit_gatekeeping"]


def test_snapshot_change_detection_skips_identical_content():
    pack = build_core_swiss_rules_enablement_pack()
    source = next(item for item in pack.sources if item.source_id == "bag_radon")

    previous = snapshot_rule_source(source, "same content")
    current = snapshot_rule_source(source, "same content")

    assert detect_legal_change(previous, current) is None


def test_asbestos_project_yields_expected_applicable_rules():
    pack = build_core_swiss_rules_enablement_pack()

    building_context = BuildingContext(canton="VD", radon_risk=False)
    project_context = ProjectContext(
        project_kind="renovation",
        pollutants_detected=["asbestos", "pcb"],
        waste_categories=["special"],
        requires_permit=True,
        touches_structure=True,
    )

    evaluations = evaluate_enablement_pack(pack, building_context, project_context)
    by_code = {evaluation.rule_code: evaluation for evaluation in evaluations}

    assert by_code["permit_gatekeeping"].status == ApplicabilityStatus.APPLICABLE
    assert by_code["permit_gatekeeping"].required_procedure_codes == ["vd_camac_permit"]
    assert by_code["suva_asbestos_notification"].status == ApplicabilityStatus.APPLICABLE
    assert by_code["cantonal_pollutant_declaration"].status == ApplicabilityStatus.APPLICABLE
    assert by_code["oled_waste_manifest"].status == ApplicabilityStatus.APPLICABLE


def test_outside_zone_case_forces_manual_review():
    pack = build_core_swiss_rules_enablement_pack()
    rule = next(item for item in pack.rule_templates if item.code == "permit_gatekeeping")

    evaluation = evaluate_rule_applicability(
        rule,
        BuildingContext(canton="GE", outside_building_zone=True),
        ProjectContext(project_kind="transformation", requires_permit=True),
    )

    assert evaluation.status == ApplicabilityStatus.MANUAL_REVIEW
    assert "outside_building_zone" in evaluation.manual_review_reasons
    assert evaluation.required_procedure_codes == ["ge_building_authorization"]


def test_impact_review_maps_impacted_subsystems():
    pack = build_core_swiss_rules_enablement_pack()
    source = next(item for item in pack.sources if item.source_id == "bafu_oled")
    previous = snapshot_rule_source(source, "manifest v1")
    current = snapshot_rule_source(source, "manifest v2")
    event = detect_legal_change(previous, current, impacted_rule_codes=["oled_waste_manifest", "permit_gatekeeping"])

    assert event is not None
    review = create_impact_review(event, decision_summary="Needs procedural refresh")

    assert review.republish_required is True
    assert "regulatory_filing" in review.impacted_subsystems
    assert "permit_tracking" in review.impacted_subsystems


def test_accessibility_rule_applies_for_public_use_project():
    pack = build_core_swiss_rules_enablement_pack()
    rule = next(item for item in pack.rule_templates if item.code == "accessibility_review")

    evaluation = evaluate_rule_applicability(
        rule,
        BuildingContext(canton="VD", usage="public"),
        ProjectContext(project_kind="new_build", public_facing=True, requires_permit=True),
    )

    assert evaluation.status == ApplicabilityStatus.MANUAL_REVIEW
    assert "accessibility_scope" in evaluation.manual_review_reasons


def test_natural_hazard_rule_applies_for_hazard_area():
    pack = build_core_swiss_rules_enablement_pack()
    rule = next(item for item in pack.rule_templates if item.code == "natural_hazard_review")

    evaluation = evaluate_rule_applicability(
        rule,
        BuildingContext(canton="FR", special_case_tags=["flood_risk"]),
        ProjectContext(project_kind="renovation", requires_permit=True, touches_structure=True),
    )

    assert evaluation.status == ApplicabilityStatus.MANUAL_REVIEW
    assert "natural_hazard_area" in evaluation.manual_review_reasons
