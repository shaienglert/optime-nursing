from __future__ import annotations
import argparse,csv,io,json,re,uuid
from pathlib import Path
from urllib.request import Request,urlopen
PLACES="https://api.census.gov/data/2020/dec/pl?get=NAME&for=place:*&in=state:32"
BATCH="https://geocoding.geo.census.gov/geocoder/geographies/addressbatch"
UA="Mozilla/5.0 OPTIME-Nursing/1.0"
VALLEY={"LAS VEGAS","NORTH LAS VEGAS","HENDERSON","PARADISE","SPRING VALLEY","ENTERPRISE","SUNRISE MANOR","WINCHESTER","WHITNEY","BOULDER CITY","SUMMERLIN SOUTH","NELLIS AFB"}
def getj(url):
    with urlopen(Request(url,headers={"User-Agent":UA}),timeout=120) as r:return json.loads(r.read())
def places():
    p=[]
    for r in getj(PLACES)[1:]:
        n=re.sub(r", Nevada$","",r[0],flags=re.I);n=re.sub(r"\s+(?:city|CDP)$","",n,flags=re.I).upper().strip();p.append(n)
    return sorted(set(p),key=len,reverse=True)
def split(raw,ps):
    base=re.sub(r",?\s*NV\s+\d{5}(?:-\d{4})?\s*$","",raw,flags=re.I).strip(" ,");u=base.upper()
    for p in ps:
        if u.endswith(" "+p):return base[:-(len(p)+1)].strip(" ,") or "UNKNOWN",p
    return base or "UNKNOWN","UNKNOWN"
def post_batch(data):
    b="----optime"+uuid.uuid4().hex; chunks=[]
    for n,v in (("benchmark","Public_AR_Current"),("vintage","Current_Current")):
        chunks.append(f'--{b}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode())
    chunks.append(f'--{b}\r\nContent-Disposition: form-data; name="addressFile"; filename="nv.csv"\r\nContent-Type: text/csv\r\n\r\n'.encode()+data+b"\r\n")
    chunks.append(f'--{b}--\r\n'.encode());body=b"".join(chunks)
    req=Request(BATCH,data=body,headers={"User-Agent":UA,"Content-Type":f"multipart/form-data; boundary={b}"},method="POST")
    with urlopen(req,timeout=240) as r:return r.read()
def batch_rows(raw):
    out={}
    for r in csv.reader(io.StringIO(raw.decode("utf-8-sig",errors="replace"))):
        if len(r)>=8:out[r[0].strip()]={"match":r[2],"matched":r[4],"state":r[8] if len(r)>8 else "","county":r[9] if len(r)>9 else ""}
    return out
def main():
    a=argparse.ArgumentParser();a.add_argument("--input",default="data/nevada/raw/hcqc_alis_facilities.csv");a.add_argument("--output",default="data/nevada/clean/hcqc_alis_facilities.csv");a.add_argument("--report",default="reports/NEVADA_HCQC_GEOGRAPHY_NORMALIZATION.json");x=a.parse_args()
    with Path(x.input).open(encoding="utf-8-sig",newline="") as h:rows=list(csv.DictReader(h))
    ps=places();s=io.StringIO();w=csv.writer(s,lineterminator="\n");unresolved=0
    for i,r in enumerate(rows):
        raw=f'{r.get("address","")} {r.get("city","")}, NV {r.get("zip","")}'.strip();street,city=split(raw,ps);r["raw_full_address"]=raw;r["address"]=street;r["city"]=city;r["geography_parse_source"]=PLACES if city!="UNKNOWN" else "UNKNOWN";unresolved+=city=="UNKNOWN";w.writerow([i,"" if street=="UNKNOWN" else street,"" if city=="UNKNOWN" else city,"NV",r.get("zip","")])
    geo=batch_rows(post_batch(s.getvalue().encode()));matches=clark=valley=0
    for i,r in enumerate(rows):
        g=geo.get(str(i),{});m=str(g.get("match","")).lower()=="match";cf=str(g.get("county","")) if m else "";matches+=m;r["county_fips"]=cf or "UNKNOWN";r["county"]="Clark" if cf=="003" else "UNKNOWN";r["census_geocoder_match"]="MATCH" if m else "NO_MATCH";r["census_geocoder_matched_address"]=g.get("matched") or "UNKNOWN";r["census_geography_source"]=BATCH if m else "UNKNOWN";is_clark=cf=="003";is_valley=is_clark and r["city"] in VALLEY;r["is_clark_county"]="true" if is_clark else ("false" if m else "UNKNOWN");r["is_las_vegas_valley"]="true" if is_valley else ("false" if m else "UNKNOWN");clark+=is_clark;valley+=is_valley
    o=Path(x.output);o.parent.mkdir(parents=True,exist_ok=True);fields=list(rows[0]);
    with o.open("w",encoding="utf-8",newline="") as h:w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows(rows)
    cities={}
    for r in rows:cities[r["city"]]=cities.get(r["city"],0)+1
    rep={"records":len(rows),"place_parse_unresolved":unresolved,"census_geocoder_matches":matches,"census_geocoder_no_matches":len(rows)-matches,"clark_county_confirmed":clark,"las_vegas_valley_confirmed":valley,"by_city":dict(sorted(cities.items())),"output":str(o)};p=Path(x.report);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(rep,indent=2)+"\n");print(json.dumps(rep,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
