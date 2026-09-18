from __future__ import annotations

import unittest

from app.services.patient_decision_engine import build_patient_needs_profile
from app.services.patient_decision_engine_runtime import _governed


class StructuredMedicalNeedsMappingTests(unittest.TestCase):
    """The "Select every relevant need" checkboxes (medicalCareProfile.needs) used to
    never become a `need` at all unless the AI clarification step happened to ask a
    follow-up about them -- a client who picked e.g. "Oxygen" but got no AI question was
    invisibly treated by care-setting ranking as having no clinical need whatsoever.
    """

    def _needs_by_id(self, needs_selected, **medical_extra):
        profile = build_patient_needs_profile(
            {
                "assistanceLevel": "Help with medications, Daytime supervision",
                "memoryStatus": "No",
                "medicalCareProfile": {"hasOngoingMedicalNeeds": "Yes", "needs": needs_selected, **medical_extra},
            },
            "",
        )
        return {item["parameter_id"]: item for item in profile["needs"]}

    def test_dialysis_checkbox_creates_a_required_need(self) -> None:
        by_id = self._needs_by_id(["Dialysis"])
        self.assertEqual("REQUIRED", by_id["dialysis_arrangements"]["requirement_level"])

    def test_wound_care_checkbox_creates_a_high_need(self) -> None:
        by_id = self._needs_by_id(["Wound care"])
        self.assertEqual("HIGH", by_id["wound_care"]["requirement_level"])

    def test_continuous_oxygen_is_high_intermittent_oxygen_is_not(self) -> None:
        continuous = self._needs_by_id(["Oxygen"], oxygenUse="Continuously")
        self.assertEqual("HIGH", continuous["respiratory_trach_vent"]["requirement_level"])

        as_needed = self._needs_by_id(["Oxygen"], oxygenUse="As needed")
        self.assertEqual("MEDIUM", as_needed["respiratory_trach_vent"]["requirement_level"])

    def test_nursing_supervision_checkbox_maps_to_nursing_24_7(self) -> None:
        by_id = self._needs_by_id(["Nursing supervision"])
        self.assertEqual("HIGH", by_id["nursing_24_7"]["requirement_level"])

    def test_no_medical_needs_selected_adds_nothing(self) -> None:
        by_id = self._needs_by_id([])
        for parameter_id in ("dialysis_arrangements", "wound_care", "respiratory_trach_vent"):
            self.assertNotIn(parameter_id, by_id)

    def test_continuous_oxygen_rules_out_plain_independent_living(self) -> None:
        profile = build_patient_needs_profile(
            {
                "assistanceLevel": "Help with medications, Daytime supervision",
                "memoryStatus": "No",
                "medicalCareProfile": {"hasOngoingMedicalNeeds": "Yes", "needs": ["Oxygen"], "oxygenUse": "Continuously"},
            },
            "",
        )
        context = _governed._care_setting_context(profile)
        self.assertTrue(context["needs_residential_assistance"])
        self.assertFalse(context["requires_skilled"])
        il = _governed._care_setting_fit(context, {"canonical_type": "INDEPENDENT_LIVING"}, {"canonical_type": "INDEPENDENT_LIVING"})
        al = _governed._care_setting_fit(context, {"canonical_type": "ASSISTED_LIVING_RFG"}, {"canonical_type": "ASSISTED_LIVING_RFG"})
        self.assertEqual("INSUFFICIENT_SETTING", il["status"])
        self.assertEqual("PRIMARY_FIT", al["status"])

    def test_dialysis_alone_without_a_skilled_nursing_checkbox_still_requires_skilled_setting(self) -> None:
        profile = build_patient_needs_profile(
            {
                "assistanceLevel": "Help with bathing",
                "memoryStatus": "No",
                "medicalCareProfile": {"hasOngoingMedicalNeeds": "Yes", "needs": ["Dialysis"]},
            },
            "",
        )
        context = _governed._care_setting_context(profile)
        self.assertTrue(context["requires_skilled"])
        snf = _governed._care_setting_fit(context, {"canonical_type": "SKILLED_NURSING"}, {"canonical_type": "SKILLED_NURSING"})
        al = _governed._care_setting_fit(context, {"canonical_type": "ASSISTED_LIVING_RFG"}, {"canonical_type": "ASSISTED_LIVING_RFG"})
        self.assertEqual("PRIMARY_FIT", snf["status"])
        self.assertEqual("INSUFFICIENT_SETTING", al["status"])

    def test_assistance_checkboxes_previously_unrecognized_now_register(self) -> None:
        # "Help with dressing"/"toileting"/"medications" and "Daytime supervision" matched
        # no keyword at all before -- selecting only these produced zero needs.
        for label in ("Help with dressing", "Help with toileting", "Help with medications", "Daytime supervision"):
            profile = build_patient_needs_profile({"assistanceLevel": label, "memoryStatus": "No"}, "")
            ids = {item["parameter_id"] for item in profile["needs"]}
            self.assertIn("adl_support", ids, f"{label!r} should register an ADL-support need")


if __name__ == "__main__":
    unittest.main()
