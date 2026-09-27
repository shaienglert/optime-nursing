from pathlib import Path


def test_research_worker_does_not_stamp_unresearched_capabilities_false():
    text = Path("backend/app/services/decision_research_worker.py").read_text(encoding="utf-8")
    assert '"social_engagement_verified": None' in text
    assert '"medication_support_verified": None' in text
    assert '"couple_coresidence_verified": None' in text
    assert '"outside_care_allowed_verified": None' in text
