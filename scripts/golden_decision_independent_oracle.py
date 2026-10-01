"""Independent golden oracle: frozen pilot facts only; never imports decision engine."""
import base64, gzip, json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PILOT=ROOT/"database"/"synthetic_pilot"
CONTRACT=ROOT/"backend"/"gold_examples"/"oomnik_golden_decision_v01.json"\nREFERENCE_POINTS={"LAS_VEGAS":(36.1699,-115.1398),"HENDERSON":(36.0395,-114.9817),"SUMMERLIN":(36.1672,-115.3322)}

def load(name):
    raw=json.loads(gzip.decompress(base64.b64decode((PILOT/name).read_text())))
    return raw if isinstance(raw,list) else raw[next(k for k,v in raw.items() if isinstance(v,list))]

def catalog():
    facilities={r["canonical_id"]:r for r in load("facility_universe.json.gz.b64")}
    facts={}
    for r in load("facility_parameter_evidence.json.gz.b64"):
        facts.setdefault(r["canonical_facility_id"],{})[r["parameter_id"]]=r.get("value")
    return facilities,facts

def distance_miles(a,b):\n    lat1,lon1=map(math.radians,a); lat2,lon2=map(math.radians,b)\n    h=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2\n    return 3958.7613*2*math.asin(math.sqrt(h))\n\ndef evaluate(s):
    facilities,facts=catalog(); p=s["profile"]; e=s["expected"]
    required=p.get("required",[]); budget=p.get("budget")
    ceiling=e.get("max_price", budget*1.10 if isinstance(budget,(int,float)) else None)
    allowed=set(e.get("allowed_archetypes",[])); never=set(e.get("never_archetypes",[]))\n    reference=REFERENCE_POINTS.get(p.get("location")); radius=p.get("radius_miles")
    eligible=[]; pending=[]; excluded=[]
    for fid,facility in facilities.items():
        ev=facts.get(fid,{}); archetype=facility.get("synthetic_archetype")
        fail=[]; unknown=[]
        if allowed and archetype not in allowed: fail.append("CARE_NOT_ALLOWED")
        if archetype in never: fail.append("CARE_FORBIDDEN")
        for key in required:
            if key in {"pets_allowed","vegetarian"}: unknown.append(key); continue
            value=str(ev.get(key,"UNKNOWN")).upper()
            if value=="NO": fail.append(key)
            elif value!="YES": unknown.append(key)
        price=ev.get("current_price")
        if isinstance(ceiling,(int,float)):
            if not isinstance(price,(int,float)): unknown.append("current_price")
            elif price>ceiling: fail.append("PRICE_ABOVE_TOLERANCE")
        if e.get("accepts_couples") is True and facility.get("accepts_couples") is not True:
            fail.append("COUPLE_NOT_ACCEPTED")
        row={"id":fid,"archetype":archetype,"price":price,"distance_miles":round(distance,2) if distance is not None else None,"availability":ev.get("current_availability"),"fail":fail,"unknown":unknown}
        (excluded if fail else pending if unknown else eligible).append(row)
    def order(r):
        over=isinstance(budget,(int,float)) and isinstance(r["price"],(int,float)) and r["price"]>budget
        return (over,r["price"] if isinstance(r["price"],(int,float)) else 10**9,r["id"])
    eligible.sort(key=order); pending.sort(key=order)
    return {"id":s["id"],"counts":{"eligible":len(eligible),"pending":len(pending),"excluded":len(excluded)},
            "top10_expected_candidate_ids":[r["id"] for r in eligible[:10]],"eligible":eligible,"pending":pending}

def main():
    contract=json.loads(CONTRACT.read_text())
    print(json.dumps({"source":"FROZEN_SYNTHETIC_PILOT_NOT_ENGINE","scenarios":[evaluate(s) for s in contract["scenarios"]]},indent=2))

if __name__=="__main__": main()
