from app.database import Base, engine
"""Live shadow gate: legacy narrative profile vs AI->Structured Profile->deterministic profile."""
import json
from scripts.pilot_acceptance.cases import CASES
from app.services.semantic_intent_ai import interpret_client_intent_with_ai
from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire
from app.services.patient_decision_engine import build_patient_needs_profile

def needs(profile):
    return {str(x.get("parameter_id")):str(x.get("requirement_level"))+"="+str(x.get("desired_value")) for x in profile.get("needs") or [] if isinstance(x,dict)}

def main():
    Base.metadata.create_all(bind=engine)
    report=[]; blocking=0
    for key,case in CASES.items():
        q=case["questionnaire"]; text=case["query"]
        legacy=build_patient_needs_profile(q,text)
        semantic=interpret_client_intent_with_ai(user_text=text,questionnaire_state=q)
        structured=build_structured_profile(q,semantic)
        materialized=materialize_questionnaire(structured)
        new=build_patient_needs_profile(materialized,"")
        a,b=needs(legacy),needs(new)
        missing={k:v for k,v in a.items() if k not in b and v.startswith(("REQUIRED=","HIGH="))}
        conflicts=structured.get("conflicts") or []
        ok=not missing and not conflicts
        if not ok: blocking+=1
        report.append({"case":key,"pass":ok,"missing_critical_needs":missing,"conflicts":conflicts,"legacy_need_count":len(a),"structured_need_count":len(b)})
    print(json.dumps({"blocking":blocking,"cases":report},indent=2))
    raise SystemExit(0 if blocking==0 else 1)

if __name__=="__main__": main()
