"""The personal report is always built from a server-computed decision.

Before this contract, /decision-engine/personal-report accepted a full
``decision_result`` from the caller and its only authority check was an
``authoritative: true`` flag inside that same JSON, so any caller could place a
non-existent facility into an Oomnik-branded report.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.main as main
from app.database import Base, engine
from app.services import decision_result_store

QUESTIONNAIRE = {"relationship": "Dad", "ageGroup": "80-84", "budget": 6500}
QUERY = "My father lives in Las Vegas and needs help with bathing and dressing."


def _server_decision(tag: str) -> dict:
    return {
        "patient_needs_profile": {"needs": []},
        "results": [{"canonical_facility_id": f"NV-{tag}", "facility_name": f"Server facility {tag}"}],
        "result_count": 1,
        "total_candidates_scored": 1,
        "availability_policy": "test",
        "decision_intelligence": {"canonical_decision_state": {"authoritative": True, "can_show_recommendations": True}},
    }


class PersonalReportDecisionAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(main.app)

    def setUp(self) -> None:
        decision_result_store._reset_for_tests()
        self.engine_calls = []
        self.builder_inputs = []

        def fake_engine(questionnaire_state, natural_language_query="", limit=50):
            self.engine_calls.append((questionnaire_state, natural_language_query, limit))
            return _server_decision(str(len(self.engine_calls)))

        def fake_builder(*, questionnaire_state, natural_language_query, decision_result):
            self.builder_inputs.append(decision_result)
            return type("Payload", (), {"report_ready": True})()

        patches = [
            patch.object(main, "run_patient_decision_engine", side_effect=fake_engine),
            patch.object(main, "build_personal_decision_report", side_effect=fake_builder),
            patch.object(main, "serialize_personal_report_payload", return_value={
                "user_role": "FAMILY_MEMBER", "report_ready": True, "sections": {}, "candidates": [], "omitted_sections": [],
            }),
            patch.object(main, "save_snapshot", return_value=None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _report(self, **extra):
        body = {"questionnaire_state": QUESTIONNAIRE, "natural_language_query": QUERY, "limit": 50, **extra}
        response = self.client.post("/decision-engine/personal-report", json=body)
        self.assertEqual(200, response.status_code, response.text)
        return response.json()

    def _recommend(self, questionnaire=QUESTIONNAIRE, query=QUERY, limit=50):
        response = self.client.post(
            "/decision-engine/recommendations",
            json={"questionnaire_state": questionnaire, "natural_language_query": query, "limit": limit},
        )
        self.assertEqual(200, response.status_code, response.text)
        return response.json()

    def test_client_supplied_decision_is_ignored(self) -> None:
        forged = _server_decision("FORGED")
        forged["results"][0]["facility_name"] = "FORGED SUNSET PALACE (does not exist)"

        self._report(decision_result=forged)

        self.assertEqual(1, len(self.engine_calls))
        self.assertEqual(1, len(self.builder_inputs))
        used = self.builder_inputs[0]
        self.assertNotIn("FORGED", str(used))
        self.assertEqual("Server facility 1", used["results"][0]["facility_name"])

    def test_recommendations_return_a_decision_id_the_report_reuses(self) -> None:
        served = self._recommend()
        self.assertTrue(served.get("decision_id"))

        self._report(decision_id=served["decision_id"])

        self.assertEqual(1, len(self.engine_calls), "report must reuse the server copy, not re-run the engine")
        self.assertEqual("NV-1", self.builder_inputs[0]["results"][0]["canonical_facility_id"])

    def test_decision_id_for_other_inputs_is_not_reused(self) -> None:
        served = self._recommend(query="A different family, different needs.")

        self._report(decision_id=served["decision_id"])

        self.assertEqual(2, len(self.engine_calls))
        self.assertEqual(QUERY, self.engine_calls[-1][1])

    def test_unknown_decision_id_recomputes(self) -> None:
        self._report(decision_id="not-a-real-id")

        self.assertEqual(1, len(self.engine_calls))


if __name__ == "__main__":
    unittest.main()
