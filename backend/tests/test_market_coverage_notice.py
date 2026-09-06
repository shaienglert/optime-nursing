from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.services.facility_parameter_service import refresh_runtime_cache
from app.services.patient_decision_engine import run_patient_decision_engine


class MarketCoverageNoticeTests(unittest.TestCase):
    """OPTIME searches exactly one fixed market per deployment (OPTIME_CANONICAL_MARKET).

    It never routes a request to a different market's data based on the query, so a
    query naming a city outside the configured market must carry an explicit notice
    instead of silently returning facilities from the wrong area.
    """

    def setUp(self) -> None:
        self.env = patch.dict(os.environ, {"OPTIME_CANONICAL_MARKET": "las-vegas"}, clear=False)
        self.env.start()
        refresh_runtime_cache("test_setup")

    def tearDown(self) -> None:
        self.env.stop()
        refresh_runtime_cache("test_teardown")

    def _run_ready(self, questionnaire: dict, query: str, limit: int = 5) -> dict:
        hi = questionnaire.setdefault("humanIntelligenceV2", {})
        hi.setdefault("personalityProfile", {}).setdefault("communitySizePreference", "No preference")
        hi.setdefault("familyProfile", {}).setdefault("socialInteractionNeed", "Neither")
        hi.setdefault("transitionRiskProfile", {}).setdefault("attitudeTowardMove", "Cautious but open")
        ai_result = {"decision_readiness": "READY", "next_question": None, "statements": []}
        with patch.dict(os.environ, {"OPTIME_SEMANTIC_AI_ENABLED": "1", "OPTIME_SEMANTIC_AI_REQUIRED": "1"}, clear=False), patch(
            "app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai", return_value=ai_result
        ):
            return run_patient_decision_engine(questionnaire, query, limit=limit)

    def test_out_of_market_city_gets_explicit_notice(self) -> None:
        result = self._run_ready(
            {"assistanceLevel": "Needs assistance", "budget": 5000},
            "Looking for assisted living in Miami for my mother",
        )
        notice = result["market_coverage_notice"]
        self.assertIsNotNone(notice)
        self.assertIn("Miami", notice)
        self.assertIn("las-vegas", notice)

    def test_in_market_city_gets_no_notice(self) -> None:
        result = self._run_ready(
            {"assistanceLevel": "Needs assistance", "budget": 5000},
            "Looking for assisted living in Henderson for my mother",
        )
        self.assertIsNone(result["market_coverage_notice"])

    def test_unrecognized_location_text_gets_no_notice(self) -> None:
        # A location we have no recognized-city mapping for must stay silent, not
        # produce a false claim about coverage.
        result = self._run_ready(
            {"assistanceLevel": "Needs assistance", "budget": 5000},
            "Looking for assisted living somewhere warm for my mother",
        )
        self.assertIsNone(result["market_coverage_notice"])

    def test_no_location_mentioned_gets_no_notice(self) -> None:
        result = self._run_ready(
            {"assistanceLevel": "Needs assistance", "budget": 5000},
            "Looking for assisted living for my mother",
        )
        self.assertIsNone(result["market_coverage_notice"])


if __name__ == "__main__":
    unittest.main()
