from __future__ import annotations
from typing import Any, Callable
from app.services.semantic_intent_ai import _default_transport

def advise_with_ai(*, analysis: dict[str, Any], client_context: dict[str, Any],
                   transport: Callable[[dict[str, Any]], dict[str, Any]] = _default_transport) -> dict[str, Any]:
    """AI selects governed advice; unverified prose, counts and alternatives cannot escape."""
    allowed = {str(x.get("parameter")): x for x in analysis.get("suggestions") or []
               if isinstance(x, dict) and x.get("authority") == "PREFERENCE"
               and x.get("action") == "OFFER_PREFERENCE_ALTERNATIVE"
               and x.get("requires_client_approval") is True and x.get("may_auto_change") is False
               and isinstance(x.get("new_recommendation_count"), int) and x["new_recommendation_count"] >= 2
               and all(c.get("canonical_facility_id") for c in x.get("candidates") or [])
               and len({c.get("canonical_facility_id") for c in x.get("candidates") or []}) == x["new_recommendation_count"]}
    prompt = {"role": "OOMNIKER_AI_DECISION_ADVISOR", "client_context": client_context, "governed_analysis": analysis,
              "hard_rules": ["Preserve every MUST and care need.", "Select measured NTH alternatives adding at least two recommendations.",
                             "Never invent counts, capabilities or quality judgments. Never change the profile."],
              "required_output": {"proposals": [{"parameter": "one supplied governed preference"}]}}
    try:
        packet = transport(prompt)
    except Exception as exc:
        return {"status": "AI_UNAVAILABLE", "message": None, "proposals": [], "error": str(exc)[:300]}
    proposals, seen = [], set()
    for proposed in packet.get("proposals") or []:
        if not isinstance(proposed, dict):
            continue
        key = str(proposed.get("parameter") or "")
        if key in allowed and key not in seen:
            proposals.append(dict(allowed[key]))
            seen.add(key)
    return {"status": "AI_ADVISORY_READY", "message": " ".join(p["message"] for p in proposals),
            "proposals": proposals, "profile_mutated": False}
