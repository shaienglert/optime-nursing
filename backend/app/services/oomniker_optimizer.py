from __future__ import annotations
from typing import Any

def analyze_oomniker(profile:dict[str,Any], candidates:list[dict[str,Any]])->dict[str,Any]:
    """Explain user-changeable constraints; never mutate profile or rerank candidates."""
    suggestions=[]
    budget=profile.get("budget")
    radius=profile.get("radius_miles") or profile.get("maximumDistanceMiles")
    if isinstance(budget,(int,float)) and budget>0:
        within=sum(1 for r in candidates if isinstance(r.get("starting_monthly_price"),(int,float)) and r["starting_monthly_price"]<=budget)
        tolerance=sum(1 for r in candidates if isinstance(r.get("starting_monthly_price"),(int,float)) and budget<r["starting_monthly_price"]<=budget*1.10)
        if tolerance:
            suggestions.append({"parameter":"budget","current":budget,"suggested_max":round(budget*1.10,2),"additional_options":tolerance,"reason":f"{tolerance} otherwise relevant options are within 10% of the requested budget."})
    if isinstance(radius,(int,float)) and radius>0:
        current=sum(1 for r in candidates if isinstance(r.get("distance_miles"),(int,float)) and r["distance_miles"]<=radius)
        expanded=sum(1 for r in candidates if isinstance(r.get("distance_miles"),(int,float)) and radius<r["distance_miles"]<=radius*2)
        if expanded:
            suggestions.append({"parameter":"radius_miles","current":radius,"suggested_max":radius*2,"additional_options":expanded,"reason":f"Expanding the radius could reveal {expanded} additional otherwise relevant options."})
    suggestions.sort(key=lambda x:(-int(x.get("additional_options") or 0),str(x.get("parameter"))))
    return {"status":"ADVISORY_ONLY","profile_mutated":False,"suggestions":suggestions,"candidate_count":len(candidates)}