from __future__ import annotations
import argparse,csv,hashlib,json,re
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ALIS_URL='https://nvdpbh.aithent.com/Protected/LIC/LicenseeSearch.aspx?Program=HHF&PubliSearch=Y&returnURL=~%2FLogin.aspx%3FTI%3D0'
CMS_URL='https://data.cms.gov/provider-data/dataset/4pq5-n9py'
LV_BUSINESS_URL='https://mapdata.lasvegasnevada.gov/clvgis/rest/services/DevelopmentServices/Business_Licenses/MapServer/0'
def utcnow(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def norm(v): return re.sub(r'[^a-z0-9]+',' ',str(v or '').lower().replace('&',' and ')).strip()
def norm_addr(v):
 t=f' {norm(v)} '
 for a,b in {' st ':' street ',' rd ':' road ',' ave ':' avenue ',' blvd ':' boulevard ',' dr ':' drive ',' ln ':' lane ',' hwy ':' highway ',' pkwy ':' parkway ',' n ':' north ',' s ':' south ',' e ':' east ',' w ':' west '}.items(): t=t.replace(a,b)
 return re.sub(r'\s+',' ',t).strip()
def zip5(v):
 m=re.search(r'\b(\d{5})',str(v or '')); return m.group(1) if m else 'UNKNOWN'
def present(v): return v not in (None,'','UNKNOWN','unknown',[],{})
def sjson(v,default):
 if not present(v): return default
 if isinstance(v,(dict,list)): return v
 try:return json.loads(str(v))
 except:return default
def ev(source,url,rid,role,at): return {'source':source,'source_url':url,'source_record_id':rid or 'UNKNOWN','source_role':role,'retrieved_at':at}
def ccn_of(row): return row.get('CMS Certification Number (CCN)') or row.get('Federal Provider Number') or 'UNKNOWN'
def ctype(t): return 'ASSISTED_LIVING_RFG' if t=='AGC' else 'SKILLED_NURSING' if t in {'SNF','SFD'} else 'UNKNOWN'
def cid_license(v): return 'NV-LIC-'+re.sub(r'[^A-Za-z0-9]+','-',v).strip('-').upper()
def cid_cms(v): return 'CMS-'+v
def campus_id(address,city,z): return 'NV-CAMPUS-'+hashlib.sha256('|'.join((norm_addr(address),norm(city),zip5(z))).encode()).hexdigest()[:16].upper()
def strong_key(name,address,city,z): return (norm(name),norm_addr(address),norm(city),zip5(z))
def compatible_name(a,b):
 a,b=norm(a),norm(b); return a==b or (min(len(a),len(b))>=35 and (a.startswith(b) or b.startswith(a)))
def add_field(r,f,v,e,overwrite=False):
 if not present(v): r.setdefault(f,'UNKNOWN'); return
 if overwrite or not present(r.get(f)): r[f]=v; r.setdefault('field_provenance',{})[f]=e
def alis_record(row,at):
 lic=row.get('license_number') or 'UNKNOWN'; typ=row.get('license_type') or 'UNKNOWN'; e=ev('Nevada HCQC / ALiS',ALIS_URL,lic,'LICENSING_SOURCE_OF_TRUTH',at); detail=sjson(row.get('official_detail'),{}); mem_e=sjson(row.get('memory_care_evidence'),[]); mem=row.get('memory_care_classification')=='CONFIRMED_OFFICIAL_DETAIL'; address=row.get('address') or 'UNKNOWN'; city=row.get('city') or 'UNKNOWN'; z=zip5(row.get('zip'))
 r={'canonical_id':cid_license(lic),'facility_name':row.get('facility_name') or 'UNKNOWN','canonical_type':ctype(typ),'license_type':typ,'nevada_license_id':lic,'license_status':row.get('status') or 'UNKNOWN','address':address,'city':city,'state':'NV','zip':z,'county':row.get('county') or 'UNKNOWN','phone':row.get('phone') or 'UNKNOWN','licensed_capacity':row.get('capacity') or 'UNKNOWN','administrator':row.get('primary_contact_name') or 'UNKNOWN','administrator_role':row.get('primary_contact_role') or 'UNKNOWN','first_issue_date':row.get('first_issue_date') or 'UNKNOWN','expiration_date':row.get('expiration_date') or 'UNKNOWN','disciplinary_action':row.get('disciplinary_action') or 'UNKNOWN','cms_ccn':row.get('federal_provider_number') or 'UNKNOWN','memory_care_classification':'CONFIRMED' if mem else 'UNKNOWN','memory_care_evidence':mem_e if mem_e else 'UNKNOWN','official_detail':detail if detail else 'UNKNOWN','detail_url':row.get('detail_url') or 'UNKNOWN','is_clark_county':str(row.get('is_clark_county') or '').lower()=='true','is_las_vegas_valley':str(row.get('is_las_vegas_valley') or '').lower()=='true','campus_group_id':campus_id(address,city,z),'source_records':[e],'field_provenance':{},'identity_merge_evidence':[],'review_flags':[]}
 for f in ['facility_name','canonical_type','license_type','nevada_license_id','license_status','address','city','state','zip','county','phone','licensed_capacity','administrator','administrator_role','first_issue_date','expiration_date','disciplinary_action','cms_ccn','memory_care_classification','memory_care_evidence','official_detail','detail_url','is_clark_county','is_las_vegas_valley']: r['field_provenance'][f]=e
 if not mem:r['review_flags'].append('MEMORY_CARE_UNKNOWN')
 return r
def merge_cms(r,row,at,method):
 c=ccn_of(row); e=ev('CMS Care Compare Provider Information',CMS_URL,c,'FEDERAL_NURSING_SOURCE_OF_TRUTH',at)
 if not any(x.get('source')==e['source'] and x.get('source_record_id')==c for x in r['source_records']): r['source_records'].append(e)
 r['identity_merge_evidence'].append({'method':method,'cms_ccn':c,'source':'CMS Care Compare'})
 for f,k in [('cms_ccn',None),('cms_provider_name','Provider Name'),('certified_beds','Number of Certified Beds'),('cms_ownership_type','Ownership Type'),('cms_overall_rating','Overall Rating'),('cms_health_inspection_rating','Health Inspection Rating'),('cms_staffing_rating','Staffing Rating'),('cms_quality_measure_rating','QM Rating'),('cms_processing_date','Processing Date')]: add_field(r,f,c if k is None else row.get(k),e,overwrite=(f=='cms_ccn' and not present(r.get(f))))
def cms_only(row,at):
 c=ccn_of(row); e=ev('CMS Care Compare Provider Information',CMS_URL,c,'FEDERAL_NURSING_SOURCE_OF_TRUTH',at); address=row.get('Provider Address') or 'UNKNOWN'; city=row.get('City/Town') or 'UNKNOWN'; z=zip5(row.get('ZIP Code')); county=row.get('County/Parish') or 'UNKNOWN'
 r={'canonical_id':cid_cms(c),'facility_name':row.get('Provider Name') or 'UNKNOWN','canonical_type':'SKILLED_NURSING','license_type':'UNKNOWN','nevada_license_id':'UNKNOWN','license_status':'UNKNOWN','address':address,'city':city,'state':'NV','zip':z,'county':county,'phone':row.get('Telephone Number') or 'UNKNOWN','licensed_capacity':'UNKNOWN','administrator':'UNKNOWN','administrator_role':'UNKNOWN','first_issue_date':'UNKNOWN','expiration_date':'UNKNOWN','disciplinary_action':'UNKNOWN','cms_ccn':c,'memory_care_classification':'UNKNOWN','memory_care_evidence':'UNKNOWN','official_detail':'UNKNOWN','detail_url':'UNKNOWN','is_clark_county':norm(county)=='clark','is_las_vegas_valley':norm(county)=='clark' and norm(city) in {'las vegas','north las vegas','henderson'},'campus_group_id':campus_id(address,city,z),'source_records':[e],'field_provenance':{},'identity_merge_evidence':[{'method':'CMS_ONLY','cms_ccn':c,'source':'CMS Care Compare'}],'review_flags':['NEVADA_LICENSE_ID_UNKNOWN','MEMORY_CARE_UNKNOWN']}
 for f in ['facility_name','canonical_type','address','city','state','zip','county','phone','cms_ccn']:r['field_provenance'][f]=e
 for f,k in [('certified_beds','Number of Certified Beds'),('cms_ownership_type','Ownership Type'),('cms_overall_rating','Overall Rating'),('cms_health_inspection_rating','Health Inspection Rating'),('cms_staffing_rating','Staffing Rating'),('cms_quality_measure_rating','QM Rating'),('cms_processing_date','Processing Date')]:add_field(r,f,row.get(k),e)
 return r
def build(alis,cms,biz):
 at=utcnow(); records=[alis_record(x,at) for x in alis]; by_ccn=defaultdict(list); by_key=defaultdict(list); by_addr=defaultdict(list)
 for i,r in enumerate(records):
  if present(r['cms_ccn']):by_ccn[str(r['cms_ccn'])].append(i)
  k=strong_key(r['facility_name'],r['address'],r['city'],r['zip']); ak=(norm_addr(r['address']),norm(r['city']),zip5(r['zip']))
  if all(present(x) for x in k):by_key[k].append(i)
  if all(present(x) for x in ak):by_addr[ak].append(i)
 methods=Counter(); conflicts=[]
 for row in cms:
  c=ccn_of(row); idx=None; method=None; exact=by_ccn.get(c,[]) if present(c) else []
  if len(exact)==1:idx=exact[0];method='EXACT_CCN'
  elif len(exact)>1:conflicts.append({'ccn':c,'reason':'AMBIGUOUS_CCN','candidate_count':len(exact)});continue
  else:
   k=strong_key(row.get('Provider Name'),row.get('Provider Address'),row.get('City/Town'),row.get('ZIP Code')); cand=by_key.get(k,[])
   if len(cand)==1:idx=cand[0];method='EXACT_NORMALIZED_NAME_ADDRESS_CITY_ZIP'
   elif len(cand)>1:conflicts.append({'ccn':c,'reason':'AMBIGUOUS_NAME_ADDRESS','candidate_count':len(cand)});continue
   else:
    ak=(norm_addr(row.get('Provider Address')),norm(row.get('City/Town')),zip5(row.get('ZIP Code'))); ac=[i for i in by_addr.get(ak,[]) if compatible_name(records[i]['facility_name'],row.get('Provider Name'))]
    if len(ac)==1:idx=ac[0];method='EXACT_NORMALIZED_ADDRESS_COMPATIBLE_TRUNCATED_NAME'
    elif len(ac)>1:conflicts.append({'ccn':c,'reason':'AMBIGUOUS_ADDRESS_NAME','candidate_count':len(ac)});continue
  if idx is None:records.append(cms_only(row,at));methods['CMS_ONLY']+=1
  else:merge_cms(records[idx],row,at,method);methods[method]+=1
 groups=defaultdict(list)
 for i,r in enumerate(records):groups[r['campus_group_id']].append(i)
 multi=mixed=0
 for _,inds in groups.items():
  if len(inds)<2:continue
  multi+=1; label='MIXED_CAMPUS' if len({records[i]['canonical_type'] for i in inds})>1 else 'MULTI_ENTITY_SAME_TYPE_CAMPUS'; mixed+=int(label=='MIXED_CAMPUS')
  for i in inds:records[i]['campus_classification']=label
 candidates=[]; seen=set(); raw_candidate_rows=0
 for row in biz:
  if row.get('license_category')!='Apartment House' or row.get('independent_living_classification') not in {'CANDIDATE_NAME_ONLY','CANDIDATE_NAME_SIGNAL'}:continue
  raw_candidate_rows+=1
  if row.get('license_status')!='Active':continue
  k=(norm(row.get('business_name')),norm_addr(row.get('address')),norm(row.get('city')))
  if k in seen:continue
  seen.add(k); candidates.append({'business_license_number':row.get('license_number') or 'UNKNOWN','business_name':row.get('business_name') or 'UNKNOWN','address':row.get('address') or 'UNKNOWN','city':row.get('city') or 'UNKNOWN','state':row.get('state') or 'NV','zip':row.get('zip') or 'UNKNOWN','license_status':row.get('license_status') or 'UNKNOWN','classification':'INDEPENDENT_LIVING_CANDIDATE_UNKNOWN','evidence':'Active Apartment House business license plus senior name signal only; not proof of Independent Living.','source':ev('City of Las Vegas Business Licenses',LV_BUSINESS_URL,row.get('license_number') or 'UNKNOWN','DISCOVERY_ENRICHMENT_ONLY',at)})
 types=Counter(r['canonical_type'] for r in records); mem=sum(r['memory_care_classification']=='CONFIRMED' for r in records); mem_unknown=sum(r['canonical_type']=='ASSISTED_LIVING_RFG' and r['memory_care_classification']!='CONFIRMED' for r in records); subsets={'nevada_statewide':records,'clark_county':[r for r in records if r['is_clark_county'] is True],'las_vegas':[r for r in records if norm(r['city'])=='las vegas'],'north_las_vegas':[r for r in records if norm(r['city'])=='north las vegas'],'henderson':[r for r in records if norm(r['city'])=='henderson'],'las_vegas_valley':[r for r in records if r['is_las_vegas_valley'] is True]}; flags=Counter(f for r in records for f in r['review_flags'])
 report={'generated_at':at,'canonical_facilities_unique':len(records),'nevada_official_license_records':len(alis),'cms_source_records':len(cms),'business_license_discovery_records':len(biz),'source_identity_merges':sum(v for k,v in methods.items() if k!='CMS_ONLY'),'merge_methods':dict(methods),'unresolved_cms_identity_conflicts':conflicts,'counts_by_type':dict(types),'memory_care_confirmed':mem,'memory_care_candidate_unknown':mem_unknown,'independent_living_confirmed':0,'independent_living_candidate_rows_all_statuses':raw_candidate_rows,'independent_living_candidates_unknown_active_unique':len(candidates),'multi_entity_campuses':multi,'mixed_campuses':mixed,'review_flags':dict(flags),'subsets':{k:len(v) for k,v in subsets.items()},'semantic_guardrails':['Nevada HCQC/ALiS is licensing source of truth.','CMS is federal nursing-facility evidence and is never used as Nevada assisted-living licensing truth.','CMS merges require exact CCN or exact normalized name+address+city+ZIP.','Distinct Nevada licenses are never collapsed merely because they share a campus.','Memory Care requires explicit official ALiS detail evidence.','Independent Living name signals remain candidates/UNKNOWN.','Commercial directories are not sources of licensing truth.']}
 return {'schema_version':'nevada-canonical-facility-v2.1.0','generated_at':at,'record_count':len(records),'records':records,'independent_living_discovery_candidates':candidates,'report':report,'subsets':subsets}
def write(payload,out,rj,rm,sd):
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({k:v for k,v in payload.items() if k!='subsets'},indent=2,ensure_ascii=False)+'\n',encoding='utf-8');rj.parent.mkdir(parents=True,exist_ok=True);rj.write_text(json.dumps(payload['report'],indent=2,ensure_ascii=False)+'\n',encoding='utf-8');sd.mkdir(parents=True,exist_ok=True)
 for k,v in payload['subsets'].items():(sd/f'{k}.json').write_text(json.dumps({'record_count':len(v),'records':v},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 r=payload['report']; lines=['# Nevada Canonical Facility Universe','',f"Generated: `{r['generated_at']}`",'',f"- Unique canonical facilities: **{r['canonical_facilities_unique']}**",f"- Nevada ALiS license records: **{r['nevada_official_license_records']}**",f"- CMS Nevada records: **{r['cms_source_records']}**",f"- Cross-source identity merges: **{r['source_identity_merges']}**",f"- Memory Care confirmed: **{r['memory_care_confirmed']}**",f"- Independent Living confirmed: **0**",f"- Independent Living active unique candidates / UNKNOWN: **{r['independent_living_candidates_unknown_active_unique']}**",'', '## Geographic subsets','']+[f'- {k}: **{v}**' for k,v in r['subsets'].items()]+['','## Merge methods','']+[f'- {k}: **{v}**' for k,v in r['merge_methods'].items()]+['','## Guardrails','']+[f'- {x}' for x in r['semantic_guardrails']];rm.write_text('\n'.join(lines)+'\n',encoding='utf-8')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--alis',type=Path,default=Path('data/nevada/clean/hcqc_alis_facilities.csv'));ap.add_argument('--cms',type=Path,default=Path('data/nevada/raw/cms_provider_information_nv.csv'));ap.add_argument('--business',type=Path,default=Path('data/nevada/raw/las_vegas_business_license_senior_candidates.json'));ap.add_argument('--output',type=Path,default=Path('database/nevada_facility_universe_canonical.json'));ap.add_argument('--report-json',type=Path,default=Path('reports/NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.json'));ap.add_argument('--report-md',type=Path,default=Path('reports/NEVADA_CANONICAL_FACILITY_UNIVERSE_REPORT.md'));ap.add_argument('--subset-dir',type=Path,default=Path('data/nevada/canonical'));a=ap.parse_args()
 with a.alis.open(encoding='utf-8-sig',newline='') as h:alis=list(csv.DictReader(h))
 with a.cms.open(encoding='utf-8-sig',newline='') as h:cms=list(csv.DictReader(h))
 biz=json.loads(a.business.read_text(encoding='utf-8'));p=build(alis,cms,biz);write(p,a.output,a.report_json,a.report_md,a.subset_dir);print(json.dumps(p['report'],indent=2,ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())