from app.services.oomniker_optimizer import analyze_oomniker

def test_system_must_is_never_relaxable():
    profile={'constraints':[{'parameter':'secure_memory','authority':'SYSTEM_MUST'}]}
    out=analyze_oomniker(profile,[{}])
    assert out['system_must_immutable']==['secure_memory']
    assert not out['suggestions']

def test_client_must_is_not_offered_for_reconsideration():
    profile={'constraints':[{'parameter':'music_lessons','authority':'CLIENT_MUST'}]}
    rows=[{'matched_parameter_ids':['music_lessons']},{'matched_parameter_ids':[]},{'matched_parameter_ids':[]}]
    out=analyze_oomniker(profile,rows)
    assert out['suggestions'] == []

def test_legacy_match_absence_cannot_prove_a_preference_gain():
    profile={'constraints':[{'parameter':'music_lessons','authority':'PREFERENCE'}]}
    rows=[{'matched_parameter_ids':['music_lessons']},{'matched_parameter_ids':[]}]
    assert analyze_oomniker(profile,rows)['suggestions'] == []

# ---- Counterfactual over the full candidate ledger (owner, 2026-10-01) ----------------

def _item(fid, *, fail=(), unknown=(), price=4000, eligibility="ELIGIBLE", unmet=()):
    return {"canonical_facility_id": fid, "eligibility_status": eligibility, "unmet_critical_needs": list(unmet),
            "must_fail": list(fail), "must_unknown": list(unknown), "price": price}


def _advise(ledger, budget=5000):
    context = {"ledger": ledger, "client_intent": {"must_haves": [{"key": "KOSHER_MEALS"}]}, "funnel": {}, "location_scope": {}}
    return analyze_oomniker({"budget": budget}, [], decision_context=context)


def test_counterfactual_never_offers_system_or_care_constraints():
    out = _advise([_item("A", fail=["LICENSE_CURRENTLY_VALID"]), _item("B", fail=["ADL_SUPPORT_AVAILABLE"]), _item("C", eligibility="INELIGIBLE", unmet=["dialysis_arrangements"])])
    assert out["suggestions"] == []
    assert set(out["immutable_constraints_blocking"]) == {"LICENSE_CURRENTLY_VALID", "ADL_SUPPORT_AVAILABLE", "dialysis_arrangements"}


def test_client_must_impact_is_explained_without_a_relaxation():
    out = _advise([_item("A", fail=["KOSHER_MEALS"]), _item("B", fail=["KOSHER_MEALS"], price=9000), _item("C")])
    assert out["suggestions"] == []
    kosher = next(s for s in out["constraint_impacts"] if s["parameter"] == "KOSHER_MEALS")
    assert kosher["blocked_count"] == 2 and kosher["sole_verified_blocker_count"] == 1
    assert kosher["may_relax"] is False
    assert out["recommendable_count"] == 1


def test_unknown_only_candidates_are_verification_items_not_relaxations():
    out = _advise([_item("A", unknown=["KOSHER_MEALS"]), _item("B", unknown=["KOSHER_MEALS"])])
    verify = [s for s in out["suggestions"] if s["action"] == "VERIFY_WITH_COMMUNITIES"]
    assert verify and verify[0]["candidates_waiting_only_on_this_evidence"] == 2
    assert not [s for s in out["suggestions"] if s["action"] == "ASK_CLIENT_TO_RECONSIDER"]
