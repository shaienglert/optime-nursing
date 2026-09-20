import json
from pathlib import Path

from app.services.canonical_intake_state import canonicalize_intake_state
from app.services.living_strategy_runtime import build_living_strategy_context
from app.services.semantic_facility_requirements import extract_semantic_facility_requirements


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "golden_intake_personas_v1.json"


def test_all_ten_golden_intake_personas_keep_identity_and_household_invariants() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture["fixture_version"] == "golden-intake-v1"
    assert len(fixture["cases"]) == 10

    for case in fixture["cases"]:
        state = canonicalize_intake_state(case["questionnaire_state"])
        expected = case["expected"]
        assert state.get("relationship", "") == expected["relationship"], case["id"]
        assert state.get("gender", "") == expected["gender"], case["id"]
        strategy = build_living_strategy_context(state, case["natural_language_query"])
        assert strategy["household"]["type"] == expected["household_type"], case["id"]


def test_geographic_distance_never_becomes_an_internal_mobility_requirement() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    case = next(item for item in fixture["cases"] if item["id"] == "P10_FRIEND_DISTANCE_ONLY")
    synthetic_semantic_packet = {
        "decision_intelligence": {
            "human_intelligence": {
                "semantic_ai": {
                    "result": {
                        "facts": [case["natural_language_query"]],
                        "preferences": [case["natural_language_query"]],
                        "constraints": [case["natural_language_query"]],
                        "statements": [],
                    }
                }
            }
        }
    }
    requirements = extract_semantic_facility_requirements(synthetic_semantic_packet, case["questionnaire_state"])
    assert "SEMANTIC_MOBILITY_LAYOUT" not in {item["key"] for item in requirements}
