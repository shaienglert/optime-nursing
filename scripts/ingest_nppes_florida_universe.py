#!/usr/bin/env python3
import csv, json, sys
from collections import defaultdict, Counter
from pathlib import Path

src=Path(sys.argv[1] if len(sys.argv)>1 else 'database/import/fl_facilities_nppes2.csv')
outdir=Path('database'); reports=Path('reports'); outdir.mkdir(exist_ok=True); reports.mkdir(exist_ok=True)
rows=list(csv.DictReader(src.open(encoding='utf-8-sig')))
by=defaultdict(list)
for r in rows: by[r['npi']].append(r)

def role(rs):
    desc=' | '.join(r['taxonomy_desc'].lower() for r in rs)
    residential=any(x in desc for x in ['assisted living','adult care home','skilled nursing facility','nursing facility','alzheimer center','custodial care facility','residential treatment facility'])
    support=any(x in desc for x in ['home health','in home supportive','respite','adult day care','hospice','homemaker','adult companion','transport'])
    return 'BOTH' if residential and support else 'RESIDENTIAL_CANDIDATE' if residential else 'SUPPORTING_PROVIDER' if support else 'OUT_OF_SCOPE'

fac=[]; tax=[]
for npi,rs in by.items():
    p=next((r for r in rs if r['taxonomy_primary'].lower()=='true'),rs[0])
    fac.append({'canonical_id':'NPI:'+npi,'npi':npi,'display_name':p['doing_business_as'] or p['organization_name'],'organization_name':p['organization_name'],'doing_business_as':p['doing_business_as'],'address_1':p['address_1'],'address_2':p['address_2'],'city':p['city'],'state':p['state'],'postal_code':p['postal_code'],'telephone_number':p['telephone_number'],'fax_number':p['fax_number'],'nppes_status':p['status'],'enumeration_date':p['enumeration_date'],'last_updated':p['last_updated'],'primary_taxonomy_code':p['taxonomy_code'],'primary_taxonomy_desc':p['taxonomy_desc'],'universe_role':role(rs),'source':'NPPES','licensure_authority':'NOT_AHCA','ahca_license_status':'UNKNOWN','licensed_beds':'UNKNOWN','current_availability':'UNKNOWN'})
    for r in rs: tax.append({'canonical_id':'NPI:'+npi,'npi':npi,'taxonomy_code':r['taxonomy_code'],'taxonomy_desc':r['taxonomy_desc'],'taxonomy_primary':r['taxonomy_primary'],'self_reported_license':r['license'],'license_state':r['license_state'],'source':'NPPES'})

(outdir/'florida_nppes_facility_identities.json').write_text(json.dumps(fac,indent=2),encoding='utf-8')
(outdir/'florida_nppes_taxonomy_evidence.json').write_text(json.dumps(tax,indent=2),encoding='utf-8')
rc=Counter(x['universe_role'] for x in fac); tc=Counter(x['taxonomy_desc'] for x in tax)
audit={'source_file':str(src),'source':'NPPES NPI Registry','authoritative_for':'NPI identity/enrollment metadata','not_authoritative_for':['Florida AHCA licensure','licensed beds','current license status','current availability'],'input_rows':len(rows),'unique_npis':len(fac),'taxonomy_evidence_rows':len(tax),'role_counts':dict(rc),'top_taxonomies':tc.most_common(50),'validation':{'one_identity_per_npi':len(fac)==len(by),'unknown_not_no':all(x['ahca_license_status']=='UNKNOWN' and x['current_availability']=='UNKNOWN' for x in fac),'facility_type_not_automatic_exclusion':True}}
(reports/'FLORIDA_NPPES_UNIVERSE_INGEST_AUDIT.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
print(json.dumps(audit,indent=2))
