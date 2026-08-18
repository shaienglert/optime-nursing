from __future__ import annotations

import argparse, csv, json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path


def d(value: str) -> date | None:
    try: return datetime.strptime(str(value or '').strip(), '%Y-%m-%d').date()
    except Exception: return None


def severity_rank(code: str) -> int:
    order = 'ABCDEFGHIJKL'
    c = str(code or '').strip().upper()
    return order.index(c)+1 if c in order else 0


def link(penalties: list[dict], deficiencies: list[dict], valley_ccns: set[str]) -> dict:
    by_ccn = defaultdict(list)
    for row in deficiencies:
        ccn = str(row.get('CMS Certification Number (CCN)') or '').strip()
        if ccn: by_ccn[ccn].append(row)
    events=[]
    for p in penalties:
        ccn=str(p.get('CMS Certification Number (CCN)') or '').strip()
        if ccn not in valley_ccns: continue
        pd=d(p.get('Penalty Date'))
        candidates=[]
        for r in by_ccn.get(ccn, []):
            sd=d(r.get('Survey Date'))
            if not pd or not sd: continue
            delta=(pd-sd).days
            if 0 <= delta <= 180:
                candidates.append((delta,r))
        if candidates:
            nearest=min(x[0] for x in candidates)
            nearest_rows=[r for delta,r in candidates if delta==nearest]
            confidence='EXACT_SURVEY_DATE' if nearest==0 else ('NEAREST_PRIOR_SURVEY_WITHIN_30_DAYS' if nearest<=30 else 'NEAREST_PRIOR_SURVEY_WITHIN_180_DAYS')
        else:
            nearest=None; nearest_rows=[]; confidence='UNKNOWN_NO_TEMPORAL_MATCH'
        citations=[]
        for r in sorted(nearest_rows, key=lambda x: severity_rank(x.get('Scope Severity Code')), reverse=True):
            citations.append({
                'survey_date': r.get('Survey Date'),
                'f_tag': f"{r.get('Deficiency Prefix','')}{r.get('Deficiency Tag Number','')}",
                'category': r.get('Deficiency Category'),
                'description': r.get('Deficiency Description'),
                'scope_severity': r.get('Scope Severity Code'),
                'complaint_deficiency': r.get('Complaint Deficiency'),
                'infection_control_deficiency': r.get('Infection Control Inspection Deficiency'),
                'corrected_status': r.get('Deficiency Corrected'),
                'correction_date': r.get('Correction Date'),
            })
        events.append({
            'ccn': ccn,
            'provider_name': p.get('Provider Name'),
            'penalty_date': p.get('Penalty Date'),
            'penalty_type': p.get('Penalty Type'),
            'fine_id': p.get('Fine ID'),
            'fine_amount': p.get('Fine Amount'),
            'linkage_confidence': confidence,
            'days_from_nearest_prior_survey': nearest if nearest is not None else 'UNKNOWN',
            'related_citations': citations,
            'causality_warning': 'CMS states penalties may be based on citations identified during inspections, but the Penalties dataset does not expose a direct penalty-to-citation key. Related citations below are temporal/CCN associations unless CMS publishes a direct link.'
        })
    return {'schema_version':'nevada-cms-penalty-citation-linkage-v1.0.0','events':events}


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--penalties',default='data/nevada/raw/cms_penalties_nv.csv'); ap.add_argument('--deficiencies',default='data/nevada/raw/cms_health_deficiencies_nv.csv'); ap.add_argument('--universe',default='database/nevada_facility_universe_canonical.json'); ap.add_argument('--output',default='reports/NEVADA_CMS_PENALTY_CITATION_LINKAGE.json'); args=ap.parse_args()
    with open(args.penalties,encoding='utf-8-sig',newline='') as h: penalties=list(csv.DictReader(h))
    with open(args.deficiencies,encoding='utf-8-sig',newline='') as h: deficiencies=list(csv.DictReader(h))
    universe=json.loads(Path(args.universe).read_text(encoding='utf-8'))
    valley_ccns={str(r.get('cms_ccn') or '').strip() for r in universe.get('records',[]) if r.get('is_las_vegas_valley') is True and r.get('canonical_type')=='SKILLED_NURSING' and str(r.get('cms_ccn') or '').strip() not in {'','UNKNOWN'}}
    result=link(penalties,deficiencies,valley_ccns)
    result['summary']={
        'valley_penalty_events':len(result['events']),
        'events_with_related_citations':sum(bool(e['related_citations']) for e in result['events']),
        'events_without_temporal_match':sum(not e['related_citations'] for e in result['events']),
        'unique_ccns':len({e['ccn'] for e in result['events']})
    }
    Path(args.output).parent.mkdir(parents=True,exist_ok=True); Path(args.output).write_text(json.dumps(result,indent=2)+"\n",encoding='utf-8')
    print(json.dumps(result['summary'],indent=2)); return 0

if __name__=='__main__': raise SystemExit(main())
