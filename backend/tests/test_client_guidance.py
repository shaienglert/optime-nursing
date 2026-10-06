import copy
import unittest

from app.services.client_guidance import build_guidance


class ClientGuidanceTests(unittest.TestCase):
    def setUp(self):
        self.state = {"relationship": "Mom", "budget": 6000}
        self.profile = {"needs": [{"need_text": "Help with medication"}]}
        self.decision = {"results": [
            {"canonical_facility_id": "a", "facility_name": "First", "must_eligibility": "MUST_ELIGIBLE", "explanation": {"why_matches": ["Medication support is provided"], "needs_verification": ["Confirm room availability"], "concerns": ["Care delivered by an external provider"]}},
            {"canonical_facility_id": "b", "facility_name": "Pending", "must_eligibility": "MUST_PENDING_VERIFICATION", "explanation": {"why_matches": ["Unverified"]}},
        ]}

    def run_guidance(self, transport, **kwargs):
        return build_guidance(state=self.state, profile=self.profile, query="Mom fears loneliness", transport=transport, **kwargs)

    def test_ai_gets_only_final_options_and_cannot_mutate_decision(self):
        before = copy.deepcopy(self.decision)
        def transport(payload):
            self.assertIn("facility:a:needs_verification:0", payload["facts"])
            self.assertIn("facility:a:concerns:0", payload["facts"])
            self.assertFalse(any(key.startswith("facility:b:") for key in payload["facts"]))
            self.assertIn("Mom fears loneliness", payload["facts"]["client:story"])
            return {"paragraphs": [{"text": "Medication support is provided.", "source_ids": ["facility:a:why_matches:0"]}], "new_ranking": ["b", "a"]}
        result = self.run_guidance(transport, decision=self.decision)
        self.assertEqual(result["status"], "AI_READY")
        self.assertNotIn("new_ranking", result)
        self.assertEqual(self.decision, before)

    def test_missing_and_unknown_citations_fail_closed(self):
        for refs in ([], ["made-up"], "need:0", [None]):
            with self.subTest(refs=refs):
                result = self.run_guidance(lambda _: {"paragraphs": [{"text": "Invented", "source_ids": refs}]})
                self.assertEqual(result["status"], "AI_UNAVAILABLE")
                self.assertEqual(result["paragraphs"], [])

    def test_numerical_claim_must_be_in_its_cited_source(self):
        result = self.run_guidance(lambda _: {"paragraphs": [{"text": "99% of families recommend it.", "source_ids": ["need:0"]}]})
        self.assertEqual(result["status"], "AI_UNAVAILABLE")

    def test_currency_formatting_does_not_reject_the_same_budget(self):
        result = self.run_guidance(lambda _: {"paragraphs": [{"text": "Your budget is $6,000 per month.", "source_ids": ["client:budget"]}]})
        self.assertEqual(result["status"], "AI_READY")

    def test_later_card_keeps_global_shortlist_count_and_its_real_position(self):
        self.decision["results"].append({"canonical_facility_id": "c", "facility_name": "Second", "must_eligibility": "MUST_ELIGIBLE", "availability_status": "NO", "client_intent_fit": {"nice_mismatch": ["CONTINUUM_OF_CARE"]}})
        def transport(payload):
            facts = payload["facts"]
            self.assertEqual(facts["search:options"], "2 options displayed in authoritative order: First, Second")
            self.assertIn("position is 2", facts["search:card_scope"])
            self.assertIn("NO", facts["facility:c:availability"])
            self.assertIn("CONTINUUM_OF_CARE", facts["facility:c:nice_mismatch"])
            self.assertNotIn("facility:a:name", facts)
            return {"paragraphs": [{"text": "Second is another option.", "source_ids": ["facility:c:name"]}]}
        self.assertEqual(self.run_guidance(transport, decision=self.decision, facility_id="c")["status"], "AI_READY")

    def test_later_card_cannot_claim_first_or_only_even_with_a_valid_citation(self):
        self.decision["results"].append({"canonical_facility_id": "c", "facility_name": "Second", "must_eligibility": "MUST_ELIGIBLE"})
        for text in ("This is the only option.", "This community is placed first."):
            result = self.run_guidance(lambda _: {"paragraphs": [{"text": text, "source_ids": ["facility:c:name"]}]}, decision=self.decision, facility_id="c")
            self.assertEqual(result["status"], "AI_UNAVAILABLE")

    def test_pending_facility_cannot_get_personal_recommendation(self):
        def never(_):
            self.fail("AI must not be called for pending recommendation")
        self.assertEqual(self.run_guidance(never, decision=self.decision, facility_id="b")["status"], "NO_RECOMMENDATION")

    def test_provider_failure_keeps_the_fact_ledger(self):
        def unavailable(_):
            raise RuntimeError("Unavailable")
        result = self.run_guidance(unavailable)
        self.assertEqual(result["status"], "AI_UNAVAILABLE")
        self.assertEqual(result["sources"]["need:0"], "Help with medication")


if __name__ == "__main__":
    unittest.main()
