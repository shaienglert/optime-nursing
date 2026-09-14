from app import services


def _row(facility_id, name, *, rating="UNKNOWN", review_count="UNKNOWN", grade=None, evidence_known=3):
    return {
        "canonical_facility_id": facility_id,
        "facility_name": name,
        "canonical_type": "INDEPENDENT_LIVING",
        "housing_modalities": ["INDEPENDENT_LIVING"],
        "care_partner_access": {"outside_care_allowed_verified": True, "status": "OUTSIDE_AGENCY_PATH_VERIFIED"},
        "regulatory_history": {"latest_known_grade": grade, "disciplinary_action": "N"},
        "client_intent_fit": {
            "hard_gate": "PASS", "must_pass": ["LAS_VEGAS", "ADL_SUPPORT_AVAILABLE"], "must_unknown": [], "must_fail": [],
            "nice_match": ["COMMUNITY_ENVIRONMENT_MATCH"], "nice_unknown": [], "nice_fit_scores": {"COMMUNITY_ENVIRONMENT_MATCH": 90.0},
            "public_reputation": {"rating": rating, "review_count": review_count},
            "relevant_evidence_known_count": evidence_known, "relevant_evidence_unknown_count": 0,
        },
        "agent_person_fit_evidence": [{"payload": {"outside_care_allowed_verified": True}}],
    }


def _base_result(agency_gate="UNKNOWN", rows=None):
    return {
        "results": rows if rows is not None else [_row("nv-il-1", "Independent Community")],
        "care_partner_options": [
            {
                "agency_id": "agency-1", "agency_name": "Care Partner", "primary_source_url": "https://example.test/agency",
                "minimum_billable_hours": "UNKNOWN" if agency_gate != "PASS" else 2, "hourly_rate": "UNKNOWN",
                "availability_status": "UNKNOWN" if agency_gate != "PASS" else "AVAILABLE",
                "care_agency_fit": {
                    "hard_gate": agency_gate,
                    "matched": ["ACTIVE_HCQC_LICENSE", "LAS_VEGAS_VALLEY_SERVICE", "BATHING_ASSISTANCE", "DRESSING_ASSISTANCE"],
                    "hard_fail_reasons": [], "material_unknowns": [] if agency_gate == "PASS" else ["MINIMUM_BILLABLE_HOURS", "AVAILABILITY_STATUS"],
                },
            }
        ],
        "decision_intelligence": {"ranking_order": ["CLIENT_INTENT", "MUST_GATE", "NICE_TO_HAVE", "GOVERNMENT_REGULATORY_DATA"]},
    }


def test_permission_without_verified_agency_downgrades_false_pass_to_pending():
    result = services._apply_combined_care_layer(_base_result("UNKNOWN"), {}, "Needs bathing and dressing for three months and prefers intimate independent living", 5)
    row = result["results"][0]
    assert row["combined_care_solution"]["delivery_model"] == "FACILITY_PLUS_EXTERNAL_AGENCY_PENDING_MATCH"
    assert row["client_intent_fit"]["hard_gate"] == "PENDING_VERIFICATION"
    assert "ADL_SUPPORT_AVAILABLE" in row["client_intent_fit"]["must_unknown"]
    assert "ADL_SUPPORT_AVAILABLE" not in row["client_intent_fit"]["must_pass"]
    assert result["decision_intelligence"]["must_gate"]["combined_care_delivery_enforced"] is True


def test_verified_agency_closes_combined_adl_must_without_changing_rank_contract():
    result = services._apply_combined_care_layer(_base_result("PASS"), {}, "Needs bathing and dressing for three months and prefers intimate independent living", 5)
    row = result["results"][0]
    assert row["combined_care_solution"]["delivery_model"] == "FACILITY_PLUS_EXTERNAL_AGENCY"
    assert row["client_intent_fit"]["hard_gate"] == "PASS"
    assert "ADL_SUPPORT_AVAILABLE" in row["client_intent_fit"]["must_pass"]
    assert result["decision_intelligence"]["ranking_order"] == ["CLIENT_INTENT", "MUST_GATE", "NICE_TO_HAVE", "GOVERNMENT_REGULATORY_DATA"]
    assert result["decision_intelligence"]["combined_care_solution"]["version"] == "combined-care-solution-v2"
    assert row["combined_care_solution"]["meal_component"]["meals_per_day"] == "UNKNOWN"


def test_rows_that_differ_on_rating_or_evidence_are_not_reported_as_tied():
    rows = [
        _row("nv-il-1", "Sunrise Community", rating=2.8, review_count=30, grade="A", evidence_known=68),
        _row("nv-il-2", "Valley Community", rating="UNKNOWN", review_count="UNKNOWN", grade=None, evidence_known=59),
    ]
    result = services._apply_combined_care_layer(_base_result(rows=rows), {}, "Prefers independent living", 5)
    ranked = result["results"]
    assert [r["facility_name"] for r in ranked] == ["Sunrise Community", "Valley Community"]
    for row in ranked:
        assert row["rank_tie_status"] == "UNIQUE_RANK"
        assert row["tied_with"] == []
    assert ranked[0]["ranking_basis"] == {
        "rating": 2.8, "review_count": 30, "latest_regulatory_grade": "A",
        "disciplinary_action_on_record": "N", "nice_preferences_matched": 1, "verified_evidence_items": 68,
    }
    assert ranked[1]["ranking_basis"]["rating"] == "UNKNOWN"
    assert ranked[1]["ranking_basis"]["verified_evidence_items"] == 59


def test_rows_with_identical_ranking_signals_are_reported_as_a_joint_rank():
    rows = [
        _row("nv-il-1", "Sunrise Community", evidence_known=59),
        _row("nv-il-2", "Valley Community", evidence_known=59),
    ]
    result = services._apply_combined_care_layer(_base_result(rows=rows), {}, "Prefers independent living", 5)
    ranked = result["results"]
    for row in ranked:
        assert row["rank_tie_status"] == "JOINT_RANK"
    assert ranked[0]["tied_with"] == [ranked[1]["facility_name"]]
    assert ranked[1]["tied_with"] == [ranked[0]["facility_name"]]
