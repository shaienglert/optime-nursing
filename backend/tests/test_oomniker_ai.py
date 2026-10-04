from app.services.oomniker_ai import advise_with_ai

def test_ai_cannot_propose_parameter_outside_governed_analysis():
    analysis={"suggestions":[{"parameter":"music_lessons","authority":"CLIENT_MUST","additional_options_if_relaxed":8}],"system_must_immutable":["secure_memory"]}
    packet={"message":"Music lessons narrow the choices.","proposals":[{"parameter":"secure_memory","alternative":"drop it","ask_client":"waive?"},{"parameter":"music_lessons","alternative":"private teacher","ask_client":"Would a private teacher preserve the goal?"}]}
    out=advise_with_ai(analysis=analysis,client_context={},transport=lambda _:packet)
    assert out["proposals"] == []
    assert out["message"] == ""
    assert out["profile_mutated"] is False

def test_ai_cannot_invent_counts_or_alternatives_in_free_prose():
    governed = {"parameter": "COMMUNITY_ENVIRONMENT_MATCH", "authority": "PREFERENCE", "action": "OFFER_PREFERENCE_ALTERNATIVE",
                "new_recommendation_count": 2, "requires_client_approval": True, "may_auto_change": False,
                "message": "Two measured alternatives.", "candidates": [{"canonical_facility_id": "A"}, {"canonical_facility_id": "B"}]}
    out = advise_with_ai(analysis={"suggestions": [governed]}, client_context={}, transport=lambda _: {
        "message": "100 excellent facilities!", "proposals": [{"parameter": governed["parameter"], "alternative": "Drop a MUST", "ask_client": "Waive care?"}]})
    assert out["message"] == governed["message"]
    assert out["proposals"] == [governed]

def test_one_or_duplicate_candidate_cannot_receive_ai_advice():
    for count, ids in [(1, ["A"]), (2, ["A", "A"])]:
        item = {"parameter": "size", "authority": "PREFERENCE", "action": "OFFER_PREFERENCE_ALTERNATIVE", "new_recommendation_count": count,
                "candidates": [{"canonical_facility_id": fid} for fid in ids]}
        out = advise_with_ai(analysis={"suggestions": [item]}, client_context={}, transport=lambda _: {"proposals": [{"parameter": "size"}]})
        assert not out["proposals"]
