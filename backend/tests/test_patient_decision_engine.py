import unittest
from unittest.mock import patch

from app.services.patient_decision_engine import (
    _eligibility_from_needs,
    _evaluate_need,
    build_patient_comparison_context,
    build_patient_needs_profile,
    run_patient_decision_engine,
)


class PatientNeedsProfileTests(unittest.TestCase):
    def test_natural_language_stroke_profile_maps_expected_parameters(self) -> None:
        profile = build_patient_needs_profile(
            questionnaire_state={},
            natural_language_query=(
                "82-year-old patient in Miami with recent stroke, limited mobility, "
                "needs 24/7 nursing, PT, OT, speech therapy if appropriate, "
                "bathing and dressing help, medication management, transfer help, "
                "mentally alert and no dementia"
            ),
        )

        needs = {item["parameter_id"]: item for item in profile["needs"]}
        self.assertEqual(profile["location_city"], "MIAMI")
        self.assertIn("nursing_24_7", needs)
        self.assertIn("pt", needs)
        self.assertIn("ot", needs)
        self.assertIn("speech_therapy", needs)
        self.assertIn("adl_support", needs)
        self.assertIn("medication_support", needs)
        self.assertIn("transfer_assistance", needs)
        self.assertIn("post_stroke_neuro_evidence", needs)
        self.assertEqual(needs["memory_care"]["desired_value"], "NO")


class EligibilitySemanticsTests(unittest.TestCase):
    def test_unknown_required_need_is_not_automatically_ineligible(self) -> None:
        needs = [
            {
                "parameter_id": "pt",
                "requirement_level": "REQUIRED",
                "desired_value": "YES",
                "acceptable_values": ["YES"],
            }
        ]
        eligibility = _eligibility_from_needs(needs, row_by_param={})
        self.assertEqual(eligibility["eligibility_status"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(len(eligibility["unmet_verified_needs"]), 0)
        self.assertEqual(len(eligibility["unknown_critical_needs"]), 1)

    def test_verified_required_gap_is_ineligible(self) -> None:
        needs = [
            {
                "parameter_id": "pt",
                "requirement_level": "REQUIRED",
                "desired_value": "YES",
                "acceptable_values": ["YES"],
            }
        ]
        eligibility = _eligibility_from_needs(needs, row_by_param={"pt": {"raw_value": "NO"}})
        self.assertEqual(eligibility["eligibility_status"], "INELIGIBLE")
        self.assertEqual(len(eligibility["unmet_verified_needs"]), 1)

    def test_desired_no_is_evaluated_before_generic_yes_no_logic(self) -> None:
        need = {
            "parameter_id": "memory_care",
            "requirement_level": "PREFERENCE",
            "desired_value": "NO",
            "acceptable_values": ["NO", "UNKNOWN"],
        }

        yes_result = _evaluate_need(need, {"memory_care": {"raw_value": "YES"}})
        no_result = _evaluate_need(need, {"memory_care": {"raw_value": "NO"}})

        self.assertEqual(yes_result[0], "GAP")
        self.assertEqual(no_result[0], "MATCH")


class EngineRuntimeTests(unittest.TestCase):
    def _mock_profile(self):
        return {
            "need_tags": ["pt", "nursing"],
            "priority_parameter_ids": ["pt", "nursing_24_7"],
            "profile_key": "stroke",
            "location_city": None,
            "needs": [
                {
                    "parameter_id": "pt",
                    "requirement_level": "REQUIRED",
                    "desired_value": "YES",
                    "acceptable_values": ["YES"],
                },
                {
                    "parameter_id": "nursing_24_7",
                    "requirement_level": "HIGH",
                    "desired_value": "YES",
                    "acceptable_values": ["YES"],
                },
            ],
        }

    def _mock_table(self, canonical_id: str):
        rows_by_id = {
            "A": [
                {"parameter_id": "pt", "raw_value": "YES", "source": "CMS"},
                {"parameter_id": "nursing_24_7", "raw_value": "YES", "source": "CMS"},
                {"parameter_id": "current_availability", "raw_value": "UNKNOWN", "source": "Direct facility confirmation required"},
            ],
            "B": [
                {"parameter_id": "pt", "raw_value": "YES", "source": "CMS"},
                {"parameter_id": "nursing_24_7", "raw_value": "UNKNOWN", "source": "Not verified"},
                {"parameter_id": "current_availability", "raw_value": "UNKNOWN", "source": "Direct facility confirmation required"},
                {"parameter_id": "extra_unknown_only", "raw_value": "UNKNOWN", "source": "Not verified"},
            ],
        }
        return {
            "canonical_facility_id": canonical_id,
            "facility_name": f"Facility {canonical_id}",
            "city": "MIAMI",
            "state": "FL",
            "county": "MIAMI-DADE",
            "zip": "33101",
            "canonical_type": "SNF",
            "role_classification": "NURSING_HOME",
            "rows": rows_by_id[canonical_id],
        }

    @patch("app.services.patient_decision_engine.get_facility_parameter_table")
    @patch("app.services.patient_decision_engine.get_all_canonical_facility_ids")
    @patch("app.services.patient_decision_engine.get_canonical_facility_index")
    @patch("app.services.patient_decision_engine.get_personalized_parameter_order")
    @patch("app.services.patient_decision_engine.build_patient_needs_profile")
    def test_deterministic_matching_and_no_type_exclusion(
        self,
        mock_build_profile,
        mock_order,
        mock_index,
        mock_ids,
        mock_table,
    ) -> None:
        mock_build_profile.return_value = self._mock_profile()
        mock_order.return_value = {
            "ordered_parameters": [
                {"parameter_id": "pt"},
                {"parameter_id": "nursing_24_7"},
            ]
        }
        mock_ids.return_value = ["A", "B"]
        mock_index.return_value = {
            "A": {"source_identity_ids": {"cms_ccn": "100001"}, "canonical_type": "SNF"},
            "B": {"source_identity_ids": {"cms_ccn": "100002"}, "canonical_type": "ALF"},
        }
        mock_table.side_effect = lambda canonical_id, **_: self._mock_table(canonical_id)

        first = run_patient_decision_engine(questionnaire_state={}, natural_language_query="", limit=10)
        second = run_patient_decision_engine(questionnaire_state={}, natural_language_query="", limit=10)

        self.assertEqual(first, second)
        self.assertEqual(first["total_candidates_scored"], 2)
        self.assertEqual({item["canonical_facility_id"] for item in first["results"]}, {"A", "B"})
        self.assertEqual(first["results"][0]["canonical_facility_id"], "A")

    @patch("app.services.patient_decision_engine.get_facility_parameter_table")
    @patch("app.services.patient_decision_engine.get_all_canonical_facility_ids")
    @patch("app.services.patient_decision_engine.get_canonical_facility_index")
    @patch("app.services.patient_decision_engine.get_personalized_parameter_order")
    @patch("app.services.patient_decision_engine.build_patient_needs_profile")
    def test_no_completeness_bias_for_extra_unknown_non_need_rows(
        self,
        mock_build_profile,
        mock_order,
        mock_index,
        mock_ids,
        mock_table,
    ) -> None:
        mock_build_profile.return_value = self._mock_profile()
        mock_order.return_value = {"ordered_parameters": [{"parameter_id": "pt"}, {"parameter_id": "nursing_24_7"}]}
        mock_ids.return_value = ["A", "B"]
        mock_index.return_value = {"A": {"source_identity_ids": {}}, "B": {"source_identity_ids": {}}}
        mock_table.side_effect = lambda canonical_id, **_: self._mock_table(canonical_id)

        output = run_patient_decision_engine(questionnaire_state={}, natural_language_query="", limit=10)
        by_id = {item["canonical_facility_id"]: item for item in output["results"]}
        self.assertEqual(by_id["A"]["match_score"], by_id["B"]["match_score"])
        self.assertGreater(by_id["A"]["evidence_certainty"], by_id["B"]["evidence_certainty"])
        self.assertEqual(by_id["A"]["explanation"]["availability_note"], "Current availability must be confirmed directly with the facility.")
        self.assertEqual(by_id["B"]["explanation"]["availability_note"], "Current availability must be confirmed directly with the facility.")


class ComparisonContextTests(unittest.TestCase):
    @patch("app.services.patient_decision_engine.compare_facility_parameter_tables")
    def test_comparison_context_uses_identical_parameter_ids_and_preserves_scope(self, mock_compare) -> None:
        mock_compare.return_value = {
            "parameter_ids": ["pt", "nursing_24_7"],
            "facilities": [
                {
                    "canonical_facility_id": "A",
                    "facility_name": "Facility A",
                    "rows": [
                        {"parameter_id": "pt", "raw_value": "YES", "source": "CMS", "detail_scope": "SERVICE", "scope_name": "Therapy"},
                        {"parameter_id": "nursing_24_7", "raw_value": "UNKNOWN", "source": "Not verified", "detail_scope": "FACILITY", "scope_name": None},
                    ],
                },
                {
                    "canonical_facility_id": "B",
                    "facility_name": "Facility B",
                    "rows": [
                        {"parameter_id": "pt", "raw_value": "NO", "source": "CMS", "detail_scope": "SERVICE", "scope_name": "Therapy"},
                        {"parameter_id": "nursing_24_7", "raw_value": "YES", "source": "CMS", "detail_scope": "FACILITY", "scope_name": None},
                    ],
                },
            ],
        }

        patient_profile = {
            "need_tags": ["pt"],
            "priority_parameter_ids": ["pt"],
            "profile_key": "stroke",
            "needs": [
                {
                    "parameter_id": "pt",
                    "requirement_level": "REQUIRED",
                    "desired_value": "YES",
                    "acceptable_values": ["YES"],
                },
                {
                    "parameter_id": "nursing_24_7",
                    "requirement_level": "HIGH",
                    "desired_value": "YES",
                    "acceptable_values": ["YES"],
                },
            ],
        }

        context = build_patient_comparison_context(["A", "B"], patient_profile)
        self.assertEqual(context["comparison_parameter_ids"], ["pt", "nursing_24_7"])
        facility_a_rows = {row["parameter_id"]: row for row in context["facilities"][0]["need_rows"]}
        facility_b_rows = {row["parameter_id"]: row for row in context["facilities"][1]["need_rows"]}

        self.assertEqual(facility_a_rows["pt"]["status"], "MATCH")
        self.assertEqual(facility_b_rows["pt"]["status"], "VERIFIED_GAP")
        self.assertEqual(facility_a_rows["nursing_24_7"]["status"], "NOT_VERIFIED")
        self.assertEqual(facility_a_rows["pt"]["scope"], "SERVICE")


class GovernedTieBreakerTests(unittest.TestCase):
    def _profile(self) -> dict:
        return {
            "need_tags": ["pt", "nursing", "stroke"],
            "priority_parameter_ids": ["pt", "nursing_24_7", "post_stroke_neuro_evidence"],
            "profile_key": "stroke",
            "location_city": None,
            "needs": [
                {
                    "parameter_id": "pt",
                    "requirement_level": "REQUIRED",
                    "desired_value": "YES",
                    "acceptable_values": ["YES"],
                },
                {
                    "parameter_id": "nursing_24_7",
                    "requirement_level": "HIGH",
                    "desired_value": "YES",
                    "acceptable_values": ["YES"],
                },
                {
                    "parameter_id": "post_stroke_neuro_evidence",
                    "requirement_level": "HIGH",
                    "desired_value": "YES",
                    "acceptable_values": ["YES"],
                },
            ],
        }

    def _base_rows(self, scope: str = "PROGRAM") -> list:
        return [
            {"parameter_id": "pt", "raw_value": "YES", "source": "CMS", "detail_scope": "SERVICE"},
            {"parameter_id": "nursing_24_7", "raw_value": "YES", "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "post_stroke_neuro_evidence", "raw_value": "YES", "source": "CMS", "detail_scope": scope},
            {"parameter_id": "current_availability", "raw_value": "UNKNOWN", "source": "Direct facility confirmation required", "detail_scope": "UNIT"},
        ]

    def _quality_good_rows(self) -> list:
        return [
            {"parameter_id": "inspection_rating", "raw_value": 5, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "deficiency_count", "raw_value": 0, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "deficiency_severity", "raw_value": 0, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "complaint_related_findings", "raw_value": 0, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "fire_safety_deficiencies", "raw_value": 0, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "infection_control_findings", "raw_value": 0, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "quality_measures", "raw_value": 16, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "sanctions_final_orders", "raw_value": "NO", "source": "AHCA", "detail_scope": "FACILITY"},
        ]

    def _quality_severe_rows(self) -> list:
        return [
            {"parameter_id": "inspection_rating", "raw_value": 2, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "deficiency_count", "raw_value": 12, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "deficiency_severity", "raw_value": 6, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "complaint_related_findings", "raw_value": 6, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "infection_control_findings", "raw_value": 4, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "penalties_fines", "raw_value": 50000, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "sanctions_final_orders", "raw_value": "YES", "source": "AHCA", "detail_scope": "FACILITY"},
            {"parameter_id": "quality_measures", "raw_value": 17, "source": "CMS", "detail_scope": "FACILITY"},
        ]

    def _staffing_strong_rows(self) -> list:
        return [
            {"parameter_id": "rn_hours_per_resident_day", "raw_value": 1.6, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "total_nurse_hours_per_resident_day", "raw_value": 4.2, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "staffing_turnover", "raw_value": 20, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "therapy_staffing", "raw_value": "YES", "source": "CMS", "detail_scope": "SERVICE"},
        ]

    def _staffing_weaker_rows(self) -> list:
        return [
            {"parameter_id": "rn_hours_per_resident_day", "raw_value": 0.6, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "total_nurse_hours_per_resident_day", "raw_value": 2.0, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "staffing_turnover", "raw_value": 45, "source": "CMS", "detail_scope": "FACILITY"},
            {"parameter_id": "therapy_staffing", "raw_value": "YES", "source": "CMS", "detail_scope": "SERVICE"},
        ]

    def _table(self, canonical_id: str, rows: list) -> dict:
        return {
            "canonical_facility_id": canonical_id,
            "facility_name": f"Facility {canonical_id}",
            "city": "MIAMI",
            "state": "FL",
            "county": "MIAMI-DADE",
            "zip": "33101",
            "canonical_type": "SNF",
            "role_classification": "NURSING_HOME",
            "rows": rows,
        }

    def _run_with_tables(self, ids: list[str], tables: dict[str, dict]) -> dict:
        with patch("app.services.patient_decision_engine.build_patient_needs_profile") as mock_profile, patch(
            "app.services.patient_decision_engine.get_personalized_parameter_order"
        ) as mock_order, patch("app.services.patient_decision_engine.get_all_canonical_facility_ids") as mock_ids, patch(
            "app.services.patient_decision_engine.get_canonical_facility_index"
        ) as mock_index, patch("app.services.patient_decision_engine.get_facility_parameter_table") as mock_table:
            mock_profile.return_value = self._profile()
            mock_order.return_value = {
                "ordered_parameters": [
                    {"parameter_id": "pt"},
                    {"parameter_id": "nursing_24_7"},
                    {"parameter_id": "post_stroke_neuro_evidence"},
                ]
            }
            mock_ids.return_value = ids
            mock_index.return_value = {item: {"source_identity_ids": {"cms_ccn": f"1000{index}"}} for index, item in enumerate(ids)}
            mock_table.side_effect = lambda canonical_id, **_: tables[canonical_id]
            return run_patient_decision_engine(questionnaire_state={}, natural_language_query="", limit=20)

    def test_controlled_five_facility_tie_break_matrix(self) -> None:
        tables = {
            "A": self._table("A", self._base_rows(scope="PROGRAM") + self._quality_good_rows() + self._staffing_strong_rows()),
            "B": self._table("B", self._base_rows(scope="PROGRAM") + self._quality_severe_rows() + self._staffing_strong_rows()),
            "C": self._table("C", self._base_rows(scope="PROGRAM") + self._quality_good_rows() + self._staffing_weaker_rows()),
            "D": self._table("D", self._base_rows(scope="SERVICE") + self._quality_good_rows() + self._staffing_weaker_rows()),
            "E": self._table(
                "E",
                self._base_rows(scope="PROGRAM")
                + self._quality_good_rows()
                + self._staffing_strong_rows()
                + [{"parameter_id": "unrelated_unknown_only", "raw_value": "UNKNOWN", "source": "Not verified", "detail_scope": "FACILITY"}],
            ),
        }

        output = self._run_with_tables(["A", "B", "C", "D", "E"], tables)
        by_id = {item["canonical_facility_id"]: item for item in output["results"]}
        ordered_ids = [item["canonical_facility_id"] for item in output["results"]]

        self.assertEqual(by_id["A"]["rank_tie_status"], "JOINT_RANK")
        self.assertEqual(by_id["E"]["rank_tie_status"], "JOINT_RANK")
        self.assertIn("E", by_id["A"]["tied_with"])
        self.assertIn("A", by_id["E"]["tied_with"])

        self.assertLess(ordered_ids.index("A"), ordered_ids.index("B"))
        self.assertLess(ordered_ids.index("A"), ordered_ids.index("C"))
        self.assertLess(ordered_ids.index("C"), ordered_ids.index("D"))
        self.assertLess(ordered_ids.index("D"), ordered_ids.index("B"))

        decisions = output.get("tie_break_decisions") or []
        pair_keys = {(item["higher_canonical_facility_id"], item["lower_canonical_facility_id"]): item for item in decisions}
        self.assertIn(("A", "E"), pair_keys)
        self.assertEqual(pair_keys[("A", "E")]["decision_dimension"], "true_tie")

        self.assertIn(("C", "D"), pair_keys)
        self.assertEqual(pair_keys[("C", "D")]["decision_dimension"], "capability_depth")

        self.assertIn(("D", "B"), pair_keys)
        self.assertEqual(pair_keys[("D", "B")]["decision_dimension"], "quality_safety")

        self.assertEqual(by_id["A"]["match_score"], by_id["E"]["match_score"])
        self.assertEqual(by_id["A"]["quality_safety_score"], by_id["E"]["quality_safety_score"])
        self.assertEqual(by_id["A"]["staffing_score"], by_id["E"]["staffing_score"])
        self.assertEqual(by_id["A"]["explanation"]["availability_note"], "Current availability must be confirmed directly with the facility.")
        self.assertEqual(by_id["B"]["explanation"]["availability_note"], "Current availability must be confirmed directly with the facility.")

    def test_more_data_alone_does_not_create_ranking_advantage(self) -> None:
        base = self._table("A", self._base_rows(scope="PROGRAM") + self._quality_good_rows() + self._staffing_strong_rows())
        richer = self._table(
            "B",
            self._base_rows(scope="PROGRAM")
            + self._quality_good_rows()
            + self._staffing_strong_rows()
            + [
                {"parameter_id": "extra_unknown_one", "raw_value": "UNKNOWN", "source": "Not verified", "detail_scope": "FACILITY"},
                {"parameter_id": "extra_unknown_two", "raw_value": "UNKNOWN", "source": "Not verified", "detail_scope": "FACILITY"},
            ],
        )
        output = self._run_with_tables(["A", "B"], {"A": base, "B": richer})
        by_id = {item["canonical_facility_id"]: item for item in output["results"]}
        self.assertEqual(by_id["A"]["rank_tie_status"], "JOINT_RANK")
        self.assertEqual(by_id["B"]["rank_tie_status"], "JOINT_RANK")

    def test_unknown_alone_is_neutral(self) -> None:
        table_a = self._table("A", self._base_rows(scope="PROGRAM") + self._quality_good_rows())
        table_b = self._table(
            "B",
            self._base_rows(scope="PROGRAM") + self._quality_good_rows() + [{"parameter_id": "staffing_turnover", "raw_value": "UNKNOWN", "source": "Not verified", "detail_scope": "FACILITY"}],
        )
        output = self._run_with_tables(["A", "B"], {"A": table_a, "B": table_b})
        by_id = {item["canonical_facility_id"]: item for item in output["results"]}
        self.assertEqual(by_id["A"]["rank_tie_status"], "JOINT_RANK")
        self.assertEqual(by_id["B"]["rank_tie_status"], "JOINT_RANK")

    def test_availability_unknown_is_neutral(self) -> None:
        table_a = self._table("A", self._base_rows(scope="PROGRAM") + self._quality_good_rows())
        table_b = self._table("B", [row for row in self._base_rows(scope="PROGRAM") if row["parameter_id"] != "current_availability"] + self._quality_good_rows())
        output = self._run_with_tables(["A", "B"], {"A": table_a, "B": table_b})
        by_id = {item["canonical_facility_id"]: item for item in output["results"]}
        self.assertEqual(by_id["A"]["rank_tie_status"], "JOINT_RANK")
        self.assertEqual(by_id["B"]["rank_tie_status"], "JOINT_RANK")
        self.assertEqual(by_id["A"]["explanation"]["availability_note"], "Current availability must be confirmed directly with the facility.")
        self.assertEqual(by_id["B"]["explanation"]["availability_note"], "Current availability must be confirmed directly with the facility.")


if __name__ == "__main__":
    unittest.main()