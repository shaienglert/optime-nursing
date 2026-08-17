from __future__ import annotations
import argparse,csv,json,re
from pathlib import Path
import xlrd
ROOT=Path(__file__).resolve().parents[1]
DEFAULT_INPUT=ROOT/'data'/'nevada'/'hcqc'
DEFAULT_OUTPUT=DEFAULT_INPUT/'nevada_hcqc_facilities.csv'
CITIES=sorted({'NORTH LAS VEGAS','LAS VEGAS','HENDERSON','BOULDER CITY','MESQUITE','LAUGHLIN','RENO','SPARKS','CARSON CITY','PAHRUMP','FALLON','GARDNERVILLE','MINDEN','FERNLEY','DAYTON','ELKO','ELY','LOVELOCK','WINNEMUCCA','YERINGTON','HAWTHORNE','BATTLE MOUNTAIN','CALIENTE','TONOPAH','SILVER SPRINGS','WELLS','WEST WENDOVER'},key=len,reverse=True)
def clean(v):
    if v is None:return ''
    if isinstance(v,float) and v.is_integer():return str(int(v))
    return re.sub(r'\s+',' ',str(v).strip())
def k(v):return re.sub(r'[^a-z0-9]+',' ',clean(v).lower()).strip()
def find_header(sheet):
    for r in range(min(sheet.nrows,40)):
        vals=[clean(sheet.cell_value(r,c)) for c in range(sheet.ncols)]; norm=[k(v) for v in vals]
        if 'name' in norm and 'credential number' in norm and 'address' in norm:return r,{norm[c]:c for c in range(len(norm)) if norm[c]}
    raise ValueError('HCQC data header not found')
def cell(row,h,*names):
    for n in names:
        i=h.get(k(n))
        if i is not None and i<len(row):return clean(row[i])
    return ''
def parse_address(raw):
    v=clean(raw); m=re.search(r'\b(\d{5})(?:-\d{4})?\s*$',v); z=m.group(1) if m else ''; before=v[:m.start()].strip(' ,') if m else v
    before=re.sub(r',?\s+NV\s*$','',before,flags=re.I).strip(' ,'); up=before.upper()
    for city in CITIES:
        if up.endswith(' '+city) or up==city:return before[:len(before)-len(city)].strip(' ,'),city.title(),'NV',z
    return before,'','NV',z
def normalize_file(path,ctype):
    s=xlrd.open_workbook(path).sheet_by_index(0); hr,h=find_header(s); out=[]
    for r in range(hr+1,s.nrows):
        row=[clean(s.cell_value(r,c)) for c in range(s.ncols)]; name=cell(row,h,'Name'); lic=cell(row,h,'Credential Number')
        if not name or not lic:continue
        raw=cell(row,h,'Address'); addr,city,state,z=parse_address(raw); fed=cell(row,h,'Federal Provider #','Federal Provider'); beds=cell(row,h,'Bed Count')
        out.append({'license_id':lic,'source_record_id':lic,'facility_name':name,'legal_name':'','dba':'','operator_name':'','owner_name':'','source_facility_type':cell(row,h,'Credential Type') or ctype,'address':addr,'address_line_2':'','city':city,'county':cell(row,h,'County','NV County'),'state':state,'zip':z,'phone':cell(row,h,'Phone#','Phone #','Phone'),'website':'','capacity':beds,'status':cell(row,h,'Status'),'effective_date':cell(row,h,'First Issue Date'),'expiration_date':cell(row,h,'Expiration Date'),'cms_ccn':fed,'npi':'','endorsement':cell(row,h,'Endorsement'),'disciplinary_action':cell(row,h,'Disciplinary Action'),'inspection_number':cell(row,h,'Inspection Number'),'inspection_score':cell(row,h,'Score'),'primary_contact_name':cell(row,h,'Primary Contact Name'),'primary_contact_role':cell(row,h,'Primary Contact Role'),'bed_count':beds,'low_income_bed_count':cell(row,h,'Low Income Bed Count'),'federal_provider_number':fed,'source_export_file':path.name,'raw_address':raw})
    return out
def main():
    p=argparse.ArgumentParser();p.add_argument('--input-dir',type=Path,default=DEFAULT_INPUT);p.add_argument('--output',type=Path,default=DEFAULT_OUTPUT);a=p.parse_args();m=json.loads((a.input_dir/'manifest.json').read_text());records=[]
    for item in m.get('downloads',[]):
        path=a.input_dir/item['file']
        if path.is_file():records+=normalize_file(path,item['credential_type'])
    if not records:raise SystemExit('No HCQC records normalized')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    types={}
    for r in records:types[r['source_facility_type']]=types.get(r['source_facility_type'],0)+1
    print(json.dumps({'normalized_records':len(records),'records_by_credential_type':types,'with_license_id':sum(bool(r['license_id']) for r in records),'with_bed_count':sum(bool(r['bed_count']) for r in records),'with_federal_provider_number':sum(bool(r['federal_provider_number']) for r in records),'with_city_parsed':sum(bool(r['city']) for r in records),'with_county':sum(bool(r['county']) for r in records)},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
