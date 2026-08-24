from __future__ import annotations

import unittest

from app.services.living_strategy_runtime import build_living_strategy_context


class WidowHouseholdStrategyTests(unittest.TestCase):
    def test_deceased_spouse_does_not_create_couple_household(self) -> None:
        state = {
            "relationship": "Mom",
            "ageGroup": "90+",
            "assistanceLevel": "Needs assistance with bathing and dressing",
            "memoryStatus": "No",
            "budget": 8000,
            "locationCity": "Las Vegas",
            "state": "NV",
        }
        query = (
            "My mother is 90. Her husband died two months ago and she does not want to remain alone at home. "
            "She is mentally alert, has no dementia, is mobile, but needs daily help with bathing, dressing and medication. "
            "She enjoys classical music and being around other people."
        )
        strategy = build_living_strategy_context(state, query)
        self.assertNotEqual(strategy["household"]["type"], "COUPLE")
        self.assertFalse(strategy["household"]["requires_two_resident_model"])
        self.assertNotIn("ccrc_entrance_fee_tolerance", strategy.get("material_unknowns") or [])
        required = {
            capability
            for candidate in strategy.get("strategy_candidates") or []
            for capability in candidate.get("required_capabilities") or []
        }
        self.assertNotIn("COUPLE_CORESIDENCE", required)


if __name__ == "__main__":
    unittest.main()
