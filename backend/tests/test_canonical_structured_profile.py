from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire

def test_button_ai_disagreement_becomes_conflict():
    profile=build_structured_profile(
        {"memoryStatus":"No memory problems","notes":"she has dementia"},
        {"questionnaire_patch":{"memoryStatus":"Dementia diagnosed"},"statements":[{"raw_text":"she has dementia","mapped_parameters":["memoryStatus"],"knowledge_state":"EXPLICIT"}]},
        family_text="she has dementia",
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
    profile=build_structured_profile({"memoryStatus":"No"},{"questionnaire_patch":{"memoryStatus":"Dementia diagnosed"},"statements":[{"raw_text":"dementia","mapped_parameters":["memoryStatus"],"knowledge_state":"KNOWN"}]},family_text="dementia")
    q=materialize_questionnaire(profile)
    assert "memoryStatus" not in q
    assert q["_structured_profile_authoritative"] is True

def test_semantically_equivalent_adl_wording_is_not_conflict():
    profile=build_structured_profile(
        {"assistanceLevel":"Needs assistance with bathing and dressing"},
        {"questionnaire_patch":{"assistanceLevel":"Help with bathing"},"statements":[{"raw_text":"He needs help with bathing","mapped_parameters":["assistanceLevel"],"knowledge_state":"EXPLICIT"}]},
        family_text="He needs help with bathing",
    )
    assert profile["conflicts"]==[]
    assert profile["fields"]["assistanceLevel"]["value"]=="Needs assistance with bathing and dressing"

def test_semantically_equivalent_memory_wording_is_not_conflict():
    profile=build_structured_profile(
        {"memoryStatus":"Mild forgetfulness"},
        {"questionnaire_patch":{"memoryStatus":"Mild memory issues"},"statements":[{"raw_text":"forgets appointments","mapped_parameters":["memoryStatus"],"knowledge_state":"EXPLICIT"}]},
        family_text="forgets appointments",
    )
    assert profile["conflicts"]==[]


def test_unknown_nested_fields_never_gain_authority_from_a_known_group():
    for group in ("languageProfile", "socialProfile", "familyProfile", "personalityProfile", "independenceProfile", "culturalProfile", "familyCultureProfile", "interestsProfile"):
        path=f"humanIntelligenceV2.{group}.inventedSafetyFact"
        profile=build_structured_profile({}, {"questionnaire_patch":{"humanIntelligenceV2":{group:{"inventedSafetyFact":True}}}, "statements":[{"raw_text":"family words","mapped_parameters":[path]}]}, family_text="family words")
        assert path not in profile["fields"]
        assert profile["out_of_schema"][0]["field"] == path
        assert "humanIntelligenceV2" not in materialize_questionnaire(profile)


def test_quote_requires_caller_supplied_source_and_literal_match():
    statement={"raw_text":"Budget is 9000", "mapped_parameters":["budget"]}
    packet={"questionnaire_patch":{"budget":9000}, "statements":[statement], "_family_text":"Budget is 9000"}
    for source in (None, "", "budget is 9000", "Budget  is 9000", "Budget is 3000"):
        profile=build_structured_profile({"budget":3000}, packet, family_text=source)
        assert materialize_questionnaire(profile)["budget"] == 3000
        assert not profile["conflicts"]
        assert profile["unprocessed"][0]["status"] == "UNPROCESSED"
        extracted=build_structured_profile({}, packet, family_text=source)
        assert "budget" not in materialize_questionnaire(extracted)


def test_materializer_rechecks_ai_schema_and_source():
    for path, quote, source in (("budget", "9000", "3000"), ("budget", "9000", None), ("humanIntelligenceV2.languageProfile.invented", "9000", "9000")):
        profile={"fields":{path:{"value":9000,"state":"EXPLICIT","provenance":"AI_EXTRACTED","quote":quote}},"family_text":source}
        assert set(materialize_questionnaire(profile)) == {"_structured_profile_authoritative","_structured_profile_schema_version"}


def test_valid_citation_is_selected_even_if_an_earlier_one_is_ungrounded():
    profile=build_structured_profile({}, {"questionnaire_patch":{"budget":9000},"statements":[{"raw_text":"invented quote","mapped_parameters":["budget"]},{"raw_text":"Budget is 9000","mapped_parameters":["budget"]}]},family_text="We agree. Budget is 9000.")
    assert materialize_questionnaire(profile)["budget"] == 9000
    assert profile["fields"]["budget"]["quote"] == "Budget is 9000"


def test_approved_nested_geography_and_language_fields_are_preserved():
    patch={"humanIntelligenceV2":{"languageProfile":{"preferredSpokenLanguage":"Hebrew"},"distanceProfile":{"referenceLocations":{"primaryCaregiverHome":"Henderson"}}}}
    paths=["humanIntelligenceV2.languageProfile.preferredSpokenLanguage", "humanIntelligenceV2.distanceProfile.referenceLocations.primaryCaregiverHome"]
    source="We speak Hebrew and the caregiver lives in Henderson."
    profile=build_structured_profile({}, {"questionnaire_patch":patch,"statements":[{"raw_text":source,"mapped_parameters":paths}]},family_text=source)
    assert materialize_questionnaire(profile)["humanIntelligenceV2"] == patch["humanIntelligenceV2"]


def test_unknown_nested_language_field_has_zero_authority():
    semantic={"questionnaire_patch":{"humanIntelligenceV2":{"languageProfile":{"inventedDecisionField":"Hebrew"}}},"statements":[{"mapped_parameters":["humanIntelligenceV2.languageProfile.inventedDecisionField"],"raw_text":"Hebrew"}]}
    profile=build_structured_profile({},semantic,family_text="Hebrew")
    assert "humanIntelligenceV2.languageProfile.inventedDecisionField" not in profile["fields"]
    assert any(x.get("field")=="humanIntelligenceV2.languageProfile.inventedDecisionField" and x.get("status")=="OUT_OF_SCHEMA" for x in profile["out_of_schema"])
    assert "inventedDecisionField" not in str(materialize_questionnaire(profile))


def test_ai_quote_without_family_source_never_materializes():
    path="humanIntelligenceV2.languageProfile.preferredSpokenLanguage"
    semantic={"questionnaire_patch":{"humanIntelligenceV2":{"languageProfile":{"preferredSpokenLanguage":"Hebrew"}}},"statements":[{"mapped_parameters":[path],"raw_text":"Hebrew"}]}
    profile=build_structured_profile({},semantic)
    assert profile["fields"][path]["state"]=="UNCLEAR"
    assert "preferredSpokenLanguage" not in str(materialize_questionnaire(profile))
