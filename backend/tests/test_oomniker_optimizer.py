from app.services.oomniker_optimizer import analyze_oomniker

def test_system_must_is_never_relaxable():
    profile={'constraints':[{'parameter':'secure_memory','authority':'SYSTEM_MUST'}]}
    out=analyze_oomniker(profile,[{}])
    assert out['system_must_immutable']==['secure_memory']
    assert not out['suggestions']

def test_client_must_requires_explicit_reconsideration():
    profile={'constraints':[{'parameter':'music_lessons','authority':'CLIENT_MUST'}]}
    rows=[{'matched_parameter_ids':['music_lessons']},{'matched_parameter_ids':[]},{'matched_parameter_ids':[]}]
    out=analyze_oomniker(profile,rows)
    s=out['suggestions'][0]
    assert s['action']=='ASK_CLIENT_TO_RECONSIDER'
    assert s['requires_client_approval'] is True
    assert s['additional_options_if_relaxed']==2

def test_preference_can_be_recommended_but_never_auto_changed():
    profile={'constraints':[{'parameter':'music_lessons','authority':'PREFERENCE'}]}
    rows=[{'matched_parameter_ids':['music_lessons']},{'matched_parameter_ids':[]}]
    s=analyze_oomniker(profile,rows)['suggestions'][0]
    assert s['action']=='RECOMMEND_TRANSPARENT_ALTERNATIVE'
    assert s['may_auto_change'] is False

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


def test_client_must_is_only_a_question_and_counts_single_constraint_unlocks():
    out = _advise([_item("A", fail=["KOSHER_MEALS"]), _item("B", fail=["KOSHER_MEALS"], price=9000), _item("C")])
    kosher = next(s for s in out["suggestions"] if s["parameter"] == "KOSHER_MEALS")
    assert kosher["action"] == "ASK_CLIENT_TO_RECONSIDER" and kosher["requires_client_approval"] and not kosher["may_auto_change"]
    assert kosher["additional_options_if_relaxed"] == 1  # B also needs budget, so it is not unlocked by kosher alone
    assert out["recommendable_count"] == 1


def test_unknown_only_candidates_are_verification_items_not_relaxations():
    out = _advise([_item("A", unknown=["KOSHER_MEALS"]), _item("B", unknown=["KOSHER_MEALS"])])
    verify = [s for s in out["suggestions"] if s["action"] == "VERIFY_WITH_COMMUNITIES"]
    assert verify and verify[0]["candidates_waiting_only_on_this_evidence"] == 2
    assert not [s for s in out["suggestions"] if s["action"] == "ASK_CLIENT_TO_RECONSIDER"]
