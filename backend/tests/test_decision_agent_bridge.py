from __future__ import annotations

import unittest

from app.models.agent_execution import AgentWorker
from app.services.decision_agent_bridge import (
    _ensure_worker,
    _material_dimensions,
    _resolve_with_agent_evidence,
    social_evidence_sort_key,
)
from app.services.decision_research_worker import process_pending_decision_research


class _FakeDialect:
    name = "sqlite"


class _FakeBind:
    dialect = _FakeDialect()


class _FakeQuery:
    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return None


class _FakeSession:
    def __init__(self) -> None:
        self.new = []

    def get_bind(self):
        return _FakeBind()

    def query(self, _model):
        return _FakeQuery()

    def add(self, row):
        self.new.append(row)


class DecisionAgentBridgeTests(unittest.TestCase):
    def test_social_research_only_becomes_material_after_explicit_high_priority(self) -> None:
        unknown = {"signals": {"social_transition_priority": {"value": "UNKNOWN"}}}
        high = {"signals": {"social_transition_priority": {"value": "HIGH"}}}
        self.assertNotIn("social_engagement", _material_dimensions(unknown))
        self.assertEqual(_material_dimensions(high)["social_engagement"], ("activities", "transportation"))

    def test_quality_safety_research_is_always_material(self) -> None:
        dimensions = _material_dimensions({"signals": {}})
        self.assertEqual(
            dimensions["facility_quality_safety"],
            (
                "inspection_rating",
                "deficiency_count",
                "deficiency_severity",
                "complaint_related_findings",
                "penalties_fines",
                "sanctions_final_orders",
            ),
        )

    def test_worker_registration_is_idempotent_inside_one_transaction(self) -> None:
        db = _FakeSession()
        _ensure_worker(db, "provider_intelligence")
        _ensure_worker(db, "provider_intelligence")
        workers = [row for row in db.new if isinstance(row, AgentWorker)]
        self.assertEqual(len(workers), 1)
        self.assertEqual(workers[0].agent_key, "provider_intelligence")

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
