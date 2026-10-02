"""Live shadow gate: legacy narrative profile vs AI->Structured Profile->deterministic profile.

Legacy = the regex narrative mapper (decision_engine_core on the raw state + story), which
the cutover removed from the decision path. Structured = the live interpreter's patch,
validated against the family's own text (exact quotes required), materialized, then the
deterministic profile. A critical need the regex found that the structured road loses
is blocking.
"""
import json
from scripts.pilot_acceptance.cases import CASES
from app.services.semantic_intent_ai import interpret_client_intent_with_ai
from app.services.canonical_structured_profile import build_structured_profile, materialize_questionnaire
from app.services.patient_decision_engine import build_patient_needs_profile
from app.services.decision_engine_core import build_patient_needs_profile as legacy_regex_profile
from app.database import engine
from app.models.agent_execution import AgentKnowledgeReportSnapshot

def needs(profile):
    return {str(x.get("parameter_id")):str(x.get("requirement_level"))+"="+str(x.get("desired_value")) for x in profile.get("needs") or [] if isinstance(x,dict)}

def main():
    import app.main  # registers all ORM models
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    report=[]; blocking=0
    for key,case in CASES.items():
        q=case["questionnaire"]; text=case["query"]
        legacy=legacy_regex_profile(q,text)
        semantic=interpret_client_intent_with_ai(user_text=text,questionnaire_state=q)
        structured=build_structured_profile(q,semantic,family_text=text)
        materialized=materialize_questionnaire(structured)
        new=build_patient_needs_profile(materialized,"")
        a,b=needs(legacy),needs(new)
        missing={k:v for k,v in a.items() if k not in b and v.startswith(("REQUIRED=","HIGH="))}
        conflicts=structured.get("conflicts") or []
        ok=not missing and not conflicts
        if not ok: blocking+=1
        unquoted=[k for k,v in (structured.get("fields") or {}).items() if v.get("unverified_reason")]
        report.append({"case":key,"pass":ok,"missing_critical_needs":missing,"conflicts":conflicts,"unquoted_ai_fields":unquoted,"legacy_need_count":len(a),"structured_need_count":len(b)})
    print(json.dumps({"blocking":blocking,"cases":report},indent=2))
    raise SystemExit(0 if blocking==0 else 1)

if __name__=="__main__": main()
