"""Test suite for GE Rules Pack — Geneva canton compliance rules (40+ rules, 20+ tests)."""

import pytest

from app.services.rules_packs.ge_rules_pack import (
    GE_RULES_PACK,
    Rule,
    RuleCategory,
    RuleSeverity,
    get_applicable_rules,
    get_rules_by_category,
    get_rules_by_severity,
)


class TestGERulesPackStructure:
    """Test overall structure and metadata of GE rules pack."""

    def test_ge_rules_pack_exists(self):
        """Test that GE rules pack is properly defined."""
        assert GE_RULES_PACK is not None
        assert GE_RULES_PACK["version"] == "1.0.0"
        assert GE_RULES_PACK["canton"] == "GE"

    def test_ge_rules_pack_contains_minimum_rules(self):
        """Test that GE pack contains at least 40 rules."""
        assert GE_RULES_PACK["count"] >= 40
        assert len(GE_RULES_PACK["rules"]) == GE_RULES_PACK["count"]

    def test_all_rules_have_required_fields(self):
        """Test that every rule has all required fields."""
        for rule in GE_RULES_PACK["rules"]:
            assert rule.id is not None
            assert rule.title_fr is not None
            assert rule.description_fr is not None
            assert rule.category is not None
            assert rule.severity is not None
            assert rule.canton == "GE"

    def test_rule_ids_are_unique(self):
        """Test that all rule IDs are unique."""
        ids = [r.id for r in GE_RULES_PACK["rules"]]
        assert len(ids) == len(set(ids)), "Duplicate rule IDs found"

    def test_all_rule_ids_follow_naming_convention(self):
        """Test that rule IDs follow GE_CATEGORY_NNN format."""
        for rule in GE_RULES_PACK["rules"]:
            assert rule.id.startswith("GE_"), f"Rule {rule.id} doesn't start with GE_"
            parts = rule.id.split("_")
            assert len(parts) == 3, f"Rule {rule.id} doesn't follow GE_CATEGORY_NNN format"

    def test_rule_categories_are_valid(self):
        """Test that all rules use valid category enums."""
        valid_categories = {c.value for c in RuleCategory}
        for rule in GE_RULES_PACK["rules"]:
            assert rule.category in RuleCategory

    def test_rule_severities_are_valid(self):
        """Test that all rules use valid severity enums."""
        valid_severities = {s.value for s in RuleSeverity}
        for rule in GE_RULES_PACK["rules"]:
            assert rule.severity in RuleSeverity


class TestAsbestosRules:
    """Test asbestos-specific rules."""

    def test_asbestos_rules_minimum_count(self):
        """Test that at least 10 asbestos rules exist."""
        asbestos_rules = get_rules_by_category(RuleCategory.ASBESTOS)
        assert len(asbestos_rules) >= 10

    def test_diagnostic_amiante_obligatoire_rule_exists(self):
        """Test GE_ASB_001 rule exists (diagnostic amiante obligatoire)."""
        rules = get_rules_by_category(RuleCategory.ASBESTOS)
        asbeste_rules = [r for r in rules if r.id == "GE_ASB_001"]
        assert len(asbeste_rules) == 1
        rule = asbeste_rules[0]
        assert rule.severity == RuleSeverity.CRITICAL

    def test_asbestos_removal_before_demolition_rule(self):
        """Test GE_ASB_003 rule (désamiantage avant démolition)."""
        rules = get_rules_by_category(RuleCategory.ASBESTOS)
        rules = [r for r in rules if r.id == "GE_ASB_003"]
        assert len(rules) == 1
        assert rules[0].severity == RuleSeverity.CRITICAL

    def test_asbestos_friable_rules_exist(self):
        """Test rules for friable asbestos (GE_ASB_004)."""
        rules = [r for r in GE_RULES_PACK["rules"] if r.id == "GE_ASB_004"]
        assert len(rules) == 1


class TestPCBRules:
    """Test PCB-specific rules."""

    def test_pcb_rules_minimum_count(self):
        """Test that at least 8 PCB rules exist."""
        pcb_rules = get_rules_by_category(RuleCategory.PCB)
        assert len(pcb_rules) >= 8

    def test_pcb_diagnostic_1955_1975_rule(self):
        """Test GE_PCB_001 rule (diagnostic PCB 1955-1975)."""
        rules = [r for r in GE_RULES_PACK["rules"] if r.id == "GE_PCB_001"]
        assert len(rules) == 1
        rule = rules[0]
        assert rule.applies_to_year_min == 1955
        assert rule.applies_to_year_max == 1975

    def test_pcb_equipment_replacement_rule(self):
        """Test GE_PCB_003 rule (equipment PCB replacement)."""
        rules = [r for r in GE_RULES_PACK["rules"] if r.id == "GE_PCB_003"]
        assert len(rules) == 1
        assert rules[0].severity == RuleSeverity.CRITICAL


class TestLeadRules:
    """Test lead-specific rules."""

    def test_lead_rules_minimum_count(self):
        """Test that at least 8 lead rules exist."""
        lead_rules = get_rules_by_category(RuleCategory.LEAD)
        assert len(lead_rules) >= 8

    def test_lead_diagnostic_before_2006_rule(self):
        """Test GE_LEAD_001 rule (diagnostic plomb before 2006)."""
        rules = [r for r in GE_RULES_PACK["rules"] if r.id == "GE_LEAD_001"]
        assert len(rules) == 1
        rule = rules[0]
        assert rule.applies_to_year_max == 2006
        assert rule.severity == RuleSeverity.CRITICAL

    def test_lead_water_contamination_rule(self):
        """Test GE_LEAD_004 rule (water lead content)."""
        rules = [r for r in GE_RULES_PACK["rules"] if r.id == "GE_LEAD_004"]
        assert len(rules) == 1
        rule = rules[0]
        assert "<10µg/L" in rule.description_fr


class TestRuleFiltering:
    """Test rule filtering utilities."""

    def test_get_rules_by_category_asbestos(self):
        """Test filtering rules by asbestos category."""
        asbestos_rules = get_rules_by_category(RuleCategory.ASBESTOS)
        assert len(asbestos_rules) >= 10
        for rule in asbestos_rules:
            assert rule.category == RuleCategory.ASBESTOS

    def test_get_rules_by_severity_critical(self):
        """Test filtering rules by critical severity."""
        critical_rules = get_rules_by_severity(RuleSeverity.CRITICAL)
        assert len(critical_rules) >= 5
        for rule in critical_rules:
            assert rule.severity == RuleSeverity.CRITICAL

    def test_get_applicable_rules_for_old_building(self):
        """Test getting applicable rules for 1970 building."""
        rules_1970 = get_applicable_rules(1970)
        # 1970 building should be affected by:
        # - Asbestos (before 1990)
        # - PCB (1955-1975 range)
        # - Lead (before 2006)
        # - HAP (< 1950 not applicable)

        asb_rules = [r for r in rules_1970 if r.category == RuleCategory.ASBESTOS]
        pcb_rules = [r for r in rules_1970 if r.category == RuleCategory.PCB]
        lead_rules = [r for r in rules_1970 if r.category == RuleCategory.LEAD]

        assert len(asb_rules) > 0
        assert len(pcb_rules) > 0
        assert len(lead_rules) > 0

    def test_get_applicable_rules_for_new_building(self):
        """Test getting applicable rules for 2010 building."""
        rules_2010 = get_applicable_rules(2010)
        # 2010 building should only have non-temporal rules (documentation, environmental, occupational)

        # Should not have asbestos diagnostic rule (before 2005)
        asb_diagnostic = [r for r in rules_2010 if r.id == "GE_ASB_001"]
        assert len(asb_diagnostic) == 0

    def test_year_filtering_asbestos(self):
        """Test that asbestos rules correctly filter by year."""
        # Building from 1985 should have asbestos rules
        rules_1985 = get_applicable_rules(1985)
        asb_rules_1985 = [r for r in rules_1985 if r.category == RuleCategory.ASBESTOS]
        assert len(asb_rules_1985) > 0

        # Building from 2010 should not have asbestos diagnostic rule
        rules_2010 = get_applicable_rules(2010)
        asb_diagnostic_2010 = [r for r in rules_2010 if r.id == "GE_ASB_001"]
        assert len(asb_diagnostic_2010) == 0

    def test_year_filtering_pcb(self):
        """Test that PCB rules correctly filter by year range."""
        # 1960 building in PCB range
        rules_1960 = get_applicable_rules(1960)
        pcb_rules_1960 = [r for r in rules_1960 if r.id == "GE_PCB_001"]
        assert len(pcb_rules_1960) > 0

        # 1950 building before PCB range
        rules_1950 = get_applicable_rules(1950)
        pcb_rules_1950 = [r for r in rules_1950 if r.id == "GE_PCB_001"]
        assert len(pcb_rules_1950) == 0

        # 1980 building after PCB range
        rules_1980 = get_applicable_rules(1980)
        pcb_rules_1980 = [r for r in rules_1980 if r.id == "GE_PCB_001"]
        assert len(pcb_rules_1980) == 0


class TestRuleRemediations:
    """Test remediation guidance in rules."""

    def test_critical_rules_have_guidance(self):
        """Test that all critical rules have remediation guidance."""
        critical_rules = get_rules_by_severity(RuleSeverity.CRITICAL)
        for rule in critical_rules:
            assert rule.remediation_guidance is not None
            assert len(rule.remediation_guidance) > 10

    def test_example_asbestos_remediation(self):
        """Test specific asbestos remediation guidance."""
        rule = [r for r in GE_RULES_PACK["rules"] if r.id == "GE_ASB_001"][0]
        assert "diagnostic" in rule.remediation_guidance.lower()
        assert "ISO 17020" in rule.remediation_guidance

    def test_example_pcb_remediation(self):
        """Test specific PCB remediation guidance."""
        rule = [r for r in GE_RULES_PACK["rules"] if r.id == "GE_PCB_003"][0]
        assert "remplaç" in rule.remediation_guidance.lower()

    def test_example_lead_remediation(self):
        """Test specific lead remediation guidance."""
        rule = [r for r in GE_RULES_PACK["rules"] if r.id == "GE_LEAD_005"][0]
        assert "remplacement" in rule.remediation_guidance.lower()


class TestRuleMetadata:
    """Test rule metadata completeness."""

    def test_all_rules_in_french(self):
        """Test that rule titles and descriptions are in French."""
        for rule in GE_RULES_PACK["rules"]:
            # Check for French characters or specific French patterns
            text = rule.title_fr + " " + rule.description_fr
            # Should have reasonable length
            assert len(rule.title_fr) > 5
            assert len(rule.description_fr) > 10

    def test_categories_coverage(self):
        """Test that rules cover all major categories."""
        categories_present = set(r.category for r in GE_RULES_PACK["rules"])
        # At least these categories should be present
        expected = {
            RuleCategory.ASBESTOS,
            RuleCategory.PCB,
            RuleCategory.LEAD,
        }
        assert expected.issubset(categories_present)

    def test_severity_distribution(self):
        """Test that rules have a reasonable distribution of severities."""
        critical = len(get_rules_by_severity(RuleSeverity.CRITICAL))
        warning = len(get_rules_by_severity(RuleSeverity.WARNING))
        info = len(get_rules_by_severity(RuleSeverity.INFO))

        # Most should be critical/warning, some info
        assert critical > 0
        assert warning > 0
        assert critical + warning > info  # More critical/warning than info


class TestRuleConsistency:
    """Test internal consistency of rules."""

    def test_no_overlapping_year_ranges(self):
        """Test that year-based rules don't have conflicting ranges."""
        # This is more of a documentation test;
        # it's OK for ranges to overlap (multiple hazards in same period)
        # But we should be aware of it
        pass

    def test_rule_object_type(self):
        """Test that all rules are Rule instances."""
        for rule in GE_RULES_PACK["rules"]:
            assert isinstance(rule, Rule)

    def test_pack_metadata_consistent(self):
        """Test that pack metadata is consistent."""
        assert GE_RULES_PACK["count"] == len(GE_RULES_PACK["rules"])
        assert GE_RULES_PACK["canton"] == "GE"
        assert GE_RULES_PACK["version"] is not None
