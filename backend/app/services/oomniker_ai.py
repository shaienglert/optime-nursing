from __future__ import annotations
from typing import Any, Callable
from app.services.semantic_intent_ai import _default_transport

def advise_with_ai(*, analysis:dict[str,Any], client_context:dict[str,Any], transport:Callable[[dict[str,Any]],dict[str,Any]]=_default_transport)->dict[str,Any]:
    """AI explains governed sensitivity facts; it cannot create or apply a relaxation."""
    allowed={str(x.get("parameter")):x for x in analysis.get("suggestions") or [] if isinstance(x,dict)}
    prompt={
        "role":"OOMNIKER_AI_DECISION_ADVISOR",
        "mission":"Help the family understand which non-system constraints reduce viable choice and suggest transparent alternatives that preserve the underlying goal.",
        "hard_rules":[
            "SYSTEM_MUST is immutable: never suggest waiving, weakening or questioning it.",
            "CLIENT_MUST may only be reconsidered by explicitly asking the client after explaining the supply impact.",
            "PREFERENCE may receive practical alternatives, including external services, but the client must approve any change.",
            "Use only the supplied sensitivity analysis. Never invent candidate counts or facility capabilities.",
            "Do not mutate parameters and do not claim a rerun happened.",
        ],
        "client_context":client_context,
        "governed_analysis":analysis,
        "required_output":{"message":"natural expert guidance","proposals":[{"parameter":"must exist in governed suggestions","alternative":"optional practical alternative","ask_client":"explicit question"}]},
    }
    try:
        packet=transport(prompt)
    except Exception as exc:
        return {"status":"AI_UNAVAILABLE","message":None,"proposals":[],"error":str(exc)[:300]}
    proposals=[]
    for p in packet.get("proposals") or []:
        if not isinstance(p,dict): continue
        key=str(p.get("parameter") or "")
        governed=allowed.get(key)
        if not governed or governed.get("authority")=="SYSTEM_MUST": continue
        proposals.append({"parameter":key,"authority":governed.get("authority"),"alternative":str(p.get("alternative") or "")[:500],"ask_client":str(p.get("ask_client") or "")[:500],"requires_client_approval":True})
    return {"status":"AI_ADVISORY_READY","message":str(packet.get("message") or "")[:2000],"proposals":proposals,"profile_mutated":False}
