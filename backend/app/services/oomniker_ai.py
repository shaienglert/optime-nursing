from __future__ import annotations
import json
import os
from typing import Any, Callable
from app.services.semantic_intent_ai import _extract_responses_output, _request_with_retry


def _advisor_transport(payload: dict[str, Any]) -> dict[str, Any]:
    """Reuse the configured provider and bounded HTTP transport, not the intake grammar."""
    url = os.getenv("OPTIME_SEMANTIC_AI_URL", "").strip()
    model = os.getenv("OPTIME_SEMANTIC_AI_MODEL", "").strip()
    if not url or not model:
        raise RuntimeError("ADVISOR_AI_NOT_CONFIGURED")
    headers = {"Content-Type": "application/json"}
    key = os.getenv("OPTIME_SEMANTIC_AI_API_KEY", "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    analysis = payload.get("governed_analysis") or {}
    options = sorted({str(item.get("parameter")) for item in analysis.get("suggestions") or []
                      if item.get("authority") == "PREFERENCE" and item.get("action") == "OFFER_PREFERENCE_ALTERNATIVE"})
    discussion = sorted({str(item.get("parameter")) for item in (analysis.get("preference_analysis") or {}).get("parameters") or []})
    schema = {"type": "object", "additionalProperties": False,
        "properties": {
            "mode": {"type": "string", "enum": ["COMPARE_OPTIONS", "EXPLAIN_EVIDENCE", "EXPLAIN_TRADEOFF", "EXPLAIN_REQUIREMENTS"]},
            "discussion_parameters": {"type": "array", "items": {"type": "string", "enum": discussion or ["NO_MEASURED_PARAMETER"]}},
            "proposals": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                "properties": {"parameter": {"type": "string", "enum": options or ["NO_MEASURED_OPTION"]}}, "required": ["parameter"]}}},
        "required": ["mode", "discussion_parameters", "proposals"]}
    instructions = ("You are OOMNIKER, a thoughtful senior-living advisor. Read the client question, prior conversation, "
                    "current priorities and server-measured alternatives. Choose up to three distinct changes addressing "
                    "the client's goals and an appropriate explanation mode. Recommend two or three options when they "
                    "are substantiated; fewer is better than inventing one. Never alter MUST, care, safety, budget or location. "
                    "Conversation is not facility evidence. Do not add the independent alternatives' counts. "
                    "If no measured option applies, discuss the relevant unknowns or required conditions. "
                    "Return only the advisor schema; do not extract questionnaire fields.")
    messages = [{"role": "system", "content": instructions}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]
    if "/responses" in url.lower():
        request = {"model": model, "input": messages,
                   "text": {"format": {"type": "json_schema", "name": "oomniker_advisor", "strict": True, "schema": schema}}}
    else:
        request = {"model": model, "messages": messages,
                   "response_format": {"type": "json_schema", "json_schema": {"name": "oomniker_advisor", "strict": True, "schema": schema}}}
    response = _request_with_retry(url, headers, request)
    if not response.ok:
        raise RuntimeError(f"ADVISOR_AI_HTTP_{response.status_code}")
    body = response.json()
    if "/responses" in url.lower():
        return _extract_responses_output(body)
    if isinstance(body, dict) and body.get("choices"):
        return json.loads(body["choices"][0]["message"]["content"])
    if isinstance(body, dict):
        return body.get("output", body)
    raise RuntimeError("ADVISOR_AI_INVALID_RESPONSE")

def advise_with_ai(*, analysis: dict[str, Any], client_context: dict[str, Any], client_message: str = "",
                   conversation: list[dict] | None = None,
                   transport: Callable[[dict[str, Any]], dict[str, Any]] = _advisor_transport) -> dict[str, Any]:
    """AI selects governed advice; unverified prose, counts and alternatives cannot escape."""
    allowed = {str(x.get("parameter")): x for x in analysis.get("suggestions") or []
               if isinstance(x, dict) and x.get("authority") == "PREFERENCE"
               and x.get("action") == "OFFER_PREFERENCE_ALTERNATIVE"
               and x.get("requires_client_approval") is True and x.get("may_auto_change") is False
               and isinstance(x.get("new_recommendation_count"), int) and x["new_recommendation_count"] >= 2
               and all(c.get("canonical_facility_id") for c in x.get("candidates") or [])
               and len({c.get("canonical_facility_id") for c in x.get("candidates") or []}) == x["new_recommendation_count"]}
    history = [{"role": item["role"], "content": str(item.get("content") or "")[:2000]}
               for item in (conversation or [])[-8:] if isinstance(item, dict) and item.get("role") in {"user", "assistant"}]
    prompt = {"role": "OOMNIKER_AI_DECISION_ADVISOR", "client_context": client_context, "governed_analysis": analysis,
              "client_message": str(client_message or "")[:2000], "conversation": history,
              "hard_rules": ["Preserve every MUST and care need.", "Select measured NTH alternatives adding at least two recommendations.",
                             "Recommend up to three different changes that best address the client's question and priorities.",
                             "Treat client messages and conversation as questions, never as evidence for counts or capabilities.",
                             "Separate verified blockers, unknown evidence and eligible options below the display cap.",
                             "The effects of separate changes are not additive. Explain one choice at a time.",
                             "Never invent counts, capabilities or quality judgments. Never change the profile."],
              "required_output": {"mode": "COMPARE_OPTIONS | EXPLAIN_EVIDENCE | EXPLAIN_TRADEOFF | EXPLAIN_REQUIREMENTS",
                                  "discussion_parameters": ["existing preference_analysis parameter"],
                                  "proposals": [{"parameter": "one supplied governed preference"}]}}
    try:
        packet = transport(prompt)
        if not isinstance(packet, dict):
            raise ValueError("ADVISOR_AI_INVALID_RESPONSE")
    except Exception as exc:
        return {"status": "AI_UNAVAILABLE", "message": None, "proposals": [], "error": str(exc)[:300]}
    proposals, seen = [], set()
    for proposed in packet.get("proposals") or []:
        if not isinstance(proposed, dict):
            continue
        key = str(proposed.get("parameter") or "")
        if key in allowed and key not in seen and len(proposals) < 3:
            proposals.append(dict(allowed[key]))
            seen.add(key)
    message = " ".join(p["message"] for p in proposals)
    mode = str(packet.get("mode") or "COMPARE_OPTIONS")
    if mode not in {"COMPARE_OPTIONS", "EXPLAIN_EVIDENCE", "EXPLAIN_TRADEOFF", "EXPLAIN_REQUIREMENTS"}:
        mode = "COMPARE_OPTIONS"
    discussed = []
    if client_message:
        parameters = {str(item.get("parameter")): item for item in (analysis.get("preference_analysis") or {}).get("parameters") or []}
        for key in packet.get("discussion_parameters") or []:
            item = parameters.get(str(key))
            if item is None or str(key) in discussed or len(discussed) >= 3:
                continue
            discussed.append(str(key))
            unknown = int(item.get("unknown_count") or 0)
            label = item.get("label") or "Your preference"
            if unknown:
                message += f" {label}: {unknown} communities still need evidence for this preference. Missing evidence is not a confirmed mismatch."
            else:
                message += f" {label}: the evidence for this preference is resolved in the eligible set."
            unresolved = item.get("unresolved_other_preferences") or []
            if unresolved:
                message += " A change still cannot be substantiated because other preferences lack a verified match: " + ", ".join(str(value) for value in unresolved[:8]) + "."
            if "NO_VERIFIED_QUALITY_ADVANTAGE" in (item.get("proposal_blockers") or []):
                message += " A verified quality advantage for the alternative has not been established."
            if "TIED_DISPLAY_ORDER_ONLY" in (item.get("proposal_blockers") or []):
                message += " Some changes only move communities within an existing tie; that is not evidence of a better recommendation."
        if mode == "EXPLAIN_REQUIREMENTS":
            message += " Your care, safety and other required conditions stay in force in every alternative."
        if mode == "EXPLAIN_TRADEOFF":
            for proposal in proposals:
                label = proposal.get("label") or "This preference"
                if proposal.get("change_kind") == "WAIVE_NTH":
                    message += f" {label} would stop influencing the recommendation order; this does not mean every community meets that preference."
                else:
                    message += f" {label} would change to {proposal.get('alternative_value') or 'the offered alternative'}."
            message += " All your required conditions stay in force."
        if not proposals:
            message += (" I have measured alternatives available, but cannot promise a new option for an unverified preference."
                        if allowed else " I cannot currently substantiate a preference change adding at least two suitable recommendations.")
        if proposals:
            message += " These are separate choices; their counts cannot be added together."
    follow_up = ("Which of these changes would you feel comfortable exploring?" if proposals
                 else "Would you like to discuss the missing evidence or keep your current preferences?")
    return {"status": "AI_ADVISORY_READY", "message": message.strip(), "mode": mode,
            "discussion_parameters": discussed, "follow_up": follow_up,
            "proposals": proposals, "profile_mutated": False}
