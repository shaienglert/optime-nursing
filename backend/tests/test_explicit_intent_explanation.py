from app.services.client_intent_runtime import attach_client_intent_fit


def language_intent(role="must_haves"):
    key = "REQUIRED_LANGUAGE_SUPPORT" if role == "must_haves" else "PREFERRED_LANGUAGE_SUPPORT"
    return {role: [{"key": key, "value": "Spanish"}]}


def test_requested_language_proof_precedes_generic_care_bullets():
    row = {"verified_capabilities": {"languages": "English, Spanish"}, "explanation": {"why_matches": ["Daily activities supported", "Medication supported", "Current price supported"]}}
    attach_client_intent_fit([row], language_intent())
    assert row["explanation"]["why_matches"][0] == "Verified Spanish language support matches your requirement."
    assert row["explanation"]["explicit_intent_matches"][0]["key"] in row["client_intent_fit"]["must_pass"]


def test_unknown_or_failed_language_is_never_described_as_verified_match():
    for capabilities in ({}, {"languages": "UNKNOWN"}, {"languages": "English"}):
        row = {"verified_capabilities": capabilities}
        attach_client_intent_fit([row], language_intent())
        assert row["explanation"]["explicit_intent_matches"] == []
        assert row["explanation"]["why_matches"] == []


def test_unrequested_language_is_not_advertised_as_personalized_match():
    row = {"verified_capabilities": {"languages": "English"}, "explanation": {"why_matches": ["Language support is supported by verified evidence", "Medication management is supported by verified evidence"]}}
    attach_client_intent_fit([row], {})
    assert row["explanation"]["why_matches"] == ["Medication management is supported by verified evidence"]


def test_preferred_language_is_described_as_preference_not_requirement():
    row = {"verified_capabilities": {"languages": "English, Spanish"}}
    attach_client_intent_fit([row], language_intent("nice_to_haves"))
    assert row["explanation"]["why_matches"] == ["Verified Spanish language support matches your preference."]


def test_refresh_removes_an_old_language_proof_and_does_not_duplicate_bullets():
    row = {"verified_capabilities": {"languages": "English, Spanish"}}
    attach_client_intent_fit([row], language_intent())
    attach_client_intent_fit([row], language_intent())
    assert len(row["explanation"]["why_matches"]) == 1
    row["verified_capabilities"] = {}
    attach_client_intent_fit([row], language_intent())
    assert row["explanation"]["why_matches"] == []


def test_declined_continuity_creates_no_continuum_explanation():
    row = {"synthetic_pilot": True, "synthetic_archetype": "CONTINUING_CARE"}
    attach_client_intent_fit([row], {})
    assert row["explanation"]["why_matches"] == []


def test_requested_activity_explanation_uses_the_actual_selected_values():
    row = {"verified_capabilities": {"activities": "Astronomy club, Classes"}}
    intent = {"must_haves": [{"key": "REQUIRED_ACTIVITIES", "value": ["Astronomy club"]}]}
    attach_client_intent_fit([row], intent)
    assert row["explanation"]["why_matches"] == ["Verified activities match your requirement: Astronomy club."]
