from __future__ import annotations

from typing import Any, Dict

SCHEMA_VERSION = "oomnik-structured-profile/0.1"
VALID_STATES = {"EXPLICIT","NEGATED","UNCLEAR","UNKNOWN","CONFLICT"}
VALID_PROVENANCE = {"BUTTON","AI_EXTRACTED"}

def build_structured_profile(questionnaire_state: Dict[str,Any], semantic_result: Dict[str,Any]|None=None) -> Dict[str,Any]:
    semantic_result=semantic_result or {}
    fields: Dict[str,Any]={}
    patch=semantic_result.get("questionnaire_patch") if isinstance(semantic_result.get("questionnaire_patch"),dict) else {}
    statements=[s for s in semantic_result.get("statements") or [] if isinstance(s,dict)]
    by_key={}
    for s in statements:
        keys=[s.get("gap_key"),s.get("target_fact_key"),*(s.get("mapped_parameters") or [])]
        for key in keys:
            if key: by_key.setdefault(str(key),[]).append(s)
    for key,value in questionnaire_state.items():
        if key in {"notes","questionnaireCompletion","humanIntelligenceV2"} or value in ("",None,[],{}): continue
        fields[key]={"value":value,"state":"EXPLICIT","provenance":"BUTTON","quote":None,"source_question_key":key}
    conflicts=[]; out=[]; unprocessed=[]
    for key,value in patch.items():
        candidates=by_key.get(str(key),[])
        quote=next((str(s.get("raw_text")) for s in candidates if str(s.get("raw_text") or "").strip()),None)
        knowledge=next((str(s.get("knowledge_state") or "").upper() for s in candidates if s.get("knowledge_state")), "")
        state="NEGATED" if knowledge=="NEGATED" else "UNCLEAR" if knowledge in {"AMBIGUOUS","UNCLEAR"} else "EXPLICIT"
        extracted={"value":value,"state":state,"provenance":"AI_EXTRACTED","quote":quote,"source_question_key":None}
        if key in fields and fields[key]["value"] != value:
            fields[key]={"value":None,"state":"CONFLICT","provenance":"BUTTON","quote":quote,"source_question_key":key}
            conflicts.append({"field":key,"button_value":questionnaire_state.get(key),"ai_value":value,"quote":quote})
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
