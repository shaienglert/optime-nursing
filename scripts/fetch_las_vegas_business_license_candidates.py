from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LAYER_URL = "https://mapdata.lasvegasnevada.gov/clvgis/rest/services/DevelopmentServices/Business_Licenses/MapServer/0"
QUERY_URL = LAYER_URL + "/query"
UA = "Mozilla/5.0 OPTIME-Nursing/1.0 (+facility-universe-research)"
WHERE = " OR ".join([
    "UPPER(LICENSECATDESC) LIKE '%APARTMENT HOUSE%'",
    "UPPER(LICENSECATDESC) LIKE '%RESIDENTIAL HOME CARE PROVIDER%'",
    "UPPER(LICENSECATDESC) LIKE '%SPECIAL CARE FACILITY%'",
    "UPPER(LICENSECATDESC) LIKE '%ADULT DAY CARE%'",
])
OUT_FIELDS = [
    "OBJECTID","LICENSENO","LICENSETYPE","LICENSETYPEDESC","CATEGORY","LICENSECATDESC",
    "LICSTATUSCODE","LICSTATUS","LICENSEDTTM","ISSDTTM","EXPDTTM","INACTVDTTM","INACTVFLAG",
    "BUS_NAME","DBANAME","BUS_TYPE","TYPEOFBUS","CAPACITY","BUS_ADDRESS","BUS_CITY","BUS_STATE",
    "BUS_ZIP","BUS_CITY_ST_ZIP","LOC_ADDRESS","WITHINCITYLIMIT","CNTCTPHONE","CNTCTEMAIL","NAICS_GROUP",
]
SENIOR_RE = re.compile(r"\b(senior|seniors|retirement|55\s*\+|active adult|independent living)\b", re.I)


def get_json(url: str, params: dict[str, str]) -> dict:
    req = Request(url + "?" + urlencode(params), headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(json.dumps(payload["error"], sort_keys=True))
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/nevada/raw/las_vegas_business_license_senior_candidates.json")
    ap.add_argument("--report", default="reports/LAS_VEGAS_BUSINESS_LICENSE_CANDIDATES.json")
    args = ap.parse_args()

    meta = get_json(LAYER_URL, {"f":"json"})
    max_count = int(meta.get("maxRecordCount") or 1000)
    fields = {f.get("name") for f in meta.get("fields") or []}
    missing = sorted(set(OUT_FIELDS) - fields)
    if missing:
        raise RuntimeError(f"Official Las Vegas business-license schema missing expected fields: {missing}")
    total = int(get_json(QUERY_URL, {"where":WHERE,"returnCountOnly":"true","f":"json"}).get("count") or 0)
    features = []
    offset = 0
    while offset < total:
        page = get_json(QUERY_URL, {
            "where":WHERE,"outFields":",".join(OUT_FIELDS),"returnGeometry":"false","f":"json",
            "resultOffset":str(offset),"resultRecordCount":str(max_count),"orderByFields":"OBJECTID ASC",
        }).get("features") or []
        if not page:
            break
        features.extend(page); offset += len(page)
    if len(features) != total:
        raise RuntimeError(f"Business-license pagination incomplete: expected {total}, got {len(features)}")

    records = []
    by_category: dict[str,int] = {}
    senior_candidates = 0
    for feature in features:
        a = feature.get("attributes") or {}
        category = str(a.get("LICENSECATDESC") or "UNKNOWN").strip()
        by_category[category] = by_category.get(category, 0) + 1
        name = str(a.get("DBANAME") or a.get("BUS_NAME") or "UNKNOWN").strip()
        is_apartment = "APARTMENT HOUSE" in category.upper()
        senior_name_evidence = bool(is_apartment and SENIOR_RE.search(name))
        senior_candidates += senior_name_evidence
        records.append({
            "source":"CITY_OF_LAS_VEGAS_BUSINESS_LICENSE_GIS",
            "source_role":"DISCOVERY_ENRICHMENT_ONLY",
            "source_url":LAYER_URL,
            "license_number":a.get("LICENSENO") or "UNKNOWN",
            "business_name":name,
            "legal_name":a.get("BUS_NAME") or "UNKNOWN",
            "license_category":category,
            "license_status":a.get("LICSTATUS") or "UNKNOWN",
            "address":a.get("BUS_ADDRESS") or a.get("LOC_ADDRESS") or "UNKNOWN",
            "city":a.get("BUS_CITY") or "UNKNOWN",
            "state":a.get("BUS_STATE") or "UNKNOWN",
            "zip":a.get("BUS_ZIP") or "UNKNOWN",
            "capacity":a.get("CAPACITY") or "UNKNOWN",
            "within_city_limit":a.get("WITHINCITYLIMIT") if a.get("WITHINCITYLIMIT") not in (None,"") else "UNKNOWN",
            "independent_living_classification":"CANDIDATE_NAME_ONLY" if senior_name_evidence else "UNKNOWN",
            "independent_living_evidence":f"Official business category={category}; senior-oriented name token only" if senior_name_evidence else "UNKNOWN",
            "raw":a,
        })
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(records,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    report = {
        "source":"City of Las Vegas DevelopmentServices Business Licenses MapServer",
        "source_url":LAYER_URL,
        "source_role":"DISCOVERY_ENRICHMENT_ONLY",
        "authoritative_scope_note":"Official City of Las Vegas business-license GIS. It is not treated as Nevada senior-facility licensing truth and does not by itself prove independent living.",
        "query_where":WHERE,
        "records":len(records),
        "by_category":dict(sorted(by_category.items())),
        "apartment_senior_name_candidates":senior_candidates,
        "independent_living_confirmed":0,
        "output":str(out),
    }
    rp=Path(args.report); rp.parent.mkdir(parents=True,exist_ok=True); rp.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False)); return 0

if __name__ == "__main__": raise SystemExit(main())
