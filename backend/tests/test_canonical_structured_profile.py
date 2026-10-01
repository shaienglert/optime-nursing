from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire

def test_button_ai_disagreement_becomes_conflict():
    profile=build_structured_profile(
        {"memoryStatus":"No memory problems","notes":"she has dementia"},
        {"questionnaire_patch":{"memoryStatus":"Dementia diagnosed"},"statements":[{"raw_text":"she has dementia","mapped_parameters":["memoryStatus"],"knowledge_state":"EXPLICIT"}]},
    )
    assert profile["fields"]["memoryStatus"]["state"]=="CONFLICT"
    assert profile["conflicts"][0]["button_value"]=="No memory problems"
    assert profile["conflicts"][0]["ai_value"]=="Dementia diagnosed"

def test_unmapped_statement_is_out_of_schema_not_hidden_must():
    profile=build_structured_profile({},{"statements":[{"raw_text":"room with a mountain view","mapped_parameters":[],"status":"OBSERVED"}]})
    assert profile["out_of_schema"]==[{"text":"room with a mountain view","quote":"room with a mountain view","reason":"NO_CANONICAL_FIELD","status":"OUT_OF_SCHEMA"}]

def test_ai_extracted_fact_keeps_exact_quote():
    profile=build_structured_profile({},{"questionnaire_patch":{"oxygenUse":"At night"},"statements":[{"raw_text":"uses oxygen at night","mapped_parameters":["oxygenUse"],"knowledge_state":"EXPLICIT"}]})
    assert profile["fields"]["oxygenUse"]["provenance"]=="AI_EXTRACTED"
    assert profile["fields"]["oxygenUse"]["quote"]=="uses oxygen at night"


def test_nested_human_intelligence_fields_are_not_dropped():
    profile=build_structured_profile({"humanIntelligenceV2":{"foodProfile":{"dietaryPreferences":["Kosher"]},"languageProfile":{"preferredSpokenLanguage":"Hebrew"}}})
    assert profile["fields"]["humanIntelligenceV2.foodProfile.dietaryPreferences"]["value"]==["Kosher"]
    assert profile["fields"]["humanIntelligenceV2.languageProfile.preferredSpokenLanguage"]["value"]=="Hebrew"


def test_materializer_excludes_conflict_from_decision_input():
    profile=build_structured_profile({"memoryStatus":"No"},{"questionnaire_patch":{"memoryStatus":"Dementia diagnosed"},"statements":[{"raw_text":"dementia","mapped_parameters":["memoryStatus"],"knowledge_state":"KNOWN"}]})
    q=materialize_questionnaire(profile)
    assert "memoryStatus" not in q
    assert q["_structured_profile_authoritative"] is True
