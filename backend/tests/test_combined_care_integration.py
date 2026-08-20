from app import services


def _base_result(agency_gate="UNKNOWN"):
    return {
        "results": [
            {
                "canonical_facility_id": "nv-il-1",
                "facility_name": "Independent Community",
                "canonical_type": "INDEPENDENT_LIVING",
                "housing_modalities": ["INDEPENDENT_LIVING"],
                "care_partner_access": {
                    "outside_care_allowed_verified": True,
                    "status": "OUTSIDE_AGENCY_PATH_VERIFIED",
                },
                "client_intent_fit": {
                    "hard_gate": "PASS",
                    "must_pass": ["LAS_VEGAS", "ADL_SUPPORT_AVAILABLE"],
                    "must_unknown": [],
                    "must_fail": [],
                    "nice_match": ["COMMUNITY_ENVIRONMENT_MATCH"],
                    "nice_unknown": [],
                    "nice_fit_scores": {"COMMUNITY_ENVIRONMENT_MATCH": 90.0},
                    "public_reputation": {},
                    "relevant_evidence_known_count": 3,
                    "relevant_evidence_unknown_count": 0,
                },
                "agent_person_fit_evidence": [
                    {"payload": {"outside_care_allowed_verified": True}}
                ],
            }
        ],
        "care_partner_options": [
            {
                "agency_id": "agency-1",
                "agency_name": "Care Partner",
                "primary_source_url": "https://example.test/agency",
                "minimum_billable_hours": "UNKNOWN" if agency_gate != "PASS" else 2,
                "hourly_rate": "UNKNOWN",
                "availability_status": "UNKNOWN" if agency_gate != "PASS" else "AVAILABLE",
                "care_agency_fit": {
                    "hard_gate": agency_gate,
                    "matched": [
                        "ACTIVE_HCQC_LICENSE",
                        "LAS_VEGAS_VALLEY_SERVICE",
                        "BATHING_ASSISTANCE",
                        "DRESSING_ASSISTANCE",
                    ],
                    "hard_fail_reasons": [],
                    "material_unknowns": [] if agency_gate == "PASS" else ["MINIMUM_BILLABLE_HOURS", "AVAILABILITY_STATUS"],
                },
            }
        ],
        "decision_intelligence": {
            "ranking_order": [
                "CLIENT_INTENT",
                "MUST_GATE",
                "NICE_TO_HAVE",
                "GOVERNMENT_REGULATORY_DATA",
            ]
        },
    }


def test_permission_without_verified_agency_downgrades_false_pass_to_pending():
    result = services._apply_combined_care_layer(
        _base_result("UNKNOWN"),
        {},
        "Needs bathing and dressing for three months and prefers intimate independent living",
        5,
    )
    row = result["results"][0]
    assert row["combined_care_solution"]["delivery_model"] == "FACILITY_PLUS_EXTERNAL_AGENCY_PENDING_MATCH"
    assert row["client_intent_fit"]["hard_gate"] == "PENDING_VERIFICATION"
    assert "ADL_SUPPORT_AVAILABLE" in row["client_intent_fit"]["must_unknown"]
    assert "ADL_SUPPORT_AVAILABLE" not in row["client_intent_fit"]["must_pass"]


def test_verified_agency_closes_combined_adl_must():
    result = services._apply_combined_care_layer(
        _base_result("PASS"),
        {},
        "Needs bathing and dressing for three months and prefers intimate independent living",
        5,
    )
    row = result["results"][0]
    assert row["combined_care_solution"]["delivery_model"] == "FACILITY_PLUS_EXTERNAL_AGENCY"
    assert row["client_intent_fit"]["hard_gate"] == "PASS"
    assert "ADL_SUPPORT_AVAILABLE" in row["client_intent_fit"]["must_pass"]
    assert result["decision_intelligence"]["ranking_order"][2] == "COMBINED_CARE_MUST_COVERAGE"
