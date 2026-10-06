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


def test_dialogue_reads_question_and_returns_at_most_three_distinct_governed_choices():
    captured = {}
    suggestions = []
    for i in range(5):
        suggestions.append({"parameter": f"nth-{i}", "authority": "PREFERENCE", "action": "OFFER_PREFERENCE_ALTERNATIVE",
            "new_recommendation_count": 2, "requires_client_approval": True, "may_auto_change": False,
            "message": f"Measured option {i} adds 2 communities.",
            "candidates": [{"canonical_facility_id": f"{i}-A"}, {"canonical_facility_id": f"{i}-B"}]})
    def transport(prompt):
        captured.update(prompt)
        return {"mode": "COMPARE_OPTIONS", "message": "999 new places and waive safety!",
                "proposals": [{"parameter": s["parameter"]} for s in suggestions]}
    out = advise_with_ai(analysis={"suggestions": suggestions}, client_context={},
                         client_message="What are my best choices?", transport=transport)
    assert captured["client_message"] == "What are my best choices?"
    assert len(out["proposals"]) == 3
    assert "999" not in out["message"] and "waive safety" not in out["message"]
    assert out["follow_up"] == "Which of these changes would you feel comfortable exploring?"
    assert out["profile_mutated"] is False


def test_no_verified_two_option_gain_is_explained_in_dialogue_without_inventing_a_change():
    out = advise_with_ai(analysis={"suggestions": [], "preference_analysis": {"parameters": [
        {"parameter": "quiet", "label": "Quiet evenings", "unknown_count": 7, "new_recommendation_count": 0}]}},
        client_context={}, client_message="What about quiet evenings?",
        transport=lambda _: {"mode": "EXPLAIN_EVIDENCE", "discussion_parameters": ["quiet"], "proposals": []})
    assert "Quiet evenings" in out["message"] and "7" in out["message"]
    assert not out["proposals"]


def test_live_advisor_uses_its_own_schema_instead_of_the_questionnaire_interpreter(monkeypatch):
    import app.services.oomniker_ai as advisor
    captured = {}
    class Response:
        ok = True
        def json(self):
            return {"output_text": '{"mode":"EXPLAIN_EVIDENCE","discussion_parameters":[],"proposals":[]}'}
    def request(url, headers, payload):
        captured.update(payload)
        return Response()
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_URL", "https://example.org/responses")
    monkeypatch.setenv("OPTIME_SEMANTIC_AI_MODEL", "configured-model")
    monkeypatch.setattr(advisor, "_request_with_retry", request)
    out = advisor._advisor_transport({"governed_analysis": {}, "client_message": "Why?"})
    schema = captured["text"]["format"]
    assert schema["name"] == "oomniker_advisor"
    assert set(schema["schema"]["properties"]) == {"mode", "discussion_parameters", "proposals"}
    assert "questionnaire_patch_fields" not in schema["schema"]["properties"]
    assert out["mode"] == "EXPLAIN_EVIDENCE"


def test_invalid_ai_packet_is_unavailable_and_does_not_apply_a_change():
    out = advise_with_ai(analysis={}, client_context={}, transport=lambda _: ["invalid"])
    assert out["status"] == "AI_UNAVAILABLE"
    assert out["proposals"] == []


def test_tradeoff_explains_only_the_selected_measured_preference():
    suggestion = {"parameter": "DINING_EXPERIENCE", "label": "Dining experience", "authority": "PREFERENCE",
        "action": "OFFER_PREFERENCE_ALTERNATIVE", "change_kind": "WAIVE_NTH", "new_recommendation_count": 2,
        "requires_client_approval": True, "may_auto_change": False, "message": "Two measured options.",
        "candidates": [{"canonical_facility_id": "A"}, {"canonical_facility_id": "B"}]}
    out = advise_with_ai(analysis={"suggestions": [suggestion]}, client_context={}, client_message="What would I give up?",
        transport=lambda _: {"mode": "EXPLAIN_TRADEOFF", "proposals": [{"parameter": "DINING_EXPERIENCE"}]})
    assert "Dining experience would stop influencing the recommendation order" in out["message"]
    assert "required conditions stay in force" in out["message"]


def test_resolved_lever_explains_other_unknown_preferences_without_promising_a_gain():
    analysis = {"suggestions": [], "preference_analysis": {"parameters": [
        {"parameter": "COMMUNITY_ENVIRONMENT_MATCH", "label": "Community size", "unknown_count": 0,
         "new_recommendation_count": 3, "unresolved_other_preferences": ["Low sodium", "Familiar routines"],
         "proposal_blockers": ["OTHER_DYNAMIC_PREFERENCES_UNRESOLVED"]}]}}
    out = advise_with_ai(analysis=analysis, client_context={}, client_message="Can a bigger place help?",
        transport=lambda _: {"mode": "EXPLAIN_EVIDENCE", "discussion_parameters": ["COMMUNITY_ENVIRONMENT_MATCH"], "proposals": []})
    assert "Low sodium" in out["message"] and "Familiar routines" in out["message"]
    assert "0 communities still need evidence" not in out["message"]
    assert "3 additional" not in out["message"]
    assert not out["proposals"] and not out["profile_mutated"]
