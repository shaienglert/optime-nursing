import json,re
from pathlib import Path
from app.services.semantic_intent_ai import interpret_client_intent_with_ai
from app.database import engine
from app.models.agent_execution import AgentKnowledgeReportSnapshot

ROOT=Path(__file__).resolve().parents[2]
CASES=json.loads((ROOT/"backend/gold_examples/oomnik_golden_interpreter_v01.json").read_text())["cases"]

def run():
    import app.main  # registers all ORM models
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    results=[]
    for case in CASES:
        baseline={"referenceLocationValue":"Las Vegas, Nevada","budget":6000,"questionnaireCompletion":{"complete":False}}
        try:
            out=interpret_client_intent_with_ai(user_text=case["text"],questionnaire_state=baseline)
        except Exception as exc:
            results.append({"id":case["id"],"pass":False,"errors":[str(exc)]})
            continue
        blob=json.dumps(out.get("questionnaire_patch") or {},ensure_ascii=False)
        low=blob.lower()
        errors=[]
        for term in case.get("must_not_contain",[]):
            if term.lower() in low: errors.append("forbidden:"+term)
        any_terms=case.get("must_contain_any",[])
        if any_terms and not any(term.lower() in (blob+" "+json.dumps(out.get("statements") or [],ensure_ascii=False)).lower() for term in any_terms):
            errors.append("missing_any:"+"/".join(any_terms))
        if case.get("numeric_range"):
            nums=[int(x.replace(",","")) for x in re.findall(r"\d[\d,]*",blob)]
            lo,hi=case["numeric_range"]
            if nums and any(n>hi*10 for n in nums): errors.append("numeric_concatenation")
        results.append({"id":case["id"],"pass":not errors,"errors":errors})
    return results

if __name__=="__main__":
    results=run(); print(json.dumps(results,indent=2)); raise SystemExit(0 if all(x["pass"] for x in results) else 1)
