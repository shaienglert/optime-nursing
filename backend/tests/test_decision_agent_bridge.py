from __future__ import annotations

import unittest

from app.models.agent_execution import AgentWorker
from app.services.decision_agent_bridge import (
    _ensure_worker,
    _governed_evidence,
    _material_dimensions,
    _resolve_with_agent_evidence,
    research_priority,
    semantic_must_research_priority,
    social_evidence_sort_key,
)
from app.services.decision_research_worker import process_pending_decision_research

class _FakeDialect: name = "sqlite"
class _FakeBind: dialect = _FakeDialect()
class _FakeQuery:
    def filter(self, *_args, **_kwargs): return self
    def first(self): return None
class _FakeSession:
    def __init__(self) -> None: self.new = []
    def get_bind(self): return _FakeBind()
    def query(self, _model): return _FakeQuery()
    def add(self, row): self.new.append(row)

class DecisionAgentBridgeTests(unittest.TestCase):
    def test_social_research_only_becomes_material_after_explicit_high_priority(self) -> None:
        unknown = {"signals": {"social_transition_priority": {"value": "UNKNOWN"}}}; high = {"signals": {"social_transition_priority": {"value": "HIGH"}}}
        self.assertNotIn("social_engagement", _material_dimensions(unknown)); self.assertEqual(_material_dimensions(high)["social_engagement"], ("activities", "transportation"))

    def test_quality_safety_research_is_always_material(self) -> None:
        self.assertEqual(_material_dimensions({"signals": {}})["facility_quality_safety"], ("inspection_rating", "deficiency_count", "deficiency_severity", "complaint_related_findings", "penalties_fines", "sanctions_final_orders"))

    def test_worker_registration_is_idempotent_inside_one_transaction(self) -> None:
        db = _FakeSession(); _ensure_worker(db, "provider_intelligence"); _ensure_worker(db, "provider_intelligence")
        workers = [row for row in db.new if isinstance(row, AgentWorker)]; self.assertEqual(len(workers), 1); self.assertEqual(workers[0].agent_key, "provider_intelligence")

    def test_verified_agent_evidence_closes_only_the_fact_it_verified(self) -> None:
        evidence = [{"source": "OFFICIAL_PROVIDER_WEBSITE", "payload": {"dimension": "social_engagement", "market": "las-vegas", "official_identity_verified": True, "social_engagement_verified": True, "transportation_verified": False}}]
        self.assertEqual(_resolve_with_agent_evidence(["activities", "transportation"], "social_engagement", evidence), ["transportation"])

    def test_unverified_directory_cannot_create_positive_fact(self) -> None:
        evidence = [{"source": "OFFICIAL_PROVIDER_WEBSITE", "confidence": 0.82, "payload": {"dimension": "social_engagement", "official_identity_verified": False, "social_engagement_verified": True}}]
        self.assertEqual(_governed_evidence(evidence, "social_engagement"), [])
        self.assertEqual(_resolve_with_agent_evidence(["activities"], "social_engagement", evidence), ["activities"])

    def test_newer_completed_unverified_research_supersedes_stale_positive(self) -> None:
        evidence = [
            {"source": "PUBLIC_RESEARCH_UNVERIFIED_IDENTITY", "payload": {"dimension": "social_engagement", "research_completed": True, "official_identity_verified": False, "social_engagement_verified": False}},
            {"source": "OFFICIAL_PROVIDER_WEBSITE", "confidence": 0.82, "payload": {"dimension": "social_engagement", "official_identity_verified": True, "social_engagement_verified": True}},
        ]
        self.assertEqual(_governed_evidence(evidence, "social_engagement"), [])
        self.assertEqual(_resolve_with_agent_evidence(["activities"], "social_engagement", evidence), ["activities"])

    def test_unknown_evidence_is_not_negative_but_governed_positive_can_order(self) -> None:
        unknown = {"agent_person_fit_evidence": []}
        positive = {"agent_person_fit_evidence": [{"source": "OFFICIAL_PROVIDER_WEBSITE", "confidence": 0.82, "payload": {"dimension": "social_engagement", "official_identity_verified": True, "social_engagement_verified": True}}]}
        self.assertLess(social_evidence_sort_key(positive), social_evidence_sort_key(unknown))

    def test_worker_module_is_importable(self) -> None: self.assertTrue(callable(process_pending_decision_research))

    def test_must_affecting_dimension_outranks_quality_and_nice_dimensions(self) -> None:
        # care_support (medication/ADL) can flip MUST eligibility; facility_quality_safety
        # is a tie-break/quality signal; social_engagement is NICE-tier in this module's
        # own _material_dimensions (only material when explicitly HIGH priority).
        self.assertGreater(research_priority("care_support", 0), research_priority("facility_quality_safety", 0))
        self.assertGreater(research_priority("facility_quality_safety", 0), research_priority("social_engagement", 0))

    def test_priority_prefers_candidates_earlier_in_the_research_pool(self) -> None:
        self.assertGreater(research_priority("care_support", 0), research_priority("care_support", 5))
        # Position can never flip the ordering across dimension bands: a low-priority
        # dimension for the very first candidate still never outranks a MUST-affecting
        # dimension for a candidate deep in the pool.
        self.assertGreater(research_priority("care_support", 250), research_priority("social_engagement", 0))

    def test_semantic_must_priority_always_uses_the_must_tier_band_not_the_shared_table(self) -> None:
        # semantic_facility_requirements.py reuses the "social_engagement" dimension
        # label for a client-stated MUST -- an unrelated, higher-stakes meaning than
        # this module's own NICE-tier "social_engagement" bucket. Its priority must
        # come from the dedicated MUST-tier helper, not a lookup that would silently
        # misclassify it as NICE-tier.
        self.assertEqual(semantic_must_research_priority(0), research_priority("care_support", 0))
        self.assertGreater(semantic_must_research_priority(0), research_priority("social_engagement", 0))

if __name__ == "__main__": unittest.main()
