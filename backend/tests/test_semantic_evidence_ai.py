from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.semantic_evidence_ai import CAPABILITY_SCHEMA, capability_map, interpret_facility_evidence_with_ai


def packet(overrides=None):
    overrides = overrides or {}
    capabilities = []
    for key, schema in CAPABILITY_SCHEMA.items():
        level = overrides.get(key, "NONE_OR_NOT_STATED")
        capabilities.append({
            "capability": key,
            "level": level,
            "evidence_summary": "Governed test interpretation",
            "confidence": "HIGH",
        })
    return {"capabilities": capabilities}


class SemanticEvidenceAiTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"OPTIME_SEMANTIC_EVIDENCE_AI_ENABLED": "1"}, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def interpret(self, result):
        return interpret_facility_evidence_with_ai(
            facility_name="Example Residence",
            city="Las Vegas",
            source_url="https://example.org/services",
            source_text="Official provider source text using arbitrary natural language.",
            requested_parameters=["medication support"],
            transport=lambda _: result,
        )

    def test_semantic_management_level_satisfies_medication_guardian_without_keyword_dependency(self):
        result = self.interpret(packet({"MEDICATION_SUPPORT": "MANAGEMENT_OR_SUPERVISION"}))
        medication = capability_map(result)["MEDICATION_SUPPORT"]
        self.assertEqual(result["status"], "AI_SEMANTIC_EVIDENCE_INTERPRETED")
        self.assertTrue(medication["guardian_must_sufficient"])

    def test_reminder_only_does_not_satisfy_medication_management_must(self):
        result = self.interpret(packet({"MEDICATION_SUPPORT": "REMINDER_ONLY"}))
        medication = capability_map(result)["MEDICATION_SUPPORT"]
        self.assertFalse(medication["guardian_must_sufficient"])

    def test_self_admin_assistance_is_distinct_and_sufficient(self):
        result = self.interpret(packet({"MEDICATION_SUPPORT": "SELF_ADMIN_ASSISTANCE"}))
        medication = capability_map(result)["MEDICATION_SUPPORT"]
        self.assertTrue(medication["guardian_must_sufficient"])
        self.assertEqual(medication["level"], "SELF_ADMIN_ASSISTANCE")

    def test_general_personal_care_does_not_prove_specific_adl(self):
        result = self.interpret(packet({"ADL_SUPPORT": "GENERAL_PERSONAL_CARE"}))
        self.assertFalse(capability_map(result)["ADL_SUPPORT"]["guardian_must_sufficient"])

    def test_specific_adl_assistance_does_satisfy_adl_guardian(self):
        result = self.interpret(packet({"ADL_SUPPORT": "SPECIFIC_ADL_ASSISTANCE"}))
        self.assertTrue(capability_map(result)["ADL_SUPPORT"]["guardian_must_sufficient"])

    def test_closed_world_rejects_missing_capabilities_when_required(self):
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_EVIDENCE_AI_REQUIRED": "1"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "SEMANTIC_EVIDENCE_AI_REQUIRED_FAILED"):
                self.interpret({"capabilities": [{"capability": "MEDICATION_SUPPORT", "level": "ADMINISTRATION_BY_STAFF", "confidence": "HIGH"}]})

    def test_arbitrary_provider_wording_is_passed_to_ai_not_reduced_to_synonym_match(self):
        seen = {}

        def transport(prompt):
            seen.update(prompt)
            return packet({"MEDICATION_SUPPORT": "ADMINISTRATION_BY_STAFF"})

        source = "Our certified care associates safely give prescribed medicines at the ordered times."
        result = interpret_facility_evidence_with_ai(
            facility_name="Example Residence",
            city="Las Vegas",
            source_url="https://example.org/services",
            source_text=source,
            requested_parameters=["medication support"],
            transport=transport,
        )
        self.assertIn(source, seen["source_text"])
        self.assertTrue(capability_map(result)["MEDICATION_SUPPORT"]["guardian_must_sufficient"])


if __name__ == "__main__":
    unittest.main()
