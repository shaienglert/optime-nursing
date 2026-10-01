from app.services.ai_candidate_ranking_runtime import _ground_ranking_reason


def test_medication_denial_is_removed_without_changing_valid_explanation():
    row = {"verified_capabilities": {"medication_support": "YES"}}
    reason = "Small community matches his preference. No verified medication support exists."
    assert _ground_ranking_reason(row, reason, [row]) == "Small community matches his preference."


def test_occupational_therapy_is_not_described_as_unverified_pt_ot():
    row = {"verified_capabilities": {"ot": "YES", "pt": "NO"}}
    assert "no verified" not in _ground_ranking_reason(row, "There is no verified PT/OT pathway.", [row]).lower()


def test_price_superlative_is_checked_across_ranked_candidates():
    row = {"starting_monthly_price": 4077}
    reason = "This community has the lowest price. Its large social community fits her needs."
    assert _ground_ranking_reason(row, reason, [row, {"starting_monthly_price": 2798}]) == "Its large social community fits her needs."
    assert _ground_ranking_reason(row, reason, [row, {"starting_monthly_price": 4941}]) == reason


def test_unknown_evidence_stays_visible():
    row = {"verified_capabilities": {"medication_support": "UNKNOWN"}}
    reason = "Medication support is not verified."
    assert _ground_ranking_reason(row, reason, [row]) == reason


def test_verified_medication_support_does_not_hide_unknown_staffing():
    row = {"verified_capabilities": {"medication_support": "YES"}, "client_intent_fit": {"must_pass": ["MEDICATION_SUPPORT_AVAILABLE"]}}
    reason = "Medication support is verified but staffing is not verified."
    assert _ground_ranking_reason(row, reason, [row]) == reason
