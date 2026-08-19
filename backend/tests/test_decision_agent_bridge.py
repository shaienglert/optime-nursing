from __future__ import annotations

import unittest

from app.services.decision_agent_bridge import (
    _material_dimensions,
    _resolve_with_agent_evidence,
    social_evidence_sort_key,
)
from app.services.decision_research_worker import process_pending_decision_research


class DecisionAgentBridgeTests(unittest.TestCase):
    def test_social_research_only_becomes_material_after_explicit_high_priority(self) -> None:
        unknown = {"signals": {"social_transition_priority": {"value": "UNKNOWN"}}}
        high = {"signals": {"social_transition_priority": {"value": "HIGH"}}}
        self.assertNotIn("social_engagement", _material_dimensions(unknown))
        self.assertEqual(_material_dimensions(high)["social_engagement"], ("activities", "transportation"))

    def test_verified_agent_evidence_closes_only_the_fact_it_verified(self) -> None:
        evidence = [{"payload": {"market": "las-vegas", "social_engagement_verified": True, "transportation_verified": False}}]
        unresolved = _resolve_with_agent_evidence(["activities", "transportation"], "social_engagement", evidence)
        self.assertEqual(unresolved, ["transportation"])

    def test_unknown_evidence_is_not_negative_but_verified_positive_can_order(self) -> None:
        unknown = {"agent_person_fit_evidence": []}
        positive = {"agent_person_fit_evidence": [{"confidence": 0.82, "payload": {"social_engagement_verified": True}}]}
        self.assertLess(social_evidence_sort_key(positive), social_evidence_sort_key(unknown))

    def test_worker_module_is_importable(self) -> None:
        self.assertTrue(callable(process_pending_decision_research))


if __name__ == "__main__":
    unittest.main()
