from __future__ import annotations

from typing import Any, Dict

SCHEMA_VERSION = "oomnik-structured-profile/0.1"
ARCHITECTURE_CUTOVER_VERSION = "2026-10-01"
VALID_STATES = {"EXPLICIT","NEGATED","UNCLEAR","UNKNOWN","CONFLICT"}
VALID_PROVENANCE = {"BUTTON","AI_EXTRACTED"}

def _flatten(data: Dict[str,Any], prefix: str = "") -> Dict[str,Any]:
    out={}
    for key,value in data.items():
        path=f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value,dict): out.update(_flatten(value,path))
        elif value not in ("",None,[],{}): out[path]=value
    return out


def _canonical_value(key: str, value: Any) -> Any:
    if isinstance(value,list):
        return sorted({_canonical_value(key,v) for v in value}, key=str)
    text=" ".join(str(value or "").strip().lower().replace("|",",").split())
    if key.endswith("assistanceLevel"):
        tokens=set()
        if "bathing" in text: tokens.add("BATHING")
        if "dressing" in text: tokens.add("DRESSING")
        if "medication" in text: tokens.add("MEDICATION")
        if "24/7" in text or "24 7" in text: tokens.add("SUPERVISION_24_7")
        if "independent" in text and not tokens: tokens.add("INDEPENDENT")
        return tuple(sorted(tokens)) if tokens else text
    if key.endswith("memoryStatus"):
        if any(x in text for x in ("no memory","no dementia","none")): return "NONE"
        if any(x in text for x in ("mild forget","mild memory")): return "MILD"
        if any(x in text for x in ("significant","dementia","alzheimer","memory care")): return "SIGNIFICANT"
    return text

def _compatible_values(key: str, button: Any, ai: Any) -> bool:
    b=_canonical_value(key,button); a=_canonical_value(key,ai)
    if b==a: return True
    if key.endswith("assistanceLevel") and isinstance(b,tuple) and isinstance(a,tuple):
        return bool(b) and bool(a) and (set(a).issubset(set(b)) or set(b).issubset(set(a)))
    return False

# Approved schema (docs/architecture/CANONICAL_STRUCTURED_PROFILE_CONTRACT.md). The
# interpreter may write only these paths; anything else is OUT_OF_SCHEMA with zero weight.
SCHEMA_FIELDS = frozenset({
    "relationship", "gender", "ageGroup", "coupleAssistance", "moveTiming", "careSearchApproach",
    "assistanceLevel", "memoryStatus", "budget", "medicareStatus", "medicaidStatus",
    "searchState", "locationImportant", "referenceLocationType", "referenceLocationValue", "referenceAddress",
    "maximumDistanceMiles", "customDistanceMiles", "approvedSearchRadiusMiles", "distanceFromFamily",
    "nearbyPlaces", "nearbyPlacesImportance", "personalDestinations", "futureCarePreference",
    "happinessPreferences", "moveLossConcerns", "otherInterests", "parkingRequirement", "parkingVehicleCount",
    *(f"medicalCareProfile.{k}" for k in ("hasOngoingMedicalNeeds", "needs", "mobilityMethod", "transferAssistance", "recentFalls", "dialysisFrequency", "dialysisCenter", "dialysisTransportation", "oxygenUse", "woundCareFrequency", "complexConditionDetails", "physicianCoordination")),
    *(f"humanIntelligenceV2.transitionRiskProfile.{k}" for k in ("biggestFear", "attitudeTowardMove", "previousMoves", "bereavementStatus", "lonelinessRisk", "socialIsolationConcern", "recentHospitalization", "hospitalizationRecency", "postHospitalRehabNeed", "wanderingConcerns")),
    *(f"humanIntelligenceV2.distanceProfile.{k}" for k in ("referenceLocations", "driveTimes", "familyVisitExpectation", "familyGeographyModel", "emotionalDistanceFactors", "optimizationStrategy")),
    *(f"humanIntelligenceV2.futureCareProfile.{k}" for k in ("agingInPlaceImportance", "avoidFutureMovesPreference", "continuumOfCarePreference", "secureMemoryNeighborhoodNeed", "familiarLanguageRequirement")),
    "humanIntelligenceV2.communityPreferenceProfile.preferredEnvironment",
    "humanIntelligenceV2.interestsProfile",
    "humanIntelligenceV2.foodProfile.dietaryPreferences",
})
# Closed leaf allowlist only. A legal parent object never authorizes arbitrary child keys.
# Every decision-capable AI path must be named explicitly here.
SCHEMA_FIELDS = frozenset(set(SCHEMA_FIELDS) | {
    *(f"humanIntelligenceV2.socialProfile.{k}" for k in ("livingAloneDuration","socialInteractionFrequency","newFriendsImportance","hobbyParticipation","preferredSocialIntensity")),
    *(f"humanIntelligenceV2.familyProfile.{k}" for k in ("involvedFamilyMembers","visitFrequencyExpectation","grandchildrenPresence","grandchildrenImportance","familyDecisionDynamics","emergencySupportNetwork","coupleStayTogetherPreference","widowStatus","lossTiming","socialActivityChangeSinceLoss","socialInteractionNeed","temporarySeparationAcceptance","griefSupportInterest")),
    *(f"humanIntelligenceV2.personalityProfile.{k}" for k in ("communitySizePreference",)),
    *(f"humanIntelligenceV2.independenceProfile.{k}" for k in ("mobilityMethod","transferAssistance","recentFalls")),
    *(f"humanIntelligenceV2.culturalProfile.{k}" for k in ("religionImportance","faithTraditions","religiousSupportNeeds","kosherRequirements","synagogueChurchAccess","holidayCelebrations","culturalIdentity","israeliJewishCommunityPreference","whatFeelsLikeHome","worshipAccessRequirement","jewishProgrammingImportance","churchAccessRequirement","christianServiceRequirement","halalMealsRequirement","prayerFacilityRequirement")),
    *(f"humanIntelligenceV2.languageProfile.{k}" for k in ("preferredSpokenLanguage","nativeLanguage","medicalDiscussionLanguage","socialInteractionLanguage","languageNeedScope","languagesUnderstood","familyLanguages","bilingualStaffRequired")),
    *(f"humanIntelligenceV2.familyCultureProfile.{k}" for k in ("involvementExpectation","decisionRole")),
})

def in_schema(path: str) -> bool:
    return path in SCHEMA_FIELDS

def _normalized_text(text: Any) -> str:
    return " ".join(str(text or "").lower().split())


def build_structured_profile(questionnaire_state: Dict[str,Any], semantic_result: Dict[str,Any]|None=None, family_text: str|None=None) -> Dict[str,Any]:
    """family_text: the family's own words the interpreter read. When given, an
    AI_EXTRACTED field must carry an exact quote found in it (contract rule)."""
    semantic_result=semantic_result or {}
    fields: Dict[str,Any]={}
    raw_patch=semantic_result.get("questionnaire_patch") if isinstance(semantic_result.get("questionnaire_patch"),dict) else {}
    patch=_flatten(raw_patch)
    statements=[s for s in semantic_result.get("statements") or [] if isinstance(s,dict)]
    by_key={}
    for s in statements:
        keys=[s.get("gap_key"),s.get("target_fact_key"),*(s.get("mapped_parameters") or [])]
        for key in keys:
            if key: by_key.setdefault(str(key),[]).append(s)
    button_state={k:v for k,v in questionnaire_state.items() if k not in {"notes","questionnaireCompletion"}}
    flattened_buttons=_flatten(button_state)
    for key,value in flattened_buttons.items():
        fields[key]={"value":value,"state":"EXPLICIT","provenance":"BUTTON","quote":None,"source_question_key":key}
    conflicts=[]; out=[]; unprocessed=[]
    source_text=_normalized_text(family_text if family_text is not None else semantic_result.get("_family_text"))
    for key,value in patch.items():
        candidates=by_key.get(str(key),[])
        quote=next((str(s.get("raw_text")) for s in candidates if str(s.get("raw_text") or "").strip()),None)
        if not in_schema(str(key)):
            # Contract: no canonical field -> OUT_OF_SCHEMA, zero decision weight.
            out.append({"field":key,"text":quote or str(value),"quote":quote,"reason":"NO_CANONICAL_FIELD","status":"OUT_OF_SCHEMA"})
            continue
        knowledge=next((str(s.get("knowledge_state") or "").upper() for s in candidates if s.get("knowledge_state")), "")
        state="NEGATED" if knowledge=="NEGATED" else "UNCLEAR" if knowledge in {"AMBIGUOUS","UNCLEAR"} else "EXPLICIT"
        # Contract: AI_EXTRACTED requires an exact quote present in the family text.
        # Without one the value is UNCLEAR and never materialized.
        quote_ok=bool(source_text) and bool(quote) and _normalized_text(quote) in source_text
        if not quote_ok:
            state="UNCLEAR"
        extracted={"value":value,"state":state,"provenance":"AI_EXTRACTED","quote":quote,"source_question_key":None,**({} if quote_ok else {"unverified_reason":"NO_EXACT_QUOTE_IN_FAMILY_TEXT"})}
        if key in fields and not quote_ok:
            continue  # an unquoted AI value can neither override nor contest a button answer
        if key in fields and not _compatible_values(key, fields[key]["value"], value):
            fields[key]={"value":None,"state":"CONFLICT","provenance":"BUTTON","quote":quote,"source_question_key":key}
            conflicts.append({"field":key,"button_value":flattened_buttons.get(key),"ai_value":value,"quote":quote})
        elif key in fields:
            pass
        else:
            fields[key]=extracted
    known=set(fields)|set(patch)
    for s in statements:
        mapped=[str(x) for x in s.get("mapped_parameters") or [] if str(x)]
        raw=str(s.get("raw_text") or "").strip()
        if raw and not mapped and str(s.get("status") or "").upper()!="ASKED":
            out.append({"text":raw,"quote":raw,"reason":"NO_CANONICAL_FIELD","status":"OUT_OF_SCHEMA"})
    if semantic_result.get("_unprocessed_narrative"):
        unprocessed.append({"text":str(semantic_result.get("_unprocessed_narrative")),"status":"UNPROCESSED"})
    return {"schema_version":SCHEMA_VERSION,"profile_status":"DRAFT","fields":fields,"out_of_schema":out,"conflicts":conflicts,"unprocessed":unprocessed}


def materialize_questionnaire(profile: Dict[str,Any]) -> Dict[str,Any]:
    """Reconstruct only confirmed structured facts; conflicts/unclear never become decision input."""
    out={}
    for path,item in (profile.get("fields") or {}).items():
        if not isinstance(item,dict) or item.get("state") not in {"EXPLICIT","NEGATED"}: continue
        target=out; parts=str(path).split(".")
        for part in parts[:-1]: target=target.setdefault(part,{})
        target[parts[-1]]=item.get("value")
    out["_structured_profile_authoritative"]=True
    out["_structured_profile_schema_version"]=profile.get("schema_version")
    return out
