from app.services.client_intent_runtime import evaluate_candidate_intent
from app.services.semantic_intent_ai import _explicit_user_text_answered_dimensions


def _couple_intent():
    return {
        "must_haves": [{"key": "COUPLE_CORESIDENCE"}],
        "nice_to_haves": [],
    }


def test_synthetic_accepts_couples_passes_couple_gate():
    result = evaluate_candidate_intent(
        {"accepts_couples": True, "canonical_type": "ASSISTED_LIVING_RFG"},
        _couple_intent(),
    )
    assert "COUPLE_CORESIDENCE" in result["must_pass"]
    assert "COUPLE_CORESIDENCE" not in result["must_unknown"]
    assert "COUPLE_CORESIDENCE" not in result["must_fail"]


def test_synthetic_rejects_couples_fails_couple_gate():
    result = evaluate_candidate_intent(
        {"accepts_couples": False, "canonical_type": "ASSISTED_LIVING_RFG"},
        _couple_intent(),
    )
    assert "COUPLE_CORESIDENCE" in result["must_fail"]


def test_missing_couple_policy_stays_unknown():
    result = evaluate_candidate_intent(
        {"canonical_type": "ASSISTED_LIVING_RFG"},
        _couple_intent(),
    )
    assert "COUPLE_CORESIDENCE" in result["must_unknown"]


def test_governed_agent_couple_evidence_still_passes():
    result = evaluate_candidate_intent(
        {
            "canonical_type": "ASSISTED_LIVING_RFG",
            "agent_person_fit_evidence": [{"payload": {"couple_coresidence_verified": True}}],
        },
        _couple_intent(),
    )
    assert "COUPLE_CORESIDENCE" in result["must_pass"]


def test_alzheimers_counts_as_explicit_cognitive_dimension():
    assert "cognitive" in _explicit_user_text_answered_dimensions("My mother has Alzheimer's.")


def test_no_dementia_counts_as_explicit_cognitive_dimension():
    assert "cognitive" in _explicit_user_text_answered_dimensions("She has no dementia.")


def test_unrelated_nursing_word_does_not_create_cognitive_dimension():
    assert "cognitive" not in _explicit_user_text_answered_dimensions("She needs nursing support after surgery.")


def test_plain_memory_concern_counts_as_cognitive_dimension():
    assert "cognitive" in _explicit_user_text_answered_dimensions("We have memory concerns.")
