from __future__ import annotations
from typing import Any

IMMUTABLE_SYSTEM_MUST='SYSTEM_MUST'
CLIENT_MUST='CLIENT_MUST'
PREFERENCE='PREFERENCE'

def analyze_oomniker(profile:dict[str,Any], candidates:list[dict[str,Any]], *, filtered_universe:list[dict[str,Any]]|None=None)->dict[str,Any]:
    """Advisory AI boundary: maximize viable choice only after SYSTEM MUST filtering."""
    universe=list(filtered_universe if filtered_universe is not None else candidates)
    constraints=profile.get('constraints') if isinstance(profile.get('constraints'),list) else []
    suggestions=[]
    immutable=[]
    for constraint in constraints:
        if not isinstance(constraint,dict): continue
        level=str(constraint.get('authority') or constraint.get('requirement_level') or PREFERENCE).upper()
        key=str(constraint.get('parameter') or constraint.get('parameter_id') or '')
        if level==IMMUTABLE_SYSTEM_MUST:
            immutable.append(key); continue
        matching=sum(1 for row in universe if key in set(row.get('matched_parameter_ids') or []))
        lost=max(0,len(universe)-matching)
        if not lost: continue
        if level==CLIENT_MUST:
            suggestions.append({'parameter':key,'authority':CLIENT_MUST,'action':'ASK_CLIENT_TO_RECONSIDER','requires_client_approval':True,'options_preserved':matching,'additional_options_if_relaxed':lost,'may_auto_change':False})
        else:
            suggestions.append({'parameter':key,'authority':PREFERENCE,'action':'RECOMMEND_TRANSPARENT_ALTERNATIVE','requires_client_approval':True,'options_preserved':matching,'additional_options_if_relaxed':lost,'may_auto_change':False})
    budget=profile.get('budget')
    if isinstance(budget,(int,float)) and budget>0:
        tolerance=sum(1 for r in universe if isinstance(r.get('starting_monthly_price'),(int,float)) and budget<r['starting_monthly_price']<=budget*1.10)
        if tolerance: suggestions.append({'parameter':'budget','authority':PREFERENCE,'action':'RECOMMEND_WITHIN_APPROVED_10_PERCENT','requires_client_approval':True,'additional_options_if_relaxed':tolerance,'may_auto_change':False})
    suggestions.sort(key=lambda x:(-int(x.get('additional_options_if_relaxed') or 0),str(x.get('parameter'))))
    return {'status':'AI_ADVISOR_WITH_GOVERNED_BOUNDARIES','system_must_immutable':immutable,'input_universe':'POST_SYSTEM_MUST_FILTER_ONLY','profile_mutated':False,'suggestions':suggestions,'candidate_count':len(universe)}