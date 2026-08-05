import unittest

from app.core.contracts import EligibilityStatus, EvidenceState, RequirementLevel
from app.domains.senior_living.adapter import (
    pair_evaluation_from_patient_result,
    requirement_from_patient_need,
)


class CoreContractTests(unittest.TestCase):
    def test_requirement_level_translation_preserves_constitutional_meaning(self) -> None:
        must = requirement_from_patient_need(
            {
                "parameter_id": "required_capability",
                "requirement_level": "REQUIRED",
                "desired_value": "YES",
                "acceptable_values": ["YES"],
                "need_text": "Required capability",
            }
        )
        important = requirement_from_patient_need(
            {
                "parameter_id": "important_capability",
                "requirement_level": "HIGH",
                "desired_value": "YES",
                "acceptable_values": ["YES"],
            }
        )
        nice = requirement_from_patient_need(
            {
                "parameter_id": "preferred_capability",
                "requirement_level": "PREFERENCE",
                "desired_value": "YES",
                "acceptable_values": ["YES"],
            }
        )

        self.assertEqual(must.level, RequirementLevel.MUST)
        self.assertEqual(important.level, RequirementLevel.IMPORTANT)
        self.assertEqual(nice.level, RequirementLevel.NICE_TO_HAVE)


class SeniorLivingAdapterTests(unittest.TestCase):
    def _profile(self) -> dict:
        return {
            "profile_key": "stroke",
            "location_city": "MIAMI",
            "need_tags": ["pt", "nursing"],
        }

    def test_adapter_preserves_not_eligible_status_without_redeciding(self) -> None:
        result = {
            "canonical_facility_id": "FAC-1",
            "facility_name": "Facility One",
            "eligibility_status": "INELIGIBLE",
            "eligibility": {
                "matched_needs": [],
                "unmet_verified_needs": [
                    {
                        "parameter_id": "pt",
                        "status": "VERIFIED_GAP",
                        "raw_value": "NO",
                        "source": "CMS",
                        "reason": "Physical therapy is not verified as available",
                    }
                ],
                "unknown_critical_needs": [],
                "unknown_noncritical_needs": [],
            },
            "explanation": {
                "strengths": [],
                "trade_offs": ["A required capability is not available"],
                "unknowns": [],
                "questions_to_confirm": [],
            },
        }

        adapted = pair_evaluation_from_patient_result(self._profile(), result)

        self.assertEqual(adapted.eligibility, EligibilityStatus.NOT_ELIGIBLE)
        self.assertEqual(adapted.option.option_id, "FAC-1")
        self.assertEqual(adapted.requirement_evaluations[0].state, EvidenceState.NO)
        self.assertFalse(adapted.requirement_evaluations[0].matched)

    def test_unknown_required_evidence_remains_unknown_not_rejected(self) -> None:
        result = {
            "canonical_facility_id": "FAC-2",
            "facility_name": "Facility Two",
            "eligibility_status": "INSUFFICIENT_EVIDENCE",
            "eligibility": {
                "matched_needs": [],
                "unmet_verified_needs": [],
                "unknown_critical_needs": [
                    {
                        "parameter_id": "nursing_24_7",
                        "status": "UNKNOWN",
                        "raw_value": "UNKNOWN",
                        "source": "Direct confirmation required",
                        "reason": "The capability has not been verified",
                    }
                ],
                "unknown_noncritical_needs": [],
            },
            "explanation": {
                "strengths": [],
                "trade_offs": [],
                "unknowns": ["24/7 nursing availability"],
                "questions_to_confirm": ["Is 24/7 nursing currently available?"],
            },
        }

        adapted = pair_evaluation_from_patient_result(self._profile(), result)

        self.assertEqual(adapted.eligibility, EligibilityStatus.ELIGIBLE_WITH_UNKNOWNS)
        self.assertIsNone(adapted.requirement_evaluations[0].matched)
        self.assertEqual(adapted.requirement_evaluations[0].state, EvidenceState.UNKNOWN)
        self.assertEqual(len(adapted.explanation.questions), 1)

    def test_adapter_does_not_expose_domain_entities_in_core_types(self) -> None:
        result = {
            "canonical_facility_id": "FAC-3",
            "facility_name": "Facility Three",
            "eligibility_status": "ELIGIBLE",
            "eligibility": {
                "matched_needs": [
                    {
                        "parameter_id": "pt",
                        "status": "MATCH",
                        "raw_value": "YES",
                        "source": "CMS",
                        "reason": "Verified",
                    }
                ],
                "unmet_verified_needs": [],
                "unknown_critical_needs": [],
                "unknown_noncritical_needs": [],
            },
            "explanation": {"strengths": ["Verified capability"]},
        }

        adapted = pair_evaluation_from_patient_result(self._profile(), result)

        self.assertEqual(adapted.eligibility, EligibilityStatus.ELIGIBLE)
        self.assertEqual(adapted.party.party_type, "SENIOR_LIVING_SEEKER")
        self.assertEqual(adapted.option.option_type, "SENIOR_LIVING_FACILITY")
        self.assertTrue(adapted.requirement_evaluations[0].matched)


if __name__ == "__main__":
    unittest.main()
