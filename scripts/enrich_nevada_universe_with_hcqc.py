from __future__ import annotations
import argparse,csv,json,re
from collections import Counter,defaultdict
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
DEFAULT_CANONICAL=ROOT/'database'/'nevada_facility_universe_canonical.json'
DEFAULT_HCQC=ROOT/'data'/'nevada'/'hcqc'/'nevada_hcqc_facilities.csv'
DEFAULT_OUTPUT=ROOT/'data'/'nevada'/'hcqc'/'nevada_facility_universe_enriched.json'
DEFAULT_REPORT=ROOT/'data'/'nevada'/'hcqc'/'nevada_hcqc_merge_report.json'
SOURCE_URL='https://nvdpbh.aithent.com/Protected/LIC/LicenseeSearch.aspx?Program=HFF&PubliSearch=Y&returnURL=~%2FLogin.aspx%3FTI%3D0'
def norm(v):return re.sub(r'[^a-z0-9]+',' ',str(v or '').lower()).strip()
def phone(v):
 d=re.sub(r'\D','',str(v or ''));return d[1:] if len(d)==11 and d.startswith('1') else d if len(d)==10 else ''
def z(v):
 m=re.search(r'\b(\d{5})',str(v or ''));return m.group(1) if m else ''
def addr(v):return norm(str(v or '').replace(' street ',' st ').replace(' road ',' rd ').replace(' avenue ',' ave ').replace(' boulevard ',' blvd ').replace(' drive ',' dr '))
def ftype(v):
 n=norm(v)
 if 'residential facility for groups' in n:return 'Assisted Living'
 if 'skilled nursing' in n:return 'Skilled Nursing Facility'
 if 'nursing facility' in n:return 'Nursing Facility'
 if 'continuing care' in n:return 'Continuing Care / Life Plan'
 return 'Other Governed Senior-Care Residential'
def lv(city,county):return norm(county)=='clark' and norm(city) in {'las vegas','north las vegas','henderson','boulder city','mesquite','laughlin','paradise','spring valley','enterprise','summerlin','centennial hills'}
def idx_unique(records,fn):
 d=defaultdict(list)
 for i,r in enumerate(records):
  k=fn(r)
  if k:d[k].append(i)
 return {k:v[0] for k,v in d.items() if len(v)==1}
def evidence(row):
 lic=row['license_id'];return {'source_name':'Nevada HCQC Health Facility Licensing','source_authority':'Nevada state licensing authority','source_url':SOURCE_URL,'dataset_identifier':row.get('source_export_file'),'source_record_id':lic,'source_update_date':None,'source_retrieved_at':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),'source_facility_type':row.get('source_facility_type'),'scope':'FACILITY'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--canonical',type=Path,default=DEFAULT_CANONICAL);p.add_argument('--hcqc',type=Path,default=DEFAULT_HCQC);p.add_argument('--output',type=Path,default=DEFAULT_OUTPUT);p.add_argument('--report',type=Path,default=DEFAULT_REPORT);a=p.parse_args()
 payload=json.loads(a.canonical.read_text(encoding='utf-8'));records=[dict(r) for r in payload.get('records',[])]
 with a.hcqc.open(encoding='utf-8',newline='') as h:state=list(csv.DictReader(h))
 by_license=idx_unique(records,lambda r:str(r.get('nevada_license_id') or ''))
 by_ccn=idx_unique(records,lambda r:str(r.get('cms_certification_number') or r.get('ccn') or ''))
 by_name_phone=idx_unique(records,lambda r:(norm(r.get('facility_name')),phone(r.get('phone'))) if norm(r.get('facility_name')) and phone(r.get('phone')) else None)
 by_addr_phone=idx_unique(records,lambda r:(addr(r.get('address')),phone(r.get('phone'))) if addr(r.get('address')) and phone(r.get('phone')) else None)
 by_name_zip=idx_unique(records,lambda r:(norm(r.get('facility_name')),z(r.get('zip'))) if norm(r.get('facility_name')) and z(r.get('zip')) else None)
 matched=set();methods=Counter();new_count=0;alzheimer=0
 for s in state:
  lic=s.get('license_id','');ccn=s.get('cms_ccn','');np=phone(s.get('phone'));name=norm(s.get('facility_name'));ad=addr(s.get('address'));zp=z(s.get('zip'))
  candidates=[('license',by_license.get(lic) if lic else None),('ccn',by_ccn.get(ccn) if ccn else None),('name_phone',by_name_phone.get((name,np)) if name and np else None),('address_phone',by_addr_phone.get((ad,np)) if ad and np else None),('name_zip',by_name_zip.get((name,zp)) if name and zp else None)]
  method,index=next(((m,i) for m,i in candidates if i is not None),(None,None))
  if index is None:
   r={'canonical_id':'NV-LIC-'+re.sub(r'[^A-Za-z0-9]+','-',lic).strip('-').upper(),'canonical_type':'NEVADA_LICENSE','canonical_schema_version':payload.get('canonical_schema_version'),'facility_name':s.get('facility_name'),'legal_name':None,'dba_trade_names':[],'former_names':[],'operator_name':None,'owner_name':None,'facility_type':ftype(s.get('source_facility_type')),'source_facility_type':s.get('source_facility_type'),'address':s.get('address'),'address_line_2':None,'city':s.get('city'),'county':s.get('county') or 'UNKNOWN','state':'NV','zip':zp,'phone':np or None,'website':None,'nevada_license_id':lic,'cms_certification_number':ccn or None,'ccn':ccn or None,'npi':None,'licensed_beds_capacity':s.get('bed_count') or None,'certified_beds':None,'license_status':str(s.get('status') or 'UNKNOWN').upper(),'license_effective_date':s.get('effective_date') or None,'license_expiration_date':s.get('expiration_date') or None,'availability':'UNKNOWN','availability_evidence_state':'UNKNOWN','source_identity_ids':{'nevada_license_id':lic,**({'cms_ccn':ccn} if ccn else {})},'source_evidence':{'nevada_hcqc:'+lic:evidence(s)},'source_retrieved_at':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),'source_record_id':lic,'identity_confidence':'HIGH','identity_conflicts':{},'aliases':[],'ownership_history':[],'name_change_history':[],'merge_evidence':[],'merge_confidence':'NOT_MERGED','source_precedence':'Nevada licensing > CMS > NPPES','duplicate_candidate':False,'duplicate_candidate_reason':None,'is_las_vegas_valley':lv(s.get('city'),s.get('county')),'market_name':'Las Vegas, Nevada' if lv(s.get('city'),s.get('county')) else 'Other Nevada','market_city_normalized':str(s.get('city') or '').title()}
   records.append(r);index=len(records)-1;new_count+=1;method='state_only'
  else:
   r=records[index];matched.add(index);methods[method]+=1
   r['canonical_type']='NEVADA_LICENSE';r['nevada_license_id']=lic;r.setdefault('source_identity_ids',{})['nevada_license_id']=lic
   if ccn:r['cms_certification_number']=ccn;r['ccn']=ccn;r['source_identity_ids']['cms_ccn']=ccn
   for field,source in [('facility_name','facility_name'),('address','address'),('city','city'),('county','county'),('zip','zip'),('phone','phone')]:
    if s.get(source):r[field]=np if field=='phone' else (zp if field=='zip' else s[source])
   r['source_facility_type']=s.get('source_facility_type') or r.get('source_facility_type');r['facility_type']=ftype(r['source_facility_type']);r['licensed_beds_capacity']=s.get('bed_count') or r.get('licensed_beds_capacity');r['license_status']=str(s.get('status') or r.get('license_status') or 'UNKNOWN').upper();r['license_effective_date']=s.get('effective_date') or r.get('license_effective_date');r['license_expiration_date']=s.get('expiration_date') or r.get('license_expiration_date');r['is_las_vegas_valley']=lv(r.get('city'),r.get('county'));r['market_name']='Las Vegas, Nevada' if r['is_las_vegas_valley'] else 'Other Nevada';r['identity_confidence']='HIGH';r['merge_confidence']='HIGH';r.setdefault('merge_evidence',[]).append('exact_'+method);r.setdefault('source_evidence',{})['nevada_hcqc:'+lic]=evidence(s)
  r=records[index];endorsement=str(s.get('endorsement') or '').strip();r['nevada_hcqc_endorsement']=endorsement or None;r['nevada_hcqc_disciplinary_action']=str(s.get('disciplinary_action') or '').strip() or None;r['nevada_hcqc_inspection_number']=str(s.get('inspection_number') or '').strip() or None;r['nevada_hcqc_inspection_score']=str(s.get('inspection_score') or '').strip() or None;r['nevada_hcqc_primary_contact_name']=str(s.get('primary_contact_name') or '').strip() or None;r['nevada_hcqc_primary_contact_role']=str(s.get('primary_contact_role') or '').strip() or None;r['nevada_hcqc_low_income_bed_count']=str(s.get('low_income_bed_count') or '').strip() or None;r['nevada_license_verification_state']='VERIFIED_CURRENT_EXPORT'
  if 'alzheimer' in endorsement.lower():r['alzheimer_endorsement']=True;alzheimer+=1
 for i,r in enumerate(records[:len(payload.get('records',[]))]):
  if not r.get('nevada_license_id'):r['nevada_license_verification_state']='NOT_MATCHED_TO_CURRENT_HCQC_EXPORT'
 records.sort(key=lambda x:str(x.get('canonical_id') or ''))
 out={'generated_at_utc':datetime.now(timezone.utc).replace(microsecond=0).isoformat(),'record_count':len(records),'canonical_schema_version':payload.get('canonical_schema_version'),'records':records};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 report={'existing_records':len(payload.get('records',[])),'hcqc_records':len(state),'matched_existing':sum(methods.values()),'match_methods':dict(methods),'new_state_only_records':new_count,'output_records':len(records),'records_with_nevada_license_id':sum(bool(r.get('nevada_license_id')) for r in records),'las_vegas_valley_records':sum(bool(r.get('is_las_vegas_valley')) for r in records),'records_with_cms_ccn':sum(bool(r.get('cms_certification_number') or r.get('ccn')) for r in records),'records_with_npi':sum(bool(r.get('npi')) for r in records),'records_with_licensed_capacity':sum(bool(r.get('licensed_beds_capacity')) for r in records),'alzheimer_endorsements':alzheimer,'facility_types':dict(Counter(str(r.get('facility_type') or 'UNKNOWN') for r in records)),'unmatched_existing_npi_only':sum(r.get('canonical_type')=='NPI_ONLY' for r in records),'guardrails':['No existing record is deleted.','Only exact/unique strong identity keys merge state evidence.','Unmatched current records remain UNKNOWN with respect to Nevada license verification; they are not treated as negative evidence.']};a.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
