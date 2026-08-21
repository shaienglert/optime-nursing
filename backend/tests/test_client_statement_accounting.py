from __future__ import annotations

import unittest

from app.services.client_statement_accounting import account_user_input
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
        # No-drop identifies the unresolved fact but does not script a question.
        # Semantic AI owns question selection under this Guardian constraint.
        self.assertEqual([], context["adaptive_questions"])
        self.assertEqual("SEMANTIC_AI", context["interview_policy"]["owner"])
        self.assertTrue(context["material_unknown_policy"]["no_silent_drop"])
        self.assertEqual("NEEDS_CLARIFICATION", context["decision_readiness"])

    def test_unknown_parameter_is_not_silently_ignored(self) -> None:
        context = build_human_intelligence_context({}, "I need a moonlight ceramics room with kiln access")
        accounting = context["user_statement_accounting"]
        self.assertEqual(0, accounting["dropped_count"])
        self.assertEqual("ASKED", accounting["unresolved_parameters"][0]["status"])
        self.assertEqual([], context["adaptive_questions"])
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
