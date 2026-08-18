from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from link_nevada_cms_penalties_to_citations import link


def test_exact_ccn_and_prior_survey_only():
    penalties=[{'CMS Certification Number (CCN)':'295090','Provider Name':'X','Penalty Date':'2026-03-15','Penalty Type':'Fine','Fine ID':'1','Fine Amount':'1000'}]
    defs=[
        {'CMS Certification Number (CCN)':'295090','Survey Date':'2026-03-01','Deficiency Prefix':'F','Deficiency Tag Number':'0689','Deficiency Category':'Quality','Deficiency Description':'Prevent accidents','Scope Severity Code':'J'},
        {'CMS Certification Number (CCN)':'999999','Survey Date':'2026-03-14','Deficiency Prefix':'F','Deficiency Tag Number':'0600','Deficiency Category':'Abuse','Deficiency Description':'Wrong facility','Scope Severity Code':'K'},
        {'CMS Certification Number (CCN)':'295090','Survey Date':'2026-03-20','Deficiency Prefix':'F','Deficiency Tag Number':'0600','Deficiency Category':'Abuse','Deficiency Description':'Future survey','Scope Severity Code':'K'},
    ]
    result=link(penalties,defs,{'295090'})['events'][0]
    assert result['linkage_confidence']=='NEAREST_PRIOR_SURVEY_WITHIN_30_DAYS'
    assert len(result['related_citations'])==1
    assert result['related_citations'][0]['f_tag']=='F0689'


def test_no_direct_link_remains_unknown_when_no_temporal_match():
    penalties=[{'CMS Certification Number (CCN)':'295090','Penalty Date':'2026-12-31','Penalty Type':'Fine'}]
    defs=[{'CMS Certification Number (CCN)':'295090','Survey Date':'2026-01-01'}]
    event=link(penalties,defs,{'295090'})['events'][0]
    assert event['linkage_confidence']=='UNKNOWN_NO_TEMPORAL_MATCH'
    assert event['related_citations']==[]
    assert 'does not expose a direct penalty-to-citation key' in event['causality_warning']
