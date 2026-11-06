import pytest

from app.services import decision_engine_core as core
from app.services.client_intent_runtime import evaluate_candidate_intent


@pytest.mark.parametrize('parameter', ['kosher', 'therapeutic_diets', 'transportation', 'arbitrary_capability'])
@pytest.mark.parametrize('raw', ['UNKNOWN', 'unknown', ' UNKNOWN ', None, '', '  '])
@pytest.mark.parametrize('level', ['REQUIRED', 'PREFERENCE'])
def test_unknown_cannot_match_even_when_acceptable_list_includes_unknown(parameter, raw, level):
    need = {'parameter_id': parameter, 'requirement_level': level,
            'desired_value': 'YES', 'acceptable_values': ['YES', 'UNKNOWN', '']}
    rows = {parameter: {'raw_value': raw, 'source': 'contract evidence'}}
    status, _reason = core._evaluate_need(need, rows)
    assert status == 'UNKNOWN'
    eligibility = core._eligibility_from_needs([need], rows)
    assert eligibility['matched_needs'] == []
    unknowns = 'unknown_critical_needs' if level == 'REQUIRED' else 'unknown_preferences'
    assert [item['parameter_id'] for item in eligibility[unknowns]] == [parameter]


@pytest.mark.parametrize('raw,expected', [('YES', 'MATCH'), ('NO', 'GAP'), ('LIMITED', 'MATCH')])
def test_known_values_retain_their_matching_meaning(raw, expected):
    need = {'parameter_id': 'transportation', 'desired_value': 'YES',
            'acceptable_values': ['YES', 'LIMITED', 'UNKNOWN']}
    assert core._evaluate_need(need, {'transportation': {'raw_value': raw}})[0] == expected


def test_missing_continuum_evidence_is_neutral():
    key = 'CONTINUUM_OF_CARE'
    fit = evaluate_candidate_intent(
        {'canonical_type': 'ASSISTED_LIVING_RFG'},
        {'must_haves': [], 'nice_to_haves': [{'key': key}]},
    )
    assert key in fit['nice_unknown']
    assert key not in fit['nice_match']
    assert key not in fit['nice_mismatch']
    assert key not in fit['nice_fit_scores']


def test_unverified_domain_fit_is_unscored_not_zero():
    need = {'parameter_id': 'kosher', 'requirement_level': 'PREFERENCE',
            'desired_value': 'YES', 'acceptable_values': ['YES', 'UNKNOWN']}
    row = {'kosher': {'raw_value': 'UNKNOWN'}}
    eligibility = core._eligibility_from_needs([need], row)
    breakdown = core._domain_breakdown(
        [need], eligibility['matched_needs'], eligibility['unmet_verified_needs'])
    assert breakdown['personal_social_fit'] is None
    assert eligibility['unknown_preferences'][0]['parameter_id'] == 'kosher'


def test_verified_gap_remains_genuine_zero_and_match_remains_full():
    need = {'parameter_id': 'kosher', 'requirement_level': 'PREFERENCE',
            'desired_value': 'YES', 'acceptable_values': ['YES']}
    gap = core._domain_breakdown([need], [], [{'parameter_id': 'kosher'}])
    match = core._domain_breakdown([need], [{'parameter_id': 'kosher'}], [])
    assert gap['personal_social_fit'] == 0.0
    assert match['personal_social_fit'] == 100.0


@pytest.mark.parametrize("level", ["REQUIRED", "HIGH"])
def test_unverified_transport_cannot_satisfy_a_critical_must(level):
    need = {"parameter_id": "transportation", "requirement_level": level,
            "desired_value": "YES", "acceptable_values": ["YES", "UNKNOWN"]}
    result = core._eligibility_from_needs(
        [need], {"transportation": {"raw_value": "UNKNOWN", "source": "facility"}})
    assert result["eligibility_status"] == "INSUFFICIENT_EVIDENCE"
    assert result["matched_needs"] == []
    assert [x["parameter_id"] for x in result["unknown_critical_needs"]] == ["transportation"]
    assert result["unmet_verified_needs"] == []


def test_unknown_transport_preference_is_neither_verified_match_nor_mismatch():
    need = {"parameter_id": "transportation", "requirement_level": "PREFERENCE",
            "desired_value": "YES", "acceptable_values": ["YES", "UNKNOWN"]}
    result = core._eligibility_from_needs(
        [need], {"transportation": {"raw_value": "UNKNOWN", "source": "facility"}})
    assert result["matched_needs"] == []
    assert result["preference_matches"] == []
    assert result["unmet_verified_needs"] == []
    assert [x["parameter_id"] for x in result["unknown_preferences"]] == ["transportation"]
    assert core._domain_breakdown([need], [], [])["personal_social_fit"] is None


def test_confirmed_transport_does_not_lose_existing_matching_behavior():
    need = {"parameter_id": "transportation", "requirement_level": "REQUIRED",
            "desired_value": "YES", "acceptable_values": ["YES", "UNKNOWN"]}
    match = core._eligibility_from_needs(
        [need], {"transportation": {"raw_value": "YES", "source": "facility"}})
    assert [x["parameter_id"] for x in match["matched_needs"]] == ["transportation"]
    assert match["unknown_critical_needs"] == []
