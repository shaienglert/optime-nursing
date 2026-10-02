from __future__ import annotations
from typing import Any
from app.services.facility_parameter_service import get_canonical_facility_index, get_facility_parameter_table

CORE=("adl_support","medication_support","memory_care","current_price","languages","transportation","dining","rehab","pt_ot")

def facility_intelligence_readiness()->dict[str,Any]:
    index=get_canonical_facility_index()
    facilities=[]; totals={"facilities":0,"core_known":0,"core_unknown":0,"license_verified":0}
    for cid,row in index.items():
        table=get_facility_parameter_table(cid,priority_parameter_ids=list(CORE),include_evidence_records=False)
        values={str(x.get("parameter_id")):x for x in table.get("rows") or []}
        known=[k for k in CORE if str((values.get(k) or {}).get("raw_value") or "UNKNOWN").upper()!="UNKNOWN"]
        unknown=[k for k in CORE if k not in known]
        license_verified=(str(row.get("canonical_type") or "").upper()=="INDEPENDENT_LIVING" or (str(row.get("license_status") or "").upper()=="ACTIVE" and str(row.get("nevada_license_id") or "").upper() not in {"","UNKNOWN"}))
        facilities.append({"canonical_facility_id":cid,"facility_name":row.get("facility_name") or row.get("name"),"known_core":known,"unknown_core":unknown,"core_coverage_pct":round(100*len(known)/len(CORE),1),"license_verified_or_not_required":license_verified,"synthetic_pilot":row.get("synthetic_pilot") is True})
        totals["facilities"]+=1; totals["core_known"]+=len(known); totals["core_unknown"]+=len(unknown); totals["license_verified"]+=int(license_verified)
    denom=max(1,totals["facilities"]*len(CORE))
    totals["core_coverage_pct"]=round(100*totals["core_known"]/denom,1)
    return {"status":"FACILITY_INTELLIGENCE_READINESS","core_parameters":list(CORE),"summary":totals,"facilities":facilities}
