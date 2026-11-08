from __future__ import annotations

import unittest

from app.services.client_statement_accounting import account_user_input, reconcile_semantic_statement_coverage
from app.services.human_intelligence_runtime_verified import build_human_intelligence_context


class ClientStatementAccountingTests(unittest.TestCase):
    def test_known_and_unknown_preferences_are_all_accounted(self) -> None:
        query = "We are a married independent couple, food is very important, we love activities, beautiful gardens, outings, and a pottery studio with evening glazing sessions."
        context = build_human_intelligence_context({}, query)
        accounting = context["user_statement_accounting"]
        self.assertEqual(100.0, accounting["coverage_percent"])
        self.assertEqual(0, accounting["dropped_count"])
        self.assertTrue(all(row["status"] in {"USED", "ASKED", "RESEARCH_REQUIRED", "NOT_DECISION_RELEVANT"} for row in accounting["statements"]))
        self.assertTrue(any("pottery studio" in row["statement"].lower() for row in accounting["unresolved_parameters"]))
        # No-drop identifies the unresolved fact. When semantic wording is
        # unavailable, deterministic policy preserves the highest-priority blocker.
        self.assertEqual(1, len(context["adaptive_questions"]))
        self.assertEqual(
            context["readiness_guardian"]["client_owned_blockers"][0]["fact_key"],
            context["adaptive_questions"][0]["target_fact_key"],
        )
        self.assertEqual("SEMANTIC_AI", context["interview_policy"]["owner"])
        self.assertTrue(context["material_unknown_policy"]["no_silent_drop"])
        self.assertEqual("NEEDS_CLARIFICATION", context["decision_readiness"])

    def test_unknown_parameter_is_not_silently_ignored(self) -> None:
        context = build_human_intelligence_context({}, "I need a moonlight ceramics room with kiln access")
        accounting = context["user_statement_accounting"]
        self.assertEqual(0, accounting["dropped_count"])
        self.assertEqual("ASKED", accounting["unresolved_parameters"][0]["status"])
        self.assertEqual(1, len(context["adaptive_questions"]))
        self.assertEqual(
            context["readiness_guardian"]["client_owned_blockers"][0]["fact_key"],
            context["adaptive_questions"][0]["target_fact_key"],
        )
        self.assertTrue(context["interview_policy"]["hard_coded_question_generation_forbidden"])

    def test_hebrew_unknown_parameter_is_preserved(self) -> None:
        context = build_human_intelligence_context({}, "חשוב לנו אוכל טוב, גינון מטופח, וסטודיו לקרמיקה עם תנור בערב")
        accounting = context["user_statement_accounting"]
        self.assertEqual(100.0, accounting["coverage_percent"])
        self.assertEqual(0, accounting["dropped_count"])
        self.assertTrue(any("סטודיו" in row["statement"] for row in accounting["unresolved_parameters"]))

    def test_existing_known_bereavement_phrase_does_not_create_false_unknown(self) -> None:
        accounting = account_user_input("recently widowed")
        self.assertEqual([], accounting["unresolved_parameters"])
        self.assertEqual("USED", accounting["statements"][0]["status"])


if __name__ == "__main__":
    unittest.main()


def test_reconciliation_does_not_claim_keyword_classification_proves_comprehension():
    text = "Dad receives dialysis three times a week and needs wound care."
    packet = {
        "questionnaire_patch": {
            "medicalCareProfile": {"needs": ["Wound care"]}
        },
        "statements": [{
            "raw_text": text, "status": "USED", "knowledge_state": "KNOWN",
            "mapped_parameters": ["medicalCareProfile.needs"],
        }],
    }
    audit = reconcile_semantic_statement_coverage(text, packet)
    assert audit["statement_count"] == 2
    assert audit["trace_linked_count"] == 2
    assert audit["semantic_coverage_percent"] is None
    assert audit["semantic_coverage_status"] == "NOT_INDEPENDENTLY_VERIFIED"


def test_unquoted_clause_is_visible_as_missing_not_silently_covered():
    text = "Mom needs a small community and loves pottery at night."
    packet = {"questionnaire_patch": {}, "statements": [{
        "raw_text": "Mom needs a small community", "status": "USED",
        "mapped_parameters": [],
    }]}
    audit = reconcile_semantic_statement_coverage(text, packet)
    assert audit["missing_source_trace_count"] == 1
    assert any("pottery" in s for s in audit["unverified_clauses"])
    assert audit["semantic_coverage_percent"] is None


def test_research_is_not_mistaken_for_materialized_capability():
    text = "We need a synagogue within walking distance."
    audit = reconcile_semantic_statement_coverage(text, {
        "questionnaire_patch": {},
        "statements": [{
            "raw_text": text, "status": "RESEARCH_REQUIRED",
            "research_task": "Check nearby synagogues",
            "mapped_parameters": [],
        }],
    })
    assert audit["statements"][0]["trace_status"] == "RESEARCH_TRACE"
    assert audit["semantic_coverage_percent"] is None
