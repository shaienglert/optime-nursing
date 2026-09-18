from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.semantic_intent_ai import interpret_client_intent_with_ai
from app.services.semantic_facility_requirements import apply_semantic_facility_requirements, extract_semantic_facility_requirements


class SemanticFacilityRequirementTests(unittest.TestCase):
    def test_facility_research_does_not_deadlock_client_readiness(self) -> None:
        ai = {
            "facts": ["independent resident"],
            "preferences": [],
            "constraints": ["100 meter route"],
            "concerns": [],
            "implications": [],
            "statements": [
                {
                    "raw_text": "services must be within 100 meters",
                    "meaning": "actual unit route distance is a hard requirement",
                    "importance": "MUST",
                    "knowledge_state": "KNOWN",
                    "status": "RESEARCH_REQUIRED",
                    "mapped_parameters": ["unit_to_dining_distance", "internal_route_distance"],
                    "clarification_question": None,
                    "research_task": "verify actual route distance for each available unit",
                }
            ],
            "next_question": None,
            "research_requests": ["verify route distance"],
            "decision_readiness": "NEEDS_RESEARCH",
        }
        learning = {"advisor": "OPTIME_NURSING_LEARNING_CENTER", "consulted": True, "agent_count": 1, "available_agent_count": 1, "agents": [], "policy": {}}
        with patch("app.services.semantic_intent_ai.build_learning_center_advice", return_value=learning):
            result = interpret_client_intent_with_ai(user_text="100 meter route", questionnaire_state={}, transport=lambda _: ai)
        self.assertEqual("READY", result["decision_readiness"])
        self.assertEqual("CLIENT_INTENT_COMPLETE_FACILITY_RESEARCH_DEFERRED", result["readiness_normalization"]["reason"])
        self.assertEqual("RESEARCH_REQUIRED", result["statements"][0]["status"])

    def test_semantic_mobility_and_dietary_musts_survive_to_facility_gate(self) -> None:
        payload = {
            "decision_intelligence": {
                "human_intelligence": {
                    "semantic_ai": {
                        "result": {
                            "statements": [
                                {
                                    "raw_text": "within 100 meters",
                                    "meaning": "short internal route required",
                                    "importance": "MUST",
                                    "knowledge_state": "KNOWN",
                                    "status": "RESEARCH_REQUIRED",
                                    "mapped_parameters": ["unit_to_dining_distance", "layout_fit"],
                                    "research_task": "verify route",
                                },
                                {
                                    "raw_text": "safe gluten-free with cross-contact controls",
                                    "meaning": "medical dietary safety required",
                                    "importance": "MUST",
                                    "knowledge_state": "KNOWN",
                                    "status": "RESEARCH_REQUIRED",
                                    "mapped_parameters": ["gluten_free_meals_required", "cross_contact_controls_required"],
                                    "research_task": "verify cross-contact controls",
                                },
                                {
                                    "raw_text": "all daily meals",
                                    "meaning": "all meals required",
                                    "importance": "MUST",
                                    "knowledge_state": "KNOWN",
                                    "status": "RESEARCH_REQUIRED",
                                    "mapped_parameters": ["all_daily_meals_required"],
                                    "research_task": "verify meal plan",
                                },
                            ]
                        }
                    }
                }
            }
        }
        rows = extract_semantic_facility_requirements(payload)
        self.assertEqual({"SEMANTIC_MOBILITY_LAYOUT", "SEMANTIC_DIETARY_SAFETY", "SEMANTIC_ALL_DAILY_MEALS"}, {row["key"] for row in rows})

    def test_ambiguous_client_owned_value_is_not_promoted_to_facility_must(self) -> None:
        payload = {
            "decision_intelligence": {
                "human_intelligence": {
                    "semantic_ai": {
                        "result": {
                            "statements": [{
                                "raw_text": "budget 8000",
                                "meaning": "period unknown",
                                "importance": "MUST",
                                "knowledge_state": "AMBIGUOUS",
                                "status": "RESEARCH_REQUIRED",
                                "mapped_parameters": ["budget_period"],
                                "research_task": "verify budget period",
                            }]
                        }
                    }
                }
            }
        }
        self.assertEqual([], extract_semantic_facility_requirements(payload))

    def test_used_future_care_must_is_still_verified_per_facility(self) -> None:
        result = {
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {
                "statements": [{
                    "raw_text": "a clear future-care path",
                    "meaning": "continuum of care is required",
                    "importance": "MUST",
                    "knowledge_state": "KNOWN",
                    "status": "USED",
                    "mapped_parameters": ["futureCareProfile.continuumOfCarePreference"],
                    "research_task": "verify the future-care pathway",
                }]
            }}}},
            "results": [
                {
                    "canonical_facility_id": "CONTINUUM",
                    "facility_name": "Continuum Community",
                    "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                    "provider_housing_evidence": {"evidence": {"continuum_of_care_verified": True}},
                },
                {
                    "canonical_facility_id": "UNKNOWN",
                    "facility_name": "Unknown Community",
                    "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                    "agent_person_fit_evidence": [],
                },
            ],
        }

        requirements = extract_semantic_facility_requirements(result)
        self.assertEqual(["SEMANTIC_FUTURE_CARE_PATH"], [item["key"] for item in requirements])
        out = apply_semantic_facility_requirements(result, research_limit=0)
        self.assertIn("SEMANTIC_FUTURE_CARE_PATH", out["results"][0]["client_intent_fit"]["must_pass"])
        self.assertEqual("PASS", out["results"][0]["client_intent_fit"]["hard_gate"])
        self.assertIn("SEMANTIC_FUTURE_CARE_PATH", out["results"][1]["client_intent_fit"]["must_unknown"])
        self.assertEqual("PENDING_VERIFICATION", out["results"][1]["client_intent_fit"]["hard_gate"])

    def test_same_apartment_transition_alone_does_not_prove_future_care_path(self) -> None:
        result = {
            "decision_intelligence": {
                "human_intelligence": {
                    "semantic_ai": {
                        "result": {
                            "statements": [{
                                "raw_text": "a clear future-care path",
                                "meaning": "continuum of care is required",
                                "importance": "MUST",
                                "knowledge_state": "KNOWN",
                                "status": "USED",
                                "mapped_parameters": ["futureCareProfile.continuumOfCarePreference"],
                            }]
                        }
                    }
                }
            },
            "results": [{
                "canonical_facility_id": "INDEPENDENT_ONLY",
                "facility_name": "Independent-only Community",
                "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                "agent_person_fit_evidence": [{
                    "payload": {
                        "same_apartment_transition_verified": True,
                        "continuum_of_care_verified": False,
                    }
                }],
            }],
        }

        out = apply_semantic_facility_requirements(result, research_limit=0)
        fit = out["results"][0]["client_intent_fit"]
        self.assertNotIn("SEMANTIC_FUTURE_CARE_PATH", fit["must_pass"])
        self.assertIn("SEMANTIC_FUTURE_CARE_PATH", fit["must_unknown"])
        self.assertEqual("PENDING_VERIFICATION", fit["hard_gate"])

    def test_future_care_mapping_alone_does_not_create_continuum_must(self) -> None:
        result = {
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {
                "statements": [{
                    "raw_text": "A family financial review is pending",
                    "meaning": "Payment source may change pending a family financial review.",
                    "importance": "MUST",
                    "knowledge_state": "KNOWN",
                    "status": "USED",
                    "mapped_parameters": ["futureCarePreference"],
                }]
            }}}},
            "results": [],
        }

        self.assertEqual([], extract_semantic_facility_requirements(result))

    def test_unrelated_historical_agent_record_cannot_prove_future_care_path(self) -> None:
        result = {
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {
                "statements": [{
                    "raw_text": "future care path",
                    "meaning": "continuum required",
                    "importance": "MUST",
                    "knowledge_state": "KNOWN",
                    "status": "USED",
                    "mapped_parameters": ["continuumOfCarePreference"],
                }]
            }}}},
            "results": [{
                "canonical_facility_id": "STALE",
                "facility_name": "Independent Housing",
                "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                "agent_person_fit_evidence": [{
                    "source": "OFFICIAL_PROVIDER_WEBSITE",
                    "payload": {
                        "dimension": "social_engagement",
                        "official_identity_verified": True,
                        "continuum_of_care_verified": True,
                    },
                }],
            }],
        }

        out = apply_semantic_facility_requirements(result, research_limit=0)
        fit = out["results"][0]["client_intent_fit"]
        self.assertIn("SEMANTIC_FUTURE_CARE_PATH", fit["must_unknown"])
        self.assertEqual("PENDING_VERIFICATION", fit["hard_gate"])

    def test_agent_interpretation_alone_cannot_settle_future_care_must(self) -> None:
        result = {
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {
                "statements": [{
                    "raw_text": "future care path",
                    "meaning": "continuum required",
                    "importance": "MUST",
                    "knowledge_state": "KNOWN",
                    "status": "USED",
                    "mapped_parameters": ["continuumOfCarePreference"],
                }]
            }}}},
            "results": [{
                "canonical_facility_id": "AGENT-ONLY",
                "facility_name": "Independent-only Community",
                "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                "agent_person_fit_evidence": [{
                    "source": "OFFICIAL_PROVIDER_WEBSITE",
                    "payload": {
                        "dimension": "recovery_transition",
                        "official_identity_verified": True,
                        "continuum_of_care_verified": True,
                    },
                }],
            }],
        }

        out = apply_semantic_facility_requirements(result, research_limit=0)
        fit = out["results"][0]["client_intent_fit"]
        self.assertIn("SEMANTIC_FUTURE_CARE_PATH", fit["must_unknown"])
        self.assertEqual("PENDING_VERIFICATION", fit["hard_gate"])

    def test_recalculation_removes_stale_semantic_pass(self) -> None:
        result = {
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {
                "statements": [{
                    "raw_text": "future care path",
                    "meaning": "continuum required",
                    "importance": "MUST",
                    "knowledge_state": "KNOWN",
                    "status": "USED",
                    "mapped_parameters": ["continuumOfCarePreference"],
                }]
            }}}},
            "results": [{
                "canonical_facility_id": "STALE-PASS",
                "facility_name": "Independent-only Community",
                "client_intent_fit": {
                    "must_pass": ["LICENSE_CURRENTLY_VALID", "SEMANTIC_FUTURE_CARE_PATH"],
                    "must_unknown": [],
                    "must_fail": [],
                    "hard_gate": "PASS",
                },
                "agent_person_fit_evidence": [],
            }],
        }

        out = apply_semantic_facility_requirements(result, research_limit=0)
        fit = out["results"][0]["client_intent_fit"]
        self.assertNotIn("SEMANTIC_FUTURE_CARE_PATH", fit["must_pass"])
        self.assertIn("SEMANTIC_FUTURE_CARE_PATH", fit["must_unknown"])
        self.assertEqual("PENDING_VERIFICATION", fit["hard_gate"])

    def test_used_dialysis_and_wound_care_musts_survive_to_the_gate(self) -> None:
        # Reproduces the live finding: Semantic AI correctly tags dialysis coordination
        # and wound care as MUST/KNOWN, but marks them USED (client-side fact is
        # understood) rather than RESEARCH_REQUIRED -- before this fix that meant they
        # were silently dropped and every facility, including plain independent living,
        # passed the MUST gate with zero visibility into the unverified clinical need.
        result = {
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {
                "statements": [
                    {
                        "raw_text": "needs dialysis three times a week",
                        "meaning": "resident requires dialysis coordination",
                        "importance": "MUST",
                        "knowledge_state": "KNOWN",
                        "status": "USED",
                        "mapped_parameters": ["dialysis_frequency", "dialysis_coordination"],
                        "research_task": "verify dialysis coordination and transport support",
                    },
                    {
                        "raw_text": "has a chronic wound that needs regular nursing care",
                        "meaning": "resident requires wound care and nursing support",
                        "importance": "MUST",
                        "knowledge_state": "KNOWN",
                        "status": "USED",
                        "mapped_parameters": ["wound_care", "nursing_support"],
                        "research_task": "verify wound care and nursing capability",
                    },
                ]
            }}}},
            "results": [
                {
                    "canonical_facility_id": "INDEPENDENT-LIVING",
                    "facility_name": "Sunrise Independent Living",
                    "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                    "agent_person_fit_evidence": [],
                },
                {
                    "canonical_facility_id": "VERIFIED-DIALYSIS",
                    "facility_name": "Verified Clinical Community",
                    "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                    "agent_person_fit_evidence": [{"payload": {"clinical_acuity_verified": True}}],
                },
            ],
        }

        requirements = extract_semantic_facility_requirements(result)
        self.assertEqual(["SEMANTIC_CLINICAL_ACUITY"], [item["key"] for item in requirements])

        out = apply_semantic_facility_requirements(result, research_limit=0)
        independent = out["results"][0]["client_intent_fit"]
        self.assertIn("SEMANTIC_CLINICAL_ACUITY", independent["must_unknown"])
        self.assertEqual("PENDING_VERIFICATION", independent["hard_gate"])

        verified = out["results"][1]["client_intent_fit"]
        self.assertIn("SEMANTIC_CLINICAL_ACUITY", verified["must_pass"])
        self.assertEqual("PASS", verified["hard_gate"])

    def test_used_kosher_and_hebrew_musts_survive_to_the_gate(self) -> None:
        result = {
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {
                "statements": [
                    {
                        "raw_text": "speaks Hebrew as her first language",
                        "meaning": "resident requires Hebrew-language communication",
                        "importance": "MUST",
                        "knowledge_state": "KNOWN",
                        "status": "USED",
                        "mapped_parameters": ["primary_language"],
                    },
                    {
                        "raw_text": "and keeps kosher",
                        "meaning": "resident requires kosher meals",
                        "importance": "MUST",
                        "knowledge_state": "KNOWN",
                        "status": "USED",
                        "mapped_parameters": ["dietary_restriction"],
                    },
                ]
            }}}},
            "results": [{
                "canonical_facility_id": "NO-EVIDENCE",
                "facility_name": "Generic Community",
                "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                "agent_person_fit_evidence": [],
            }],
        }

        requirements = extract_semantic_facility_requirements(result)
        self.assertEqual({"SEMANTIC_LANGUAGE_SUPPORT", "SEMANTIC_KOSHER_DIET"}, {item["key"] for item in requirements})

        out = apply_semantic_facility_requirements(result, research_limit=0)
        fit = out["results"][0]["client_intent_fit"]
        self.assertIn("SEMANTIC_LANGUAGE_SUPPORT", fit["must_unknown"])
        self.assertIn("SEMANTIC_KOSHER_DIET", fit["must_unknown"])
        self.assertEqual("PENDING_VERIFICATION", fit["hard_gate"])

    def test_used_budget_must_survives_to_the_gate(self) -> None:
        # Reproduces the live finding for budget_constrained_high_adl: Semantic AI
        # tags the stated monthly budget as MUST/KNOWN/USED. Before this fix, budget
        # only ever became a PREFERENCE-level "prefer transparent pricing" need in
        # patient_decision_engine.py's _map_financial(), so a facility with no pricing
        # evidence at all still showed a full PASS/FINAL recommendation to a family
        # who explicitly said their budget was tight.
        result = {
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {
                "statements": [
                    {
                        "raw_text": "Our budget is tight",
                        "meaning": "affordability is a hard constraint",
                        "importance": "MUST",
                        "knowledge_state": "KNOWN",
                        "status": "USED",
                        "mapped_parameters": ["budget_tightness"],
                    },
                    {
                        "raw_text": "around $3,000 a month",
                        "meaning": "stated monthly budget is $3,000",
                        "importance": "MUST",
                        "knowledge_state": "KNOWN",
                        "status": "USED",
                        "mapped_parameters": ["monthly_affordability"],
                    },
                ]
            }}}},
            "results": [{
                "canonical_facility_id": "NO-PRICE-EVIDENCE",
                "facility_name": "Generic Community",
                "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                "agent_person_fit_evidence": [],
            }],
        }

        requirements = extract_semantic_facility_requirements(result)
        self.assertEqual(["SEMANTIC_BUDGET_VERIFICATION"], [item["key"] for item in requirements])

        out = apply_semantic_facility_requirements(result, research_limit=0)
        fit = out["results"][0]["client_intent_fit"]
        self.assertIn("SEMANTIC_BUDGET_VERIFICATION", fit["must_unknown"])
        self.assertEqual("PENDING_VERIFICATION", fit["hard_gate"])

    def test_budget_verification_passes_when_facility_price_is_at_or_under_stated_budget(self) -> None:
        # published_rates_verified alone only proves a facility discloses its rates --
        # not that the rate fits the client. A facility with a known starting price at
        # or under what the client stated should reach a real PASS, not stay pending
        # forever just because no agent research record happens to exist.
        result = {
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {
                "statements": [{
                    "raw_text": "around $3,000 a month",
                    "meaning": "stated monthly budget is $3,000",
                    "importance": "MUST",
                    "knowledge_state": "KNOWN",
                    "status": "USED",
                    "mapped_parameters": ["monthly_affordability"],
                }]
            }}}},
            "results": [{
                "canonical_facility_id": "WITHIN-BUDGET",
                "facility_name": "Affordable Community",
                "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                "agent_person_fit_evidence": [],
                "starting_monthly_price": 2800,
            }],
        }

        out = apply_semantic_facility_requirements(result, research_limit=0, questionnaire_state={"budget": 3000})
        fit = out["results"][0]["client_intent_fit"]
        self.assertIn("SEMANTIC_BUDGET_VERIFICATION", fit["must_pass"])
        self.assertEqual("PASS", fit["hard_gate"])

    def test_budget_verification_stays_pending_when_confirmed_price_exceeds_budget(self) -> None:
        # A confirmed price that is clearly over budget must never be treated as
        # satisfying the client's stated budget MUST -- that would turn a genuine
        # mismatch into a false "final" recommendation, which is exactly the failure
        # this MUST gate exists to prevent.
        result = {
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {
                "statements": [{
                    "raw_text": "around $3,000 a month",
                    "meaning": "stated monthly budget is $3,000",
                    "importance": "MUST",
                    "knowledge_state": "KNOWN",
                    "status": "USED",
                    "mapped_parameters": ["monthly_affordability"],
                }]
            }}}},
            "results": [{
                "canonical_facility_id": "OVER-BUDGET",
                "facility_name": "Premium Memory Care",
                "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                "agent_person_fit_evidence": [],
                "starting_monthly_price": 9500,
            }],
        }

        out = apply_semantic_facility_requirements(result, research_limit=0, questionnaire_state={"budget": 3000})
        fit = out["results"][0]["client_intent_fit"]
        self.assertNotIn("SEMANTIC_BUDGET_VERIFICATION", fit["must_pass"])
        self.assertIn("SEMANTIC_BUDGET_VERIFICATION", fit["must_unknown"])
        self.assertEqual("PENDING_VERIFICATION", fit["hard_gate"])

    def test_context_level_medicaid_mention_is_not_promoted(self) -> None:
        # Live behavior for the same persona: Semantic AI classified Medicaid
        # eligibility as CONTEXT, not MUST ("may qualify" is not a firm requirement).
        # The importance filter at the top of extract_semantic_facility_requirements
        # already excludes non-MUST statements -- this asserts the new Medicaid bucket
        # doesn't change that for a statement the AI itself did not mark MUST.
        result = {
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {
                "statements": [{
                    "raw_text": "She may qualify for Medicaid",
                    "meaning": "possible future Medicaid eligibility",
                    "importance": "CONTEXT",
                    "knowledge_state": "KNOWN",
                    "status": "USED",
                    "mapped_parameters": ["medicaid_eligibility"],
                }]
            }}}},
            "results": [],
        }
        self.assertEqual([], extract_semantic_facility_requirements(result))

    def test_used_explicit_medicaid_requirement_survives_to_the_gate(self) -> None:
        result = {
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"result": {
                "statements": [{
                    "raw_text": "the facility must accept Medicaid",
                    "meaning": "Medicaid acceptance is a hard requirement",
                    "importance": "MUST",
                    "knowledge_state": "KNOWN",
                    "status": "USED",
                    "mapped_parameters": ["medicaid_requirement"],
                }]
            }}}},
            "results": [{
                "canonical_facility_id": "NO-MEDICAID-EVIDENCE",
                "facility_name": "Generic Community",
                "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                "agent_person_fit_evidence": [],
            }],
        }
        requirements = extract_semantic_facility_requirements(result)
        self.assertEqual(["SEMANTIC_MEDICAID_PATHWAY"], [item["key"] for item in requirements])
        out = apply_semantic_facility_requirements(result, research_limit=0)
        fit = out["results"][0]["client_intent_fit"]
        self.assertIn("SEMANTIC_MEDICAID_PATHWAY", fit["must_unknown"])
        self.assertEqual("PENDING_VERIFICATION", fit["hard_gate"])

    def test_structured_questionnaire_budget_survives_even_without_ai_statements(self) -> None:
        # Reproduces the live finding for recently_widowed_isolation_risk: the client's
        # $5,000 budget was only ever in questionnaire_state.budget, with no matching
        # free-text mention -- so it never reached Semantic AI's statements at all, and
        # stayed invisible even when the AI call failed outright for an unrelated
        # reason (SEMANTIC_AI_REPAIR_CLARIFICATION_WITHOUT_QUESTION in the live capture,
        # meaning zero statements existed). This must not depend on the AI succeeding.
        result = {
            "decision_intelligence": {"human_intelligence": {"semantic_ai": {"status": "FAILED", "error": "SOME_UNRELATED_FAILURE"}}},
            "results": [{
                "canonical_facility_id": "NO-PRICE-EVIDENCE",
                "facility_name": "Generic Community",
                "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                "agent_person_fit_evidence": [],
            }],
        }
        requirements = extract_semantic_facility_requirements(result, {"budget": 5000})
        self.assertEqual(["SEMANTIC_BUDGET_VERIFICATION"], [item["key"] for item in requirements])

        out = apply_semantic_facility_requirements(result, research_limit=0, questionnaire_state={"budget": 5000})
        fit = out["results"][0]["client_intent_fit"]
        self.assertIn("SEMANTIC_BUDGET_VERIFICATION", fit["must_unknown"])
        self.assertEqual("PENDING_VERIFICATION", fit["hard_gate"])

    def test_no_questionnaire_budget_and_no_ai_statement_creates_no_requirement(self) -> None:
        result = {"decision_intelligence": {"human_intelligence": {"semantic_ai": {"status": "FAILED"}}}}
        self.assertEqual([], extract_semantic_facility_requirements(result, {"budget": None}))
        self.assertEqual([], extract_semantic_facility_requirements(result, {}))
        self.assertEqual([], extract_semantic_facility_requirements(result, None))

    def test_stamped_false_agent_evidence_never_hard_fails_a_semantic_must(self) -> None:
        # decision_research_worker.py stamps social_engagement_verified=False by default
        # on every research record, regardless of which dimension was actually
        # requested -- so a facility with unrelated agent research (e.g. a
        # couple_coresidence check) must not be excluded from a client's social-
        # engagement MUST just because that unrelated record carries the default False.
        result = {
            "decision_intelligence": {
                "human_intelligence": {
                    "semantic_ai": {
                        "result": {
                            "statements": [{
                                "raw_text": "organized activities and card games so she never feels isolated",
                                "meaning": "material social programming required",
                                "importance": "MUST",
                                "knowledge_state": "KNOWN",
                                "status": "RESEARCH_REQUIRED",
                                "mapped_parameters": ["organized_activities", "isolation"],
                                "research_task": "verify organized social programming",
                            }]
                        }
                    }
                }
            },
            "results": [
                {
                    "canonical_facility_id": "TEST-1",
                    "facility_name": "Test Facility",
                    "client_intent_fit": {"must_pass": [], "must_unknown": [], "must_fail": []},
                    "agent_person_fit_evidence": [
                        {"payload": {"dimension": "couple_coresidence", "social_engagement_verified": False, "couple_coresidence_verified": True}}
                    ],
                }
            ],
        }
        out = apply_semantic_facility_requirements(result)
        fit = out["results"][0]["client_intent_fit"]
        self.assertNotIn("SEMANTIC_SOCIAL_DELIVERY", fit["must_fail"])
        self.assertNotEqual("FAIL", fit["hard_gate"])
        self.assertIn("SEMANTIC_SOCIAL_DELIVERY", fit["must_unknown"])


if __name__ == "__main__":
    unittest.main()
