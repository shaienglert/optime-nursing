from __future__ import annotations

import unittest

from app.services import patient_decision_engine as production_runtime

try:
    from .interpreter_road import decision_facts, interpreter_off, interpreter_packet, interpreter_returning, statement
except ImportError:  # pragma: no cover - direct module import
    from interpreter_road import decision_facts, interpreter_off, interpreter_packet, interpreter_returning, statement


class LaunchPracticalConstraintContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Follow the explicit production chain: integrated runtime -> governed
        # facade -> legacy evidence core. Never rely on the ambiguous
        # patient_decision_engine module/package name for private contracts.
        cls.core = production_runtime._governed._legacy

    # Single authority (owner, 2026-10-01): free text reaches the production profile only as
    # the interpreter's questionnaire_patch (AI_EXTRACTED Structured Profile fields). The old
    # recognized_tokens assertions checked the regex reader itself; that responsibility now
    # belongs to the Live Golden Interpreter set, and the regex mapping no longer runs
    # (status RAW_NARRATIVE_NOT_DECISION_INPUT).
    BUDGET_MEDICAID_TEXT = "Her budget is $5,000 per month and Medicaid eligibility is pending."
    NEGATED_MEDICAID_TEXT = "He has Medicare and is not applying for Medicaid."

    def test_budget_survives_while_insurance_is_removed_from_the_production_profile(self) -> None:
        packet = interpreter_packet(
            {"budget": 5000, "medicaidStatus": "Application pending"},
            [statement(self.BUDGET_MEDICAID_TEXT, ["budget", "medicaidStatus"])],
        )
        with interpreter_returning(packet):
            profile = production_runtime.build_patient_needs_profile({}, self.BUDGET_MEDICAID_TEXT)
        needs = {item["parameter_id"]: item for item in profile["needs"]}
        self.assertIn("published_rates", needs)
        self.assertNotIn("medicaid_attributes", needs)
        fields = profile["canonical_structured_profile"]["fields"]
        self.assertEqual("AI_EXTRACTED", fields["budget"]["provenance"])
        self.assertNotIn("medicaidStatus", profile["canonical_decision_questionnaire"])
        self.assertEqual("RAW_NARRATIVE_NOT_DECISION_INPUT", profile["natural_language_mapping"]["status"])

    def test_budget_and_medicaid_text_without_the_interpreter_changes_no_decision_fact(self) -> None:
        with interpreter_off():
            baseline = decision_facts(production_runtime.build_patient_needs_profile({}, ""))
            profile = production_runtime.build_patient_needs_profile({}, self.BUDGET_MEDICAID_TEXT)
        self.assertEqual(baseline, decision_facts(profile))
        needs = {item["parameter_id"] for item in profile["needs"]}
        self.assertNotIn("published_rates", needs)
        self.assertNotIn("medicaid_attributes", needs)

    def test_negated_medicaid_does_not_become_a_preference(self) -> None:
        packet = interpreter_packet(
            {"medicaidStatus": "Not eligible"},
            [statement("not applying for Medicaid", ["medicaidStatus"], knowledge_state="NEGATED")],
        )
        with interpreter_returning(packet):
            profile = production_runtime.build_patient_needs_profile({"medicaidStatus": "Not eligible"}, self.NEGATED_MEDICAID_TEXT)
        needs = {item["parameter_id"]: item for item in profile["needs"]}
        self.assertNotIn("medicaid_attributes", needs)
        self.assertNotIn("medicaidStatus", profile["canonical_decision_questionnaire"])

    def test_negated_medicaid_text_without_the_interpreter_changes_no_decision_fact(self) -> None:
        # Negation handling inside the regex reader is now the Live Golden Interpreter
        # set's responsibility; with AI off the sentence has no decision effect at all.
        state = {"medicaidStatus": "Not eligible"}
        with interpreter_off():
            baseline = decision_facts(production_runtime.build_patient_needs_profile(state, ""))
            profile = production_runtime.build_patient_needs_profile(state, self.NEGATED_MEDICAID_TEXT)
        self.assertEqual(baseline, decision_facts(profile))
        self.assertNotIn("medicaid_attributes", {item["parameter_id"] for item in profile["needs"]})

    def test_legacy_structured_insurance_never_changes_the_search(self) -> None:
        profile = production_runtime.build_patient_needs_profile(
            {"medicaidStatus": "Application pending"},
            "She needs help finding an appropriate community.",
        )
        needs = {item["parameter_id"]: item for item in profile["needs"]}
        self.assertNotIn("medicaid_attributes", needs)
        self.assertNotIn("medicaidStatus", profile["canonical_decision_questionnaire"])

    def test_practical_gaps_are_visible_without_becoming_safety_failures(self) -> None:
        needs = [
            {"parameter_id": "published_rates", "requirement_level": "PREFERENCE", "desired_value": "KNOWN", "acceptable_values": ["KNOWN", "UNKNOWN"]},
            {"parameter_id": "medicaid_attributes", "requirement_level": "PREFERENCE", "desired_value": "YES", "acceptable_values": ["YES", "UNKNOWN"]},
        ]
        eligibility = self.core._eligibility_from_needs(needs, {})
        _strong, verify, _concerns = self.core._top_reasons(
            eligibility,
            [{"parameter_id": "current_availability"}],
        )

        self.assertEqual("ELIGIBLE", eligibility["eligibility_status"])
        self.assertEqual(2, len(eligibility["unknown_preferences"]))
        self.assertIn("Current monthly pricing and fees must be confirmed against your stated budget", verify)
        self.assertIn("Medicaid acceptance and the applicable payment pathway must be confirmed", verify)
        self.assertEqual(
            [
                "Current availability must be confirmed directly with the facility",
                "Current monthly pricing and fees must be confirmed against your stated budget",
                "Medicaid acceptance and the applicable payment pathway must be confirmed",
            ],
            verify[:3],
        )


if __name__ == "__main__":
    unittest.main()


def test_availability_yes_and_no_both_require_direct_confirmation():
    from app.services import decision_engine_core as core
    need={"parameter_id":"current_availability","requirement_level":"HIGH","desired_value":"YES","acceptable_values":["YES"]}
    for raw in ("YES","NO","LIMITED","UNKNOWN"):
        status, reason = core._evaluate_need(need,{"current_availability":{"raw_value":raw,"source":"provider evidence"}})
        assert status == "UNKNOWN"
        assert "direct facility confirmation" in reason
