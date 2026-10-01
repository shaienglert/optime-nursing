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
    # The schema path is medicalCareProfile.oxygenUse (contract); a bare "oxygenUse" is
    # not a canonical field and is now OUT_OF_SCHEMA.
    profile=build_structured_profile({},{"questionnaire_patch":{"medicalCareProfile":{"oxygenUse":"At night"}},"statements":[{"raw_text":"uses oxygen at night","mapped_parameters":["medicalCareProfile.oxygenUse"],"knowledge_state":"EXPLICIT"}]},family_text="Mom uses oxygen at night.")
    assert profile["fields"]["medicalCareProfile.oxygenUse"]["provenance"]=="AI_EXTRACTED"
    assert profile["fields"]["medicalCareProfile.oxygenUse"]["quote"]=="uses oxygen at night"


def test_unknown_ai_field_is_out_of_schema_and_never_decision_input():
    profile=build_structured_profile({},{"questionnaire_patch":{"scoringEngine":{"boost":"10"},"facilityMustBeFancy":"Yes"},"statements":[]})
    assert not profile["fields"]
    assert {o["field"] for o in profile["out_of_schema"]}=={"scoringEngine.boost","facilityMustBeFancy"}
    assert set(materialize_questionnaire(profile))=={"_structured_profile_authoritative","_structured_profile_schema_version"}


def test_ai_field_without_an_exact_quote_is_unclear_and_not_materialized():
    profile=build_structured_profile({},{"questionnaire_patch":{"medicaidStatus":"Approved"},"statements":[{"raw_text":"she was approved for medicaid","mapped_parameters":["medicaidStatus"],"knowledge_state":"KNOWN"}]},family_text="We are still waiting to hear about Medicaid.")
    assert profile["fields"]["medicaidStatus"]["state"]=="UNCLEAR"
    assert "medicaidStatus" not in materialize_questionnaire(profile)
    unquoted=build_structured_profile({"memoryStatus":"No"},{"questionnaire_patch":{"memoryStatus":"Dementia diagnosed"},"statements":[]})
    assert unquoted["fields"]["memoryStatus"]["provenance"]=="BUTTON" and not unquoted["conflicts"]


def test_nested_human_intelligence_fields_are_not_dropped():
    profile=build_structured_profile({"humanIntelligenceV2":{"foodProfile":{"dietaryPreferences":["Kosher"]},"languageProfile":{"preferredSpokenLanguage":"Hebrew"}}})
    assert profile["fields"]["humanIntelligenceV2.foodProfile.dietaryPreferences"]["value"]==["Kosher"]
    assert profile["fields"]["humanIntelligenceV2.languageProfile.preferredSpokenLanguage"]["value"]=="Hebrew"


def test_materializer_excludes_conflict_from_decision_input():
    profile=build_structured_profile({"memoryStatus":"No"},{"questionnaire_patch":{"memoryStatus":"Dementia diagnosed"},"statements":[{"raw_text":"dementia","mapped_parameters":["memoryStatus"],"knowledge_state":"KNOWN"}]})
    q=materialize_questionnaire(profile)
    assert "memoryStatus" not in q
    assert q["_structured_profile_authoritative"] is True

def test_semantically_equivalent_adl_wording_is_not_conflict():
    profile=build_structured_profile(
        {"assistanceLevel":"Needs assistance with bathing and dressing"},
        {"questionnaire_patch":{"assistanceLevel":"Help with bathing"},"statements":[{"raw_text":"He needs help with bathing","mapped_parameters":["assistanceLevel"],"knowledge_state":"EXPLICIT"}]},
    )
    assert profile["conflicts"]==[]
    assert profile["fields"]["assistanceLevel"]["value"]=="Needs assistance with bathing and dressing"

def test_semantically_equivalent_memory_wording_is_not_conflict():
    profile=build_structured_profile(
        {"memoryStatus":"Mild forgetfulness"},
        {"questionnaire_patch":{"memoryStatus":"Mild memory issues"},"statements":[{"raw_text":"forgets appointments","mapped_parameters":["memoryStatus"],"knowledge_state":"EXPLICIT"}]},
    )
    assert profile["conflicts"]==[]
