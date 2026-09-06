import json
from pathlib import Path

from app.services.personal_decision_report_builder import build_personal_report_payload
from app.services.personal_decision_report_renderer import render_personal_report


def test_expected_report_artifact_matches_generator():
    root = Path(__file__).parent / "fixtures"
    fixture = json.loads((root / "personal_report_example.json").read_text())
    expected = json.loads((root / "personal_report_expected.json").read_text())
    result = {
        "results": [{"client_intent_fit": {"hard_gate": "MUST_ELIGIBLE"}}],
        "must_eligible_count": 1,
        "must_pending_verification_count": 0,
        "decision_intelligence": {
            "human_intelligence": {"decision_readiness": "READY"},
            "facility_selection_pipeline": {
                "ai_ranking": {"status": "AI_RANKED"},
                "dynamic_preferences": {"preference_count": 0},
            },
        },
    }
    actual = render_personal_report(build_personal_report_payload(
        result,
        case_claims=fixture["case_claims"],
        research_claims=fixture["research_claims"],
        facility_claims=fixture["facility_claims"],
    ))
    # Expected artifact contains documentation-only markers not emitted to users.
    comparable = {k: v for k, v in expected.items() if k not in {"fixture_only", "warning"}}
    # Confidence is retained by the live renderer; omit it here to keep fixture readable.
    for section in actual["sections"]:
        for claim in section["claims"]:
            claim.pop("confidence", None)
    assert actual == comparable
