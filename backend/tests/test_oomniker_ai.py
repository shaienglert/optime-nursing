from app.services.oomniker_ai import advise_with_ai

def test_ai_cannot_propose_parameter_outside_governed_analysis():
    analysis={"suggestions":[{"parameter":"music_lessons","authority":"CLIENT_MUST","additional_options_if_relaxed":8}],"system_must_immutable":["secure_memory"]}
    packet={"message":"Music lessons narrow the choices.","proposals":[{"parameter":"secure_memory","alternative":"drop it","ask_client":"waive?"},{"parameter":"music_lessons","alternative":"private teacher","ask_client":"Would a private teacher preserve the goal?"}]}
    out=advise_with_ai(analysis=analysis,client_context={},transport=lambda _:packet)
    assert [x["parameter"] for x in out["proposals"]]==["music_lessons"]
    assert out["proposals"][0]["requires_client_approval"] is True
    assert out["profile_mutated"] is False
